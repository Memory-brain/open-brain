#!/usr/bin/env python3
"""
compress_logs.py — deterministic compression of Hot Cache.md and Session Log.md.

Motivated by hard caps per observation, not per session: without them, the Hot
Cache and the Session Log grow without limit and pruning depends on remembering
to do it.

Vault rule: nothing is deleted, it is archived. This script ONLY moves content
into archive files (existing or analogous ones) — it removes nothing.

Usage:
    python3 compress_logs.py --dry-run     # report what would be archived, touch nothing
    python3 compress_logs.py --apply       # run the archiving
    python3 compress_logs.py --auto        # repack only if the always-loaded layer is over budget

Vault location: OPEN_BRAIN_VAULT (or VAULT_ROOT) when set; otherwise the parent
of this script's folder (engines installed at the vault root).

Rules:
  - Hot Cache "Recent changes" section (`## Recent changes ...`, or the legacy
    Spanish heading `## Cambios recientes ...`): dated entries (bullet
    "- **YYYY-MM-DD ...") older than 14 days move to
    `Resources/Hot Cache — Cambios Archive.md` (file name kept as is; "Cambios" =
    changes; same pattern as `Hot Cache — Threads Archive.md`). The last 2 weeks
    stay live. If the section lives in its own on-demand file
    (`Resources/Hot Cache — Cambios recientes.md`), that file is used.
  - Session Log.md: append-only by design, so it is NOT truncated aggressively by
    age — every entry from already closed calendar months (not the current month
    nor the previous one) is archived, by month, to
    `Resources/Session Logs/{YYYY-MM}.md`. The current and previous months stay live.
  - Closed threads (`[CLOSED ...]`, legacy `[CERRADO ...]`) still listed under
    "## Pending threads" (legacy `## Threads pendientes`) move to
    `Resources/Hot Cache — Threads Archive.md`.
"""

import argparse
import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path


def _vault_root() -> Path:
    for k in ("OPEN_BRAIN_VAULT", "VAULT_ROOT"):
        if os.environ.get(k):
            return Path(os.environ[k])
    return Path(__file__).resolve().parent.parent


VAULT = _vault_root()
HOT_CACHE = VAULT / "Resources" / "Hot Cache.md"
CAMBIOS_ARCHIVE = VAULT / "Resources" / "Hot Cache — Cambios Archive.md"
# "Recent changes" may live outside the always-loaded Hot Cache.md, in this
# on-demand file. When it exists, age-based archiving reads from it, not from
# Hot Cache.md. (File name kept as is.)
CAMBIOS_RECIENTES = VAULT / "Resources" / "Hot Cache — Cambios recientes.md"
SESSION_LOG = VAULT / "Resources" / "Session Log.md"
SESSION_LOGS_DIR = VAULT / "Resources" / "Session Logs"

# Section headings accepted (English first, legacy Spanish kept for old vaults).
RECENT_CHANGES_HEADINGS = ("## Recent changes", "## Cambios recientes")
PENDING_THREADS_HEADINGS = ("## Pending threads", "## Threads pendientes")

TODAY = date.today()

DATE_RE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")

WITNESS_LOG = VAULT / "Resources" / "Vault Health" / "witness-log.jsonl"


def write_witness(op, source, destination, items, bytes_before, bytes_after,
                  actor="health-engine/compress_logs.py", **extra):
    """Witness of a fold: what moved, from where, how much and when.

    The closing protocol promises that nothing is deleted and that every fold
    leaves "a dated line saying what moved and where it came from". The
    `## Archived <date>` header this script writes says WHEN, not HOW MUCH nor
    FROM WHERE: on its own it cannot reconstruct whether a fold lost something.
    This line can. It is read by `check_38` in health_check.py, which reports every
    fold event without a witness.

    Append-only and fail-safe: a witness that cannot be written does not abort
    the archiving (the content is already moved and losing the witness is worse
    than not having it), but it leaves a trace on stdout."""
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "op": op,
             "source": source, "destination": destination, "items": items,
             "bytes_before": bytes_before, "bytes_after": bytes_after,
             "actor": actor}
    entry.update({k: v for k, v in extra.items() if v is not None})
    try:
        WITNESS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with WITNESS_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"  WARNING: could not write the witness ({exc.__class__.__name__}): {entry}")


