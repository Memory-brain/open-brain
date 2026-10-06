#!/usr/bin/env python3
"""
vault-scan — shared scanning library for an Open Brain vault.

Shared infrastructure (like autolink/). health, enrich and synthesize reuse it
instead of reimplementing the same scan three times. No LLM — pure determinism.

Two ways to use it:

  1. As a library (the engines import it):
        import sys; sys.path.insert(0, "<vault>/vault-scan")
        import vaultscan as vs
        vault = vs.find_vault_root()
        cov = vs.layer_coverage("Communication")

  2. As a CLI (bash / other engines consume JSON):
        python3 vaultscan.py layer-coverage "Communication"
        python3 vaultscan.py crowding
        python3 vaultscan.py domain-notes "Communication"
        python3 vaultscan.py orphans
        python3 vaultscan.py term-refs "Agent Memory"
        python3 vaultscan.py totals

The vault is autodetected (walking up from this file). Override with
OPEN_BRAIN_VAULT (or the legacy VAULT_ROOT).
"""

from __future__ import annotations  # Python 3.9 compatibility: without this, "int | None" in a signature fails at import time

import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from functools import lru_cache

LAYERS = ["knowledge", "compression", "mental-model", "application", "artifact",
          "decision", "diagnosis", "coaching", "practice"]
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+)")


# ============================================================
# PRIMITIVES
# ============================================================

def find_vault_root() -> Path:
    env = os.environ.get("OPEN_BRAIN_VAULT") or os.environ.get("VAULT_ROOT")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "Permanent Notes").exists() and (parent / "Domains").exists():
            return parent
    raise SystemExit("ERROR: vault not found. Set OPEN_BRAIN_VAULT to your vault root.")


VAULT = find_vault_root()


def parse_fm(text: str) -> dict:
    """Minimal dependency-free frontmatter parser. Inline lists [a, b] and block lists - a.

    Joins the continuations of folded values (YAML allows splitting a long value
    across indented lines). Without this, a large share of notes returned their
    `title` truncated at the last word, and `sources` titles split across two lines
    did not resolve to their note: any metric crossing PNs with LNs came out low
    without warning.
    """
    m = FM_RE.match(text)
    if not m:
        return {}
    fm, key = {}, None
    last_scalar = None
    for raw in m.group(1).splitlines():
        if re.match(r"^\s*-\s+", raw) and key:
            fm.setdefault(key, [])
            if isinstance(fm[key], list):
                fm[key].append(raw.strip()[1:].strip().strip("'\""))
            last_scalar = None
            continue
        m2 = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", raw)
        if m2:
            key = m2.group(1)
            v = m2.group(2).strip()
            if v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                fm[key] = [x.strip().strip("'\"") for x in inner.split(",")] if inner else []
                last_scalar = None
            elif v:
                fm[key] = v.strip("'\"")
                last_scalar = key
            else:
                fm[key] = []
                last_scalar = None
            continue
        cont = re.match(r"^\s+(\S.*)$", raw)
        if cont:
            tail = cont.group(1).strip().strip("'\"")
            if key and isinstance(fm.get(key), list) and fm[key]:
                fm[key][-1] = f"{fm[key][-1]} {tail}".strip()
            elif last_scalar and isinstance(fm.get(last_scalar), str):
                fm[last_scalar] = f"{fm[last_scalar]} {tail}".strip()
    return fm


# Files that iter_notes could not read. They used to be dropped with a silent
# `continue`: on a vault with intermittent read errors (e.g. a mounted or synced
# folder returning EACCES) that makes ANY metric vary between runs without
# warning — two consecutive scans can count hundreds of notes apart with nothing
# changed on disk. Consumers must report SKIPPED if it is not empty.
SKIPPED: list = []


def iter_notes(folder: str):
    base = VAULT / folder
    if not base.exists():
        return
    for p in base.rglob("*.md"):
        try:
            yield p, p.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            SKIPPED.append({"path": str(p.relative_to(VAULT)), "error": str(exc)})
            continue


def body_of(text: str) -> str:
    return FM_RE.sub("", text)


def wikilinks(text: str) -> list:
    return [m.group(1).split("/")[-1].strip() for m in WIKILINK_RE.finditer(text)]


