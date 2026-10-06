"""
update_graph.py — Update graph.jsonl for ONE specific note.

Lightweight hook for open-brain-promote / open-brain-extract (and manual use).
Instead of regenerating the whole graph (seconds on a vault of thousands of
notes), it processes only the given note and MERGES its edges into the
existing graph.

Stale reconciliation:
  - Edges the note had and still has → kept (with their myelination weight).
  - New edges in the note → added with weight 1.0 / traversals 0.
  - Edges the note had and no longer has → removed.

Idempotent: if the note did not change, the graph does not change (nor its myelination).
Fails quietly if autolink/ or entities.json do not exist.

Usage:
  python3 autolink/update_graph.py "Literature Notes/My LN.md"
  python3 autolink/update_graph.py /absolute/path/to/My PN.md

  # Quiet mode (to call from a skill):
  python3 autolink/update_graph.py "path" --quiet

Exit codes:
  0  all OK (with or without changes)
  1  recoverable error (note does not exist)
  2  hard error (no entities.json — run indexer.py first)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Reuse all of autolink.py's logic instead of duplicating it.
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from autolink import (  # noqa: E402
    ENTITIES_F,
    GRAPH_F,
    VAULT,
    extract_edges,
    slugify,
)


def load_entities() -> dict:
    """Load entities.json. SystemExit if missing (run indexer.py first)."""
    if not ENTITIES_F.exists():
        raise SystemExit(f"entities.json not found at {ENTITIES_F} — run indexer.py first")
    return json.loads(ENTITIES_F.read_text(encoding="utf-8"))


def load_graph() -> list[dict]:
    """Read graph.jsonl as a list of edges. Empty if it does not exist."""
    if not GRAPH_F.exists():
        return []
    edges: list[dict] = []
    with GRAPH_F.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                edges.append(json.loads(line))
    return edges


def write_graph(edges: list[dict]) -> None:
    """Rewrite graph.jsonl. Atomic via a temp file when the filesystem allows it."""
    payload = "\n".join(json.dumps(e, ensure_ascii=False) for e in edges) + "\n"
    tmp = GRAPH_F.with_suffix(".jsonl.tmp")
    try:
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(GRAPH_F)
    except OSError:
        # Some mounts (e.g. synced folders) do not allow rename/unlink.
        GRAPH_F.write_text(payload, encoding="utf-8")


def edge_key(edge: dict) -> tuple[str, str, str]:
    """Edge identity: (from, to, type). Same triple = same edge."""
    return (edge["from"], edge["to"], edge["type"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("note_path", help="Note path (relative to the vault, or absolute).")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    log = (lambda *a, **kw: None) if args.quiet else print

    # 1. Load the index (needed to resolve wikilinks)
    try:
        entities = load_entities()
    except SystemExit as e:
        print(f"[update_graph] error: {e}", file=sys.stderr)
        return 2

    # 2. Resolve the note path
    path = Path(args.note_path)
    if not path.is_absolute():
        path = VAULT / args.note_path

    if not path.exists():
        print(f"[update_graph] note not found: {path}", file=sys.stderr)
        return 1

    # The graph is keyed by slug, not title: extract_edges emits
    # from = slugify(path.stem). The same key must be used here or the
    # reconciliation never finds the note's previous edges.
    source_slug = slugify(path.stem)

    # 3. Detect the note's current relations (reusing autolink).
    #    extract_edges already filters self-links and broken links, and returns
    #    edges in the graph's canonical shape (from/from_title/to/to_title/type/
    #    weight/traversals).
    new_edges = extract_edges(path, entities)
    new_keys = {edge_key(e) for e in new_edges}

    # 4. Load the existing graph
    existing = load_graph()
    # `co_usada` edges (co_usage.py) are not produced by extract_edges: if they
    # were treated as "this note's" edges they would show up as removed and be
    # lost in the merge. They are preserved as if they belonged to another note.
    _CU = "co_usada"
    existing_for_this_note = [e for e in existing
                              if e["from"] == source_slug and e.get("type") != _CU]
    existing_by_key = {edge_key(e): e for e in existing_for_this_note}
    existing_keys = set(existing_by_key)
    other_notes_edges = [e for e in existing
                         if e["from"] != source_slug or e.get("type") == _CU]

    # 5. Preserve myelination: an edge that already existed keeps its weight
    #    and traversals. Without this, every incremental update would reset to
    #    1.0/0 everything myelinate.py had learned about that note.
    for edge in new_edges:
        prev = existing_by_key.get(edge_key(edge))
        if prev:
            edge["weight"] = prev.get("weight", edge.get("weight", 1.0))
            edge["traversals"] = prev.get("traversals", edge.get("traversals", 0))

    # 6. Diff
    added = new_keys - existing_keys
    removed = existing_keys - new_keys
    kept = new_keys & existing_keys

    # 7. Rebuild: other notes' edges + this note's current edges
    merged = other_notes_edges + new_edges
    if added or removed:
        write_graph(merged)

    # 8. Short report (unless --quiet)
    log(f"📊 {path.stem}")
    log(f"   previous edges: {len(existing_for_this_note)}")
    log(f"   current edges:  {len(new_edges)}")
    log(f"   ➕ added:        {len(added)}")
    log(f"   ➖ removed:      {len(removed)}")
    log(f"   = kept:         {len(kept)}")
    log(f"   graph total:    {len(merged)}")

    if not args.quiet and (added or removed):
        if added:
            log("\n   New edges:")
            for k in list(added)[:10]:
                log(f"     + [{k[2]:18s}] → {k[1][:70]}")
        if removed:
            log("\n   Removed edges (stale reconciliation):")
            for k in list(removed)[:10]:
                log(f"     - [{k[2]:18s}] → {k[1][:70]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
