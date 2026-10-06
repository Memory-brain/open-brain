#!/usr/bin/env python3
"""
practice-log-engine — deterministic plumbing for the practice-log skill.

Autolink model: file writes, the scaffold and the harvest AGGREGATION live here
(no LLM). The AI keeps the judgment: inferring domain/capabilities, applying the
rubric, classifying gap vs insight, grouping gaps by concept in harvest.

Commands:
  hanging                         → status:open logs started >12h ago (for the open flow)
  muniton <Domain> <Capability>   → endorsed/provisional PNs from feeder-pns.md
  open  --json '<payload>'        → scaffolds the session note (the AI builds the payload)
  close --json '<payload>'        → writes Cierre, frontmatter, gaps.md, promote-feedback,
                                     external_outputs (payload with what the AI captured)
  outcome --file <log> --checklist y,n,y | --score N [--note "..."]  → the user's verdict; CLOSES the log
  abandon --file <log> [--reason "..."] → marks status:abandoned (discarded draft,
                                     does not touch gaps.md/harvest — use for auto-opened logs that do not count)
  harvest <Domain|all> [--days 30]→ aggregates closed logs → JSON of signals for the AI
  bootstrap [--force]             → generates Resources/Practice Capabilities.md from Domains/

The vault is autodetected (via vault-scan). Override with OPEN_BRAIN_VAULT or VAULT_ROOT.
All writes are report-first: they print what they would do and do it unless --dry-run.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, date, timedelta
from pathlib import Path


def _bootstrap_vaultscan():
    envs = [os.environ.get(k) for k in ("OPEN_BRAIN_ENGINES", "OPEN_BRAIN_VAULT", "VAULT_ROOT")]
    bases = [Path(e) for e in envs if e] + [Path(__file__).resolve().parent,
                                            *Path(__file__).resolve().parents]
    for base in bases:
        for cand in [base / "vault-scan", base]:
            if (cand / "vaultscan.py").exists():
                sys.path.insert(0, str(cand)); return
    raise SystemExit("ERROR: cannot find vault-scan/vaultscan.py. Install vault-scan or set OPEN_BRAIN_ENGINES.")


_bootstrap_vaultscan()
import vaultscan as vs  # noqa: E402

# primitives = vault-scan (single core, no duplication)
VAULT = Path(os.environ["OPEN_BRAIN_VAULT"]) if os.environ.get("OPEN_BRAIN_VAULT") else vs.VAULT
FM_RE = vs.FM_RE
parse_fm = vs.parse_fm
days_since_dt = vs.days_since

PLOG = VAULT / "Practice Log"
NOW = datetime.now(timezone.utc)
TODAY = date.today()


def to_int(v, d=None):
    try:
        return int(str(v).strip())
    except (ValueError, TypeError):
        return d


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------- hanging
def cmd_hanging():
    res = []
    if PLOG.exists():
        for p in PLOG.glob("*.md"):
            fm = parse_fm(p.read_text(encoding="utf-8", errors="ignore"))
            if (fm.get("status") or "") == "open":
                started = fm.get("started") or ""
                m = re.search(r"(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})", started)
                old = True
                if m:
                    try:
                        dt = datetime.fromisoformat(started)
                        old = (datetime.now() - dt) > timedelta(hours=12)
                    except ValueError:
                        old = True
                if old:
                    res.append({"file": str(p.relative_to(VAULT)), "started": started})
    out({"ok": True, "hanging": res})


# ---------------------------------------------------------------- muniton
def cmd_muniton(domain, capability):
    f = VAULT / "Skills" / domain / capability / "feeder-pns.md"
    buckets = {"endorsed": [], "provisional": []}
    if f.exists():
        section = None
        for ln in f.read_text(encoding="utf-8").splitlines():
            h = re.match(r"^##\s+(Endorsed|Provisional)", ln, re.I)
            if h:
                section = h.group(1).lower()
                continue
            m = re.search(r"\[\[([^\]]+)\]\]", ln)
            if m and section in buckets:
                buckets[section].append(m.group(1).split("|")[0].strip())
    out({"ok": True, "feeder_exists": f.exists(), **buckets})


# ---------------------------------------------------------------- open
OPEN_TEMPLATE = """---
domain: {domain}
capabilities: [{caps}]
emergent_capabilities: [{emergent}]
task_type: {task_type}
linked_skill:
linked_artifact:
output_pns: []
linked_pns:
{pns_yaml}
linked_cases: []
started: {started}
closed:
status: open
confidence_before: {confidence}
rubric_score:
outcome_score:
rubric_summary:
score_note:
---

