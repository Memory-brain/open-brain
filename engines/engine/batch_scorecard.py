"""
batch_scorecard.py — the per-batch scorekeeper for the extraction admission gate.

WHY: the admission gate of `open-brain-extract` Step 0.4 is a *prediction*.
A prediction without a later scorekeeper is an invented rubric. This script
measures, per extraction batch and grouped by source type, four numbers — all
derivable from frontmatter that already exists, none new:

  1. hit_rate         — share of the batch's LNs with times_retrieved > 0
  2. elaboration_rate — share with a non-empty `## Your extension` (the user's judgment)
  3. activation_rate  — share cited in the output ledger
                        (Resources/Output Ledger/ledger.jsonl)
  4. commitment       — the careo's bet: resolved / pending / overdue

The historical hit rate per source TYPE is the admission prior. A type with hit
rate ~0 over 5 batches stops being admitted by default: that is the utility
function, empirical instead of invented.

VALIDITY WARNING (important, do not delete): the `times_retrieved` counter is
only trustworthy from the date your vault started recording it. Batches before
that date have a hit rate biased downwards. Pass `--trust-from YYYY-MM-DD` and
the script marks older batches `instrument: partial` — do not compare them with
later ones without saying so. Without the flag every batch is treated as `full`.

KILL CRITERION FOR THIS EVAL: if after 60 days the four numbers come out the
same across source types, the gate discriminates nothing and you are optimising
a dead metric. Check it with `--by-type`, looking at the spread.

  python3 engine/batch_scorecard.py                 # markdown table per batch
  python3 engine/batch_scorecard.py --by-type       # aggregate per source type (the prior)
  python3 engine/batch_scorecard.py --json          # raw output
  python3 engine/batch_scorecard.py --min-notes 5   # ignore tiny batches
  python3 engine/batch_scorecard.py --trust-from 2026-01-01  # mark older batches partial

Vault root: OPEN_BRAIN_VAULT if set, otherwise the parent of this script's folder.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
from collections import defaultdict
from pathlib import Path

VAULT = Path(os.environ["OPEN_BRAIN_VAULT"]) if os.environ.get("OPEN_BRAIN_VAULT") \
    else Path(__file__).resolve().parent.parent
# Date from which `times_retrieved` is trustworthy in your vault. None = all batches
# are treated as fully instrumented. Set with --trust-from.
INSTRUMENT_TRUSTWORTHY_FROM: datetime.date | None = None
BET_TTL_DAYS = 7  # the careo asks for the bet "within 7 days"
NO_PREFIX = "(no prefix)"


def frontmatter(raw: str) -> str:
    m = re.match(r"---\n(.*?)\n---", raw, re.S)
    return m.group(1) if m else ""


def fm_get(fm: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}:[ \t]*(\S[^\n]*)$", fm, re.M)
    return m.group(1).strip().strip("'\"") if m else None


def batch_of(name: str) -> str:
    return name.split(" - ")[0] if " - " in name else NO_PREFIX


def extension_filled(raw: str) -> bool:
    # "## Your extension"; legacy "## Tu extensión" accepted
    m = re.search(r"##\s*(?:Your extension|Tu extensi[oó]n)\s*\n(.*)$", raw, re.S | re.I)
    if not m:
        return False
    body = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S).strip()
    return len(body) > 0


def load_ledger_notes() -> set[str]:
    lp = VAULT / "Resources" / "Output Ledger" / "ledger.jsonl"
    cited: set[str] = set()
    if not lp.exists():
        return cited
    for line in lp.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        for sn in row.get("source_notes") or []:
            n = sn.get("note") if isinstance(sn, dict) else sn
            if n:
                cited.add(str(n).strip())
    return cited


# The type vocabulary is spread over several fields and three folders — normalising it
# here is what makes the prior comparable. Without this, most batches came out
# "(no dossier)" and the per-type aggregate meant nothing.
TYPE_FIELDS = ("dossier_type", "source_type", "kind", "format", "medium")
TYPE_CANON = {
    "paper": "paper", "arxiv-paper": "paper", "academic-paper": "paper",
    "article": "article", "longform-article": "article", "article-series": "article",
    "essay": "article", "report": "article", "deep-research": "article",
    "blog-post": "article", "post": "article",
    "book": "book",
    "github-repo": "repo", "github-repo-corpus": "repo", "repository": "repo",
    "repo": "repo", "tool": "repo",
    "tweet": "transcript", "twitter-thread": "transcript", "video": "transcript",
    "podcast": "transcript", "transcript": "transcript", "course": "transcript",
    "talk": "transcript",
}


def source_types() -> dict[str, str]:
    """ln_prefix -> canonical type. Reads Dossiers/, Inbox/ and Sources/ — a source's
    record lives in any of the three depending on when it was ingested."""
    out: dict[str, str] = {}
    for folder in ("Dossiers", "Inbox", "Sources"):
        d = VAULT / folder
        if not d.is_dir():
            continue
        for p in d.rglob("*.md"):
            try:
                fm = frontmatter(p.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
            pref = fm_get(fm, "ln_prefix")
            if not pref:
                continue
            raw_type = next((fm_get(fm, k) for k in TYPE_FIELDS if fm_get(fm, k)), None)
            typ = TYPE_CANON.get((raw_type or "").lower().strip(), None)
            # Dossiers wins over Inbox: a stub does not overwrite an existing canonical type.
            if typ or pref not in out:
                out[pref] = typ or (raw_type or "(no type)")
    return out


def careo_bets() -> dict[str, dict]:
    """prefix -> state of the P3 bet, derived from Fleeting Notes/Careo — *.md."""
    out: dict[str, dict] = {}
    d = VAULT / "Fleeting Notes"
    if not d.is_dir():
        return out
    today = datetime.date.today()
    for p in sorted(d.glob("Careo — *.md")):
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = frontmatter(raw)
        prefs = {batch_of(m) for m in re.findall(r"\[\[([^\]|]+)\]\]", fm)}
        prefs = {x for x in prefs if x and x != NO_PREFIX and len(x) <= 12}
        # "## P3 — The bet"; legacy "## P3 — La apuesta" accepted
        m = re.search(r"##\s*P3\s*—\s*(?:The bet|La apuesta)\s*\n(.*?)(?=\n##\s|\Z)", raw, re.S)
        body = m.group(1) if m else ""
        answer = re.sub(r"^>.*$", "", body, flags=re.M).strip()
        created = fm_get(fm, "created") or ""
        try:
            cdate = datetime.date.fromisoformat(created[:10])
        except ValueError:
            cdate = None
        if not m:
            state = "no_bet"
        elif answer and answer.lower() not in ("[pending]", "pending", "[pendiente]", "pendiente", "-"):
            state = "resolved"
        elif cdate and (today - cdate).days > BET_TTL_DAYS:
            state = "overdue"
        else:
            state = "pending"
        for pref in prefs:
            out[pref] = {"state": state, "careo": p.name, "created": created}
    return out


def collect(min_notes: int) -> list[dict]:
    cited = load_ledger_notes()
    types, bets = source_types(), careo_bets()
    batches: dict[str, list[dict]] = defaultdict(list)

    for p in (VAULT / "Literature Notes").rglob("*.md"):
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = frontmatter(raw)
        if not fm:
            continue
        tr = re.search(r"^times_retrieved:[ \t]*(\d+)", fm, re.M)
        batches[batch_of(p.name)].append({
            "stem": p.stem,
            "retrieved": bool(tr and int(tr.group(1)) > 0),
            "extended": extension_filled(raw),
            "activated": p.stem in cited,
            "created": fm_get(fm, "created") or "",
        })

    rows = []
    for pref, notes in batches.items():
        if len(notes) < min_notes:
            continue
        dates = sorted(d for d in (n["created"][:10] for n in notes) if re.match(r"\d{4}-\d{2}-\d{2}", d))
        newest = dates[-1] if dates else ""
        instrument = "full"
        if newest and INSTRUMENT_TRUSTWORTHY_FROM is not None:
            try:
                instrument = "full" if datetime.date.fromisoformat(newest) >= INSTRUMENT_TRUSTWORTHY_FROM else "partial"
            except ValueError:
                instrument = "unknown"
        n = len(notes)
        bet = bets.get(pref, {})
        rows.append({
            "batch": pref,
            "type": types.get(pref, "(no dossier)"),
            "notes": n,
            "created": newest,
            "instrument": instrument,
            "hit_rate": round(sum(x["retrieved"] for x in notes) / n, 3),
            "elaboration_rate": round(sum(x["extended"] for x in notes) / n, 3),
            "activation_rate": round(sum(x["activated"] for x in notes) / n, 3),
            "commitment": bet.get("state", "no_careo"),
        })
    rows.sort(key=lambda r: (r["created"], r["batch"]), reverse=True)
    return rows


def _verdict(batches: int, hit: float, elaboration: float) -> str:
    """The hit rate is the prior. But a type can have hit ~0 and high elaboration —
    books often do: almost never retrieved, yet the highest share of extensions the
    user actually wrote. Retiring that type by hit rate would retire exactly the
    notes that did move their judgment. When the two numbers disagree, the verdict
    is not automatic: it is the user's."""
    if batches < 5:
        return "NO DATA — fewer than 5 batches"
    if hit >= 0.05:
        return "admitted"
    if elaboration >= 0.10:
        return "REVIEW BY HAND — hit ~0 but high elaboration: it is read, not retrieved"
    return "NO LONGER ADMITTED BY DEFAULT — hit and elaboration ~0 over 5+ batches"


