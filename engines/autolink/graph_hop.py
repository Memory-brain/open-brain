#!/usr/bin/env python3
"""
graph_hop.py — Post-grep graph expansion for vault retrieval.

Given a set of seed notes (titles or slugs from grep results), walks 1 hop
through graph.jsonl along high-signal semantic edges and returns neighbors
ranked by edge quality and myelination.

Designed to be called after the keyword (grep) phase of retrieval, before the
confrontation phase. Adds conceptual neighbors that share no
keywords with the query but ARE connected in the knowledge graph.

Usage:
    # From titles (as an agent would call it)
    python3 graph_hop.py --seeds "Note title one" "Note title two" [--max 5] [--json]

    # From slugs
    python3 graph_hop.py --slugs "note-slug-one" "note-slug-two" [--max 5] [--json]

    # Pipe seed titles from stdin (one per line)
    echo -e "Note title one\\nNote title two" | python3 graph_hop.py --stdin [--max 5] [--json]

Output (default): one neighbor per line, ranked by score
    score  edge_type  ←/→  seed_title  |  neighbor_title

Output (--json): JSON array of neighbor objects for programmatic use

Integrates with:
    - open-brain-retrieve skill (graph expansion step after keyword search)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

AUTOLINK = Path(__file__).parent
GRAPH_F = AUTOLINK / "graph.jsonl"

# ── Edge types worth traversing (high signal) ─────────────────────────────

HIGH_SIGNAL_EDGES = {
    "contradice":     2.5,
    "refuta":         2.5,
    "cross_domain":   2.0,
    "alimenta":       1.5,
    "operacionaliza": 1.5,
    "extiende":       1.2,
    "refuerza":       1.0,
    "validado_por":   0.8,
    # empirical co-usage derived from the Retrieval Log (autolink/co_usage.py).
    # Medium weight on purpose: it is usage evidence, not a semantic relation;
    # the edge's `traversals` (= sessions in which the pair was used together)
    # already rank it. Without this line most pairs you use together are
    # unreachable by a hop, because they were never linked in the notes.
    "co_usada":       1.0,
}

# Edges to SKIP — too noisy, too many
SKIP_EDGES = {"menciona", "relacionada_con", "indexa_por", "pertenece_a", "cita"}


# ── Helpers ────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def load_graph() -> list[dict]:
    if not GRAPH_F.exists():
        print(f"❌ graph.jsonl not found at {GRAPH_F}", file=sys.stderr)
        sys.exit(1)
    edges = []
    for line in GRAPH_F.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            edges.append(json.loads(line))
    return edges


def build_indices(edges: list[dict]):
    """Build slug→title map and adjacency indices."""
    slug_to_title = {}
    from_idx = defaultdict(list)  # slug → [edge]
    to_idx = defaultdict(list)    # slug → [edge]

    for e in edges:
        from_slug = e["from"]
        to_slug = e["to"]
        if "from_title" in e:
            slug_to_title[from_slug] = e["from_title"]
        if "to_title" in e:
            slug_to_title[to_slug] = e["to_title"]
        from_idx[from_slug].append(e)
        to_idx[to_slug].append(e)

    return slug_to_title, from_idx, to_idx


# ── Core: graph hop ───────────────────────────────────────────────────────

def graph_hop(
    seed_titles: list[str],
    edges: list[dict],
    max_neighbors: int = 5,
    edge_whitelist: dict[str, float] | None = None,
) -> list[dict]:
    """
    Walk 1 hop from seed notes through high-signal edges.

    Returns neighbors ranked by:
      1. Edge type weight (contradice/refuta highest)
      2. Myelination (traversals > 0 = empirically co-used)
      3. Number of distinct seeds connecting to this neighbor

    Each result: {title, slug, score, connections: [{seed, edge_type, traversals, direction}]}
    """
    if edge_whitelist is None:
        edge_whitelist = HIGH_SIGNAL_EDGES

    slug_to_title, from_idx, to_idx = build_indices(edges)

    # Resolve seed titles to slugs
    # Build reverse map: title → slug
    title_to_slug = {v: k for k, v in slug_to_title.items()}
    seed_slugs = set()
    for t in seed_titles:
        slug = title_to_slug.get(t)
        if slug:
            seed_slugs.add(slug)
        else:
            # Try slugifying the title
            slug = slugify(t)
            seed_slugs.add(slug)

    # Walk neighbors
    neighbor_data = defaultdict(lambda: {"score": 0.0, "connections": []})

    for seed_slug in seed_slugs:
        seed_title = slug_to_title.get(seed_slug, seed_slug)

        # Outgoing edges
        for e in from_idx.get(seed_slug, []):
            etype = e["type"]
            if etype not in edge_whitelist:
                continue
            neighbor_slug = e["to"]
            if neighbor_slug in seed_slugs:
                continue  # don't return seeds

            w = edge_whitelist[etype]
            trav = e.get("traversals", 0)
            myelin_bonus = min(trav * 0.3, 1.5)

            nd = neighbor_data[neighbor_slug]
            nd["score"] += w + myelin_bonus
            nd["connections"].append({
                "seed": seed_title,
                "edge_type": etype,
                "traversals": trav,
                "sessions": e.get("sessions", []),
                "direction": "→",  # seed → neighbor
            })

        # Incoming edges
        for e in to_idx.get(seed_slug, []):
            etype = e["type"]
            if etype not in edge_whitelist:
                continue
            neighbor_slug = e["from"]
            if neighbor_slug in seed_slugs:
                continue

            w = edge_whitelist[etype]
            trav = e.get("traversals", 0)
            myelin_bonus = min(trav * 0.3, 1.5)

            nd = neighbor_data[neighbor_slug]
            nd["score"] += w + myelin_bonus
            nd["connections"].append({
                "seed": seed_title,
                "edge_type": etype,
                "traversals": trav,
                "sessions": e.get("sessions", []),
                "direction": "←",  # neighbor → seed
            })

    # Build ranked results
    results = []
    for slug, data in neighbor_data.items():
        title = slug_to_title.get(slug, slug)
        # Bonus for being connected to multiple seeds (cross-pollination signal)
        distinct_seeds = len(set(c["seed"] for c in data["connections"]))
        if distinct_seeds > 1:
            data["score"] *= 1.0 + 0.3 * (distinct_seeds - 1)

        results.append({
            "title": title,
            "slug": slug,
            "score": round(data["score"], 2),
            "distinct_seeds": distinct_seeds,
            "connections": data["connections"],
        })

    results.sort(key=lambda x: -x["score"])
    return results[:max_neighbors]


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Post-grep graph expansion: find conceptual neighbors of seed notes"
    )
    parser.add_argument("--seeds", nargs="+", help="Seed note titles")
    parser.add_argument("--slugs", nargs="+", help="Seed note slugs")
    parser.add_argument("--stdin", action="store_true",
                        help="Read seed titles from stdin (one per line)")
    parser.add_argument("--max", type=int, default=5,
                        help="Max neighbors to return (default: 5)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON array")
    parser.add_argument("--edge-types", nargs="+",
                        help="Override edge types to traverse (default: high-signal set)")
    args = parser.parse_args()

    # Resolve seeds
    seed_titles = []
    if args.stdin:
        seed_titles = [line.strip() for line in sys.stdin if line.strip()]
    elif args.seeds:
        seed_titles = args.seeds
    elif args.slugs:
        # Load graph to resolve slugs to titles
        edges = load_graph()
        slug_to_title, _, _ = build_indices(edges)
        seed_titles = [slug_to_title.get(s, s) for s in args.slugs]
    else:
        parser.error("Provide --seeds, --slugs, or --stdin")

    if not seed_titles:
        parser.error("No seed notes provided")

    edges = load_graph()

    # Edge type override
    whitelist = HIGH_SIGNAL_EDGES
    if args.edge_types:
        whitelist = {t: HIGH_SIGNAL_EDGES.get(t, 1.0) for t in args.edge_types}

    results = graph_hop(seed_titles, edges, max_neighbors=args.max,
                        edge_whitelist=whitelist)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        if not results:
            print("No neighbors found via high-signal edges.")
            return

        print(f"{'Score':>6}  {'Edge Type':<16}  {'Dir':>3}  {'Seed':<40}  Neighbor")
        print("-" * 110)
        for r in results:
            # Show the strongest connection for each neighbor
            best = max(r["connections"], key=lambda c: HIGH_SIGNAL_EDGES.get(c["edge_type"], 0))
            myelin = f" (myelin={best['traversals']})" if best["traversals"] > 0 else ""
            multi = f" [{r['distinct_seeds']} seeds]" if r["distinct_seeds"] > 1 else ""
            print(f"{r['score']:>6.1f}  {best['edge_type']:<16}  {best['direction']:>3}  "
                  f"{best['seed'][:40]:<40}  {r['title'][:50]}{myelin}{multi}")

        if len(results) == args.max:
            print(f"\n(showing top {args.max} — use --max N for more)")


if __name__ == "__main__":
    main()
