#!/usr/bin/env python3
"""
course-engine — deterministic engine for open-brain-course.

Autolink model: ALL the plumbing lives here (no LLM). The AI only contributes
judgment in the middle phase. The browser consumes the artefacts.

THREE-phase contract:

  1. collect  (deterministic, here)  → writes  course-spec.json
        collects feeder PNs, gaps, promote-feedback, shipped Cases,
        validates preconditions, scaffolds the Skill dir, decides the mode hint.

  2. [AI in your Claude session, outside this script]
        reads course-spec.json (small, structured — NOT the whole vault)
        writes the pedagogical TEXT of each module → course-content.json

  3. render   (deterministic, here)  → writes  course.html + flashcards.json
        fills the template with the built-in design system, emits flashcards,
        updates course-history.md.

Usage:
    python3 course_build.py collect  "<Domain>" "<Skill>" [--mode learning|review]
    python3 course_build.py render   "<Domain>" "<Skill>"
    python3 course_build.py validate "<Domain>" "<Skill>"   # preconditions only
    python3 course_build.py record-outcome "<Domain>" "<Skill>" --result pass|partial|fail

(--mode also accepts the legacy values aprendizaje|revision.)

The vault is autodetected by walking up from this file until
'Resources/Practice Capabilities.md' is found. Override with the env var
OPEN_BRAIN_VAULT (or the legacy VAULT_ROOT).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# ----------------------------------------------------------------------------
# Vault location
# ----------------------------------------------------------------------------

def find_vault_root() -> Path:
    env = os.environ.get("OPEN_BRAIN_VAULT") or os.environ.get("VAULT_ROOT")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "Resources" / "Practice Capabilities.md").exists():
            return parent
    raise SystemExit("ERROR: vault not found (Resources/Practice Capabilities.md). "
                     "Set OPEN_BRAIN_VAULT to your vault root.")

VAULT = find_vault_root()
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
NOW = datetime.now(timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def fail(msg: str) -> None:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# Fixed self-report shown after every module and scenario (illusion-of-learning
# diagnostic, Barcaui). open-brain-course-evaluate crosses it with the real score.
EFFORT_CHECK = {
    "question": "Was this hard, or did it come easily?",
    "options": ["it was hard", "normal", "it came easily"],
}

# --mode accepts English values; the legacy Spanish ones still work.
MODE_ALIASES = {"learning": "aprendizaje", "review": "revision"}
# Display labels for the mode identifiers written to course-spec.json.
MODE_LABELS = {"course-de-aprendizaje": "learning course",
               "course-de-revisión": "review course"}


# ----------------------------------------------------------------------------
# Reading notes / frontmatter
# ----------------------------------------------------------------------------

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def read_frontmatter(text: str) -> dict:
    """Minimal dependency-free frontmatter parser. Supports key: value and simple lists."""
    m = FM_RE.match(text)
    if not m:
        return {}
    fm, cur_key = {}, None
    for raw in m.group(1).splitlines():
        if re.match(r"^\s*-\s+", raw) and cur_key:
            fm.setdefault(cur_key, [])
            if isinstance(fm[cur_key], list):
                fm[cur_key].append(raw.strip()[1:].strip().strip('"'))
            continue
        m2 = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", raw)
        if m2:
            cur_key = m2.group(1)
            val = m2.group(2).strip().strip('"')
            fm[cur_key] = val if val else []
    return fm


def iter_notes(folder: Path):
    if not folder.exists():
        return
    for p in folder.rglob("*.md"):
        try:
            yield p, p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue


# ----------------------------------------------------------------------------
# Preconditions
# ----------------------------------------------------------------------------

MANDATORY = [
    "Resources/Skills System Schema.md",
    "Resources/Practice Capabilities.md",
]
# A personal learning playbook used to be mandatory here as well. It isn't
# shipped, so it was dropped from the preconditions; if you keep your own
# learning playbook, add its vault-relative path to this list.


def capability_definition(skill: str) -> str | None:
    pc_path = VAULT / "Resources" / "Practice Capabilities.md"
    if not pc_path.exists():  # validate() already reports it as a missing mandatory file
        return None
    pc = pc_path.read_text(encoding="utf-8")
    m = re.search(rf"^\-\s+\*\*{re.escape(skill)}\*\*\s+—\s+(.+)$", pc, re.MULTILINE)
    return m.group(1).strip() if m else None


def validate(domain: str, skill: str) -> dict:
    problems = []
    for rel in MANDATORY:
        if not (VAULT / rel).exists():
            problems.append(f"missing mandatory file: {rel}")
    cap = capability_definition(skill)
    if cap is None:
        problems.append(f"'{skill}' is not in Practice Capabilities.md — add it first")
    domain_index = VAULT / "Domains" / f"{domain}.md"
    if not domain_index.exists():
        problems.append(f"Domains/{domain}.md does not exist")
    return {"ok": not problems, "problems": problems, "capability_definition": cap}


# ----------------------------------------------------------------------------
# Mastery state — cross-skill graph (inspired by the "placement rule" +
# spaced retrieval validated by Bastani et al. / LAT).
#
# A single persistent YAML in Skills/skill_mastery_state.yaml tracks, per
# skill (domain/skill), a 3-gate + retirement + prerequisites model, applied
# to the skills YOU generate with open-brain-course. Without it, two
# consecutive courses (e.g. "Positioning execution", which depends on "JTBD
# discovery") don't know they are related.
#
# The YAML keys (estado, ultima_practica, proxima_revision, intervalo_dias,
# aciertos_consecutivos, errores_recientes, prerequisitos, subsume) and the
# state enum values are identifiers read by the skills: kept as is.
# ----------------------------------------------------------------------------

MASTERY_PATH_REL = Path("Skills") / "skill_mastery_state.yaml"
GATE_ORDER = ["no_expuesta", "aprendiendo", "gate1", "gate2", "gate3", "automatizada", "retired"]
PREREQ_MIN_GATE = "gate2"  # a prerequisite must be at gate2+
# channel | budget | stakeholder | deadline | format (identifiers, kept as is)
CONSTRAINT_DIMENSIONS = ["canal", "presupuesto", "stakeholder", "plazo", "formato"]


def mastery_key(domain: str, skill: str) -> str:
    return f"{domain}/{skill}"


def _mastery_default_entry() -> dict:
    return {
        "estado": "no_expuesta",
        "ultima_practica": None,
        "proxima_revision": None,
        "intervalo_dias": 1,
        "aciertos_consecutivos": 0,
        "errores_recientes": [],
        "prerequisitos": [],
        "subsume": [],
    }


def load_mastery() -> dict:
    """Loads Skills/skill_mastery_state.yaml. Doesn't invent data if it doesn't
    exist — returns an empty skeleton (hygiene: conservative over optimistic)."""
    path = VAULT / MASTERY_PATH_REL
    if yaml is None or not path.exists():
        return {"meta": {"ultima_sesion": TODAY, "total_skills": 0}, "skills": {}}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:  # noqa: BLE001
        log(f"⚠️ could not parse {path}: {e} — treating it as empty")
        data = {}
    data.setdefault("meta", {"ultima_sesion": TODAY, "total_skills": 0})
    data.setdefault("skills", {})
    return data


def save_mastery(data: dict) -> None:
    if yaml is None:
        log("⚠️ pyyaml not available — could not persist skill_mastery_state.yaml")
        return
    path = VAULT / MASTERY_PATH_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    data["meta"]["ultima_sesion"] = TODAY
    data["meta"]["total_skills"] = len(data.get("skills", {}))
    path.write_text(
        "# skill_mastery_state.yaml — cross-skill mastery graph (open-brain-course)\n"
        "# Gate model applied to the skills generated by open-brain-course.\n"
        + yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def get_or_create_entry(mastery: dict, domain: str, skill: str, prerequisitos: list[str]) -> dict:
    key = mastery_key(domain, skill)
    entry = mastery["skills"].get(key)
    if entry is None:
        entry = _mastery_default_entry()
        mastery["skills"][key] = entry
    # the prerequisites declared in meta.md are the authority — they are synced
    # here without overwriting the rest of the state (state/interval/streak are kept).
    if prerequisitos:
        entry["prerequisitos"] = prerequisitos
    return entry


def read_meta_prerequisites(domain: str, skill: str) -> list[str]:
    """Reads 'prerequisitos:' (prerequisites) from the skill's meta.md, if you
    declared it. They are operational, not theoretical: do you need to master X
    to be able to do Y? Format: list of 'Domain/Skill'."""
    meta = skill_dir(domain, skill) / "meta.md"
    if not meta.exists():
        return []
    fm = read_frontmatter(meta.read_text(encoding="utf-8", errors="ignore"))
    prereqs = fm.get("prerequisitos", [])
    return prereqs if isinstance(prereqs, list) else ([prereqs] if prereqs else [])


def check_prerequisites(mastery: dict, prerequisitos: list[str]) -> list[dict]:
    """Checks each prerequisite against the graph. Does NOT block — they are
    recommendations ('the graph can't be rigid'). Returns a list of warnings
    for the AI to decide."""
    warnings = []
    for prereq_key in prerequisitos:
        entry = mastery["skills"].get(prereq_key)
        estado = entry["estado"] if entry else "no_expuesta"
        ok = GATE_ORDER.index(estado) >= GATE_ORDER.index(PREREQ_MIN_GATE) if estado in GATE_ORDER else False
        if not ok:
            warnings.append({
                "prerequisite": prereq_key,
                "estado_actual": estado,
                "minimo_requerido": PREREQ_MIN_GATE,
            })
    return warnings


def compute_scaling_hint(entry: dict, next_course_brief: dict | None, version_count: int) -> dict:
    """Decides whether the Transfer phase should scale by APPEND (one more
    atomic constraint on the same scenario) instead of the user/AI rewriting
    the scenario from scratch. Based on LAT (Kim et al. 2026): append-only is
    the only strategy that guarantees monotonic difficulty, and the constraint
    ratio should scale with demonstrated ability, not with a fixed external
    calendar.

    Condition: the learner has already shown recent mastery (gate2+, ≥1
    consecutive pass) AND there is a next_course_brief asking to advance (not
    repair). If the brief asks to repair vocabulary/production, DON'T scale —
    that would raise difficulty on a weak base (the harm the 'effortless trap'
    describes)."""
    if entry["estado"] not in ("gate2", "gate3", "automatizada"):
        return {"scaling_hint": "new_scenario", "reason": "insufficient mastery to scale by append"}
    if entry["aciertos_consecutivos"] < 1:
        return {"scaling_hint": "new_scenario", "reason": "no recent consecutive passes"}
    next_move = (next_course_brief or {}).get("next_move", "") if next_course_brief else ""
    if next_move in ("repair_vocabulary", "repair_course"):
        return {"scaling_hint": "new_scenario", "reason": f"next_move={next_move} — repair before scaling"}
    dimension = CONSTRAINT_DIMENSIONS[version_count % len(CONSTRAINT_DIMENSIONS)]
    return {
        "scaling_hint": "append_constraint",
        "suggested_constraint_dimension": dimension,
        "reason": "mastery shown + brief doesn't ask for repair — add ONE constraint, don't rewrite the scenario",
    }


def read_previous_scenarios(domain: str, skill: str) -> list[dict]:
    content_path = skill_dir(domain, skill) / "course-content.json"
    if not content_path.exists():
        return []
    try:
        content = json.loads(content_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    return content.get("scenarios", [])


def record_outcome(domain: str, skill: str, result: str, note: str = "") -> dict:
    """Updates skill_mastery_state.yaml after closing a course (called by
    open-brain-course-evaluate). Spaced-retrieval algorithm: the interval
    doubles on a pass, halves on a fail, capped at 30 days.
    result: pass | partial | fail."""
    mastery = load_mastery()
    key = mastery_key(domain, skill)
    entry = mastery["skills"].setdefault(key, _mastery_default_entry())
    today = datetime.now(timezone.utc).date()
    interval = entry.get("intervalo_dias") or 1

    if result == "pass":
        entry["aciertos_consecutivos"] = entry.get("aciertos_consecutivos", 0) + 1
        interval = min(interval * 2.0, 30)
        idx = GATE_ORDER.index(entry["estado"]) if entry["estado"] in GATE_ORDER else 0
        if entry["estado"] in ("no_expuesta", "aprendiendo"):
            entry["estado"] = "gate1"
        elif entry["estado"] == "gate1":
            entry["estado"] = "gate2"
        elif entry["estado"] == "gate2":
            entry["estado"] = "gate3"
        elif entry["estado"] == "gate3" and entry["aciertos_consecutivos"] >= 3:
            entry["estado"] = "automatizada"
    elif result == "partial":
        interval = max(interval * 0.75, 1)
        # doesn't reset aciertos_consecutivos nor step back a gate — treated
        # like a minor miss: short review, not a restart.
    else:  # fail
        entry["aciertos_consecutivos"] = 0
        interval = max(interval * 0.5, 1)
        if entry["estado"] in ("gate2", "gate3", "automatizada"):
            idx = GATE_ORDER.index(entry["estado"])
            entry["estado"] = GATE_ORDER[max(idx - 1, 1)]

    entry["intervalo_dias"] = round(interval, 1)
    entry["ultima_practica"] = str(today)
    entry["proxima_revision"] = str(today + timedelta(days=round(interval)))
    if note:
        errores = entry.setdefault("errores_recientes", [])
        errores.append({"fecha": str(today), "nota": note})
        entry["errores_recientes"] = errores[-5:]

    save_mastery(mastery)
    return {"ok": True, "skill": key, "entry": entry}


# ----------------------------------------------------------------------------
# PHASE 1 — collect
# ----------------------------------------------------------------------------

LAYERS = ["compression", "mental-model", "application", "artifact",
          "coaching", "decision", "diagnosis"]


def skill_dir(domain: str, skill: str) -> Path:
    return VAULT / "Skills" / domain / skill


def scaffold(domain: str, skill: str, cap: str) -> bool:
    d = skill_dir(domain, skill)
    created = not d.exists()
    d.mkdir(parents=True, exist_ok=True)
    meta = d / "meta.md"
    if not meta.exists():
        meta.write_text(
            f"---\ntype: skill-meta\ndomain: {domain}\nskill: {skill}\n"
            f'capability_definition: "{cap}"\ncreated: {TODAY}\nupdated: {TODAY}\n'
            f"status: active\n---\n\n# Skill: {skill} ({domain})\n", encoding="utf-8")
    feeder_f = d / "feeder-pns.md"
    if not feeder_f.exists():
        feeder_f.write_text(
            f"# Feeder PNs — {skill}\n"
            f"## Literature Notes\n\n"
            f"## Endorsed (0)\nNone yet.\n"
            f"## Provisional (0)\nNone yet.\n"
            f"## Rejected (0)\nNone.\n", encoding="utf-8")
    for fn, hdr in [("gaps.md", "Gaps"),
                    ("promote-feedback.md", "Promote Feedback")]:
        f = d / fn
        if not f.exists():
            f.write_text(f"# {hdr} — {skill}\n", encoding="utf-8")
    return created


def parse_curated_feeder(domain: str, skill: str) -> dict | None:
    """Reads the curated feeder-pns.md if it exists. It is the AUTHORITY: the list
    you maintain by hand wins over any automatic scan.
    Supported sections: ## Endorsed, ## Provisional, ## Rejected, ## Suggested
    (legacy: ## Sugeridas), and ## Literature Notes (LNs that feed the course
    BEFORE promote)."""
    f = skill_dir(domain, skill) / "feeder-pns.md"
    if not f.exists():
        return None
    text = f.read_text(encoding="utf-8")
    buckets = {"endorsed": [], "provisional": [], "rejected": [], "suggested": [],
               "literature_notes": []}
    section = None
    for ln in text.splitlines():
        h = re.match(r"^##\s+(Endorsed|Provisional|Rejected|Suggested|Sugeridas|Literature\s+Notes)", ln, re.I)
        if h:
            key = re.sub(r"\s+", " ", h.group(1).lower().strip())
            section = {"endorsed": "endorsed", "provisional": "provisional",
                       "rejected": "rejected", "suggested": "suggested",
                       "sugeridas": "suggested",
                       "literature notes": "literature_notes"}[key]
            continue
        m = re.search(r"\[\[([^\]]+)\]\]", ln)
        if m and section:
            buckets[section].append(m.group(1).split("|")[0].strip())
    has_any = any(buckets[k] for k in ("endorsed", "provisional", "rejected", "literature_notes"))
    return buckets if has_any else None


def extract_note_digest(title: str) -> dict | None:
    """Reads a note (PN or LN) and returns a compressed digest with the essentials
    so the AI can write pedagogical content without reading the full note.
    Searches Permanent Notes AND Literature Notes.
    Fields: title, note_type (pn|ln), layer, sources, core (~500 chars of the body),
    evidence (~400 chars of the Evidence section),
    boundary (boundary conditions section), connections (linked titles)."""
    search_folders = [
        (VAULT / "Permanent Notes", "pn"),
        (VAULT / "Literature Notes", "ln"),
    ]
    for folder, note_type in search_folders:
        candidate = folder / f"{title}.md"
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8", errors="ignore")
            fm = read_frontmatter(text)
            body = FM_RE.sub("", text).strip()

            # core: first real paragraphs (no headers, no lists, no embeds)
            core_parts, char_count = [], 0
            for chunk in re.split(r"\n\s*\n", body):
                c = chunk.strip()
                if not c or c.startswith(("#",)):
                    continue
                clean = re.sub(r"!\[\[[^\]]*\]\]|!\[[^\]]*\]\([^)]*\)", "", c).strip()
                if not clean:
                    continue
                core_parts.append(re.sub(r"\s+", " ", clean))
                char_count += len(core_parts[-1])
                if char_count > 500:
                    break

            # evidence: Evidence / Why this matters section (Spanish labels kept for older notes)
            evidence = ""
            for ev_label in (r"Evidence", r"Evidencia", r"Why this matters",
                             r"Por qué importa"):
                ev_match = re.search(
                    rf"\*\*{ev_label}\*\*:?\s*(.+?)(?=\n\*\*|\n##|\Z)",
                    body, re.DOTALL | re.IGNORECASE)
                if ev_match:
                    evidence = re.sub(r"\s+", " ", ev_match.group(1).strip())[:400]
                    break

            # boundary conditions
            bc_match = re.search(
                r"\*\*Boundary conditions?\*\*:?\s*(.+?)(?=\n\*\*|\n##|\Z)",
                body, re.DOTALL | re.IGNORECASE)
            boundary = re.sub(r"\s+", " ", bc_match.group(1).strip())[:300] if bc_match else ""

            # connections: titles of linked notes
            connections = re.findall(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]", body)
            seen_conn, unique_conn = set(), []
            for conn in connections:
                if conn not in seen_conn:
                    seen_conn.add(conn)
                    unique_conn.append(conn)

            sources = fm.get("sources", fm.get("source", []))
            if isinstance(sources, str):
                sources = [sources] if sources else []

            return {
                "title": title,
                "note_type": note_type,
                "layer": fm.get("layer", ""),
                "sources": sources[:5],
                "core": "\n\n".join(core_parts[:3]),
                "evidence": evidence,
                "boundary": boundary,
                "connections": unique_conn[:8],
            }
    return None


# Backward-compatibility alias
extract_pn_digest = extract_note_digest


def scan_suggestions(domain: str, skill: str, cap: str, known: set) -> dict:
    """STRICT scan to propose new notes (PNs and LNs).
    Rule: match on title OR on the frontmatter search_terms — never on the body.
    Returns {"suggested_pns": [...], "suggested_lns": [...]}."""
    keywords = set(w.lower() for w in re.findall(r"[a-záéíóúñ]{5,}", cap.lower()))
    skill_low = skill.lower()
    pns, lns, seen = [], [], set()
    scan_folders = [
        (VAULT / "Permanent Notes", pns),
        (VAULT / "Literature Notes", lns),
    ]
    for folder, target in scan_folders:
        for p, text in iter_notes(folder):
            title = p.stem
            if title in known or title in seen:
                continue
            fm = read_frontmatter(text)
            terms = " ".join(fm.get("search_terms", []) if isinstance(
                fm.get("search_terms"), list) else [str(fm.get("search_terms", ""))]).lower()
            title_hit = skill_low in title.lower() or any(
                k in title.lower() for k in keywords)
            terms_hit = sum(1 for k in keywords if k in terms) >= 2
            if title_hit or terms_hit:
                seen.add(title)
                target.append(title)
    return {"suggested_pns": pns[:10], "suggested_lns": lns[:15]}


def find_feeders(domain: str, skill: str, cap: str) -> dict:
    """Authority = curated feeder-pns.md. The scan adds 'suggested_pns' and 'suggested_lns'.
    The natural flow: LNs → Course → Judgment → Promote PN."""
    curated = parse_curated_feeder(domain, skill)
    if curated is None:
        curated = {"endorsed": [], "provisional": [], "rejected": [], "suggested": [],
                   "literature_notes": []}
        known = set()
    else:
        known = set(curated["endorsed"] + curated["provisional"] + curated["rejected"]
                    + curated.get("literature_notes", []))
    suggestions = scan_suggestions(domain, skill, cap, known)
    curated["suggested"] = suggestions["suggested_pns"]
    curated["suggested_lns"] = suggestions["suggested_lns"]
    return curated


# Backward-compatibility alias
find_feeder_pns = find_feeders


def read_open_gaps(domain: str, skill: str) -> list:
    f = skill_dir(domain, skill) / "gaps.md"
    if not f.exists():
        return []
    text = f.read_text(encoding="utf-8")
    return re.findall(r"^##\s+(.+)$", text, re.MULTILINE)


def read_pending_friction(domain: str, skill: str) -> list:
    f = skill_dir(domain, skill) / "promote-feedback.md"
    if not f.exists():
        return []
    text = f.read_text(encoding="utf-8")
    return re.findall(r"^##\s+(.+)$", text, re.MULTILINE)


def read_next_course_brief(domain: str, skill: str) -> dict | None:
    """Reads the brief generated when a course is closed. It is priority input
    for regenerating: if it exists, the next course must repair or advance
    exactly on what the learner failed, not start from scratch."""
    f = skill_dir(domain, skill) / "next-course-brief.md"
    if not f.exists():
        return None
    text = f.read_text(encoding="utf-8", errors="ignore")
    fm = read_frontmatter(text)

    def section(name: str) -> str:
        m = re.search(rf"^##\s+{re.escape(name)}\s*\n(.*?)(?=^##\s+|\Z)",
                      text, re.MULTILINE | re.DOTALL)
        return m.group(1).strip() if m else ""

    def bullets(name: str) -> list[str]:
        body = section(name)
        return [re.sub(r"^\-\s+", "", ln).strip()
                for ln in body.splitlines()
                if re.match(r"^\-\s+", ln) and "(none)" not in ln.lower()]

    return {
        "source_path": str(f),
        "next_move": fm.get("next_move") or section("Move"),
        "title": section("Title"),
        "objective": section("Objective"),
        "concepts": bullets("Concepts"),
        "practices": bullets("Practices"),
        "anti_patterns": bullets("Anti-patterns"),
        "raw": text[:6000],
    }


SHIPPED_STATUSES = {"shipped", "published", "ship-ready", "final", "complete ✅"}


def _first_paragraph(text: str) -> str:
    """First real paragraph after frontmatter and markdown headings."""
    body = FM_RE.sub("", text)
    for chunk in re.split(r"\n\s*\n", body):
        c = chunk.strip()
        if not c or c.startswith(("#", "|", ">", "-", "*")):
            continue
        # skip image embeds (![[...]] or ![](...)) and lines that are only that
        c = re.sub(r"!\[\[[^\]]*\]\]|!\[[^\]]*\]\([^)]*\)", "", c).strip()
        if not c:
            continue
        return re.sub(r"\s+", " ", c)[:220]
    return ""


def read_shipped_cases() -> list:
    """Shipped cases/posts for knowledge-checks. Covers:
    - Published/  (real posts: type/status published, with link and platform)
    - Cases/      (shippable status: ship-ready, shipped, final, complete)
    - Manuscripts/ (status shipped/published)"""
    cases, seen = [], set()
    folders = [VAULT / "Published", VAULT / "Cases", VAULT / "Manuscripts"]
    for folder in folders:
        for p, text in iter_notes(folder):
            if p.stem in seen:
                continue
            fm = read_frontmatter(text)
            status = (fm.get("status") or "").lower().strip()
            typ = (fm.get("type") or "").lower().strip()
            is_shipped = status in SHIPPED_STATUSES or typ == "published"
            if not is_shipped:
                continue
            seen.add(p.stem)
            cases.append({
                "title": p.stem,
                "hook": _first_paragraph(text),
                "platform": fm.get("platform") or "",
                "link": fm.get("link") or "",
                "date": fm.get("published_date") or fm.get("date") or "",
            })
    return cases


def collect(domain: str, skill: str, mode_override: str | None) -> dict:
    v = validate(domain, skill)
    if not v["ok"]:
        fail("; ".join(v["problems"]))
    cap = v["capability_definition"]
    created = scaffold(domain, skill, cap)
    feeders = find_feeders(domain, skill, cap)
    gaps = read_open_gaps(domain, skill)
    friction = read_pending_friction(domain, skill)
    next_course_brief = read_next_course_brief(domain, skill)
    cases = read_shipped_cases()

    # --- Cross-skill mastery graph (see the "Mastery state" section above) ---
    prerequisitos = read_meta_prerequisites(domain, skill)
    mastery_state = load_mastery()
    mastery_entry = get_or_create_entry(mastery_state, domain, skill, prerequisitos)
    prereq_warnings = check_prerequisites(mastery_state, mastery_entry["prerequisitos"])
    version_count = (skill_dir(domain, skill) / "course-history.md").read_text(
        encoding="utf-8", errors="ignore").count("\n## v") if (skill_dir(domain, skill) / "course-history.md").exists() else 0
    scaling = compute_scaling_hint(mastery_entry, next_course_brief, version_count)
    previous_scenarios = read_previous_scenarios(domain, skill) if scaling["scaling_hint"] == "append_constraint" else []
    save_mastery(mastery_state)  # persist the entry in case this is the first time the skill is seen

    # --- Digest of ALL feeder notes (PNs + LNs) ---
    # The course is built on what exists: LNs alone are enough for a learning
    # course. Endorsed PNs are only needed for review. The scan's
    # suggested_lns are digested too: without them the course loses the prior
    # learning context the learner needs to promote PNs with judgment.
    all_feeder_titles = (feeders["endorsed"] + feeders["provisional"]
                         + feeders.get("literature_notes", [])
                         + feeders.get("suggested_lns", []))
    digests = []
    for t in all_feeder_titles:
        d = extract_note_digest(t)
        if d:
            digests.append(d)

    n_endorsed = len(feeders["endorsed"])
    n_lns_curated = len(feeders.get("literature_notes", []))
    n_lns_suggested = len(feeders.get("suggested_lns", []))
    n_lns = n_lns_curated + n_lns_suggested
    n_provisional = len(feeders["provisional"])
    # Mode identifiers stay as they are ("course-de-aprendizaje" = learning
    # course, "course-de-revisión" = review course); render shows them in English.
    mode_override = MODE_ALIASES.get(mode_override, mode_override)
    if mode_override in ("aprendizaje", "revision"):
        mode = "course-de-" + ("aprendizaje" if mode_override == "aprendizaje" else "revisión")
    else:
        # Review only if there are ≥3 endorsed PNs (judgment already formed).
        # If there are only LNs or provisional PNs → learning (the course builds judgment).
        mode = "course-de-revisión" if n_endorsed >= 3 else "course-de-aprendizaje"

    mode_reason_parts = []
    if n_endorsed:
        mode_reason_parts.append(f"{n_endorsed} PNs endorsed")
    if n_provisional:
        mode_reason_parts.append(f"{n_provisional} PNs provisional")
    if n_lns:
        ln_detail = f"{n_lns} LNs"
        if n_lns_curated and n_lns_suggested:
            ln_detail += f" ({n_lns_curated} curated + {n_lns_suggested} suggested)"
        mode_reason_parts.append(ln_detail)
    if not mode_reason_parts:
        mode_reason_parts.append("no feeders")
    mode_reason = ", ".join(mode_reason_parts)
    if mode_override:
        mode_reason += " (override)"

    spec = {
        "ok": True,
        "schema": "course-spec/2",
        "generated_at": NOW.isoformat(),
        "domain": domain,
        "skill": skill,
        "skill_slug": slug(skill),
        "capability_definition": cap,
        "scaffolded": created,
        "mode": mode,
        "mode_reason": mode_reason,
        "feeder_pns": feeders,
        "feeder_digests": digests,
        "open_gaps": gaps[:5],
        "pending_friction": friction,
        "next_course_brief": next_course_brief,
        "shipped_cases": cases,
        "cases_warning": len(cases) < 3,
        # --- Cross-skill mastery graph (Skills/skill_mastery_state.yaml) ---
        "mastery": {
            "estado": mastery_entry["estado"],
            "aciertos_consecutivos": mastery_entry["aciertos_consecutivos"],
            "prerequisitos": mastery_entry["prerequisitos"],
            "prerequisite_warnings": prereq_warnings,
            "scaling_hint": scaling["scaling_hint"],
            "suggested_constraint_dimension": scaling.get("suggested_constraint_dimension"),
            "scaling_reason": scaling["reason"],
            "previous_scenarios": previous_scenarios,
        },
        # the layers the AI must cover as modules (the ones with signal)
        "layers_to_cover": LAYERS,
        # contract for what the AI must return in course-content.json
        "expected_content_schema": {
            "schema": "course-content/2.0",
            "mode": "<echo of the mode>",
            "concept_primer": [{
                "term": "<concept>",
                "definition": "<short definition>",
                "example": "<concrete example>",
                "anti_example": "<anti-example>",
                "why_it_matters": "<why it unlocks the skill>",
                "quiz": {
                    "question": "<recognition question>",
                    "options": ["<option A>", "<option B>", "<option C>"],
                    "correct_index": 0
                }
            }],
            "modules": [{
                "n": "I",
                "layer": "compression",
                "title": "<module title>",
                "objective": "<one line>",
                "pretest": "<prior question — the learner answers BEFORE reading>",
                "before": {"presupone": ["<what the learner should already be able to do>"],
                           "no_presupone": ["<what they don't need to know yet>"]},
                "concept": "<concept with a concrete example FIRST, 2+ paragraphs>",
                "quote": {"text": "<literal quote>", "author": "<mentor>",
                          "source": "<LN/PN>"},
                "application": ["<context 1>", "<context 2>"],
                "comprehension": "<question + reasonable answer>",
                "teaching": "<prompt: explain it to a stakeholder>",
                "anti_patterns": [{"action": "...", "consequence": "..."}],
                "effort_check": dict(EFFORT_CHECK),
                "flashcards": [{
                    "concept": "<concept assessed>",
                    "front": "<generation question>",
                    "back": "<reasonable canonical answer>",
                    "quiz": {
                        "options": ["<correct option>", "<distractor>", "I don't know"],
                        "correct_index": 0
                    }
                }]
            }],
            "scenarios": [{
                "title": "<scenario name>",
                "context": "<realistic situation with a client/stakeholder>",
                "constraint": "<constraint that forces a choice>",
                "deliverable": "<what the learner must produce>",
                "evaluation_criteria": [
                    {"name": "<criterion>", "description": "<what demonstrates mastery>"}
                ],
                "expert_reference": "<expert's reference answer>",
                "effort_check": dict(EFFORT_CHECK)
            }]
        },
    }

    spec_path = skill_dir(domain, skill) / "course-spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"✓ course-spec.json written ({n_endorsed} endorsed / "
        f"{n_provisional} provisional / {n_lns} LNs / {len(digests)} digests / "
        f"{len(cases)} cases / mode={mode} / "
        f"mastery={mastery_entry['estado']} / scaling={scaling['scaling_hint']})")
    if prereq_warnings:
        log(f"⚠️ prerequisites below {PREREQ_MIN_GATE}: "
            + ", ".join(f"{w['prerequisite']} ({w['estado_actual']})" for w in prereq_warnings)
            + " — not blocking, they are recommendations")
    # machine-readable output to stdout so the skill can read it cheaply
    print(json.dumps({
        "ok": True, "spec_path": str(spec_path), "mode": mode,
        "feeders": {k: len(v) for k, v in feeders.items()},
        "digests": len(digests),
        "gaps": len(gaps), "cases": len(cases),
        "cases_warning": spec["cases_warning"],
        "mastery": spec["mastery"],
    }, ensure_ascii=False))
    return spec


# ----------------------------------------------------------------------------
# PHASE 3 — render
# ----------------------------------------------------------------------------

def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def json_for_html(data) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def _step(html: str, last: bool = False) -> str:
    """Wraps a spine step. Hidden by default (the JS reveals it);
    the first one of each module starts visible."""
    btn = "" if last else '<button class="continue">Continue ↓</button>'
    return f'<div class="spine-step">{html}{btn}</div>'


def render_module(m: dict, idx: int) -> str:
    pres = "".join(f"<li>{esc(x)}</li>" for x in m.get("before", {}).get("presupone", []))
    nopres = "".join(f"<li>{esc(x)}</li>" for x in m.get("before", {}).get("no_presupone", []))
    apps = "".join(f"<li>{esc(x)}</li>" for x in m.get("application", []))
    q = m.get("quote", {})
    aps = "".join(
        f'<div class="anti-pattern"><span class="ap-label">Anti-pattern</span>'
        f'<div class="ap-action">{esc(ap.get("action",""))}</div>'
        f'<div class="ap-conseq">{esc(ap.get("consequence",""))}</div></div>'
        for ap in m.get("anti_patterns", []))

    steps = []
    # 1 — header + pretest (visible from the start)
    pretest = re.sub(r"^\s*(Antes de leer|Before reading):\s*", "", str(m.get("pretest", "")), flags=re.I)
    steps.append(
        f'<div class="module-header"><span class="numeral">{esc(m.get("n",""))}</span>'
        f'<h2>{esc(m.get("title",""))}</h2>'
        f'<p class="objective">{esc(m.get("objective",""))}</p></div>'
        f'<div class="pretest"><strong>Try it before reading:</strong> {esc(pretest)}</div>')
    # 2 — before starting
    steps.append('<div class="readiness"><h3>Entry checkpoint</h3>'
                 '<p>This tells you whether you can practise this module now. If the left column doesn\'t ring a bell, '
                 'don\'t carry on out of inertia: go back to the Concept Primer or mark the gap in the practice.</p></div>'
                 f'<div class="before"><div><h4>You should already be able to</h4><ul>{pres}</ul></div>'
                 f'<div><h4>You don\'t need to know yet</h4><ul>{nopres}</ul></div></div>')
    # 3 — concept
    concept = esc(m.get("concept", "")).replace(chr(10) + chr(10), "</p><p>")
    steps.append(f'<div class="concept"><p>{concept}</p></div>')
    # 4 — quote
    steps.append(
        f'<blockquote class="pull-quote"><div class="avatar">{esc((q.get("author","?") or "?")[:2])}</div>'
        f'<div><p>{esc(q.get("text",""))}</p>'
        f'<cite>— {esc(q.get("author",""))}, {esc(q.get("source",""))}</cite></div></blockquote>')
    # 5 — application
    steps.append(f'<div class="application"><h4>In your real work</h4><ul>{apps}</ul></div>')
    # 6 — comprehension + AI check
    m_comp = esc(m.get("comprehension", ""))
    m_title = esc(m.get("title", ""))
    steps.append(
        f'<div class="comprehension" data-verify-type="comprehension" '
        f'data-context="{m_title}" data-question="{m_comp}">'
        f'<strong>Check:</strong> {m_comp}'
        f'<textarea class="module-answer" rows="4" '
        f'placeholder="Write your answer before continuing…"></textarea>'
        f'<button class="verify-btn" data-type="comprehension">Check with AI ↗</button>'
        f'<div class="gh-feedback-output"></div>'
        f'</div>')
    # 7 — teaching + AI check + anti-patterns (last step, no button)
    m_teach = esc(m.get("teaching", ""))
    steps.append(
        f'<div class="teaching self-explain" data-verify-type="teaching" '
        f'data-context="{m_title}" data-question="{m_teach}">'
        f'✎ {m_teach}'
        f'<textarea class="module-answer" rows="4" '
        f'placeholder="Write your explanation for the stakeholder…"></textarea>'
        f'<button class="verify-btn" data-type="teaching">Check with AI ↗</button>'
        f'<div class="gh-feedback-output"></div>'
        f'</div>{aps}')
    # 8 — effort check (illusion-of-learning diagnostic — Barcaui)
    ec = m.get("effort_check") or EFFORT_CHECK
    effort_opts = "".join(
        f'<button class="effort-opt" data-effort-module="{idx}" data-value="{esc(opt)}">{esc(opt)}</button>'
        for opt in ec.get("options", []))
    steps.append(
        f'<div class="effort-check" data-effort-for="{idx}">'
        f'<p class="effort-question">{esc(ec.get("question",""))}</p>'
        f'<div class="effort-opts">{effort_opts}</div>'
        f'<p class="effort-note muted">This is not scored as right/wrong — it only detects whether the '
        f'module felt easier than it really was (illusion of learning).</p>'
        f'</div>')

    body = "".join(_step(s, last=(i == len(steps) - 1)) for i, s in enumerate(steps))
    return (f'<section class="module phase-content" id="mod-{idx}" data-phase="produccion" data-layer="{esc(m.get("layer",""))}">'
            f'{body}</section>')


def render_cases(cases: list) -> str:
    if not cases:
        return ('<section class="cases" id="cases"><h2>Cases</h2>'
                '<p class="muted">No shipped pieces detected for knowledge-checks.</p></section>')
    items = []
    for c in cases[:8]:
        link = (f'<a href="{esc(c["link"])}" target="_blank">open ↗</a>'
                if c.get("link") else "")
        plat = f'<span class="case-plat">{esc(c["platform"])}</span>' if c.get("platform") else ""
        items.append(
            f'<div class="case-card"><div class="case-head"><strong>{esc(c["title"])}</strong>{plat}</div>'
            f'<p class="case-hook">{esc(c.get("hook",""))}</p>{link}</div>')
    return (f'<section class="cases" id="cases"><h2>Cases — reconstruct the decision</h2>'
            f'<p class="muted">Your real pieces. For each one: what hook did you use? What friction did it name?</p>'
            f'<div class="case-grid">{"".join(items)}</div></section>')


def render_concept_primer(content: dict) -> str:
    concepts = content.get("concept_primer") or content.get("concepts") or []
    if not concepts:
        return ""
    cards = []
    for i, c in enumerate(concepts):
        quiz = c.get("quiz", {})
        quiz_html = ""
        if quiz and quiz.get("options"):
            opts = "".join(
                f'<button class="primer-quiz-opt" data-idx="{j}" data-concept="{i}">'
                f'{esc(opt)}</button>'
                for j, opt in enumerate(quiz["options"]))
            quiz_html = (
                f'<div class="primer-quiz" data-correct="{quiz.get("correct_index", 0)}" '
                f'data-concept-idx="{i}">'
                f'<p class="primer-quiz-q">{esc(quiz.get("question", ""))}</p>'
                f'{opts}'
                f'<div class="primer-quiz-result"></div>'
                f'</div>')
        cards.append(
            '<article class="concept-card">'
            f'<h3>{esc(c.get("term", ""))}</h3>'
            f'<p>{esc(c.get("definition", ""))}</p>'
            f'<dl><dt>Example</dt><dd>{esc(c.get("example", ""))}</dd>'
            f'<dt>Anti-example</dt><dd>{esc(c.get("anti_example", ""))}</dd>'
            f'<dt>Why it matters</dt><dd>{esc(c.get("why_it_matters", ""))}</dd></dl>'
            f'{quiz_html}'
            '</article>')
    primer_data = json_for_html([{
        "term": c.get("term", ""),
        "quiz": c.get("quiz", {})
    } for c in concepts])
    return (
        '<section class="primer phase-content" id="primer" data-phase="vocabulario">'
        '<h2>Phase 1 — Working vocabulary</h2>'
        '<p class="muted">Without this vocabulary you can\'t think with the skill. '
        'Answer the quiz for each concept. You need ≥70% to move on to Production.</p>'
        f'<div class="concept-grid">{"".join(cards)}</div>'
        '<div class="phase-gate" id="vocab-gate">'
        '<div class="gate-score">Quiz: <span id="vocab-score">0</span>/<span id="vocab-total">0</span></div>'
        '<button class="gate-btn" id="unlock-production" disabled>Unlock Production →</button>'
        '</div>'
        f'<script type="application/json" id="primer-data">{primer_data}</script>'
        '</section>')


def render_practice(content: dict) -> str:
    """Intrinsic practice block: free production first; revealing the answer
    counts as not knowing. Exports practice-export.md for open-brain-course-evaluate."""
    cards = []
    for m in content.get("modules", []):
        for c in m.get("flashcards", []):
            cards.append({
                "module": m.get("title", ""),
                "concept": c.get("concept") or c.get("front", "")[:80],
                "front": c.get("front", ""),
                "back": c.get("back", ""),
                "quiz": c.get("quiz") or {},
            })
    if not cards:
        return ""
    practice_json = json_for_html(cards)
    items = "".join(
        '<li class="recall-item" data-practice-index="{i}">'
        '<div class="recall-meta">{module} · {concept}</div>'
        '<div class="recall-front">{front}</div>'
        '<label class="answer-label" for="answer-{i}">Your answer, without looking</label>'
        '<textarea id="answer-{i}" class="practice-answer" rows="5" '
        'placeholder="Write whatever you can recall. If nothing comes, mark I don\'t know."></textarea>'
        '<div class="practice-actions">'
        '<button class="save-answer">Save answer</button>'
        '<button class="unknown-answer">I don\'t know</button>'
        '<button class="quiz-mode">Switch to multiple choice</button>'
        '<button class="reveal-back">Show canonical answer</button>'
        '</div>'
        '<div class="quiz-panel" hidden></div>'
        '<div class="recall-back">{back}</div>'
        '<div class="item-status">Status: pending</div>'
        '</li>'.format(
            i=i,
            module=esc(c.get("module", "")),
            concept=esc(c.get("concept", "")),
            front=esc(c.get("front", "")),
            back=esc(c.get("back", "")),
        )
        for i, c in enumerate(cards))
    return (
        '<section class="practice phase-content" id="practice" data-phase="produccion"><h2>Phase 2 — Production</h2>'
        '<div class="wager"><span>Before you start, bet your confidence:</span>'
        '<div class="wager-btns">'
        '<button data-w="alta">High</button>'
        '<button data-w="media">Medium</button>'
        '<button data-w="baja">Low</button></div>'
        '<p class="wager-note"></p></div>'
        '<p class="muted">The canonical answer is hidden. Viewing it is recorded as '
        '<code>revealed</code>; “I don\'t know” is recorded as a gap for the next course.</p>'
        f'<ol class="recall-list">{items}</ol>'
        '<div class="practice-export">'
        '<button id="download-practice-md">Download practice-export.md</button>'
        '<button id="copy-practice-md">Copy markdown</button>'
        '<button id="copy-evaluation-bundle">Copy prompt + answers</button>'
        '</div>'
        '<div class="evaluation-import">'
        '<p class="muted">Recommended: download <code>practice-export.md</code>, save it in this course\'s folder '
        'and say <code>course-evaluate</code> in your Claude session. Alternative: “Copy prompt + answers” copies the '
        'evaluator prompt with your answers for any Claude chat; paste the reply below to keep it.</p>'
        '<label for="claude-eval">Paste Claude\'s evaluation here</label>'
        '<textarea id="claude-eval" rows="8" placeholder="Paste Claude\'s feedback on your answers."></textarea>'
        '<button id="save-claude-eval">Save evaluation (download course-evaluation.md)</button>'
        '<div id="claude-eval-output"></div>'
        '</div>'
        f'<script type="application/json" id="practice-data">{practice_json}</script>'
        '<div class="phase-gate" id="production-gate">'
        '<div class="gate-score">Exercises: <span id="prod-done">0</span>/<span id="prod-total">0</span></div>'
        '<button class="gate-btn" id="unlock-transfer" disabled>Unlock Transfer →</button>'
        '</div>'
        '</section>')


def render_scenarios(content: dict) -> str:
    scenarios = content.get("scenarios", [])
    if not scenarios:
        return ""
    items = []
    for i, s in enumerate(scenarios):
        criteria_html = "".join(
            f'<li><strong>{esc(cr.get("name", ""))}</strong>: {esc(cr.get("description", ""))}</li>'
            for cr in s.get("evaluation_criteria", []))
        ec = s.get("effort_check") or EFFORT_CHECK
        effort_opts = "".join(
            f'<button class="effort-opt" data-effort-scenario="{i}" data-value="{esc(opt)}">{esc(opt)}</button>'
            for opt in ec.get("options", []))
        items.append(
            f'<div class="scenario-card" data-scenario="{i}">'
            f'<h3>{esc(s.get("title", ""))}</h3>'
            f'<div class="scenario-context"><strong>Situation:</strong> {esc(s.get("context", ""))}</div>'
            f'<div class="scenario-constraint"><strong>Constraint:</strong> {esc(s.get("constraint", ""))}</div>'
            f'<div class="scenario-deliverable"><strong>Produce:</strong> {esc(s.get("deliverable", ""))}</div>'
            f'<div class="scenario-criteria"><strong>You will be assessed on:</strong><ul>{criteria_html}</ul></div>'
            f'<label class="answer-label" for="scenario-{i}">Your answer</label>'
            f'<textarea id="scenario-{i}" class="scenario-answer" rows="8" '
            f'placeholder="Apply the skill to this case. Without looking at the previous modules."></textarea>'
            f'<div class="scenario-actions">'
            f'<button class="save-scenario" data-scenario="{i}">Save answer</button>'
            f'<button class="verify-scenario-btn" data-scenario="{i}">Check with AI ↗</button>'
            f'</div>'
            f'<div class="gh-feedback-output" id="gh-feedback-scenario-{i}"></div>'
            f'<div class="scenario-status">Status: pending</div>'
            f'<div class="effort-check" data-effort-for-scenario="{i}">'
            f'<p class="effort-question">{esc(ec.get("question",""))}</p>'
            f'<div class="effort-opts">{effort_opts}</div>'
            f'</div>'
            f'</div>')
    scenario_data = json_for_html([{
        "title": s.get("title", ""),
        "context": s.get("context", ""),
        "constraint": s.get("constraint", ""),
        "deliverable": s.get("deliverable", ""),
        "evaluation_criteria": s.get("evaluation_criteria", []),
        "expert_reference": s.get("expert_reference", "")
    } for s in scenarios])
    return (
        '<section class="scenarios phase-content" id="scenarios" data-phase="transferencia">'
        '<h2>Phase 3 — Transfer</h2>'
        '<p class="muted">Apply the skill to new situations. This is where real mastery shows: '
        'not recognising, not repeating — building.</p>'
        f'<div class="scenario-list">{"".join(items)}</div>'
        '<div class="sync-section">'
        '<p>Done? Export your answers, save the file in this course\'s folder '
        '(<code>Skills/&lt;Domain&gt;/&lt;Skill&gt;/</code>) and say <code>course-evaluate</code> in your Claude session.</p>'
        '<div class="sync-actions">'
        '<button id="download-export-final" class="sync-btn">Download practice-export.md</button>'
        '<button id="copy-export-final" class="sync-btn secondary">Copy markdown</button>'
        '</div>'
        '<p class="sync-optional">Only if you run your own sync endpoint: '
        '<button id="sync-to-vault" class="sync-btn secondary">Sync to the vault</button></p>'
        '<div id="sync-status"></div>'
        '</div>'
        f'<script type="application/json" id="scenario-data">{scenario_data}</script>'
        '</section>')


def render(domain: str, skill: str) -> dict:
    d = skill_dir(domain, skill)
    spec_path, content_path = d / "course-spec.json", d / "course-content.json"
    if not spec_path.exists():
        fail("course-spec.json missing — run 'collect' first")
    if not content_path.exists():
        fail("course-content.json missing — the AI must write it (phase 2) before render")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    content = json.loads(content_path.read_text(encoding="utf-8"))

    tpl_path = TEMPLATE_DIR / "course.html.template"
    if not tpl_path.exists():
        fail(f"template missing: {tpl_path}")
    tpl = tpl_path.read_text(encoding="utf-8")

    mods = content.get("modules", [])
    primer_html = render_concept_primer(content)
    modules_html = "".join(render_module(m, i) for i, m in enumerate(mods))
    cases_html = render_cases(spec.get("shipped_cases", []))
    practice_html = render_practice(content)
    scenarios_html = render_scenarios(content)
    n_scenarios = len(content.get("scenarios", []))
    nav = []
    # Phase 1
    if primer_html:
        nav.append(("primer", "1", "Vocabulary", "vocabulario"))
    # Phase 2
    for i, m in enumerate(mods):
        nav.append((f"mod-{i}", m.get("n", ""), m.get("title", ""), "produccion"))
    nav.append(("practice", "▷", "Practice", "produccion"))
    # Phase 3
    if scenarios_html:
        nav.append(("scenarios", "3", "Transfer", "transferencia"))
    nav.append(("cases", "◆", "Cases", "always"))
    sidebar = "".join(
        f'<a class="nav-card" href="#{anchor}" data-nav-phase="{phase}">'
        f'<span class="nav-num">{esc(num)}</span>'
        f'<span class="nav-title">{esc(title)}</span></a>'
        for anchor, num, title, phase in nav)

    html = (tpl
            .replace("{{SKILL}}", esc(skill))
            .replace("{{DOMAIN}}", esc(domain))
            .replace("{{MODE}}", esc(MODE_LABELS.get(spec.get("mode", ""), spec.get("mode", ""))))
            .replace("{{ENDORSED}}", str(len(spec["feeder_pns"]["endorsed"])))
            .replace("{{PROVISIONAL}}", str(len(spec["feeder_pns"]["provisional"])))
            .replace("{{SIDEBAR}}", sidebar)
            .replace("{{PRIMER}}", primer_html)
            .replace("{{MODULES}}", modules_html)
            .replace("{{PRACTICE}}", practice_html)
            .replace("{{SCENARIOS}}", scenarios_html)
            .replace("{{CASES}}", cases_html)
            .replace("{{GENERATED}}", TODAY))
    course_path = d / "course.html"
    course_path.write_text(html, encoding="utf-8")

    # flashcards
    cards = []
    for m in content.get("modules", []):
        for c in m.get("flashcards", []):
            cards.append({**c, "module": m.get("n"), "layer": m.get("layer")})
    fc_dir = VAULT / "Resources" / "Flashcards Logs"
    fc_dir.mkdir(parents=True, exist_ok=True)
    fc_path = fc_dir / f"from-course-{spec['skill_slug']}-{TODAY}.json"
    fc_path.write_text(json.dumps({
        "source": "vault-course", "skill": skill, "domain": domain,
        "generated_at": NOW.isoformat(), "cards": cards}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    # history (append)
    hist = d / "course-history.md"
    prev = hist.read_text(encoding="utf-8") if hist.exists() else f"# Course history — {skill}\n"
    vnum = prev.count("\n## v") + 1
    entry = (f"\n## v{vnum} · {NOW.strftime('%Y-%m-%dT%H:%M')}\n\n"
             f"**Mode**: {spec['mode']}\n"
             f"**Feeder**: {len(spec['feeder_pns']['endorsed'])} endorsed / "
             f"{len(spec['feeder_pns']['provisional'])} provisional\n"
             f"**Modules**: {len(content.get('modules', []))}\n"
             f"**Flashcards**: {len(cards)}\n"
             f"**Scenarios**: {n_scenarios}\n"
             f"**Cases used**: {len(spec['shipped_cases'])}\n")
    hist.write_text(prev + entry, encoding="utf-8")

    print(json.dumps({
        "ok": True, "course_html": str(course_path), "version": vnum,
        "modules": len(content.get("modules", [])), "flashcards": len(cards),
        "scenarios": n_scenarios,
        "flashcards_path": str(fc_path),
    }, ensure_ascii=False))
    return {"ok": True}


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="course-engine — deterministic engine for open-brain-course")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("collect", "render", "validate"):
        p = sub.add_parser(name)
        p.add_argument("domain")
        p.add_argument("skill")
        if name == "collect":
            p.add_argument("--mode", choices=["learning", "review", "aprendizaje", "revision"],
                           default=None,
                           help="force the course mode (legacy values aprendizaje|revision also accepted)")
    rec = sub.add_parser("record-outcome",
                          help="Updates skill_mastery_state.yaml after evaluating a course "
                               "(called by open-brain-course-evaluate)")
    rec.add_argument("domain")
    rec.add_argument("skill")
    rec.add_argument("--result", choices=["pass", "partial", "fail"], required=True)
    rec.add_argument("--note", default="")
    args = ap.parse_args()

    if args.cmd == "validate":
        print(json.dumps(validate(args.domain, args.skill), ensure_ascii=False, indent=2))
    elif args.cmd == "collect":
        collect(args.domain, args.skill, args.mode)
    elif args.cmd == "render":
        render(args.domain, args.skill)
    elif args.cmd == "record-outcome":
        result = record_outcome(args.domain, args.skill, args.result, args.note)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