def as_list(v) -> list:
    if isinstance(v, list):
        return v
    return [v] if v else []


def days_since(val) -> int | None:
    if not isinstance(val, str):
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", val)
    if not m:
        return None
    try:
        return (date.today() - date(int(m[1]), int(m[2]), int(m[3]))).days
    except ValueError:
        return None


@lru_cache(maxsize=1)
def all_stems() -> frozenset:
    return frozenset(p.stem for p in VAULT.rglob("*.md")
                     if p.relative_to(VAULT).parts[0] not in DELETED_DIRS)


def _domain_match(fm: dict, domain: str) -> bool:
    for d in as_list(fm.get("domains")) + as_list(fm.get("domain")):
        if domain.lower() in str(d).lower():
            return True
    return False


# ============================================================
# SHARED SCANS (consumed by health/enrich/synthesize)
# ============================================================

def domain_notes(domain: str) -> dict:
    """All notes tagged with a domain, by type. For synthesize and enrich."""
    res = {"permanent": [], "literature": [], "cases": []}
    for folder, key in [("Permanent Notes", "permanent"),
                        ("Literature Notes", "literature"), ("Cases", "cases")]:
        for p, text in iter_notes(folder):
            if _domain_match(parse_fm(text), domain):
                res[key].append(p.stem)
    return res


def layer_coverage(domain: str) -> dict:
    """PN count per layer in a domain + layers at 0 (layer gaps).
    Used by synthesize (coverage) and health (check 4)."""
    counts = {layer: 0 for layer in LAYERS}
    total = 0
    for p, text in iter_notes("Permanent Notes"):
        fm = parse_fm(text)
        if not _domain_match(fm, domain):
            continue
        total += 1
        lyr = (fm.get("layer") or "").strip().lower()
        if lyr in counts:
            counts[lyr] += 1
    gaps = [l for l, n in counts.items() if n == 0]
    return {"domain": domain, "total_pns": total, "by_layer": counts, "gaps": gaps}


# ============================================================
# MATURITY — a DERIVED field, never written by hand
# ============================================================

# The 6 legal values of `features` (multi-label, v10) and the functions
# considered operative (know-how) versus declarative (knowing that).
FEATURES = ("code-artifact", "diagnosis", "application", "decision", "factual", "conceptual")
OPERATIVE_FEATURES = ("decision", "application", "diagnosis", "code-artifact")
OPERATIVE_LAYERS = ("decision", "application", "diagnosis", "artifact", "practice", "coaching")

MATURITY_STATES = ("seed", "growing", "evergreen")


def maturity(times_retrieved=0, external_outputs=0, internal_outputs=0) -> str:
    """Maturity state of a PN, DERIVED from its counters. The single implementation.

    Contract (`budding` remains a dead alias of `growing`, and the `active`
    state of the old schema is gone):

      seed       — nobody has used it yet.
      growing    — >=2 retrievals OR it has fed some output (shipped or published).
      evergreen  — >=5 retrievals AND >=1 PUBLISHED output (external_outputs).

    Why derived and not written: when `maturity` is written by hand and no line
    of code computes it, the vault drifts — notes end up in states that do not
    exist in the contract, nothing ever reaches evergreen, and most notes declare
    a maturity their own counters don't support.
    """
    tr = int(times_retrieved or 0)
    eo = int(external_outputs or 0)
    io = int(internal_outputs or 0)
    if tr >= 5 and eo >= 1:
        return "evergreen"
    if tr >= 2 or eo >= 1 or io >= 1:
        return "growing"
    return "seed"


def maturity_of(fm: dict) -> str:
    """maturity() applied to a note's frontmatter."""
    def num(k):
        v = fm.get(k)
        try:
            return int(str(v).strip().strip('"\''))
        except Exception:
            return 0
    return maturity(num("times_retrieved"), num("external_outputs"), num("internal_outputs"))


CONF_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.3}
ENDORSE_WEIGHT = {"endorsed": 1.0, "provisional": 0.5, "unendorsed": 0.2, "rejected": 0.0}


