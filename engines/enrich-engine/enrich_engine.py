#!/usr/bin/env python3
"""
enrich-engine — deterministic plumbing for open-brain-enrich.

Reuses vault-scan (does not reimplement scanning). The engine does: selection of
under-indexed notes, search_terms audit (resolved vs broken), active domain
registry + orphan domain detection, crowding (via vault-scan), report
persistence, and the WRITING of the terms/domains the AI decided.

The AI keeps the judgment: GENERATING candidate search_terms (synonyms, inverse,
problem angle), deciding secondary domains, and how to split a saturated term.

Commands:
  scan [--threshold N] [--folder F]   → distribution + notes under threshold
  audit "<note_path>"                 → search_terms (resolved/broken), domains, orphans
  crowding                            → delegates to vault-scan
  registry                            → active domains
  apply --json '<payload>'            → writes search_terms/domains/enriched to a note
  resolve-terms --json '<payload>'    → exact / alias / near / free, + hub rule
  report --json '<payload>'           → persists the Enrichment Report
  retrieval-gaps [--since D]          → candidates from the Retrieval Log
  mark-processed --json '<payload>'   → records triaged Retrieval Log entries
  split-orphans [--parent P] [--all]  → notes with a hub but no child (mandatory close of a split)

The vault and vault-scan are autodetected. Override with OPEN_BRAIN_VAULT
(or the legacy VAULT_ROOT).
"""

# `X | None` in annotations is 3.10+; on Python 3.9 the module crashed on
# import. With this future import annotations aren't evaluated and it runs.
from __future__ import annotations


import argparse
import difflib
import json
import os
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

# --- locate vault-scan and import it (shared infra in the vault) ---
def _bootstrap_vaultscan():
    env = os.environ.get("OPEN_BRAIN_VAULT") or os.environ.get("VAULT_ROOT")
    candidates = []
    if env:
        candidates.append(Path(env))
    here = Path(__file__).resolve()
    candidates += [here.parent, *here.parents]
    for base in candidates:
        for vs_dir in [base / "vault-scan", base]:
            if (vs_dir / "vaultscan.py").exists():
                sys.path.insert(0, str(vs_dir))
                return
    raise SystemExit("ERROR: vault-scan/vaultscan.py not found. "
                     "Copy vault-scan/ into the vault root or set OPEN_BRAIN_VAULT.")


_bootstrap_vaultscan()
import vaultscan as vs  # noqa: E402

VAULT = vs.VAULT
TODAY = date.today().isoformat()


def out(o):
    print(json.dumps(o, ensure_ascii=False, indent=2))


def st_count(fm) -> int:
    """Raw string count. Still reported, but it is NOT the gate."""
    return len(vs.as_list(fm.get("search_terms")))


_REGISTRY = None


def term_registry() -> dict:
    """{'terms': set, 'hubs': set}. Same semantics as engine/ln_lint.py L05:
    a hub is a term that has children (`X - something`), or a Domain. A hub
    doesn't discriminate, so it doesn't count as a specific term."""
    global _REGISTRY
    if _REGISTRY is not None:
        return _REGISTRY
    st_dir = VAULT / "Search Terms"
    terms = {q.stem for q in st_dir.rglob("*.md")} if st_dir.is_dir() else set()
    dom_dir = VAULT / "Domains"
    domains = {q.stem for q in dom_dir.rglob("*.md")} if dom_dir.is_dir() else set()
    hubs = {x for x in terms
            if any(o.startswith(x + " \u2014 ") or o.startswith(x + " - ") for o in terms)}
    _REGISTRY = {"terms": terms, "hubs": hubs | domains}
    return _REGISTRY


# Single threshold. ln_lint.py L05 requires >=3 specific-resolvable terms
# (deliberately lowered from 4 to 3). If enrich used 4 it would count as backlog
# notes that already meet extract's contract. The source of truth is L05.
MIN_SPECIFIC = 3


def clean(name) -> str:
    return str(name).replace("[[", "").replace("]]", "").split("|")[0].strip()


