#!/usr/bin/env python3
"""
health-engine — deterministic engine for open-brain-health.

Autolink model: the plumbing of the mechanical checks lives here (no LLM).
Emits findings.json. The AI only prioritizes, writes the report and resolves the
judgment checks (semantic contradictions, mentor photos).

Usage:
    python3 health_check.py run            # run every check -> findings.json + stdout
    python3 health_check.py run --json     # raw JSON only, to stdout
    python3 health_check.py run --check 1,3,6   # subset
    python3 health_check.py run --stdout-only   # JSON to stdout WITHOUT rewriting findings.json
    python3 health_check.py self-test      # negative + positive fixtures for the status checks

Vault location: OPEN_BRAIN_VAULT (or VAULT_ROOT) when set; otherwise vault-scan
autodetects it by walking up from this file. The engines are expected to live in
the vault root (`<vault>/health-engine/`, `<vault>/vault-scan/`, `<vault>/engine/`),
or in the directory named by OPEN_BRAIN_ENGINES.

Optional configuration (environment variables, all optional):
    OPEN_BRAIN_INSTRUCTION_SURFACES   extra instruction files for check 26,
                                      ';'-separated, relative to the vault
    OPEN_BRAIN_ALWAYS_SURFACES        always-loaded instruction files for check 40,
                                      ','-separated (default: CLAUDE.md)
    OPEN_BRAIN_ON_DEMAND_SURFACES     on-demand instruction files for check 40
    OPEN_BRAIN_BINDING_RULES          file whose declared figures check 43 audits
    OPEN_BRAIN_NON_TAXONOMY           extra root items check 25 treats as machinery
    OPEN_BRAIN_ENDORSEMENT_CUTOFF     YYYY-MM-DD from which check 41 applies
                                      (also --endorsement-cutoff)
Checks that depend on optional engines or files that are not present skip
gracefully and say so in their finding.
"""

import argparse
import hashlib
import subprocess
import json
import os
import re
import sys
from datetime import datetime, timezone, date, timedelta
from pathlib import Path


# OPEN_BRAIN_VAULT overrides everything. vault-scan reads VAULT_ROOT, so mirror it
# there BEFORE importing it: both modules must agree on the same vault.
if os.environ.get("OPEN_BRAIN_VAULT"):
    os.environ["VAULT_ROOT"] = os.environ["OPEN_BRAIN_VAULT"]


# --- import the shared vault-scan library (single core) ---
def _bootstrap_vaultscan():
    envs = [os.environ.get(k) for k in ("OPEN_BRAIN_ENGINES", "OPEN_BRAIN_VAULT", "VAULT_ROOT")]
    bases = [Path(e) for e in envs if e] + [Path(__file__).resolve().parent,
                                            *Path(__file__).resolve().parents]
    for base in bases:
        for cand in [base / "vault-scan", base]:
            if (cand / "vaultscan.py").exists():
                sys.path.insert(0, str(cand)); return
    raise SystemExit("ERROR: cannot find vault-scan/vaultscan.py. Install the vault-scan "
                     "engine next to health-engine/ or set OPEN_BRAIN_ENGINES.")


_bootstrap_vaultscan()
import vaultscan as vs  # noqa: E402

# primitives = vault-scan (single core, no duplication)
VAULT = vs.VAULT
FM_RE = vs.FM_RE
WIKILINK_RE = vs.WIKILINK_RE
parse_fm = vs.parse_fm
notes = vs.iter_notes
days_since = vs.days_since
all_stems = vs.all_stems

NOW = datetime.now(timezone.utc)
TODAY = date.today()

# Pure read mode. Set by --stdout-only and honoured by EVERY check, not only by
# the findings.json write: check_26 keeps its own history, and without this guard
# a plain "give me the findings" from a reader would add a fake measurement to the
# series. A reader that mutates its source when queried is not a reader.
READ_ONLY = False


def to_int(v, default=0) -> int:
    try:
        return int(str(v).strip())
    except (ValueError, TypeError):
        return default


def _env_list(name):
    """';'-separated list from an environment variable (empty when unset)."""
    raw = os.environ.get(name, "")
    return [x.strip() for x in raw.split(";") if x.strip()]


# ============================================================
# CHECKS
# ============================================================

def check_1_orphans():
    """PNs with 0 outgoing links in the body (cheap orphan proxy)."""
    out = []
    for p, text in notes("Permanent Notes"):
        body = FM_RE.sub("", text)
        if not WIKILINK_RE.search(body):
            out.append(p.stem)
    return {"id": 1, "name": "Orphan Notes", "severity": "important",
            "count": len(out), "items": out[:30],
            "note": "PNs without outgoing wikilinks in the body. Check incoming links too."}


def check_3_stale():
    """Knowledge not revalidated for > 180d. Sorted by times_retrieved.

    Design notes. An earlier version was `last_validated > 180d AND
    confidence != high`, and it had three holes that together kept it at a
    permanent zero:

    1. **`confidence: high` exempted the note.** The extraction pipeline writes
       `high` by default, so it is not evidence of anything; an immunity that
       covers most notes is the rule under another name. The field that DOES
       record a human event is `endorsement_state`, so immunity now hangs on
       `endorsement_state: endorsed`.
    2. **A missing `last_validated` gave permanent immunity** (`days_since(None)`
       returned None: never stale). It now falls back to `created`, which always
       exists.
    3. **The threshold is a cliff, not a signal.** Notes written in one batch all
       cross 180 days on the same day; a critical check that jumps from 0 to
       hundreds overnight gets ignored wholesale. That is why the result carries
       `crossing_soon`: the wave is visible before it arrives.

    What it does NOT do: decide. Revalidating a note is the vault owner's call."""
    out, soon, endorsed_n, no_lv = [], {}, 0, 0
    for p, text in notes("Permanent Notes"):
        fm = parse_fm(text)
        lv = fm.get("last_validated")
        if not lv:
            no_lv += 1
        d = days_since(lv) if lv else days_since(fm.get("created"))
        if d is None:
            continue
        endorsed = (fm.get("endorsement_state") or "").lower() == "endorsed"
        if d > 180:
            if endorsed:
                endorsed_n += 1
                continue
            out.append({"note": p.stem, "days": d,
                        "times_retrieved": to_int(fm.get("times_retrieved")),
                        "date_used": "last_validated" if lv else "created",
                        "confidence": (fm.get("confidence") or "").lower()})
        else:
            weeks = (180 - d) // 7
            if weeks <= 8:
                soon[weeks] = soon.get(weeks, 0) + 1
    out.sort(key=lambda x: x["times_retrieved"], reverse=True)
    return {"id": 3, "name": "Stale Knowledge", "severity": "critical",
            "count": len(out), "items": out[:20],
            "exempted_by_endorsement": endorsed_n,
            "without_last_validated_use_created": no_lv,
            "crossing_soon": {f"in_{k}_weeks": v for k, v in sorted(soon.items())},
            "note": "Immunity comes from `endorsement_state: endorsed` (a human "
                    "event), not from `confidence`, which the pipeline sets high "
                    "by default. `crossing_soon` warns of the wave: the 180-day "
                    "threshold is a cliff for notes written in the same batch."}


def check_4_function_coverage():
    """Coverage of cognitive functions per domain.

    History: this used to be "Layer Gaps"; it broke when notes moved from a single
    `layer` to multi-label `features` and silently dropped out of the check
    registry while the documentation kept describing it.

    Severity `maintenance` ON PURPOSE: it is a signal to steer extraction, not a
    target to hit. When an earlier version did trigger action, it produced filler
    PNs in the flagged domains that were never retrieved. A domain with a low
    operative ratio means "you can talk about this and have trained nothing" —
    input for deciding what to read, not for fabricating notes.
    """
    rows, gaps = [], []
    for d in vs.list_domains():
        c = vs.function_coverage(d)
        if c["total_pns"] == 0:
            continue
        rows.append({"domain": d, "pns": c["total_pns"], "operative": c["operative"],
                     "declarative": c["declarative"], "operative_ratio": c["operative_ratio"],
                     "tagged_with_features": c["tagged_with_features"]})
        if c["total_pns"] >= 5 and c["operative_ratio"] < 0.34:
            gaps.append({"domain": d, "pns": c["total_pns"],
                         "operative_ratio": c["operative_ratio"],
                         "read": "plenty of mental models, little application/decision/diagnosis"})
    rows.sort(key=lambda r: r["operative_ratio"])
    tagged = sum(r["tagged_with_features"] for r in rows)
    return {"id": 4, "name": "Function Coverage by Domain", "severity": "maintenance",
            "count": len(gaps), "items": gaps[:15], "all_domains": rows,
            "note": f"PNs with `features` (v10): {tagged}. If 0, the check is reading "
                    "the legacy `layer` — migrating features onto PNs is still pending. "
                    "Gap threshold: operative ratio <0.34 with >=5 PNs. WARN, never BLOCK: "
                    "do not create notes just to fill layers."}


def check_5_inbox():
    """Inbox processed:false older than 30d. Sorted by rating desc."""
    out = []
    for p, text in notes("Inbox"):
        fm = parse_fm(text)
        proc = str(fm.get("processed", "")).lower()
        d = days_since(fm.get("created"))
        if proc == "false" and (d is None or d > 30):
            out.append({"note": p.stem, "days": d,
                        "rating": to_int(fm.get("rating"))})
    out.sort(key=lambda x: (x["rating"], x["days"] or 0), reverse=True)
    return {"id": 5, "name": "Unprocessed Inbox (>30d)", "severity": "maintenance",
            "count": len(out), "items": out[:15]}


def check_6_maturity():
    """Declared `maturity` vs the value derived from the counters (single source:
    vs.maturity()).

    An earlier version asked "is there maturity:active with <2 sources?", which
    accepted `active` as a valid state — a leftover the contract does not define.
    That check institutionalised the problem instead of detecting it: the
    seed -> growing -> evergreen ladder never promoted anyone because nothing
    computed it. Now `maturity` is derived and this check requires the declared
    value to match. It should always be 0; >0 means someone wrote the field by
    hand again (repair with `engine/maturity_migrate.py --apply`)."""
    res = vs.maturity_drift()
    out = res["drift"]
    return {"id": 6, "name": "Maturity Drift (declared != derived)", "severity": "important",
            "count": len(out), "items": out[:30],
            "note": f"derived today: {res['derived_counts']}. "
                    "maturity is a derived field (vs.maturity): seed / growing "
                    "(>=2 retrievals or >=1 output) / evergreen (>=5 retrievals AND >=1 published)."}


def check_7_frontmatter():
    """`type` present in PNs/LNs/Inbox; `layer` required only in PNs.

    v10 extraction (open-brain-extract) dropped the forced `layer` classification
    for Literature Notes (low metadata accuracy and high inter-layer ambiguity,
    documented in that skill). The current LN template has no `layer`; requiring
    it here would produce false positives on correct notes. `layer` is still
    mandatory in Permanent Notes.
    """
    missing = []
    for folder, need_layer in [("Permanent Notes", True), ("Literature Notes", False),
                               ("Inbox", False)]:
        for p, text in notes(folder):
            if folder == "Inbox" and p.relative_to(VAULT).parts[:2] == ("Inbox", "Raw"):
                continue
            fm = parse_fm(text)
            probs = []
            if not fm.get("type"):
                probs.append("type")
            if need_layer and not fm.get("layer"):
                probs.append("layer")
            if probs:
                missing.append({"note": p.stem, "folder": folder, "missing": probs})
    return {"id": 7, "name": "Frontmatter Compliance", "severity": "maintenance",
            "count": len(missing), "items": missing[:30]}


def check_8_broken_links():
    """Wikilinks in PNs that resolve to no stem in the vault."""
    stems = all_stems()
    broken = []
    for p, text in notes("Permanent Notes"):
        body = FM_RE.sub("", text)
        for m in WIKILINK_RE.finditer(body):
            target = m.group(1).split("/")[-1].strip()
            if target and target not in stems:
                broken.append({"in": p.stem, "target": target})
    return {"id": 8, "name": "Broken Links (PNs)", "severity": "maintenance",
            "count": len(broken), "items": broken[:30]}


def check_9_low_conf_pillars():
    """confidence:low AND times_retrieved>5 — the worst combination."""
    out = []
    for p, text in notes("Permanent Notes"):
        fm = parse_fm(text)
        if (fm.get("confidence") or "").lower() == "low" and to_int(fm.get("times_retrieved")) > 5:
            out.append({"note": p.stem, "times_retrieved": to_int(fm.get("times_retrieved"))})
    out.sort(key=lambda x: x["times_retrieved"], reverse=True)
    return {"id": 9, "name": "Low-Confidence Pillars", "severity": "critical",
            "count": len(out), "items": out}


def check_11_count_drift():
    """literature_notes_count in Dossiers vs actual files in Literature Notes/.

    Longest-prefix-wins: when two Dossiers declare prefixes where one is an
    initial substring of the other (e.g. "ABC" and "ABC26" — two distinct real
    codes, not a numeric continuation), a stem is assigned to the longest declared
    prefix that matches, never to both. Bug fixed: the earlier version with a
    (?![A-Za-z]) boundary counted "ABC26-01" as part of "ABC" because a digit is
    not a letter — inflating the "real" count of short-prefix Dossiers that another
    Dossier extends.
    """
    drift = []
    ln_stems = [p.stem for p in (VAULT / "Literature Notes").rglob("*.md")] \
        if (VAULT / "Literature Notes").exists() else []

    dossiers = list(notes("Dossiers"))
    declared_prefixes = set()
    for p, text in dossiers:
        fm = parse_fm(text)
        prefix = (fm.get("ln_prefix") or "").strip()
        if prefix:
            declared_prefixes.add(prefix)
    prefixes_by_len_desc = sorted(declared_prefixes, key=len, reverse=True)
    boundary_pat = {pref: re.compile(rf"^{re.escape(pref)}(?![A-Za-z])") for pref in prefixes_by_len_desc}

    def longest_match(stem):
        for pref in prefixes_by_len_desc:
            if boundary_pat[pref].match(stem):
                return pref
        return None

    real_counts = {}
    for s in ln_stems:
        m = longest_match(s)
        if m:
            real_counts[m] = real_counts.get(m, 0) + 1

    for p, text in dossiers:
        fm = parse_fm(text)
        if "literature_notes_count" not in fm:
            continue
        declared = to_int(fm.get("literature_notes_count"), -1)
        prefix = (fm.get("ln_prefix") or "").strip()
        if not prefix:
            continue
        real = real_counts.get(prefix, 0)
        if declared >= 0 and real != declared:
            drift.append({"dossier": p.stem, "declared": declared, "real": real,
                          "delta": real - declared})
    return {"id": 11, "name": "Count Drift (Dossiers)", "severity": "maintenance",
            "count": len(drift), "items": drift[:30],
            "note": "Only Dossiers with ln_prefix. Longest-prefix-wins among declared prefixes (see docstring). --fix-counts would reconcile it (not implemented here)."}


DUP_KEY_LINE_RE = re.compile(r'^([A-Za-z_][\w]*):', re.MULTILINE)
DOUBLE_BRACKET_RE = re.compile(r'\[\[\[\[|\]\]\]\]')