def _num(fm: dict, key: str) -> int:
    v = fm.get(key)
    try:
        return int(str(v).strip().strip('"\''))
    except Exception:
        return 0


def importance_of(fm: dict) -> float:
    """Approximation of 'importance' for dormancy_score() -- first draft
    (principle: forgetting should degrade fidelity gradually, gated by age times
    importance, never by storage cost). Combines declared confidence +
    endorsement_state + real evidence of use (times_retrieved, capped at 5) --
    none of the three alone, so as not to trust only a declared proxy or only
    recency. Weights (0.4/0.3/0.3) are not calibrated against real vault data."""
    conf = CONF_WEIGHT.get(str(fm.get("confidence") or "").strip().lower(), 0.5)
    endorse = ENDORSE_WEIGHT.get(str(fm.get("endorsement_state") or "").strip().lower(), 0.5)
    retrieval_boost = min(_num(fm, "times_retrieved") / 5.0, 1.0)
    return round(0.4 * conf + 0.3 * endorse + 0.3 * retrieval_boost, 3)


def _cold_start_guard() -> date | None:
    """Date from which your vault started counting `times_retrieved`.

    Set it with OPEN_BRAIN_COLD_START=YYYY-MM-DD (e.g. the day you installed
    open-brain-retrieve). Default: None — no guard, ages are taken as they are.
    """
    raw = os.environ.get("OPEN_BRAIN_COLD_START", "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", raw)
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None


COLD_START_GUARD = _cold_start_guard()  # times_retrieved counting starts here — never before.


def _age_days_with_cold_start_guard(fm: dict) -> int | None:
    """days_since(created), floored at COLD_START_GUARD (when set).

    Without this, a PN created before the vault started counting times_retrieved
    (see 'Tracking What You Read' in open-brain-retrieve) accumulates age from
    its real `created` date even though it could never accumulate retrievals
    during that period -- inflating dormancy_score() with an artefact of when the
    instrument started, not with real neglect."""
    raw = days_since(fm.get("created")) or days_since(fm.get("last_validated"))
    if raw is None:
        return None
    if COLD_START_GUARD is None:
        return raw
    floor = (date.today() - COLD_START_GUARD).days
    return min(raw, floor) if floor >= 0 else raw


def dormancy_score(fm: dict) -> float | None:
    """First draft of a successor to the retired 'Dormant Deprecation cascade'.
    Age x (1 - importance): an old AND unimportant note accumulates a high score;
    an old but highly important note (lots of retrieval, high confidence,
    endorsed) barely accumulates, even at the same age -- age alone is a near-null
    signal. It never writes anything nor changes `maturity`: it is a read signal
    for health/Hot Cache, and the state change remains a human decision.
    Threshold and weights are a first cut -- calibrate against real retrieval
    logs before trusting the exact number (avoid threshold leakage).

    Age uses _age_days_with_cold_start_guard(): when OPEN_BRAIN_COLD_START is
    set, a PN older than that date accumulates no dormancy for age prior to the
    instrument."""
    age = _age_days_with_cold_start_guard(fm)
    if age is None:
        return None
    age_norm = min(age / 365.0, 2.0)
    importance = importance_of(fm)
    return round(age_norm * (1 - importance), 3)


def maturity_drift() -> dict:
    """PNs whose declared `maturity` does not match the derived one. Used by health (check 6)."""
    items = []
    counts = {s: 0 for s in MATURITY_STATES}
    for p, text in iter_notes("Permanent Notes"):
        fm = parse_fm(text)
        derived = maturity_of(fm)
        counts[derived] += 1
        declared = str(fm.get("maturity") or "").strip().lower()
        if declared != derived:
            items.append({"note": p.stem, "declared": declared or "(empty)", "derived": derived})
    return {"derived_counts": counts, "drift": items}



