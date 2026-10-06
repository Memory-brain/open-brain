#!/usr/bin/env python3
"""rlib — shared library of the retrieval eval engine.

Three pieces that any recall measurement needs:

  1. A deterministic CORPUS (which notes are retrievable) with typed fields
     (title, aliases, search_terms, body) — see iter_notes().
  2. A deterministic, ranked RETRIEVER — field-weighted BM25, an exact-match
     channel over metadata, and 1-hop expansion over the autolink graph.
     Without it you can measure the recall of ONE episode, not of a system:
     two runs of the same query through the agent do not return the same list.
  3. A RESOLVER of Retrieval Log wikilinks against the filesystem.
     A real log accumulates links that do not resolve (titles shortened while
     writing, notes renamed later — a quarter of them in the original vault).
     They are resolved on READ, by unique prefix, and the log is NOT rewritten:
     it is append-only with a "Never delete" policy, and repairing historical
     entries is the vault owner's decision, not a cleanup.

Vault root: $OPEN_BRAIN_VAULT if set; otherwise the first ancestor directory
that contains Resources/Retrieval Log.md.

Must run on Python 3.9: no "X | None" annotations.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from math import log

# Folders that are never part of the retrievable corpus: tooling, engines,
# archives and the system's own logs. Add your own non-note folders with the
# environment variable OB_SKIP_DIRS (comma-separated folder names).
SKIP_DIRS = {
    ".git", ".obsidian", ".cache", "node_modules", "_to_delete", "Archive",
    "Templates", "autolink", "engine", "eval-engine", "enrich-engine",
    "health-engine", "synthesize-engine", "course-engine", "vault-scan",
    "retrieval-eval", "Practice Log", "Session Logs", "Vault Health", "Evals",
} | {d.strip() for d in os.environ.get("OB_SKIP_DIRS", "").split(",") if d.strip()}
# ^ add your own folders through OB_SKIP_DIRS rather than editing this set.

# Files that are LOGS of the system itself: they contain the queries and the
# answers, so indexing them makes them win any search by construction (leakage).
SKIP_FILES = {
    "Retrieval Log.md", "Session Log.md", "Hot Cache.md",
    "Home.md", "README.md", "INSTALL.md", "CLAUDE.md",
}
SKIP_FILE_RE = re.compile(r"^(Retrieval Log|Session Log|CHANGELOG|"
                          r"Skill Improvements Log|INSTALL)", re.I)

# Stopwords: Spanish + English, so bilingual vaults tokenize sensibly.
STOP = set("""
a al algo alguna algunas alguno algunos ante antes aqui asi aun aunque cada casi como con
contra cual cuales cuando de del desde donde dos el ella ellas ello ellos en entre era eran
es esa esas ese eso esos esta estan estas este esto estos fue fueron ha hace hacen hacia han
hasta hay la las le les lo los mas me mi mientras mis mucho muy nada ni no nos o os otra otras
otro otros para pero poco por porque que se ser si sin sobre solo son su sus tambien tan tanto
te tiene tienen todo todos tu tus un una uno unos ya yo qué cómo cuál dónde cuándo por_qué
the a an and or of to in for on with without is are was were be been being that this these
those it its as at by from into no not but if then than so such can could should would may
might will do does did done have has had how what which who whom when where why your you
i me my we our they them their he she his her
""".split())


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def tokenize(s):
    s = strip_accents(s.lower())
    s = re.sub(r"[`*_>#\[\]\(\)\{\}\|]", " ", s)
    toks = re.findall(r"[a-z0-9][a-z0-9\-]{1,}", s)
    return [t for t in toks if t not in STOP and len(t) > 2]


def norm_title(s):
    """Title comparison key: no folder, no pipe alias, no accents, no
    punctuation, no truncation ellipsis."""
    s = s.split("|")[0]
    s = s.split("/")[-1]
    s = s.replace("…", " ").replace("...", " ")
    s = strip_accents(s.lower())
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def vault_root(start=None):
    """$OPEN_BRAIN_VAULT if set; otherwise walk up from `start` (or the cwd)
    to the first directory containing Resources/Retrieval Log.md."""
    env = os.environ.get("OPEN_BRAIN_VAULT")
    if env:
        if not os.path.isdir(env):
            raise SystemExit("OPEN_BRAIN_VAULT=%s is not a directory" % env)
        return os.path.abspath(env)
    d = os.path.abspath(start or os.getcwd())
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, "Resources", "Retrieval Log.md")):
            return d
        d = os.path.dirname(d)
    raise SystemExit("Vault not found: no ancestor contains Resources/Retrieval Log.md. "
                     "Set OPEN_BRAIN_VAULT to your vault root.")


# --------------------------------------------------------------- frontmatter

FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def parse_frontmatter(text):
    """Minimal, tolerant YAML parser: scalars, inline lists [a, b] and dash
    lists. Enough for aliases / search_terms / type / domain."""
    m = FM_RE.match(text)
    if not m:
        return {}, text
    fm, body = {}, text[m.end():]
    key, buf = None, []
    for raw in m.group(1).splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if re.match(r"^\s*-\s+", raw) and key:
            buf.append(re.sub(r"^\s*-\s+", "", raw).strip().strip("\"'"))
            continue
        if key and buf:
            fm[key] = buf
            buf = []
        km = re.match(r"^([A-Za-z_][\w\-]*)\s*:\s*(.*)$", raw)
        if not km:
            continue
        key, val = km.group(1).strip(), km.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            fm[key] = [v.strip().strip("\"'") for v in val[1:-1].split(",") if v.strip()]
            key = None
        elif val:
            fm[key] = val.strip("\"'")
            key = None
    if key and buf:
        fm[key] = buf
    return fm, body


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    return [str(v)] if str(v).strip() else []


def iter_notes(root):
    for dirpath, dirnames, filenames in os.walk(root):
        # sorted() is not cosmetic: os.walk does not guarantee directory order,
        # and indexing order decides ties in by_norm (titles that normalise the
        # same). Without it, two runs of the same eval give different numbers.
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP_DIRS and not d.startswith("."))
        for fn in sorted(filenames):
            if not fn.endswith(".md") or fn in SKIP_FILES or SKIP_FILE_RE.match(fn):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root)
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            fm, body = parse_frontmatter(text)
            yield {
                "rel": rel,
                "folder": rel.split(os.sep)[0],
                "title": fn[:-3],
                "aliases": _as_list(fm.get("aliases")) + _as_list(fm.get("alias")),
                "search_terms": _as_list(fm.get("search_terms")),
                "type": str(fm.get("type", "")),
                "domain": str(fm.get("domain", "")),
                "times_retrieved": fm.get("times_retrieved"),
                "body": body,
            }


# --------------------------------------------------------------- BM25 index

TITLE_W, META_W, BODY_W = 4, 3, 1
BODY_CHARS = 4000   # a long LN body dilutes idf; the first stretch is the claim


class Index(object):
    def __init__(self):
        self.docs = []          # [{rel, title, folder, ntoks}]
        self.tf = []            # [Counter]
        self.df = Counter()
        self.meta_tokens = []   # [set] title+aliases+search_terms (exact channel)
        self.by_rel = {}
        self.by_norm = defaultdict(list)   # norm_title -> [idx]
        self.avg_len = 0.0

    def add(self, note):
        t_title = tokenize(note["title"])
        t_meta = tokenize(" ".join(note["aliases"] + note["search_terms"]))
        t_body = tokenize(note["body"][:BODY_CHARS])
        tf = Counter()
        for t in t_title:
            tf[t] += TITLE_W
        for t in t_meta:
            tf[t] += META_W
        for t in t_body:
            tf[t] += BODY_W
        if not tf:
            return
        i = len(self.docs)
        self.docs.append({"rel": note["rel"], "title": note["title"],
                          "folder": note["folder"], "type": note["type"],
                          "ntoks": sum(tf.values())})
        self.tf.append(tf)
        self.meta_tokens.append(set(t_title) | set(t_meta))
        for t in tf:
            self.df[t] += 1
        self.by_rel[note["rel"]] = i
        self.by_norm[norm_title(note["title"])].append(i)

    def finalize(self):
        self.avg_len = (sum(d["ntoks"] for d in self.docs) / len(self.docs)) if self.docs else 0.0

    # ---- channel 1: BM25 with field-weighted tf
    def bm25(self, query, k=100, k1=1.4, b=0.72):
        qt = [t for t in tokenize(query) if self.df.get(t)]
        if not qt:
            return []
        N = len(self.docs)
        idf = {t: log(1 + (N - self.df[t] + 0.5) / (self.df[t] + 0.5)) for t in set(qt)}
        scores = defaultdict(float)
        postings = defaultdict(list)
        for i, tf in enumerate(self.tf):
            for t in set(qt):
                f = tf.get(t)
                if f:
                    postings[t].append((i, f))
        for t, plist in postings.items():
            w = idf[t]
            for i, f in plist:
                dl = self.docs[i]["ntoks"]
                scores[i] += w * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / (self.avg_len or 1)))
        # tie-break by rel: without a secondary key the order depends on string
        # hashing, which python randomises per process (PYTHONHASHSEED) -> two
        # runs of the same eval give different numbers.
        top = sorted(scores.items(), key=lambda x: (-x[1], self.docs[x[0]]["rel"]))[:k]
        return [(self.docs[i]["rel"], round(s, 4)) for i, s in top]

    # ---- channel 2: exact match over metadata (what the agent does with grep
    #      over frontmatter and Search Terms). Independent of BM25: no idf and
    #      no length, only how many query terms appear in the metadata.
    def meta_match(self, query, k=100, min_hits=2):
        qt = set(t for t in tokenize(query) if self.df.get(t))
        if not qt:
            return []
        N = len(self.docs)
        rare = {t: log(N / max(1, self.df[t])) for t in qt}
        out = []
        for i, mt in enumerate(self.meta_tokens):
            hits = qt & mt
            if len(hits) >= min_hits:
                # sorted(): float addition is not associative and the order of
                # a set of strings varies per process
                out.append((i, sum(rare[t] for t in sorted(hits)), len(hits)))
        out.sort(key=lambda x: (-x[1], -x[2], self.docs[x[0]]["rel"]))
        return [(self.docs[i]["rel"], round(s, 4)) for i, s, _ in out[:k]]

    def fingerprint(self):
        """Fingerprint of the document ORDER. lsa.npz stores vectors indexed by
        position and bridge.json stores hub indices: if the index is rebuilt and
        the order changes, those artifacts go out of sync and the channel
        silently contributes noise (it once dropped known-item hits from 90%
        to 0% without any error)."""
        import hashlib
        h = hashlib.sha1()
        for d in self.docs:
            h.update(d["rel"].encode("utf-8", "ignore"))
            h.update(b"\x00")
        return h.hexdigest()[:16]

    def save(self, path):
        json.dump({
            "docs": self.docs,
            "tf": [dict(c) for c in self.tf],
            "df": dict(self.df),
            "meta": [sorted(s) for s in self.meta_tokens],
            "avg_len": self.avg_len,
            "fingerprint": self.fingerprint(),
        }, open(path, "w", encoding="utf-8"))

    @classmethod
    def load(cls, path):
        raw = json.load(open(path, encoding="utf-8"))
        ix = cls()
        ix.docs = raw["docs"]
        ix.tf = [Counter(d) for d in raw["tf"]]
        ix.df = Counter(raw["df"])
        ix.meta_tokens = [set(s) for s in raw["meta"]]
        ix.avg_len = raw["avg_len"]
        for i, d in enumerate(ix.docs):
            ix.by_rel[d["rel"]] = i
            ix.by_norm[norm_title(d["title"])].append(i)
        return ix


def build_index(root):
    ix = Index()
    for note in iter_notes(root):
        ix.add(note)
    ix.finalize()
    return ix


# --------------------------------------------------------------- channel 3: graph

def load_graph(root):
    p = os.path.join(root, "autolink", "graph.jsonl")
    nb = defaultdict(set)
    title_by_slug = {}
    if not os.path.exists(p):
        return nb, title_by_slug
    for line in open(p, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        f, t = e.get("from"), e.get("to")
        if not f or not t:
            continue
        nb[f].add(t)
        nb[t].add(f)
        if e.get("from_title"):
            title_by_slug[f] = e["from_title"]
        if e.get("to_title"):
            title_by_slug[t] = e["to_title"]
    return nb, title_by_slug


def slugify(text):
    s = strip_accents(text.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def graph_hop(ix, nb, title_by_slug, seed_rels, limit=30):
    """1-hop neighbours of the seeds, resolved to corpus notes."""
    seeds = set()
    for rel in seed_rels:
        i = ix.by_rel.get(rel)
        if i is not None:
            seeds.add(slugify(ix.docs[i]["title"]))
    cnt = Counter()
    for s in sorted(seeds):
        for n in sorted(nb.get(s, ())):
            if n not in seeds:
                cnt[n] += 1
    out = []
    for slug, c in sorted(cnt.items(), key=lambda x: (-x[1], x[0])):
        title = title_by_slug.get(slug)
        if not title:
            continue
        idxs = ix.by_norm.get(norm_title(title))
        if idxs:
            out.append((ix.docs[idxs[0]]["rel"], c))
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------- link resolution

class Resolver(object):
    """log wikilink -> real corpus rel. Three passes: normalised exact match,
    unique prefix (titles shortened while writing), and unique containment."""

    def __init__(self, ix, root):
        self.ix = ix
        self.norm_keys = sorted(ix.by_norm.keys())
        # every .md in the vault, not only the corpus: a link can point to a
        # real note the corpus excludes (Archive, logs). Telling "does not
        # exist" from "exists but is not retrievable" matters for recall.
        self.all_titles = {}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames
                                 if not d.startswith(".") and d != "node_modules")
            for fn in filenames:
                if fn.endswith(".md"):
                    self.all_titles.setdefault(norm_title(fn[:-3]), os.path.relpath(
                        os.path.join(dirpath, fn), root))
        self._cache = {}

    def resolve(self, link):
        """-> (rel|None, status) with status in
        {exact, prefix, contains, outside_corpus, ambiguous, missing}"""
        if link in self._cache:
            return self._cache[link]
        key = norm_title(link)
        res = (None, "missing")
        if not key:
            self._cache[link] = res
            return res
        idxs = self.ix.by_norm.get(key)
        if idxs:
            res = (self.ix.docs[idxs[0]]["rel"], "exact")
        else:
            pref = [k for k in self.norm_keys if k.startswith(key)]
            if len(pref) == 1:
                res = (self.ix.docs[self.ix.by_norm[pref[0]][0]]["rel"], "prefix")
            elif len(pref) > 1:
                res = (None, "ambiguous")
            else:
                cont = [k for k in self.norm_keys if key in k]
                if len(cont) == 1:
                    res = (self.ix.docs[self.ix.by_norm[cont[0]][0]]["rel"], "contains")
                elif len(cont) > 1:
                    res = (None, "ambiguous")
                elif key in self.all_titles:
                    res = (self.all_titles[key], "outside_corpus")
        self._cache[link] = res
        return res


# --------------------------------------------------------------- Retrieval Log

LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _field(body, name):
    m = re.search(r"\*\*" + name + r"[^*]*\*\*\s*:?(.*?)(?=\n\*\*|\n---|\Z)", body, re.S)
    return m.group(1).strip() if m else None


def parse_log(root):
    """-> [{key, date, intent, query, returned[], used[], gaps, outcome, reformulation}]

    The Retrieval Log ($OPEN_BRAIN_VAULT/Resources/Retrieval Log.md) is the
    user-supplied gold source: entries are `## YYYY-MM-DD ... [intent: X]`
    blocks with `**Query**:`, `**Notas devueltas**:` (returned) and
    `**Notas usadas sustantivamente**:` (used) fields written by
    open-brain-retrieve. The Spanish field names are identifiers, kept verbatim.
    """
    path = os.path.join(root, "Resources", "Retrieval Log.md")
    if not os.path.exists(path):
        raise SystemExit("No Retrieval Log at %s. The eval measures against your own "
                         "log; run open-brain-retrieve a few times first." % path)
    text = open(path, encoding="utf-8", errors="ignore").read()
    parts = re.split(r"(?m)^(## \d{4}-\d{2}-\d{2}.*)$", text)
    entries = []
    for header, body in zip(parts[1::2], parts[2::2]):
        h = header.strip()
        date = re.match(r"##\s*(\d{4}-\d{2}-\d{2})", h).group(1)
        im = re.search(r"intent:\s*([^\]]+)", h)
        q = _field(body, "Query")
        if q:
            q = q.strip().strip('"').strip()
        ret = _field(body, "Notas devueltas") or ""
        use = _field(body, "Notas usadas") or ""
        entries.append({
            "key": h,
            "date": date,
            "intent": im.group(1).strip() if im else "",
            "query": q,
            "returned": LINK_RE.findall(ret),
            "used": LINK_RE.findall(use),
            "returned_is_prose": bool(ret) and len(LINK_RE.findall(ret)) == 0,
            "gaps": _field(body, "Gaps detectados"),
            "outcome": (_field(body, "Outcome") or "").split()[0].lower().strip(".,;—")
                       if _field(body, "Outcome") else "",
            "reformulation": bool(re.match(r"(s[ií]|yes)", (_field(body, r"Reformulation\?") or ""), re.I)),
            # Level B: relevant-but-not-returned notes declared by the user.
            "missing": bool(re.search(r"(?m)^\**missing\**\s*:\s*\S", body, re.I)),
            # Vault vocabulary written BEFORE retrieving. It is the only engine
            # lever that was significant in the original measurement. Reading it from the log
            # turns every retrieval into a reproducible eval row at no cost. Not
            # to be confused with "Términos que matchearon", which is
            # after-the-fact attribution.
            "expansion": (_field(body, "Expansi[oó]n") or "").strip(),
            # Entries opened by `log_entry.py` BEFORE searching. An open,
            # unclosed entry is not a defective entry: it is a query that was
            # recorded and whose retrieval never got written down. Telling it
            # apart from an incomplete log is what lets the gap be counted
            # instead of assumed. "" = hand-written entry, not instrumented.
            "state": (re.search(r"(?m)^\*\*Estado\*\*:\s*(\w+)", body).group(1)
                       if re.search(r"(?m)^\*\*Estado\*\*:\s*(\w+)", body) else ""),
        })
    return entries