def check_22_frontmatter_integrity():
    """Structural integrity of the frontmatter YAML — not just field presence
    (that is check_7), but whether the block is well formed.

    Born from a real incident: enrich_engine.py's upsert_list had a regex
    (`^{key}:.*?(?=^\\S|\\Z)`) that failed on unindented lists — the lookahead
    fired before consuming any item, leaving the key effectively duplicated
    (new block inserted + old orphan block below, without its own `key:` line).
    check_7 would never have seen it: the field "existed". This check detects
    (a) top-level keys repeated within the same frontmatter block, and (b)
    double-bracket corruption `[[[[...]]]]` left by a known earlier bug of the
    same engine. Both are purely structural signals — no semantic judgment
    needed; they should always be 0.
    """
    dup_keys, double_bracket, unparseable, bad_enum = [], [], [], []
    # Closed enums: a typo in a state value does not break the YAML but makes
    # the note invisible to any consumer that filters on that value (e.g.
    # `provisionall` slipped past the endorsement gate unnoticed).
    ENUMS = {"endorsement_state": {"provisional", "endorsed", "unendorsed", "rejected"},
             "maturity": {"seed", "growing", "evergreen"},
             "type": None}
    try:
        import yaml as _yaml
    except ImportError:
        _yaml = None
    for folder in ["Literature Notes", "Permanent Notes", "Inbox", "Fleeting Notes",
                   "Search Terms", "Cases", "Domains", "Dossiers", "Mentors", "Ideas"]:
        for p, text in notes(folder):
            fm_m = FM_RE.match(text)
            if not fm_m:
                continue
            fm_block = fm_m.group(1)
            # (c) can a real YAML parser read the block? The proxies below look
            # for known shapes of corruption; this asks the only question that
            # matters to a consumer: does it parse? Without it, the check once
            # reported 0 while many notes were unreadable.
            if _yaml is not None:
                try:
                    _yaml.safe_load(fm_block)
                except Exception as e:
                    unparseable.append({"note": p.stem, "folder": folder,
                                        "error": str(e).split("\n")[0][:120]})
            keys = DUP_KEY_LINE_RE.findall(fm_block)
            seen = set()
            dupes = set()
            for k in keys:
                if k in seen:
                    dupes.add(k)
                seen.add(k)
            if dupes:
                dup_keys.append({"note": p.stem, "folder": folder,
                                  "keys": sorted(dupes)})
            if DOUBLE_BRACKET_RE.search(fm_block):
                double_bracket.append({"note": p.stem, "folder": folder})
            for key, legal in ENUMS.items():
                if legal is None:
                    continue
                m_enum = re.search(rf"^{key}:\s*([^\n#]+?)\s*$", fm_block, re.M)
                if m_enum:
                    val = m_enum.group(1).strip().strip('"\'')
                    if val and val not in legal:
                        bad_enum.append({"note": p.stem, "folder": folder,
                                         "field": key, "value": val[:40],
                                         "legal": sorted(legal)})
    count = len(dup_keys) + len(double_bracket) + len(unparseable) + len(bad_enum)
    return {"id": 22, "name": "Frontmatter YAML Integrity", "severity": "critical" if count else "maintenance",
            "count": count,
            "dup_keys": dup_keys[:30], "dup_keys_total": len(dup_keys),
            "double_bracket": double_bracket[:30], "double_bracket_total": len(double_bracket),
            "unparseable": unparseable[:30], "unparseable_total": len(unparseable),
            "bad_enum": bad_enum[:30], "bad_enum_total": len(bad_enum),
            "note": "Must always be 0. bad_enum = value outside the legal enum "
                    "(endorsement_state, maturity): does not break the YAML but makes the "
                    "note invisible to the filter that uses that field. dup_keys = same "
                    "frontmatter key repeated (symptom of a partial/corrupt write). "
                    "unparseable = the frontmatter fails yaml.safe_load: the note is "
                    "invisible to any consumer that parses YAML. double_bracket = "
                    "'[[[[X]]]]' produced by writing a value already wrapped in [[ ]] "
                    "through enrich_engine apply (the tool wraps on its own). If count>0, "
                    "repair BEFORE running any further enrich batch — the originating "
                    "bug may still be active."}


def _is_backup_copy(path) -> bool:
    """A backup copy inside Archive/ is not an archived note.

    Recurring incident: a backup of `Permanent Notes/` copied to
    `Archive/_backup-*/` before a mass write makes EVERY live note linking to a
    PN count as a back-link to Archive — hundreds of false findings. The
    convention is to keep backups in `engine/backups-*/`, but the convention alone
    already failed twice: this makes it structural.
    """
    return any(part.startswith("_backup") for part in path.parts)


def check_13_ghosts():
    """0-byte ghost files outside Archive + live back-links to Archive/."""
    ghosts = [str(p.relative_to(VAULT)) for p in VAULT.rglob("*.md")
              if p.stat().st_size == 0 and "Archive" not in p.parts and "_to_delete" not in p.parts]
    archived = {p.stem for p in (VAULT / "Archive").rglob("*.md")
                if not _is_backup_copy(p)} \
        if (VAULT / "Archive").exists() else set()
    backlinks = {}
    if archived:
        for p in VAULT.rglob("*.md"):
            if "Archive" in p.parts or "_to_delete" in p.parts:
                continue
            try:
                body = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for m in WIKILINK_RE.finditer(body):
                t = m.group(1).split("/")[-1].strip()
                if t in archived:
                    backlinks[t] = backlinks.get(t, 0) + 1
    top = sorted(backlinks.items(), key=lambda x: -x[1])[:10]
    return {"id": 13, "name": "Ghosts & Archive Back-links", "severity": "important",
            "count": len(ghosts) + len(backlinks),
            "ghost_files": ghosts,
            "archive_backlinks_top": [{"target": t, "refs": n} for t, n in top],
            "archive_backlink_targets": len(backlinks)}


SEARCH_TERMS_FIELD_RE = re.compile(r'^search_terms:(.*?)(?=^\S|\Z)', re.MULTILINE | re.DOTALL)


def check_16_crowding():
    """Saturated Search Terms. Delegates to `vs.crowding()` — a single
    implementation shared with enrich (there used to be two, and they diverged:
    health and enrich reported very different red counts on the same vault).

    Two signals, not one:
    - `tag_count`: occurrences in the frontmatter field `search_terms:`. The real
      over-tagging signal — the one that competes for retrieval precision.
    - `mention_count`: any wikilink to the term in the note (incl. `search_context:`
      and "## Typed Connections"). Hub connectivity, high by design for umbrella
      terms. Not crowding.

    Double threshold: hub and leaf_of_hub against 150, `flat` against 20 — see the
    docstring of `vs.crowding()`. `actionable` = already has a more specific sibling
    in the registry (mechanical redistribution); `atomic` = splitting it would need
    new taxonomy, which is the vault owner's decision.
    """
    c = vs.crowding()
    tag_red = c["red"]
    return {"id": 16, "name": "Search Term Crowding", "severity": "important",
            "count": len(tag_red),
            "thresholds": c["thresholds"],
            "tag_red": [{"term": e["term"], "tag_count": e["tag_count"],
                         "tier": e["tier"], "threshold": e["threshold"]}
                        for e in tag_red],
            "tag_red_actionable": c["red_actionable"],
            "tag_red_atomic_count": len(c["red_atomic"]),
            "tag_red_atomic": c["red_atomic"][:20],
            "yellow_count": len(c["yellow"]),
            "yellow_top": c["yellow"][:10],
            "green_count": c["green_count"],
            "mention_top": [{"term": t, "mentions": n} for t, n in
                            sorted(c["mention_counts"].items(), key=lambda x: -x[1])[:10]],
            "note": "count/tag_red = frontmatter field search_terms with double threshold "
                    "hub(150)/flat(20) — the real over-tagging signal. mention_top = "
                    "wikilinks anywhere in the note (hub connectivity, expected for umbrella "
                    "terms, NOT crowding). tag_red_actionable = has >=1 sibling ALREADY "
                    "in the registry (cross-tag without inventing taxonomy). "
                    "tag_red_atomic = has no sibling — needs the vault owner's decision."}


def check_17_stale_claims():
    """claim_date > 180d without superseded_by. PNs without claim_date are counted apart."""
    with_claim, without = [], 0
    for p, text in notes("Permanent Notes"):
        fm = parse_fm(text)
        cd = fm.get("claim_date")
        if not cd:
            without += 1
            continue
        d = days_since(cd)
        if d is not None and d > 180 and not fm.get("superseded_by"):
            with_claim.append({"note": p.stem, "days": d,
                               "times_retrieved": to_int(fm.get("times_retrieved"))})
    with_claim.sort(key=lambda x: x["times_retrieved"], reverse=True)
    return {"id": 17, "name": "Stale Claims (Epistemology)", "severity": "important",
            "count": len(with_claim), "items": with_claim[:15],
            "pns_without_claim_date": without,
            "note": "Most PNs have no claim_date — consider migrating it in promote."}


CONNECTOR_BLOCK_RE = re.compile(
    r'^\s*>?\s*\[!claude\][^\n]*\n((?:^\s*>?.*\n?)*?)(?=\n\s*\n|\n##|\Z)',
    re.MULTILINE)

# "Strong" relation verbs — they differentiate the TYPE of connection
# (contradicts, extends, depends on...). The "weak" ones are the archetype of
# generic synthesis that Chen/Zhao/Cohan 2026 measure as an LLM homogenisation
# bias: models converge on "integrate/relate" 34.2% of the time vs 2.35% in human
# ideation. A connector that only says "related to" carries no signal about HOW
# the notes relate — the same pattern the paper documents. Spanish forms are kept
# alongside the English ones so bilingual vaults are measured correctly.
CONNECTOR_WEAK_RE = re.compile(
    r'relacionad[oa]\s+con|conecta(?:da)?\s+con|related\s+to|connects?\s+to|'
    r'vinculad[oa]\s+con|parecid[oa]\s+a|similar\s+a',
    re.IGNORECASE)
CONNECTOR_STRONG_RE = re.compile(
    r'contradice|refuta|extiende|ejemplifica|depende\s+de|aplica\s+a|'
    r'operacionaliza|alimenta|refuerza|contrasta\s+con|diverge\s+de|'
    r'cuestiona|matiza|reemplaza|desacopla|sintetiza\s+desde|cross[- ]domain|'
    r'converge\s+con|confirma\s+(?:un\s+)?patrón|'
    # English equivalents — many LNs from English sources keep body + connectors
    # in English. Without these, English notes with genuinely differentiated
    # verbs were mislabeled "weak".
    r'contradicts?|refutes?|extends?|exemplifies|depends?\s+on|applies\s+to|'
    r'operationalizes?|feeds|informs?|reinforces?|contrasts?\s+with|'
    r'diverges?\s+from|questions?|qualifies|replaces?|decouples?|'
    r'synthesizes?\s+from|converges?\s+with|confirms?\s+a?\s*pattern',
    re.IGNORECASE)


def check_21_connector_diversity():
    """Detects whether the vault's [!claude] Connectors callouts are mostly of the
    'related to / connects to' kind (no differentiation of the relation type)
    instead of verbs that discriminate (contradicts, extends, depends on...).
    Not a semantic content check — a cheap lexical proxy, like the engine's other
    checks. The AI interprets the result in Phase 2 (judgment), the same way
    open-brain-graph does with autolink's typed edges."""
    total, weak_only = 0, []
    for p, text in notes("Literature Notes"):
        body = FM_RE.sub("", text)
        for m in CONNECTOR_BLOCK_RE.finditer(body):
            block = m.group(1)
            if not block.strip():
                continue
            total += 1
            has_strong = bool(CONNECTOR_STRONG_RE.search(block))
            has_weak = bool(CONNECTOR_WEAK_RE.search(block))
            if has_weak and not has_strong:
                weak_only.append(p.stem)
            break  # only one callout per note counts
    ratio = (len(weak_only) / total) if total else 0.0
    severity = "important" if ratio > 0.6 else "maintenance"
    return {"id": 21, "name": "Connector Verb Diversity", "severity": severity,
            "count": len(weak_only), "total_connectors_scanned": total,
            "weak_ratio": round(ratio, 2), "items": weak_only[:30],
            "note": "Lexical proxy: connectors that only use 'related to / "
                    "connects to' without a verb that differentiates the relation "
                    "type (contradicts, extends, depends on...). Inspired by "
                    "Chen/Zhao/Cohan 2026: LLMs converge on 'integrate/relate' far "
                    "more than humans. Severity 'important' if >60% of the scanned "
                    "connectors are homogeneous."}


GRAPH_F = VAULT / "autolink" / "graph.jsonl"
ENTITIES_F = VAULT / "autolink" / "entities.json"
# Same types as `autolink/query.py contradictions` (autolink edge types are kept
# in Spanish: `contradice` = contradicts, `refuta` = refutes). `refina` (refines)
# is NOT included: it sharpens a claim, it does not deny it — including it would
# inflate the count with relations that are not tension.
TENSION_TYPES = {"contradice", "refuta"}