def function_coverage(domain: str) -> dict:
    """Coverage of cognitive FUNCTIONS in a domain (v10: `features`, fallback `layer`).

    Replaces layer_coverage() as the basis of health's check 4. Why: the schema
    moved from a single `layer` to multi-label `features`, and the per-domain
    coverage audit lost its implementation along the way. Notes that predate the
    change have no `features`, so the legacy `layer` is counted as a fallback.

    Returns operative vs declarative counts and the functions at zero. It is a
    WARN signal, not a BLOCK: the labels are noisy (strict precision on
    `diagnosis` is low), so it serves to orient, not to force extraction — the
    anti-pattern to avoid is creating notes just to fill the table (filler notes
    are rarely retrieved).
    """
    counts = {f: 0 for f in FEATURES}
    legacy = {l: 0 for l in LAYERS}
    total = tagged = 0
    for _p, text in iter_notes("Permanent Notes"):
        fm = parse_fm(text)
        if not _domain_match(fm, domain):
            continue
        total += 1
        feats = [str(x).strip().lower() for x in as_list(fm.get("features"))]
        feats = [f for f in feats if f in counts]
        if feats:
            tagged += 1
            for f in feats:
                counts[f] += 1
        else:
            lyr = (fm.get("layer") or "").strip().lower()
            if lyr in legacy:
                legacy[lyr] += 1
    op = sum(counts[f] for f in OPERATIVE_FEATURES) + sum(legacy[l] for l in OPERATIVE_LAYERS if l in legacy)
    dec = (total - op) if total else 0
    return {"domain": domain, "total_pns": total, "tagged_with_features": tagged,
            "by_feature": counts, "by_legacy_layer": legacy,
            "operative": op, "declarative": dec,
            "operative_ratio": round(op / total, 2) if total else 0.0,
            "features_at_zero": [f for f, n in counts.items() if n == 0]}


# Term families: hub -> prefixes that count as its specific children even when
# they don't share its literal name. Only affects `orphan_of` in crowding().
#
# This is vault-specific taxonomy, so it ships EMPTY. Declare your own families
# in a JSON file next to this script, `vault-scan/term_families.json` (or point
# OPEN_BRAIN_TERM_FAMILIES at another path), mapping a hub Search Term to the
# Search Terms that are its semantic children:
#
#   {
#     "Product Management": ["Product Discovery", "Product Strategy", "Jobs To Be Done"],
#     "Agent Memory": ["Episodic Memory", "Semantic Memory", "Context Retrieval"]
#   }
#
# Declare a family when a saturated flat term already has specific terms in
# Search Terms/ covering its territory that don't follow the "Parent — Child"
# naming convention detected by siblings_of(): declaring them is cheaper and
# cleaner than creating duplicate child terms. Avoid cycles (don't list a term's
# own ancestors as its children).
def _load_term_families() -> dict:
    path = os.environ.get("OPEN_BRAIN_TERM_FAMILIES") or str(Path(__file__).resolve().parent / "term_families.json")
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"WARNING: could not read term families from {p}: {exc}", file=sys.stderr)
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): tuple(str(x) for x in as_list(v)) for k, v in data.items()}


TERM_FAMILIES = _load_term_families()


