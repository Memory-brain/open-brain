"""
hyperedge.py — Manage hyperedges (n-ary clusters) in the vault graph.

Hyperedges represent convergences of 3+ notes on a single thesis,
productive tensions between groups, or application bundles (Case + PNs).
They live in hyperedges.jsonl, SEPARATE from graph.jsonl (they never touch it).

Three types:
  - convergence         Several LNs/PNs point to the same insight.
  - tension_cluster     Several notes in productive tension.
  - application_bundle  A Case + the PNs it operationalizes.

Usage:
  python3 hyperedge.py add --members "slug1" "slug2" "slug3" \
      --type convergence --thesis "What they converge on" --source synthesize

  python3 hyperedge.py query                          # all
  python3 hyperedge.py query --type convergence        # by type
  python3 hyperedge.py query --member "slug1"          # containing a slug

  python3 hyperedge.py detect                          # scan graph.jsonl
  python3 hyperedge.py detect --min-shared 3           # minimum shared edges

Flags:
  --limit N    maximum results (default 20)
  --json       machine-readable output
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
HYPEREDGES_FILE = SCRIPT_DIR / "hyperedges.jsonl"
GRAPH_FILE = SCRIPT_DIR / "graph.jsonl"

VALID_TYPES = {"convergence", "tension_cluster", "application_bundle"}
VALID_SOURCES = {"synthesize", "promote", "manual"}


# ============================================================
# DATA LOADING
# ============================================================


def load_hyperedges() -> list[dict]:
    if not HYPEREDGES_FILE.exists():
        return []
    edges: list[dict] = []
    with HYPEREDGES_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                edges.append(json.loads(line))
    return edges


def load_graph_edges() -> list[dict]:
    if not GRAPH_FILE.exists():
        raise SystemExit(
            "graph.jsonl not found. Run: python3 indexer.py && python3 autolink.py --all --write-graph"
        )
    edges: list[dict] = []
    with GRAPH_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                edges.append(json.loads(line))
    return edges


def next_id(existing: list[dict]) -> str:
    nums = []
    for he in existing:
        hid = he.get("id", "")
        if hid.startswith("he_"):
            try:
                nums.append(int(hid[3:]))
            except ValueError:
                pass
    n = max(nums) + 1 if nums else 1
    return f"he_{n:03d}"


# ============================================================
# HELPERS
# ============================================================


def truncate(s: str, n: int = 70) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


# ============================================================
# COMMAND: add
# ============================================================


def cmd_add(args: argparse.Namespace) -> None:
    if len(args.members) < 3:
        sys.exit("A hyperedge requires at least 3 members.")
    if args.type not in VALID_TYPES:
        sys.exit(f"Invalid type '{args.type}'. Valid: {', '.join(sorted(VALID_TYPES))}")
    if args.source not in VALID_SOURCES:
        sys.exit(f"Invalid source '{args.source}'. Valid: {', '.join(sorted(VALID_SOURCES))}")

    existing = load_hyperedges()
    he = {
        "id": next_id(existing),
        "type": args.type,
        "members": args.members,
        "thesis": args.thesis,
        "source_skill": args.source,
        "strength": 1.0,
        "created": date.today().isoformat(),
    }

    with HYPEREDGES_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(he, ensure_ascii=False) + "\n")

    print(f"\n✅ Hyperedge {he['id']} created ({he['type']}, {len(he['members'])} members)")
    print(f"   Thesis: {he['thesis']}")
    for m in he["members"]:
        print(f"     • {truncate(m)}")


# ============================================================
# COMMAND: query
# ============================================================


def cmd_query(args: argparse.Namespace) -> None:
    hes = load_hyperedges()

    if args.type:
        hes = [h for h in hes if h["type"] == args.type]
    if args.member:
        hes = [h for h in hes if args.member in h.get("members", [])]

    print(f"\n🔗 HYPEREDGES  ({len(hes)} total)")
    print("=" * 72)

    if not hes:
        print("  (no hyperedges recorded)\n")
        if args.json:
            print(json.dumps([], indent=2))
        return

    for h in hes[: args.limit]:
        icon = {"convergence": "🎯", "tension_cluster": "⚡", "application_bundle": "📦"}.get(
            h["type"], "🔗"
        )
        print(f"\n  {icon} {h['id']}  [{h['type']}]  str={h.get('strength', 1.0):.1f}  ({h['created']})")
        print(f"     Thesis: {truncate(h['thesis'], 80)}")
        print(f"     Source: {h.get('source_skill', '?')}")
        for m in h.get("members", []):
            print(f"       • {truncate(m)}")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps(hes[: args.limit], ensure_ascii=False, indent=2))


# ============================================================
# COMMAND: detect
# ============================================================


def cmd_detect(args: argparse.Namespace) -> None:
    edges = load_graph_edges()
    fertile_types = {"alimenta", "extiende", "operacionaliza", "sintetiza_desde"}

    # Build adjacency: for each node, track which other nodes connect to/from it
    # via fertile edge types. We want groups of 3+ nodes sharing ≥2 edges
    # pointing to/from a common hub node.
    hub_inbound: dict[str, list[str]] = defaultdict(list)   # hub ← sources
    hub_outbound: dict[str, list[str]] = defaultdict(list)  # hub → targets

    for e in edges:
        if e["type"] in fertile_types:
            hub_inbound[e["to"]].append(e["from"])
            hub_outbound[e["from"]].append(e["to"])

    min_shared = args.min_shared
    candidates: list[dict] = []

    # Pattern 1: ≥3 nodes pointing TO the same hub with fertile edges
    for hub, sources in hub_inbound.items():
        if len(sources) >= 3:
            # Count how many edges each source shares with hub
            source_counts = defaultdict(int)
            for s in sources:
                source_counts[s] += 1
            qualified = [s for s, c in source_counts.items()]
            if len(qualified) >= 3:
                candidates.append({
                    "hub": hub,
                    "direction": "inbound",
                    "members": sorted(set(qualified)),
                    "edge_count": len(sources),
                })

    # Pattern 2: hub pointing OUT to ≥3 nodes with fertile edges
    for hub, targets in hub_outbound.items():
        if len(targets) >= 3:
            target_counts = defaultdict(int)
            for t in targets:
                target_counts[t] += 1
            qualified = [t for t, c in target_counts.items()]
            if len(qualified) >= 3:
                candidates.append({
                    "hub": hub,
                    "direction": "outbound",
                    "members": sorted(set(qualified)),
                    "edge_count": len(targets),
                })

    # Sort by number of members descending
    candidates.sort(key=lambda c: -len(c["members"]))

    # Filter existing hyperedges to avoid suggesting duplicates
    existing = load_hyperedges()
    existing_sets = [frozenset(h.get("members", [])) for h in existing]

    print(f"\n🔍 CLUSTER DETECTION  ({len(candidates)} candidates)")
    print("=" * 72)
    print(f"Edges scanned: {len(edges)}. Fertile types: {', '.join(sorted(fertile_types))}.")
    print(f"Minimum: 3 nodes connected to the same hub.\n")

    shown = 0
    for c in candidates:
        member_set = frozenset(c["members"] + [c["hub"]])
        already = any(member_set <= es or es <= member_set for es in existing_sets)
        tag = " (already recorded)" if already else ""

        if shown >= args.limit:
            break
        shown += 1

        direction = "→ hub" if c["direction"] == "inbound" else "hub →"
        print(f"  📊 Hub: {truncate(c['hub'], 70)}  ({direction}, {c['edge_count']} edges){tag}")
        for m in c["members"][:8]:
            print(f"       • {truncate(m)}")
        if len(c["members"]) > 8:
            print(f"       ... and {len(c['members']) - 8} more")
        print()

    if not candidates:
        print("  (no cluster detected with the current criteria)\n")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps(candidates[: args.limit], ensure_ascii=False, indent=2))


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    # --- add ---
    p_add = sub.add_parser("add", help="Add a hyperedge")
    p_add.add_argument("--members", nargs="+", required=True, help="Member slugs (minimum 3)")
    p_add.add_argument("--type", required=True, choices=sorted(VALID_TYPES), help="Cluster type")
    p_add.add_argument("--thesis", required=True, help="Short description of the convergence")
    p_add.add_argument("--source", required=True, choices=sorted(VALID_SOURCES), help="Source skill")

    # --- query ---
    p_query = sub.add_parser("query", help="Query hyperedges")
    p_query.add_argument("--type", default=None, choices=sorted(VALID_TYPES))
    p_query.add_argument("--member", default=None, help="Filter by member slug")
    p_query.add_argument("--limit", type=int, default=20)
    p_query.add_argument("--json", action="store_true")

    # --- detect ---
    p_detect = sub.add_parser("detect", help="Detect candidate clusters in graph.jsonl")
    p_detect.add_argument("--min-shared", type=int, default=2, help="Minimum shared edges (default 2)")
    p_detect.add_argument("--limit", type=int, default=20)
    p_detect.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\nCommands: add, query, detect")
        return

    if args.command == "add":
        cmd_add(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "detect":
        cmd_detect(args)


if __name__ == "__main__":
    main()
