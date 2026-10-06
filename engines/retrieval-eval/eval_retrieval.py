#!/usr/bin/env python3
"""eval_retrieval — retrieval recall over your own vault, using the Retrieval Log
as the real query distribution.

Two layers, with different denominators and different labels. They are never mixed:

  LAYER 1 — recall vs recorded use (automatic, n = every query in the log).
    Gold = "Notas usadas sustantivamente" (notes used substantively) of each
    entry: notes the user DID use, hence relevant by definition. It measures
    whether the deterministic retriever recovers what the system already showed
    to be useful. Known, directional bias: it only contains notes the agent's
    retrieval ALREADY found, so it ignores what was never found. It is a
    ceiling, not a recall.

  LAYER 2 — TREC-style pooled recall (judged, on a sample).
    Pool = union of contributing systems at depth D. Relevance is judged for
    the whole pool and recall@k = relevant in top-k / relevant in the pool. The
    number is "recall relative to the pool", never absolute, and is reported
    with D and the systems. Queries with no relevant note in the pool are not
    recall failures: they are content gaps, and are listed as such.

GOLD SET — user-supplied, never bundled. There is no built-in list of queries,
titles or judgments. Every input is yours:

  $OPEN_BRAIN_VAULT/Resources/Retrieval Log.md   REQUIRED. The gold source. Each
      `## YYYY-MM-DD ... [intent: X]` entry with `**Query**:`, `**Notas devueltas**:`
      and `**Notas usadas sustantivamente**:` (as written by open-brain-retrieve /
      log_entry.py). `gold` fails with a clear message if it is missing.
  retrieval-eval/data/expansions.jsonl           optional. One JSON per line:
      {"qid": "q07", "expansion": "vault vocabulary terms"}. Newer log entries
      carry an `Expansión` field, which takes precedence.
  retrieval-eval/data/judgments.jsonl            optional, written by `judge-set`.
      {"qid": "q07", "rel": "Permanent Notes/X.md", "label": 0|1|2}
  retrieval-eval/data/human_judgments.jsonl      optional, same format, for `calibrate`.
  retrieval-eval/data/exclusions.jsonl           optional, written by `exclude`/`include`.

qids are positional over the log (`q%02d` = index of the entry). `data/` is your
non-derived work (version it privately); `.cache/` is regenerable.

The optional embedding channel stays OFF unless OB_EMBED=1 (see embed.py).

Commands:
  index                          rebuilds .cache/index.json (+ lsa.npz, bridge.json)
  gold                           builds .cache/gold.jsonl and audits link resolution
  layer1 [--k 10]                recall@k / MRR against recorded use
  pool [--depth 30] [--n N]      builds pool + judging worksheet (.cache/pool.jsonl, worksheet.md)
  judge --file F.jsonl           ingests judgments {qid, rel, label} (0|1|2)
  layer2 [--k 10]                pooled recall/precision with the ingested judgments
  exclude --qid Q --reason "..."  removes that log entry from ALL metrics
  include --qid Q                puts it back
  exclusions                     what is excluded, why and since when
  metrics                        flat JSON for a dashboard (Meta/metrics.json, kind engine)
  retrieve "<query>" [--k 20] [--expand "..."] [--json]
                                 candidates for the auto-retrieve L0 step (operational use)
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib
import lsa as lsa_mod
import bridge as bridge_mod
import embed as embed_mod

HERE = os.path.dirname(os.path.abspath(__file__))
# Optional local site-packages: if your python3 cannot install packages (e.g. a
# sandboxed VM), put scipy in retrieval-eval/.pylib. It is APPENDED to the path
# so it never shadows the system numpy. Only `index` uses it.
_PYLIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pylib")
if os.path.isdir(_PYLIB) and _PYLIB not in sys.path:
    sys.path.append(_PYLIB)
CACHE = os.path.join(HERE, ".cache")
IX_PATH = os.path.join(CACHE, "index.json")
GOLD_PATH = os.path.join(CACHE, "gold.jsonl")
POOL_PATH = os.path.join(CACHE, "pool.jsonl")
JUDG_PATH = os.path.join(CACHE, "judgments.jsonl")
EXT_PATH = os.path.join(CACHE, "pool_extended.jsonl")
EMB_PATH = os.path.join(CACHE, "embed.npz")

# Sixth channel behind a flag, OFF by default. In the original measurement the
# result was negative on two independent instruments (Layer 1 and the judged
# pool), so it does not enter the system the dashboard measures until there is
# evidence in its favour. The model is NOT broken — it wins on known-item
# lookups — it fails on real queries, which is a different thing.
# OB_EMBED=1 turns it on to experiment without touching code.
EMB_ON = os.environ.get("OB_EMBED", "0") != "0"


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def load_ix():
    if not os.path.exists(IX_PATH):
        sys.exit("The index is missing. Run: python3 eval_retrieval.py index")
    return rlib.Index.load(IX_PATH)


# ------------------------------------------------------------------ index / gold

def cmd_index(root):
    """Rebuilds the THREE artifacts together. They are not optional separately:
    lsa.npz and bridge.json reference index positions, so rebuilding only one
    puts them out of sync (and an out-of-sync channel does not fail, it returns
    noise)."""
    # Preflight: without scipy, lsa.build fails AFTER ix.save and the engine is
    # silently left broken. Check before touching any artifact.
    try:
        import numpy  # noqa: F401
        import scipy.sparse.linalg  # noqa: F401
    except ImportError as e:
        sys.exit("index aborted without touching anything: numpy/scipy missing in this "
                 "python3 (%s). Install them or run index where you have them." % e)
    ix = rlib.build_index(root)
    ix.finalize()
    os.makedirs(CACHE, exist_ok=True)
    ix.save(IX_PATH)
    _MODELS.clear()
    lsa_info = lsa_mod.build(ix, os.path.join(CACHE, "lsa.npz"))
    br_info = bridge_mod.build(root, ix, os.path.join(CACHE, "bridge.json"))
    emb_info = (embed_mod.build(root, ix, EMB_PATH)
                if EMB_ON and os.path.exists(embed_mod.MODEL_DIR) else None)
    out({"ok": True, "docs": len(ix.docs), "vocab": len(ix.df),
         "avg_len": round(ix.avg_len, 1), "fingerprint": ix.fingerprint(),
         "lsa": lsa_info, "bridge": br_info, "embed": emb_info,
         "folders": Counter(d["folder"] for d in ix.docs).most_common(10)})


def cmd_gold(root):
    ix = load_ix()
    rs = rlib.Resolver(ix, root)
    entries = rlib.parse_log(root)
    rows, stats = [], Counter()
    for n, e in enumerate(entries):
        if not e["query"]:
            stats["sin_query"] += 1
            continue
        gold, gold_status = [], Counter()
        for lk in e["used"]:
            rel, st = rs.resolve(lk)
            gold_status[st] += 1
            stats["used_" + st] += 1
            if rel and st != "outside_corpus":
                gold.append(rel)
        returned = []
        for lk in e["returned"]:
            rel, st = rs.resolve(lk)
            stats["ret_" + st] += 1
            if rel and st != "outside_corpus":
                returned.append(rel)
        rows.append({
            "qid": "q%02d" % n,
            "key": e["key"], "date": e["date"], "intent": e["intent"],
            "query": e["query"],
            "gold": sorted(set(gold)),
            "returned": sorted(set(returned)),
            "returned_is_prose": e["returned_is_prose"],
            "gaps": e["gaps"], "outcome": e["outcome"],
            "gold_status": dict(gold_status),
        })
        stats["queries"] += 1
        if gold:
            stats["queries_with_gold"] += 1
    with open(GOLD_PATH, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    resolved = sum(v for k, v in stats.items() if k.startswith("used_") and
                   k.split("_", 1)[1] in ("exact", "prefix", "contains"))
    total_used = sum(v for k, v in stats.items() if k.startswith("used_"))
    out({"ok": True, "queries": stats["queries"], "queries_with_gold": stats["queries_with_gold"],
         "links_used": total_used, "resolved_to_corpus": resolved,
         "resolution_rate": round(resolved / total_used, 3) if total_used else None,
         "detail": {k: v for k, v in sorted(stats.items())}})


DATA = os.path.join(HERE, "data")
EXP_PATH = os.path.join(CACHE, "expansions.jsonl")
if not os.path.exists(EXP_PATH) and os.path.exists(os.path.join(DATA, "expansions.jsonl")):
    EXP_PATH = os.path.join(DATA, "expansions.jsonl")   # data/ is not derived (user-supplied)


def load_expansions():
    """Expansion is the semantic step the agent does in its head and that is
    otherwise not recorded. Storing it turns it into a reproducible artifact:
    the subsequent retrieval is deterministic even if the expansion comes from
    an LLM. Optional file format: one {"qid": ..., "expansion": ...} per line."""
    exp = {}
    if os.path.exists(EXP_PATH):
        exp = {j["qid"]: j["expansion"] for j in
               (json.loads(l) for l in open(EXP_PATH, encoding="utf-8") if l.strip())}
    # Newer log entries carry an `Expansión` field written before retrieving. It
    # overrides the hand-written file — the file is a retrofit for older
    # entries, the log is the live source. The key is the same qid `gold`
    # assigns (position in the log).
    try:
        for i, e in enumerate(rlib.parse_log(rlib.vault_root(HERE))):
            if e.get("expansion"):
                exp["q%02d" % i] = e["expansion"]
    except Exception:
        pass
    return exp


EXCL_PATH = os.path.join(DATA, "exclusions.jsonl")   # data/ is not derived


def _qfingerprint(text):
    """Query fingerprint, so an exclusion keeps pointing at the entry the user
    excluded even if qids shift.

    qids are POSITIONAL over the Retrieval Log (`q%02d` by index). As long as the
    log is append-only they are stable, but an exclusion is a policy decision,
    not a measurement: if an entry is ever inserted in the middle, it is better
    for the exclusion to be flagged as orphaned than to start hiding another query.
    """
    import hashlib
    norm = " ".join((text or "").lower().split())
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]


def load_exclusions():
    """qid -> {reason, at, fingerprint, query}. Append-only, last line wins:
    `include` writes a line with excluded=false instead of deleting the previous
    one, like the rest of the system. No file, empty dict."""
    ex = {}
    if not os.path.exists(EXCL_PATH):
        return ex
    for line in open(EXCL_PATH, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        qid = r.get("qid")
        if not qid:
            continue
        if r.get("excluded") is False:
            ex.pop(qid, None)
        else:
            ex[qid] = r
    return ex


def load_gold(keep_excluded=False):
    """Gold set from the log, ALREADY without the excluded entries.

    This is the only place the filter is applied, which is why it holds for
    everything: layer1, pool, layer2, metrics and the audits all load through
    here. An exclusion applied in each command separately is an exclusion that
    some command forgets.

    `gold.jsonl` still contains ALL entries: the filter is a lens applied on
    read, not an amputation of the artifact. That way the dashboard can keep
    saying how many are excluded and why — the difference between scoping a
    measurement and dressing it up.
    """
    if not os.path.exists(GOLD_PATH):
        sys.exit("The gold set is missing. Run: python3 eval_retrieval.py gold "
                 "(it is built from your Resources/Retrieval Log.md)")
    rows = [json.loads(l) for l in open(GOLD_PATH, encoding="utf-8") if l.strip()]
    ex = load_exclusions()
    if not ex:
        return rows
    keep = []
    for r in rows:
        e = ex.get(r["qid"])
        if not e:
            keep.append(r)
            continue
        # Fingerprint mismatch: the entry at that qid today is not the one that
        # was excluded. The exclusion is not applied -- hiding the wrong query is
        # worse than measuring one too many -- and `exclusions` lists it as orphaned.
        fp = e.get("fingerprint")
        if fp and fp != _qfingerprint(r.get("query")):
            keep.append(r)
            continue
        r["excluded"] = True
        r["exclusion_reason"] = e.get("reason", "")
        if keep_excluded:
            keep.append(r)
    return keep


# ------------------------------------------------------------------ retriever

# Instruction boilerplate that appears in log queries and is not content: the
# agent ignores it because it understands the request; a lexical retriever
# scores it. Spanish and English forms.
QUERY_BOILERPLATE = re.compile(
    r"\b(recupera(me)?|recuperar|busca(me)?|buscar|dame|damelo|traeme|revisa|revisar|"
    r"quiero|necesito|puedes|podrias|ayudame|hazme|dime|piensas|opinas|piensa|"
    r"notas?|nota|vault|mi vault|del vault|open ?brain|permanent notes?|literature notes?|"
    r"que piensas|que opinas|por favor|"
    r"retrieve|search( for)?|find( me)?|look up|give me|show me|bring me|review|"
    r"i want|i need|can you|could you|help me|tell me|my vault|"
    r"what do you think|please)\b", re.I)


def clean_query(q):
    q = rlib.strip_accents(q or "")
    return QUERY_BOILERPLATE.sub(" ", q)


_MODELS = {}


def models(root, ix):
    # The specific key is checked, not `if not _MODELS`: the note-type prior also
    # caches here, and with the generic guard asking for the prior before the
    # channels was enough for the channels never to load.
    if "lsa" not in _MODELS:
        lp = os.path.join(CACHE, "lsa.npz")
        bp = os.path.join(CACHE, "bridge.json")
        # Without numpy the LSA channel is simply unavailable; the rest still runs.
        L = (lsa_mod.LSA(lp, ix)
             if (os.path.exists(lp) and lsa_mod.np is not None) else None)
        B = bridge_mod.Bridge(bp, ix, L) if os.path.exists(bp) else None
        E = embed_mod.Embed(EMB_PATH, ix) if (EMB_ON and os.path.exists(EMB_PATH)) else None
        _MODELS["lsa"], _MODELS["bridge"], _MODELS["embed"] = L, B, E
    return _MODELS["lsa"], _MODELS["bridge"], _MODELS["embed"]


def _only_candidates(ix, pairs, k):
    out = []
    for rel, s in pairs:
        i = ix.by_rel.get(rel)
        if i is not None and bridge_mod.is_candidate(ix.docs[i]["folder"]):
            out.append(rel)
            if len(out) >= k:
                break
    return out


def channels(ix, nb, tbs, query, depth, root=None):
    """-> dict channel -> ranked [rel]. Independent channels, all restricted to
    candidate folders (hubs are a bridge, not an answer)."""
    q = clean_query(query)
    L, B, EM = models(root or rlib.vault_root(HERE), ix)
    bm = _only_candidates(ix, ix.bm25(q, k=depth * 6), depth)
    mm = _only_candidates(ix, ix.meta_match(q, k=depth * 6), depth)
    sem = _only_candidates(ix, L.search(q, k=depth * 6), depth) if L else []
    br = _only_candidates(ix, B.search(q, k=depth * 4), depth) if B else []
    # The embedding channel is fed the query WITHOUT stripping boilerplate: the
    # model understands the whole sentence and removing "find notes about" robs
    # it of context — unlike BM25, which would score it as content.
    emb = _only_candidates(ix, EM.search(query, k=depth * 6), depth) if EM else []
    seeds = (emb[:5] + sem[:5] + bm[:5] + br[:5])
    # The hop used to get depth//3 while the rest got the full depth, and it is
    # the best of the five channels. Measured with leave-one-session-out over
    # the co-use edges (without LOSO the hop is inflated ~20pp, because the
    # edges derive from the same log that defines the gold): raising the cap to
    # depth and the weight from 0.5 to 1.5 improved r@10, r@50 and MRR all at
    # once, which rules out a trade-off. It is not raised further: with a few
    # dozen queries, weight 3.0 maximises r@50 but already hurts MRR, i.e. above
    # 2.0 it is fitting noise.
    hop = _only_candidates(ix, rlib.graph_hop(ix, nb, tbs, seeds, limit=depth * 4),
                           max(10, depth))
    return {"bm25": bm, "meta": mm, "lsa": sem, "bridge": br, "hop": hop, "embed": emb}


# Note-type prior. In the vault this was calibrated on, Permanent Notes were a
# few percent of the indexed corpus but well over half of what was actually
# used: a ~20x enrichment. The channels do not know that — they score by text
# similarity, and a long LN beats the PN that compresses it. Measured with
# leave-one-session-out, the prior roughly doubled r@10 and MRR and raised r@50
# by ~15 pp.
#
# The multiplier saturates: from 8 upwards the result is identical up to 200,
# because the real effect is not "score higher" but ORDER BY TIERS — PNs first,
# the rest behind. So there is no constant to tune, and it is not a parameter
# overfitted to a small n: there is no peak, there is a plateau.
#
# 2-fold x20 cross-validation held up on unseen queries, and the negative
# control (the same prior on Search Terms, Projects or Mentors) moved nothing
# or made things worse. The effect belongs to PNs, not to "favouring a small
# folder".
#
# Second tier, maturity: growing/evergreen above seed. It does not change
# recall (noise) but raises MRR — it puts the good note earlier. And
# `times_retrieved` is NOT used even though it also scores: that counter is
# incremented by the Retrieval Log itself, so predicting the gold with it would
# be the same circularity that inflated the hop by 20 points.
PRIOR_PN = 8.0
PRIOR_MADURA = 3.0
MADURAS = ("growing", "evergreen")
_MATURITY_RE = re.compile(r"^maturity:\s*(.+)$", re.M)


def note_prior(root, ix):
    """rel -> multiplier. Read from the PNs' frontmatter (fast) instead of being
    stored in the index: that way there is no fourth artifact that can go out of
    sync, which is the failure mode that already cost the lsa channel once."""
    if "prior" not in _MODELS:
        pri = {}
        for d in ix.docs:
            if d["folder"] != "Permanent Notes":
                continue
            m = 0.0
            try:
                head = open(os.path.join(root, d["rel"]), encoding="utf-8",
                            errors="ignore").read(1200)
                g = _MATURITY_RE.search(head)
                m = PRIOR_MADURA if (g and g.group(1).strip().strip('"\'') in MADURAS) else 1.0
            except OSError:
                m = 1.0
            pri[d["rel"]] = PRIOR_PN * m
        _MODELS["prior"] = pri
    return _MODELS["prior"]


def fuse(ch, k=None, prior=None):
    """Reciprocal rank fusion — a single system ranking from the channels, with
    the note-type prior applied after fusing."""
    W = {"bm25": 1.0, "meta": 0.8, "lsa": 1.0, "bridge": 0.9, "hop": 1.5, "embed": 1.2}
    sc = defaultdict(float)
    for name, lst in ch.items():
        for i, rel in enumerate(lst):
            sc[rel] += W.get(name, 1.0) / (60 + i + 1)
    if prior:
        for rel in list(sc):
            p = prior.get(rel)
            if p:
                sc[rel] *= p
    ranked = [r for r, _ in sorted(sc.items(), key=lambda x: (-x[1], x[0]))]
    return ranked[:k] if k else ranked


# ------------------------------------------------------------------ automatic expansion

# Query expansion is the biggest lever measured in the whole engine: it was
# significant in the original measurement — the only intervention that was. The problem is that an LLM writes it
# in its head and it is not recorded, so when the agent does not produce one,
# the retrieval goes out bare.
#
# This is the floor, not the ceiling: pseudo-relevance feedback (classic RM3).
# A first pass is run, the discriminating terms of what came back are taken and
# the query is re-asked. No LLM, deterministic, no network.
#
# In the original measurement its gain over no expansion was positive but its
# confidence interval crossed zero, so it is NOT a substitute for LLM expansion
# (which was significant). That is why it only
# fires when there is no expansion: there, what it competes with is not the
# LLM, it is nothing.
#
# Terms are only taken from Permanent Notes: they are the vault's compressed
# vocabulary and give better expansion than the whole corpus (fewer queries
# that recover zero gold). With 20 terms instead of 8 recall rises slightly but
# MRR drops clearly: it stays at 8, which improved all four metrics at once.
PRF_DOCS = 10
PRF_TERMS = 8
PRF_MIN_DF = 3
PRF_MAX_DF_RATIO = 0.05


def auto_expand(root, ix, nb, tbs, query, n_docs=PRF_DOCS, n_terms=PRF_TERMS):
    """LLM-free expansion: discriminating terms of the best-ranked PNs in a first
    pass. Deterministic — the ranking tie-break already has a secondary key and
    here it sorts by (-weight, term)."""
    import math
    ch = channels(ix, nb, tbs, query, depth=50, root=root)
    first = fuse(ch, k=n_docs * 3, prior=note_prior(root, ix))
    N = len(ix.docs)
    cnt = defaultdict(float)
    taken = 0
    for rel in first:
        i = ix.by_rel.get(rel)
        if i is None or ix.docs[i]["folder"] != "Permanent Notes":
            continue
        taken += 1
        for t, f in ix.tf[i].items():
            df = ix.df.get(t, 1)
            if df < PRF_MIN_DF or df > N * PRF_MAX_DF_RATIO:
                continue
            cnt[t] += (1.0 + math.log(f)) * math.log(N / df)
        if taken >= n_docs:
            break
    qt = set(rlib.tokenize(clean_query(query)))
    ranked = sorted(cnt.items(), key=lambda x: (-x[1], x[0]))
    return " ".join([t for t, _ in ranked if t not in qt][:n_terms])


# ------------------------------------------------------------------ layer 1

def compute_layer1(root, ks, expanded=False, prf=False):
    ix, (nb, tbs) = load_ix(), rlib.load_graph(root)
    rows = [r for r in load_gold() if r["gold"]]
    exp = load_expansions() if expanded else {}
    agg = {k: [] for k in ks}
    rr, per_q = [], []
    for r in rows:
        if prf:
            prf_terms = auto_expand(root, ix, nb, tbs, r["query"])
            qtext = r["query"] + ("  " + prf_terms if prf_terms else "")
        else:
            qtext = r["query"] + ("  " + exp.get(r["qid"], "") if exp else "")
        ch = channels(ix, nb, tbs, qtext, depth=100, root=root)
        ranked = fuse(ch, prior=note_prior(root, ix))
        gold = set(r["gold"])
        pos = [i for i, rel in enumerate(ranked) if rel in gold]
        for k in ks:
            hit = len([i for i in pos if i < k])
            agg[k].append(hit / len(gold))
        rr.append(1.0 / (pos[0] + 1) if pos else 0.0)
        # features used by the PRF reanalysis: always computed, they cost nothing
        # extra, and are only read when the caller uses prf=True.
        ch_raw = ch if not prf else channels(ix, nb, tbs, r["query"], depth=100, root=root)
        ranked_raw = ranked if not prf else fuse(ch_raw, prior=note_prior(root, ix))
        top10 = ranked_raw[:10]
        folders = set()
        for rel in top10:
            i = ix.by_rel.get(rel)
            if i is not None:
                folders.add(ix.docs[i]["folder"])
        n_cands_iniciales = len(set(rel for lst in ch_raw.values() for rel in lst))
        per_q.append({"qid": r["qid"], "date": r["date"], "n_gold": len(gold),
                      "recall10": round(len([i for i in pos if i < 10]) / len(gold), 3),
                      "recall50": round(len([i for i in pos if i < 50]) / len(gold), 3),
                      "first_rank": (pos[0] + 1) if pos else None,
                      "query": r["query"][:90],
                      "length_chars": len(r["query"]),
                      "n_concepts": len(set(rlib.tokenize(clean_query(r["query"])))),
                      "n_initial_candidates": n_cands_iniciales,
                      "folder_dispersion_top10": len(folders)})
    res = {"n_queries": len(rows), "expanded": bool(exp), "prf": prf,
           "recall": {("recall@%d" % k): round(sum(v) / len(v), 4) for k, v in agg.items()},
           "mrr": round(sum(rr) / len(rr), 4) if rr else None,
           "queries_without_any_gold_retrieved": sum(1 for p in per_q if p["first_rank"] is None)}
    return res, per_q


def cmd_layer1(root, ks, expanded=False):
    res, per_q = compute_layer1(root, ks, expanded)
    json.dump({"summary": res, "per_query": per_q},
              open(os.path.join(CACHE, "layer1.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    out(res)


# ------------------------------------------------------------------ layer 2: pool

def cmd_pool(root, depth, n, seed_kind, expanded=True, qids=None):
    """TREC-style pool with TWO contributing systems:

      system A = the agent (what the Retrieval Log records as returned),
      system B = this engine's deterministic retriever (5 channels, expanded).

    Pooling two independent systems is what makes the number defensible: the
    agent contributes what it finds through conversation context (and that no
    text retriever recovers), the engine contributes what the agent never
    looked at. With the judged pool, the recall of EACH system is computed over
    the same denominator — including the agent's, which is the one the user
    actually relies on.
    """
    ix, (nb, tbs) = load_ix(), rlib.load_graph(root)
    rows = load_gold()
    exp = load_expansions() if expanded else {}
    if qids:
        want = set(qids.split(","))
        rows = [r for r in rows if r["qid"] in want]
    elif seed_kind == "with-gold":
        rows = [r for r in rows if r["gold"]]
    if n:
        step = max(1, len(rows) // n)
        rows = rows[::step][:n]
    pool_rows = []
    for r in rows:
        qtext = r["query"] + ("  " + exp.get(r["qid"], "") if exp else "")
        ch = channels(ix, nb, tbs, qtext, depth=depth, root=root)
        mine = fuse(ch, k=depth, prior=note_prior(root, ix))
        agent_ret, agent_used = list(r["returned"]), set(r["gold"])
        seen, cands = set(), []
        def add(rel, source, rank):
            if rel in seen:
                for c in cands:
                    if c["rel"] == rel and source not in c["sources"]:
                        c["sources"].append(source)
                return
            seen.add(rel)
            i = ix.by_rel.get(rel)
            cands.append({
                "rel": rel,
                "title": ix.docs[i]["title"] if i is not None else rel,
                "folder": ix.docs[i]["folder"] if i is not None else "",
                "sources": [source],
                "rank_mine": (mine.index(rel) + 1) if rel in mine else None,
                "rank_agent": (agent_ret.index(rel) + 1) if rel in agent_ret else None,
                "used_by_agent": rel in agent_used,
            })
        for j, rel in enumerate(agent_ret):
            add(rel, "agent", j + 1)
        for rel in sorted(agent_used):
            add(rel, "agent_used", 0)
        for j, rel in enumerate(mine):
            add(rel, "engine", j + 1)
        pool_rows.append({"qid": r["qid"], "date": r["date"], "query": r["query"],
                          "expansion": exp.get(r["qid"], ""),
                          "agent_returned": agent_ret, "agent_used": sorted(agent_used),
                          "engine_ranked": mine, "candidates": cands})
    with open(POOL_PATH, "w", encoding="utf-8") as fh:
        for p in pool_rows:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")
    wpath = os.path.join(CACHE, "worksheet.md")
    to_judge = 0
    with open(wpath, "w", encoding="utf-8") as fh:
        fh.write("# Judging worksheet — 2-system pool (agent + engine), depth %d\n\n" % depth)
        fh.write("Labels: **2** answers the query · **1** partially relevant · **0** not relevant.\n")
        fh.write("`[U]` = used by the agent -> already worth 2, not judged. "
                 "`A#`/`E#` = rank in the agent / in the engine.\n\n")
        for p in pool_rows:
            fh.write("## %s (%s)\n\n**Query**: %s\n\n" % (p["qid"], p["date"], p["query"]))
            for c in p["candidates"]:
                if c["used_by_agent"]:
                    continue
                to_judge += 1
                tag = "A%s" % c["rank_agent"] if c["rank_agent"] else ""
                tag += (" E%s" % c["rank_mine"]) if c["rank_mine"] else ""
                fh.write("- ( ) %-28s %s  `%s`\n" % (tag, c["title"][:110], c["rel"]))
            fh.write("\n")
    out({"ok": True, "queries": len(pool_rows), "depth": depth,
         "pool_total": sum(len(p["candidates"]) for p in pool_rows),
         "prelabeled_agent_use": sum(1 for p in pool_rows for c in p["candidates"]
                                           if c["used_by_agent"]),
         "to_judge": to_judge, "worksheet": wpath})


def cmd_pool_extend(root, depth, system="bm25_raw"):
    """Adds a THIRD contributing system to the already judged pool: raw BM25,
    unexpanded and single-channel.

    It is the cheapest lever against contribution bias. With two systems, each
    is measured against qrels it mostly wrote itself (see `loro`); a third
    independent run adds relevant notes neither had seen and lowers that share.
    Raw BM25 works precisely because it is weak and different: it contributes
    pure lexical matches, where the fused engine and the agent are blind at once.

    It does NOT overwrite .cache/pool.jsonl. It writes a separate extended pool
    and a worksheet with only what is left to judge, so the dashboard's live
    number does not drop while the extension is half judged.
    """
    if not os.path.exists(POOL_PATH):
        sys.exit("The base pool is missing. Run: python3 eval_retrieval.py pool")
    ix = load_ix()
    jud = _judgments()
    EM = embed_mod.Embed(EMB_PATH, ix) if system == "embed" else None
    if system == "embed" and EM is None:
        sys.exit(".cache/embed.npz is missing. Run: OB_EMBED=1 python3 eval_retrieval.py index")
    exp = load_expansions()
    pool = _read_pool()
    nuevos, filas = 0, []
    for p in pool:
        if system == "embed":
            q = p["query"] + "  " + exp.get(p["qid"], "")
            bm = _only_candidates(ix, EM.search(q, k=depth * 6), depth)
        else:
            bm = _only_candidates(ix, ix.bm25(clean_query(p["query"]), k=depth * 6), depth)
        seen = {c["rel"] for c in p["candidates"]}
        cands = list(p["candidates"])
        for c in cands:
            if c["rel"] in bm and system not in c["sources"]:
                c["sources"].append(system)
                c["rank_bm25_raw"] = bm.index(c["rel"]) + 1
        for rel in bm:
            if rel in seen:
                continue
            i = ix.by_rel.get(rel)
            cands.append({"rel": rel,
                          "title": ix.docs[i]["title"] if i is not None else rel,
                          "folder": ix.docs[i]["folder"] if i is not None else "",
                          "sources": [system], "rank_mine": None, "rank_agent": None,
                          "rank_bm25_raw": bm.index(rel) + 1, "used_by_agent": False})
            nuevos += 1
        q = dict(p, candidates=cands, bm25_ranked=bm)
        filas.append(q)
    ext = os.path.join(CACHE, "pool_extended.jsonl")
    with open(ext, "w", encoding="utf-8") as fh:
        for q in filas:
            fh.write(json.dumps(q, ensure_ascii=False) + "\n")
    wpath = os.path.join(CACHE, "worksheet_extended.md")
    pend = 0
    with open(wpath, "w", encoding="utf-8") as fh:
        fh.write("# Judging worksheet — ONLY what the third system adds (%s, depth %d)\n\n" % (system, depth))
        fh.write("Labels: **2** answers the query · **1** partially relevant · **0** not relevant.\n\n")
        for q in filas:
            falta = [c for c in q["candidates"]
                     if not c["used_by_agent"] and (q["qid"], c["rel"]) not in jud]
            if not falta:
                continue
            fh.write("## %s\n\n**Query**: %s\n\n" % (q["qid"], q["query"]))
            for c in falta:
                pend += 1
                fh.write("- ( ) B%-4s %s  `%s`\n"
                         % (c.get("rank_bm25_raw", "-"), c["title"][:105], c["rel"]))
            fh.write("\n")
    out({"ok": True, "pool_extended": ext, "worksheet": wpath,
         "new_candidates": nuevos, "judgments_pending": pend,
         "note": "the dashboard keeps reading .cache/pool.jsonl until the extension is "
                 "fully judged; then `layer2 --pool extended` and it is promoted."})


def cmd_judge(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    seen = {}
    if os.path.exists(JUDG_PATH):
        for l in open(JUDG_PATH, encoding="utf-8"):
            if l.strip():
                j = json.loads(l)
                seen[(j["qid"], j["rel"])] = j
    for j in rows:
        seen[(j["qid"], j["rel"])] = j
    with open(JUDG_PATH, "w", encoding="utf-8") as fh:
        for j in seen.values():
            fh.write(json.dumps(j, ensure_ascii=False) + "\n")
    out({"ok": True, "judgments_total": len(seen), "new_or_updated": len(rows)})


def cmd_layer2(ks, tag="", which="auto"):
    path = {"base": POOL_PATH, "extended": EXT_PATH}.get(which) or _pool_in_use()[0]
    if not os.path.exists(path):
        sys.exit("The pool is missing. Run: python3 eval_retrieval.py pool")
    pool = _read_pool(path)
    jud = {}
    if os.path.exists(JUDG_PATH):
        for l in open(JUDG_PATH, encoding="utf-8"):
            if l.strip():
                j = json.loads(l)
                jud[(j["qid"], j["rel"])] = int(j["label"])
    ag_rec, ag_prec, en_rec = [], [], {k: [] for k in ks}
    gaps, per_q, incompletas, sin_lista = [], [], [], []
    for p in pool:
        labels = {}
        for c in p["candidates"]:
            if c["used_by_agent"]:
                labels[c["rel"]] = 2
            elif (p["qid"], c["rel"]) in jud:
                labels[c["rel"]] = jud[(p["qid"], c["rel"])]
        pend = len(p["candidates"]) - len(labels)
        if pend:
            incompletas.append({"qid": p["qid"], "missing": pend})
            continue
        rel_set = {r for r, v in labels.items() if v >= 1}
        if not rel_set:
            gaps.append({"qid": p["qid"], "query": p["query"][:110]})
            continue
        # If the log did not write the returned list (prose field), there is no
        # system A to measure: it is missing data, NOT zero recall. It is excluded
        # from the agent's numerator and reported separately.
        if p["agent_returned"]:
            ar = len(rel_set & set(p["agent_returned"])) / len(rel_set)
            ap = len(rel_set & set(p["agent_returned"])) / len(p["agent_returned"])
            ag_rec.append(ar)
            ag_prec.append(ap)
        else:
            ar = ap = None
            sin_lista.append(p["qid"])
        row = {"qid": p["qid"], "n_relevant_pool": len(rel_set),
               "recall_agent": round(ar, 3) if ar is not None else None,
               "precision_agent": round(ap, 3) if ap is not None else None}
        for k in ks:
            v = len(rel_set & set(p["engine_ranked"][:k])) / len(rel_set)
            en_rec[k].append(v)
            row["recall_motor@%d" % k] = round(v, 3)
        per_q.append(row)
    def avg(v):
        return round(sum(v) / len(v), 4) if v else None
    res = {"n_queries_complete": len(per_q),
           "pool": {"systems": ["agent (Retrieval Log)", "deterministic engine (5 channels)"]},
           "agent": {"recall_pooled": avg(ag_rec), "precision": avg(ag_prec),
                      "n": len(ag_rec),
                      "excluded_log_without_returned_list": sin_lista},
           "engine": {("recall@%d" % k): avg(v) for k, v in en_rec.items()},
           "content_gaps_without_relevant_in_pool": gaps,
           "queries_with_incomplete_judgments": incompletas,
           "per_query": per_q}
    json.dump(res, open(os.path.join(CACHE, "layer2.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # A layer2 run is a deliberate measurement: it enters the history so the
    # paired gate has something to compare against. The dashboard (`metrics`)
    # does not write history — if it did, refreshing the screen would count as
    # measuring.
    rob = _layer2_stats(1, path)
    res["pool_used"] = os.path.basename(path)
    _append_run(rob, tag=tag)
    res["robust"] = {k: rob[k] for k in
                       ("agent_recall_ci", "agent_rbp", "agent_rbp_residual",
                        "engine_rbp", "engine_rbp_residual", "agent_bpref",
                        "engine_bpref", "loro", "bm25_raw_r20")} if rob else None
    res["paired_vs_previous_run"] = _paired_last()
    out({k: v for k, v in res.items() if k != "per_query"})


# ------------------------------------------------------------------ retrieve (operational use)

def cmd_retrieve(root, query, k, expand, as_json, log_id="", intent="implicit", sidecar=True):
    """Second candidate source for the auto-retrieve L0 step.

    In the original judged pool the agent returned at high precision but low
    recall, and this engine alone found several times more of the pool's
    relevant notes than the agent alone. The agent does not need tuning, it
    needs to look at more candidates. This command gives it 20 in ~1 s; triage
    stays with the agent. If the index is missing or stale, it says how stale
    and continues: the protocol is "if it fails, continue".
    """
    import time
    if not os.path.exists(IX_PATH):
        out({"ok": False, "error": "no index", "fix": "python3 eval_retrieval.py index"})
        return 1
    ix = load_ix()
    nb, tbs = rlib.load_graph(root)
    # If the agent brings an expansion, its own wins: that is the one measured as
    # significant. If it brings none, the engine makes one — there, what PRF
    # competes with is not the LLM, it is no expansion at all.
    auto = ""
    if not expand:
        auto = auto_expand(root, ix, nb, tbs, query)
    qtext = query + ("  " + (expand or auto) if (expand or auto) else "")
    ch = channels(ix, nb, tbs, qtext, depth=max(k, 20), root=root)
    ranked = fuse(ch, k=k, prior=note_prior(root, ix))
    prov = {}
    for name, lst in ch.items():
        for i, rel in enumerate(lst):
            prov.setdefault(rel, []).append("%s@%d" % (name, i + 1))
    age_days = round((time.time() - os.path.getmtime(IX_PATH)) / 86400, 1)
    rows = []
    for rel in ranked:
        i = ix.by_rel.get(rel)
        d = ix.docs[i]
        rows.append({"title": d["title"], "folder": d["folder"], "rel": rel,
                     "channels": prov.get(rel, [])})
    # Automatic sidecar. It used to be a manual protocol step and barely got a
    # handful of lines in weeks: any logging instruction that depends on
    # remembering is not followed. Now the engine writes it when answering.
    if sidecar:
        try:
            import datetime as _dt
            sc = os.path.join(root, "Resources", "Retrieval Candidates.jsonl")
            row = {"date": _dt.date.today().isoformat(), "intent": intent or "implicit",
                   "query": query, "candidates": rows}
            if log_id:
                row["log_id"] = log_id
            with open(sc, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception as e:  # the protocol is "if it fails, continue"
            sys.stderr.write("sidecar not written: %s\n" % e)
    if as_json:
        out({"ok": True, "query": query, "expand": expand or "", "expand_auto": auto,
             "expand_source": "agente" if expand else ("prf" if auto else "ninguna"),  # output values kept for compatibility
             "k": k, "index_age_days": age_days, "index_docs": len(ix.docs),
             "candidates": rows})
    else:
        print("# %d candidates · index %.1f days old (%d notes)%s"
              % (len(rows), age_days, len(ix.docs),
                 ("\n# automatic expansion (PRF, no LLM): " + auto) if auto else ""))
        for j, r in enumerate(rows, 1):
            print("%2d. [[%s]]  (%s · %s)" % (j, r["title"], r["folder"], ",".join(r["channels"][:3])))
    return 0


# ------------------------------------------------------------------ robust measures
#
# A 2-system pool at depth 20 is not a reusable collection: each system
# contributed most of the relevant notes it is measured against. Recall@k cannot
# say so; these measures can. All are deterministic (the bootstrap has a fixed
# seed) because an eval that gives two different numbers for the same input is
# not an eval.

BOOT_SEED = 12345   # arbitrary fixed seed; any constant works
BOOT_N = 20000


def _mean(v):
    return sum(v) / len(v) if v else None


def _bootstrap_ci(vals, alpha=0.05, n=BOOT_N, seed=BOOT_SEED):
    """Percentile bootstrap CI on the mean. With few queries the interval is
    wide: that is exactly the information missing when a bare percentage is
    quoted."""
    if len(vals) < 2:
        return (None, None)
    rnd = random.Random(seed)
    m = len(vals)
    boots = sorted(sum(rnd.choice(vals) for _ in range(m)) / m for _ in range(n))
    lo = boots[int((alpha / 2) * n)]
    hi = boots[min(n - 1, int((1 - alpha / 2) * n))]
    return (round(lo, 4), round(hi, 4))


def _rbp(ranked, labels, p=0.8):
    """Rank-Biased Precision (Moffat & Zobel) with an explicit residual.

    RBP models a reader who, after each result, keeps going down with
    probability p. Its virtue here is not the score but the RESIDUAL: how much
    of the uncertainty comes from documents nobody judged. With shallow pools
    the residual stops being a footnote and becomes part of the figure: an RBP
    of 0.30 with residual 0.45 does not say 0.30, it says "between 0.30 and 0.75".
    """
    score = res = 0.0
    for i, rel in enumerate(ranked):
        w = (1 - p) * (p ** i)
        if rel in labels:
            if labels[rel] >= 1:
                score += w
        else:
            res += w                      # unjudged: nobody knows. Goes to the residual.
    res += p ** len(ranked)               # unseen tail below the list
    return round(score, 4), round(res, 4)


def _bpref(ranked, labels, rel_set):
    """bpref (Buckley & Voorhees) — only looks at JUDGED documents, so it does not
    penalise a system for retrieving things the pool never saw. It is the
    standard measure when judgments are incomplete, which is exactly this case."""
    nonrel = [r for r in ranked if r in labels and labels[r] == 0]
    R, N = len(rel_set), len(nonrel)
    if not R:
        return None
    cap = min(R, N)
    total, seen_nonrel = 0.0, 0
    for r in ranked:
        if r in labels and labels[r] == 0:
            seen_nonrel += 1
        elif r in rel_set:
            total += 1 - (min(seen_nonrel, cap) / cap if cap else 0)
    return round(total / R, 4)


def _loro(per_q):
    """Leave-one-run-out: the standard pool reusability test (Zobel 1998).

    The relevant notes contributed ONLY by one system are removed from the
    qrels and that system is re-evaluated. If its score collapses, its original
    number was propped up by what it put into the pool itself, and the
    collection cannot be used to judge a third system. Computed for both
    systems: the bias is not only the engine's.
    """
    ag_full, ag_loro, en_full, en_loro = [], [], [], []
    for q in per_q:
        rel, A, E = q["rel"], q["A"], q["E20"]
        # Only queries where BOTH systems are measurable. Comparing the agent on
        # one subset with the engine on a larger one would repeat, inside the
        # bias test, the denominator error the test exists to catch.
        if not A:
            continue
        ag_full.append(len(rel & A) / len(rel))
        sin_ag = rel & E                           # qrels without the agent's unique contributions
        if sin_ag:
            ag_loro.append(len(rel & A & E) / len(sin_ag))
        en_full.append(len(rel & E) / len(rel))
        sin_en = rel & A                           # qrels without the engine's unique contributions
        if sin_en:
            en_loro.append(len(rel & E & A) / len(sin_en))
    def pair(f, l):
        mf, ml = _mean(f), _mean(l)
        share = round(1 - ml / mf, 4) if mf and ml is not None else None
        return {"pool": round(mf, 4) if mf is not None else None,
                "loro": round(ml, 4) if ml is not None else None,
                "self_supplied": share}
    return {"agent": pair(ag_full, ag_loro), "engine_20": pair(en_full, en_loro),
            "n": len(ag_full)}


def _kappa_quadratic(pairs):
    """Cohen's kappa with quadratic weights over ordinal labels 0/1/2.
    Without weights, confusing 1 with 2 would cost the same as confusing 0 with
    2, and they are not the same: 'partial vs answers' is a disagreement of
    degree, 'not relevant vs answers' is an error."""
    if not pairs:
        return None
    cats = [0, 1, 2]
    n = len(pairs)
    obs = defaultdict(int)
    ma, mb = Counter(), Counter()
    for a, b in pairs:
        obs[(a, b)] += 1
        ma[a] += 1
        mb[b] += 1
    w = lambda i, j: ((i - j) ** 2) / ((len(cats) - 1) ** 2)
    num = sum(w(i, j) * obs.get((i, j), 0) for i in cats for j in cats)
    den = sum(w(i, j) * ma[i] * mb[j] / n for i in cats for j in cats)
    if not den:
        return 1.0
    return round(1 - num / den, 4)

# ------------------------------------------------------------------ metrics (dashboard contract)

def _judgments():
    """Relevance judgments, with explicit precedence.

    `.cache/judgments.jsonl` is the base (LLM judge, derived and regenerable) and
    `data/judgments.jsonl` OVERRIDES it: it is non-derived work, versioned, and
    where human judgments are written. It used to be the other way round —
    cache first with setdefault — and the effect was that a human judgment on a
    pair already labelled by the LLM changed nothing: it was saved and ignored.

    Within each file the LAST line for a (qid, rel) pair wins: correcting
    yourself means writing again, not deleting the previous line. History stays.
    """
    jud = {}
    for p in (JUDG_PATH, os.path.join(DATA, "judgments.jsonl")):
        if not os.path.exists(p):
            continue
        for l in open(p, encoding="utf-8"):
            if l.strip():
                j = json.loads(l)
                jud[(j["qid"], j["rel"])] = int(j["label"])
    return jud



# Layer 2 cache. Measuring a query is an act of the eval, not of the screen: the
# dashboard calls `metrics` on every refresh and has no reason to re-judge
# anything. The signature covers the inputs that can change the result — the
# pool, the judgments, the exclusions and the engine code — and nothing else.
# If one changes, the cache is discarded whole; otherwise it is read as is.
L2_CACHE = os.path.join(CACHE, "layer2_stats.json")


def _code_sig():
    """A change in the engine changes what is measured, even with the same
    inputs. Without this, touching a weight in `fuse()` would leave the
    dashboard showing the old measurement dressed as new — exactly the failure
    this cache could introduce."""
    import hashlib
    h = hashlib.sha1()
    for f in ("eval_retrieval.py", "rlib.py", "lsa.py", "bridge.py"):
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            h.update(open(p, "rb").read())
    return h.hexdigest()[:12]


def _read_pool(path=None):
    """Pool rows ALREADY without the excluded queries.

    It exists because of a real bug: filtering only in `load_gold()` removed the
    excluded query from the gold but `layer2` kept counting it, because layer2
    reads the pool, not the gold. Two doors into the same data with the
    exclusion applied at only one is an exclusion forgotten in half the figures.
    Here there is a single door.

    `pool.jsonl` keeps the row: it is filtered on read, the artifact is not amputated.
    """
    path = path or POOL_PATH
    if not os.path.exists(path):
        return []
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    ex = load_exclusions()
    if not ex:
        return rows
    keep = []
    for r in rows:
        e = ex.get(r["qid"])
        if e and (not e.get("fingerprint")
                  or e["fingerprint"] == _qfingerprint(r.get("query"))):
            continue
        keep.append(r)
    return keep


def _inputs_sig(pool_path):
    import hashlib
    h = hashlib.sha1()
    h.update(_code_sig().encode())
    for p in (pool_path, JUDG_PATH, os.path.join(DATA, "judgments.jsonl"), EXCL_PATH):
        if os.path.exists(p):
            h.update(os.path.basename(p).encode())
            h.update(open(p, "rb").read())
    return h.hexdigest()[:16]


def _l2_cache_read(sig, thr, pool_path):
    try:
        blob = json.load(open(L2_CACHE, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    e = blob.get("%s|%d|%s" % (sig, thr, os.path.basename(pool_path)))
    return e


def _l2_cache_write(sig, thr, pool_path, res):
    try:
        blob = json.load(open(L2_CACHE, encoding="utf-8"))
    except (OSError, ValueError):
        blob = {}
    # CAREFUL: do not filter by "current signature only". The base and extended
    # pools have different signatures (the signature includes pool content), so
    # that filter made each one delete the other's entry on every run and the
    # cache never hit. The last 8 entries are kept, that's all.
    key = "%s|%d|%s" % (sig, thr, os.path.basename(pool_path))
    blob.pop(key, None)
    blob[key] = res
    if len(blob) > 8:
        for k in list(blob)[:len(blob) - 8]:
            del blob[k]
    os.makedirs(CACHE, exist_ok=True)
    json.dump(blob, open(L2_CACHE, "w", encoding="utf-8"), ensure_ascii=False)


def _layer2_stats(thr, pool_path=None):
    """Pooled recall per system over the stored pool, plus the measures that
    tolerate incomplete judgments. Same as cmd_layer2 but returns the dict and
    accepts a relevance threshold (1 = partial counts, 2 = only 'answers the query').

    Completeness rule: a query only counts if its WHOLE pool is judged. Counting
    an unjudged candidate as not relevant would inflate the system that
    contributed it, which is the bias this module exists to measure, not repeat.
    """
    path = pool_path or POOL_PATH
    if not os.path.exists(path):
        return None
    sig = _inputs_sig(path)
    hit = _l2_cache_read(sig, thr, path)
    if hit is not None:
        return dict(hit, from_cache=True)
    pool = _read_pool(path)
    jud = _judgments()
    rA, pA, r10, r20, n_rel = [], [], [], [], []
    rB = []                                   # third system (raw bm25), if present
    r10p, r20p = [], []                       # engine on the agent's queries
    uniq = {"agent_only": 0, "engine_only": 0, "both": 0}
    rbp_ag, rbp_ag_res, rbp_en, rbp_en_res, bp_ag, bp_en = [], [], [], [], [], []
    per_q, judged, incomplete, falta = [], 0, 0, 0
    for p in pool:
        lab = {}
        for c in p["candidates"]:
            if c["used_by_agent"]:
                lab[c["rel"]] = 2
            elif (p["qid"], c["rel"]) in jud:
                lab[c["rel"]] = jud[(p["qid"], c["rel"])]
        if len(lab) < len(p["candidates"]):
            incomplete += 1
            falta += len(p["candidates"]) - len(lab)
            continue
        rel = {r for r, v in lab.items() if v >= thr}
        if not rel:
            continue
        judged += 1
        n_rel.append(len(rel))
        A, E = set(p["agent_returned"]), p["engine_ranked"]
        uniq["agent_only"] += len(rel & A - set(E))
        uniq["engine_only"] += len(rel & set(E) - A)
        uniq["both"] += len(rel & A & set(E))
        if A:
            rA.append(len(rel & A) / len(rel)); pA.append(len(rel & A) / len(A))
            s, res = _rbp(p["agent_returned"], lab); rbp_ag.append(s); rbp_ag_res.append(res)
            b = _bpref(p["agent_returned"], lab, rel)
            if b is not None:
                bp_ag.append(b)
        r10.append(len(rel & set(E[:10])) / len(rel)); r20.append(len(rel & set(E[:20])) / len(rel))
        if A:   # same query subset as the agent: the comparable pair
            r10p.append(len(rel & set(E[:10])) / len(rel))
            r20p.append(len(rel & set(E[:20])) / len(rel))
        s, res = _rbp(E[:20], lab); rbp_en.append(s); rbp_en_res.append(res)
        b = _bpref(E[:20], lab, rel)
        if b is not None:
            bp_en.append(b)
        bm = p.get("bm25_ranked")
        if bm:
            rB.append(len(rel & set(bm[:20])) / len(rel))
        per_q.append({"qid": p["qid"], "rel": rel, "A": A, "E20": set(E[:20]),
                      "recall_agent": round(len(rel & A) / len(rel), 4) if A else None,
                      # For the dashboard's per-query breakdown: the mean hides a
                      # wide real range. An aggregate figure that cannot be
                      # opened up has to be taken on faith.
                      "query": p.get("query", ""), "date": p.get("date", ""),
                      "n_rel": len(rel),
                      "n_returned": len(A),
                      "precision_agent": round(len(rel & A) / len(A), 4) if A else None,
                      "recall_engine_20": round(len(rel & set(E[:20])) / len(rel), 4)})
    avg = lambda v: round(sum(v) / len(v), 4) if v else None
    ci_lo, ci_hi = _bootstrap_ci(rA)
    res = {"agent_recall": avg(rA), "agent_precision": avg(pA), "n_agent": len(rA),
            "engine_r10": avg(r10), "engine_r20": avg(r20), "n_judged": judged,
            "engine_r10_paired": avg(r10p), "engine_r20_paired": avg(r20p),
            "incomplete": incomplete, "judgments_missing": falta,
            "rel_per_query": avg(n_rel), "uniq": uniq,
            "judgments": len(jud),
            "pool_depth": max((len(p["engine_ranked"]) for p in pool), default=0),
            "agent_recall_ci": [ci_lo, ci_hi],
            "agent_rbp": avg(rbp_ag), "agent_rbp_residual": avg(rbp_ag_res),
            "engine_rbp": avg(rbp_en), "engine_rbp_residual": avg(rbp_en_res),
            "agent_bpref": avg(bp_ag), "engine_bpref": avg(bp_en),
            "bm25_raw_r20": avg(rB), "n_bm25_raw": len(rB),
            "loro": _loro(per_q),
            "per_query": [{"qid": q["qid"], "recall_agent": q["recall_agent"]} for q in per_q],
            "rows": [{k: q[k] for k in ("qid", "date", "query", "recall_agent",
                                        "precision_agent", "recall_engine_20",
                                        "n_rel", "n_returned")} for q in per_q],
           "inputs_sig": sig}
    _l2_cache_write(sig, thr, path, res)
    return dict(res, from_cache=False)


# ------------------------------------------------------------------ history and paired gate
#
# With a handful of queries the CI of the mean is ~20pp wide: an absolute gate
# fires on noise in a sizeable share of runs. But the question that matters is
# not "what level is it at" but "has it dropped since the previous run", and
# that is answered PAIRED by query: between-query variance cancels out and the
# same small n becomes enough. That is why each run stores per-query detail.

RUNS_PATH = os.path.join(DATA, "runs.jsonl")

# --- engine provenance ---------------------------------------------------
# WHY. A recall run is a number about a specific engine. If the engine changes
# between two runs, the paired delta measures both things at once and there is
# no way to separate them afterwards. So every row carries the hash of the code
# that produced it and whether the tree was dirty when it ran, and `_paired`
# refuses to silently compare two runs from different engines.
#
# A dirty tree matters as much as the hash: a modified, uncommitted file means
# the hash belongs to something that exists in no revision, so the run is not
# reproducible even though the hash is recorded. (Without git, dirtiness is
# reported as unknown.)
ENGINE_FILES = ("eval_retrieval.py", "rlib.py", "embed.py", "lsa.py")


def _engine_fingerprint():
    import hashlib
    import subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    h = hashlib.sha256()
    present = []
    for name in ENGINE_FILES:
        fp = os.path.join(here, name)
        try:
            with open(fp, "rb") as fh:
                h.update(fh.read())
            present.append(name)
        except OSError:
            continue
    dirty = None
    try:
        r = subprocess.run(["git", "status", "--porcelain", "--", here],
                           cwd=here, capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            sucios = [l[3:] for l in r.stdout.splitlines()
                      if l.strip() and "__pycache__" not in l]
            dirty = sorted(sucios)
    except (OSError, subprocess.SubprocessError):
        dirty = None       # no git: unknown, which is NOT the same as clean
    return {"sha": h.hexdigest()[:12], "files": present,
            "dirty": dirty, "dirty_known": dirty is not None}


def _append_run(l2, tag=""):
    """A run = a deliberate measurement (`layer2`), not a dashboard refresh.
    Append-only, like the Retrieval Log: history is not rewritten."""
    import datetime
    if not l2 or not l2.get("per_query"):
        return None
    rec = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "tag": tag, "agent_recall": l2["agent_recall"], "n_agent": l2["n_agent"],
           "judgments": l2["judgments"], "pool_depth": l2["pool_depth"],
           "per_query": {q["qid"]: q["recall_agent"] for q in l2["per_query"]
                         if q["recall_agent"] is not None},
           "engine": _engine_fingerprint()}
    os.makedirs(DATA, exist_ok=True)
    with open(RUNS_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def _load_runs():
    if not os.path.exists(RUNS_PATH):
        return []
    return [json.loads(l) for l in open(RUNS_PATH, encoding="utf-8") if l.strip()]


def _paired(prev, cur):
    """Per-query paired delta between two runs + bootstrap CI on the delta and a
    sign test. Only queries present in both are compared: a new query is not an
    improvement."""
    qids = sorted(set(prev["per_query"]) & set(cur["per_query"]))
    if len(qids) < 2:
        return None
    # Engine warning: it does not block the comparison — sometimes the engine
    # change IS what you want to measure — but a delta between different engines
    # cannot be attributed to the corpus, and that sentence must travel with the
    # number.
    av = []
    pe, ce = prev.get("engine"), cur.get("engine")
    if not pe or not ce:
        av.append("one of the two runs did not record the engine version "
                  "(recorded before engine provenance existed): the delta is not attributable")
    elif pe.get("sha") != ce.get("sha"):
        av.append(f"the engine changed between the two runs ({pe.get('sha')} → "
                  f"{ce.get('sha')}): the delta measures corpus AND engine at once")
    for tag, e in (("previous", pe), ("current", ce)):
        if e and e.get("dirty"):
            av.append(f"the {tag} run was made with a dirty tree "
                      f"({len(e['dirty'])} uncommitted files): not reproducible")
        elif e and not e.get("dirty_known"):
            av.append(f"the {tag} run could not check whether the tree was clean")
    d = [cur["per_query"][q] - prev["per_query"][q] for q in qids]
    lo, hi = _bootstrap_ci(d)
    up = sum(1 for x in d if x > 0)
    down = sum(1 for x in d if x < 0)
    return {"n_paired": len(qids), "delta_mean": round(_mean(d), 4),
            "ci95": [lo, hi], "improve": up, "worsen": down,
            "tie": len(d) - up - down,
            "significant": bool(lo is not None and (lo > 0 or hi < 0)),
            "from": prev["at"], "to": cur["at"],
            "engine_previous": (pe or {}).get("sha"),
            "engine_current": (ce or {}).get("sha"),
            "engine_warnings": av,
            "comparable": not av,
            "by_query": {q: round(cur["per_query"][q] - prev["per_query"][q], 4)
                          for q in qids}}


def _paired_last():
    runs = _load_runs()
    return _paired(runs[-2], runs[-1]) if len(runs) >= 2 else None


def cmd_runs(_root):
    runs = _load_runs()
    out({"runs": [{k: v for k, v in r.items() if k != "per_query"} for r in runs],
         "paired_last_two": _paired_last()})


# ------------------------------------------------------------------ judge calibration

HUMAN_PATH = os.path.join(DATA, "human_judgments.jsonl")


def cmd_calibrate(_root, n):
    """Without a human anchor, the recall figure depends on an LLM's good faith.
    This draws a sample stratified by label (so it is not 30 zeros) and, when
    data/human_judgments.jsonl exists, returns the weighted kappa and the
    confusion matrix. The bias it looks for is systematic: a judge that calls 1
    what you call 0 inflates the denominator of every recall at once."""
    jud = _judgments()
    if not jud:
        sys.exit("No judgments to calibrate. Run: python3 eval_retrieval.py judge --file ...")
    human = {}
    if os.path.exists(HUMAN_PATH):
        for l in open(HUMAN_PATH, encoding="utf-8"):
            if l.strip():
                j = json.loads(l)
                human[(j["qid"], j["rel"])] = int(j["label"])
    if human:
        pairs = [(human[k], jud[k]) for k in human if k in jud]
        obs = Counter(pairs)
        acc = sum(1 for a, b in pairs if a == b) / len(pairs) if pairs else None
        out({"ok": True, "n_compared": len(pairs),
             "kappa_quadratic": _kappa_quadratic(pairs),
             "exact_agreement": round(acc, 4) if acc is not None else None,
             "matrix_human_x_llm": {"%d,%d" % k: v for k, v in sorted(obs.items())},
             "reading": "kappa >= 0.8 excellent · 0.6-0.8 substantial · < 0.6 the judge "
                        "is not a substitute and the number needs an asterisk"})
        return
    # No human labels yet: generate the stratified worksheet.
    rnd = random.Random(BOOT_SEED)
    by_label = defaultdict(list)
    for (qid, rel), lab in sorted(jud.items()):
        by_label[lab].append((qid, rel))
    per = max(1, n // max(1, len(by_label)))
    muestra = []
    for lab in sorted(by_label):
        pool_l = by_label[lab][:]
        rnd.shuffle(pool_l)
        muestra += [(q, r, lab) for q, r in pool_l[:per]]
    rnd.shuffle(muestra)
    path = os.path.join(CACHE, "calibration_worksheet.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Judge calibration — %d items\n\n" % len(muestra))
        fh.write("Label blind: **2** answers the query · **1** partially relevant · "
                 "**0** not relevant. The LLM's label is deliberately NOT shown.\n\n")
        fh.write("Write the result to `data/human_judgments.jsonl`, one line per item:\n"
                 "`{\"qid\": \"q22\", \"rel\": \"...\", \"label\": 1}`\n\n")
        qs = {}
        for p in (_read_pool()
                  if os.path.exists(POOL_PATH) else []):
            qs[p["qid"]] = p["query"]
        for qid, rel, _ in muestra:
            fh.write("- ( ) `%s`\n      query: %s\n      note: `%s`\n\n"
                     % (qid, qs.get(qid, "?")[:100], rel))
    out({"ok": True, "sample": len(muestra), "worksheet": path,
         "next": "label blind -> data/human_judgments.jsonl -> "
                      "python3 eval_retrieval.py calibrate"})


# ------------------------------------------------------------------ judgment budget

def cmd_plan(_root, budget):
    """For a FIXED judgment budget, many shallowly judged queries beat a few
    deeply judged ones (Carterette et al., Million Query Track). CI width goes
    with 1/sqrt(n_queries), not with depth, so going deeper buys pool ceiling
    but not statistical precision. This puts numbers on that trade-off using
    the variance measured today."""
    l2 = _layer2_stats(1)
    if not l2:
        sys.exit("The judged pool is missing.")
    import math
    vals = [q["recall_agent"] for q in l2["per_query"] if q["recall_agent"] is not None]
    if len(vals) < 2:
        sys.exit("At least 2 measured queries are needed.")
    m = _mean(vals)
    sd = (sum((x - m) ** 2 for x in vals) / (len(vals) - 1)) ** 0.5
    # judgments per query ~ unique pool candidates at that depth, measured today
    pool = _read_pool()
    cands = _mean([len(p["candidates"]) for p in pool]) or 1
    depth_hoy = l2["pool_depth"] or 20
    filas = []
    for depth in (5, 7, 10, 15, 20):
        por_q = max(1.0, cands * (depth / depth_hoy))
        nq = int(budget / por_q)
        if nq < 2:
            continue
        half = 1.96 * sd / math.sqrt(nq)
        filas.append({"depth": depth, "queries": nq,
                      "judgments_per_query": round(por_q, 1),
                      "ci95_mean": ("+-%.1f pp" % (half * 100)),
                      "detectable_paired_delta": ("~%.1f pp" % (half * 100 / math.sqrt(2)))})
    out({"judgment_budget": budget,
         "today": {"queries": l2["n_agent"], "depth": depth_hoy,
                 "judgments": l2["judgments"],
                 "sd_between_queries": round(sd, 4),
                 "ci95": l2["agent_recall_ci"]},
         "options": filas,
         "reading": "CI width is set by the number of queries, not by depth. "
                    "Going deeper raises the pool ceiling and reusability; adding "
                    "queries raises statistical power. They are two different purchases."})



def _pool_in_use():
    """The extended pool (3 systems) takes over as soon as it is fully judged;
    until then the dashboard stays on the 2-system one. Automatic promotion with
    no broken window: there is never a moment when the live number comes from a
    half-judged pool."""
    if os.path.exists(EXT_PATH):
        st = _layer2_stats(1, EXT_PATH)
        if st and not st["incomplete"]:
            return EXT_PATH, "extended (3 systems)"
        falta = st["judgments_missing"] if st else 0
        return POOL_PATH, "base (2 systems) · extension pending %d judgments" % falta
    return POOL_PATH, "base (2 systems)"



L1_CACHE = os.path.join(CACHE, "layer1_stats.json")


def _layer1_sig(root):
    import hashlib
    h = hashlib.sha1()
    h.update(_code_sig().encode())
    for p in (IX_PATH, GOLD_PATH, EXP_PATH, EXCL_PATH,
              os.path.join(root, "autolink", "graph.jsonl")):
        if os.path.exists(p):
            st = os.stat(p)
            h.update(("%s|%d|%d" % (os.path.basename(p), st.st_size, int(st.st_mtime))).encode())
    return h.hexdigest()[:16]


def _layer1_cached(root):
    """Same as compute_layer1 but does not re-measure if nothing relevant has
    changed. The signature covers index + gold + expansions + graph + code;
    mtimes are enough because these artifacts are regenerated whole, never edited."""
    sig = _layer1_sig(root)
    try:
        blob = json.load(open(L1_CACHE, encoding="utf-8"))
    except (OSError, ValueError):
        blob = {}
    if not isinstance(blob, dict) or "sig" in blob:      # old single-entry format
        blob = {}
    if sig in blob:
        return blob[sig]["summary"], blob[sig]["per_query"]
    l1, per_q = compute_layer1(root, [10, 20, 50], expanded=True)
    # Several entries on purpose: the real eval flow is measure A, change the
    # engine, measure B and go back to A to compare. With a single entry, every
    # step back costs a re-measurement and discourages exactly what you should do.
    blob[sig] = {"summary": l1, "per_query": per_q}
    if len(blob) > 4:
        for k in list(blob)[:len(blob) - 4]:
            del blob[k]
    os.makedirs(CACHE, exist_ok=True)
    json.dump(blob, open(L1_CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    return l1, per_q




def _vocab_faltante(ix, g_gold, query_text, ranked, n=6):
    """The terms that would have found what the query did not find.

    DO NOT READ THIS AS A PREDICTION: it comes from the gold notes that were
    missed, so it is an AFTER-THE-FACT diagnosis. The system could not have
    known it beforehand; the vault owner could, because they are their notes.
    That is why it lives in the review table and not in retrieve: it helps you
    learn which vocabulary you are not using, not expand the query automatically.

    In the original validation, adding these terms raised mean recall@50
    substantially on the queries with gold that received a suggestion.
    """
    import math
    perdidas = [r for r in g_gold if r not in set(ranked)]
    if not perdidas:
        return []
    qt = set(rlib.tokenize(clean_query(query_text)))
    N = len(ix.docs)
    sc, veces = {}, {}
    for rel in perdidas:
        i = ix.by_rel.get(rel)
        if i is None:
            continue
        for t in set(rlib.tokenize(ix.docs[i]["title"])):
            # Out: what the query already said, very short tokens, LN prefix codes
            # (e.g. ABCD, XYZ18) and terms too common or too rare to teach anything.
            if t in qt or len(t) < 5 or any(c.isdigit() for c in t):
                continue
            df = ix.df.get(t, 1)
            if df < 2 or df > N * 0.03:
                continue
            sc[t] = sc.get(t, 0) + math.log(N / df)
            veces[t] = veces.get(t, 0) + 1
    # A term that appears in SEVERAL missed notes is topic vocabulary; one that
    # appears in a single one may be a stray word from that title.
    orden = sorted(sc.items(), key=lambda x: (-veces.get(x[0], 0), -x[1], x[0]))
    return [t for t, _ in orden[:n]]


ROWS_CACHE = os.path.join(CACHE, "query_rows.json")


def _all_query_rows_cached(root, l2):
    """Same treatment as the two layers: the per-query breakdown is a
    measurement, not a render. It takes a few seconds because it re-ranks every
    query with gold to learn what was missed; the signature is Layer 1's (index,
    gold, expansions, graph, code) plus Layer 2's (pool and judgments) plus the
    Retrieval Log itself."""
    # The Retrieval Log is part of the signature, and that is a fix. The
    # signature used to be Layer 1 + Layer 2 — the inputs of the MEASUREMENT,
    # but not the input of the LIST: one row per log entry. Adding a search to
    # the log moved none of those signatures, so the breakdown froze at the
    # entries present the day it was cached, and the dashboard showed one query
    # fewer than the log had. A cache whose signature does not include its own
    # input is not a cache: it is an old copy with today's date.
    _log = os.path.join(root, "Resources", "Retrieval Log.md")
    _log_sig = "-"
    if os.path.exists(_log):
        _st = os.stat(_log)
        _log_sig = "%d|%d" % (_st.st_size, int(_st.st_mtime))
    sig = "%s|%s|%s" % (_layer1_sig(root), (l2 or {}).get("inputs_sig", "-"), _log_sig)
    try:
        blob = json.load(open(ROWS_CACHE, encoding="utf-8"))
        if blob.get("sig") == sig:
            return blob["rows"]
    except (OSError, ValueError, KeyError):
        pass
    rows = _all_query_rows(root, l2)
    os.makedirs(CACHE, exist_ok=True)
    json.dump({"sig": sig, "rows": rows}, open(ROWS_CACHE, "w", encoding="utf-8"),
              ensure_ascii=False)
    return rows


def _all_query_rows(root, l2):
    """One row for EVERY Retrieval Log entry, not only the pooled ones.

    The dashboard breakdown used to show only the few queries with pooled recall
    out of a much larger log; quoting the few without saying out of how many
    turns a sample into a census. Each row carries the measurement that applies
    and, if there is none, WHY — which is the information that decides whether
    it is worth judging more pool or fixing how the log is written.

    Three measurement levels, strongest to weakest:
      pooled  — recall against the judged pool (denominator: relevant in pool)
      log     — recall@k against the notes the user used (denominator: recorded use)
      ninguna — none, with the reason
    """
    try:
        l1s, l1p = _layer1_cached(root)
    except SystemExit:
        l1p = []
    l1 = {r["qid"]: r for r in l1p}
    ix = load_ix()
    nb, tbs = rlib.load_graph(root)
    exp = load_expansions()
    goldmap = {r["qid"]: r for r in load_gold()}
    excl = load_exclusions()
    pooled = {r["qid"]: r for r in (l2 or {}).get("rows", [])}
    rows = []
    for i, e in enumerate(rlib.parse_log(root)):
        if not e.get("query"):
            continue
        qid = "q%02d" % i
        p, a = pooled.get(qid), l1.get(qid)
        # An excluded query is not removed from the table: it is marked.
        # Disappearing without a trace is how you lose count of what was taken
        # out of the denominator -- and with it the chance to argue about it.
        exq = excl.get(qid)
        if exq and (not exq.get("fingerprint")
                    or exq["fingerprint"] == _qfingerprint(e["query"])):
            rows.append({
                "qid": qid, "date": e.get("date", ""), "query": e["query"],
                "level": "excluida", "recall": None, "denominator": None,
                "recall_pooled": None, "precision_agent": None, "recall_engine_20": None,
                "recall_log_10": None, "recall_log_50": None, "first_hit": None,
                "n_returned": None, "outcome": e.get("outcome", ""),
                "reason": exq.get("reason", ""), "no_returned": not e["returned"],
                "missing_vocab": [],
            })
            continue
        if p and p.get("recall_agent") is not None:
            nivel, recall, den = "pooled", p["recall_agent"], p.get("n_rel")
        elif a:
            nivel, recall, den = "log", a.get("recall50"), a.get("n_gold")
        else:
            nivel, recall, den = "ninguna", None, None
        # The reason only makes sense when there is NO measurement. Putting it on
        # measurements against recorded use made a row with 100% recall carry
        # "outside the judged pool" next to it, which reads as a failure and is
        # not: it is measured, with another denominator.
        # Vocabulary that would have helped: only for queries with gold, the only
        # ones where WHAT was missed is known.
        vocab = []
        gg = goldmap.get(qid)
        if gg and gg.get("gold"):
            qtext = e["query"] + "  " + exp.get(qid, "")
            ranked = fuse(channels(ix, nb, tbs, qtext, depth=100, root=root),
                          k=50, prior=note_prior(root, ix))
            vocab = _vocab_faltante(ix, gg["gold"], qtext, ranked)
        # Incomplete entry: the log did not record `Notas devueltas`. It is not a
        # decision (that is `exclude`), it is a recording defect — and it is
        # detected by itself, with no list to maintain: the day the entry is
        # completed, it stops being incomplete.
        #
        # NOTHING about the agent can be computed without knowing what it
        # returned: neither pooled recall nor precision. Layer 1 can, because the
        # USED notes are recorded, and there the measurement is fully valid. So
        # this flags the row for the dashboard to hide, and does not drop it from
        # Layer 1: skipping them there too would cost a large share of the
        # queries with gold.
        sin_dev = not e["returned"]
        # An entry opened by `log_entry.py` and not yet closed has its own level.
        # Without it, it fell into "ninguna" with the reason "no used notes
        # recorded", which is the reason for a hand-written entry missing a
        # field -- and the dashboard hid it. They are two different things:
        # there the data is missing, here the data that matters is present (the
        # query was made, at this time) and the close is missing. Hiding it would
        # erase the only proof that a retrieval started and was not recorded.
        if e.get("state") == "abierta":
            nivel = "abierta"
            rows.append({
                "qid": qid, "date": e.get("date", ""), "query": e["query"],
                "level": nivel, "recall": None, "denominator": None,
                "recall_pooled": None, "precision_agent": None, "recall_engine_20": None,
                "recall_log_10": None, "recall_log_50": None, "first_hit": None,
                "n_returned": None, "outcome": e.get("outcome", ""),
                "reason": "recorded at the start; the retrieval was never closed",
                "no_returned": False, "missing_vocab": [],
            })
            continue
        motivo = ""
        if sin_dev and nivel != "ninguna":
            motivo = ("the log did not record Notas devueltas: without knowing what the "
                      "agent returned there is no agent recall or precision to compute")
        if nivel == "ninguna":
            if e.get("returned_is_prose"):
                motivo = "returned notes written as prose: no list to measure"
            elif not (a and a.get("n_gold")):
                motivo = "no used notes recorded: nothing to measure against"
            else:
                motivo = "in the judged pool but with no returned list"
        rows.append({
            "qid": qid, "date": e.get("date", ""), "query": e["query"],
            "level": nivel, "recall": recall, "denominator": den,
            "recall_pooled": p.get("recall_agent") if p else None,
            "precision_agent": p.get("precision_agent") if p else None,
            "recall_engine_20": p.get("recall_engine_20") if p else None,
            "recall_log_10": a.get("recall10") if a else None,
            "recall_log_50": a.get("recall50") if a else None,
            "first_hit": a.get("first_rank") if a else None,
            "n_returned": p.get("n_returned") if p else None,
            "outcome": e.get("outcome", ""), "reason": motivo,
            "no_returned": sin_dev,
            "missing_vocab": vocab,
        })
    rows.sort(key=lambda r: (r["date"], r["qid"]), reverse=True)
    return rows



# ------------------------------------------------------------------ exclusions

def cmd_exclude(root, qid, reason):
    """Removes a log entry from ALL metrics, without touching the log.

    The Retrieval Log is append-only and this engine does not write to the
    vault: the exclusion lives in `data/exclusions.jsonl`, which is non-derived
    work versioned alongside the judgments. Deleting the log entry would lose
    the traceability of a session that existed.

    The reason is MANDATORY. Excluding without a written reason is
    indistinguishable from removing from the denominator whatever went wrong,
    which is the cheap way to raise any metric; with a reason, the decision
    stays auditable next to the number.
    """
    reason = (reason or "").strip()
    if not reason:
        out({"ok": False, "error": "--reason is required: an exclusion without a written "
                                   "reason is indistinguishable from dressing up the figure"})
        return
    rows = {r["qid"]: r for r in _all_gold_rows()}
    r = rows.get(qid)
    if not r:
        out({"ok": False, "error": "%s does not exist in the gold set" % qid,
             "fix": "python3 eval_retrieval.py gold"})
        return
    import datetime
    rec = {"qid": qid, "excluded": True, "reason": reason,
           "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "fingerprint": _qfingerprint(r.get("query")),
           "date": r.get("date", ""), "query": (r.get("query") or "")[:160]}
    os.makedirs(DATA, exist_ok=True)
    with open(EXCL_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    ex = load_exclusions()
    out({"ok": True, "excluded": qid, "reason": reason, "excluded_now": len(ex),
         "next": "layer2 and metrics now ignore it; the dashboard recomputes by itself"})


def cmd_include(root, qid):
    """Undoes an exclusion. Append-only: writes the re-inclusion mark, does not
    delete the previous line. The history of it being out, and why, is kept."""
    if qid not in load_exclusions():
        out({"ok": False, "error": "%s is not excluded" % qid})
        return
    import datetime
    rec = {"qid": qid, "excluded": False,
           "at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    with open(EXCL_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    out({"ok": True, "reinstated": qid, "excluded_now": len(load_exclusions())})


def cmd_exclusions(root):
    """What is outside the measurement, why, and since when. Orphans -- a
    fingerprint that no longer matches that qid's query -- are listed apart and
    are NOT being applied."""
    ex = load_exclusions()
    rows = {r["qid"]: r for r in _all_gold_rows()}
    activas, huerfanas = [], []
    for qid, e in sorted(ex.items()):
        g = rows.get(qid)
        item = {"qid": qid, "date": e.get("date") or (g or {}).get("date", ""),
                "reason": e.get("reason", ""), "at": e.get("at", ""),
                "query": (e.get("query") or (g or {}).get("query", ""))[:120]}
        fp = e.get("fingerprint")
        if not g:
            item["problem"] = "the qid no longer exists in the gold set"
            huerfanas.append(item)
        elif fp and fp != _qfingerprint(g.get("query")):
            item["problem"] = "the query at that qid has changed: the exclusion is NOT applied"
            huerfanas.append(item)
        else:
            activas.append(item)
    out({"ok": True, "excluded": len(activas), "active": activas,
         "orphans": huerfanas, "file": EXCL_PATH})


def _all_gold_rows():
    if not os.path.exists(GOLD_PATH):
        sys.exit("The gold set is missing. Run: python3 eval_retrieval.py gold "
                 "(it is built from your Resources/Retrieval Log.md)")
    return [json.loads(l) for l in open(GOLD_PATH, encoding="utf-8") if l.strip()]


# ------------------------------------------------------------------ manual judging

def cmd_judge_list(root, qid):
    """Candidates of a pooled query with their current label, for judging by
    hand. Those the agent USED come back locked: they are worth 2 by definition
    and leaving them editable would invite faking the number from the UI."""
    path, _ = _pool_in_use()
    if not os.path.exists(path):
        out({"ok": False, "error": "no pool", "fix": "python3 eval_retrieval.py pool"})
        return 1
    ix = load_ix()
    jud = _judgments()
    for p in (json.loads(l) for l in open(path, encoding="utf-8") if l.strip()):
        if p["qid"] != qid:
            continue
        cands = []
        for c in p["candidates"]:
            i = ix.by_rel.get(c["rel"])
            d = ix.docs[i] if i is not None else {}
            cands.append({
                "rel": c["rel"], "title": c.get("title") or d.get("title", c["rel"]),
                "folder": d.get("folder", ""), "sources": c.get("sources", []),
                "rank_agent": c.get("rank_agent"), "rank_engine": c.get("rank_mine"),
                "used_by_agent": bool(c.get("used_by_agent")),
                "label": 2 if c.get("used_by_agent") else jud.get((qid, c["rel"])),
                "locked": bool(c.get("used_by_agent")),
            })
        cands.sort(key=lambda c: (c["rank_agent"] is None, c["rank_agent"] or 0,
                                  c["rank_engine"] or 999))
        out({"ok": True, "qid": qid, "query": p["query"], "candidates": cands,
             "unjudged": sum(1 for c in cands if c["label"] is None)})
        return 0
    out({"ok": False, "error": "query %s is not in the judged pool" % qid,
         "fix": 'python3 eval_retrieval.py pool --qids %s' % qid})
    return 1


def cmd_judge_set(root, qid, rel, label):
    """One judgment, written where human work lives: data/judgments.jsonl, which
    is NOT derived and is versioned. Append-only; the last line for a (qid, rel)
    pair wins, so correcting yourself leaves a trace instead of deleting the
    previous judgment."""
    if label not in (0, 1, 2):
        out({"ok": False, "error": "label must be 0, 1 or 2"})
        return 1
    import datetime
    os.makedirs(DATA, exist_ok=True)
    dst = os.path.join(DATA, "judgments.jsonl")
    with open(dst, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"qid": qid, "rel": rel, "label": label,
                             "by": "human", "at": datetime.datetime.now(
                                 datetime.timezone.utc).isoformat()},
                            ensure_ascii=False) + "\n")
    # The caches depend on the judgments: they are invalidated together so the
    # dashboard does not keep showing the recall from before the judgment just made.
    for p in (L2_CACHE, ROWS_CACHE):
        try:
            os.remove(p)
        except OSError:
            pass
    st = _layer2_stats(1)
    out({"ok": True, "qid": qid, "rel": rel, "label": label,
         "recall_agent": st["agent_recall"] if st else None,
         "n_queries": st["n_agent"] if st else 0,
         "judgments": st["judgments"] if st else 0})
    return 0


def cmd_metrics(root):
    """Flat output for `Meta/metrics.json` (kind: engine, pick: <key>). The
    dashboard computes nothing: it takes the key the contract tells it to.
    Recomputes Layer 1 (a few seconds, cached) and reads Layer 2 from the stored
    judgments; if something is missing it returns null for that key and goes
    on, so one metric without data does not take down the others."""
    import datetime
    import time
    res = {"schema": "retrieval-eval-metrics/1",
           "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "vault": root}
    # Layer 2
    pool_path, pool_label = _pool_in_use()
    l2 = _layer2_stats(1, pool_path) if os.path.exists(pool_path) else None
    l2s = _layer2_stats(2, pool_path) if l2 else None
    res["pool_in_use"] = pool_label
    # Measurement basis: two Layer 2 figures can only be subtracted if they come
    # from the SAME pool at the SAME depth. Once, a small pool at depth 20 and a
    # large pool at depth 5 were compared and the dashboard announced a huge
    # "improvement" nobody had measured. With the basis shown alongside, whoever
    # compares can refuse. This engine does not interpret it: it publishes it.
    res["basis"] = ("pool %dq · depth %d" % (l2["n_judged"], l2["pool_depth"])) if l2 else None
    res["measurement_cached"] = bool(l2 and l2.get("from_cache"))
    res["inputs_sig"] = l2.get("inputs_sig") if l2 else None
    fmt_pct = lambda v: ("%.1f %%" % (v * 100)) if v is not None else "—"
    if l2:
        u = l2["uniq"]
        res.update({
            "agent_recall_pooled": l2["agent_recall"], "agent_precision": l2["agent_precision"],
            "agent_recall_pooled_strict": l2s["agent_recall"], "agent_precision_strict": l2s["agent_precision"],
            "n_queries_agent": l2["n_agent"], "n_queries_judged": l2["n_judged"], "judgments": l2["judgments"],
            "pool_depth": l2["pool_depth"], "relevant_per_query": l2["rel_per_query"],
            "engine_recall_at_10": l2["engine_r10"], "engine_recall_at_20": l2["engine_r20"],
            "disjunction_agent_only": u["agent_only"], "disjunction_engine_only": u["engine_only"],
            "disjunction_both": u["both"],
            # "mean per query" is not decoration: with a precision gate near the
            # macro average, the micro average (over all returned notes) can land
            # on the other side and the traffic light changes colour. A figure
            # read against a threshold must say how it was averaged, or the
            # threshold means nothing.
            "agent_detail": "%s recall · %s precision · mean per query · n=%d queries with a list · pool depth %d · strict threshold: %s / %s" % (
                fmt_pct(l2["agent_recall"]), fmt_pct(l2["agent_precision"]), l2["n_agent"], l2["pool_depth"],
                fmt_pct(l2s["agent_recall"]), fmt_pct(l2s["agent_precision"])),
            "precision_detail": "%s of what was returned is relevant (partial counts) · %s requiring it to answer the query · mean per query · n=%d" % (
                fmt_pct(l2["agent_precision"]), fmt_pct(l2s["agent_precision"]), l2["n_agent"]),
            "disjunction_detail": "%d agent only · %d engine only · %d both (%d queries judged, %d judgments)" % (
                u["agent_only"], u["engine_only"], u["both"], l2["n_judged"], l2["judgments"]),
        })
        # Measures that tolerate an incomplete 2-system pool. They go to the
        # dashboard because bare recall claims more than this data supports.
        ci = l2["agent_recall_ci"]
        lo = l2["loro"]
        res.update({
            "agent_recall_ci_low": ci[0], "agent_recall_ci_high": ci[1],
            "agent_rbp": l2["agent_rbp"], "agent_rbp_residual": l2["agent_rbp_residual"],
            "engine_rbp": l2["engine_rbp"], "engine_rbp_residual": l2["engine_rbp_residual"],
            "agent_bpref": l2["agent_bpref"], "engine_bpref": l2["engine_bpref"],
            "pool_selfsupplied_agent": lo["agent"]["self_supplied"],
            "pool_selfsupplied_engine": lo["engine_20"]["self_supplied"],
            "agent_recall_loro": lo["agent"]["loro"],
            "engine_recall_loro": lo["engine_20"]["loro"],
            "bm25_raw_r20": l2["bm25_raw_r20"], "pool_systems": 3 if l2["n_bm25_raw"] else 2,
            # Per-query breakdown: what is behind the mean. The dashboard renders it
            # in a collapsible table; without it, a small-n mean cannot be audited.
            "agent_query_rows": _all_query_rows_cached(root, l2),
            "engine_recall_at_10_paired": l2["engine_r10_paired"],
            "engine_recall_at_20_paired": l2["engine_r20_paired"],
            "n_queries_loro": l2["loro"]["n"],
            "ci_detail": "95%% CI [%s – %s] by bootstrap over n=%d queries · "
                         "width %s pp: the level cannot distinguish changes smaller than that" % (
                fmt_pct(ci[0]), fmt_pct(ci[1]), l2["n_agent"],
                ("%.1f" % ((ci[1] - ci[0]) * 100)) if ci[0] is not None else "—"),
            "loro_detail": "leave-one-run-out: agent %s → %s · engine@20 %s → %s. "
                           "%s %% of the agent's recall is propped up by its own contribution "
                           "to the pool (%d contributing systems, depth %d)" % (
                fmt_pct(lo["agent"]["pool"]), fmt_pct(lo["agent"]["loro"]),
                fmt_pct(lo["engine_20"]["pool"]), fmt_pct(lo["engine_20"]["loro"]),
                ("%.0f" % ((lo["agent"]["self_supplied"] or 0) * 100)),
                3 if l2["n_bm25_raw"] else 2, l2["pool_depth"]),
            "rbp_detail": "RBP(0.8) agent %s with residual %s · engine %s with residual %s. "
                          "The residual is what is unknown because nothing deeper was judged" % (
                fmt_pct(l2["agent_rbp"]), fmt_pct(l2["agent_rbp_residual"]),
                fmt_pct(l2["engine_rbp"]), fmt_pct(l2["engine_rbp_residual"])),
        })
        pr = _paired_last()
        if pr:
            res.update({
                # In percentage points, the unit the dashboard expects for
                # format delta_pp (same convention as graph.hop_delta).
                "agent_recall_delta_paired": round(pr["delta_mean"] * 100, 2),
                "paired_detail": "%s pp paired over %d queries · 95%% CI [%s – %s] · "
                                 "%d improve / %d worsen / %d tie%s" % (
                    ("%+.1f" % (pr["delta_mean"] * 100)), pr["n_paired"],
                    fmt_pct(pr["ci95"][0]), fmt_pct(pr["ci95"][1]),
                    pr["improve"], pr["worsen"], pr["tie"],
                    "" if pr["significant"] else " · the CI crosses zero: inconclusive"),
            })
        else:
            res.update({"agent_recall_delta_paired": None,
                        "paired_detail": "only one run in the history: the paired delta "
                                         "appears with the second (`layer2` records it)"})
    else:
        res.update({k: None for k in ("agent_recall_pooled", "agent_precision", "disjunction_engine_only")})
        res["agent_detail"] = "no judged pool: python3 eval_retrieval.py pool / judge"
    # Layer 1 (deterministic prefilter). It is the expensive part of the
    # command: one full retrieval per query with gold. Caching it like Layer 2
    # makes a dashboard refresh cost a disk read, not a re-measurement.
    try:
        l1, per_q = _layer1_cached(root)
        res.update({
            "prefilter_recall_at_10": l1["recall"]["recall@10"], "prefilter_recall_at_20": l1["recall"]["recall@20"],
            "prefilter_recall_at_50": l1["recall"]["recall@50"], "prefilter_mrr": l1["mrr"],
            "prefilter_queries_zero": l1["queries_without_any_gold_retrieved"], "gold_queries": l1["n_queries"],
            "prefilter_detail": "recall@10 %s · @20 %s · @50 %s · MRR %.3f · %d/%d queries with no gold in top-100" % (
                fmt_pct(l1["recall"]["recall@10"]), fmt_pct(l1["recall"]["recall@20"]), fmt_pct(l1["recall"]["recall@50"]),
                l1["mrr"], l1["queries_without_any_gold_retrieved"], l1["n_queries"]),
        })
    except SystemExit as e:
        res.update({"prefilter_recall_at_50": None, "prefilter_detail": str(e)})
    # Health of the log as an instrument. The denominator is the entries THAT
    # COUNT: measuring the parseability of an entry you decided not to measure
    # counts a defect that is not one. Excluded entries are reported apart, never
    # silenced.
    entries = rlib.parse_log(root)
    excl = load_exclusions()
    with_q_all, with_q = [], []
    for i, e in enumerate(entries):
        if not e["query"]:
            continue
        with_q_all.append(e)
        ex = excl.get("q%02d" % i)
        if ex and (not ex.get("fingerprint")
                   or ex["fingerprint"] == _qfingerprint(e["query"])):
            continue
        with_q.append(e)
    parseable = sum(1 for e in with_q if e["returned"])
    missing = sum(1 for e in with_q if e.get("missing"))
    n_excl = len(with_q_all) - len(with_q)
    res.update({
        "log_entries": len(with_q),
        "log_entries_total": len(with_q_all),
        "excluded_queries": n_excl,
        "excluded_detail": ("%d of %d entries outside the measurement by written decision" %
                            (n_excl, len(with_q_all))) if n_excl else "no entries excluded",
        "excluded_rows": [
            {"qid": q, "date": x.get("date", ""), "reason": x.get("reason", ""),
             "at": x.get("at", ""), "query": (x.get("query") or "")[:120]}
            for q, x in sorted(excl.items())
        ],
        "log_returned_parseable": round(parseable / len(with_q), 4) if with_q else None,
        "log_missing_populated": missing,
        "log_detail": "%d/%d entries with a parseable returned list · %d with missing: populated (Level B)%s" % (
            parseable, len(with_q), missing,
            " · %d excluded" % n_excl if n_excl else ""),
    })
    if os.path.exists(IX_PATH):
        res["index_age_days"] = round((time.time() - os.path.getmtime(IX_PATH)) / 86400, 1)
    out(res)


# ------------------------------------------------------------------ reanalysis audits
# Three marginal-cost audits that do not change the engine: expansion-audit
# (prediction P1), hop-loso (checks that `sessions` in graph.jsonl reproduces the
# leave-one-session-out hop recall without hand-joining co-usage.jsonl) and
# prf-audit (prediction P2).

def _pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx, my = _mean(xs), _mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return 0.0
    import math
    return round(cov / math.sqrt(vx * vy), 4)


def _bootstrap_corr_ci(xs, ys, alpha=0.05, n=BOOT_N, seed=BOOT_SEED):
    if len(xs) < 3:
        return (None, None)
    rnd = random.Random(seed)
    m = len(xs)
    idx = list(range(m))
    boots = []
    for _ in range(n):
        samp = [rnd.choice(idx) for _ in range(m)]
        r = _pearson([xs[i] for i in samp], [ys[i] for i in samp])
        if r is not None:
            boots.append(r)
    if not boots:
        return (None, None)
    boots.sort()
    lo = boots[int((alpha / 2) * len(boots))]
    hi = boots[min(len(boots) - 1, int((1 - alpha / 2) * len(boots)))]
    return (round(lo, 4), round(hi, 4))


def cmd_expansion_audit(_root):
    """Correlation between the number of terms in each stored LLM expansion and
    the number of distinct gold notes of its query. Prediction P1: r < 0.15
    (Ammann et al. 2025 predict r ≈ -0.02 if the expansion is a fixed-N-terms
    template disguised as decomposition). If it holds: expansion is lexical
    coverage, not semantic decomposition, and the skill's expansion step should
    ask for "one term per distinct concept" instead of a fixed number of terms."""
    exp = {}
    if os.path.exists(EXP_PATH):
        exp = {j["qid"]: j["expansion"] for j in
               (json.loads(l) for l in open(EXP_PATH, encoding="utf-8") if l.strip())}
    gold_by_qid = {r["qid"]: r for r in load_gold()}
    xs, ys, rows = [], [], []
    for qid, text in sorted(exp.items()):
        g = gold_by_qid.get(qid)
        if not g or not g["gold"]:
            continue
        n_terms = len(text.split())
        n_gold = len(set(g["gold"]))
        xs.append(n_terms); ys.append(n_gold)
        rows.append({"qid": qid, "n_terms": n_terms, "n_gold_distinct": n_gold})
    r = _pearson(xs, ys)
    lo, hi = _bootstrap_corr_ci(xs, ys)
    res = {"n": len(rows), "pearson_r": r, "ci95": [lo, hi],
           "prediction_P1": "r < 0.15", "holds": bool(r is not None and r < 0.15),
           "detail": rows}
    json.dump(res, open(os.path.join(CACHE, "expansion_audit.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    out({k: v for k, v in res.items() if k != "detail"})


def _load_graph_raw(root):
    p = os.path.join(root, "autolink", "graph.jsonl")
    if not os.path.exists(p):
        sys.exit("autolink/graph.jsonl not found: hop-loso needs the autolink graph.")
    edges = []
    for line in open(p, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if line:
            try:
                edges.append(json.loads(line))
            except ValueError:
                continue
    return edges


def _build_nb(edges, mode, date=None):
    """mode: full (all edges), no_cousage (without co_usada), loso (a co_usada edge
    only counts if it has evidence from a session OTHER than `date` -- without
    this, LOSO requires hand-joining graph.jsonl with co-usage.jsonl)."""
    nb = defaultdict(set)
    tbs = {}
    for e in edges:
        f, t = e.get("from"), e.get("to")
        if not f or not t:
            continue
        if e.get("from_title"):
            tbs[f] = e["from_title"]
        if e.get("to_title"):
            tbs[t] = e["to_title"]
        if e.get("type") == "co_usada":
            if mode == "no_cousage":
                continue
            if mode == "loso":
                sessions = e.get("sessions")
                if sessions is None:
                    pass  # no backfill: treated as pre-existing evidence
                elif not (set(sessions) - {date}):
                    continue  # the only evidence is the session being left out
        nb[f].add(t)
        nb[t].add(f)
    return nb, tbs


def cmd_hop_loso(root, reference_loso=None, tolerance=0.03):
    """Hop-channel recall@50 with all edges / leave-one-session-out / without
    co-use edges, using `sessions` directly from graph.jsonl -- no hand-joining
    of co-usage.jsonl. The query is the EXPANDED one (LLM, load_expansions),
    the same basis as the layer-1 measurement, so it compares like with like.

    Prediction P5 (optional): pass --reference-loso with a LOSO value you
    measured earlier; the command checks it is reproduced within --tolerance.
    Without a reference, it just reports the three numbers."""
    ix = load_ix()
    rows = [r for r in load_gold() if r["gold"]]
    edges = _load_graph_raw(root)
    exp = load_expansions()

    def qtext_of(r):
        return r["query"] + ("  " + exp.get(r["qid"], "") if exp else "")

    def hop_recall(nb, tbs, per_date=False):
        vals = []
        for r in rows:
            use_nb, use_tbs = (nb, tbs) if not per_date else _build_nb(edges, "loso", r["date"])
            ch = channels(ix, use_nb, use_tbs, qtext_of(r), depth=100, root=root)
            gold = set(r["gold"])
            vals.append(len(set(ch["hop"][:50]) & gold) / len(gold))
        return vals

    nb_full, tbs_full = _build_nb(edges, "full")
    vals_full = hop_recall(nb_full, tbs_full)
    nb_no, tbs_no = _build_nb(edges, "no_cousage")
    vals_no = hop_recall(nb_no, tbs_no)
    vals_loso = hop_recall(None, None, per_date=True)

    res = {"n_queries": len(rows),
           "hop_recall50_all_edges": round(_mean(vals_full), 4),
           "hop_recall50_LOSO": round(_mean(vals_loso), 4),
           "hop_recall50_without_cousage": round(_mean(vals_no), 4)}
    if reference_loso is not None:
        res["prediction_P5"] = "%.3f +/- %.3f" % (reference_loso, tolerance)
        res["holds"] = abs(_mean(vals_loso) - reference_loso) <= tolerance
    json.dump(res, open(os.path.join(CACHE, "hop_loso.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    out(res)


def cmd_prf_audit(root):
    """Recall@50 per query with and without automatic PRF (auto_expand), a
    gained/lost/neutral split, and a search for a feature separating the first
    two. Prediction P2: there is a split with >=25% of queries that lose."""
    _sum, per_sin = compute_layer1(root, [10, 20, 50], expanded=False, prf=False)
    _con, per_con = compute_layer1(root, [10, 20, 50], expanded=False, prf=True)
    by_qid_con = {p["qid"]: p for p in per_con}
    rows = []
    for p in per_sin:
        c = by_qid_con.get(p["qid"])
        if not c:
            continue
        delta = c["recall50"] - p["recall50"]
        rows.append({"qid": p["qid"], "recall50_without_prf": p["recall50"],
                     "recall50_with_prf": c["recall50"], "delta": round(delta, 4),
                     "length_chars": p["length_chars"], "n_concepts": p["n_concepts"],
                     "n_initial_candidates": p["n_initial_candidates"],
                     "folder_dispersion_top10": p["folder_dispersion_top10"]})
    ganan = [r for r in rows if r["delta"] > 0]
    pierden = [r for r in rows if r["delta"] < 0]
    empatan = [r for r in rows if r["delta"] == 0]
    feats = ["length_chars", "n_concepts", "n_initial_candidates", "folder_dispersion_top10"]
    rasgos = {}
    for f in feats:
        g = [r[f] for r in ganan]; p_ = [r[f] for r in pierden]
        rasgos[f] = {"mean_won": round(_mean(g), 2) if g else None,
                     "mean_lost": round(_mean(p_), 2) if p_ else None,
                     "delta_means": round((_mean(g) - _mean(p_)), 2) if g and p_ else None}
    # append-only, specific to this reanalysis -- NOT written to data/runs.jsonl
    # (that file feeds layer2's paired gate and a layer1 entry there would break
    # `_paired_last()` for the next real layer2 run).
    audit_path = os.path.join(DATA, "prf_audit.jsonl")
    os.makedirs(DATA, exist_ok=True)
    import datetime
    with open(audit_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                             "per_query": rows}, ensure_ascii=False) + "\n")
    res = {"n": len(rows), "n_wins_prf": len(ganan), "n_loses_prf": len(pierden),
           "n_neutral": len(empatan), "pct_loses": round(100.0 * len(pierden) / len(rows), 1) if rows else None,
           "recall50_mean_without_prf": round(_mean([r["recall50_without_prf"] for r in rows]), 4),
           "recall50_mean_with_prf": round(_mean([r["recall50_with_prf"] for r in rows]), 4),
           "prediction_P2": ">=25% pierden", "holds": bool(rows) and len(pierden) / len(rows) >= 0.25,
           "candidate_separating_feature": rasgos, "detail_path": audit_path}
    json.dump(res, open(os.path.join(CACHE, "prf_audit.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    out({k: v for k, v in res.items() if k != "detail_path"} | {"detail_path": audit_path})


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("index")
    sub.add_parser("gold")
    l1 = sub.add_parser("layer1"); l1.add_argument("--k", default="1,5,10,20")
    l1.add_argument("--expanded", action="store_true")
    pl = sub.add_parser("pool")
    pl.add_argument("--depth", type=int, default=30)
    pl.add_argument("--n", type=int, default=0)
    pl.add_argument("--seed", default="all", choices=["all", "with-gold"])
    pl.add_argument("--qids", default=None, help="comma-separated list of qids")
    jd = sub.add_parser("judge"); jd.add_argument("--file", required=True)
    l2 = sub.add_parser("layer2"); l2.add_argument("--k", default="5,10,20")
    l2.add_argument("--tag", default="", help="label for this run in the history")
    l2.add_argument("--pool", default="auto", choices=["auto", "base", "extended"])
    px = sub.add_parser("pool-extend", help="adds raw BM25 as a third contributing system")
    px.add_argument("--depth", type=int, default=20)
    px.add_argument("--system", default="bm25_raw", choices=["bm25_raw", "embed"],
                    help="third contributing system; `embed` also measures the optional channel")
    sub.add_parser("runs", help="run history + paired delta of the last two")
    jl = sub.add_parser("judge-list", help="a query's candidates, with their current label")
    jl.add_argument("--qid", required=True)
    js = sub.add_parser("judge-set", help="writes a relevance judgment (0|1|2)")
    js.add_argument("--qid", required=True); js.add_argument("--rel", required=True)
    js.add_argument("--label", type=int, required=True)
    cb = sub.add_parser("calibrate", help="sample for human judging / kappa against the LLM judge")
    cb.add_argument("--n", type=int, default=30)
    pn = sub.add_parser("plan", help="split a judgment budget between queries and depth")
    pn.add_argument("--budget", type=int, default=200)
    xc = sub.add_parser("exclude", help="removes a log entry from all metrics")
    xc.add_argument("--qid", required=True)
    xc.add_argument("--reason", required=True, help="why it does not apply; mandatory")
    xi = sub.add_parser("include", help="undoes an exclusion")
    xi.add_argument("--qid", required=True)
    sub.add_parser("exclusions", help="what is outside the measurement, why and since when")
    sub.add_parser("metrics", help="flat output for Meta/metrics.json (eval dashboard)")
    sub.add_parser("expansion-audit", help="P1: correlation n-terms x n-gold over the stored LLM expansions")
    hl = sub.add_parser("hop-loso", help="hop channel recall with all / LOSO / no-co-use edges from graph.jsonl")
    hl.add_argument("--reference-loso", type=float, default=None,
                    help="previously measured LOSO recall@50 to check reproduction against (optional)")
    hl.add_argument("--tolerance", type=float, default=0.03)
    sub.add_parser("prf-audit", help="P2: recall50 with/without PRF per query, gain/loss split and separating feature")
    rv = sub.add_parser("retrieve", help="top-k candidates for a query (operational use, L0 step)")
    rv.add_argument("--log-id", default="", help="id from log_entry.py open, to join sidecar and log")
    rv.add_argument("--intent", default="implicit")
    rv.add_argument("--no-sidecar", action="store_true", help="do not write to Retrieval Candidates.jsonl (evals)")
    rv.add_argument("query")
    rv.add_argument("--k", type=int, default=20)
    rv.add_argument("--expand", default="",
                    help="key concepts in vault vocabulary; if omitted, the engine generates "
                         "an automatic PRF expansion (worse than yours, better than nothing)")
    rv.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not a.cmd:
        ap.print_help()
        return
    root = rlib.vault_root(HERE)
    if a.cmd == "index":
        cmd_index(root)
    elif a.cmd == "gold":
        cmd_gold(root)
    elif a.cmd == "layer1":
        cmd_layer1(root, [int(x) for x in a.k.split(",")], a.expanded)
    elif a.cmd == "pool":
        cmd_pool(root, a.depth, a.n, a.seed, True, a.qids)
    elif a.cmd == "judge":
        cmd_judge(a.file)
    elif a.cmd == "layer2":
        cmd_layer2([int(x) for x in a.k.split(",")], a.tag, a.pool)
    elif a.cmd == "pool-extend":
        cmd_pool_extend(root, a.depth, a.system)
    elif a.cmd == "runs":
        cmd_runs(root)
    elif a.cmd == "judge-list":
        sys.exit(cmd_judge_list(root, a.qid))
    elif a.cmd == "judge-set":
        sys.exit(cmd_judge_set(root, a.qid, a.rel, a.label))
    elif a.cmd == "calibrate":
        cmd_calibrate(root, a.n)
    elif a.cmd == "plan":
        cmd_plan(root, a.budget)
    elif a.cmd == "exclude":
        cmd_exclude(root, a.qid, a.reason)
    elif a.cmd == "include":
        cmd_include(root, a.qid)
    elif a.cmd == "exclusions":
        cmd_exclusions(root)
    elif a.cmd == "metrics":
        cmd_metrics(root)
    elif a.cmd == "expansion-audit":
        cmd_expansion_audit(root)
    elif a.cmd == "hop-loso":
        cmd_hop_loso(root, a.reference_loso, a.tolerance)
    elif a.cmd == "prf-audit":
        cmd_prf_audit(root)
    elif a.cmd == "retrieve":
        sys.exit(cmd_retrieve(root, a.query, a.k, a.expand, a.json,
                              log_id=a.log_id, intent=a.intent, sidecar=not a.no_sidecar))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
