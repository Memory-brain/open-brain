#!/usr/bin/env python3
"""
eval-engine — evaluation system for an Open Brain vault.

Collects L1 metrics (mechanical, 100% deterministic) across 6 dimensions,
writes timestamped JSON to Resources/Evals/, and generates a markdown report
with trends vs the previous eval.

Usage:
    python3 eval_engine.py run                  # full eval → JSON + MD
    python3 eval_engine.py run --json           # raw JSON to stdout only
    python3 eval_engine.py run --dim graph      # a single dimension
    python3 eval_engine.py trend                # trend over the last 5 evals
    python3 eval_engine.py trend --last 10      # last 10

Dimensions: integrity, graph, pipeline, practice, funnel, output

The vault is auto-detected (needs vault-scan/vaultscan.py next to this engine).
Override with OPEN_BRAIN_VAULT (or the older VAULT_ROOT).

Engine data (autolink/, Flashcards/ or $OPEN_BRAIN_FLASHCARDS_DIR, Manuscripts/, Practice Log/) is looked
up in the vault root, where the engines are installed; for older layouts where
those folders sit one level above the vault, the parent is used as a fallback.
"""

# `X | None` in annotations is 3.10+; on Python 3.9 the module crashed on
# import. With this future import annotations are not evaluated and it runs.
from __future__ import annotations


import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path


# ============================================================
# BOOTSTRAP — import vault-scan (the single shared core)
# ============================================================

def _bootstrap_vaultscan():
    # OPEN_BRAIN_VAULT is the public override; vaultscan itself reads VAULT_ROOT.
    if os.environ.get("OPEN_BRAIN_VAULT") and not os.environ.get("VAULT_ROOT"):
        os.environ["VAULT_ROOT"] = os.environ["OPEN_BRAIN_VAULT"]
    env = os.environ.get("VAULT_ROOT")
    bases = ([Path(env)] if env else []) + [Path(__file__).resolve().parent,
                                            *Path(__file__).resolve().parents]
    for base in bases:
        for cand in [base / "vault-scan", base]:
            if (cand / "vaultscan.py").exists():
                sys.path.insert(0, str(cand)); return
    raise SystemExit("ERROR: vault-scan/vaultscan.py not found. Install the engines in your "
                     "vault root or set OPEN_BRAIN_VAULT.")


_bootstrap_vaultscan()
import vaultscan as vs  # noqa: E402

VAULT = vs.VAULT
# Folder holding engine data (autolink/, Flashcards/, Manuscripts/). With the
# standard install the engines live in the vault root; older layouts kept them
# one level above the vault, so fall back to the parent when that is where they are.
OUTER = VAULT if (VAULT / "autolink").exists() or not (VAULT.parent / "autolink").exists() \
    else VAULT.parent
FM_RE = vs.FM_RE
WIKILINK_RE = vs.WIKILINK_RE
parse_fm = vs.parse_fm
notes = vs.iter_notes
body_of = vs.body_of
all_stems = vs.all_stems
days_since = vs.days_since
as_list = vs.as_list

NOW = datetime.now(timezone.utc)
TODAY = date.today()
EVALS_DIR = VAULT / "Resources" / "Evals"


# Older vaults wrote the LN voice_state with the owner's name instead of
# "extended-by-owner". List any such legacy values here to keep counting them.
LEGACY_EXTENDED: tuple = ()


def to_int(v, default=0) -> int:
    try:
        return int(str(v).strip())
    except (ValueError, TypeError):
        return default


# ============================================================
# DIM 1 — VAULT INTEGRITY
# ============================================================