def by_type(rows: list[dict]) -> list[dict]:
    """The admission prior: historical hit rate per source type."""
    agg: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        agg[r["type"]].append(r)
    out = []
    for typ, rs in agg.items():
        n = len(rs)
        trusted = [r for r in rs if r["instrument"] == "full"]
        out.append({
            "type": typ,
            "batches": n,
            "batches_trusted_instrument": len(trusted),
            "notes": sum(r["notes"] for r in rs),
            "hit_rate_mean": round(sum(r["hit_rate"] for r in rs) / n, 3),
            "hit_rate_mean_trusted": round(sum(r["hit_rate"] for r in trusted) / len(trusted), 3) if trusted else None,
            "elaboration_mean": round(sum(r["elaboration_rate"] for r in rs) / n, 3),
            "activation_mean": round(sum(r["activation_rate"] for r in rs) / n, 3),
            "verdict": _verdict(n,
                                  sum(r["hit_rate"] for r in rs) / n,
                                  sum(r["elaboration_rate"] for r in rs) / n),
        })
    out.sort(key=lambda r: -r["notes"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--by-type", action="store_true")
    ap.add_argument("--min-notes", type=int, default=3)
    ap.add_argument("--trust-from", default=None,
                    help="YYYY-MM-DD from which times_retrieved is trustworthy; "
                         "older batches are marked instrument: partial")
    a = ap.parse_args()
    global INSTRUMENT_TRUSTWORTHY_FROM
    if a.trust_from:
        INSTRUMENT_TRUSTWORTHY_FROM = datetime.date.fromisoformat(a.trust_from)

    rows = collect(a.min_notes)
    data = by_type(rows) if a.by_type else rows

    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    if a.by_type:
        print(f"\nAdmission prior per source type ({len(rows)} batches, min {a.min_notes} notes)\n")
        print("| Type | Batches | Notes | Hit rate | Hit (trusted instrument) | Elaboration | Activation | Verdict |")
        print("|---|--:|--:|--:|--:|--:|--:|---|")
        for r in data:
            hf = "n/a" if r["hit_rate_mean_trusted"] is None else f"{r['hit_rate_mean_trusted']:.0%}"
            print(f"| {r['type']} | {r['batches']} | {r['notes']} | {r['hit_rate_mean']:.0%} | {hf} "
                  f"| {r['elaboration_mean']:.0%} | {r['activation_mean']:.0%} | {r['verdict']} |")
        return

    print(f"\nPer-batch scorecard ({len(rows)} batches with >= {a.min_notes} notes)\n")
    print("| Batch | Type | Notes | Date | Instrument | Hit | Elaboration | Activation | Bet |")
    print("|---|---|--:|---|---|--:|--:|--:|---|")
    for r in rows:
        print(f"| {r['batch']} | {r['type']} | {r['notes']} | {r['created']} | {r['instrument']} "
              f"| {r['hit_rate']:.0%} | {r['elaboration_rate']:.0%} | {r['activation_rate']:.0%} | {r['commitment']} |")


if __name__ == "__main__":
    main()