def crowding(red=20, yellow=10, red_hub=150) -> dict:
    """Search Term crowding. Used by health (16) and enrich.

    Measures TWO distinct signals and does not confuse them:

    - `tag_count`: occurrences of the term in the `search_terms:` frontmatter
      field. This is the REAL crowding signal — the one that competes on
      precision when you search by that term.
    - `mention_count`: any wikilink to the term anywhere in the note
      (frontmatter + `search_context:` + prose + "## Typed Connections"). That
      is hub connectivity, not crowding. Classifying red/yellow on this signal
      overcounts 2-12x, because modern notes repeat each `[[term]]` in the
      `search_context:` block with its justification — so a split that really
      reduced crowding would still be reported as if nothing had happened.

    Double threshold. `tier` classifies each term:
    - `hub`: matches a registered domain or already has children ("Term — Sub").
    - `leaf_of_hub`: is the child of an existing parent term. Counts as a hub
      because it is the hub of its own subtree: if saturated, reducing it needs
      a second taxonomy level, not a redistribution.
    - `flat`: neither parent nor child. Intended to be specific.
    The first two are judged against `red_hub` (high by design), `flat` against
    `red`. That way red doesn't fill up with deliberate hubs, and a split
    (e.g. Leadership → — Vision/Feedback/...) reads as what it is: the children
    are now hubs of their subtree, not overflowing specific terms.

    Each entry carries `actionable`: True if the term already has a more
    specific sibling in the registry (redistributing is mechanical), False if
    splitting it would require creating new taxonomy (your decision, not a
    check's).
    """
    st_dir = VAULT / "Search Terms"
    term_files = [p.stem for p in st_dir.rglob("*.md")] if st_dir.exists() else []
    term_set = frozenset(term_files)
    domain_set = frozenset(list_domains())

    tag_counts, mention_counts = {}, {}
    note_tagsets = []
    for folder in ["Literature Notes", "Permanent Notes", "Fleeting Notes"]:
        for p, text in iter_notes(folder):
            seen = set()
            for t in wikilinks(text):
                if t in term_set and t not in seen:
                    mention_counts[t] = mention_counts.get(t, 0) + 1
                    seen.add(t)
            tag_seen = set()
            for raw in as_list(parse_fm(text).get("search_terms")):
                t = raw.replace("[[", "").replace("]]", "").split("|")[0].strip()
                if t in term_set and t not in tag_seen:
                    tag_counts[t] = tag_counts.get(t, 0) + 1
                    tag_seen.add(t)
            if tag_seen:
                note_tagsets.append(tag_seen)

    def siblings_of(t):
        sib = [s for s in term_files
               if s.startswith(t + " —") or s.startswith(t + " - ")]
        # Declared families: prefixes that are semantic children of `t` even
        # though they don't carry its name. Without this, `orphan_of` counts as
        # an orphan a note tagged [[Product Management]] + [[Product Discovery —
        # Customer Interviews]], which is exactly the opposite of an unspecified
        # note. See TERM_FAMILIES above.
        for pref in TERM_FAMILIES.get(t, ()):
            sib += [s for s in term_files
                    if s == pref or s.startswith(pref + " —") or s.startswith(pref + " - ")]
        return sorted(set(sib))

    def parent_of(t):
        for sep in (" — ", " - "):
            if sep in t:
                cand = t.split(sep)[0].strip()
                if cand in term_set:
                    return cand
        return None

    def orphan_of(t, sib):
        """Notes tagged with the parent `t` that carry NONE of its children.

        A parent term is kept alongside the child by convention, so its raw
        `tag_count` always paints it red even when there is nothing to
        redistribute. What can be redistributed from a parent is only the notes
        that carry it *without* a child. For parents, red is judged against this
        number; `tag_count` is still reported intact so consumers don't break.
        """
        if not sib:
            return None
        s = set(sib)
        return sum(1 for tags in note_tagsets if t in tags and not (tags & s))

    def entry(t, n):
        sib = siblings_of(t)
        parent = parent_of(t)
        tier = "hub" if (t in domain_set or sib) else ("leaf_of_hub" if parent else "flat")
        orph = orphan_of(t, sib)
        return {"term": t, "tag_count": n, "mention_count": mention_counts.get(t, 0),
                "tier": tier, "is_hub": tier != "flat",
                "threshold": red if tier == "flat" else red_hub,
                "parent": parent, "sibling_count": len(sib), "actionable": bool(sib),
                "orphan_tag_count": orph,
                "effective_count": n if orph is None else orph,
                # compat: old consumers read "notes"
                "notes": n}

    scored = [entry(t, n) for t, n in tag_counts.items()]
    red_l = sorted([e for e in scored if e["effective_count"] > e["threshold"]],
                   key=lambda e: -e["effective_count"])
    yel_l = sorted([e for e in scored
                    if yellow < e["effective_count"] <= e["threshold"]],
                   key=lambda e: -e["effective_count"])
    return {"red": red_l,
            "yellow": yel_l,
            "green_count": sum(1 for e in scored if e["effective_count"] <= yellow),
            "thresholds": {"red_specific": red, "red_hub": red_hub, "yellow": yellow},
            "red_actionable": [e for e in red_l if e["actionable"]],
            "red_atomic": [e for e in red_l if not e["actionable"]],
            "all_counts": tag_counts,
            "mention_counts": mention_counts}



