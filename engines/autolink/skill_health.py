"""
skill_health.py — Detect skill degradation from Practice Logs.

Reads every practice log in the vault (`Practice Log/*.md`), groups them by
`linked_skill` and `capabilities` (skills are discovered from the logs
themselves — no list is hardcoded), and detects degradation, stagnation and
recurring abandonment.

Usage:
  python3 skill_health.py scan          # full analysis to stdout
  python3 skill_health.py brief         # compact scorecard-style brief
  python3 skill_health.py scan --json   # machine-readable output
  python3 skill_health.py brief --json

Flags:
  --json       JSON output instead of markdown
  --min N      minimum data points for analysis (default 3)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# Vault root: $OPEN_BRAIN_VAULT if set, otherwise the parent of this autolink/ folder.
VAULT_DIR = Path(os.environ.get("OPEN_BRAIN_VAULT") or SCRIPT_DIR.parent)
PRACTICE_LOG_DIR = VAULT_DIR / "Practice Log"

# Thresholds (rubric_score is 0-100)
DEGRADATION_AVG = 70        # rolling avg below this = degraded
DEGRADATION_DROP = 15       # drop from peak > this = degraded
STAGNATION_STDDEV = 3.0     # stddev < this over last 5 = stagnant
ROLLING_WINDOW = 5
ABANDON_RATE_WARN = 0.4     # >40% abandoned = problem signal


# ============================================================
# FRONTMATTER PARSING
# ============================================================


def parse_frontmatter(text: str) -> dict | None:
    """Extract YAML frontmatter from markdown. Regex-based, no pyyaml needed."""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    raw = m.group(1)
    fm: dict = {}
    for line in raw.split("\n"):
        # skip list items and empty lines
        if line.strip().startswith("-") or not line.strip():
            continue
        colon = line.find(":")
        if colon == -1:
            continue
        key = line[:colon].strip()
        val = line[colon + 1:].strip()
        # parse simple list on same line: [a, b, c]
        if val.startswith("[") and val.endswith("]"):
            items = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
            fm[key] = items
        elif val == "" or val == "[]":
            fm[key] = None
        else:
            fm[key] = val.strip("'\"")
    return fm


def parse_gaps(text: str) -> list[str]:
    """Extract gap lines from the Gaps section (inside `## Cierre`, the closing section)."""
    gaps: list[str] = []
    in_gaps = False
    for line in text.split("\n"):
        stripped = line.strip()
        if re.match(r"^#{1,4}\s+Gaps", stripped):
            in_gaps = True
            continue
        if in_gaps:
            if stripped.startswith("#"):
                break
            if stripped.startswith("- "):
                gaps.append(stripped[2:].strip())
    return gaps


# ============================================================
# DATA LOADING
# ============================================================


def load_logs() -> list[dict]:
    """Read all practice log .md files, return parsed records."""
    if not PRACTICE_LOG_DIR.exists():
        raise SystemExit(f"Practice log folder not found: {PRACTICE_LOG_DIR} (create it or set OPEN_BRAIN_VAULT)")
    records: list[dict] = []
    for f in sorted(PRACTICE_LOG_DIR.glob("*.md")):
        if f.name == "README.md":
            continue
        text = f.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if not fm:
            continue
        # Parse rubric_score
        score = None
        raw_score = fm.get("rubric_score")
        if raw_score is not None:
            try:
                score = int(raw_score) if isinstance(raw_score, str) else int(raw_score)
            except (ValueError, TypeError):
                score = None
        # Parse date from filename
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", f.name)
        date_str = date_match.group(1) if date_match else ""
        records.append({
            "file": f.name,
            "date": date_str,
            "domain": fm.get("domain", ""),
            "capabilities": fm.get("capabilities") or [],
            "linked_skill": fm.get("linked_skill") or "",
            "status": fm.get("status", "open"),
            "rubric_score": score,
            "gaps": parse_gaps(text),
            "task_type": fm.get("task_type", ""),
        })
    return records


# ============================================================
# ANALYSIS
# ============================================================


def rolling_avg(scores: list[int], window: int = ROLLING_WINDOW) -> float:
    recent = scores[-window:]
    return sum(recent) / len(recent) if recent else 0.0


def stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def analyze(records: list[dict], min_points: int = 3) -> dict:
    """Group by skill/capability, detect degradation & stagnation."""
    # Group by linked_skill (non-empty) and by each capability
    by_skill: dict[str, list[dict]] = defaultdict(list)
    by_cap: dict[str, list[dict]] = defaultdict(list)
    by_domain: dict[str, list[dict]] = defaultdict(list)

    for r in records:
        if r["linked_skill"]:
            by_skill[r["linked_skill"]].append(r)
        for cap in r["capabilities"]:
            if isinstance(cap, str) and cap:
                by_cap[cap].append(r)
        if r["domain"]:
            by_domain[r["domain"]].append(r)

    results: dict = {"degraded": [], "stagnant": [], "stable": [], "no_data": [], "abandon_warn": []}

    def assess(key: str, group_type: str, logs: list[dict]) -> None:
        total = len(logs)
        abandoned = sum(1 for l in logs if l["status"] == "abandoned")
        scored = [l for l in logs if l["rubric_score"] is not None]
        scores = [l["rubric_score"] for l in scored]

        # Collect recurring gaps
        gap_counts: dict[str, int] = defaultdict(int)
        for l in logs:
            for g in l["gaps"]:
                # Normalize short gap text
                normalized = g[:80].lower().strip()
                gap_counts[normalized] += 1
        recurring_gaps = [(g, c) for g, c in gap_counts.items() if c >= 2]
        recurring_gaps.sort(key=lambda x: -x[1])

        entry = {
            "key": key,
            "group_type": group_type,
            "total_sessions": total,
            "abandoned": abandoned,
            "abandon_rate": round(abandoned / total, 2) if total else 0,
            "scored_sessions": len(scores),
            "recurring_gaps": recurring_gaps[:5],
        }

        # Abandon rate warning
        if total >= min_points and abandoned / total > ABANDON_RATE_WARN:
            results["abandon_warn"].append(entry)

        if len(scores) < min_points:
            entry["reason"] = f"{len(scores)} scored sessions (need {min_points})"
            results["no_data"].append(entry)
            return

        avg = rolling_avg(scores)
        peak = max(scores)
        recent_std = stddev([float(s) for s in scores[-ROLLING_WINDOW:]])

        entry.update({
            "rolling_avg": round(avg, 1),
            "peak": peak,
            "drop_from_peak": round(peak - avg, 1),
            "recent_stddev": round(recent_std, 1),
            "last_scores": scores[-ROLLING_WINDOW:],
        })

        if avg < DEGRADATION_AVG or (peak - avg) > DEGRADATION_DROP:
            entry["signal"] = "degradation"
            results["degraded"].append(entry)
        elif recent_std < STAGNATION_STDDEV:
            entry["signal"] = "stagnation"
            results["stagnant"].append(entry)
        else:
            entry["signal"] = "stable"
            results["stable"].append(entry)

    # Assess skills
    for skill, logs in sorted(by_skill.items()):
        assess(skill, "skill", logs)

    # Assess capabilities
    for cap, logs in sorted(by_cap.items()):
        assess(cap, "capability", logs)

    # Summary stats
    results["summary"] = {
        "total_logs": len(records),
        "unique_skills": len(by_skill),
        "unique_capabilities": len(by_cap),
        "unique_domains": len(by_domain),
        "logs_with_score": sum(1 for r in records if r["rubric_score"] is not None),
        "logs_abandoned": sum(1 for r in records if r["status"] == "abandoned"),
        "domain_counts": {d: len(ls) for d, ls in sorted(by_domain.items())},
    }
    return results


# ============================================================
# OUTPUT — BRIEF
# ============================================================


def format_brief(results: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"## Skill Health Brief — {today}\n"]
    summary = results["summary"]

    lines.append(f"**{summary['total_logs']}** practice logs | "
                 f"**{summary['logs_with_score']}** scored | "
                 f"**{summary['logs_abandoned']}** abandoned | "
                 f"**{summary['unique_skills']}** skills | "
                 f"**{summary['unique_capabilities']}** capabilities\n")

    # Degradation
    if results["degraded"]:
        lines.append("### Degradation Detected\n")
        for e in results["degraded"]:
            label = f"{e['group_type']}: **{e['key']}**"
            lines.append(f"- {label} — avg {e['rolling_avg']}/100 (last {ROLLING_WINDOW}), "
                         f"down from peak {e['peak']}")
            if e["recurring_gaps"]:
                gap_str = ", ".join(f"{g} ({c}x)" for g, c in e["recurring_gaps"][:3])
                lines.append(f"  Recurring gaps: {gap_str}")
            lines.append(f"  -> Suggested: re-evaluate and revise the skill with these findings\n")

    # Stagnation
    if results["stagnant"]:
        lines.append("### Stagnation Detected\n")
        for e in results["stagnant"]:
            label = f"{e['group_type']}: **{e['key']}**"
            lines.append(f"- {label} — avg {e['rolling_avg']}/100 (last {ROLLING_WINDOW}), "
                         f"stddev {e['recent_stddev']} (flat)")
            lines.append(f"  -> Suggested: increase difficulty or change approach\n")

    # Abandon warnings
    if results["abandon_warn"]:
        lines.append("### High Abandon Rate\n")
        for e in results["abandon_warn"]:
            label = f"{e['group_type']}: **{e['key']}**"
            pct = int(e["abandon_rate"] * 100)
            lines.append(f"- {label} — {pct}% abandoned ({e['abandoned']}/{e['total_sessions']})")
            lines.append(f"  -> Investigate: task too hard, wrong scope, or wrong skill?\n")

    # Stable
    if results["stable"]:
        lines.append("### Stable Skills\n")
        for e in results["stable"]:
            label = f"{e['group_type']}: **{e['key']}**"
            lines.append(f"- {label} — avg {e['rolling_avg']}/100 (last {ROLLING_WINDOW}), steady")

    # No data
    no_data_names = [e["key"] for e in results["no_data"]]
    if no_data_names:
        lines.append(f"\n### Insufficient Data\n")
        lines.append(f"Skills/capabilities with <{3} scored sessions: {', '.join(no_data_names)}")

    # Domain breakdown
    lines.append(f"\n### Domain Distribution\n")
    for domain, count in summary["domain_counts"].items():
        lines.append(f"- {domain}: {count} sessions")

    return "\n".join(lines)


# ============================================================
# COMMANDS
# ============================================================


def cmd_scan(args: argparse.Namespace) -> None:
    records = load_logs()
    results = analyze(records, min_points=args.min)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(format_brief(results))


def cmd_brief(args: argparse.Namespace) -> None:
    records = load_logs()
    results = analyze(records, min_points=args.min)
    if args.json:
        # Brief JSON: only actionable items
        brief = {
            "degraded": results["degraded"],
            "stagnant": results["stagnant"],
            "abandon_warn": results["abandon_warn"],
            "summary": results["summary"],
        }
        print(json.dumps(brief, ensure_ascii=False, indent=2))
    else:
        print(format_brief(results))


# ============================================================
# MAIN
# ============================================================


COMMANDS = ["scan", "brief"]


def print_menu() -> None:
    print("skill_health.py — detect skill degradation from Practice Logs")
    print("\nCommands:")
    print("  scan     full analysis of all logs")
    print("  brief    compact brief with actionable signals")
    print("\nFlags: --json | --min N")
    print("\nExamples:")
    print("  python3 skill_health.py brief")
    print("  python3 skill_health.py scan --json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=COMMANDS)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--min", type=int, default=3, help="Min data points for analysis")
    args = parser.parse_args()

    if not args.command:
        print_menu()
        return

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "brief":
        cmd_brief(args)


if __name__ == "__main__":
    main()
