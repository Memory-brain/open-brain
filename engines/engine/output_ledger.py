"""
output_ledger.py — two-tier output ledger (v2).

WHY IT EXISTS: a ledger that only records public publications sees a tiny
fraction of real production — most delivered work (proposals, plans, handoffs,
team docs) never gets published. An "outputs per week" metric built on it
measures almost nothing.

TWO TIERS:
  shipped   — artifact delivered to someone other than you (proposal, plan,
              handoff, team doc, one-pager, PDF, Case).
  published — goes out to the open world (a website, social post, talk).
`published` is a conceptual subset: a published artifact was also delivered.
The published/shipped ratio is the last-mile metric.

ANTI-GOODHART GUARD: `audience` is mandatory. No recipient, no count.
Machine files (health reports, evals, logs, this very report) DO NOT count:
they are excluded by folder and by pattern.

TRACEABILITY: `source_notes` is extracted from the document's own wikilinks
that resolve to a real PN or LN. That makes `external_outputs` auditable
instead of a hand-written counter.

LEDGER PATH: Resources/Output Ledger/ledger.jsonl.
Vault root: OPEN_BRAIN_VAULT if set, otherwise the parent of this script's folder.

USAGE:
  python3 engine/output_ledger.py scan            # what it would detect, no writes
  python3 engine/output_ledger.py backfill        # writes the new entries
  python3 engine/output_ledger.py series          # weekly shipped/published series
  python3 engine/output_ledger.py series --json   # same, as JSON
  python3 engine/output_ledger.py counters        # derives counters per PN/LN
  python3 engine/output_ledger.py counters --apply  # writes them to frontmatter
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

VAULT = Path(os.environ["OPEN_BRAIN_VAULT"]) if os.environ.get("OPEN_BRAIN_VAULT") \
    else Path(__file__).resolve().parent.parent
LEDGER = VAULT / "Resources" / "Output Ledger" / "ledger.jsonl"

# Default lower bound for artifact dates (YYYY-MM-DD). Neutral: count everything.
# Pass --since to restrict the window.
DEFAULT_SINCE = "2000-01-01"

# Folders where deliverable work lives
ARTIFACT_ROOTS = ["Projects", "Playbooks", "Manuscripts", "Cases", "Areas", "Published"]
# Never count: machinery, notes, raw material. Add your own patterns here.
EXCLUDE_DIR_PAT = re.compile(
    r"(?:^|/)(?:Sources|Extracted Text|Archive|_to_delete|"
    r"Drafts|Abandoned)(?:/|$)", re.I)
EXCLUDE_FILE_PAT = re.compile(
    r"(transcript|export|dump|\braw\b|health report|vault health|eval|\blog\b)", re.I)
# Docs about the vault's own machinery: the audience is you, they do not count
# (anti-Goodhart guard: the system cannot score itself for documenting itself).
# Status and audit documents of a vault system ABOUT ITSELF are not deliverables —
# same class as an eval. What is APPLIED still counts (proposals, handoffs, Cases).
# Add your own self-referential title patterns here.
SELF_REFERENTIAL_PAT = re.compile(r"(hot cache|vault map)", re.I)
SELF_REFERENTIAL_TYPES = {"eval-report", "testing-plan", "pre-registration", "tracker", "audit"}
EXT = {".md", ".pdf", ".docx", ".pptx", ".html", ".xlsx"}

KIND_BY_HINT = [
    (re.compile(r"handoff", re.I), "handoff"),
    (re.compile(r"propuesta|proposal", re.I), "proposal"),
    (re.compile(r"^plan |plan de |plan —|plan-", re.I), "plan"),
    (re.compile(r"one-?pager|onepager", re.I), "one-pager"),
    (re.compile(r"recap|slack", re.I), "message"),
    (re.compile(r"case ?-|^case", re.I), "case"),
    (re.compile(r"guía|guide|playbook|cuadernillo|workbook", re.I), "guide"),
    (re.compile(r"update|novedades|release", re.I), "update"),
    (re.compile(r"spec|especificaci", re.I), "spec"),
    (re.compile(r"síntesis|sintesis|synthesis|research", re.I), "report"),
]

# Audience inferred from the path when the artifact does not declare `audience:`.
# Project folders are deliberately absent: declare `audience:` in the artifact's
# frontmatter, or add entries such as
#   (re.compile(r"Projects/Active/<Your Project>", re.I), "<project team>"),
AUDIENCE_BY_PATH = [
    (re.compile(r"Published", re.I), "public audience"),
    (re.compile(r"Manuscripts", re.I), "public audience (draft)"),
    (re.compile(r"Cases", re.I), "own shareable record"),
    (re.compile(r"Playbooks", re.I), "team / shared use"),
    (re.compile(r"Areas", re.I), "personal"),
]


def fm_of(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    m = re.match(r"---\n(.*?)\n---", raw, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if mm:
            out[mm.group(1)] = mm.group(2).strip().strip('"\'')
    return out


def body_of(path: Path) -> str:
    if path.suffix.lower() != ".md":
        return ""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    parts = re.split(r"^---\s*$", raw, maxsplit=2, flags=re.M)
    return parts[2] if len(parts) >= 3 else raw


def note_index() -> tuple[set, set]:
    pn = {p.stem for p in (VAULT / "Permanent Notes").rglob("*.md")}
    ln = {p.stem for p in (VAULT / "Literature Notes").rglob("*.md")}
    return pn, ln


def date_of(path: Path, fm: dict) -> str | None:
    m = re.search(r"(20\d\d-\d\d-\d\d)", path.name)
    if m:
        return m.group(1)
    for k in ("published_date", "created", "session_date", "date", "ship_by"):
        v = str(fm.get(k, ""))[:10]
        if re.match(r"20\d\d-\d\d-\d\d", v):
            return v
    return None


def kind_of(path: Path, fm: dict) -> str:
    t = str(fm.get("type", "")).strip().lower()
    if t in {"case", "playbook", "published", "spec", "plan"}:
        return t
    for pat, k in KIND_BY_HINT:
        if pat.search(path.name):
            return k
    return "document"


def audience_of(path: Path, fm: dict) -> str:
    if fm.get("audience"):
        return str(fm["audience"])
    rel = str(path.relative_to(VAULT))
    for pat, a in AUDIENCE_BY_PATH:
        if pat.search(rel):
            return a
    return ""


def tier_of(path: Path, fm: dict) -> str:
    rel = str(path.relative_to(VAULT))
    if rel.startswith("Published/") or fm.get("url") or fm.get("platform") \
       or str(fm.get("status", "")).lower() == "published":
        return "published"
    return "shipped"


def iso_week(d: str) -> str:
    y, m, dd = map(int, d.split("-"))
    c = datetime.date(y, m, dd).isocalendar()
    return f"{c[0]}-W{c[1]:02d}"


def discover(year_from: str = DEFAULT_SINCE) -> list[dict]:
    pn, ln = note_index()
    rows = []
    for root in ARTIFACT_ROOTS:
        base = VAULT / root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in EXT:
                continue
            rel = str(p.relative_to(VAULT))
            if EXCLUDE_DIR_PAT.search(rel) or EXCLUDE_FILE_PAT.search(p.name):
                continue
            if SELF_REFERENTIAL_PAT.search(p.name):
                continue
            fm = fm_of(p)
            if str(fm.get("type", "")).strip().lower() in SELF_REFERENTIAL_TYPES:
                continue
            d = date_of(p, fm)
            if not d or d < year_from:
                continue
            aud = audience_of(p, fm)
            if not aud:          # anti-Goodhart guard: no recipient, no count
                continue
            src = []
            for t in re.findall(r"\[\[([^\]]+)\]\]", body_of(p)):
                b = t.split("|")[0].split("#")[0].split("/")[-1].replace(".md", "").strip()
                if b in pn:
                    src.append({"note": b, "type": "PN"})
                elif b in ln:
                    src.append({"note": b, "type": "LN"})
            seen, uniq = set(), []
            for s in src:
                if s["note"] not in seen:
                    seen.add(s["note"]); uniq.append(s)
            rows.append({
                "week": iso_week(d), "date": d, "tier": tier_of(p, fm),
                "kind": kind_of(p, fm), "title": p.stem, "audience": aud,
                "path": rel, "source_notes": uniq,
                # Explicit provenance. Without it, an entry without `source_notes` and
                # one with them read the same: the empty list did not distinguish "rests
                # on nothing" from "nobody looked". `missing` is NOT an error and blocks
                # nothing here: it is the mark that makes the gap countable. Any gating
                # belongs to whatever publishing step you run downstream.
                "provenance": ("linked" if uniq else "missing"),
                "url": fm.get("url", "") or fm.get("link", ""),
                "audience_source": "declared" if fm.get("audience") else "inferred",
                "detected_by": "output_ledger.py v2",
            })
    rows.sort(key=lambda r: (r["date"], r["path"]))
    # dedup md/pdf of the SAME artifact: keeping an index .md next to the delivered
    # .pdf would otherwise count one deliverable twice. The .md is preferred: it is
    # the only one source_notes can be extracted from.
    best = {}
    for r in rows:
        k = (r["title"].lower(), r["date"])
        prev = best.get(k)
        if prev is None or (not prev["path"].lower().endswith(".md")
                            and r["path"].lower().endswith(".md")):
            best[k] = r
    rows = sorted(best.values(), key=lambda r: (r["date"], r["path"]))
    return rows


def load_ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def key_of(row: dict) -> str:
    return (row.get("path") or row.get("url") or row.get("title", "")).lower()


def cmd_scan(args):
    rows = discover(args.since)
    have = {key_of(r) for r in load_ledger()}
    new = [r for r in rows if key_of(r) not in have]
    print(f"detected {len(rows)} artifacts with a recipient | new {len(new)}")
    print("by tier:", Counter(r["tier"] for r in rows).most_common())
    print("by kind:", Counter(r["kind"] for r in rows).most_common())
    print("with source_notes:", sum(1 for r in rows if r["source_notes"]),
          f"({100*sum(1 for r in rows if r['source_notes'])/max(1,len(rows)):.0f}%)")
    missing = [r for r in rows if r.get("provenance") == "missing"]
    print(f"provenance: linked={len(rows)-len(missing)}  missing={len(missing)}"
          + (f"  <- {len(missing)} deliverables recorded without knowing what they rest on" if missing else ""))
    for r in new[-12:]:
        print(f"  {r['date']} [{r['tier']:9s}] {r['kind']:10s} {r['title'][:52]:52s} ← {len(r['source_notes'])} notes")


def cmd_backfill(args):
    rows = discover(args.since)
    existing = load_ledger()
    have = {key_of(r) for r in existing}
    new = [r for r in rows if key_of(r) not in have]
    # preservation: back up before rewriting
    if existing:
        bak = LEDGER.with_name(f"ledger-backup-{datetime.date.today().isoformat()}.jsonl")
        if not bak.exists():
            bak.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in existing) + "\n",
                           encoding="utf-8")
    for r in existing:
        r.setdefault("tier", "published")
        r.setdefault("audience", "public audience")
    allrows = existing + new
    allrows.sort(key=lambda r: (r.get("date", ""), r.get("path", "")))
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in allrows) + "\n",
                      encoding="utf-8")
    print(f"ledger: {len(existing)} → {len(allrows)} entries (+{len(new)})")


def cmd_series(args):
    rows = load_ledger()
    by = defaultdict(Counter)
    for r in rows:
        if r.get("date", "") >= args.since:
            by[r.get("week") or iso_week(r["date"])][r.get("tier", "shipped")] += 1
    if getattr(args, "json", False):
        weeks = sorted(by)
        tot = Counter()
        for w in weeks:
            tot += by[w]
        n = max(1, len(weeks))
        print(json.dumps({
            "ok": True, "schema": "output-ledger-series/1",
            "since": args.since,
            "shipped": tot["shipped"], "published": tot["published"],
            "shipped_per_week": round(tot["shipped"] / n, 2),
            "published_ratio": round(tot["published"] / max(1, tot["shipped"]), 4),
            "series": [{"week": w, "shipped": by[w]["shipped"],
                        "published": by[w]["published"]} for w in weeks],
        }, ensure_ascii=False))
        return
    print("week        shipped  published")
    tot = Counter()
    for w in sorted(by):
        print(f"  {w}   {by[w]['shipped']:>5}   {by[w]['published']:>7}")
        tot += by[w]
    n = max(1, len(by))
    print(f"\ntotal shipped {tot['shipped']} · published {tot['published']} "
          f"· mean {tot['shipped']/n:.1f} shipped/week · published/shipped ratio "
          f"{tot['published']/max(1,tot['shipped']):.3f}")


def cmd_counters(args):
    rows = load_ledger()
    pub, ship = Counter(), Counter()
    pn_stems, ln_stems = note_index()
    def norm(name):
        n = str(name).strip()
        n = re.sub(r"^(?:PN|LN)\s*-\s*", "", n)
        if n in pn_stems or n in ln_stems:
            return n
        cand = [s for s in (pn_stems | ln_stems) if s.startswith(n[:45])] if len(n) > 20 else []
        return cand[0] if len(cand) == 1 else n
    for r in rows:
        for s in r.get("source_notes", []):
            nm = norm(s["note"] if isinstance(s, dict) else s)
            (pub if r.get("tier") == "published" else ship)[nm] += 1
    print(f"notes cited by some output: {len(set(pub) | set(ship))} "
          f"(published {len(pub)}, shipped {len(ship)})")
    changed = []
    for folder in ("Permanent Notes", "Literature Notes"):
        for p in (VAULT / folder).rglob("*.md"):
            e_new, i_new = pub.get(p.stem, 0), ship.get(p.stem, 0)
            fm = fm_of(p)
            e_old = int(fm.get("external_outputs") or 0) if str(fm.get("external_outputs", "")).isdigit() else 0
            i_old = int(fm.get("internal_outputs") or 0) if str(fm.get("internal_outputs", "")).isdigit() else 0
            if (e_new, i_new) != (e_old, i_old) and (e_new or i_new or e_old):
                changed.append((p, e_old, e_new, i_old, i_new))
    print(f"notes with a counter to update: {len(changed)}")
    for p, eo, en, io, iN in changed[:25]:
        print(f"   {p.stem[:58]:58s} external {eo}→{en}  internal {io}→{iN}")
    if not args.apply:
        print("\n(dry-run: --apply to write)")
        return
    for p, eo, en, io, iN in changed:
        raw = p.read_text(encoding="utf-8")
        m = re.match(r"(---\n)(.*?)(\n---)", raw, re.S)
        if not m:
            continue
        fmtxt = m.group(2)
        # external_outputs: published only (keeps the gate's meaning)
        if eo > en and not re.search(r"^external_outputs_legacy:", fmtxt, re.M):
            fmtxt += f"\nexternal_outputs_legacy: {eo}   # hand-written value, no trace in the ledger"
        if re.search(r"^external_outputs:.*$", fmtxt, re.M):
            fmtxt = re.sub(r"^external_outputs:.*$", f"external_outputs: {en}", fmtxt, flags=re.M)
        else:
            fmtxt += f"\nexternal_outputs: {en}"
        if re.search(r"^internal_outputs:.*$", fmtxt, re.M):
            fmtxt = re.sub(r"^internal_outputs:.*$", f"internal_outputs: {iN}", fmtxt, flags=re.M)
        else:
            fmtxt += f"\ninternal_outputs: {iN}"
        p.write_text(m.group(1) + fmtxt + m.group(3) + raw[m.end():], encoding="utf-8")
    print(f"wrote {len(changed)} files")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    for name, fn in (("scan", cmd_scan), ("backfill", cmd_backfill), ("series", cmd_series), ("counters", cmd_counters)):
        p = sub.add_parser(name)
        p.add_argument("--since", default=DEFAULT_SINCE,
                       help="only artifacts dated on/after YYYY-MM-DD")
        if name == "series":
            p.add_argument("--json", action="store_true",
                           help="series and aggregates to stdout as JSON (writes nothing)")
        if name == "counters":
            p.add_argument("--apply", action="store_true")
        p.set_defaults(fn=fn)
    a = ap.parse_args()
    if not getattr(a, "fn", None):
        ap.print_help(); return
    a.fn(a)


if __name__ == "__main__":
    main()