def st_specific(fm) -> int:
    """Terms that EXIST in Search Terms/ and are not hubs. That is the only
    thing that retrieves anything, and therefore the only thing that should
    govern the threshold.

    The threshold used to be applied to st_count (strings). Any string satisfies
    it, so enrich closed the quota with the cheapest term that vaguely fit --
    leaving many terms in the vault that resolve to no note at all. Measuring
    strings and calling it indexing is the same Goodhart that ln_lint L05
    corrects; it's why "I ran enrich and nothing changed": the metric went up
    and retrieval didn't."""
    reg = term_registry()
    names = [clean(x) for x in vs.as_list(fm.get("search_terms"))]
    return sum(1 for n in names if n in reg["terms"] and n not in reg["hubs"])



# ------------------------------------------------------------ bilingual registry (H1)
# term_registry() answers "does this stem exist". It doesn't answer the question
# that actually produces vocabulary drift: "does the term I'm about to coin
# already exist under another name?". In a multilingual vault you end up with
# e.g. "cognitive load", "carga cognitiva" and "sobrecarga cognitiva" side by
# side, while most Search Terms/ pages already declare `aliases` nobody
# consults. The index below is that lookup.

_ALIASES = None


def _norm(s) -> str:
    """Canonical form for comparison: no wikilink, no accents, no punctuation,
    hierarchical separators flattened. 'Human-in-the-Loop' and
    'Human In The Loop' collapse; so do 'Leadership - Feedback' and
    'Leadership — Feedback'."""
    s = clean(s).replace("—", " ").replace("–", " ").replace("-", " ")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def alias_index() -> dict:
    """{'by_norm': {canonical_form: [stems]}, 'alias': {alias_norm: [stems]}}.

    `by_norm` catches FORM variants (casing, hyphen, accent) of the same term.
    `alias` catches NAME variants that the term's own page declares
    (translation, synonym, acronym). All Search Terms/ pages are read once and
    cached (a few thousand pages take ~1.5 s)."""
    global _ALIASES
    if _ALIASES is not None:
        return _ALIASES
    by_norm, alias = {}, {}
    st_dir = VAULT / "Search Terms"
    if st_dir.is_dir():
        for p in st_dir.rglob("*.md"):
            by_norm.setdefault(_norm(p.stem), []).append(p.stem)
            try:
                fm = vs.parse_fm(p.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
            for a in vs.as_list(fm.get("aliases")):
                # An alias starting with a sigil (/command, @handle, #tag) is NOT
                # a synonym: it's another way of invoking. `_norm` eats the sigil,
                # so "/workflows" collapsed with "Workflows" and resolve-terms
                # would have redirected the general term "Workflows" to the
                # specific "Dynamic Workflows" (a feature of one product).
                if str(a).strip()[:1] in "/@#":
                    continue
                n = _norm(a)
                if n and n != _norm(p.stem):
                    alias.setdefault(n, []).append(p.stem)
    _ALIASES = {"by_norm": by_norm, "alias": alias}
    return _ALIASES


def domain_covers(parent: str, note_domains) -> bool:
    """True if the note declares the parent or one of its subdomains. Notes write
    `domains: [[Leadership — Feedback]]` (a subdomain, with no file of its own in
    Domains/) and that counts as Leadership: requiring the exact parent flagged
    as 'out of domain' notes that declared precisely the subdomain."""
    pl = parent.lower()
    for d in note_domains or []:
        d = str(d).lower().strip()
        if d == pl or d.startswith(pl + " — ") or d.startswith(pl + " - "):
            return True
    return False


def hub_parent(term: str) -> str | None:
    """'Leadership — Feedback' -> 'Leadership', but ONLY if the parent is a real
    Domain. Deliberate scope: most hierarchical terms hang from a term
    ('Agentic AI — Memory'), not from a domain. Applying the domain rule to those
    would reject legitimate sub-terms, which is the false positive that kills a
    new rule. It applies only to the ones hanging from a Domain, which are the
    ones prone to over-application."""
    doms = {d.lower(): d for d in (q.stem for q in (VAULT / "Domains").rglob("*.md"))}
    for sep in (" — ", " - ", " – "):
        if sep in term:
            parent = clean(term).split(sep)[0].strip()
            return doms.get(parent.lower())
    return None


def resolve_terms(terms, note_domains=None) -> dict:
    """Classifies each proposed term as: exact / alias / near / free, and flags
    hierarchical hubs whose parent domain the note doesn't declare.

    It is the gate `enrich` applies (reject what has no page) made available to
    `extract`, which writes search_terms without going through it — that is
    where unregistered free terms leak in from."""
    reg = term_registry()
    idx = alias_index()
    note_domains = [clean(d).lower() for d in (note_domains or [])]
    res = {"exact": [], "alias": [], "near": [], "free": [], "hub_domain_mismatch": [], "hub": []}
    stems_norm = list(idx["by_norm"].keys())
    for raw in terms:
        t = clean(raw)
        if not t:
            continue
        parent = hub_parent(t)
        if parent and not domain_covers(parent, note_domains):
            res["hub_domain_mismatch"].append({"term": t, "parent": parent})
        n = _norm(t)
        if t in reg["terms"] and t in reg["hubs"]:
            # A hub exists but does NOT count for L05. It used to come out as
            # `exact` without warning and extract used it as one of its terms,
            # leaving notes one specific term short.
            kids = sorted(x for x in reg["terms"]
                          if x.startswith(t + " \u2014 ") or x.startswith(t + " - "))
            res["hub"].append({"term": t, "counts": False, "children": kids[:12]})
        elif t in reg["terms"]:
            res["exact"].append({"term": t, "canon": t})
        elif n in idx["by_norm"]:
            res["alias"].append({"term": t, "canon": idx["by_norm"][n][0], "via": "form variant"})
        elif n in idx["alias"]:
            res["alias"].append({"term": t, "canon": idx["alias"][n][0], "via": "declared alias"})
        else:
            close = difflib.get_close_matches(n, stems_norm, n=3, cutoff=0.88)
            if close:
                res["near"].append({"term": t,
                                    "candidates": [idx["by_norm"][c][0] for c in close]})
            else:
                res["free"].append(t)
    return res


def cmd_resolve_terms(payload):
    r = resolve_terms(payload.get("terms", []), payload.get("domains"))
    n_free = len(r["free"])
    out({"ok": True, **r,
         "counts": {k: len(v) for k, v in r.items()},
         "hint_hub": ("`hub`: exists but doesn't count as specific (ln_lint L05). You can "
                      "keep it, but add one of its `children` or another specific "
                      "term to reach the minimum.") if r["hub"] else None,
         "hint": ("Replace each `alias` with its `canon` and each `near` with the candidate "
                  "if it's the same concept. A `free` term is only coined if >=2 notes "
                  "in the batch justify it and its page is created in Search Terms/ in the "
                  "same batch; if only one note carries it, leave it in the body -- the body "
                  "grep (weight 0.5) already finds it and it doesn't pollute the intersection."
                  ) if n_free else None})

# ------------------------------------------------------------ scan
def cmd_scan(threshold, folder):
    folders = [folder] if folder else ["Literature Notes", "Permanent Notes", "Fleeting Notes"]
    dist = {"strict_ge6": 0, "default_ge4": 0, "lenient_ge3": 0, "under": 0}
    under = []
    needs = []
    total = 0
    for fol in folders:
        for p, text in vs.iter_notes(fol):
            fm = vs.parse_fm(text)
            total += 1
            n = st_specific(fm)
            n_raw = st_count(fm)
            if n >= 6:
                dist["strict_ge6"] += 1
            if n >= 4:
                dist["default_ge4"] += 1
            if n >= 3:
                dist["lenient_ge3"] += 1
            if n < threshold:
                dist["under"] += 1
                under.append({"note": p.stem, "folder": fol,
                              "specific_resolvable": n, "raw_strings": n_raw})
            if str(fm.get("needs_enrichment", "")).lower() == "true":
                needs.append(p.stem)
    out({"ok": True, "threshold": threshold, "total": total,
         # The threshold applies to SPECIFIC AND RESOLVABLE terms, not strings.
         # A run against an older version will show more notes under threshold:
         # that's not a regression, it's the backlog the string count didn't see.
         "counting": "specific_resolvable (exists in Search Terms/ and is not a hub)",
         "registry_size": len(term_registry()["terms"]),
         "distribution": dist,
         "needs_enrichment": needs,
         # failed reads: if not 0, `total` and `under` are a subset and
         # comparing two runs means nothing. See vaultscan.SKIPPED.
         "skipped_unreadable": len(vs.SKIPPED),
         "skipped_sample": vs.SKIPPED[:10],
         "under_threshold": sorted(under, key=lambda x: x["specific_resolvable"])[:60]})


# ------------------------------------------------------------ audit
def cmd_audit(note_path):
    p = VAULT / note_path if not os.path.isabs(note_path) else Path(note_path)
    if not p.exists():
        # try to resolve by stem
        hits = list(VAULT.rglob(f"{note_path}.md"))
        if hits:
            p = hits[0]
        else:
            out({"ok": False, "error": f"not found: {note_path}"}); return
    fm = vs.parse_fm(p.read_text(encoding="utf-8", errors="ignore"))
    stems = vs.all_stems()
    terms = vs.as_list(fm.get("search_terms"))
    resolved, broken = [], []
    for t in terms:
        name = t.replace("[[", "").replace("]]", "").split("|")[0].strip()
        (resolved if name in stems else broken).append(name)
    registry = set(vs.list_domains())
    note_domains = [d.replace("[[", "").replace("]]", "").strip()
                    for d in vs.as_list(fm.get("domains"))]
    orphans = [d for d in note_domains if d and d not in registry]
    out({"ok": True, "note": p.stem,
         "search_terms_count": len(terms),
         "resolved": resolved, "broken_links": broken,
         "domains": note_domains, "orphan_domains": orphans})


# ------------------------------------------------------------ crowding / registry
def cmd_crowding():
    """Prioritised crowding. vs.crowding() counts over the `search_terms` field
    (not wikilinks across the whole note — see its docstring) and applies a
    double hub/specific threshold. Here it is only prioritised for the AI's eye:
    `tag_red_actionable` first (the term already has a more specific sibling →
    redistribution is mechanical), `tag_red_atomic` after (splitting it would
    require new taxonomy → the vault owner's decision, not an enrich fix)."""
    c = vs.crowding()
    out({"ok": True,
         "thresholds": c["thresholds"],
         "tag_red_actionable": c["red_actionable"],
         "tag_red_atomic": c["red_atomic"],
         "red": c["red"], "yellow_count": len(c["yellow"]),
         "green_count": c["green_count"],
         "note": ("tag_count = occurrences in the search_terms field (the real "
                  "crowding signal). mention_count = wikilinks across the whole note, "
                  "including search_context (hub connectivity, not crowding).")})


def cmd_registry():
    out({"ok": True, "domains": vs.list_domains()})


# ------------------------------------------------------------ apply
def cmd_apply(payload, dry, allow_new=False, needs_enrichment_threshold=MIN_SPECIFIC,
              allow_hub_mismatch=False):
    """Writes the search_terms/domains/enriched the AI decided. NEVER touches
    content or protected fields. add_search_terms and add_domains are lists of names.

    Also: if after applying the terms the note reaches the threshold (same
    criterion as `scan`: specific-resolvable, not strings), it clears
    `needs_enrichment` -> false. If it's still below, the flag is deliberately
    left true -- it's still real backlog. Previously `enriched` was stamped
    without ever touching the flag, so a scan filtered by needs_enrichment kept
    showing notes that had already been fixed."""
    p = VAULT / payload["note"] if not os.path.isabs(payload["note"]) else Path(payload["note"])
    if not p.exists():
        hits = list(VAULT.rglob(f"{payload['note']}.md"))
        if hits:
            p = hits[0]
        else:
            out({"ok": False, "error": f"not found: {payload['note']}"}); return
    text = p.read_text(encoding="utf-8")
    fm = vs.parse_fm(text)
    PROTECTED = {"layer", "confidence", "maturity", "times_retrieved", "external_outputs",
                 "last_retrieved", "last_validated", "primary_form", "visual_goal",
                 "cognitive_mode", "pattern_family", "emotional_tone", "density",
                 "text_to_visual_ratio", "reuse_score", "output_targets", "linked_pns",
                 "source_lns", "related_principles", "why_i_like_it", "interactive_asset"}
    # safety: don't allow touching protected fields
    for k in list(payload.keys()):
        if k in PROTECTED:
            out({"ok": False, "error": f"protected field: {k}"}); return

    existing_terms = [t.replace("[[", "").replace("]]", "").strip()
                      for t in vs.as_list(fm.get("search_terms"))]
    proposed = [t for t in payload.get("add_search_terms", []) if clean(t) not in existing_terms]
    # A term that doesn't exist in Search Terms/ adds no edge to the graph and
    # nobody retrieves it: it's a string in YAML. It is rejected loudly instead
    # of being written. If the term is good and missing, create its note first
    # (or pass --allow-new deliberately).
    reg = term_registry()
    new_terms = [t for t in proposed if clean(t) in reg["terms"]]
    rejected = [t for t in proposed if clean(t) not in reg["terms"]]
    if allow_new:
        new_terms, rejected = proposed, []
    existing_dom = [d.replace("[[", "").replace("]]", "").strip()
                    for d in vs.as_list(fm.get("domains"))]
    new_dom = [d for d in payload.get("add_domains", []) if d not in existing_dom]

    # H2 -- domain rule for hierarchical hubs. A hub "X - Y" whose parent X is
    # a Domain is only attached if the note declares X in `domains`. Without
    # this rule the hub gets pasted like a template (e.g. "Leadership - Feedback"
    # ending up on writing and motivation notes, most of them outside
    # Leadership). A hub pasted that way discriminates nothing and also pollutes
    # any future term x type intersection, which is what prefiltering measures.
    # It is rejected LOUDLY, like a term without a page, not silently.
    doms_after = [d.lower() for d in (existing_dom + new_dom)]
    hub_mismatch = []
    if not allow_hub_mismatch:
        kept = []
        for t in new_terms:
            parent = hub_parent(t)
            if parent and not domain_covers(parent, doms_after):
                hub_mismatch.append({"term": clean(t), "parent": parent})
            else:
                kept.append(t)
        new_terms = kept

    fm_match = vs.FM_RE.match(text)
    if not fm_match:
        out({"ok": False, "error": "no frontmatter"}); return
    fm_block = fm_match.group(1)

    def upsert_list(block, key, existing, additions):
        # clean() before wrapping: the payload may carry "[[X]]" and `existing`
        # is already clean, so wrapping without cleaning produced "[[[[X]]]]"
        # (health check_22 detects it; the defect was in this writer, not in
        # any batch).
        all_vals = list(dict.fromkeys(clean(v) for v in existing + additions))
        yaml = f"{key}:\n" + "\n".join(f'  - "[[{v}]]"' for v in all_vals)
        if re.search(rf"^{key}:", block, re.MULTILINE):
            # Replace the key's block: the key line + all the item lines that
            # follow it ("- ..." with or without indentation). An earlier
            # lookahead (?=^\S|\Z) failed with non-indented lists ("- ..." at
            # column 0) because that item line is already ^\S, cutting the
            # match before consuming any item and duplicating the block on
            # every apply.
            block = re.sub(rf"^{key}:[ \t]*\n(?:[ \t]*-.*\n?)*", yaml + "\n", block,
                           count=1, flags=re.MULTILINE)
        else:
            block = block.rstrip() + "\n" + yaml + "\n"
        return block

    if new_terms:
        fm_block = upsert_list(fm_block, "search_terms", existing_terms, new_terms)
    if new_dom:
        fm_block = upsert_list(fm_block, "domains", existing_dom, new_dom)
    # enriched date
    if re.search(r"^enriched:", fm_block, re.MULTILINE):
        fm_block = re.sub(r"^enriched:.*$", f"enriched: {TODAY}", fm_block, count=1, flags=re.MULTILINE)
    else:
        fm_block = fm_block.rstrip() + f"\nenriched: {TODAY}\n"

    # needs_enrichment: clear only if the note, with the terms already merged,
    # reaches the threshold by specific-resolvable terms (same criterion as st_specific).
    all_terms_after = list(dict.fromkeys(existing_terms + new_terms))  # + allow_new if applicable
    names_after = [clean(t) for t in all_terms_after]
    specific_after = sum(1 for n in names_after if n in reg["terms"] and n not in reg["hubs"])
    was_flagged = str(fm.get("needs_enrichment", "")).lower() == "true"
    cleared_needs_enrichment = False
    if was_flagged and specific_after >= needs_enrichment_threshold:
        if re.search(r"^needs_enrichment:", fm_block, re.MULTILINE):
            fm_block = re.sub(r"^needs_enrichment:.*$", "needs_enrichment: false",
                               fm_block, count=1, flags=re.MULTILINE)
            cleared_needs_enrichment = True

    new_text = text[:fm_match.start(1)] + fm_block + text[fm_match.end(1):]
    if not dry:
        p.write_text(new_text, encoding="utf-8")
    out({"ok": True, "dry_run": dry, "note": p.stem,
         "added_search_terms": new_terms, "added_domains": new_dom,
         "rejected_unresolved": rejected,
         "rejected_hub_domain_mismatch": hub_mismatch,
         "hint": ("terms without a note in Search Terms/: not written. "
                  "Create the term's note or repeat with --allow-new if it's "
                  "deliberate.") if rejected else None,
         "hint_hub": ("hierarchical hub whose parent domain the note doesn't declare: "
                      "not written. Add the parent domain to `domains` if the note "
                      "belongs to that domain, pick a specific term if it doesn't, or "
                      "repeat with --allow-hub-mismatch if it's deliberate."
                      ) if hub_mismatch else None,
         "enriched": TODAY,
         "specific_resolvable_after": specific_after,
         "needs_enrichment_threshold": needs_enrichment_threshold,
         "cleared_needs_enrichment": cleared_needs_enrichment,
         "needs_enrichment_still_true": was_flagged and not cleared_needs_enrichment})


# ------------------------------------------------------------ retrieval-gaps (fix 5.2)
# The Retrieval Log is meant to feed enrich. This is that Phase 0: it uses
# real evidence of use (what was searched, what came out, what was missing)
# instead of only the static count of search_terms.
RETRIEVAL_LOG = VAULT / "Resources" / "Retrieval Log.md"
GAPS_LEDGER = VAULT / "Resources" / "Vault Health" / "Retrieval Gaps Processed.jsonl"


def _rl_field(body, name):
    """Extracts a field '**Name** (optional): value' up to the next bold field or
    double blank line. Best-effort -- the log is prose markdown, not YAML."""
    m = re.search(rf"\*\*{name}\*\*\s*(?:\([^)]*\))?\s*:\s*(.+?)(?:\n\n|\n\*\*[A-Za-zÁÉÍÓÚñ¿]|\Z)",
                   body, re.S)
    return m.group(1).strip() if m else None


def _parse_retrieval_log():
    """Parses Resources/Retrieval Log.md into entries. Returns a list of dicts:
    header, query, dominio (detected domain), outcome, reformulation (bool),
    repeated_failure (bool), gaps_detectados (gaps detected), raw_excerpt (first
    ~1200 chars of the body, so the AI can read nuances the parser didn't
    capture -- e.g. a real gap added as a late correction to the same entry).
    Field names in the log (`Dominio detectado`, `Gaps detectados`) are
    identifiers written by open-brain-retrieve and are kept verbatim."""
    if not RETRIEVAL_LOG.exists():
        return []
    text = RETRIEVAL_LOG.read_text(encoding="utf-8", errors="ignore")
    # require a real date in the header: the log itself carries a schema block
    # with "## YYYY-MM-DD HH:MM — [intent: ...]" which, unless filtered, comes in
    # as a phantom entry (and shows up as a triage candidate).
    parts = re.split(r"(?m)^(## \d{4}-\d{2}-\d{2}.*)$", text)
    entries = []
    for header, body in zip(parts[1::2], parts[2::2]):
        outcome_raw = _rl_field(body, "Outcome")
        outcome = outcome_raw.split()[0].lower().strip(",.;") if outcome_raw else None
        reform_raw = _rl_field(body, r"Reformulation\?")
        entries.append({
            "header": header.strip(),
            "query": _rl_field(body, "Query"),
            "dominio": _rl_field(body, r"Dominio detectado"),
            "outcome": outcome,
            "reformulation": bool(reform_raw and re.match(r"(s[ií]|yes)", reform_raw, re.I)),
            "repeated_failure": "Repeated failure pattern" in body,
            "gaps_detectados": _rl_field(body, "Gaps detectados"),
            "raw_excerpt": body.strip()[:1200],
        })
    return entries


def _load_gaps_ledger():
    if not GAPS_LEDGER.exists():
        return {}
    rows = {}
    for line in GAPS_LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            rows[row["entry_key"]] = row
        except Exception:
            continue
    return rows


def cmd_retrieval_gaps(since, gate="both"):
    """Extracts candidates to triage from the Retrieval Log.

    Available gates:

      outcome  original behaviour: outcome partial/failure, reformulation, or a
               repeated-failure marker. **This gate tends to be dead in
               practice**: the Outcome is inferred with the Level A heuristic
               (">=1 note cited"), which is nearly tautological -> almost every
               entry is `success` and the gate returns 0 candidates. The
               harvester ends up gated by the saturated instrument it was meant
               to diagnose.

      gaps     fires when the `Gaps detectados` (gaps detected) field is filled
               and is not "ninguno"/"none". That's where the real signal gets
               written.

      both     union of the two (default).

    It does NOT classify: that's judgment. Expect most candidates to be
    content/product gaps and only a few indexing misses. The fourth category
    (`output_debt`) covers entries that don't ask to extract anything: they ask
    to publish something already compressed and unused (high times_retrieved
    with external_outputs = 0).
    """
    entries = _parse_retrieval_log()
    processed = _load_gaps_ledger()
    candidates = []
    for e in entries:
        if e["header"] in processed:
            continue
        m = re.match(r"##\s*(\d{4}-\d{2}-\d{2})", e["header"])
        if since and m and m.group(1) < since:
            continue
        by_outcome = (e["outcome"] in ("partial", "failure") or e["reformulation"]
                      or e["repeated_failure"])
        g = (e.get("gaps_detectados") or "").strip()
        by_gaps = bool(g) and not g.lower().startswith(("ninguno", "none"))
        hit = {"outcome": by_outcome, "gaps": by_gaps,
               "both": by_outcome or by_gaps}[gate]
        if hit:
            e = dict(e)
            e["trigger"] = ([] + (["outcome"] if by_outcome else [])
                            + (["gaps"] if by_gaps else []))
            candidates.append(e)
    out({"ok": True, "gate": gate, "total_entries": len(entries),
         "already_processed": len(processed),
         "candidates_count": len(candidates), "candidates": candidates,
         "triage_categories": ["indexing_fix", "content_gap", "output_debt",
                               "not_actionable"],
         "hint": ("indexing_fix: the note exists and search_terms don't cover the query's "
                  "angle -> generate candidate terms and apply via `apply` (normal Phases 2/3). "
                  "content_gap: no note answers it -> DON'T touch, report it for "
                  "ingest/[!gap] callout. output_debt: the note exists, gets retrieved and "
                  "produces no output (high times_retrieved, external_outputs 0) -> it's not "
                  "extraction work, it's writing work; it goes to Forced Promotion, not the "
                  "Inbox. not_actionable: product/feature gap, not a retrieval gap. After "
                  "deciding each candidate, record it with `mark-processed` so it doesn't repeat.")})


def cmd_mark_processed(payload):
    """Records already-triaged entries in the ledger (by exact header) so
    retrieval-gaps doesn't repeat them on the next run.
    payload: {"entries":[{"entry_key":"<header>","classification":"indexing_fix|content_gap|not_actionable","note":"..."}]}"""
    GAPS_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    rows_in = payload.get("entries", [])
    with GAPS_LEDGER.open("a", encoding="utf-8") as f:
        for r in rows_in:
            row = {"entry_key": r["entry_key"], "classification": r.get("classification", ""),
                   "note": r.get("note", ""), "date": TODAY}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    out({"ok": True, "marked": len(rows_in),
         "ledger": str(GAPS_LEDGER.relative_to(VAULT))})


# ------------------------------------------------------------ report
def cmd_report(payload, dry):
    d = VAULT / "Resources" / "Vault Health" / "Enrichment Reports"
    path = d / f"{TODAY}.md"
    md = payload.get("markdown", "")
    if not dry:
        d.mkdir(parents=True, exist_ok=True)
        prev = path.read_text(encoding="utf-8") + "\n\n---\n\n" if path.exists() else ""
        path.write_text(prev + md, encoding="utf-8")
    out({"ok": True, "dry_run": dry, "report": str(path.relative_to(VAULT))})


# ------------------------------------------------------------ split-orphans
def cmd_split_orphans(parent=None, only_under=True):
    """Notes that carry a hub with children but none of its children.

    Every crowding split turns the parent into a hub, and a hub doesn't count
    for L05. If the split only reclassifies the notes that were sampled, the
    rest silently lose a specific term. This command is the mandatory closing
    step of a split: run it with --parent and assign a child to each note it
    returns. only_under=True limits it to the ones that also ended up under
    MIN_SPECIFIC."""
    reg = term_registry()
    kids_of = {}
    for t in reg["terms"]:
        for sep in (" \u2014 ", " - "):
            if sep in t:
                kids_of.setdefault(t.split(sep)[0].strip(), set()).add(t)
    targets = {parent} if parent else set(kids_of)
    rows = []
    for folder in ("Literature Notes", "Permanent Notes", "Fleeting Notes"):
        for p, text in vs.iter_notes(folder):
            fm = vs.parse_fm(text)
            names = [clean(x) for x in vs.as_list(fm.get("search_terms"))]
            spec = sum(1 for n in names if n in reg["terms"] and n not in reg["hubs"])
            if only_under and spec >= MIN_SPECIFIC:
                continue
            for h in names:
                if h in targets and h in kids_of and not (kids_of[h] & set(names)):
                    rows.append({"note": p.stem, "folder": folder, "hub": h,
                                 "children": sorted(kids_of[h]), "specific": spec,
                                 "description": str(fm.get("description", ""))[:200]})
    out({"ok": True, "count": len(rows), "only_under": only_under, "orphans": rows})


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan"); s.add_argument("--threshold", type=int, default=MIN_SPECIFIC); s.add_argument("--folder", default=None)
    a = sub.add_parser("audit"); a.add_argument("note")
    sub.add_parser("crowding")
    sub.add_parser("registry")
    ap_ = sub.add_parser("apply"); ap_.add_argument("--json", required=True); ap_.add_argument("--dry-run", action="store_true")
    ap_.add_argument("--allow-new", action="store_true",
                     help="also write terms that don't exist in Search Terms/ (deliberate)")
    ap_.add_argument("--needs-enrichment-threshold", type=int, default=MIN_SPECIFIC,
                     help="specific-resolvable threshold to clear needs_enrichment (default MIN_SPECIFIC=3, same as scan and ln_lint L05)")
    ap_.add_argument("--allow-hub-mismatch", action="store_true",
                     help="also write hierarchical hubs whose parent domain the note doesn't declare (deliberate)")
    rt = sub.add_parser("resolve-terms",
                        help="classify proposed terms: exact / alias / near / free")
    rt.add_argument("--json", required=True,
                    help='{"terms": [...], "domains": [...]} -- domains is optional and enables the hub rule')
    rp = sub.add_parser("report"); rp.add_argument("--json", required=True); rp.add_argument("--dry-run", action="store_true")
    rg = sub.add_parser("retrieval-gaps"); rg.add_argument("--since", default=None,
                        help="only Retrieval Log entries dated >= YYYY-MM-DD")
    rg.add_argument("--gate", default="both", choices=["outcome", "gaps", "both"],
                    help="what triggers a candidate (default both; 'outcome' reproduces "
                         "the original behaviour, which usually returns 0)")
    so = sub.add_parser("split-orphans", help="notes with a hub but none of its children")
    so.add_argument("--parent", default=None); so.add_argument("--all", action="store_true",
                    help="include notes that already reach the minimum")
    mp = sub.add_parser("mark-processed"); mp.add_argument("--json", required=True)
    args = ap.parse_args()

    if args.cmd == "scan":
        cmd_scan(args.threshold, args.folder)
    elif args.cmd == "audit":
        cmd_audit(args.note)
    elif args.cmd == "crowding":
        cmd_crowding()
    elif args.cmd == "registry":
        cmd_registry()
    elif args.cmd == "apply":
        cmd_apply(json.loads(args.json), args.dry_run, getattr(args, "allow_new", False),
                  getattr(args, "needs_enrichment_threshold", MIN_SPECIFIC),
                  getattr(args, "allow_hub_mismatch", False))
    elif args.cmd == "resolve-terms":
        cmd_resolve_terms(json.loads(args.json))
    elif args.cmd == "report":
        cmd_report(json.loads(args.json), args.dry_run)
    elif args.cmd == "retrieval-gaps":
        cmd_retrieval_gaps(args.since, args.gate)
    elif args.cmd == "split-orphans":
        cmd_split_orphans(args.parent, not args.all)
    elif args.cmd == "mark-processed":
        cmd_mark_processed(json.loads(args.json))


if __name__ == "__main__":
    main()