## Briefing

You are training **{domain} / {caps}** on a `{task_type}` task.

PNs available as ammunition:
{pns_brief}

Performance prediction: {confidence}/100

## Cierre

*(filled in by `practice-log close`)*
"""


PIPELINE_TASK_TYPES = {"extraction", "extraccion", "extracción", "extract", "ingest", "enrich", "promote", "index", "health",
                       "maintain", "autolink"}


def _skills_catalog():
    """Actual capability catalog: Skills/<Domain>/<Capability>/ (what muniton reads)."""
    cat = {}
    root = VAULT / "Skills"
    if root.exists():
        for d in root.iterdir():
            if d.is_dir():
                cat[d.name] = sorted(c.name for c in d.iterdir() if c.is_dir())
    return cat


def _match(name, options):
    n = (name or "").strip().lower()
    for o in options:
        if o.lower() == n:
            return o
    return None


def _feeder_pns(domain, cap):
    f = VAULT / "Skills" / domain / cap / "feeder-pns.md"
    res = []
    if f.exists():
        for ln in f.read_text(encoding="utf-8").splitlines():
            m = re.search(r"\[\[([^\]]+)\]\]", ln)
            if m:
                res.append(m.group(1).split("|")[0].strip())
    return res


def cmd_open(payload, dry):
    p = dict(payload)
    # Guard 1: pipeline operations are not practice. Without this guard most hanging
    # logs turned out to be extractions opened with nobody around to close them.
    tt = (p.get("task_type") or "").strip().lower()
    if tt in PIPELINE_TASK_TYPES:
        out({"ok": False, "skipped": True,
             "reason": f"task_type '{tt}' is a pipeline operation, not practice: no log opened"})
        return
    # Guard 2: domain and capabilities checked against the real catalog (Skills/).
    # Free text meant muniton never found ammunition and harvest could not aggregate.
    # Common aliases → canonical domain names (only used if that domain exists in Skills/).
    cat = _skills_catalog()
    if cat:
        # Empty by default. Add lowercase alias -> exact domain name in Skills/,
        # e.g. {"pkm": "Personal Knowledge Management"}.
        aliases = {}
        raw = (p.get("domain") or "").strip()
        dom = _match(aliases.get(raw.lower(), raw), cat.keys())
        if not dom:
            out({"ok": False, "error": f"domain '{p.get('domain')}' does not exist in Skills/",
                 "valid_domains": sorted(cat.keys())})
            return
        p["domain"] = dom
        known, emergent = [], list(p.get("emergent_capabilities", []))
        for c in p.get("capabilities", []):
            m = _match(c, cat[dom])
            (known.append(m) if m else emergent.append(c))
        p["capabilities"], p["emergent_capabilities"] = known, emergent
        if not p.get("linked_pns"):
            seen = []
            for c in known:
                for x in _feeder_pns(dom, c):
                    if x not in seen:
                        seen.append(x)
            p["linked_pns"] = seen[:8]
        warn = [] if known else [f"no capability of {dom} recognised; valid: {cat[dom]}"]
    else:
        warn = []
    caps = ", ".join(p.get("capabilities", []))
    pns = p.get("linked_pns", [])
    pns_yaml = "\n".join(f'  - "[[{x}]]"' for x in pns) or "  []"
    pns_brief = "\n".join(f"- [[{x}]]" for x in pns) or "- (none)"
    started = p.get("started") or datetime.now().strftime("%Y-%m-%dT%H:%M")
    body = OPEN_TEMPLATE.format(
        domain=p["domain"], caps=caps,
        emergent=", ".join(p.get("emergent_capabilities", [])),
        task_type=p.get("task_type", ""),
        pns_yaml=pns_yaml, started=started,
        confidence=p.get("confidence_before", ""), pns_brief=pns_brief)
    slug = re.sub(r"\s+", " ", p.get("task_short", "session")).strip()
    name = f"{TODAY.isoformat()} — {slug}.md"
    path = PLOG / name
    i = 2
    while path.exists():
        path = PLOG / f"{TODAY.isoformat()} — {slug} ({i}).md"
        i += 1
    if not dry:
        PLOG.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    out({"ok": True, "created": str(path.relative_to(VAULT)), "dry_run": dry,
         "domain": p["domain"], "capabilities": p.get("capabilities", []),
         "emergent_capabilities": p.get("emergent_capabilities", []),
         "linked_pns": len(pns), "warnings": warn})


# ---------------------------------------------------------------- close
def _append_block(path: Path, block: str, header: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    prev = path.read_text(encoding="utf-8") if path.exists() else f"# {header}\n"
    path.write_text(prev + block, encoding="utf-8")


def cmd_close(payload, dry):
    p = payload
    log_path = VAULT / p["log_file"] if not os.path.isabs(p["log_file"]) else Path(p["log_file"])
    if not log_path.exists():
        out({"ok": False, "error": f"log does not exist: {log_path}"})
        return
    text = log_path.read_text(encoding="utf-8")
    fm = parse_fm(text)
    domain = fm.get("domain", "")
    caps = fm.get("capabilities", []) if isinstance(fm.get("capabilities"), list) else []
    actions = []

    # 1) Cierre section + Rubric
    gaps = p.get("gaps", [])
    patterns = p.get("patterns", [])
    insights = p.get("insights", [])
    cierre = "\n### Gaps\n" + "\n".join(f"- {g}" for g in gaps)
    cierre += "\n\n### Patterns\n" + "\n".join(f"- {x}" for x in patterns)
    cierre += "\n\n### Insights\n" + "\n".join(f"- {x}" for x in insights)
    rub = p.get("rubric")  # {dims:[{name,score,max}], total, confidence_before}
    if rub:
        cierre += "\n\n### Rubric\n" + "\n".join(
            f"- {d['name']}: {d['score']}/{d.get('max',25)}" for d in rub["dims"])
        cierre += f"\n**Total: {rub['total']}/100**"
        cb = to_int(fm.get("confidence_before"))
        if cb is not None:
            cierre += f"\n\nPrediction: {cb} → Performance: {rub['total']} → Delta: {rub['total']-cb:+d}"
    new_text = re.sub(r"## Cierre.*$", "## Cierre\n" + cierre + "\n", text, flags=re.DOTALL)

    # 2) frontmatter updates
    def set_fm(t, key, val):
        if re.search(rf"^{key}:.*$", t, re.MULTILINE):
            return re.sub(rf"^{key}:.*$", f"{key}: {val}", t, count=1, flags=re.MULTILINE)
        return t
    new_text = set_fm(new_text, "status", "closed")
    new_text = set_fm(new_text, "closed", datetime.now().strftime("%Y-%m-%dT%H:%M"))
    if rub:
        new_text = set_fm(new_text, "rubric_score", rub["total"])
        summary = ", ".join(f"{d['name']} {d['score']}/{d.get('max',25)}" for d in rub["dims"])
        new_text = set_fm(new_text, "rubric_summary", f'"{summary}"')
    if p.get("score_note"):
        new_text = set_fm(new_text, "score_note", f'"{p["score_note"]}"')
    if p.get("output_pns"):
        new_text = set_fm(new_text, "output_pns",
                          "[" + ", ".join(f'"[[{x}]]"' for x in p["output_pns"]) + "]")
    if not dry:
        log_path.write_text(new_text, encoding="utf-8")
    actions.append("note: Cierre + frontmatter updated")

    # 3) gaps.md per capability
    ref = f"[[Practice Log/{log_path.stem}]]"
    for cap in caps:
        gp = VAULT / "Skills" / domain / cap / "gaps.md"
        if not gp.parent.exists():
            continue
        for g in gaps:
            block = (f"\n---\n\n## {NOW.strftime('%Y-%m-%dT%H:%M')} · practice-log · capability:{cap}\n\n"
                     f"**Source**: practice-log\n**Source ref**: {ref}\n"
                     f"**Capability**: {cap}\n**Gap**: \"{g}\"\n**Status**: open\n")
            if not dry:
                _append_block(gp, block, f"Gaps — {cap}")
        if gaps:
            actions.append(f"gaps.md ({cap}): +{len(gaps)} blocks")

    # 4) promote-feedback.md (one friction)
    fr = p.get("friction")  # {pn, friction_type, note, case}
    if fr and caps:
        cap = caps[0]
        pf = VAULT / "Skills" / domain / cap / "promote-feedback.md"
        block = (f"\n---\n\n## {NOW.strftime('%Y-%m-%dT%H:%M')} · practice-log · pn:[[{fr['pn']}]]\n\n"
                 f"**Source**: practice-log\n**Source ref**: {ref}\n"
                 f"**PN**: [[{fr['pn']}]]\n**Case**: {fr.get('case','')}\n"
                 f"**Friction type**: {fr.get('friction_type','')}\n"
                 f"**Owner note**: \"{fr.get('note','')}\"\n**Status**: pending-review\n")
        if not dry:
            _append_block(pf, block, f"Promote Feedback — {cap}")
        actions.append(f"promote-feedback.md ({cap}): friction against [[{fr['pn']}]]")

    # 5) external_outputs ++ on PNs
    incremented = []
    for pn in p.get("output_pns", []):
        pnp = VAULT / "Permanent Notes" / f"{pn}.md"
        if not pnp.exists():
            continue
        t = pnp.read_text(encoding="utf-8")
        m = re.search(r"^external_outputs:\s*(\d+)", t, re.MULTILINE)
        if m:
            t2 = re.sub(r"^external_outputs:\s*\d+", f"external_outputs: {int(m[1])+1}",
                        t, count=1, flags=re.MULTILINE)
        else:
            t2 = re.sub(r"^---\n", f"---\nexternal_outputs: 1\n", t, count=1)
        if not dry:
            pnp.write_text(t2, encoding="utf-8")
        incremented.append(pn)
    if incremented:
        actions.append(f"external_outputs ++ on {len(incremented)} PNs")

    out({"ok": True, "dry_run": dry, "actions": actions})


# ---------------------------------------------------------------- outcome
CHECKLIST_Q = ("used", "decision", "would_repeat")
CHECKLIST_TXT = {"used": "did you use the result?", "decision": "did it change any decision?",
                 "would_repeat": "would you do it the same way again?"}
YES = ("y", "yes", "s", "si", "sí")   # Spanish s/si accepted for backward compatibility
NO = ("n", "no")


def parse_checklist(s):
    """'y,n,y' -> {'used': True, 'decision': False, 'would_repeat': True}.

    CheckEval (arXiv 2403.18771): the reliability of an assessment comes from
    decomposing it into concrete binary questions, not from the scale. A bare 0-5
    score tends to go unanswered. Three concrete yes/no questions replace the
    score; 0-5 is still accepted. That it is cheaper to answer is a hypothesis,
    not what the paper says: review it against your closed logs."""
    vals = [v.strip().lower() for v in (s or "").split(",")]
    if len(vals) != 3 or any(v not in YES + NO for v in vals):
        return None
    return {q: v in YES for q, v in zip(CHECKLIST_Q, vals)}


def cmd_outcome(log_file, score, note, dry, checklist=None):
    """The user's verdict (0-5) and closing of the log. It also sets status:closed;
    otherwise a scored log would keep showing up in hanging."""
    path = VAULT / log_file if not os.path.isabs(log_file) else Path(log_file)
    if not path.exists():
        out({"ok": False, "error": f"does not exist: {path}"}); return
    cl = None
    if checklist is not None:
        cl = parse_checklist(checklist)
        if cl is None:
            out({"ok": False, "error": "--checklist expects three comma-separated y/n: used,decision,would_repeat"}); return
        if score is None:
            # derived and marked as such: it is not a score the user gave
            score = round(5 * sum(cl.values()) / 3)
    if score is None:
        out({"ok": False, "error": "need --checklist y,n,y or --score 0-5"}); return
    if not (0 <= score <= 5):
        out({"ok": False, "error": "outcome_score ranges from 0 to 5 (the user's verdict)"}); return
    t = path.read_text(encoding="utf-8")
    if cl is not None:
        line = "outcome_checklist: {" + ", ".join(f"{k}: {'true' if v else 'false'}" for k, v in cl.items()) + "}"
        if re.search(r"^outcome_checklist:.*$", t, re.MULTILINE):
            t = re.sub(r"^outcome_checklist:.*$", line, t, count=1, flags=re.MULTILINE)
        else:
            t = re.sub(r"^(outcome_score:.*)$", r"\1\n" + line + "\nscore_derived: " +
                       ("true" if checklist is not None else "false"), t, count=1, flags=re.MULTILINE)
    t = re.sub(r"^outcome_score:.*$", f"outcome_score: {score}", t, count=1, flags=re.MULTILINE)
    if note:
        t = re.sub(r"^score_note:.*$", f'score_note: "{note}"', t, count=1, flags=re.MULTILINE)
    fm = parse_fm(t)
    if (fm.get("status") or "") in ("open", ""):
        t = re.sub(r"^status:.*$", "status: closed", t, count=1, flags=re.MULTILINE)
    if not (fm.get("closed") or "").strip():
        t = re.sub(r"^closed:.*$", f"closed: {datetime.now().strftime('%Y-%m-%dT%H:%M')}",
                   t, count=1, flags=re.MULTILINE)
    detail = ""
    if cl is not None:
        detail = "\n" + "\n".join(f"- {CHECKLIST_TXT[k]} {'yes' if v else 'no'}" for k, v in cl.items())
    verdict = f"\n\n### Owner verdict\n{score}/5" + (f" · {note}" if note else "") + detail + "\n"
    # legacy logs carry a Spanish "### Veredicto de ..." heading: do not add a second one
    if not re.search(r"^### (Owner verdict|Veredicto de )", t, re.MULTILINE):
        t = t.rstrip("\n") + verdict
    if not dry:
        path.write_text(t, encoding="utf-8")
    out({"ok": True, "dry_run": dry, "outcome_score": score, "checklist": cl, "status": "closed"})


# ---------------------------------------------------------------- abandon
def cmd_abandon(log_file, reason, dry):
    path = VAULT / log_file if not os.path.isabs(log_file) else Path(log_file)
    if not path.exists():
        out({"ok": False, "error": f"does not exist: {path}"}); return
    text = path.read_text(encoding="utf-8")
    fm = parse_fm(text)
    if (fm.get("status") or "") == "closed":
        out({"ok": False, "error": "the log is already closed — use outcome, not abandon"}); return

    def set_fm(t, key, val):
        if re.search(rf"^{key}:.*$", t, re.MULTILINE):
            return re.sub(rf"^{key}:.*$", f"{key}: {val}", t, count=1, flags=re.MULTILINE)
        return t

    new_text = set_fm(text, "status", "abandoned")
    new_text = set_fm(new_text, "closed", datetime.now().strftime("%Y-%m-%dT%H:%M"))
    if reason:
        note = f"\n\n### Abandoned\n{reason}\n"
        if "## Cierre" in new_text:
            new_text = re.sub(r"## Cierre.*$", "## Cierre" + note, new_text, flags=re.DOTALL)
        else:
            new_text += note
    if not dry:
        path.write_text(new_text, encoding="utf-8")
    try:
        rel = str(path.relative_to(VAULT))
    except ValueError:
        rel = str(path)
    out({"ok": True, "dry_run": dry, "abandoned": rel})


# ---------------------------------------------------------------- harvest
def _norm(s):
    return re.sub(r"[^a-záéíóúñ ]", "", s.lower()).strip()


def cmd_harvest(domain, days):
    cutoff = TODAY - timedelta(days=days)
    sessions = []
    if PLOG.exists():
        for p in PLOG.glob("*.md"):
            if p.name.lower().startswith("readme"):
                continue
            fm = parse_fm(p.read_text(encoding="utf-8", errors="ignore"))
            if (fm.get("status") or "") != "closed":
                continue
            if domain != "all" and (fm.get("domain") or "") != domain:
                continue
            d = days_since_dt(fm.get("closed") or fm.get("started"))
            if d is not None and d > days:
                continue
            sessions.append((p, fm))

    cap_count, cap_scores, cap_calib = {}, {}, {}
    pn_muniton, friction_pns = {}, {}
    for p, fm in sessions:
        caps = fm.get("capabilities", []) if isinstance(fm.get("capabilities"), list) else []
        for c in caps:
            cap_count[c] = cap_count.get(c, 0) + 1
            rs = to_int(fm.get("rubric_score"))
            if rs is not None:
                cap_scores.setdefault(c, []).append(rs)
                cb = to_int(fm.get("confidence_before"))
                if cb is not None:
                    cap_calib.setdefault(c, []).append(abs(cb - rs))
        for pn in (fm.get("linked_pns", []) if isinstance(fm.get("linked_pns"), list) else []):
            pn_muniton[pn] = pn_muniton.get(pn, 0) + 1

    def avg(xs):
        return round(sum(xs) / len(xs)) if xs else None

    out({
        "ok": True, "domain": domain, "window_days": days,
        "sessions_closed": len(sessions),
        "capabilities_trained": sorted(
            [{"capability": c, "sessions": n} for c, n in cap_count.items()],
            key=lambda x: -x["sessions"]),
        "performance": [
            {"capability": c, "scored_sessions": len(s), "avg_rubric_score": avg(s),
             "scores": s}
            for c, s in cap_scores.items()],
        "calibration": [
            {"capability": c, "calibrated_sessions": len(s), "avg_abs_delta": avg(s)}
            for c, s in cap_calib.items()],
        "top_muniton_pns": sorted(
            [{"pn": k, "times": v} for k, v in pn_muniton.items()],
            key=lambda x: -x["times"])[:10],
        "note": "The AI groups recurring gaps/patterns by concept (semantically) by reading "
                "the capabilities' gaps.md files — the engine does not do that grouping.",
    })


# ---------------------------------------------------------------- bootstrap
def cmd_bootstrap(dry, force=False):
    """Read Domains/ folder and generate/update Resources/Practice Capabilities.md.

    Extracts domain names and competencies from domain-index notes.
    - If Practice Capabilities.md already has content (## headings), skip to avoid
      overwriting user edits (unless force=True).
    - If empty or missing, generate from Domains/.
    """
    cap_file = VAULT / "Resources" / "Practice Capabilities.md"

    # Guard: don't overwrite if already has domain sections
    if not force and cap_file.exists():
        existing = cap_file.read_text(encoding="utf-8")
        if re.search(r"^## (?!Reglas|Rules)\w", existing, re.MULTILINE):
            out({"ok": False, "error": "Practice Capabilities.md already has domains defined. "
                 "Use --force to regenerate.", "path": str(cap_file.relative_to(VAULT))})
            return

    domains_dir = VAULT / "Domains"
    if not domains_dir.exists():
        out({"ok": False, "error": "No Domains/ folder found in vault."})
        return

    sections = []
    for p in sorted(domains_dir.glob("*.md")):
        raw = p.read_text(encoding="utf-8", errors="ignore")
        fm = parse_fm(raw)
        domain_name = fm.get("domain") or p.stem

        # Try to extract competencies from Competency Map table
        skills = []
        # Pattern: | CompetencyName | layer | notes | maturity |
        for row in re.finditer(
            r"^\|\s*([^|]+?)\s*\|\s*(\w[\w-]*)\s*\|.*?\|.*?\|",
            raw, re.MULTILINE
        ):
            name = row.group(1).strip()
            # Skip table header rows
            if name.startswith("---") or name.lower() in ("competency", "competencia"):
                continue
            layer = row.group(2).strip()
            skills.append((name, layer))

        section = f"## {domain_name}\n"
        if skills:
            for name, layer in skills:
                section += f"- **{name}** — {layer}-level capability in {domain_name}\n"
        else:
            desc = fm.get("description", "").strip()
            section += f"- **Core {domain_name}** — {desc or f'foundational skills in {domain_name}'}\n"
        sections.append(section)

    if not sections:
        out({"ok": False, "error": "No domain notes found in Domains/."})
        return

    body = "# Practice Capabilities\n\n"
    body += "> Auto-generated from Domains/ by practice-log bootstrap.\n"
    body += "> Edit freely — add, rename, or remove skills.\n\n"
    body += "\n".join(sections)
    body += "\n\n## Emergent\n\n"
    body += "> Capabilities discovered during practice that don't fit existing domains yet.\n"

    if not dry:
        cap_file.parent.mkdir(parents=True, exist_ok=True)
        cap_file.write_text(body, encoding="utf-8")

    domain_count = len(sections)
    skill_count = sum(1 for s in sections for _ in re.finditer(r"^- \*\*", s, re.MULTILINE))
    out({"ok": True, "dry_run": dry,
         "path": str(cap_file.relative_to(VAULT)),
         "domains": domain_count, "skills": skill_count,
         "note": "Edit the file to refine skill names and definitions."})


def cmd_bootstrap_force(dry):
    """Same as bootstrap but overwrites existing content (backs up first)."""
    cap_file = VAULT / "Resources" / "Practice Capabilities.md"
    if cap_file.exists() and not dry:
        import shutil
        backup = cap_file.with_suffix(".md.bak")
        shutil.copy2(cap_file, backup)
    cmd_bootstrap(dry, force=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("hanging")
    m = sub.add_parser("muniton"); m.add_argument("domain"); m.add_argument("capability")
    for name in ("open", "close"):
        s = sub.add_parser(name)
        s.add_argument("--json", required=True)
        s.add_argument("--dry-run", action="store_true")
    o = sub.add_parser("outcome")
    o.add_argument("--file", required=True); o.add_argument("--score", type=int, default=None)
    o.add_argument("--checklist", default=None, help="y,n,y = did you use the result?, did it change any decision?, would you do it the same way?")
    o.add_argument("--note", default=""); o.add_argument("--dry-run", action="store_true")
    ab = sub.add_parser("abandon")
    ab.add_argument("--file", required=True); ab.add_argument("--reason", default="")
    ab.add_argument("--dry-run", action="store_true")
    h = sub.add_parser("harvest"); h.add_argument("domain"); h.add_argument("--days", type=int, default=30)
    b = sub.add_parser("bootstrap"); b.add_argument("--dry-run", action="store_true")
    b.add_argument("--force", action="store_true")
    a = ap.parse_args()

    if a.cmd == "hanging":
        cmd_hanging()
    elif a.cmd == "muniton":
        cmd_muniton(a.domain, a.capability)
    elif a.cmd == "open":
        cmd_open(json.loads(a.json), a.dry_run)
    elif a.cmd == "close":
        cmd_close(json.loads(a.json), a.dry_run)
    elif a.cmd == "outcome":
        cmd_outcome(a.file, a.score, a.note, a.dry_run, checklist=a.checklist)
    elif a.cmd == "abandon":
        cmd_abandon(a.file, a.reason, a.dry_run)
    elif a.cmd == "harvest":
        cmd_harvest(a.domain, a.days)
    elif a.cmd == "bootstrap":
        if a.force:
            cmd_bootstrap_force(a.dry_run)
        else:
            cmd_bootstrap(a.dry_run)


if __name__ == "__main__":
    main()