def days_since(d: date) -> int:
    return (TODAY - d).days


def parse_date(s: str):
    m = DATE_RE.search(s)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def split_cambios_section(text: str):
    lines = text.split("\n")
    start = None
    end = None
    for i, line in enumerate(lines):
        if line.startswith(RECENT_CHANGES_HEADINGS):
            start = i
        elif start is not None and end is None and line.startswith("## ") and i > start:
            end = i
            break
    if start is None:
        return None
    if end is None:
        end = len(lines)
    header_line = lines[start]
    body_lines = lines[start + 1:end]
    entries = []
    current = []
    for line in body_lines:
        if line.startswith("- **20") or line.startswith("- 20"):
            if current:
                entries.append("\n".join(current).strip("\n"))
            current = [line]
        else:
            current.append(line)
    if current:
        entries.append("\n".join(current).strip("\n"))
    before = "\n".join(lines[:start])
    after = "\n".join(lines[end:])
    return before, header_line, entries, after


def compress_hot_cache(apply: bool, keep_days: int = 14):
    source = CAMBIOS_RECIENTES if CAMBIOS_RECIENTES.exists() else HOT_CACHE
    if not source.exists():
        print(f"{source.relative_to(VAULT)} not found — nothing to do.")
        return
    text = source.read_text(encoding="utf-8")
    parsed = split_cambios_section(text)
    if not parsed:
        print(f"{source.name}: no '## Recent changes' section found — touching nothing.")
        return
    before, header_line, entries, after = parsed

    keep, archive = [], []
    for entry in entries:
        d = parse_date(entry)
        if d is None:
            keep.append(entry)
            continue
        if days_since(d) > keep_days:
            archive.append((d, entry))
        else:
            keep.append(entry)

    print(f"{source.name} — Recent changes: {len(entries)} entries in total, "
          f"{len(keep)} stay (<= {keep_days}d), {len(archive)} get archived (> {keep_days}d).")

    if not archive:
        print("Nothing to archive.")
        return

    if not apply:
        for d, entry in archive:
            first_line = entry.split("\n")[0][:120]
            print(f"  [dry-run] would archive ({d}): {first_line}...")
        return

    archive.sort(key=lambda x: x[0])
    if CAMBIOS_ARCHIVE.exists():
        archive_text = CAMBIOS_ARCHIVE.read_text(encoding="utf-8")
    else:
        archive_text = (
            "---\n"
            "type: resource\n"
            "purpose: \"'Recent changes' entries from the Hot Cache archived by age "
            "(>14 days). Not deleted — taken out of every session's reading because "
            "they are no longer 'last week'. Generated by "
            "health-engine/compress_logs.py.\"\n"
            f"created: {TODAY.isoformat()}\n"
            "---\n\n"
            "# Hot Cache — Changes Archive\n"
        )
    stamp = f"\n\n## Archived {TODAY.isoformat()}\n\n"
    body = "\n\n".join(entry for _, entry in archive)
    archive_text = archive_text.rstrip("\n") + stamp + body + "\n"
    CAMBIOS_ARCHIVE.write_text(archive_text, encoding="utf-8")

    new_body = header_line + "\n\n" + "\n\n".join(keep) + "\n\n"
    new_text = before + ("\n" if before else "") + new_body + after
    new_text = re.sub(r"\n{4,}", "\n\n\n", new_text)
    source.write_text(new_text, encoding="utf-8")
    write_witness("fold-hot-cache",
                  str(source.relative_to(VAULT)),
                  str(CAMBIOS_ARCHIVE.relative_to(VAULT)),
                  len(archive), len(text), len(new_text))
    print(f"Archived {len(archive)} entries → {CAMBIOS_ARCHIVE}")
    print(f"{source.name} rewritten ({len(text)} → {len(new_text)} characters).")


SESSION_HEADER_RE = re.compile(r"^## (20\d{2}-\d{2}-\d{2})")