def over_application(min_notes=20, ratio=0.40) -> dict:
    """OVER-APPLIED terms: the pathology that `crowding()` doesn't distinguish.

    crowding() measures how many notes carry a term. That doesn't separate two
    very different causes that look the same in red:

    - SATURATED: the term is correct on all its notes, there are just many.
      The fix is to split it (create new taxonomy).
    - OVER-APPLIED: the term is placed on notes that don't earn it. The fix is
      to remove it. Splitting it here only relabels the error in two places.

    The reflex "it's red -> split it" fails when the cause is the second kind.
    A typical origin of the spraying: a lint rule that requires a minimum number
    of search_terms counted as strings, so enrichment satisfies the quota with
    the cheapest hub term that vaguely fits.

    Two independent signals, neither conclusive on its own — they are a "go read
    these notes", not a verdict:

    1. `sibling_overlap`: of the notes with `P - X`, what fraction ALSO carry
       another child of `P`. High = `X` doesn't discriminate within its own
       family (e.g. `Leadership - Vision` co-occurring with `- Feedback` on half
       of its notes).
    2. `domain_mismatch`: for a term that is also a registered Domain, what
       fraction of its notes does NOT declare it in `domains:`. High = the term
       is used as a convenience label outside its domain.

    High overlap can be legitimate (a note can be about vision AND feedback).
    What isn't legitimate is for it to be the majority.

    BLIND SPOT: this signal detects labels that don't discriminate WITHIN their
    family, and is blind to the absorption of foreign material. When a term
    absorbs whole corpora from ANOTHER domain and those notes declare the term's
    domain in `domains:` in good faith, the metadata agrees with itself, so no
    metadata comparison sees it. That only shows up by reading a sample (title +
    description of 10 random notes of the term), which can't be automated.

    Don't treat "0 flagged" as absence of over-application.
    """
    st_dir = VAULT / "Search Terms"
    term_files = [p.stem for p in st_dir.rglob("*.md")] if st_dir.exists() else []
    term_set = frozenset(term_files)
    domain_set = frozenset(list_domains())

    children: dict = {}
    for t in term_files:
        for sep in (" — ", " - "):
            if sep in t:
                par = t.split(sep)[0].strip()
                if par in term_set:
                    children.setdefault(par, set()).add(t)
                break

    tagsets = []
    for folder in ["Literature Notes", "Permanent Notes", "Fleeting Notes"]:
        for _p, text in iter_notes(folder):
            fm = parse_fm(text)
            tags = set()
            for raw in as_list(fm.get("search_terms")):
                t = raw.replace("[[", "").replace("]]", "").split("|")[0].strip()
                if t in term_set:
                    tags.add(t)
            doms = {d.replace("[[", "").replace("]]", "").split("|")[0].strip()
                    for d in as_list(fm.get("domains"))}
            if tags:
                tagsets.append((tags, doms))

    out = []
    for t in term_files:
        notes = [(tg, dm) for tg, dm in tagsets if t in tg]
        n = len(notes)
        if n < min_notes:
            continue
        par = None
        for sep in (" — ", " - "):
            if sep in t:
                cand = t.split(sep)[0].strip()
                if cand in term_set:
                    par = cand
                break
        sib_overlap = None
        if par:
            sibs = children.get(par, set()) - {t}
            if sibs:
                sib_overlap = round(sum(1 for tg, _ in notes if tg & sibs) / n, 2)
        dom_mismatch = None
        if t in domain_set:
            dom_mismatch = round(sum(1 for _, dm in notes if t not in dm) / n, 2)
        flags = []
        if sib_overlap is not None and sib_overlap > ratio:
            flags.append("sibling_overlap")
        if dom_mismatch is not None and dom_mismatch > ratio:
            flags.append("domain_mismatch")
        if flags:
            out.append({"term": t, "notes": n, "parent": par,
                        "sibling_overlap": sib_overlap,
                        "domain_mismatch": dom_mismatch,
                        "flags": flags})
    out.sort(key=lambda e: -e["notes"])
    return {"thresholds": {"min_notes": min_notes, "ratio": ratio},
            "flagged": out, "skipped_unreadable": len(SKIPPED)}