def check_12_contradiction_candidates():
    """DECLARED tensions, read from the typed graph.

    It used to return a fixed `count: 0` and leave all the work to the AI:
    "list the PNs by domain and compare claims". With hundreds of PNs that is a
    manual pass of hundreds of reads, while `autolink/graph.jsonl` already held
    `contradice`/`refuta` edges extracted deterministically from the verbs in the
    body. The work was done twice and the cheap version was the one not used.

    WHAT THIS CHECK SEES AND WHAT IT DOES NOT — it matters so nothing is assumed
    covered that is not. The graph detects **declared** tensions: someone wrote
    "Contradicts [[X]]" or a `[!contradiction]` in the body. It is blind to the
    **undeclared** contradiction, which is exactly the dangerous one: two PNs that
    deny each other without either mentioning the other. So the AI's judgment is
    still needed, but its task changes: it no longer enumerates; it (a) verifies
    that each declared pair is a real contradiction at the decision level, and (b)
    looks for undeclared ones among notes that share a search_term and do not cite
    each other.

    Skill exclusion rules applied here: self-edges are dropped and unordered pairs
    are deduplicated; pairs with no search_term and no domain in common do not
    count in `count` (they go to `no_overlap`), because a tension between unrelated
    domains with no shared term is almost always a false positive of the verb, not
    a real clash.
    """
    if not GRAPH_F.exists():
        return {"id": 12, "name": "Contradiction Scan", "severity": "important",
                "count": 0, "items": [], "graph_missing": True,
                "note": "No `autolink/graph.jsonl`: this check cannot see anything. "
                        "Run `open-brain-autolink` before accepting the absence of "
                        "contradictions — a 0 here without a graph is not a signal, it is a gap."}

    graph_age = (TODAY - date.fromtimestamp(GRAPH_F.stat().st_mtime)).days
    try:
        ents = json.loads(ENTITIES_F.read_text(encoding="utf-8")) if ENTITIES_F.exists() else {}
    except Exception:
        ents = {}

    def info(slug):
        e = ents.get(slug)
        return e if isinstance(e, dict) else {}

    seen, pairs = set(), []
    with GRAPH_F.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("type") not in TENSION_TYPES:
                continue
            a, b = e.get("from"), e.get("to")
            if not a or not b or a == b:
                continue
            key = tuple(sorted((a, b)))
            if key in seen:
                continue
            seen.add(key)
            pairs.append((a, b, e.get("type"), e.get("from_title"), e.get("to_title")))

    def terms_and_domains(slug):
        path = info(slug).get("path")
        if not path:
            return set(), set()
        f = VAULT / path
        if not f.exists():
            return set(), set()
        try:
            fm = parse_fm(f.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            return set(), set()
        def clean(vals):
            out = set()
            for v in vs.as_list(vals):
                out.add(re.sub(r"^\[\[|\]\]$", "", str(v)).split("|")[0].strip())
            return {x for x in out if x}
        return clean(fm.get("search_terms")), clean(fm.get("domains"))

    actionable, no_overlap, non_pn = [], [], 0
    for a, b, typ, ta, tb in pairs:
        type_a, type_b = info(a).get("type"), info(b).get("type")
        if type_a != "permanent" or type_b != "permanent":
            non_pn += 1
            continue
        sa, da = terms_and_domains(a)
        sb, db = terms_and_domains(b)
        shared_t, shared_d = sorted(sa & sb), sorted(da & db)
        rec = {"a": ta or a, "b": tb or b, "type": typ,
               # `domain_only` = share a domain but no search_term. They count,
               # because they are not a crossing between unrelated domains, but a
               # broad domain ("Product Management") is much weaker evidence than
               # a concrete term: the AI should verify these first.
               "evidence": "search_term" if shared_t else "domain_only",
               "shared_search_terms": shared_t[:4], "shared_domains": shared_d[:3]}
        (actionable if (shared_t or shared_d) else no_overlap).append(rec)

    severity = "judgment" if graph_age <= 7 else "important"
    return {"id": 12, "name": "Contradiction Scan", "severity": severity,
            "count": len(actionable), "items": actionable[:30],
            "graph_age_days": graph_age,
            "tension_edges_total": len(pairs),
            "by_evidence": {"search_term": sum(1 for r in actionable if r["evidence"] == "search_term"),
                            "domain_only": sum(1 for r in actionable if r["evidence"] == "domain_only")},
            "no_overlap_count": len(no_overlap), "no_overlap": no_overlap[:10],
            "non_pn_pairs": non_pn,
            "note": "PN pairs with a `contradice`/`refuta` (contradicts/refutes) edge in the "
                    "typed graph, deduplicated and filtered to those sharing a search_term or "
                    f"domain. Graph is {graph_age} day(s) old: if more than 7, regenerate with "
                    "`open-brain-autolink` before trusting the count — an old graph "
                    "reports another vault's tensions. `no_overlap` are pairs with no "
                    "shared term or domain (probable verb false positive; not counted). "
                    "`non_pn_pairs` includes LNs and Cases: useful, but outside this check's scope. "
                    "THE AI'S JUDGMENT IS STILL NEEDED and its task changed: verify that "
                    "each pair is a contradiction at the decision level, and look for the "
                    "UNDECLARED ones — the graph only sees those someone already wrote."}


def check_23_orphans_all():
    """Orphans across the WHOLE vault, classified. Complements check 1, which only
    looks at Permanent Notes — right scope, practical blindness: a vault can hold
    thousands of notes without a single wikilink while check 1 reports 0.
    Only the `knowledge` class counts as a finding; the rest is reported so that
    graph noise is not mistaken for a problem again."""
    b = vs.orphans_all()
    k = b["knowledge"]
    by_folder = {}
    for rel in k:
        f = rel.split("/")[0]
        by_folder[f] = by_folder.get(f, 0) + 1
    return {"id": 23, "name": "Orphan Notes (vault-wide)", "severity": "important",
            "count": len(k), "items": k[:40],
            "breakdown": {"knowledge": len(k), "capture": len(b.get("capture", [])),
                          "terminal": len(b["terminal"]),
                          "infra": len(b["infra"]), "subvault": len(b["subvault"])},
            "by_folder": dict(sorted(by_folder.items(), key=lambda x: -x[1])),
            "note": "Notes with NO wikilink at all. Only `knowledge` is actionable: "
                    "knowledge that should be woven into the network and is not. "
                    "`capture` are input buffers (Inbox, Ideas, Fleeting): being "
                    "unwoven there is the default state, not debt. `terminal` are "
                    "output artifacts (recaps, updates, handoffs), `infra` are "
                    "templates/skills/reference, `subvault` are paths listed in "
                    "vault-scan's SUBVAULT_PREFIXES, which follow their own contract "
                    "(e.g. plain-text search_terms)."}


def check_24_unlinked_search_terms():
    """Notes whose `search_terms` are plain text instead of wikilinks.

    A term without brackets passes any count threshold and adds not a single edge
    to the graph: enrich considers the note indexed and the note stays invisible
    to retrieve. Sub-vaults (vault-scan's SUBVAULT_PREFIXES) that use plain text by
    their own contract are kept apart so they do not drown the main vault's signal.
    """
    d = vs.unlinked_search_terms()
    main = d["main"]
    return {"id": 24, "name": "Search Terms Without Wikilink", "severity": "important",
            "count": len(main), "items": main[:30],
            "subvault_count": len(d["subvault"]),
            "note": "A plain-text search_term creates no retrieval: it does not link. "
                    "`count` excludes sub-vaults with their own contract "
                    f"({len(d['subvault'])} notes) so they do not drown the main vault's signal. "
                    "The enrich threshold counts terms, not links — that is why this check exists."}


# --- check 25: taxonomy adherence (FSM, Zhou et al. 2026) ---------------------
# Deterministic proxies of B1-B4 + combined tree. NON_TAXONOMY declares which
# root items are machinery, not part of the knowledge tree.

NON_TAXONOMY = {
    # Open Brain engines (installed at the vault root).
    "autolink", "course-engine", "engine", "enrich-engine", "eval-engine",
    "health-engine", "practice-log-engine", "synthesize-engine", "vault-scan",
    "retrieval-eval", "mentor-engine", "skill-sources",
    # Machinery and tooling folders.
    "Templates", "Meta", ".obsidian", ".git", ".claude",
    # Deferred trash (nothing is hard-deleted).
    "_to_delete",
    # Output of engine/practice_log.py, not knowledge tree.
    "Practice Log",
    # Add your own machinery folders through OPEN_BRAIN_NON_TAXONOMY
    # (';'-separated) instead of editing this list.
} | set(_env_list("OPEN_BRAIN_NON_TAXONOMY"))

# Root files that are entry points on purpose, not unclassified siblings.
ROOT_ENTRY_FILES = {"Home.md", "CLAUDE.md", "AGENTS.md", "README.md", "INSTALL.md"}

KNOWLEDGE_FOLDERS = {
    "Literature Notes", "Permanent Notes", "Search Terms", "Mentors", "Sources",
    "Cases", "Domains", "Dossiers", "Fleeting Notes", "Inbox", "Ideas",
    "Manuscripts", "Playbooks", "Projects", "Published", "Research",
    "Resources", "Skills", "Tasks", "Areas", "Archive",
}


def _norm_label(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[áàä]", "a", s); s = re.sub(r"[éèë]", "e", s)
    s = re.sub(r"[íìï]", "i", s); s = re.sub(r"[óòö]", "o", s)
    s = re.sub(r"[úùü]", "u", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def _mentor_metrics():
    """Mentor metrics from an optional mentor-engine, without reimplementing them here.

    The definition of distilled/canon/undistilled lives in a single place on
    purpose: two implementations of the same metric diverge and nobody notices
    until two tools report different figures for the same vault. mentor-engine is
    NOT shipped with Open Brain: when `<vault>/mentor-engine/mentor_metrics.py` is
    absent this returns None and the dependent checks skip that part.
    """
    engine = VAULT / "mentor-engine" / "mentor_metrics.py"
    if not engine.exists():
        return None
    try:
        out = subprocess.run([sys.executable, str(engine), "run", "--json"],
                             capture_output=True, text=True, timeout=120,
                             env={**os.environ, "VAULT_ROOT": str(VAULT),
                                  "OPEN_BRAIN_VAULT": str(VAULT)})
        if out.returncode != 0:
            return None
        return json.loads(out.stdout)
    except Exception:
        return None


def check_31_mentor_attribution():
    """Literature Notes without an identifiable mentor.

    An LN without `mentor:` (nor a `source:` with a wikilink) counts for nobody: it
    adds nothing to the mentor's metrics, does not show up when asking who you
    learned X from, and its knowledge is orphaned of authorship. It is the ceiling
    of every mentor metric. The dangling-mentor part needs the optional
    mentor-engine; without it only the unattributed LNs are counted.
    """
    no_mentor = []
    for path, text in vs.iter_notes("Literature Notes"):
        fm = vs.parse_fm(text)
        has = re.search(r"\[\[", str(fm.get("mentor") or "")) or re.search(r"\[\[", str(fm.get("source") or ""))
        if not has:
            no_mentor.append(str(path.relative_to(VAULT)))
    # Plus the ones that do point to someone, but to someone who no longer exists
    # as a note. They grow when Mentors/ is cleaned up, which is healthy, but they
    # leave the knowledge without an owner.
    data = _mentor_metrics()
    dangling = (data or {}).get("dangling", [])
    total_dangling = sum(d["lns"] for d in dangling)
    top = ", ".join(f"{d['name']} ({d['lns']})" for d in dangling[:6])
    org_lns = ((data or {}).get("totals") or {}).get("lnsOrganization", 0)
    detail = (f"{len(no_mentor)} without attribution and {total_dangling} pointing to a mentor "
              f"that does not exist as a note ({len(dangling)} names). Largest: {top}. "
              f"Separately, {org_lns} LNs attributed to organizations in Sources/Organizations/ "
              f"(not counted as broken).")
    if data is None:
        detail = (f"{len(no_mentor)} without attribution. Dangling-mentor detection skipped: "
                  "optional mentor-engine not installed.")
    return {"id": 31, "name": "Literature Notes Without Mentor", "severity": "important",
            "count": len(no_mentor) + total_dangling,
            "items": sorted(no_mentor)[:15] + [f"[[{d['name']}]] — {d['lns']} LN without a mentor note" for d in dangling[:15]],
            "detail": detail}


def check_32_undistilled_mentors():
    """Mentors read in volume and never distilled into criteria.

    20 LNs or more and no Permanent Note citing them. Not a vault error: it is a
    work queue for promote, and the most honest signal of accumulated reading
    without conversion. Categories that are not mentors (Unknown and similar) are
    listed alongside because they top any volume ordering and confuse the
    diagnosis. Requires the optional mentor-engine; skipped without it.
    """
    data = _mentor_metrics()
    if not data:
        return {"id": 32, "name": "Undistilled Mentors", "severity": "info", "count": 0,
                "items": [], "skipped": True,
                "detail": "Optional mentor-engine not installed: check skipped."}
    pending = [r for r in data.get("mentors", []) if r.get("undistilled")]
    pending.sort(key=lambda r: -r["lns"])
    lns = sum(r["lns"] for r in pending)
    cats = ", ".join(f"{c['name']} ({c['lns']} LN)" for c in data.get("categories", []))
    return {"id": 32, "name": "Undistilled Mentors", "severity": "important",
            "count": len(pending),
            "items": [f"{r['name']} — {r['lns']} LN, 0 PN" for r in pending[:30]],
            "detail": f"{lns} readings that never became criteria. Left out of the list for not being mentors: {cats}."}


def check_25_taxonomy_adherence():
    """Adherence to the taxonomy contract P1-P5 (proxies B1-B4 from Zhou et al.).

    Measures the tree, not the notes: (a) unclassified root items (P2),
    (b) crowded flat folders without a search surface (P1/P3/P5),
    (c) confusable siblings — names that collide when normalised (B1),
    (d) `description:` coverage in frontmatter (the signal an agent sees without
    opening the file), (e) shape of the combined folders+headings tree.
    The other checks look at note health; this one looks at what the paper says
    erodes silently."""
    findings = {}

    # (a) root: unrelated siblings (P2)
    root_items = [p.name for p in VAULT.iterdir() if not p.name.startswith(".")]
    unclassified = [n for n in root_items
                    if n not in NON_TAXONOMY and n not in KNOWLEDGE_FOLDERS
                    # Entry points are at the root on purpose, not unclassified siblings.
                    and n not in ROOT_ENTRY_FILES]
    findings["root_unclassified"] = sorted(unclassified)

    # (b) crowded flat folders + (c) collisions + (d) description coverage
    crowded, collisions_sample, desc_cov = [], [], {}
    total_collisions = 0
    for folder in sorted(KNOWLEDGE_FOLDERS):
        base = VAULT / folder
        if not base.exists():
            continue
        mds = list(base.rglob("*.md"))
        if not mds:
            continue
        subdirs = sum(1 for p in base.iterdir() if p.is_dir())
        with_desc = 0
        seen = {}
        for p in mds:
            try:
                head = p.read_text(encoding="utf-8", errors="ignore")[:6000]
            except OSError:
                head = ""
            # description lives in the frontmatter (which can be long because of
            # search_context); search only inside the delimited block
            fm_m = re.match(r"^---\n(.*?)\n---", head, re.S)
            # The KEY existing is not enough: the open-brain-extract template ships
            # `description: ""`, so a key-only check would report 100% coverage on
            # a vault full of empty descriptions. A non-empty value is required.
            if fm_m and re.search(r'^description:\s*["\']?\s*\S', fm_m.group(1), re.M):
                _v = re.search(r'^description:\s*(.*)$', fm_m.group(1), re.M).group(1)
                if _v.strip().strip('"\'') :
                    with_desc += 1
            # B1 is between siblings: the key includes the parent directory
            key = (str(p.parent), _norm_label(p.stem))
            if key in seen:
                total_collisions += 1
                if len(collisions_sample) < 15:
                    collisions_sample.append(f"{folder}: {seen[key]} ~ {p.stem}")
            else:
                seen[key] = p.stem
        desc_cov[folder] = round(100 * with_desc / len(mds), 1)
        if len(mds) > 500 and subdirs == 0:
            crowded.append({"folder": folder, "files": len(mds),
                            "description_pct": desc_cov[folder]})

    # (e) combined tree: folder depth + headings (sample per folder)
    tree = {}
    for folder in ("Literature Notes", "Permanent Notes"):
        base = VAULT / folder
        if not base.exists():
            continue
        max_h = 0
        for p in list(base.rglob("*.md"))[:2000]:
            try:
                body = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            hs = re.findall(r"^(#{1,6}) ", body, re.M)
            if hs:
                max_h = max(max_h, max(len(h) for h in hs))
        depth_dirs = max((len(p.relative_to(base).parts) for p in base.rglob("*.md")), default=1)
        tree[folder] = {"dir_depth": depth_dirs, "max_heading_depth": max_h,
                        "combined_depth": depth_dirs + max_h}
    findings["combined_tree"] = tree

    # (d) is a CUT, not narration. Description coverage used to be printed but
    # did not enter `count` ("tolerable with high description"), which describes
    # the problem instead of flagging it. Declared floor: 90% per knowledge folder.
    # A threshold without a number is not a cut.
    # The floor applies ONLY where the contract asks for `description`: the folders
    # whose templates carry it. Capture buffers (Inbox, Ideas, Fleeting) and
    # terminal artifacts (Manuscripts, Published, Projects, Research) do not carry
    # it by design, and including them would produce findings from day one — which
    # is how people learn to ignore a check.
    DESC_FLOOR = 90.0
    DESC_REQUIRED = {"Literature Notes", "Permanent Notes", "Cases", "Dossiers",
                     "Domains", "Mentors", "Search Terms"}
    desc_below = [{"folder": f, "pct": v, "floor": DESC_FLOOR}
                  for f, v in sorted(desc_cov.items())
                  if f in DESC_REQUIRED and v < DESC_FLOOR]

    count = (len(unclassified) + len(crowded) + total_collisions
             + len(desc_below))
    return {"id": 25, "name": "Taxonomy Adherence (P1-P5)", "severity": "important",
            "description_below_floor": desc_below,
            "count": count,
            "root_unclassified": findings["root_unclassified"][:20],
            "crowded_flat_folders": crowded,
            "confusable_siblings": {"total": total_collisions, "sample": collisions_sample},
            "description_coverage_pct": desc_cov,
            "combined_tree": findings["combined_tree"],
            "note": "Proxies of the P1-P5 contract (FSM, Zhou et al. 2026). `count` = "
                    "unclassified root items + flat folders >500 without substructure + "
                    "confusable siblings + folders below the description floor. "
                    "Description coverage is the search surface an agent sees before "
                    "opening the note, and it is a 90% cut, not a tolerance: "
                    "`description: \"\"` does not count as covered. Declare your own "
                    "machinery folders with OPEN_BRAIN_NON_TAXONOMY."}


def check_46_description_claim():
    """Quality of `description` as a CLAIM, not as a label.

    Why it exists. No other check looks at what a `description` says; `check_25`
    only counts whether it exists. And the field is not decorative: the template
    calls it the dominant retrieval signal, and the Careo gate requires reading it
    to cite what a note claims. A description that states the TOPIC ("about memory
    in agents") serves neither purpose: it does not discriminate in a sweep and it
    cannot be cited.

    Three criteria, all mechanical:
      (a) starts with "sobre "/"about " — that is an announced topic, not a claim
      (b) fewer than 8 words — no room for a statement with subject and predicate
      (c) repeated in more than one note — a description valid for two notes
          distinguishes neither; it is a label under another name

    What it does NOT implement, and why. A fourth criterion would be "no verb".
    Any mechanical verb detector on free bilingual text produces more false
    positives than findings, and a check with more noise than signal trains people
    to ignore it. Left out on purpose, and said so."""
    from collections import defaultdict as _dd
    FOLDERS = ("Literature Notes", "Permanent Notes", "Cases", "Dossiers")
    topic, short = [], []
    by_text = _dd(list)
    total = 0
    for folder in FOLDERS:
        base = VAULT / folder
        if not base.exists():
            continue
        for p in base.rglob("*.md"):
            try:
                head = p.read_text(encoding="utf-8", errors="ignore")[:6000]
            except OSError:
                continue
            fm_m = re.match(r"^---\n(.*?)\n---", head, re.S)
            if not fm_m:
                continue
            m = re.search(r'^description:\s*(.*)$', fm_m.group(1), re.M)
            if not m:
                continue
            val = m.group(1).strip().strip('"').strip("'").strip()
            if not val:
                continue           # empty: check_25 counts it as coverage
            total += 1
            low = val.lower()
            if low.startswith("sobre ") or low.startswith("about "):
                topic.append(f"{folder}/{p.stem[:50]}")
            if len(val.split()) < 8:
                short.append(f"{folder}/{p.stem[:46]} — «{val[:40]}»")
            by_text[low].append(p.stem)

    repeated = [{"description": k[:70], "notes": len(v), "example": v[0][:50]}
                for k, v in by_text.items() if len(v) > 1]
    repeated.sort(key=lambda r: -r["notes"])
    n_rep = sum(r["notes"] for r in repeated)

    count = len(topic) + len(short) + n_rep
    return {"id": 46, "name": "Description as Claim, Not Label",
            "severity": "important", "count": count,
            "descriptions_evaluated": total,
            "topic_not_claim": {"total": len(topic), "sample": sorted(topic)[:12]},
            "under_8_words": {"total": len(short), "sample": sorted(short)[:12]},
            "repeated": {"groups": len(repeated), "notes": n_rep,
                         "sample": repeated[:8]},
            "note": "Only looks at NON-empty descriptions: coverage belongs to check_25. "
                    "The 'no verb' criterion is left out on purpose — no mechanical verb "
                    "detector on bilingual text has better signal than noise."}


# Instruction surfaces measured by check_26. CLAUDE.md and AGENTS.md are the
# usual agent instruction files at the vault root; add any other always-relevant
# rule files (a vault specification, a store contract...) through
# OPEN_BRAIN_INSTRUCTION_SURFACES (';'-separated, relative to the vault).
# Surfaces that do not exist are reported as absent but are not findings.
INSTRUCTION_SURFACES = ["CLAUDE.md", "AGENTS.md"] + [
    s for s in _env_list("OPEN_BRAIN_INSTRUCTION_SURFACES") if s not in ("CLAUDE.md", "AGENTS.md")]

# "Instruction" proxy (Chakrabarti 2026, arXiv:2608.11095, §3.1 adapted).
# EXACT rule, do not change without resetting the history: outside code blocks,
# ignoring empty lines, headings (#) and quotes (>), every line that is a list item
# (-, *, +, 1.) or contains a normative marker counts as an instruction. It is a
# proxy, not a semantic segmentation: it serves the DELTA between passes, not as
# an absolute figure. Changing the regex invalidates every earlier comparison.
# (The Spanish markers are kept so bilingual instruction files are counted.)
_NORMATIVE = re.compile(
    r"\b(debe|debes|deben|nunca|siempre|no\s+\w+es|usa|usar|añade|añadir|crea|crear|"
    r"ejecuta|escribe|escribir|must|should|never|always|do not|don't|use|write|run|check)\b",
    re.I)
_LIST_ITEM = re.compile(r"^([-*+]\s|\d+[.)]\s)")


def count_instructions(txt):
    """Returns (instructions, non_empty_lines, bytes) for a surface."""
    instr = 0
    in_code = False
    for line in txt.split("\n"):
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not s or s.startswith("#") or s.startswith(">"):
            continue
        if _LIST_ITEM.match(s) or _NORMATIVE.search(s):
            instr += 1
    return instr, len([l for l in txt.split("\n") if l.strip()]), len(txt)


# Regenerable region of the agent instruction file (CLAUDE.md). The rule is that
# no skill or script writes outside these markers. Here it is only MEASURED: the
# instructions inside and outside are counted separately, so growth outside the
# block shows up in the history. No new regex — it reuses count_instructions, so
# the series is not invalidated. `estado-derivado` ("derived state") is an
# identifier; keep it as written.
_AUTOGEN_OPEN = "<!-- BEGIN:AUTOGEN estado-derivado"
_AUTOGEN_CLOSE = "<!-- END:AUTOGEN estado-derivado"


def split_autogen(txt):
    """Splits a surface into (inside_block, outside_block).

    Without markers it returns (None, txt): the block does not exist yet, and that
    is a finding, not an error."""
    lines = txt.split("\n")
    opens = [i for i, l in enumerate(lines) if l.startswith(_AUTOGEN_OPEN)]
    closes = [i for i, l in enumerate(lines) if l.startswith(_AUTOGEN_CLOSE)]
    if len(opens) != 1 or len(closes) != 1 or closes[0] < opens[0]:
        return None, txt
    # the marker lines count as part of the block: inside + outside then add up
    # exactly to the whole-file count and no line is lost.
    inside = lines[opens[0]:closes[0] + 1]
    outside = lines[:opens[0]] + lines[closes[0] + 1:]
    return "\n".join(inside), "\n".join(outside)


def check_26_surface_sync():
    """Measures the vault's INSTRUCTION SURFACE and its drift between passes.

    Why. A first version only compared the DATES of CLAUDE.md and AGENTS.md and
    never read the content. Counting instructions showed the real failure mode:
    after rewriting the main instruction file to shrink it, the instructions did
    not go away — they moved to a sibling file. A field study that measures one
    file per repo cannot see that ratchet; this check can, because it adds up all
    the surfaces.

    What it does and what it does NOT do. Measures: count per file, total, and
    delta against the previous pass (history in instruction-surface-history.jsonl,
    idempotent — nothing is appended if nothing changed). It does NOT decide what
    to delete: pruning is the vault owner's judgment. Automating deletion by
    absence of a rationale comment would delete rules whose reason was real but
    never written down. This check produces a number; the number does not
    authorise a deletion.

    Generic-vault behaviour: surfaces that do not exist are listed in
    `missing_surfaces` but are not findings; the CLAUDE.md/AGENTS.md date drift is
    only evaluated when both files exist; the missing autogen block is a finding
    only when CLAUDE.md exists."""
    hist_path = VAULT / "Resources" / "Vault Health" / "instruction-surface-history.jsonl"
    per_file, total, missing = {}, 0, []
    autogen = {"block_present": False, "inside": None, "outside": None}
    claude_exists = (VAULT / "CLAUDE.md").exists()
    for rel in INSTRUCTION_SURFACES:
        fp = VAULT / rel
        if not fp.exists():
            missing.append(rel)
            continue
        try:
            txt = fp.read_text(encoding="utf-8")
        except OSError as e:
            missing.append(f"{rel} ({e.__class__.__name__})")
            continue
        instr, lines, nbytes = count_instructions(txt)
        per_file[rel] = {"instructions": instr, "lines": lines, "bytes": nbytes}
        total += instr
        if rel == "CLAUDE.md":
            inside, outside = split_autogen(txt)
            if inside is None:
                autogen = {"block_present": False, "inside": None, "outside": instr}
            else:
                autogen = {"block_present": True,
                           "inside": count_instructions(inside)[0],
                           "outside": count_instructions(outside)[0]}

    # --- history and delta ---
    prev = None
    if hist_path.exists():
        try:
            entries = [json.loads(l) for l in hist_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            prev = entries[-1] if entries else None
        except (OSError, ValueError):
            prev = None
    delta_total = None
    delta_per_file = {}
    if prev:
        delta_total = total - prev.get("total", 0)
        for rel, cur in per_file.items():
            was = (prev.get("per_file") or {}).get(rel, {}).get("instructions")
            if was is not None and was != cur["instructions"]:
                delta_per_file[rel] = cur["instructions"] - was
    changed = (prev is None
               or prev.get("total") != total
               or {k: v["instructions"] for k, v in per_file.items()}
               != {k: v.get("instructions") for k, v in (prev.get("per_file") or {}).items()})
    if changed and not READ_ONLY and per_file:
        hist_path.parent.mkdir(parents=True, exist_ok=True)
        with hist_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": NOW.isoformat(), "total": total,
                                 "per_file": per_file}, ensure_ascii=False) + "\n")

    # --- date drift (original signal, kept) ---
    claude_path, agents_path = VAULT / "CLAUDE.md", VAULT / "AGENTS.md"
    claude_date = agents_date = None
    if claude_path.exists():
        m = re.search(r"validated:\s*(\d{4}-\d{2}-\d{2})", claude_path.read_text(encoding="utf-8"))
        if m:
            claude_date = date.fromisoformat(m.group(1))
    if agents_path.exists():
        m = re.search(r"(?:ltima actualizaci[oó]n|[Ll]ast updated|validated):\s*(\d{4}-\d{2}-\d{2})",
                      agents_path.read_text(encoding="utf-8"))
        if m:
            agents_date = date.fromisoformat(m.group(1))
    drift_days = abs((claude_date - agents_date).days) if (claude_date and agents_date) else None
    both_exist = claude_path.exists() and agents_path.exists()

    # --- severity: growth is the primary signal; dates are secondary ---
    growth_pct = (delta_total / prev["total"] * 100) if (prev and prev.get("total")) else None
    if growth_pct is not None and growth_pct > 2:
        severity = "important"
    elif both_exist and (drift_days is None or drift_days > 30):
        severity = "important"
    elif (delta_total or 0) > 0 or (drift_days or 0) > 7:
        severity = "maintenance"
    else:
        severity = "info"
    block_missing = claude_exists and not autogen["block_present"]
    count = (1 if (delta_total or 0) > 0 else 0) + \
        (1 if both_exist and (drift_days is None or drift_days > 7) else 0) + \
        (1 if block_missing else 0)
    if block_missing:
        severity = "important"

    return {"id": 26, "name": "Instruction Surface (count + drift)",
            "severity": severity,
            "count": count,
            "total_instructions": total,
            "surfaces_measured": len(per_file),
            "per_file": per_file,
            "delta_total": delta_total,
            "delta_per_file": delta_per_file,
            "growth_pct": round(growth_pct, 2) if growth_pct is not None else None,
            "previous_at": prev.get("at") if prev else None,
            "missing_surfaces": missing,
            "claude_autogen": autogen,
            "claude_validated": str(claude_date) if claude_date else None,
            "agents_validated": str(agents_date) if agents_date else None,
            "drift_days": drift_days,
            "note": "Adds up the instructions of every instruction surface and reports the "
                    "delta against the previous pass. The count is a line proxy, not a "
                    "semantic segmentation: it is valid for the DELTA, not as an absolute "
                    "figure, and changing the count_instructions regex invalidates the "
                    "history. A positive delta does NOT authorise deleting anything — "
                    "pruning is by falsification and the vault owner decides it (log it in "
                    "Meta/Instruction Surface Log.md if you keep one). `claude_autogen` "
                    "reports the instructions inside and outside the regenerable block of "
                    "CLAUDE.md. Only the inside is regenerated automatically; growth outside "
                    "the block is the signal to watch, and the absence of the block is a "
                    "finding in itself. Absent surfaces are listed, not counted."}


def check_27_dormancy_candidates():
    """First draft of a successor to a retired 'dormant deprecation cascade'. Uses
    vs.dormancy_score() (age x (1 - importance)) to rank PNs that are candidates
    for review — it does NOT change `maturity`, does NOT delete, does NOT mark
    `[!stale]` automatically (that stays the vault owner's decision). The 0.6
    threshold and the importance weights are a first cut not calibrated against
    real retrieval logs — treat the relative ranking (who is higher) as more
    reliable than the absolute number."""
    out = []
    for p, text in notes("Permanent Notes"):
        fm = parse_fm(text)
        score = vs.dormancy_score(fm)
        if score is not None:
            out.append({"note": p.stem, "score": score,
                        "age_days": vs.days_since(fm.get("created")),
                        "confidence": fm.get("confidence"),
                        "endorsement_state": fm.get("endorsement_state"),
                        "times_retrieved": fm.get("times_retrieved")})
    out.sort(key=lambda x: x["score"], reverse=True)
    scores_only = [o["score"] for o in out]
    stats = {"n": len(scores_only),
             "max": scores_only[0] if scores_only else None,
             "median": scores_only[len(scores_only) // 2] if scores_only else None}
    # No absolute threshold on purpose: on a young vault the maximum score sits far
    # below any "reasonable" cut chosen by eye (0.6) before looking at the real
    # distribution — fixing a threshold without looking at the data is threshold
    # leakage. Report a relative top-N until there is enough history (months, not
    # days) for an absolute cut to make sense.
    return {"id": 27, "name": "Dormancy Candidates (age x importance, draft)",
            "severity": "info",
            # `count` = 0 on purpose. This check has no failure threshold: reporting
            # len(out) = ALL PNs made the run summary show hundreds of "findings"
            # when there are 0 problems and one ranking. The population size lives
            # in distribution["n"].
            "count": 0, "ranked": len(out), "top_20": out[:20], "distribution": stats,
            "note": "Relative ranking (top-20 by score), not a failure threshold — a "
                    "young vault's score distribution is too compressed for an absolute "
                    "cut to make sense without leaking from the data itself. It changes no "
                    "maturity and deletes nothing — the vault owner decides what to do with "
                    "each one (mark [!stale], revalidate, or ignore). Formula not calibrated "
                    "against real retrieval logs."}


def check_33_log_bloat():
    """Bloat of Hot Cache.md / Session Log.md — current bytes + pending archivable
    entries (>14d in 'Recent changes', closed months not yet archived in the
    Session Log). It archives NOTHING on its own (checks are read-only) — if
    count > 0, the fix is
    `python3 "$OPEN_BRAIN_ENGINES/health-engine/compress_logs.py" --apply`.
    Motivated by hard caps per observation, not per session."""
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent))
        import compress_logs
        data = compress_logs.analyze()
    except Exception as e:
        return {"id": 33, "name": "Log Bloat (Hot Cache / Session Log)",
                "severity": "info", "count": 0,
                "detail": f"compress_logs.py unavailable or failed: {e}"}
    archivable = data["hot_cache_archivable"] + data["session_log_archivable"]
    flags = []
    if (data["hot_cache_bytes"] or 0) > 30000:
        flags.append("hot_cache_over_30kb")
    if (data["session_log_bytes"] or 0) > 40000:
        flags.append("session_log_over_40kb")
    if archivable > 0:
        flags.append("archivable_entries_pending")
    return {"id": 33, "name": "Log Bloat (Hot Cache / Session Log)",
            "severity": "important" if archivable > 0 else "info",
            "count": archivable,
            "hot_cache_bytes": data["hot_cache_bytes"],
            "session_log_bytes": data["session_log_bytes"],
            "hot_cache_archivable": data["hot_cache_archivable"],
            "session_log_archivable": data["session_log_archivable"],
            "flags": flags,
            "fix": 'python3 "$OPEN_BRAIN_ENGINES/health-engine/compress_logs.py" --apply' if archivable else None}



def check_34_pipeline_compression():
    """Token compression/expansion between each Inbox note's raw source
    (raw_strategy: full) and the total of the Literature Notes it produced,
    measured in characters/4 (same convention as the session-closing protocol).
    The idea: if public benchmarks exist for how much an external agent-trajectory
    format compresses, the vault's own pipeline deserves the same kind of honest
    measurement — without assuming that "more structured" means "more token
    efficient". It does NOT decide whether the pipeline should be optimised for
    tokens — that is the vault owner's judgment. A ratio > 1.0x (LNs weigh MORE
    than the raw) is the EXPECTED result (each LN adds frontmatter,
    search_context, connectors and provenance per atomic insight) — not an alarm.
    Any source that does not meet the requirements (raw_strategy: full + existing
    raw_path + locatable LNs) is reported as skipped with a reason, never silently
    dropped from the average."""
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
        import compression_benchmark
        data = compression_benchmark.analyze(root=VAULT, min_ln_count=1)
    except Exception as e:
        return {"id": 34, "name": "Pipeline Compression Benchmark",
                "severity": "info", "count": 0,
                "detail": f"compression_benchmark.py unavailable or failed: {e}"}
    return {"id": 34, "name": "Pipeline Compression Benchmark",
            "severity": "info",
            "count": len(data["results"]),
            "avg_ratio": data["avg_ratio"],
            "results": data["results"][:20],
            "skipped_count": len(data["skipped"]),
            "skipped_sample": data["skipped"][:10],
            "note": "ratio = LN_chars / raw_chars over comparable sources. "
                    ">1.0x means expansion (LNs weigh more than the raw), "
                    "expected — not an alarm. Descriptive, not a verdict on "
                    "whether the pipeline 'should' compress more; that decision "
                    "belongs to the vault owner."}


def check_35_skill_sequence_signal():
    """Adoption of the skill_sequence field and retrieval/output signal per
    observed skill sequence (ingest->extract, extract alone, etc.). Same origin as
    check 34: which skill sequences produce notes that actually get retrieved or
    published. Very recent field — low adoption or a signal without a clear
    pattern is NOT a failure; not enough real time has passed for
    times_retrieved/outputs to accumulate on these notes."""
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
        import skill_sequence_report
        data = skill_sequence_report.analyze(root=VAULT)
    except Exception as e:
        return {"id": 35, "name": "skill_sequence Adoption & Signal",
                "severity": "info", "count": 0,
                "detail": f"skill_sequence_report.py unavailable or failed: {e}"}
    return {"id": 35, "name": "skill_sequence Adoption & Signal",
            "severity": "info",
            "count": data["with_seq"],
            "total_notes": data["total_notes"],
            "adoption_pct": data["adoption_pct"],
            "sequences": data["sequences"][:10],
            "signal": data["signal"][:10],
            "parse_errors": data["parse_errors"],
            "note": "new field — low adoption or a signal without a clear "
                    "pattern is expected, not a failure. The cross with "
                    "times_retrieved/outputs is illustrative until more real "
                    "time has passed."}


def check_28_over_application():
    """OVER-APPLIED terms — the pathology check 16 cannot tell apart.

    Check 16 says how many notes carry a term. Red there can mean two opposite
    things: the term is right and there are many notes (split it), or the term is
    placed where it does not belong (remove it). The "red -> split it" reflex
    failed repeatedly until someone read the notes and saw that only a small
    fraction of those tagged with a hub actually talked about it.

    This check provides the missing signal. Read the docstring of
    `vs.over_application()` for the two metrics and, above all, for its measured
    BLIND SPOT: it catches only some of the real cases. A 0 here does not prove
    there is no over-application.
    """
    r = vs.over_application()
    return {"id": 28, "name": "Term Over-application", "severity": "important",
            "count": len(r["flagged"]),
            "thresholds": r["thresholds"],
            "flagged": r["flagged"],
            "skipped_unreadable": r["skipped_unreadable"],
            "note": "sibling_overlap = fraction of the term's notes that ALSO carry "
                    "another child of the same parent (high = the term does not "
                    "discriminate within its family). domain_mismatch = fraction that "
                    "does NOT declare the term in `domains:`. Neither is a verdict: they "
                    "are a 'go read these notes'. BLIND SPOT: when a term absorbs a corpus "
                    "from another domain, the metadata agrees with itself and neither "
                    "metric fires. That is only caught by reading a sample."}


def check_29_engine_stamp_drift():
    """Detects silent drift in the real .py engines by comparing against a hash
    baseline (`engine-stamp.json`, Graft "wiring-stamp" style).

    Why it exists. Engines can end up duplicated under the same relative name in
    two places in the tree (e.g. `engine/practice_log.py` and
    `practice-log-engine/practice_log.py`), byte-identical at first. Nothing
    prevented someone from editing one copy and not the other — two engines with
    the same name giving different results with nothing flagging it, the same
    failure mode Graft documents as "wiring-stamp drift".

    What it does. Reads `health-engine/engine-stamp.json` (a baseline you
    generate: sha256 of each real engine .py) and, for each registered path,
    recomputes the sha256 of the real file. Reports missing ones (the engine the
    stamp expected is no longer there) and mismatches (the content changed since
    the baseline). For basenames with more than one path (real duplicates), it
    also compares the paths AGAINST EACH OTHER, not only each against the stamp —
    that is what detects the day one copy is edited and the other is not.

    What it does NOT do. It does not decide which copy is right, does not merge,
    does not delete, does not regenerate the stamp by itself (if the drift is
    intentional, regenerating the baseline is an explicit action of the vault
    owner). A mismatch here means "this changed since the baseline", not "this is
    wrong". Without a stamp file the check is skipped (severity info)."""
    stamp_path = VAULT / "health-engine" / "engine-stamp.json"
    if not stamp_path.exists():
        return {"id": 29, "name": "Engine Stamp Drift", "severity": "info",
                "count": 0, "missing_stamp": True, "skipped": True,
                "note": "No health-engine/engine-stamp.json — this check cannot "
                        "compare anything and is skipped. Generate a baseline "
                        "(sha256 of each real engine .py) if you want this "
                        "signal."}
    try:
        stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"id": 29, "name": "Engine Stamp Drift", "severity": "important",
                "count": 0, "missing_stamp": True,
                "note": f"engine-stamp.json could not be read ({e.__class__.__name__}) — "
                        "not comparable."}

    missing, mismatched, duplicates_diverged, ok = [], [], [], 0
    engines = stamp.get("engines", {})
    for basename, entries in engines.items():
        live_hashes = {}
        for e in entries:
            fp = VAULT / e["path"]
            if not fp.exists():
                missing.append({"basename": basename, "path": e["path"]})
                continue
            try:
                live_sha = hashlib.sha256(fp.read_bytes()).hexdigest()
            except OSError as ex:
                missing.append({"basename": basename, "path": e["path"],
                                "error": ex.__class__.__name__})
                continue
            live_hashes[e["path"]] = live_sha
            if live_sha != e.get("sha256"):
                mismatched.append({"basename": basename, "path": e["path"],
                                    "stamped_sha256": e.get("sha256"),
                                    "live_sha256": live_sha})
            else:
                ok += 1
        # real duplicates: more than one path for the same basename — verify that
        # they still agree WITH EACH OTHER, not only each one against the stamp.
        if len(entries) > 1:
            distinct = set(live_hashes.values())
            if len(distinct) > 1:
                duplicates_diverged.append({"basename": basename,
                                            "paths": dict(live_hashes)})

    count = len(missing) + len(mismatched) + len(duplicates_diverged)
    severity = "important" if count else "info"
    return {"id": 29, "name": "Engine Stamp Drift", "severity": severity,
            "count": count, "engines_checked": len(engines), "engines_ok": ok,
            "missing": missing, "mismatched": mismatched,
            "duplicates_diverged": duplicates_diverged,
            "stamp_generated": stamp.get("generated"),
            "note": "Comparison against the baseline of " + str(stamp.get("generated")) +
                    ". `duplicates_diverged` is the signal that motivated this check: "
                    "basenames with more than one real path where the paths NO longer "
                    "match each other (0 expected while the copies are identical). A "
                    "normal mismatch (stamp vs. live) can be a legitimate edit; regenerate "
                    "the stamp once you confirm the change is intentional."}



