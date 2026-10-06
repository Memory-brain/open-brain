#!/usr/bin/env python3
"""
skill_sequence_report.py — First mechanical aggregator over the skill_sequence field.

Scans Literature Notes/, Inbox/, Cases/, Design References/ looking for the
`skill_sequence` field in the YAML frontmatter (not in the body — avoids false
positives from prose containing the word "skill:"). Reports:
  1. Adoption: how many notes have skill_sequence vs the total.
  2. Observed sequences and their frequency.
  3. Cross with times_retrieved / external_outputs / internal_outputs per sequence
     — the weak signal that motivated the field ("which skill sequence produces
     notes that actually get retrieved or published"). While the field is new and
     the sample small, the cross is illustrative, not conclusive.

Usage:
    python3 engine/skill_sequence_report.py [--vault-root PATH]

--vault-root defaults to OPEN_BRAIN_VAULT (or VAULT_ROOT) when set, otherwise the
parent of this script's folder (engines installed at the vault root).

Writes nothing — it only reads and reports. Safe to run at any time.
"""
import argparse
import os
import pathlib
import sys
from collections import Counter, defaultdict

try:
    import yaml
except ImportError:
    print("Missing pyyaml: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

FOLDERS = ["Literature Notes", "Inbox", "Cases", "Design References"]


def _default_root():
    return (os.environ.get("OPEN_BRAIN_VAULT") or os.environ.get("VAULT_ROOT")
            or str(pathlib.Path(__file__).resolve().parent.parent))


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm_text = text[3:end]
    try:
        return yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return None


def analyze(root=None):
    """Programmatic version of main(): same scan, no printing, so that other
    callers (health_check.py check_35) can consume the result as structured
    data instead of parsing stdout."""
    root = pathlib.Path(root) if root is not None else pathlib.Path(".")
    total_notes = 0
    with_seq = 0
    seq_counter = Counter()
    skill_counter = Counter()
    seq_signal = defaultdict(lambda: {"notes": 0, "times_retrieved_sum": 0,
                                       "external_outputs_sum": 0, "internal_outputs_sum": 0})
    parse_errors = []

    for folder in FOLDERS:
        d = root / folder
        if not d.exists():
            continue
        for p in d.rglob("*.md"):  # rglob: Inbox/ may have an Archive/ subfolder
            total_notes += 1
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fm = parse_frontmatter(text)
            if fm is None:
                if "skill_sequence:" in text:
                    parse_errors.append(str(p))
                continue
            seq = fm.get("skill_sequence")
            if not seq or not isinstance(seq, list):
                continue
            with_seq += 1
            skills = [entry.get("skill") for entry in seq if isinstance(entry, dict) and entry.get("skill")]
            if not skills:
                continue
            seq_key = " → ".join(skills)
            seq_counter[seq_key] += 1
            for s in skills:
                skill_counter[s] += 1
            sig = seq_signal[seq_key]
            sig["notes"] += 1
            sig["times_retrieved_sum"] += int(fm.get("times_retrieved") or 0)
            sig["external_outputs_sum"] += int(fm.get("external_outputs") or 0)
            sig["internal_outputs_sum"] += int(fm.get("internal_outputs") or 0)

    pct = (100 * with_seq / total_notes) if total_notes else 0.0
    sequences = [{"sequence": seq, "notes": n} for seq, n in seq_counter.most_common()]
    skills_ranked = [{"skill": s, "notes": n} for s, n in skill_counter.most_common()]
    signal = []
    for seq, sig in sorted(seq_signal.items(), key=lambda kv: -kv[1]["notes"]):
        avg_tr = round(sig["times_retrieved_sum"] / sig["notes"], 2) if sig["notes"] else 0.0
        signal.append({"sequence": seq, "notes": sig["notes"],
                        "times_retrieved_sum": sig["times_retrieved_sum"],
                        "avg_times_retrieved": avg_tr,
                        "external_outputs_sum": sig["external_outputs_sum"],
                        "internal_outputs_sum": sig["internal_outputs_sum"]})

    return {
        "total_notes": total_notes,
        "with_seq": with_seq,
        "adoption_pct": round(pct, 1),
        "parse_errors": parse_errors,
        "sequences": sequences,
        "skills_ranked": skills_ranked,
        "signal": signal,
    }


def main():
    ap = argparse.ArgumentParser(description="skill_sequence adoption and signal report (read-only).")
    ap.add_argument("--vault-root", default=_default_root(),
                    help="vault root (default: OPEN_BRAIN_VAULT, else the parent of engine/)")
    args = ap.parse_args()

    root = pathlib.Path(args.vault_root)
    total_notes = 0
    with_seq = 0
    seq_counter = Counter()
    skill_counter = Counter()
    # per-sequence aggregate of retrieval/output signal
    seq_signal = defaultdict(lambda: {"notes": 0, "times_retrieved_sum": 0,
                                       "external_outputs_sum": 0, "internal_outputs_sum": 0})
    parse_errors = []

    for folder in FOLDERS:
        d = root / folder
        if not d.exists():
            continue
        for p in d.rglob("*.md"):  # rglob: Inbox/ may have an Archive/ subfolder
            total_notes += 1
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fm = parse_frontmatter(text)
            if fm is None:
                if "skill_sequence:" in text:
                    parse_errors.append(str(p))
                continue
            seq = fm.get("skill_sequence")
            if not seq or not isinstance(seq, list):
                continue
            with_seq += 1
            skills = [entry.get("skill") for entry in seq if isinstance(entry, dict) and entry.get("skill")]
            if not skills:
                continue
            seq_key = " → ".join(skills)
            seq_counter[seq_key] += 1
            for s in skills:
                skill_counter[s] += 1
            sig = seq_signal[seq_key]
            sig["notes"] += 1
            sig["times_retrieved_sum"] += int(fm.get("times_retrieved") or 0)
            sig["external_outputs_sum"] += int(fm.get("external_outputs") or 0)
            sig["internal_outputs_sum"] += int(fm.get("internal_outputs") or 0)

    print(f"Total notes scanned: {total_notes}")
    pct = (100 * with_seq / total_notes) if total_notes else 0.0
    print(f"With skill_sequence (valid frontmatter): {with_seq} ({pct:.1f}%)")
    if parse_errors:
        print(f"WARNING: {len(parse_errors)} notes with 'skill_sequence:' in the text but unparseable frontmatter — review:")
        for e in parse_errors[:10]:
            print(f"    {e}")

    print("\nObserved sequences (per note):")
    for seq, n in seq_counter.most_common(20):
        print(f"  {n:4}  {seq}")

    print("\nPer individual skill:")
    for s, n in skill_counter.most_common(20):
        print(f"  {n:4}  {s}")

    print("\nRetrieval/output signal per sequence (times_retrieved / external_outputs / internal_outputs, summed):")
    for seq, sig in sorted(seq_signal.items(), key=lambda kv: -kv[1]["notes"]):
        avg_tr = sig["times_retrieved_sum"] / sig["notes"] if sig["notes"] else 0
        print(f"  {seq:40}  notes={sig['notes']:4}  times_retrieved_sum={sig['times_retrieved_sum']:4} "
              f"(avg {avg_tr:.2f})  external_outputs_sum={sig['external_outputs_sum']:3}  "
              f"internal_outputs_sum={sig['internal_outputs_sum']:3}")

    print("\nNote: skill_sequence is a new field, so the sample is small and recent. "
          "The cross with retrieval/output is illustrative, not conclusive — real time has to pass "
          "for times_retrieved/outputs to accumulate on these notes before drawing conclusions.")


if __name__ == "__main__":
    main()