def split_session_log(text: str):
    lines = text.split("\n")
    first_entry_idx = None
    for i, line in enumerate(lines):
        if SESSION_HEADER_RE.match(line):
            first_entry_idx = i
            break
    if first_entry_idx is None:
        return None
    preamble = "\n".join(lines[:first_entry_idx])
    body_lines = lines[first_entry_idx:]
    entries = []
    current = []
    for line in body_lines:
        if SESSION_HEADER_RE.match(line):
            if current:
                entries.append("\n".join(current).rstrip("\n"))
            current = [line]
        else:
            current.append(line)
    if current:
        entries.append("\n".join(current).rstrip("\n"))
    return preamble, entries


def compress_session_log(apply: bool):
    if not SESSION_LOG.exists():
        print(f"{SESSION_LOG.relative_to(VAULT)} not found — nothing to do.")
        return
    text = SESSION_LOG.read_text(encoding="utf-8")
    parsed = split_session_log(text)
    if not parsed:
        print("Session Log: no entries in '## YYYY-MM-DD' format found — touching nothing.")
        return
    preamble, entries = parsed

    current_month = (TODAY.year, TODAY.month)
    prev_month_date = date(TODAY.year - 1, 12, 1) if TODAY.month == 1 else date(TODAY.year, TODAY.month - 1, 1)
    prev_month = (prev_month_date.year, prev_month_date.month)

    keep = []
    by_month = {}
    for entry in entries:
        m = SESSION_HEADER_RE.match(entry.split("\n")[0])
        d = parse_date(m.group(1)) if m else None
        if d is None:
            keep.append(entry)
            continue
        key = (d.year, d.month)
        if key == current_month or key == prev_month:
            keep.append(entry)
        else:
            by_month.setdefault(key, []).append(entry)

    total_archived = sum(len(v) for v in by_month.values())
    print(f"Session Log: {len(entries)} entries in total, {len(keep)} stay "
          f"(current + previous month), {total_archived} get archived by closed month.")

    if not by_month:
        print("Nothing to archive.")
        return

    if not apply:
        for (y, mo), ents in sorted(by_month.items()):
            print(f"  [dry-run] would archive {len(ents)} entries from {y}-{mo:02d} -> "
                  f"Resources/Session Logs/{y}-{mo:02d}.md")
        return

    SESSION_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    for (y, mo), ents in sorted(by_month.items()):
        out_path = SESSION_LOGS_DIR / f"{y}-{mo:02d}.md"
        if out_path.exists():
            existing = out_path.read_text(encoding="utf-8")
        else:
            existing = (
                "---\n"
                "type: resource\n"
                f"purpose: \"Entries of Resources/Session Log.md for {y}-{mo:02d}, "
                "archived at month close. Not deleted. Generated by "
                "health-engine/compress_logs.py.\"\n"
                f"created: {TODAY.isoformat()}\n"
                "---\n\n"
                f"# Session Log — {y}-{mo:02d}\n"
            )
        existing = existing.rstrip("\n") + "\n\n" + "\n\n---\n\n".join(ents) + "\n"
        out_path.write_text(existing, encoding="utf-8")
        write_witness("fold-session-log",
                      str(SESSION_LOG.relative_to(VAULT)),
                      str(out_path.relative_to(VAULT)),
                      len(ents), None, len(existing))
        print(f"  Archived {len(ents)} entries from {y}-{mo:02d} -> {out_path}")

    new_text = preamble.rstrip("\n") + "\n\n" + "\n\n---\n\n".join(keep) + "\n"
    SESSION_LOG.write_text(new_text, encoding="utf-8")
    print(f"Session Log.md rewritten ({len(text)} -> {len(new_text)} characters).")


# Always-loaded layer: the files in OPEN_BRAIN_ALWAYS_SURFACES (','-separated,
# relative to the vault; default CLAUDE.md, same setting as health check 40) plus
# the Hot Cache this script compresses.
ALWAYS_FILES = [VAULT / x.strip() for x in
                os.environ.get("OPEN_BRAIN_ALWAYS_SURFACES", "CLAUDE.md").split(",")
                if x.strip()]
if HOT_CACHE not in ALWAYS_FILES:
    ALWAYS_FILES.append(HOT_CACHE)
THREADS_ARCHIVE = VAULT / "Resources" / "Hot Cache — Threads Archive.md"
# Automatic repack threshold. Without periodic repacks the compression savings
# collapse: the always-loaded layer creeps back up within days. --auto removes the
# dependence on remembering: it only runs if the layer is over this threshold.
AUTO_THRESHOLD_TOKENS = 8000