def dim_integrity() -> dict:
    """Frontmatter compliance, broken links, orphan PNs."""
    total, compliant, missing_type, missing_layer = 0, 0, 0, 0
    for folder, need_layer in [("Permanent Notes", True), ("Literature Notes", True),
                                ("Inbox", False), ("Cases", False)]:
        for p, text in notes(folder):
            total += 1
            fm = parse_fm(text)
            has_type = bool(fm.get("type"))
            has_layer = bool(fm.get("layer")) if need_layer else True
            if has_type and has_layer:
                compliant += 1
            if not has_type:
                missing_type += 1
            if need_layer and not fm.get("layer"):
                missing_layer += 1

    # Broken links (PNs only for speed)
    stems = all_stems()
    broken = []
    for p, text in notes("Permanent Notes"):
        for t in vs.wikilinks(body_of(text)):
            if t and t not in stems:
                broken.append({"in": p.stem, "target": t})

    # Orphan PNs (0 outgoing wikilinks in body)
    orphans = []
    for p, text in notes("Permanent Notes"):
        if not WIKILINK_RE.search(body_of(text)):
            orphans.append(p.stem)

    # Count drift (Dossiers declared vs actual LN count)
    ln_stems = [p.stem for p in (VAULT / "Literature Notes").rglob("*.md")] \
        if (VAULT / "Literature Notes").exists() else []
    drift_items = []
    for p, text in notes("Dossiers"):
        fm = parse_fm(text)
        if "literature_notes_count" not in fm:
            continue
        declared = to_int(fm.get("literature_notes_count"), -1)
        prefix = (fm.get("ln_prefix") or "").strip()
        if prefix:
            real = sum(1 for s in ln_stems if s.startswith(prefix))
            if declared >= 0 and real != declared:
                drift_items.append({"dossier": p.stem, "declared": declared,
                                    "real": real, "delta": real - declared})

    pct = round(compliant / total * 100, 1) if total else 0
    return {
        "dimension": "integrity",
        "frontmatter_compliance_pct": pct,
        "total_notes_scanned": total,
        "compliant": compliant,
        "missing_type": missing_type,
        "missing_layer": missing_layer,
        "broken_links": len(broken),
        "broken_links_sample": broken[:10],
        "orphan_pns": len(orphans),
        "orphan_pns_sample": orphans[:10],
        "count_drift_items": len(drift_items),
        "count_drift_sample": drift_items[:10],
    }


# ============================================================
# DIM 2 — GRAPH HEALTH
# ============================================================

def dim_graph() -> dict:
    """Signal/noise ratio, edge type distribution, myelination."""
    graph_path = OUTER / "autolink" / "graph.jsonl"
    entities_path = OUTER / "autolink" / "entities.json"

    edges, type_counts = [], Counter()
    noise_types = {"menciona", "cita", "relacionada_con"}

    if graph_path.exists():
        for line in graph_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                edges.append(e)
                type_counts[e.get("type", "unknown")] += 1
            except json.JSONDecodeError:
                continue

    total_edges = len(edges)
    noise_count = sum(type_counts.get(t, 0) for t in noise_types)
    signal_count = total_edges - noise_count
    signal_ratio = round(signal_count / total_edges * 100, 1) if total_edges else 0

    # Generative types (the valuable ones)
    generative_types = {"contradice", "refuta", "refina", "extiende", "cross_domain",
                        "validado_por", "ejemplifica", "aplica_a", "alimenta", "depende_de"}
    generative_count = sum(type_counts.get(t, 0) for t in generative_types)
    generative_ratio = round(generative_count / total_edges * 100, 1) if total_edges else 0

    # Entity count
    entity_count = 0
    if entities_path.exists():
        try:
            data = json.loads(entities_path.read_text(encoding="utf-8", errors="ignore"))
            entity_count = len(data) if isinstance(data, list) else len(data)
        except (json.JSONDecodeError, OSError):
            pass

    edges_per_entity = round(total_edges / entity_count, 2) if entity_count else 0

    # Myelination state
    myelin_state = OUTER / "autolink" / "myelination-state.json"
    myelin_stats = {"available": False}
    if myelin_state.exists():
        try:
            mdata = json.loads(myelin_state.read_text(encoding="utf-8", errors="ignore"))
            weights = [e.get("weight", 1.0) for e in mdata if isinstance(e, dict)]
            if weights:
                myelin_stats = {
                    "available": True,
                    "count": len(weights),
                    "min": round(min(weights), 3),
                    "max": round(max(weights), 3),
                    "mean": round(sum(weights) / len(weights), 3),
                }
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "dimension": "graph",
        "total_edges": total_edges,
        "total_entities": entity_count,
        "edges_per_entity": edges_per_entity,
        "signal_noise_ratio_pct": signal_ratio,
        "generative_ratio_pct": generative_ratio,
        "generative_count": generative_count,
        "type_distribution": dict(type_counts.most_common()),
        "myelination": myelin_stats,
    }


# ============================================================
# DIM 3 — PIPELINE FLOW
# ============================================================

