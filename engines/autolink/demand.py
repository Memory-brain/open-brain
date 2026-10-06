"""
demand.py — Concept Demand Report (deterministic, no LLM).

Scans the vault for broken wikilinks — `[[targets]]` that point to notes that
do NOT exist — and ranks them by how often they are referenced. A target that
is referenced many times but never created is a *demanded concept*: the graph
is telling you what to write next.

This signal is NOT in graph.jsonl (which only stores edges whose target exists),
so this script scans note bodies directly on the filesystem. It defines its own
vault root and ignore rules (below).

Buckets:
  - concept   clean title, no source/code markers → highest-value writing backlog
  - source    coded LN prefix (e.g. "RC - ..."), Dossiers/Sources/Inbox path,
              or "(author year)" → missing source/dossier note (run ingest/index)
  - archive   Archive/ path or "removed" → dead link, candidate for cleanup

Usage:
  python3 demand.py                     # top demanded concepts (min 3 refs)
  python3 demand.py --limit 40 --min 2  # widen the list
  python3 demand.py --all-buckets       # also show source + archive buckets
  python3 demand.py --json              # machine-readable (for health engine)

Flags:
  --limit N        max results per bucket shown (default 25)
  --min N          minimum reference count to include (default 3)
  --all-buckets    also print source + archive buckets (default: concepts only)
  --json           emit JSON instead of the human report
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# Vault root: $OPEN_BRAIN_VAULT if set, otherwise the parent of this autolink/ folder.
VAULT_INNER = Path(os.environ.get("OPEN_BRAIN_VAULT") or SCRIPT_DIR.parent)
# Folders never scanned. Add your own non-note folders here (e.g. "Attachments").
IGNORE_DIRS = {"Archive", "Templates", ".git", ".obsidian", "Attachments"}

LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
CODED_LN_RE = re.compile(r"^[A-Z]{2,5}\d* ?-")  # e.g. "RC - ...", "ABC-07 - ..."

# Template/example placeholders and schema abbreviations — never real concepts.
STOPLIST = {
    "wikilinks", "wikilink", "link", "links", "pn", "ln", "case", "x", "y", "z",
    "target", "note", "title", "concept", "tag", "slug", "...", "etc",
    "permanent note", "literature note", "search term",
}
SOURCE_MARKERS = ("book notes", "book note", "ebook", "- notes", "— notes")

# Machinery, not the knowledge tree. These items sit outside the taxonomy (the
# health checks exclude them too); without this list the top of the report gets
# polluted with template placeholders such as [[Term 1]] / [[Term 2]] or
# Resources/Images/Source/filename.png that no real note contains.
#
# Mind the scope: these directories are excluded as link EMITTERS (their bodies
# are not scanned), but they still count as EXISTING notes in the resolution
# index — otherwise every legitimate link into Meta/ or Templates/ would be
# counted as broken.
#
# Add your own machinery folders (skill sources, generated reports…) here.
NON_TAXONOMY_DIRS = {
    "Templates", "Meta", "Skills",
    # Open Brain engine folders installed at the vault root
    "autolink", "engine", "vault-scan", "retrieval-eval",
}
NON_TAXONOMY_SUFFIXES = ("-engine",)
NON_TAXONOMY_PREFIXES = (
    "Resources/Vault Health",
)


def is_taxonomy(p: Path) -> bool:
    """True if the note belongs to the knowledge tree (may emit demand)."""
    try:
        rel = p.relative_to(VAULT_INNER).as_posix()
    except ValueError:
        return True
    if rel.startswith(NON_TAXONOMY_PREFIXES):
        return False
    for part in p.parts:
        if part in NON_TAXONOMY_DIRS or part.endswith(NON_TAXONOMY_SUFFIXES):
            return False
    return True


def iter_notes() -> list[Path]:
    notes: list[Path] = []
    if not VAULT_INNER.exists():
        raise SystemExit(f"Vault not found at {VAULT_INNER} (set OPEN_BRAIN_VAULT)")
    for md in VAULT_INNER.rglob("*.md"):
        if set(md.parts) & IGNORE_DIRS:
            continue
        notes.append(md)
    return notes


def build_index(notes: list[Path]) -> tuple[set[str], set[str]]:
    """Existing-note resolution sets: basename stems + relative paths (no ext)."""
    stems: set[str] = set()
    relpaths: set[str] = set()
    for p in notes:
        stems.add(p.stem)
        try:
            relpaths.add(str(p.relative_to(VAULT_INNER).with_suffix("")))
        except ValueError:
            pass
    return stems, relpaths


def resolves(target: str, stems: set[str], relpaths: set[str]) -> bool:
    base = target.split("/")[-1]
    return base in stems or target in relpaths


def classify(target: str) -> str:
    low = target.lower().strip()
    if low in STOPLIST:
        return "noise"
    if target.startswith("Archive/") or "removed" in low:
        return "archive"
    last = target.split("/")[-1]
    if (
        "/" in target
        or last.endswith(".md")                 # filename refs (README.md, AGENTS.md)
        or CODED_LN_RE.match(last)
        or "(" in target
        or any(mk in low for mk in SOURCE_MARKERS)
        or target.startswith(("Dossiers", "Sources", "Inbox"))
    ):
        return "source"
    return "concept"


def scan() -> dict[str, Counter]:
    notes = iter_notes()
    stems, relpaths = build_index(notes)
    buckets: dict[str, Counter] = {
        "concept": Counter(), "source": Counter(), "archive": Counter(), "noise": Counter(),
    }
    total = 0
    broken = 0
    scanned = 0
    for p in notes:
        if not is_taxonomy(p):
            continue
        scanned += 1
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in LINK_RE.findall(text):
            tgt = m.split("|")[0].split("#")[0].strip()
            if not tgt:
                continue
            total += 1
            if resolves(tgt, stems, relpaths):
                continue
            broken += 1
            buckets[classify(tgt)][tgt] += 1
    buckets["_meta"] = Counter(total=total, broken=broken, notes=scanned,
                               notes_indexed=len(notes))  # type: ignore
    return buckets


def to_payload(buckets: dict[str, Counter], limit: int, minref: int) -> dict:
    meta = buckets["_meta"]
    out = {
        "total_links": meta["total"],
        "broken_links": meta["broken"],
        "broken_pct": round(100 * meta["broken"] / meta["total"], 1) if meta["total"] else 0.0,
        "notes_scanned": meta["notes"],
        "counts": {b: sum(c.values()) for b, c in buckets.items() if b != "_meta"},
        "demanded": {},
    }
    for b in ("concept", "source", "archive"):
        out["demanded"][b] = [
            {"target": t, "refs": n}
            for t, n in buckets[b].most_common()
            if n >= minref
        ][:limit]
    return out


def print_report(payload: dict, all_buckets: bool) -> None:
    print("\n📝 CONCEPT DEMAND REPORT")
    print("=" * 72)
    print(
        f"  {payload['notes_scanned']} notes | {payload['total_links']} wikilinks | "
        f"{payload['broken_links']} broken ({payload['broken_pct']}%)"
    )
    c = payload["counts"]
    print(
        f"  Broken by bucket: concept={c.get('concept',0)} "
        f"source={c.get('source',0)} archive={c.get('archive',0)}"
    )

    concepts = payload["demanded"]["concept"]
    print(f"\n  🎯 DEMANDED CONCEPTS — referenced but never created (write these next):")
    if not concepts:
        print("     (none above threshold)")
    for item in concepts:
        print(f"     {item['refs']:4d}x  [[{item['target']}]]")

    if all_buckets:
        for label, key in (("📚 MISSING SOURCES / DOSSIERS", "source"),
                            ("🗑️  DEAD / ARCHIVED LINKS", "archive")):
            rows = payload["demanded"][key]
            print(f"\n  {label}:")
            if not rows:
                print("     (none above threshold)")
            for item in rows:
                print(f"     {item['refs']:4d}x  [[{item['target']}]]")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--min", dest="minref", type=int, default=3)
    ap.add_argument("--all-buckets", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    payload = to_payload(scan(), args.limit, args.minref)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_report(payload, args.all_buckets)


if __name__ == "__main__":
    main()