def always_tokens():
    return sum(f.stat().st_size for f in ALWAYS_FILES if f.exists()) // 4


def fold_closed_threads(apply: bool):
    """Moves to the Threads Archive the threads marked [CLOSED ...] (legacy
    [CERRADO ...]) that are still under "## Pending threads". A closed thread is
    not pending: its place is the archive. Moves the text unedited and leaves a
    witness."""
    if not HOT_CACHE.exists():
        print(f"{HOT_CACHE.relative_to(VAULT)} not found — nothing to do.")
        return 0
    text = HOT_CACHE.read_text(encoding="utf-8")
    lines = text.split("\n")
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith(PENDING_THREADS_HEADINGS))
    except StopIteration:
        print("Hot Cache: no '## Pending threads' section.")
        return 0
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    body = "\n".join(lines[start + 1:end])
    blocks = re.split(r"\n\s*\n", body)
    closed = [b for b in blocks if re.match(r"^\s*\d?[a-z0-9]{1,4}\.\s+\*\*\[(?:CLOSED|CERRADO)", b)]
    print(f"Closed threads in the always layer: {len(closed)}")
    if not closed or not apply:
        return len(closed)
    keep = [b for b in blocks if b not in closed]
    new_text = "\n".join(lines[:start + 1]) + "\n" + "\n\n".join(keep).rstrip("\n") + "\n\n" + "\n".join(lines[end:])
    if THREADS_ARCHIVE.exists():
        arch = THREADS_ARCHIVE.read_text(encoding="utf-8")
    else:
        arch = ("---\ntype: resource\npurpose: \"Closed Hot Cache threads, folded out of the "
                "always-loaded layer. Not deleted. Generated by "
                "health-engine/compress_logs.py.\"\n"
                f"created: {TODAY.isoformat()}\n---\n\n# Hot Cache — Threads Archive\n")
    arch = arch.rstrip("\n") + f"\n\n## Folded {TODAY.isoformat()} — closed threads (compress_logs.py --auto)\n\n" + "\n\n".join(b.strip() for b in closed) + "\n"
    THREADS_ARCHIVE.write_text(arch, encoding="utf-8")
    HOT_CACHE.write_text(new_text, encoding="utf-8")
    write_witness("fold-closed-threads", str(HOT_CACHE.relative_to(VAULT)),
                  str(THREADS_ARCHIVE.relative_to(VAULT)), len(closed), len(text), len(new_text))
    return len(closed)