def orphans() -> list:
    """PNs with no outgoing wikilinks in the body. health (1) and enrich."""
    out = []
    for p, text in iter_notes("Permanent Notes"):
        if not WIKILINK_RE.search(body_of(text)):
            out.append(p.stem)
    return out


# --- orphan classification (v3.3) ---------------------------------------------
# orphans() above only looks at Permanent Notes. That makes it correct in scope
# and blind in practice: a vault can have thousands of notes without a single
# wikilink while health reports "Orphan Notes: 0". Not all of them are a problem,
# so counting them raw doesn't help either — they must be classified.

INFRA_DIRS = {
    "Skills", "Templates", "Search Terms", "Meta", "Tasks",
    "Archive",
    "autolink", "engine", "vault-scan",
    "enrich-engine", "eval-engine", "health-engine", "synthesize-engine",
    "practice-log-engine", "course-engine", "retrieval-eval",
    "Resources",  # Hot Cache, specs, rubrics, system playbooks: reference, not network
}
# Deferred trash: when a session can't delete files, it moves here what you
# should delete by hand. They are COPIES of live notes: counting them duplicates
# findings and, via all_stems(), makes a link to a deleted note look resolved.
DELETED_DIRS = {"_to_delete"}

# Sub-vaults with their own metadata contract: search_terms as plain text
# instead of wikilinks. They aren't broken — they are outside the graph by
# design. Mixing them with the real orphans hides the ones that matter.
# Vault-specific: add path prefixes relative to the vault root, e.g.
# ("Projects/Active/My Sub-vault",). Empty by default.
SUBVAULT_PREFIXES: tuple = ()
# Terminal artefacts: the note IS the output (it gets sent, published, archived).
# It doesn't feed the graph forward, so not linking is not a defect.
TERMINAL_DIRS = {"Manuscripts", "Published", "Research", "Projects"}
TERMINAL_TYPES = {
    "article", "post", "talk", "report", "message", "repo", "manuscript",
    "handoff", "recap", "research-report", "research-plan",
    "vault-health-report", "health-report", "eval-report", "audit", "benchmark",
    "historical-artifact", "scripts-readme",
    # Kept: engine/batch_scorecard.py maps this source type.
    "github-repo",
}
# Capture buffers: the note comes in raw and gets woven later (or never — it's
# discarded). Having no links here isn't debt, it's the default state. Counting
# them as `knowledge` inflates check 23 and buries the knowledge that really is
# disconnected.
CAPTURE_DIRS = {"Inbox", "Ideas", "Fleeting Notes"}
# Folders where a note without links IS a failure: knowledge that should be
# woven into the network.
KNOWLEDGE_DIRS = {
    "Permanent Notes", "Literature Notes", "Cases", "Dossiers", "Domains",
    "Mentors", "Playbooks", "Areas", "Sources",
}


def _orphan_class(rel_path: str, folder: str, ntype: str) -> str:
    if SUBVAULT_PREFIXES and rel_path.startswith(SUBVAULT_PREFIXES):
        return "subvault"
    if "/" not in rel_path:  # README.md, Home.md… root docs
        return "infra"
    if folder in INFRA_DIRS:
        return "infra"
    if folder in TERMINAL_DIRS or ntype in TERMINAL_TYPES:
        return "terminal"
    if folder in CAPTURE_DIRS:
        return "capture"
    if folder in KNOWLEDGE_DIRS:
        return "knowledge"
    return "other"


def orphans_all() -> dict:
    """Notes with NO wikilink at all (frontmatter or body), classified by class.
    Only `knowledge` is actionable; the rest is reported so it isn't mistaken
    for a problem again. Consumed by health (check 23)."""
    buckets = {"knowledge": [], "capture": [], "terminal": [], "infra": [],
               "subvault": [], "other": []}
    for p in VAULT.rglob("*.md"):
        rel = p.relative_to(VAULT).as_posix()
        if rel.startswith("."):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if WIKILINK_RE.search(text):
            continue
        folder = rel.split("/")[0]
        ntype = str(parse_fm(text).get("type", "") or "")
        buckets[_orphan_class(rel, folder, ntype)].append(rel)
    return {k: sorted(v) for k, v in buckets.items()}