def check_30_source_drift():
    """Compares the LNs' `source_hash` against the real hash of the cache in
    `Resources/Extracted Text/`, resolving the path LN -> source -> cache.

    Why it exists. `open-brain-extract` (Step 6.2) writes
    `source_hash: "sha256:<16-hex>"` in each LN born from a source with a
    markitdown cache. This is the reading side of that contract.

    The LN -> cache mapping uses `raw_cache`, a field that the Inbox notes created
    by `open-brain-ingest` already carry (full path relative to the vault, e.g.
    `Resources/Extracted Text/{slug}.md`). Dossiers created directly by
    `open-brain-extract` (with no prior ingest step, e.g. from a PDF pasted into
    the conversation) may lack that field. A source without `raw_cache` in its note
    (Dossier or Inbox) is "unmapped", not a failure — coverage grows source by
    source, not retroactively.

    What it does. For each LN with `source_hash`: resolves the `source:` wikilink
    to a real note (direct path if the link includes it; otherwise searches by
    basename under `Dossiers/` and `Inbox/`, the two places a source note lives);
    reads that note's `raw_cache`; if present, recomputes the sha256 (16 hex) of
    the real cache and compares it against the hash stored in the LN.

    What it does NOT do. It does not decide whether an LN is still valid when the
    hash changes — that is the vault owner's judgment. Step 6.2 already says so:
    the verbatim quote is the real anchor, not the hash; a mismatch here only
    flags WHERE to re-check the quote against the re-edited text, never that the
    LN is wrong."""
    mismatched, missing_cache, unmapped, ok = [], [], [], 0
    for p, text in notes("Literature Notes"):
        fm = parse_fm(text)
        sh = fm.get("source_hash")
        if not isinstance(sh, str) or not sh.startswith("sha256:"):
            continue
        stored_hash = sh.split(":", 1)[1].strip()
        src = fm.get("source")
        link = (src if isinstance(src, str) else "").strip()
        if link.startswith("[[") and link.endswith("]]"):
            link = link[2:-2]
        basename = link.rsplit("/", 1)[-1].strip()
        source_path = VAULT / f"{link}.md" if link else None
        if not source_path or not source_path.exists():
            hits = []
            for folder in ("Dossiers", "Inbox"):
                hits += list((VAULT / folder).rglob(f"{basename}.md")) if basename else []
            source_path = hits[0] if hits else None
        if not source_path or not source_path.exists():
            unmapped.append({"note": p.stem, "reason": "source not resolved from source: "
                              "(neither Dossiers/ nor Inbox/)", "source": src})
            continue
        try:
            source_text = source_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            unmapped.append({"note": p.stem, "reason": f"source unreadable ({exc.__class__.__name__})",
                              "source_note": source_path.stem})
            continue
        sfm = parse_fm(source_text)
        cache_rel = sfm.get("raw_cache")
        if not cache_rel or not isinstance(cache_rel, str):
            unmapped.append({"note": p.stem, "reason": "source without raw_cache",
                              "source_note": source_path.stem})
            continue
        cache_path = VAULT / cache_rel
        if not cache_path.exists():
            missing_cache.append({"note": p.stem, "cache": cache_rel, "source_note": source_path.stem})
            continue
        try:
            live = hashlib.sha256(cache_path.read_bytes()).hexdigest()[:16]
        except OSError as exc:
            missing_cache.append({"note": p.stem, "cache": cache_rel,
                                  "error": exc.__class__.__name__})
            continue
        if live != stored_hash:
            mismatched.append({"note": p.stem, "cache": cache_rel,
                                "stored": stored_hash, "live": live})
        else:
            ok += 1

    total_with_hash = ok + len(mismatched) + len(missing_cache) + len(unmapped)
    count = len(mismatched) + len(missing_cache)
    severity = "important" if mismatched else ("info" if count == 0 else "maintenance")
    return {"id": 30, "name": "Source Drift (LN vs cache)", "severity": severity,
            "count": count, "ok": ok, "mismatched": mismatched,
            "missing_cache": missing_cache, "unmapped": unmapped[:20],
            "unmapped_total": len(unmapped), "total_with_source_hash": total_with_hash,
            "note": ("A mismatch = the cache in Resources/Extracted Text/ changed since "
                      "the LN was written (source re-edited or cache regenerated). It does "
                      "not imply the LN is invalid — the verbatim quote is still the "
                      "anchor (Step 6.2 of open-brain-extract); this check only flags "
                      f"where to re-verify it. `unmapped` ({len(unmapped)} of {total_with_hash} "
                      "LNs with source_hash) are sources whose note (Dossier or Inbox) does "
                      "not have `raw_cache` yet — not comparable yet, not failures; "
                      "coverage grows with each new extraction.")}