def verify_fold(backup, destinations, op, source, event_date, apply):
    """Witnesses a fold ALREADY done by checking against its backup that every
    sentence of what was there before still exists in some destination. It does
    not invent a witness: what it writes is the result of a check (method,
    sentences, missing). If something is missing, it writes no witness and lists
    what is absent."""
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    cur = norm(" ".join(Path(d).read_text(encoding="utf-8") for d in destinations if Path(d).exists()))
    raw = Path(backup).read_text(encoding="utf-8")
    raw = re.sub(r"\A---\n.*?\n---\n", "", raw, flags=re.S)  # frontmatter: metadata, not content
    sents = []
    for line in raw.splitlines():
        line = line.strip()
        # headings and separators are structure: a fold changes them by design
        if not line or line.startswith("#") or line == "---":
            continue
        line = re.sub(r"^(?:>\s*|[-*]\s+|\d?[a-z0-9]{1,4}\.\s+(?=\*\*))", "", line)
        sents += [norm(s) for s in re.split(r"(?<=[\.\)])\s+", line) if len(s) > 25]
    missing = [s for s in sents if s not in cur]
    print(f"verify-fold: {len(sents)} sentences in the backup, {len(missing)} missing from the destinations")
    for m in missing[:10]:
        print("   ·", m[:200])
    if missing:
        print("No witness written: the fold cannot be shown to be lossless.")
        return 1
    if apply:
        write_witness(op, source, str(Path(destinations[0]).resolve().relative_to(VAULT.resolve())),
                      None, Path(backup).stat().st_size, None,
                      actor="health-engine/compress_logs.py --verify-fold",
                      event_date=event_date, verified=True, method="sentence-coverage",
                      sentences=len(sents), missing=0,
                      backup=str(Path(backup).resolve().relative_to(VAULT.resolve())))
        print("Verified witness written.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Archive (never delete) old Hot Cache and Session Log entries.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="report what would be archived")
    g.add_argument("--apply", action="store_true", help="run the archiving")
    g.add_argument("--auto", action="store_true",
                   help="repack only if the always layer exceeds the threshold (for session close)")
    g.add_argument("--witness", action="store_true",
                   help="record the witness of a fold done by hand")
    g.add_argument("--verify-fold", metavar="BACKUP",
                   help="witness a fold already done by checking it against its backup")
    ap.add_argument("--op"); ap.add_argument("--source"); ap.add_argument("--destination", action="append")
    ap.add_argument("--items", type=int); ap.add_argument("--bytes-before", type=int)
    ap.add_argument("--bytes-after", type=int); ap.add_argument("--event-date")
    ap.add_argument("--threshold", type=int, default=AUTO_THRESHOLD_TOKENS)
    args = ap.parse_args()
    if not VAULT.is_dir():
        raise SystemExit(f"ERROR: vault directory not found: {VAULT}. Set OPEN_BRAIN_VAULT.")
    if args.witness:
        if not (args.op and args.source and args.destination):
            ap.error("--witness requires --op, --source and --destination")
        write_witness(args.op, args.source, args.destination[0], args.items,
                      args.bytes_before, args.bytes_after, actor="manual (session)",
                      event_date=args.event_date)
        print("Witness written.")
        return
    if args.verify_fold:
        if not args.destination:
            ap.error("--verify-fold requires at least one --destination")
        raise SystemExit(verify_fold(args.verify_fold, args.destination, args.op or "fold-verified",
                                     args.source or "Resources/Hot Cache.md",
                                     args.event_date, True))
    if args.auto:
        before = always_tokens()
        print(f"Always layer: {before} tokens (threshold {args.threshold}).")
        if before <= args.threshold:
            print("Below the threshold: nothing is folded.")
            return
        compress_hot_cache(True)
        fold_closed_threads(True)
        compress_session_log(True)
        after = always_tokens()
        print(f"Always layer: {before} -> {after} tokens.")
        if after > args.threshold:
            print("WARNING: still above the threshold after the mechanical repack. What "
                  "remains is judgment (which open threads go out): the vault owner's "
                  "decision, not the script's.")
        return
    apply = args.apply
    print("=== Hot Cache ===")
    compress_hot_cache(apply)
    print("\n=== Closed threads ===")
    fold_closed_threads(apply)
    print("\n=== Session Log ===")
    compress_session_log(apply)


def analyze():
    """Pure analysis (writes nothing), consumed by health_check.py check_33."""
    result = {
        "hot_cache_bytes": HOT_CACHE.stat().st_size if HOT_CACHE.exists() else None,
        "session_log_bytes": SESSION_LOG.stat().st_size if SESSION_LOG.exists() else None,
        "hot_cache_archivable": 0,
        "session_log_archivable": 0,
    }
    if HOT_CACHE.exists():
        parsed = split_cambios_section(HOT_CACHE.read_text(encoding="utf-8"))
        if parsed:
            _, _, entries, _ = parsed
            for entry in entries:
                d = parse_date(entry)
                if d is not None and days_since(d) > 14:
                    result["hot_cache_archivable"] += 1
    if SESSION_LOG.exists():
        parsed = split_session_log(SESSION_LOG.read_text(encoding="utf-8"))
        if parsed:
            _, entries = parsed
            current_month = (TODAY.year, TODAY.month)
            prev_month_date = date(TODAY.year - 1, 12, 1) if TODAY.month == 1 else date(TODAY.year, TODAY.month - 1, 1)
            prev_month = (prev_month_date.year, prev_month_date.month)
            for entry in entries:
                m = SESSION_HEADER_RE.match(entry.split("\n")[0])
                d = parse_date(m.group(1)) if m else None
                if d is not None and (d.year, d.month) not in (current_month, prev_month):
                    result["session_log_archivable"] += 1
    return result


if __name__ == "__main__":
    main()