def unlinked_search_terms() -> dict:
    """Notes whose search_terms are plain text instead of wikilinks.
    They pass any count threshold and contribute not a single edge to the graph
    — the failure that let enrich consider a note indexed with 7 'terms' that
    linked to nothing. Separates the sub-vault (own contract) from the rest."""
    main, subvault = [], []
    for p in VAULT.rglob("*.md"):
        rel = p.relative_to(VAULT).as_posix()
        if rel.startswith(".") or rel.split("/")[0] in INFRA_DIRS | DELETED_DIRS:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        raw = as_list(parse_fm(text).get("search_terms"))
        plain = [str(t) for t in raw if "[[" not in str(t)]
        if not plain:
            continue
        rec = {"note": rel, "plain": len(plain), "total": len(raw), "sample": plain[:3]}
        is_sub = bool(SUBVAULT_PREFIXES) and rel.startswith(SUBVAULT_PREFIXES)
        (subvault if is_sub else main).append(rec)
    return {"main": main, "subvault": subvault}


def term_refs(term: str) -> dict:
    """Notes that reference a specific Search Term. enrich (term splitting)."""
    refs = []
    for folder in ["Literature Notes", "Permanent Notes", "Fleeting Notes"]:
        for p, text in iter_notes(folder):
            if term in wikilinks(text):
                refs.append({"note": p.stem, "folder": folder})
    return {"term": term, "count": len(refs), "refs": refs[:200]}


def broken_links(folder="Permanent Notes") -> list:
    stems = all_stems()
    out = []
    for p, text in iter_notes(folder):
        for t in wikilinks(body_of(text)):
            if t and t not in stems:
                out.append({"in": p.stem, "target": t})
    return out


def totals() -> dict:
    t = {}
    for folder in ["Permanent Notes", "Literature Notes", "Inbox", "Cases",
                   "Domains", "Search Terms", "Fleeting Notes"]:
        b = VAULT / folder
        t[folder] = sum(1 for _ in b.rglob("*.md")) if b.exists() else 0
    return t


def list_domains() -> list:
    b = VAULT / "Domains"
    return sorted(p.stem for p in b.glob("*.md")) if b.exists() else []


# ============================================================
# CLI
# ============================================================

def _cli():
    import argparse
    ap = argparse.ArgumentParser(description="vault-scan — shared vault scanning")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("totals")
    sub.add_parser("domains")
    sub.add_parser("orphans")
    sub.add_parser("orphans-all")
    sub.add_parser("unlinked-search-terms")
    sub.add_parser("crowding")
    sub.add_parser("maturity-drift")
    for name in ("layer-coverage", "function-coverage", "domain-notes"):
        s = sub.add_parser(name); s.add_argument("domain")
    s = sub.add_parser("term-refs"); s.add_argument("term")
    s = sub.add_parser("broken-links"); s.add_argument("--folder", default="Permanent Notes")
    a = ap.parse_args()

    fn = {
        "totals": lambda: totals(),
        "domains": lambda: list_domains(),
        "orphans": lambda: {"count": len(orphans()), "items": orphans()[:50]},
        "orphans-all": lambda: {k: {"count": len(v), "items": v[:25]}
                                for k, v in orphans_all().items()},
        "unlinked-search-terms": lambda: {k: {"count": len(v), "items": v[:25]}
                                          for k, v in unlinked_search_terms().items()},
        "crowding": lambda: {k: (v if k != "all_counts" else f"{len(v)} terms")
                             for k, v in crowding().items()},
        "maturity-drift": lambda: {**{k: v for k, v in maturity_drift().items() if k != "drift"},
                                   "drift_count": len(maturity_drift()["drift"]),
                                   "sample": maturity_drift()["drift"][:15]},
        "layer-coverage": lambda: layer_coverage(a.domain),
        "function-coverage": lambda: function_coverage(a.domain),
        "domain-notes": lambda: {k: len(v) for k, v in domain_notes(a.domain).items()},
        "term-refs": lambda: term_refs(a.term),
        "broken-links": lambda: {"count": len(broken_links(a.folder))},
    }[a.cmd]
    print(json.dumps({"ok": True, "vault": str(VAULT), "result": fn()},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()
