"""
validation_gap.py — Validation Gap Report (deterministic, no LLM).

The vault has many synthesized claims (Permanent Notes) but few are validated
against lived experience (Cases). A claim no Case backs is theory, not judgment.
This script makes that gap actionable WITHOUT fabricating Cases — Cases are
the vault owner's real experiences only. It surfaces three things:

  1. VALIDATION QUEUE — load-bearing PNs (high times_retrieved + graph in-degree)
     that NO Case validates. These are the claims most worth grounding in a real case.
  2. ORPHAN CASES — Cases with no `principles_validated` field: real experiences
     captured but not wired to any principle. Cheapest win: link them.
  3. BROKEN LINKS — `principles_validated` entries pointing to PNs that don't exist
     (renamed/moved). Re-point them.

Linkage model:
  - Case frontmatter: `principles_validated: [[PN title]], ...`  (Case → PN)
  - PN frontmatter (optional reciprocal): `cases: [[Case title]]`

Usage:
  python3 validation_gap.py                 # coverage + top unvalidated PNs + orphans
  python3 validation_gap.py --limit 30      # widen the queue
  python3 validation_gap.py --min-tr 1      # only PNs retrieved >=1 (default 1)
  python3 validation_gap.py --json          # machine-readable (for health engine)

Flags:
  --limit N     max PNs in the validation queue (default 20)
  --min-tr N    only queue PNs with times_retrieved >= N (default 1; load-bearing)
  --json        emit JSON instead of the human report
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
GRAPH_FILE = SCRIPT_DIR / "graph.jsonl"

# Vault root: $OPEN_BRAIN_VAULT if set, otherwise the parent of this autolink/ folder.
VAULT_INNER = Path(os.environ.get("OPEN_BRAIN_VAULT") or SCRIPT_DIR.resolve().parent)

LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
FM_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def frontmatter(text: str) -> str:
    m = FM_RE.match(text)
    return m.group(1) if m else ""


def list_field(fm: str, field: str) -> list[str]:
    """Extract [[wikilinks]] from a YAML list/inline field until the next top-level key."""
    m = re.search(rf"^{field}:(.*?)(?:\n[A-Za-z_]+:|\Z)", fm, re.DOTALL | re.MULTILINE)
    if not m:
        return []
    # Fold multi-line YAML values (quoted strings wrapped across lines with
    # indentation) into single-line text before extracting links — otherwise a
    # wikilink whose title happens to wrap across two YAML lines is captured
    # with the literal "\n  " still inside it and never matches any real note
    # stem, producing a false-positive broken link.
    folded = re.sub(r"\s*\n\s*", " ", m.group(1))
    return [x.split("|")[0].strip() for x in LINK_RE.findall(folded)]


def load_indegree() -> Counter:
    """Graph in-degree per note title (how many notes point to it) = load-bearing proxy."""
    deg: Counter = Counter()
    if not GRAPH_FILE.exists():
        return deg
    with GRAPH_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                deg[e["to"]] += 1
            except Exception:
                continue
    return deg


def scan() -> dict:
    pn_dir = VAULT_INNER / "Permanent Notes"
    case_dir = VAULT_INNER / "Cases"

    # PNs: title -> times_retrieved
    pn_tr: dict[str, int] = {}
    for p in glob.glob(str(pn_dir / "*.md")):
        title = os.path.splitext(os.path.basename(p))[0]
        fm = frontmatter(open(p, encoding="utf-8", errors="ignore").read())
        mm = re.search(r"times_retrieved:\s*(\d+)", fm)
        pn_tr[title] = int(mm.group(1)) if mm else 0

    # Cases: validated PNs + orphans + broken links
    validated: set[str] = set()
    orphan_cases: list[str] = []
    broken_links: list[tuple[str, str]] = []
    cases = glob.glob(str(case_dir / "*.md"))
    for c in cases:
        name = os.path.basename(c)
        fm = frontmatter(open(c, encoding="utf-8", errors="ignore").read())
        pvs = list_field(fm, "principles_validated")
        if not pvs:
            orphan_cases.append(name)
            continue
        for pv in pvs:
            if pv in pn_tr:
                validated.add(pv)
            else:
                broken_links.append((name, pv))

    indeg = load_indegree()
    unval = {t: tr for t, tr in pn_tr.items() if t not in validated}
    # importance = times_retrieved (primary) + graph in-degree (secondary, scaled)
    def importance(t: str) -> tuple[int, int]:
        return (unval[t], indeg.get(t, 0))

    queue = sorted(unval, key=importance, reverse=True)
    return {
        "pn_total": len(pn_tr),
        "validated": len(validated),
        "unvalidated": len(unval),
        "coverage_pct": round(100 * len(validated) / len(pn_tr), 1) if pn_tr else 0.0,
        "cases_total": len(cases),
        "orphan_cases": orphan_cases,
        "broken_links": broken_links,
        "queue": [
            {"pn": t, "times_retrieved": unval[t], "in_degree": indeg.get(t, 0)}
            for t in queue
        ],
        "_indeg": indeg,
    }


def to_payload(data: dict, limit: int, min_tr: int) -> dict:
    q = [x for x in data["queue"] if x["times_retrieved"] >= min_tr][:limit]
    return {
        "pn_total": data["pn_total"],
        "validated": data["validated"],
        "unvalidated": data["unvalidated"],
        "coverage_pct": data["coverage_pct"],
        "cases_total": data["cases_total"],
        "orphan_cases": data["orphan_cases"],
        "broken_links": [{"case": c, "missing_pn": p} for c, p in data["broken_links"]],
        "validation_queue": q,
    }


def print_report(p: dict) -> None:
    print("\n🧪 VALIDATION GAP REPORT")
    print("=" * 72)
    print(
        f"  {p['validated']}/{p['pn_total']} PNs validated by a Case "
        f"({p['coverage_pct']}%) — {p['unvalidated']} unvalidated. "
        f"{p['cases_total']} Cases total."
    )

    print(f"\n  🎯 VALIDATION QUEUE — load-bearing claims with NO Case (ground these in a real experience):")
    if not p["validation_queue"]:
        print("     (none above threshold)")
    for x in p["validation_queue"]:
        print(f"     tr={x['times_retrieved']:2d} in={x['in_degree']:3d}  {x['pn'][:74]}")

    if p["orphan_cases"]:
        print(f"\n  🔗 ORPHAN CASES — real experiences not linked to any principle (cheapest win — wire `principles_validated`):")
        for c in p["orphan_cases"]:
            print(f"     - {c}")

    if p["broken_links"]:
        print(f"\n  ⚠️  BROKEN principles_validated LINKS (re-point to the renamed PN):")
        for b in p["broken_links"]:
            print(f"     {b['case']}  →  [[{b['missing_pn']}]]")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--min-tr", dest="min_tr", type=int, default=1)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    payload = to_payload(scan(), args.limit, args.min_tr)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_report(payload)


if __name__ == "__main__":
    main()