def dim_pipeline() -> dict:
    """Inbox age, source coverage, endorsement states, promote backlog."""
    # Inbox age distribution
    inbox_total, inbox_stale, inbox_ages = 0, 0, []
    for p, text in notes("Inbox"):
        inbox_total += 1
        fm = parse_fm(text)
        d = days_since(fm.get("created"))
        if d is not None:
            inbox_ages.append(d)
            if d > 30:
                inbox_stale += 1

    # Source coverage from Dossiers
    coverage_counts = Counter()
    for p, text in notes("Dossiers"):
        fm = parse_fm(text)
        vc = (fm.get("vault_coverage") or "").strip().lower()
        if "complete" in vc or "completo" in vc:
            coverage_counts["complete"] += 1
        elif "partial" in vc:
            coverage_counts["partial"] += 1
        elif "literature" in vc:
            coverage_counts["literature_only"] += 1
        elif "sin notas" in vc or "pendiente" in vc or "no notes" in vc or "pending" in vc:
            coverage_counts["pending"] += 1
        elif vc:
            coverage_counts["other"] += 1

    # Endorsement state distribution (PNs)
    endorsement = Counter()
    pn_total = 0
    for p, text in notes("Permanent Notes"):
        pn_total += 1
        fm = parse_fm(text)
        es = (fm.get("endorsement_state") or "").strip().lower()
        if es:
            endorsement[es] += 1
        else:
            endorsement["missing"] += 1

    # Promote backlog: LNs with voice_state != extended-by-owner
    # (LEGACY_EXTENDED: the pre-rename value is still accepted when reading)
    voice_states = Counter()
    ln_total = 0
    for p, text in notes("Literature Notes"):
        ln_total += 1
        fm = parse_fm(text)
        vs_val = (fm.get("voice_state") or "").strip().lower()
        if vs_val:
            voice_states[vs_val] += 1
        else:
            voice_states["missing"] += 1

    extended = voice_states.get("extended-by-owner", 0) + \
        sum(voice_states.get(v, 0) for v in LEGACY_EXTENDED)
    awaiting_owner = voice_states.get("with-claude-connectors", 0)

    return {
        "dimension": "pipeline",
        "inbox_total": inbox_total,
        "inbox_stale_30d": inbox_stale,
        "inbox_median_age_days": sorted(inbox_ages)[len(inbox_ages)//2] if inbox_ages else None,
        "source_coverage": dict(coverage_counts),
        "endorsement_distribution": dict(endorsement),
        "pn_total": pn_total,
        "pn_endorsed_pct": round(endorsement.get("endorsed", 0) / pn_total * 100, 1)
            if pn_total else 0,
        "ln_total": ln_total,
        "voice_state_distribution": dict(voice_states),
        "ln_extended_by_owner": extended,
        "ln_awaiting_owner": awaiting_owner,
        "owner_extension_rate_pct": round(extended / ln_total * 100, 1)
            if ln_total else 0,
    }


# ============================================================
# DIM 4 — PRACTICE & RETENTION
# ============================================================

def dim_practice() -> dict:
    """SM-2 flashcard accuracy, practice log counts."""
    flashcard_dir = Path(os.environ["OPEN_BRAIN_FLASHCARDS_DIR"]) if os.environ.get("OPEN_BRAIN_FLASHCARDS_DIR") else OUTER / "Flashcards"
    domains = []

    if flashcard_dir.exists():
        for sf in flashcard_dir.glob("state-*.json"):
            try:
                data = json.loads(sf.read_text(encoding="utf-8", errors="ignore"))
                domain = data.get("domain", sf.stem.replace("state-", ""))
                cards = data.get("cards", {})
                total_cards = len(cards)
                correct, wrong, weak, strong = 0, 0, 0, 0
                for cname, cdata in cards.items():
                    c = cdata.get("correct", 0)
                    w = cdata.get("wrong", 0)
                    correct += c
                    wrong += w
                    total_reviews = c + w
                    if total_reviews > 0:
                        acc = c / total_reviews
                        if acc <= 0.33:
                            weak += 1
                        elif acc >= 0.9:
                            strong += 1

                sessions = data.get("sessions", [])
                accuracy = round(correct / (correct + wrong) * 100, 1) \
                    if (correct + wrong) > 0 else None

                domains.append({
                    "domain": domain,
                    "total_cards": total_cards,
                    "total_sessions": len(sessions),
                    "accuracy_pct": accuracy,
                    "weak_cards": weak,
                    "strong_cards": strong,
                })
            except (json.JSONDecodeError, OSError):
                continue

    # Practice logs
    log_dir = VAULT / "Practice Log"
    if not log_dir.exists():
        log_dir = OUTER / "Practice Log"
    log_total = 0
    log_recent_7d = 0
    if log_dir.exists():
        for p in log_dir.glob("*.md"):
            log_total += 1
            m = re.search(r"(\d{4}-\d{2}-\d{2})", p.stem)
            if m:
                d = days_since(m.group(1))
                if d is not None and d <= 7:
                    log_recent_7d += 1

    total_weak = sum(d["weak_cards"] for d in domains)
    total_cards = sum(d["total_cards"] for d in domains)
    overall_acc_vals = [d["accuracy_pct"] for d in domains if d["accuracy_pct"] is not None]
    overall_accuracy = round(sum(overall_acc_vals) / len(overall_acc_vals), 1) \
        if overall_acc_vals else None

    return {
        "dimension": "practice",
        "flashcard_domains": domains,
        "flashcard_total_cards": total_cards,
        "flashcard_overall_accuracy_pct": overall_accuracy,
        "flashcard_weak_cards": total_weak,
        "practice_logs_total": log_total,
        "practice_logs_last_7d": log_recent_7d,
    }


# ============================================================
# DIM 5 — KNOWLEDGE FUNNEL
# ============================================================

def dim_funnel() -> dict:
    """Source → Inbox → LN → PN conversion, voice_state, endorsement."""
    counts = {}
    for folder in ["Permanent Notes", "Literature Notes", "Inbox", "Cases",
                    "Domains", "Search Terms", "Fleeting Notes", "Dossiers", "Ideas"]:
        b = VAULT / folder
        counts[folder] = sum(1 for _ in b.rglob("*.md")) if b.exists() else 0

    # PN metrics aggregation
    confidence_dist = Counter()
    maturity_dist = Counter()
    layer_dist = Counter()
    times_retrieved_vals = []
    external_outputs_sum = 0

    for p, text in notes("Permanent Notes"):
        fm = parse_fm(text)
        conf = (fm.get("confidence") or "missing").strip().lower()
        mat = (fm.get("maturity") or "missing").strip().lower()
        lyr = (fm.get("layer") or "missing").strip().lower()
        confidence_dist[conf] += 1
        maturity_dist[mat] += 1
        layer_dist[lyr] += 1
        tr = to_int(fm.get("times_retrieved"))
        times_retrieved_vals.append(tr)
        external_outputs_sum += to_int(fm.get("external_outputs"))

    # Funnel conversion rates
    dossiers = counts.get("Dossiers", 0)
    lns = counts.get("Literature Notes", 0)
    pns = counts.get("Permanent Notes", 0)
    ln_to_pn = round(pns / lns * 100, 1) if lns else 0
    pns_retrieved = sum(1 for v in times_retrieved_vals if v > 0)
    pns_used = external_outputs_sum

    return {
        "dimension": "funnel",
        "note_counts": counts,
        "funnel": {
            "dossiers": dossiers,
            "literature_notes": lns,
            "permanent_notes": pns,
            "ln_to_pn_ratio_pct": ln_to_pn,
        },
        "pn_confidence": dict(confidence_dist.most_common()),
        "pn_maturity": dict(maturity_dist.most_common()),
        "pn_layer_distribution": dict(layer_dist.most_common()),
        "times_retrieved": {
            "total_pns": len(times_retrieved_vals),
            "never_retrieved": sum(1 for v in times_retrieved_vals if v == 0),
            "retrieved_1plus": pns_retrieved,
            "retrieved_3plus": sum(1 for v in times_retrieved_vals if v >= 3),
            "max": max(times_retrieved_vals) if times_retrieved_vals else 0,
        },
        "external_outputs_sum": external_outputs_sum,
    }


# ============================================================
# DIM 6 — OUTPUT METRICS
# ============================================================

def dim_output() -> dict:
    """Ideas, published ideas, manuscripts, output signals."""
    ideas_dir = VAULT / "Ideas"
    ideas_total = sum(1 for _ in ideas_dir.rglob("*.md")) if ideas_dir.exists() else 0

    # "Ideas/Published" (older vaults: "Ideas/Publicados")
    published = 0
    for sub in ("Published", "Publicados"):
        d = VAULT / "Ideas" / sub
        if d.exists():
            published += sum(1 for _ in d.rglob("*.md"))

    manuscripts_dir = OUTER / "Manuscripts"
    manuscripts = 0
    if manuscripts_dir.exists():
        for p in manuscripts_dir.rglob("*"):
            if p.is_file() and p.suffix in {".md", ".docx", ".pdf"}:
                manuscripts += 1

    # Rejected PNs (quality gate signal)
    rejected_dir = VAULT / "Permanent Notes" / "Rejected"
    rejected = sum(1 for _ in rejected_dir.rglob("*.md")) if rejected_dir.exists() else 0

    return {
        "dimension": "output",
        "ideas_total": ideas_total,
        "published": published,
        "manuscripts": manuscripts,
        "rejected_pns": rejected,
        "publication_rate": f"{published}/{ideas_total}" if ideas_total else "0/0",
    }


# ============================================================
# REPORT GENERATION
# ============================================================

DIMENSIONS = {
    "integrity": dim_integrity,
    "graph": dim_graph,
    "pipeline": dim_pipeline,
    "practice": dim_practice,
    "funnel": dim_funnel,
    "output": dim_output,
}


def _load_previous_eval() -> dict | None:
    """Load the most recent eval JSON for comparison."""
    if not EVALS_DIR.exists():
        return None
    evals = sorted(EVALS_DIR.glob("*.json"), reverse=True)
    if not evals:
        return None
    try:
        return json.loads(evals[0].read_text(encoding="utf-8", errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return None


# Keys renamed in the public version; older eval JSONs are still readable.
_LEGACY_KEYS = {
    "published": "publicados",
}


def _legacy(d: dict, key: str):
    """d[key], falling back to the pre-rename key in older eval files."""
    if not d:
        return None
    v = d.get(key)
    if v is None and key in _LEGACY_KEYS:
        v = d.get(_LEGACY_KEYS[key])
    return v


def _delta(current, previous, fmt=".1f"):
    """Compute delta string between two values."""
    c = current
    p = previous
    if c is None or p is None:
        return ""
    diff = c - p
    if diff == 0:
        return " (=)"
    sign = "+" if diff > 0 else ""
    return f" ({sign}{diff:{fmt}})"


def generate_report(result: dict, prev: dict | None) -> str:
    """Generate markdown report from eval result."""
    lines = [
        f"# Open Brain Eval — {result['timestamp'][:10]}",
        "",
        f"> Vault: `{result['vault']}`  ",
        f"> Generated: {result['timestamp']}  ",
        f"> Previous eval: {prev['timestamp'][:10] if prev else 'none'}",
        "",
    ]

    # Helper to get prev dim
    def pdim(name):
        if not prev:
            return {}
        for d in prev.get("dimensions", []):
            if d.get("dimension") == name:
                return d
        return {}

    # --- INTEGRITY ---
    d = next((x for x in result["dimensions"] if x["dimension"] == "integrity"), {})
    pd = pdim("integrity")
    if d:
        dl = _delta(d.get("frontmatter_compliance_pct"), pd.get("frontmatter_compliance_pct"))
        lines += [
            "## 1. Vault Integrity",
            "",
            f"| Metric | Value |",
            f"|---|---|",
            f"| Frontmatter compliance | {d.get('frontmatter_compliance_pct', '?')}%{dl} |",
            f"| Broken links (PNs) | {d.get('broken_links', '?')}{_delta(d.get('broken_links'), pd.get('broken_links'), fmt='d')} |",
            f"| Orphan PNs | {d.get('orphan_pns', '?')}{_delta(d.get('orphan_pns'), pd.get('orphan_pns'), fmt='d')} |",
            f"| Count drift items | {d.get('count_drift_items', '?')} |",
            "",
        ]

    # --- GRAPH ---
    d = next((x for x in result["dimensions"] if x["dimension"] == "graph"), {})
    pd = pdim("graph")
    if d:
        lines += [
            "## 2. Graph Health",
            "",
            f"| Metric | Value |",
            f"|---|---|",
            f"| Total edges | {d.get('total_edges', '?')}{_delta(d.get('total_edges'), pd.get('total_edges'), fmt='d')} |",
            f"| Total entities | {d.get('total_entities', '?')} |",
            f"| Edges/entity | {d.get('edges_per_entity', '?')} |",
            f"| Signal/noise ratio | {d.get('signal_noise_ratio_pct', '?')}%{_delta(d.get('signal_noise_ratio_pct'), pd.get('signal_noise_ratio_pct'))} |",
            f"| Generative ratio | {d.get('generative_ratio_pct', '?')}%{_delta(d.get('generative_ratio_pct'), pd.get('generative_ratio_pct'))} |",
            f"| Generative edges | {d.get('generative_count', '?')} |",
            "",
            "**Edge type distribution:**",
            "",
        ]
        for etype, count in sorted(d.get("type_distribution", {}).items(),
                                     key=lambda x: -x[1]):
            lines.append(f"- `{etype}`: {count}")
        lines.append("")

    # --- PIPELINE ---
    d = next((x for x in result["dimensions"] if x["dimension"] == "pipeline"), {})
    pd = pdim("pipeline")
    if d:
        lines += [
            "## 3. Pipeline Flow",
            "",
            f"| Metric | Value |",
            f"|---|---|",
            f"| Inbox total | {d.get('inbox_total', '?')} |",
            f"| Inbox stale (>30d) | {d.get('inbox_stale_30d', '?')} |",
            f"| Inbox median age | {d.get('inbox_median_age_days', '?')}d |",
            f"| LN total | {d.get('ln_total', '?')} |",
            f"| PN total | {d.get('pn_total', '?')} |",
            f"| Owner extension rate | {d.get('owner_extension_rate_pct', '?')}%{_delta(d.get('owner_extension_rate_pct'), _legacy(pd, 'owner_extension_rate_pct'))} |",
            f"| LNs awaiting owner | {d.get('ln_awaiting_owner', '?')} |",
            f"| PN endorsed % | {d.get('pn_endorsed_pct', '?')}% |",
            "",
            "**Source coverage:**",
            "",
        ]
        for k, v in d.get("source_coverage", {}).items():
            lines.append(f"- `{k}`: {v}")
        lines += [
            "",
            "**Endorsement distribution:**",
            "",
        ]
        for k, v in d.get("endorsement_distribution", {}).items():
            lines.append(f"- `{k}`: {v}")
        lines.append("")

    # --- PRACTICE ---
    d = next((x for x in result["dimensions"] if x["dimension"] == "practice"), {})
    pd = pdim("practice")
    if d:
        lines += [
            "## 4. Practice & Retention",
            "",
            f"| Metric | Value |",
            f"|---|---|",
            f"| Flashcard domains | {len(d.get('flashcard_domains', []))} |",
            f"| Total cards | {d.get('flashcard_total_cards', '?')} |",
            f"| Overall accuracy | {d.get('flashcard_overall_accuracy_pct', '?')}% |",
            f"| Weak cards (≤33%) | {d.get('flashcard_weak_cards', '?')} |",
            f"| Practice logs total | {d.get('practice_logs_total', '?')} |",
            f"| Practice logs (7d) | {d.get('practice_logs_last_7d', '?')} |",
            "",
        ]
        if d.get("flashcard_domains"):
            lines += ["**Per domain:**", ""]
            for fd in d["flashcard_domains"]:
                lines.append(f"- **{fd['domain']}**: {fd['total_cards']} cards, "
                             f"{fd['accuracy_pct']}% acc, "
                             f"{fd['weak_cards']} weak, {fd['strong_cards']} strong, "
                             f"{fd['total_sessions']} sessions")
            lines.append("")

    # --- FUNNEL ---
    d = next((x for x in result["dimensions"] if x["dimension"] == "funnel"), {})
    pd = pdim("funnel")
    if d:
        f_data = d.get("funnel", {})
        tr = d.get("times_retrieved", {})
        lines += [
            "## 5. Knowledge Funnel",
            "",
            f"| Stage | Count |",
            f"|---|---|",
            f"| Dossiers (sources) | {f_data.get('dossiers', '?')} |",
            f"| Literature Notes | {f_data.get('literature_notes', '?')} |",
            f"| Permanent Notes | {f_data.get('permanent_notes', '?')} |",
            f"| LN → PN ratio | {f_data.get('ln_to_pn_ratio_pct', '?')}% |",
            "",
            f"| Retrieval | Count |",
            f"|---|---|",
            f"| Never retrieved | {tr.get('never_retrieved', '?')} |",
            f"| Retrieved 1+ | {tr.get('retrieved_1plus', '?')} |",
            f"| Retrieved 3+ | {tr.get('retrieved_3plus', '?')} |",
            f"| Max retrievals | {tr.get('max', '?')} |",
            f"| External outputs | {d.get('external_outputs_sum', '?')} |",
            "",
        ]

    # --- OUTPUT ---
    d = next((x for x in result["dimensions"] if x["dimension"] == "output"), {})
    pd = pdim("output")
    if d:
        lines += [
            "## 6. Output Metrics",
            "",
            f"| Metric | Value |",
            f"|---|---|",
            f"| Ideas total | {d.get('ideas_total', '?')} |",
            f"| Published | {d.get('published', '?')} |",
            f"| Manuscripts | {d.get('manuscripts', '?')} |",
            f"| Rejected PNs | {d.get('rejected_pns', '?')} |",
            f"| Publication rate | {d.get('publication_rate', '?')} |",
            "",
        ]

    # --- SCORECARD ---
    lines += [
        "## Scorecard",
        "",
        _build_scorecard(result, prev),
        "",
    ]

    return "\n".join(lines)


def _build_scorecard(result: dict, prev: dict | None) -> str:
    """Build a quick-glance scorecard of key health indicators."""
    dims = {d["dimension"]: d for d in result.get("dimensions", [])}

    metrics = []

    # 1. Frontmatter compliance
    v = dims.get("integrity", {}).get("frontmatter_compliance_pct")
    if v is not None:
        status = "🟢" if v >= 95 else "🟡" if v >= 80 else "🔴"
        metrics.append(f"| Frontmatter compliance | {v}% | {status} |")

    # 2. Signal/noise
    v = dims.get("graph", {}).get("signal_noise_ratio_pct")
    if v is not None:
        status = "🟢" if v >= 20 else "🟡" if v >= 10 else "🔴"
        metrics.append(f"| Graph signal/noise | {v}% | {status} |")

    # 3. Owner extension rate
    v = dims.get("pipeline", {}).get("owner_extension_rate_pct")
    if v is not None:
        status = "🟢" if v >= 5 else "🟡" if v >= 1 else "🔴"
        metrics.append(f"| Owner extension rate | {v}% | {status} |")

    # 4. Inbox stale
    v = dims.get("pipeline", {}).get("inbox_stale_30d")
    total = dims.get("pipeline", {}).get("inbox_total", 1)
    if v is not None:
        pct = round(v / total * 100) if total else 0
        status = "🟢" if pct <= 20 else "🟡" if pct <= 50 else "🔴"
        metrics.append(f"| Inbox stale rate | {pct}% ({v}/{total}) | {status} |")

    # 5. LN → PN conversion
    v = dims.get("funnel", {}).get("funnel", {}).get("ln_to_pn_ratio_pct")
    if v is not None:
        status = "🟢" if v >= 10 else "🟡" if v >= 5 else "🔴"
        metrics.append(f"| LN → PN conversion | {v}% | {status} |")

    # 6. PNs retrieved at least once
    tr = dims.get("funnel", {}).get("times_retrieved", {})
    total_pns = tr.get("total_pns", 0)
    retrieved = tr.get("retrieved_1plus", 0)
    if total_pns:
        pct = round(retrieved / total_pns * 100, 1)
        status = "🟢" if pct >= 30 else "🟡" if pct >= 15 else "🔴"
        metrics.append(f"| PNs ever retrieved | {pct}% ({retrieved}/{total_pns}) | {status} |")

    # 7. External outputs
    eo = dims.get("funnel", {}).get("external_outputs_sum", 0)
    if total_pns:
        status = "🟢" if eo >= 20 else "🟡" if eo >= 5 else "🔴"
        metrics.append(f"| External outputs | {eo} | {status} |")

    header = "| Indicator | Value | Status |\n|---|---|---|"
    return header + "\n" + "\n".join(metrics) if metrics else "No scorecard data."


# ============================================================
# TREND
# ============================================================

def trend(last_n: int = 5, json_mode: bool = False):
    """Show trend across last N evals."""
    if not EVALS_DIR.exists():
        raise SystemExit("No evals found in Resources/Evals/.")
    evals = sorted(EVALS_DIR.glob("*.json"), reverse=True)[:last_n]
    if not evals:
        raise SystemExit("No eval JSON files found.")

    key_metrics = [
        ("integrity", "frontmatter_compliance_pct"),
        ("graph", "signal_noise_ratio_pct"),
        ("graph", "total_edges"),
        ("pipeline", "owner_extension_rate_pct"),
        ("pipeline", "inbox_stale_30d"),
        ("funnel", "external_outputs_sum"),
        ("output", "ideas_total"),
        ("practice", "flashcard_overall_accuracy_pct"),
    ]

    rows = []
    for ep in reversed(evals):  # chronological
        try:
            data = json.loads(ep.read_text(encoding="utf-8", errors="ignore"))
        except (json.JSONDecodeError, OSError):
            continue
        dims = {d["dimension"]: d for d in data.get("dimensions", [])}
        row = {"date": data.get("timestamp", ep.stem)[:10]}
        for dim_name, metric in key_metrics:
            val = _legacy(dims.get(dim_name, {}), metric)
            # Handle nested funnel
            if val is None and dim_name == "funnel":
                val = dims.get("funnel", {}).get("funnel", {}).get(metric)
            row[f"{dim_name}.{metric}"] = val
        rows.append(row)

    if json_mode:
        print(json.dumps({"ok": True, "trend": rows}, ensure_ascii=False, indent=2))
    else:
        # Pretty table
        if not rows:
            print("No eval data found.")
            return
        headers = ["date"] + [f"{d}.{m}" for d, m in key_metrics]
        widths = [max(len(h), max(len(str(r.get(h, ""))) for r in rows)) for h in headers]
        fmt = " | ".join(f"{{:<{w}}}" for w in widths)
        print(fmt.format(*headers))
        print("-+-".join("-" * w for w in widths))
        for r in rows:
            print(fmt.format(*[str(r.get(h, "")) for h in headers]))


# ============================================================
# MAIN
# ============================================================

def run(selected_dims=None, json_mode=False):
    # Load previous eval BEFORE collecting new data (so we don't compare to ourselves)
    prev = _load_previous_eval()

    dims_to_run = selected_dims or list(DIMENSIONS.keys())
    dimensions = []
    for name in dims_to_run:
        if name not in DIMENSIONS:
            raise SystemExit(f"Unknown dimension: {name}. "
                             f"Valid: {', '.join(DIMENSIONS.keys())}")
        dimensions.append(DIMENSIONS[name]())

    # Normalize vault path — strip a container mount prefix if present
    vault_display = str(VAULT)
    if "/sessions/" in vault_display and "/mnt/" in vault_display:
        vault_display = vault_display.split("/mnt/", 1)[1]

    result = {
        "ok": True,
        "schema": "eval/1",
        "timestamp": NOW.isoformat(),
        "vault": vault_display,
        "dimensions": dimensions,
    }

    # Write JSON
    EVALS_DIR.mkdir(parents=True, exist_ok=True)
    ts = NOW.strftime("%Y-%m-%d_%H%M%S")
    json_path = EVALS_DIR / f"{ts}.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write markdown report
    md_path = EVALS_DIR / f"{ts}.md"
    report = generate_report(result, prev)
    md_path.write_text(report, encoding="utf-8")

    if json_mode:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps({
            "ok": True,
            "json_path": str(json_path),
            "md_path": str(md_path),
            "summary": {d["dimension"]: {
                k: v for k, v in d.items()
                if k != "dimension" and not isinstance(v, (list, dict))
            } for d in dimensions}
        }, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Run eval and generate report")
    run_p.add_argument("--json", action="store_true", help="raw JSON to stdout")
    run_p.add_argument("--dim", help="a single dimension: integrity|graph|pipeline|practice|funnel|output")

    trend_p = sub.add_parser("trend", help="Show trend across evals")
    trend_p.add_argument("--last", type=int, default=5, help="Number of past evals")
    trend_p.add_argument("--json", action="store_true")

    args = ap.parse_args()
    if args.cmd == "run":
        dims = [args.dim] if args.dim else None
        run(selected_dims=dims, json_mode=args.json)
    elif args.cmd == "trend":
        trend(last_n=args.last, json_mode=args.json)


if __name__ == "__main__":
    main()
