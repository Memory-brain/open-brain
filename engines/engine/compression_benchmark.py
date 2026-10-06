#!/usr/bin/env python3
"""
compression_benchmark.py — Compares the size of the raw source against the total
of the Literature Notes it produced, for each source indexed in
Resources/Source Index.md that has a complete raw available (Inbox note with
raw_strategy: full and an existing raw_path).

Uses characters / 4 as a token approximation (same convention as the
session-closing protocol). Not a real tokenizer — a consistent estimate for
comparing sources with each other, not an absolute billing value.

Usage:
    python3 engine/compression_benchmark.py [--vault-root PATH] [--min-ln-count N]

--vault-root defaults to OPEN_BRAIN_VAULT (or VAULT_ROOT) when set, otherwise the
parent of this script's folder (engines installed at the vault root).

Writes nothing — it only reads and reports.
"""
import argparse
import os
import pathlib
import re
import sys

try:
    import yaml
except ImportError:
    print("Missing pyyaml: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def _default_root():
    return (os.environ.get("OPEN_BRAIN_VAULT") or os.environ.get("VAULT_ROOT")
            or str(pathlib.Path(__file__).resolve().parent.parent))


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    try:
        return yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return None


def parse_source_index(root):
    """Returns a list of dicts {source, author, type, prefix, ln_count, coverage, date}."""
    p = root / "Resources" / "Source Index.md"
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 7 or cells[0] in ("Source", "---") or cells[0].startswith("---"):
            continue
        rows.append({
            "source": cells[0], "author": cells[1], "type": cells[2],
            "prefix": cells[3], "ln_count": cells[4], "coverage": cells[5], "date": cells[6],
        })
    return rows


def find_inbox_note(root, source_title):
    """Finds the Inbox/ note whose frontmatter title (or file name) matches."""
    d = root / "Inbox"
    if not d.exists():
        return None
    # fast match by file name first
    candidate = d / f"{source_title}.md"
    if candidate.exists():
        return candidate
    for p in d.rglob("*.md"):  # rglob: Inbox/ may have an Archive/ subfolder
        text = p.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        if fm and fm.get("title") == source_title:
            return p
    return None


def ln_chars_for_prefix(root, prefix):
    total, n = 0, 0
    d = root / "Literature Notes"
    if not d.exists() or not prefix:
        return 0, 0
    seen = set()
    for pattern in (f"{prefix}-*.md", f"{prefix} -*.md"):
        for p in d.glob(pattern):
            if p in seen:
                continue
            seen.add(p)
            total += len(p.read_text(encoding="utf-8", errors="replace"))
            n += 1
    return total, n


def analyze(root=None, min_ln_count=1):
    """Programmatic version of main(): same computation, no printing, so that
    other callers (health_check.py check_34) can consume the result as
    structured data instead of parsing stdout."""
    root = pathlib.Path(root) if root is not None else pathlib.Path(".")
    rows = parse_source_index(root)
    results = []
    skipped = []
    for row in rows:
        try:
            ln_count_declared = int(row["ln_count"])
        except ValueError:
            ln_count_declared = 0
        if ln_count_declared < min_ln_count:
            continue
        inbox_path = find_inbox_note(root, row["source"])
        if inbox_path is None:
            skipped.append({"source": row["source"], "reason": "no Inbox note locatable"})
            continue
        fm = parse_frontmatter(inbox_path.read_text(encoding="utf-8", errors="replace"))
        if not fm or fm.get("raw_strategy") != "full":
            skipped.append({"source": row["source"],
                             "reason": f"raw_strategy={fm.get('raw_strategy') if fm else '?'} (not full)"})
            continue
        raw_path = fm.get("raw_path")
        if not raw_path:
            skipped.append({"source": row["source"], "reason": "raw_strategy full but no raw_path"})
            continue
        raw_file = root / raw_path
        if not raw_file.exists():
            skipped.append({"source": row["source"], "reason": f"raw_path missing file: {raw_path}"})
            continue
        raw_chars = len(raw_file.read_text(encoding="utf-8", errors="replace"))
        ln_chars, ln_n = ln_chars_for_prefix(root, row["prefix"])
        if ln_n == 0:
            skipped.append({"source": row["source"],
                             "reason": f"prefix '{row['prefix']}' found no LNs in Literature Notes/"})
            continue
        ratio = ln_chars / raw_chars if raw_chars else 0.0
        results.append({"source": row["source"], "prefix": row["prefix"], "ln_n": ln_n,
                         "raw_chars": raw_chars, "ln_chars": ln_chars, "ratio": round(ratio, 3)})
    results.sort(key=lambda r: -r["ratio"])
    avg_ratio = (sum(r["ratio"] for r in results) / len(results)) if results else None
    return {"results": results, "skipped": skipped, "avg_ratio": avg_ratio}


def main():
    ap = argparse.ArgumentParser(description="Raw source vs Literature Notes size benchmark (read-only).")
    ap.add_argument("--vault-root", default=_default_root(),
                    help="vault root (default: OPEN_BRAIN_VAULT, else the parent of engine/)")
    ap.add_argument("--min-ln-count", type=int, default=1)
    args = ap.parse_args()

    root = pathlib.Path(args.vault_root)
    rows = parse_source_index(root)
    if not rows:
        print(f"Resources/Source Index.md not found or empty under {root}.", file=sys.stderr)
        sys.exit(1)

    results = []
    skipped = []

    for row in rows:
        try:
            ln_count_declared = int(row["ln_count"])
        except ValueError:
            ln_count_declared = 0
        if ln_count_declared < args.min_ln_count:
            continue

        inbox_path = find_inbox_note(root, row["source"])
        if inbox_path is None:
            skipped.append((row["source"], "no locatable Inbox note"))
            continue

        fm = parse_frontmatter(inbox_path.read_text(encoding="utf-8", errors="replace"))
        if not fm or fm.get("raw_strategy") != "full":
            skipped.append((row["source"], f"raw_strategy={fm.get('raw_strategy') if fm else '?'} (not 'full')"))
            continue

        raw_path = fm.get("raw_path")
        if not raw_path:
            skipped.append((row["source"], "raw_strategy: full but no raw_path"))
            continue
        raw_file = root / raw_path
        if not raw_file.exists():
            skipped.append((row["source"], f"raw_path points to a missing file: {raw_path}"))
            continue

        raw_chars = len(raw_file.read_text(encoding="utf-8", errors="replace"))
        ln_chars, ln_n = ln_chars_for_prefix(root, row["prefix"])
        if ln_n == 0:
            skipped.append((row["source"], f"prefix '{row['prefix']}' found no LNs in Literature Notes/"))
            continue

        ratio = ln_chars / raw_chars if raw_chars else 0.0
        results.append({
            "source": row["source"], "prefix": row["prefix"], "ln_n": ln_n,
            "raw_chars": raw_chars, "ln_chars": ln_chars, "ratio": ratio,
        })

    if not results:
        print("No source met the requirements (raw_strategy: full + existing raw_path + locatable LNs).")
    else:
        print(f"{'Prefix':7} {'raw_tok~':>9} {'LN_n':>5} {'LN_tok~':>9} {'ratio':>7}  Source")
        for r in sorted(results, key=lambda r: -r["ratio"]):
            print(f"{r['prefix']:7} {r['raw_chars']//4:9} {r['ln_n']:5} {r['ln_chars']//4:9} "
                  f"{r['ratio']:6.2f}x  {r['source']}")
        avg = sum(r["ratio"] for r in results) / len(results)
        print(f"\nAverage ratio (LN_chars / raw_chars) over {len(results)} sources: {avg:.2f}x")
        print("ratio > 1.0 means the LNs weigh MORE than the raw source (expansion, not compression).")

    if skipped:
        print(f"\n{len(skipped)} sources skipped (no comparable complete raw):")
        for source, reason in skipped[:15]:
            print(f"  - {source}: {reason}")
        if len(skipped) > 15:
            print(f"  ... and {len(skipped) - 15} more")


if __name__ == "__main__":
    main()