# ============================================================
# PROVENANCE AND SURFACE CHECKS (36-42)
#
# Output contract specific to this block: besides `count`, each check returns
# `status` and `failure_origin`. A `count: 0` in a report does not distinguish
# "I looked and there was nothing" from "I could not look". The three values of
# `status`:
#
#   ok        -> the check ran over its universe and found nothing.
#   findings  -> the check ran and found `count` things.
#   not_run   -> the check could NOT run; `failure_origin` says why.
#
# `failure_origin` is None except for not_run. The rule is that a missing
# precondition (a list not created yet, a file that does not exist) is a declared
# state and not a silent zero. Covered by `health_check.py self-test` with a
# negative fixture: if a check stops reporting on the broken test vault, the
# self-test fails.
# ============================================================

def _mk(id_, name, severity, count, items=None, failure_origin=None, **extra):
    """Single constructor for the status block. Derives `status` from
    (count, failure_origin) so no two checks use different criteria for what a
    zero is."""
    status = "not_run" if failure_origin else ("findings" if count else "ok")
    out = {"id": id_, "name": name, "severity": severity, "status": status,
           "count": count, "failure_origin": failure_origin,
           "items": (items or [])[:30]}
    out.update(extra)
    return out


_STEM_INDEX = None


def _stem_index():
    """stem -> first path with that stem, excluding _to_delete. Same universe as
    vault-scan's `all_stems()`, but keeping the path: without it there is no way to
    know whether a resolved source is an LN, a Dossier or a PN."""
    global _STEM_INDEX
    if _STEM_INDEX is None:
        idx = {}
        for p in VAULT.rglob("*.md"):
            if p.relative_to(VAULT).parts[0] in vs.DELETED_DIRS:
                continue
            idx.setdefault(p.stem, p)
        _STEM_INDEX = idx
    return _STEM_INDEX


def _deref(ref) -> str:
    """Normalises a frontmatter reference to a stem: strips [[ ]], the alias after
    |, the anchor after # and the folder prefix. Same rule check_8 uses in the body."""
    r = str(ref).strip()
    if r.startswith("[["):
        r = r[2:]
    if r.endswith("]]"):
        r = r[:-2]
    return r.split("|")[0].split("#")[0].split("/")[-1].strip()


_AUTHOR_CACHE = {}


def _author_of(path) -> str:
    """Author of a resolved note: `mentor` in LNs, `author` in Dossiers. Returns
    "" when there is none — and that "" is information, not a failure: a source
    without a known author can neither support nor refute a PN's independence."""
    key = str(path)
    if key not in _AUTHOR_CACHE:
        try:
            fm = parse_fm(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            fm = {}
        raw = fm.get("mentor") or fm.get("author") or ""
        _AUTHOR_CACHE[key] = _deref(raw).lower() if raw else ""
    return _AUTHOR_CACHE[key]


def check_36_pn_provenance():
    """PN provenance: resolves the FRONTMATTER `sources:` against the vault.

    Why it exists. `check_8` audits the wikilinks in the BODY of PNs and to do so
    runs `FM_RE.sub("", text)` — it deletes the frontmatter before looking. In
    other words: the only place where a PN declares its sources is exactly the only
    place the engine did not read. A manual traceability audit can find a sizeable
    share of `sources:` references that resolve to no note, none of which ever
    appeared in a health report. A structural blind spot, not a one-session slip.

    What it measures, in three figures matching the three ways of breaking the
    two-independent-sources rule:
      1. `orphan_refs` — `sources:` references that resolve to no note in the
         vault. The chain is broken in the file, not in the contract.
      2. `under_two_sources` — PNs that, after resolving, have fewer than two real
         sources. The rule requires >=2; declaring them is not having them.
      3. `single_author` — PNs with >=2 resolved sources, ALL with a known author,
         and a single author among them. Independence means a different author:
         these break the rule by construction even if they pass any count.

    What it does NOT do. It does not decide the fix. Each PN on the lists has three
    possible exits (find a second independent source, downgrade to
    `confidence: medium` with a reason, or merge into its LN) and choosing is the
    vault owner's judgment. This check produces the list; the list does not
    authorise a downgrade. Nor does it count as a violation a PN whose resolved
    sources declare no author: without an author there is no independence to
    check, and counting it would invent a breach."""
    idx = _stem_index()
    orphan_refs, under_two, single_author = [], [], []
    total_refs = 0
    pns = 0
    for p, text in notes("Permanent Notes"):
        pns += 1
        fm = parse_fm(text)
        resolved = []
        for ref in vs.as_list(fm.get("sources")):
            if not str(ref).strip():
                continue
            total_refs += 1
            hit = idx.get(_deref(ref))
            if hit is None:
                orphan_refs.append({"pn": p.stem, "ref": _deref(ref)})
            else:
                resolved.append(hit)
        if len(resolved) < 2:
            under_two.append({"pn": p.stem, "resolved": len(resolved),
                              "declared": len(vs.as_list(fm.get("sources")))})
            continue
        authors = [_author_of(x) for x in resolved]
        if all(authors) and len(set(authors)) == 1:
            single_author.append({"pn": p.stem, "author": authors[0],
                                  "sources": len(resolved)})

    pns_with_orphans = len({o["pn"] for o in orphan_refs})
    count = len(orphan_refs) + len(under_two) + len(single_author)
    return _mk(36, "PN Provenance (resolved sources:)", "critical", count,
               items=orphan_refs,
               orphan_refs=len(orphan_refs), pns_with_orphan_refs=pns_with_orphans,
               under_two_sources=len(under_two), under_two_items=under_two[:30],
               single_author=len(single_author), single_author_items=single_author[:30],
               total_refs=total_refs, pns_scanned=pns,
               note=("Three distinct breaches of the two-independent-sources rule in one "
                     "check: references that do not resolve, PNs with <2 real sources, and "
                     "PNs with >=2 sources from a single author. `count` is the sum; look at "
                     "them separately to decide. A PN whose resolved sources declare no "
                     "author is NOT counted as single-author: without an author there is no "
                     "verifiable independence."))


_THIRD_PARTY_LIST = "Meta/third-party-names.txt"


def check_37_third_party_names():
    """Third parties' proper names in the knowledge tree.

    Why it exists. The vault contract forbids storing the names of coworkers,
    bosses or colleagues — only generic roles. A periodic manual grep is another
    way of saying it is never audited; names easily slip into file names.

    Where the list lives and why there. In `Meta/third-party-names.txt`, one line
    per name, `#` for comments. Meta/ is machinery, not knowledge tree, so the
    list does not violate the principle it guards. It is the only exception, and a
    deliberate one: a name detector needs the names.

    What it does NOT do. It deletes or renames nothing, and does not guess names:
    without a list there is no check, and it says so (`not_run`) instead of
    returning a reassuring zero. Public authors and mentors you cite are NOT on the
    list: the rule explicitly allows them."""
    list_path = VAULT / _THIRD_PARTY_LIST
    if not list_path.exists():
        return _mk(37, "Third-Party Names", "important", 0,
                   failure_origin=f"{_THIRD_PARTY_LIST} does not exist: no list, no grep. "
                                  "Create it (one line per name) or the check cannot run.")
    try:
        raw = list_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return _mk(37, "Third-Party Names", "important", 0,
                   failure_origin=f"{_THIRD_PARTY_LIST} unreadable ({exc.__class__.__name__})")
    names, excepts = [], []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        (excepts if s.startswith("!") else names).append(s.lstrip("!").strip())
    if not names:
        return _mk(37, "Third-Party Names", "important", 0,
                   failure_origin=f"{_THIRD_PARTY_LIST} exists but is empty: "
                                  "zero names to look for is not zero findings.")

    def _rx(s):
        return re.compile(r"(?<![\w])" + re.escape(s) + r"(?![\w])", re.IGNORECASE)

    pats = [(n, _rx(n)) for n in names]
    # Exceptions (lines starting with '!'): public authors whose FULL name contains
    # a name on the list. Without this, a common first name on the list would flag
    # every PN citing a well-known author who shares it. Suppression is by
    # POSITION OVERLAP, not by text: it only silences the hit that falls inside the
    # author's full name and leaves every other use of the same name alive.
    ex_pats = [_rx(e) for e in excepts]

    def _suppressed(text, m):
        return any(x.start() <= m.start() and m.end() <= x.end()
                   for rx in ex_pats for x in rx.finditer(text))

    def _hit(text, rx):
        return any(not _suppressed(text, m) for m in rx.finditer(text))

    hits, suppressed = [], 0
    for folder in ("Manuscripts", "Cases", "Permanent Notes"):
        for p, text in notes(folder):
            for n, rx in pats:
                where = []
                if _hit(p.stem, rx):
                    where.append("title")
                if _hit(text, rx):
                    where.append("body")
                if where:
                    hits.append({"note": p.stem, "folder": folder,
                                 "name": n, "where": "+".join(where)})
                elif rx.search(text) or rx.search(p.stem):
                    suppressed += 1
    in_title = sum(1 for h in hits if "title" in h["where"])
    return _mk(37, "Third-Party Names", "important", len(hits), items=hits,
               names_in_list=len(names), exceptions_in_list=len(excepts),
               suppressed_by_exception=suppressed, hits_in_title=in_title,
               note=("A hit in `title` is the serious case: the name travels in the file "
                     "path and in every wikilink pointing to it. The list lives in Meta/ "
                     "(machinery), never in the knowledge tree. Lines starting with '!' are "
                     "public authors: they suppress the hit only when it falls inside their "
                     "full name."))


_WITNESS_LOG = "Resources/Vault Health/witness-log.jsonl"
# Fold headers. compress_logs.py writes "## Archived <date>" / "## Folded <date>";
# folds done by hand may omit the "##". The Spanish forms ("Archivado", "Plegado")
# are still accepted for archives written by earlier versions.
_ARCHIVE_SECTION = re.compile(
    r"^(?:##\s+)?(?:Archived|Folded|Archivado|Plegado)\s+(\d{4}-\d{2}-\d{2})", re.MULTILINE)
# The "Cambios Archive" file name is kept as is ("Cambios" = changes).
_FOLD_TARGETS = [
    "Resources/Hot Cache — Cambios Archive.md",
    "Resources/Hot Cache — Threads Archive.md",
]


def check_38_prune_witness():
    """Witness log: every fold of vault content leaves a record of what moved,
    from where, and how much.

    Why it exists. The closing protocol says nothing is deleted: whatever leaves a
    block is folded into its archive "with a dated line saying what moved and
    where it came from". That dated line is a promise of the contract that nobody
    checked. `compress_logs.py` writes an `## Archived YYYY-MM-DD` header in the
    destination file, but that header says WHEN, not HOW MUCH nor FROM WHERE: it
    does not allow reconstructing whether the fold lost something on the way.

    How it works. A fold event observable on disk = each `## Archived <date>`
    section of the Hot Cache archive files, plus each file in
    `Resources/Session Logs/`. Witness = an entry in witness-log.jsonl with
    `{ts, op, source, destination, items, bytes_before, bytes_after}`. The check
    pairs them by (destination, date) and reports the events without a witness.

    What it does NOT do. It does not retro-invent witnesses for folds that predate
    this check: a backfilled witness attests nothing, it only looks like a
    witness. Earlier events are listed as unwitnessed, which is their real state,
    and the counter drops as the engine writes witnesses for new folds."""
    log_path = VAULT / _WITNESS_LOG
    witnessed = set()
    log_entries = 0
    if log_path.exists():
        try:
            for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                log_entries += 1
                dest = str(e.get("destination") or "")
                # event_date: date of the witnessed fold when the witness is written
                # later (verify-fold against a backup); otherwise the witness's own.
                ts = str(e.get("event_date") or e.get("ts") or "")[:10]
                witnessed.add((dest.split("/")[-1], ts))
        except OSError as exc:
            return _mk(38, "Prune Witness Log", "important", 0,
                       failure_origin=f"{_WITNESS_LOG} unreadable ({exc.__class__.__name__})")

    events = []
    for rel in _FOLD_TARGETS:
        fp = VAULT / rel
        if not fp.exists():
            continue
        try:
            txt = fp.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in _ARCHIVE_SECTION.finditer(txt):
            events.append({"destination": rel, "date": m.group(1)})
    sl_dir = VAULT / "Resources" / "Session Logs"
    if sl_dir.exists():
        for p in sorted(sl_dir.rglob("*.md")):
            events.append({"destination": f"Resources/Session Logs/{p.name}",
                           "date": datetime.fromtimestamp(p.stat().st_mtime,
                                                          timezone.utc).date().isoformat()})

    seen = set()
    events = [e for e in events if not ((e["destination"], e["date"]) in seen
                                        or seen.add((e["destination"], e["date"])))]
    unwitnessed = [e for e in events
                   if (e["destination"].split("/")[-1], e["date"]) not in witnessed]
    return _mk(38, "Prune Witness Log", "important", len(unwitnessed), items=unwitnessed,
               fold_events=len(events), witness_entries=log_entries,
               witness_log=_WITNESS_LOG,
               note=("A fold without a witness is not necessarily a loss: it is a fold "
                     "for which it cannot be shown that there was none. Events before this "
                     "check are not backfilled — a witness invented after the fact attests "
                     "nothing."))


def check_39_batch_link_audit():
    """Wikilink audit against disk, per extraction BATCH.

    Why it exists. `check_8` looks at the body wikilinks of PNs and
    `check_23`/`check_24` look at orphans and loose Search Terms, but none groups
    by batch. The vault's real failure mode is per batch: one extraction can bring
    in dozens of broken wikilinks at once because of a defect in the extract
    package, and they get found by chance, not by the engine. A batch is the unit
    in which the pipeline fails, so it is the unit to audit.

    How a batch is defined. (`source`, `created`) of the LNs: one source extracted
    on one day. Batches of >= MIN_BATCH notes created in the last WINDOW_DAYS days
    are audited — looking at old batches changes nothing that can be fixed today,
    and the goal is to close the loop while the package that produced them is
    still installed.

    What it does NOT do. It does not fix the links nor guess the right target. It
    reports the batch, the defect and how many notes share it, which is what lets
    you decide whether the failure belongs to one note or to the package that
    produced all 40."""
    MIN_BATCH, WINDOW_DAYS = 8, 45
    stems = all_stems()
    batches = {}
    for p, text in notes("Literature Notes"):
        fm = parse_fm(text)
        created = fm.get("created")
        d = days_since(created)
        if d is None or d > WINDOW_DAYS:
            continue
        key = (_deref(fm.get("source") or "(no source)"), str(created)[:10])
        batches.setdefault(key, []).append((p, text))

    out = []
    audited_notes = 0
    for (src, created), members in sorted(batches.items()):
        if len(members) < MIN_BATCH:
            continue
        audited_notes += len(members)
        broken = {}
        for p, text in members:
            for m in WIKILINK_RE.finditer(text):
                target = m.group(1).split("/")[-1].strip()
                if target and target not in stems:
                    broken.setdefault(target, set()).add(p.stem)
        if broken:
            out.append({"source": src, "created": created, "notes": len(members),
                        "broken_targets": len(broken),
                        "broken_links": sum(len(v) for v in broken.values()),
                        "worst": sorted(((t, len(v)) for t, v in broken.items()),
                                        key=lambda x: -x[1])[:5]})
    out.sort(key=lambda x: -x["broken_links"])
    return _mk(39, "Batch Link Audit (LN)", "important", len(out), items=out,
               batches_audited=len([1 for k, v in batches.items() if len(v) >= MIN_BATCH]),
               notes_audited=audited_notes, min_batch=MIN_BATCH, window_days=WINDOW_DAYS,
               note=(f"Batch = (source, created) with >= {MIN_BATCH} LNs in the last "
                     f"{WINDOW_DAYS} days. `count` is BATCHES with broken links, not links: "
                     "a batch with 40 broken is a defect of the extract package, and 40 "
                     "batches with 1 each are 40 typos. That distinction is the goal of the check."))


# Always-loaded instruction files (read at the start of every session).
# Configure with OPEN_BRAIN_ALWAYS_SURFACES (','-separated, relative to the
# vault). Default: CLAUDE.md. Missing files only count as findings when the list
# was configured explicitly; with the default, a vault without them reports 0.
_ALWAYS_EXPLICIT = bool(os.environ.get("OPEN_BRAIN_ALWAYS_SURFACES", "").strip())
_ALWAYS_LOADED = [x.strip() for x in
                  os.environ.get("OPEN_BRAIN_ALWAYS_SURFACES", "CLAUDE.md").split(",")
                  if x.strip()] or ["CLAUDE.md"]
# On-demand instruction files (read only when a step needs them). Personal to each
# vault, so empty by default: list yours in OPEN_BRAIN_ON_DEMAND_SURFACES
# (';'-separated, relative to the vault).
_ON_DEMAND = _env_list("OPEN_BRAIN_ON_DEMAND_SURFACES")
# Budget for the always-loaded layer. A typical agent instruction file estimates
# ~3,000 tokens of always-load instructions; 6,000 is double that figure — room
# for the Hot Cache, not permission to grow without limit. If you raise it, raise
# it with a dated reason.
_ALWAYS_BUDGET_TOKENS = 6000


def check_40_instruction_layers():
    """Cost of the instruction surface PER LAYER, not in an aggregate ratio.

    Why it exists. `check_26` measures instructions per file and their drift, but
    it adds apples (what is loaded in every session) to oranges (what is read on
    demand). An aggregate ratio hides the only number that decides the real cost:
    how much ALWAYS enters the context.

    What it measures. Two declared layers: `always` (what the session protocol
    says to read at the start of every substantive session) and `on_demand` (read
    when needed). Per file: bytes, estimated tokens (bytes/4) and instructions,
    reusing `count_instructions` so as not to break check_26's series.

    What it does NOT do. It does not prune. A large file in the always layer is a
    finding, not an order to cut: the same restriction as check_26 — the number
    says where to look, not what to delete."""
    def layer(rels):
        files, tot_b, tot_i = [], 0, 0
        for rel in rels:
            fp = VAULT / rel
            if not fp.exists():
                files.append({"file": rel, "status": "missing"})
                continue
            try:
                txt = fp.read_text(encoding="utf-8", errors="ignore")
            except OSError as exc:
                files.append({"file": rel, "status": f"unreadable:{exc.__class__.__name__}"})
                continue
            instr, _, b = count_instructions(txt)
            files.append({"file": rel, "bytes": b, "est_tokens": round(b / 4),
                          "instructions": instr})
            tot_b += b
            tot_i += instr
        return files, tot_b, tot_i

    a_files, a_bytes, a_instr = layer(_ALWAYS_LOADED)
    d_files, d_bytes, d_instr = layer(_ON_DEMAND)
    a_tokens = round(a_bytes / 4)
    over = [f for f in a_files if f.get("est_tokens")] and a_tokens > _ALWAYS_BUDGET_TOKENS
    missing = [f["file"] for f in (a_files if _ALWAYS_EXPLICIT else []) + d_files
               if f.get("status") == "missing"]
    count = (1 if over else 0) + len(missing)
    return _mk(40, "Instruction Cost by Layer", "maintenance", count,
               items=([{"layer": "always", "est_tokens": a_tokens,
                        "budget": _ALWAYS_BUDGET_TOKENS,
                        "over_by": a_tokens - _ALWAYS_BUDGET_TOKENS}] if over else [])
                     + [{"missing": m} for m in missing],
               always={"files": a_files, "bytes": a_bytes, "est_tokens": a_tokens,
                       "instructions": a_instr, "budget_tokens": _ALWAYS_BUDGET_TOKENS,
                       "over_budget": bool(over)},
               on_demand={"files": d_files, "bytes": d_bytes,
                          "est_tokens": round(d_bytes / 4), "instructions": d_instr},
               note=("Split into two layers on purpose: `always` is what every session "
                     "costs, `on_demand` is what costs only when used. Adding them into a "
                     "single ratio hid the only number that is always paid. The budget is "
                     "double the ~3,000-token always-load estimate, as margin."))


# From which `created` date check_41 applies. Empty = applies to every PN with a
# `created` date. Set it (OPEN_BRAIN_ENDORSEMENT_CUTOFF=YYYY-MM-DD or
# `run --endorsement-cutoff`) to the date you adopt the rule, so older PNs are
# reported as legacy backlog instead of violations.
_ENDORSEMENT_CUTOFF = os.environ.get("OPEN_BRAIN_ENDORSEMENT_CUTOFF", "").strip()


def check_41_endorsement_events():
    """A PN's approval as a dated EVENT, not as a state.

    Why it exists. No PN should exist without the vault owner's explicit
    confirmation. The field meant to record it, `endorsement_state`, ends up
    `provisional` on almost every note: a state that nearly all notes share
    distinguishes nothing. In particular it does not distinguish "the owner
    approved it and nobody recorded it" from "never reviewed", which is exactly the
    difference the rule exists to mark. Hence two fields: `endorsed_at` (date) and
    `endorsed_via` (sesion, review-queue, promote, careo, ...).

    How it counts. The rule applies GOING FORWARD, from the cutoff. A PN created on
    or after the cutoff must carry `endorsed_at` or declare `status: draft`; if it
    has neither, it is a breach and adds to `count`. Those before the cutoff are
    debt: reported as `legacy_backlog` and NOT added — retroactively requiring a
    date nobody wrote down would produce hundreds of identical findings and a
    check nobody reads.

    What it does NOT do. It writes `endorsed_at` in no note, nor infers the
    approval date from another field. An inferred approval date is the opposite of
    what the rule asks: it would be the system certifying that the owner approved
    something."""
    endorsed, drafts, violations, legacy, no_hist = [], [], [], [], []
    scanned = 0
    for p, text in notes("Permanent Notes"):
        scanned += 1
        fm = parse_fm(text)
        # The `## Historial` (history) block is append-only and only records
        # epistemic events (approval, downgrade, merge, later source). An approved
        # PN without any history line has lost its first event: the approval
        # itself. The heading is an identifier and stays as written.
        has_hist = "## Historial" in text and any(
            l.strip().startswith("20") for l in text.split("## Historial", 1)[-1].split("\n"))
        at = str(fm.get("endorsed_at") or "").strip()
        st = str(fm.get("status") or "").strip().lower()
        created = str(fm.get("created") or "").strip()[:10]
        if at:
            endorsed.append({"pn": p.stem, "at": at,
                             "via": str(fm.get("endorsed_via") or "").strip() or "(no via)"})
            if not has_hist:
                no_hist.append(p.stem)
            continue
        if st == "draft":
            drafts.append(p.stem)
            continue
        if created and created >= _ENDORSEMENT_CUTOFF:
            violations.append({"pn": p.stem, "created": created})
        else:
            legacy.append(p.stem)

    no_via = [e for e in endorsed if e["via"] == "(no via)"]
    since = _ENDORSEMENT_CUTOFF or "the first dated PN (no cutoff set)"
    return _mk(41, "Endorsement as Event", "important",
               len(violations) + len(no_hist),
               items=violations + [{"pn": x, "missing": "Historial line"} for x in no_hist],
               endorsed=len(endorsed), endorsed_without_via=len(no_via),
               endorsed_without_history=len(no_hist),
               drafts=len(drafts), legacy_backlog=len(legacy),
               pns_scanned=scanned, cutoff=_ENDORSEMENT_CUTOFF or None,
               note=(f"The rule applies from {since}: a PN created on or after it must "
                     "carry `endorsed_at` or `status: draft`. `count` is only those "
                     "breaches. `legacy_backlog` is the debt before the cutoff and is not "
                     "added: retroactively requiring a date nobody wrote down would give "
                     "hundreds of identical findings and a check nobody reads. A PN with "
                     "`endorsed_at` and no line in its `## Historial` block also counts: the "
                     "approval is the first event of the timeline and losing it empties the "
                     "block of its only guaranteed content."))


def _voc_norm(s) -> str:
    """Same canonical form as `enrich_engine._norm`. Duplicated on purpose instead
    of imported: `health_check.py` does not depend on `enrich-engine/` anywhere
    else, and a new dependency between engines for six lines is a worse deal than
    six repeated lines. If they diverge, the fixture catches it."""
    import unicodedata
    s = str(s).replace("[[", "").replace("]]", "").split("|")[0].strip()
    s = s.replace("—", " ").replace("–", " ").replace("-", " ")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


_VOC_FOLDERS = ["Permanent Notes", "Literature Notes", "Cases", "Fleeting Notes"]
_VOC_WINDOW_DAYS = 14
_VOC_FREE_GATE = 0.02        # <=2% free terms in the window
_VOC_HUB_MIN_NOTES = 20      # below this, the domain ratio is noise
_VOC_HUB_RATIO = 0.50        # a hub with <50% of its notes in its domain is over-applied


def check_42_vocabulary():
    """VOCABULARY. Measures the three kinds of drift that make a term x type
    intersection return garbage faster.

    Why it exists. A vault has two vocabulary layers and usually only one is
    controlled: terms with a page in `Search Terms/` behave like a vocabulary
    (few notes each); free terms are mostly singletons. `enrich_engine` rejects
    terms without a page, but `extract` writes `search_terms` without going
    through that registry. This check is the instrument that says whether that
    leak is closed.

    The three signals, and why these and not others:

    1. `free_ratio_window` — % of free terms in notes created in the last 14 days.
       It is the only one of the three that measures FLOW: the inherited stock is
       not fixed by a check, it is fixed by an approved batch. Gate: <=2%.

       Terms are deduplicated PER NOTE before counting: `search_terms` is a set,
       and counting occurrences inflated the hub signal. Repetitions are reported
       separately in `duplicate_terms` — they are a defect of their own and must
       not vanish inside another metric.

    2. `hubs_over_applied` — hierarchical "X - Y" hubs whose parent X is a Domain
       and that appear in >=20 notes with fewer than 50% declaring X in `domains`.
       It is exactly the condition `enrich_engine.cmd_apply` rejects, measured over
       the corpus: the rule and its measurement share a definition on purpose, so
       that "0 new" means something. `check_28` measures a broader family with
       another criterion and remains valid; this is the narrow flank the rule can
       close.

    3. `bilingual_drift` — free terms whose canonical form is ALREADY the declared
       alias of an existing page ("carga cognitiva" -> "Cognitive Load"). Each one
       is a term coined with the hub right there.

    The gate is (1) and (2). (3) is reported and does not block: replacing a term
    with its hub touches notes, so it needs the vault owner's approval and cannot
    be automated from a check.
    """
    st_dir = VAULT / "Search Terms"
    if not st_dir.is_dir():
        return _mk(42, "Vocabulary Drift", "important", 0,
                   failure_origin=f"{st_dir} does not exist: without a term registry "
                                  "free terms cannot be told apart from hubs.")
    stems, by_norm, alias = set(), {}, {}
    for p in st_dir.rglob("*.md"):
        stems.add(p.stem)
        by_norm.setdefault(_voc_norm(p.stem), []).append(p.stem)
        try:
            fm = vs.parse_fm(p.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        for a in vs.as_list(fm.get("aliases")):
            n = _voc_norm(a)
            if n and n not in by_norm:
                alias.setdefault(n, p.stem)
    doms = {q.stem.lower(): q.stem for q in (VAULT / "Domains").rglob("*.md")}

    cutoff = (TODAY - timedelta(days=_VOC_WINDOW_DAYS)).isoformat()
    win_tot = win_free = 0
    win_notes = []
    duplicate_terms = 0
    duplicate_notes = []
    hub_notes, hub_ok = {}, {}
    drift = {}
    read_failures = 0
    for folder in _VOC_FOLDERS:
        base = VAULT / folder
        if not base.is_dir():
            continue
        for p in base.rglob("*.md"):
            rel = str(p.relative_to(VAULT))
            if "_to_delete" in rel or "/Archive/" in rel:
                continue
            try:
                fm = vs.parse_fm(p.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                read_failures += 1
                continue
            created = str(fm.get("created") or "")[:10]
            note_doms = {str(d).replace("[[", "").replace("]]", "").split("|")[0].strip().lower()
                         for d in vs.as_list(fm.get("domains"))}
            terms = [str(t).replace("[[", "").replace("]]", "").split("|")[0].strip()
                     for t in vs.as_list(fm.get("search_terms"))]
            terms = [t for t in terms if t]
            # Deduplicate PER NOTE. `search_terms` is semantically a set: a note
            # that carries the same term twice is not indexed twice. Counting
            # occurrences inflated the hub signal (Fleeting Notes with the term
            # repeated in their own list).
            dups = len(terms) - len(set(terms))
            duplicate_terms += dups
            if dups:
                duplicate_notes.append({"note": rel, "repeated": sorted(
                    {t for t in terms if terms.count(t) > 1})})
            terms = list(dict.fromkeys(terms))
            fresh = bool(created) and created >= cutoff
            n_free_here = 0
            for t in terms:
                free = t not in stems
                if fresh:
                    win_tot += 1
                    win_free += free
                    n_free_here += free
                if free:
                    n = _voc_norm(t)
                    if n in alias or n in by_norm:
                        canon = by_norm[n][0] if n in by_norm else alias[n]
                        drift.setdefault(canon, set()).add(t)
                    continue
                # hierarchical hub with a Domain parent
                for sep in (" — ", " - ", " – "):
                    if sep in t:
                        parent = doms.get(t.split(sep)[0].strip().lower())
                        if parent:
                            hub_notes[t] = hub_notes.get(t, 0) + 1
                            hub_ok[t] = hub_ok.get(t, 0) + any(
                                d == parent.lower() or d.startswith(parent.lower() + " — ") or d.startswith(parent.lower() + " - ")
                                for d in note_doms)  # a subdomain counts as the parent
                        break
            if fresh and n_free_here:
                win_notes.append({"note": rel, "free_terms": n_free_here})

    ratio = (win_free / win_tot) if win_tot else 0.0
    over = [{"hub": h, "parent": h.split(" — ")[0].split(" - ")[0],
             "notes": n, "in_domain": hub_ok[h], "ratio": round(hub_ok[h] / n, 2)}
            for h, n in hub_notes.items()
            if n >= _VOC_HUB_MIN_NOTES and hub_ok[h] / n < _VOC_HUB_RATIO]
    over.sort(key=lambda x: x["ratio"])
    bilingual = [{"canon": k, "free_variants": sorted(v)} for k, v in drift.items()]
    bilingual.sort(key=lambda x: -len(x["free_variants"]))

    items = []
    if ratio > _VOC_FREE_GATE:
        items.append({"kind": "free_ratio", "window_days": _VOC_WINDOW_DAYS,
                      "terms": win_tot, "free": win_free, "ratio": round(ratio, 3),
                      "gate": _VOC_FREE_GATE,
                      "worst_notes": sorted(win_notes, key=lambda x: -x["free_terms"])[:10]})
    items += [{"kind": "hub_over_applied", **o} for o in over]

    return _mk(42, "Vocabulary Drift", "important", len(items), items,
               free_ratio_window=round(ratio, 3),
               free_terms_window=win_free, terms_window=win_tot,
               hubs_over_applied=len(over),
               duplicate_terms=duplicate_terms,
               duplicate_notes=duplicate_notes[:15],
               bilingual_drift=len(bilingual),
               bilingual_sample=bilingual[:15],
               read_failures=read_failures,
               note="The gate is the first two signals: free-term ratio in the window "
                    "<=2% and 0 new over-applied hubs. `bilingual_drift` is reported and "
                    "does NOT block — replacing a term with its hub touches notes, so the "
                    "vault owner approves it. The window measures FLOW: the inherited "
                    "stock is not visible to it and should not be.")


def check_43_binding_rules_drift():
    """Parses figures declared by hand in a rules document against the real
    filesystem/engine — the same pattern as check_26 (instruction surface) but for
    loose figures in prose that nobody recomputes.

    Why it exists. Rule documents state figures ("N active checks", "~N tokens"
    for the Hot Cache) that drift silently as the system grows. The principle
    "verify against the filesystem before trusting a cited figure" is automated
    here for that document.

    Which document. Set OPEN_BRAIN_BINDING_RULES to its path relative to the
    vault. Without it (or if the file is absent) the check is skipped.

    What it measures and what it does NOT. Two patterns: "N active checks" /
    "N checks activos" (against `len(CHECKS)`) and "~N tokens" on a line that
    mentions the Hot Cache (against the real size of `Resources/Hot Cache.md` / 4).
    It is NOT a generic parser of any figure in prose — adding a third pattern is
    new code, not configuration, and it stays documented that way instead of
    pretending full coverage."""
    rel = os.environ.get("OPEN_BRAIN_BINDING_RULES", "").strip()
    name = "Binding Rules: declared figures vs filesystem"
    fp = VAULT / rel if rel else None
    findings = []
    if not fp or not fp.exists():
        return {"id": 43, "name": name, "severity": "info", "count": 0,
                "findings": [], "skipped": True,
                "note": ("Skipped: no rules document configured. Set OPEN_BRAIN_BINDING_RULES "
                         "to audit one." if not rel else
                         f"Skipped: {rel} (OPEN_BRAIN_BINDING_RULES) not found in the vault.")}
    txt = fp.read_text(encoding="utf-8", errors="ignore")

    # --- Pattern 1: "N active checks" vs len(CHECKS) ---
    m = re.search(r"(\d+)\s+(?:checks activos|active checks)", txt)
    if m:
        declared = int(m.group(1))
        real = len(CHECKS)
        if declared != real:
            findings.append({
                "claim": m.group(0), "declared": declared, "real": real,
                "delta": real - declared,
                "issue": f"The rules document says '{m.group(0)}'; "
                         f"CHECKS has {real} registered today (delta {real - declared:+d})."})

    # --- Pattern 2: Hot Cache "~N tokens" vs real size / 4 ---
    hc_path = VAULT / "Resources" / "Hot Cache.md"
    real_tokens = None
    if hc_path.exists():
        try:
            real_tokens = round(len(hc_path.read_text(encoding="utf-8", errors="ignore")) / 4)
        except OSError:
            real_tokens = None
    # Only mentions on the same line as the words "Hot Cache"
    for line in txt.splitlines():
        if "Hot Cache" in line:
            mm = re.search(r"~\s*(\d+)\s*tokens", line)
            if mm and real_tokens is not None:
                declared_tok = int(mm.group(1))
                if abs(declared_tok - real_tokens) > declared_tok * 0.5:  # >50% drift
                    findings.append({
                        "claim": mm.group(0), "declared": declared_tok, "real": real_tokens,
                        "delta": real_tokens - declared_tok,
                        "context_line": line.strip()[:120],
                        "issue": f"The rules document cites '~{declared_tok} tokens' for the Hot Cache; "
                                 f"Resources/Hot Cache.md measures ~{real_tokens} tokens today "
                                 f"(delta {real_tokens - declared_tok:+d})."})

    severity = "important" if findings else "info"
    return {"id": 43, "name": name,
            "severity": severity,
            "count": len(findings),
            "findings": findings,
            "checks_registered_real": len(CHECKS),
            "hot_cache_tokens_real": real_tokens,
            "note": "Covers 2 patterns (N active checks, Hot Cache ~N tokens) — not a "
                    "generic parser of every figure cited in the document. See this "
                    "function's docstring for the why and the declared scope."}


def _significant_words(title):
    words = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9_.-]{3,}", title)
    seen, out = set(), []
    for w in words:
        wl = w.lower()
        if wl in _RECURRENCE_STOPWORDS or wl in seen:
            continue
        seen.add(wl)
        out.append(w)
    return out[:6]


# Short stopwords, Spanish and English (bilingual logs).
_RECURRENCE_STOPWORDS = set("""de el la los las en y a que no por para del al un una su
sus se es fue son este esta estos estas como sin mas ya solo tras entre desde
hasta cuando donde claude md the and for with from that this into over when
where what which without after before about then than""".split())


def check_44_rule_recurrence():
    """Recurrence counter: for each round in `Meta/Instruction Surface Log.md`,
    counts how many entries of `Resources/Session Log.md` DATED AFTER it mention
    the same topic (>=2 significant words of the round's title). A round with high
    recurrence is a rule that was "fixed" in the log and keeps showing up as
    friction in normal sessions. The check computes it instead of relying on
    memory.

    Method, deliberately simple. Extracts up to 6 significant words (>=4 letters,
    no short stopwords) from each round's title; a Session Log entry counts as a
    "recurrence" if it shares >=2 of those words AND is dated after the round. It
    is vocabulary intersection, not semantic understanding — it can fail by
    synonymy (false negative) or by domain coincidence (false positive on very
    general topics). Reported as a first-pass heuristic, not a verdict.

    Formats parsed: rounds as `## r<N> — YYYY-MM-DD · <title>`; Session Log
    entries as `## YYYY-MM-DD — <label>`. Skipped when either file is absent.

    `Meta/Instruction Surface Log.md` is optional and user-created: one
    `## r<N> — YYYY-MM-DD · <title>` heading per round of rule changes."""
    isl_path = VAULT / "Meta" / "Instruction Surface Log.md"
    log_path = VAULT / "Resources" / "Session Log.md"
    if not isl_path.exists() or not log_path.exists():
        missing = [str(p.relative_to(VAULT)) for p in (isl_path, log_path) if not p.exists()]
        return {"id": 44, "name": "Rule Recurrence (ISL vs Session Log)",
                "severity": "info", "count": 0, "findings": [], "skipped": True,
                "note": f"Skipped: files not found {missing}. Keep both logs to enable this check."}

    isl_txt = isl_path.read_text(encoding="utf-8", errors="ignore")
    rounds = []
    for m in re.finditer(r"^## r(\d+) — (\d{4}-\d{2}-\d{2}) · (.+)$", isl_txt, re.MULTILINE):
        rounds.append({"round": int(m.group(1)), "date": m.group(2), "title": m.group(3).strip()})

    log_txt = log_path.read_text(encoding="utf-8", errors="ignore")
    entries = []
    # A stricter pattern ("## DATE — [Domain]") loses entries whose header does not
    # put the domain in brackets right after the dash (free format). The generic
    # pattern avoids losing them over a formatting convention the log itself does
    # not follow consistently.
    headers = list(re.finditer(r"^## (\d{4}-\d{2}-\d{2}) — (.+)$", log_txt, re.MULTILINE))
    for i, hm in enumerate(headers):
        start = hm.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(log_txt)
        label = hm.group(2).strip()
        bm = re.search(r"\[(.+?)\]", label)
        domain = bm.group(1) if bm else label
        entries.append({"date": hm.group(1), "domain": domain, "body": log_txt[start:end]})

    findings = []
    for r in rounds:
        keywords = _significant_words(r["title"])
        if len(keywords) < 2:
            continue
        matches = []
        for e in entries:
            if e["date"] <= r["date"]:
                continue
            hits = sum(1 for kw in keywords if kw.lower() in e["body"].lower())
            if hits >= 2:
                matches.append({"date": e["date"], "domain": e["domain"], "keyword_hits": hits})
        if matches:
            findings.append({"round": r["round"], "round_date": r["date"], "title": r["title"],
                              "keywords_used": keywords, "recurrence_count": len(matches),
                              "session_log_matches": matches[:10]})

    findings.sort(key=lambda x: -x["recurrence_count"])
    high_recurrence = [f for f in findings if f["recurrence_count"] >= 2]
    severity = "important" if high_recurrence else ("maintenance" if findings else "info")

    return {"id": 44, "name": "Rule Recurrence (ISL vs Session Log)",
            "severity": severity,
            "count": len(findings),
            "rounds_measured": len(rounds),
            "session_log_entries_measured": len(entries),
            "high_recurrence_rounds": len(high_recurrence),
            "findings": findings[:15],
            "note": "Vocabulary-intersection heuristic (>=2 significant words of the round "
                    "title), not semantic understanding — see docstring. A round with "
                    "recurrence_count>=2 is a candidate to raise with the vault owner: a rule "
                    "that keeps being ignored should be flagged, not silently re-added."}


_SKILL_SOURCE_ROOTS = [".claude/skills"]
# Budget per SKILL.md. A skill that keeps a short SKILL.md (~3,000 tokens) and puts
# the rest in `references/`, `subskills/` or scripts that are read only when a step
# asks for them shows the pattern works; 4,000 is that ceiling with margin. If you
# raise it, raise it with a dated reason.
_SKILL_BUDGET_TOKENS = 4000
_SIDECAR_DIRS = ("references", "subskills", "scorer", "reference", "assets")


def check_45_skill_payload():
    """What INVOKING a skill costs, separate from what having it costs.

    Why it exists. `check_40` measures the vault's always-loaded layer. Neither it
    nor an instruction count sees the number paid on every invocation: the tokens
    of SKILL.md, which enter the context whole each time the skill fires. In a
    typical retrieve, instructions can weigh several times more than the notes
    served. Without this check, the savings of a refactor are opinion.

    What it measures. Per skill: `skill_tokens` (SKILL.md, paid every time the
    skill is invoked) and `sidecar_tokens` (what lives in references/ subskills/
    scorer/ and is only read when a step asks for it). The ratio between the two
    is the signal: a 22k SKILL.md with sidecar 0 is a monolith; a 3k one with 29k
    alongside is the progressive-disclosure pattern applied.

    What it does NOT do. It does not prune. Like `check_26` and `check_40`: the
    number says where to look, not what to delete. A SKILL.md over budget can be
    justified — what it cannot be is unmeasured. Skipped (not_run) when the
    skill root (`.claude/skills/`) does not exist inside the vault."""
    skills, missing_roots = [], []
    seen = set()
    for root_rel in _SKILL_SOURCE_ROOTS:
        root = VAULT / root_rel
        if not root.is_dir():
            missing_roots.append(root_rel)
            continue
        for sp in sorted(root.glob("*/SKILL.md")):
            name = sp.parent.name
            if name in seen:
                continue
            seen.add(name)
            try:
                b = len(sp.read_bytes())
            except OSError as exc:
                skills.append({"skill": name, "status": f"unreadable:{exc.__class__.__name__}"})
                continue
            side_b, side_files = 0, 0
            for d in _SIDECAR_DIRS:
                dp = sp.parent / d
                if not dp.is_dir():
                    continue
                for f in dp.rglob("*"):
                    if f.is_file() and f.suffix.lower() in (".md", ".tsv", ".py", ".txt"):
                        try:
                            side_b += f.stat().st_size
                            side_files += 1
                        except OSError:
                            pass
            skills.append({
                "skill": name, "source": root_rel,
                "bytes": b, "skill_tokens": round(b / 4),
                "sidecar_files": side_files, "sidecar_tokens": round(side_b / 4),
                "over_budget": round(b / 4) > _SKILL_BUDGET_TOKENS,
            })
    if missing_roots and len(missing_roots) == len(_SKILL_SOURCE_ROOTS):
        return _mk(45, "Skill Invocation Payload", "maintenance", 0,
                   failure_origin=f"no skill root exists in the vault: {missing_roots}")
    over = sorted((s for s in skills if s.get("over_budget")),
                  key=lambda s: -s["skill_tokens"])
    total = sum(s.get("skill_tokens", 0) for s in skills)
    return _mk(45, "Skill Invocation Payload", "maintenance", len(over),
               items=[{"skill": s["skill"], "skill_tokens": s["skill_tokens"],
                       "budget": _SKILL_BUDGET_TOKENS,
                       "over_by": s["skill_tokens"] - _SKILL_BUDGET_TOKENS,
                       "sidecar_tokens": s["sidecar_tokens"]} for s in over],
               skills=skills, skills_measured=len(skills),
               total_skill_tokens=total, budget_tokens=_SKILL_BUDGET_TOKENS,
               missing_roots=missing_roots,
               note=("`skill_tokens` is what enters the context on EVERY invocation; "
                     "`sidecar_tokens` only when a step asks for it. It measures plain "
                     "sources inside the vault, not what is installed in ~/.claude/skills "
                     "(unreachable from a remote session): if the plain source is not up to "
                     "date, this number measures the source, not what runs."))


def check_47_careo_pointers():
    """Careos that cite notes by code instead of by what they say.

    Why it exists. A Careo question should never cite a bare note prefix without
    its content; open-brain-extract provides the way (an alias carrying the claim),
    but an instruction nobody checks is only half followed. This turns it into a
    number.

    Counts, in `Resources/Careo/Pendiente — *.md` (pending Careos; the file-name
    prefix is an identifier kept as is), the wikilinks to code-prefixed notes
    without an alias and the loose codes in prose (outside wikilinks and
    `code`). Skipped (not_run) when `Resources/Careo/` does not exist."""
    items = []
    bare_re = re.compile(r"^[A-Z][A-Z0-9]{1,7}(-\d+)?\s*-\s")
    code_re = re.compile(r"(?<![\w|/-])[A-Z]{2,6}\d{0,2}-\d{2}(?![\w\]])")
    d = VAULT / "Resources" / "Careo"
    if not d.exists():
        return _mk(47, "Careo Pointers", "maintenance", 0, failure_origin="Resources/Careo does not exist")
    for fp in sorted(d.glob("Pendiente — *.md")):
        try:
            txt = fp.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        links = re.findall(r"\[\[([^\]]+)\]\]", txt)
        bare = [l for l in links if "|" not in l and bare_re.match(l)]
        parts = re.split(r"(\[\[[^\]]*\]\]|`[^`]*`)", txt)
        loose = [c for p in parts if not p.startswith(("[[", "`")) for c in code_re.findall(p)]
        if bare or loose:
            items.append({"file": fp.name, "bare_links": len(bare), "loose_codes": loose[:5]})
    return _mk(47, "Careo Pointers", "maintenance", len(items), items=items,
               note="Fix: alias [[note|claim from its description]]; without a description, the title without the prefix.")


CHECKS = {
    1: check_1_orphans, 3: check_3_stale, 4: check_4_function_coverage,
    5: check_5_inbox, 6: check_6_maturity,
    7: check_7_frontmatter, 8: check_8_broken_links, 9: check_9_low_conf_pillars,
    11: check_11_count_drift, 12: check_12_contradiction_candidates,
    13: check_13_ghosts, 16: check_16_crowding, 17: check_17_stale_claims,
    21: check_21_connector_diversity, 22: check_22_frontmatter_integrity,
    23: check_23_orphans_all, 24: check_24_unlinked_search_terms,
    25: check_25_taxonomy_adherence, 26: check_26_surface_sync,
    27: check_27_dormancy_candidates, 28: check_28_over_application,
    29: check_29_engine_stamp_drift,
    30: check_30_source_drift,
    31: check_31_mentor_attribution, 32: check_32_undistilled_mentors,
    33: check_33_log_bloat,
    34: check_34_pipeline_compression, 35: check_35_skill_sequence_signal,
    36: check_36_pn_provenance, 37: check_37_third_party_names,
    38: check_38_prune_witness, 39: check_39_batch_link_audit,
    40: check_40_instruction_layers, 41: check_41_endorsement_events,
    42: check_42_vocabulary, 43: check_43_binding_rules_drift,
    44: check_44_rule_recurrence, 45: check_45_skill_payload,
    46: check_46_description_claim, 47: check_47_careo_pointers,
}

# Checks with the {status, count, failure_origin} contract. The self-test runs them
# against a broken vault and a clean one: each must report on the first and stay
# silent on the second. Adding a check to the block without adding it here makes
# the self-test fail, which is the point.
STATUS_CHECKS = [36, 37, 38, 39, 40, 41, 42]


def vault_totals():
    t = {}
    for folder in ["Permanent Notes", "Literature Notes", "Inbox", "Cases",
                   "Domains", "Search Terms", "Fleeting Notes"]:
        b = VAULT / folder
        t[folder] = sum(1 for _ in b.rglob("*.md")) if b.exists() else 0
    return t


def run(selected=None, json_only=False, stdout_only=False):
    global READ_ONLY
    READ_ONLY = stdout_only
    if not VAULT.is_dir():
        raise SystemExit(f"ERROR: vault directory not found: {VAULT}. "
                         "Set OPEN_BRAIN_VAULT to your vault root.")
    ids = selected or sorted(CHECKS.keys())
    vs.SKIPPED.clear()
    findings = [CHECKS[i]() for i in ids if i in CHECKS]
    # Denominator and read failures, ALWAYS. Rule: no check may report 0 without
    # saying over how many notes and with how many failed reads. False zeros come
    # from not looking — a check that did not parse YAML, a scan that swallowed
    # OSErrors silently. A 0 without a denominator is not information.
    skipped = list(vs.SKIPPED)
    result = {
        "ok": True, "schema": "health-findings/1",
        "generated_at": NOW.isoformat(), "vault": str(VAULT),
        "totals": vault_totals(),
        "read_failures": len(skipped),
        "read_failures_sample": skipped[:10],
        "read_failures_caveat": (
            "0 failed reads: the counts cover the whole vault."
            if not skipped else
            f"WARNING: {len(skipped)} notes could not be read. Every 'count' in "
            f"this report is a LOWER BOUND and is not comparable with another pass."),
        "findings": findings,
        "judgment_pending": ["12 Contradiction Scan (semantic)",
                             "14 Mentor Photos (interactive)",
                             "15c Design Ref frontmatter (visual)",
                             "18 Myelination (run myelinate.py report)"],
    }
    # --stdout-only exists so a reader (a UI) can ask for the findings without
    # reading them rewriting them. A consumer that mutates its source when queried
    # is not a reader: it is another writer competing for the same file.
    out_path = VAULT / "Resources" / "Vault Health" / "findings.json"
    if not stdout_only:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if json_only or stdout_only:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps({"ok": True, "findings_path": str(out_path),
                          "totals": result["totals"],
                          "read_failures": result["read_failures"],
                          "read_failures_caveat": result["read_failures_caveat"],
                          "summary": {f["name"]: f.get("count", "—") for f in findings}},
                         ensure_ascii=False, indent=2))


# ============================================================
# SELF-TEST WITH A NEGATIVE FIXTURE
#
# The NEGATIVE fixture is a minimal, deliberately broken vault where every check
# in the status block MUST report. The POSITIVE one is the same vault fixed, where
# the same checks must stay silent. A check that passes the negative but not the
# positive detects nothing; one that passes the positive but not the negative is
# dead and nobody notices. Both are needed.
#
# Each fixture runs in a SUBPROCESS with OPEN_BRAIN_VAULT/VAULT_ROOT pointing to
# the test vault, through the same CLI you use. Testing the function from the
# inside and not the CLI would have left uncovered exactly what breaks: the
# registration in CHECKS and the --check plumbing.
# ============================================================

_FIX_NAME = "Invented Test Person"


def _w(base, rel, text):
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def _fixture(base, broken: bool):
    """Writes a minimal vault. broken=True -> the status checks must report."""
    recent = (TODAY - timedelta(days=3)).isoformat()

    # --- 36: provenance -------------------------------------------------
    for i, mentor in ((1, "Author One"), (2, "Author Two")):
        _w(base, f"Literature Notes/FIX-0{i} - Test note {i}.md",
           f"---\ntype: literature\nsource: \"[[Dossiers/Test Source]]\"\n"
           f"mentor: \"[[{mentor}]]\"\ncreated: {recent}\n---\n\nBody.\n")
    _w(base, "Dossiers/Test Source.md",
       "---\ntype: dossier\nauthor: \"[[Author One]]\"\n---\n\nBody.\n")
    # The mentor notes must exist: otherwise the "clean" fixture carries broken
    # `mentor:` wikilinks and check_39 rightly reports. The self-test found this
    # on its first pass — the fixture was wrong, not the check.
    for m in ("Author One", "Author Two"):
        _w(base, f"Mentors/{m}.md", "---\ntype: mentor\n---\n\nBody.\n")
    _w(base, "Permanent Notes/Healthy Test PN.md",
       "---\ntype: permanent\nsources:\n  - \"[[FIX-01 - Test note 1]]\"\n"
       "  - \"[[FIX-02 - Test note 2]]\"\n---\n\nBody.\n")
    if broken:
        # a reference that does not resolve + a single-author PN
        _w(base, "Permanent Notes/PN With Broken Source.md",
           "---\ntype: permanent\nsources:\n  - \"[[Note That Does Not Exist On Disk]]\"\n"
           "  - \"[[FIX-01 - Test note 1]]\"\n---\n\nBody.\n")
        _w(base, "Permanent Notes/Single Author PN.md",
           "---\ntype: permanent\nsources:\n  - \"[[FIX-01 - Test note 1]]\"\n"
           "  - \"[[Dossiers/Test Source]]\"\n---\n\nBody.\n")

    # --- 41: approval as an event ----------------------------------------
    if broken:
        _w(base, "Permanent Notes/Unapproved Test PN.md",
           f"---\ntype: permanent\ncreated: {recent}\nsources:\n"
           "  - \"[[FIX-01 - Test note 1]]\"\n  - \"[[FIX-02 - Test note 2]]\"\n"
           "---\n\nBody.\n")
    else:
        _w(base, "Permanent Notes/Approved Test PN.md",
           f"---\ntype: permanent\ncreated: {recent}\nendorsed_at: {recent}\n"
           "endorsed_via: sesion\nsources:\n  - \"[[FIX-01 - Test note 1]]\"\n"
           "  - \"[[FIX-02 - Test note 2]]\"\n---\n\nBody.\n\n"
           f"## Historial\n\n{recent} - approved - fixture\n")

    # --- 37: third-party names ------------------------------------------
    _w(base, "Meta/third-party-names.txt", f"# fixture\n{_FIX_NAME}\n")
    if broken:
        _w(base, f"Manuscripts/Recap for {_FIX_NAME}.md",
           "---\ntype: manuscript\n---\n\nBody.\n")

    # --- 38: witness log -------------------------------------------------
    _w(base, "Resources/Hot Cache — Cambios Archive.md",
       "---\ntype: resource\n---\n\n# Changes Archive\n\n## Archived 2026-01-15\n\n- something\n")
    if not broken:
        _w(base, "Resources/Vault Health/witness-log.jsonl",
           json.dumps({"ts": "2026-01-15T00:00:00+00:00", "op": "fold",
                       "source": "Resources/Hot Cache.md",
                       "destination": "Resources/Hot Cache — Cambios Archive.md",
                       "items": 1, "bytes_before": 10, "bytes_after": 5},
                      ensure_ascii=False) + "\n")

    # --- 39: wikilink audit per batch -----------------------------------
    # The batch's term has a page in Search Terms/ on purpose: if it did not,
    # check_42 would count it as a free term and the CLEAN fixture would report.
    # Fixtures are shared, so a new check can invalidate another's positive —
    # which is what this harness exists to catch.
    _w(base, "Search Terms/Test Term.md",
       "---\ntype: search-term\nterm: \"Test Term\"\n"
       "aliases:\n  - \"trial term\"\n---\n\nBody.\n")
    n = 10
    for i in range(n):
        link = "[[Search Term That Does Not Exist]]" if broken else "[[Test Term]]"
        _w(base, f"Literature Notes/BATCH-{i:02d} - Batch note.md",
           f"---\ntype: literature\nsource: \"[[Dossiers/Test Source]]\"\n"
           f"mentor: \"[[Author One]]\"\ncreated: {recent}\n"
           f"search_terms:\n  - \"{link}\"\n---\n\nBody.\n")

    # --- 42: vocabulary --------------------------------------------------
    # (a) control note with three invented terms — the case that must be tested
    #     explicitly: the check has to go red with it.
    if broken:
        _w(base, "Literature Notes/CTRL-01 - Vocabulary control note.md",
           f"---\ntype: literature\nsource: \"[[Dossiers/Test Source]]\"\n"
           f"mentor: \"[[Author One]]\"\ncreated: {recent}\n"
           "domains:\n  - \"[[Test Leadership]]\"\n"
           "search_terms:\n  - \"[[Invented Term One]]\"\n"
           "  - \"[[Invented Term Two]]\"\n  - \"[[Invented Term Three]]\"\n"
           "---\n\nBody.\n")
    # (b) hierarchical hub with a Domain parent: over-applied in the broken one
    #     (2 of 20 declare the domain), well applied in the clean one (20 of 20).
    _w(base, "Domains/Test Leadership.md", "---\ntype: domain\n---\n\nBody.\n")
    _w(base, "Search Terms/Test Leadership — Feedback.md",
       "---\ntype: search-term\nterm: \"Test Leadership — Feedback\"\n---\n\nBody.\n")
    for i in range(20):
        with_domain = (not broken) or i < 2
        dom = "domains:\n  - \"[[Test Leadership]]\"\n" if with_domain else ""
        _w(base, f"Literature Notes/HUB-{i:02d} - Hub note.md",
           f"---\ntype: literature\nsource: \"[[Dossiers/Test Source]]\"\n"
           f"mentor: \"[[Author One]]\"\ncreated: {recent}\n{dom}"
           "search_terms:\n  - \"[[Test Leadership — Feedback]]\"\n---\n\nBody.\n")

    # --- 40: cost per layer ----------------------------------------------
    _w(base, "CLAUDE.md", "# Contract\n\n- One rule.\n")
    hot = "- hot cache line\n" * (9000 if broken else 5)
    _w(base, "Resources/Hot Cache.md", f"---\nupdated: {recent}\n---\n\n{hot}")
    _w(base, "Resources/Hot Cache - Active Context.md", "# Active\n\n- something\n")
    for rel in _ON_DEMAND:
        _w(base, rel, "# Tier 2\n\n- one rule.\n")


def _run_fixture(base):
    env = dict(os.environ, VAULT_ROOT=str(base), OPEN_BRAIN_VAULT=str(base),
               OPEN_BRAIN_ENDORSEMENT_CUTOFF="",
               OPEN_BRAIN_ALWAYS_SURFACES=("CLAUDE.md,Resources/Hot Cache.md,"
                                           "Resources/Hot Cache - Active Context.md"))
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "run",
         "--check", ",".join(str(i) for i in STATUS_CHECKS), "--stdout-only"],
        capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise SystemExit(f"self-test: the engine failed on the fixture\n{proc.stderr}")
    return {f["id"]: f for f in json.loads(proc.stdout)["findings"]}


def self_test():
    import tempfile
    failures, rows = [], []
    with tempfile.TemporaryDirectory() as td:
        neg, pos = Path(td) / "broken", Path(td) / "clean"
        _fixture(neg, broken=True)
        _fixture(pos, broken=False)
        got_neg, got_pos = _run_fixture(neg), _run_fixture(pos)

    for cid in STATUS_CHECKS:
        n, p = got_neg.get(cid), got_pos.get(cid)
        if n is None or p is None:
            failures.append(f"check {cid}: missing from the output "
                            "(registered in CHECKS and in STATUS_CHECKS?)")
            continue
        for f, tag in ((n, "negative"), (p, "positive")):
            for k in ("status", "count", "failure_origin"):
                if k not in f:
                    failures.append(f"check {cid} ({tag}): '{k}' missing from the output")
            if f.get("status") == "not_run":
                failures.append(f"check {cid} ({tag}): not_run — {f.get('failure_origin')}")
        if n.get("count", 0) < 1:
            failures.append(f"check {cid}: the NEGATIVE fixture reports nothing "
                            "(the check is dead or the fixture broke)")
        if p.get("count", 1) != 0:
            failures.append(f"check {cid}: the POSITIVE fixture reports "
                            f"{p.get('count')} (false positive)")
        rows.append({"id": cid, "name": n.get("name"),
                     "negative": {"status": n.get("status"), "count": n.get("count")},
                     "positive": {"status": p.get("status"), "count": p.get("count")}})

    print(json.dumps({"ok": not failures, "checks": rows, "failures": failures},
                     ensure_ascii=False, indent=2))
    return 0 if not failures else 1


def main():
    global _ENDORSEMENT_CUTOFF
    ap = argparse.ArgumentParser(description="Deterministic health checks for an Open Brain vault.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the checks and write Resources/Vault Health/findings.json")
    r.add_argument("--json", action="store_true", help="print the raw JSON to stdout")
    r.add_argument("--stdout-only", action="store_true",
                   help="JSON to stdout without rewriting findings.json (pure read)")
    r.add_argument("--check", default=None, help="comma-separated check ids: 1,3,6")
    r.add_argument("--endorsement-cutoff", default=None,
                   help="YYYY-MM-DD from which check 41 applies (default: "
                        "OPEN_BRAIN_ENDORSEMENT_CUTOFF, or every dated PN)")
    sub.add_parser("self-test", help="negative + positive fixtures for the status checks (36-42)")
    args = ap.parse_args()
    if args.cmd == "run":
        if args.endorsement_cutoff is not None:
            _ENDORSEMENT_CUTOFF = args.endorsement_cutoff.strip()
        sel = [int(x) for x in args.check.split(",")] if args.check else None
        run(sel, args.json, args.stdout_only)
    elif args.cmd == "self-test":
        raise SystemExit(self_test())


if __name__ == "__main__":
    main()
