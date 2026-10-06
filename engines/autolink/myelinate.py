"""
myelinate.py — Myelination engine for the vault graph.

Inspired by neuron (Z-Sigma): edges traversed during retrieval get
reinforced; unused edges decay. The result: frequently-used knowledge
paths become stronger over time.

THREE OPERATIONS:
  1. record   — Log a traversal event (called by open-brain-retrieve).
  2. apply    — Read traversals.jsonl, update weights in graph.jsonl.
  3. report   — Show the strongest/weakest edges and decay candidates.

DATA MODEL:
  - traversals.jsonl: append-only log of edge traversals.
    {"from": "slug", "to": "slug", "timestamp": "ISO", "query": "...", "intent": "operative"}
  - graph.jsonl gets TWO new optional fields per edge:
    {"from": ..., "to": ..., "type": ..., "layer": ..., "weight": 1.0, "traversals": 0}

MYELINATION RULES:
  - Each traversal: weight *= REINFORCE_FACTOR (1.10, cap WEIGHT_CAP 2.0)
  - Each apply cycle: only edges ever traversed (traversals > 0) decay by
    DECAY_FACTOR (0.98, floor 0.1). Edges never traversed keep their base
    weight.
  - Edges with weight <= PRUNE_THRESHOLD (0.3) get flagged as decay candidates.
  - Edges with weight >= STRONG_THRESHOLD (1.25) are "myelinated" — prioritized in queries.

Usage:
  python3 myelinate.py record --from "PN-slug" --to "PN-slug" --query "what do I know about X" --intent operative
  python3 myelinate.py apply                  # update graph weights
  python3 myelinate.py apply --no-decay       # reinforce only, no decay
  python3 myelinate.py apply --decay-all      # decay every edge, including never-traversed ones (legacy behaviour)
  python3 myelinate.py recompute --from-factor 1.05 [--apply]  # re-derive weights after changing REINFORCE_FACTOR
  python3 myelinate.py report                 # show weight distribution
  python3 myelinate.py report --strongest 20  # top 20 myelinated edges
  python3 myelinate.py report --weakest 20    # bottom 20 decaying edges
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Reuse the exact slug format graph.jsonl keys use (autolink.py lives in
# the same directory). Falls back to a local copy if the import path ever
# breaks, so record/apply never silently write mismatched keys again.
sys.path.insert(0, str(Path(__file__).parent))
try:
    from autolink import slugify
except ImportError:
    import re
    import unicodedata

    def slugify(text: str) -> str:
        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_-]+", "-", text)
        return text.strip("-")

SCRIPT_DIR = Path(__file__).parent
GRAPH_FILE = SCRIPT_DIR / "graph.jsonl"
TRAVERSALS_FILE = SCRIPT_DIR / "traversals.jsonl"
APPLIED_FILE = SCRIPT_DIR / "traversals-applied.jsonl"   # history, append-only

# Myelination parameters
#
# Calibration rationale. With a base weight around 0.9 (similarity) and a
# reinforcement of 1.05, an edge needed ~11 traversals to cross 1.5 — an
# unreachable threshold at realistic retrieval volume. Two gentle levers instead
# of one abrupt one: reinforcement 1.10 and threshold 1.25, so edges with about
# 4 or more traversals become strong. Revisit once you have a month of
# retrieval data.
REINFORCE_FACTOR = 1.10   # per traversal (previously 1.05)
DECAY_FACTOR = 0.98       # per apply cycle — only on edges with traversals > 0
# Decay used to apply to every edge in the graph while each pass reinforced only
# a handful: the mean weight dropped on every run and the mechanism destroyed
# more signal than it created. That was not a script bug but the real
# read/write ratio of a vault. Now an edge can only decay if it was traversed at
# least once: decay measures disuse of a path that existed, not the absence of
# use of a path that was never opened. Falsifiable: if strong edges do not grow
# over the following weeks, the problem was retrieval volume, not decay, and
# this rule should be revisited.
# --decay-all restores the previous behaviour for simulations.
WEIGHT_CAP = 2.0          # max weight
WEIGHT_FLOOR = 0.1        # min weight (never reaches 0)
STRONG_THRESHOLD = 1.25   # "myelinated" edge (previously 1.5, unreachable at real volume)
PRUNE_THRESHOLD = 0.3     # decay candidate


# ============================================================
# RECORD — append a traversal event
# ============================================================

def cmd_record(args: argparse.Namespace) -> None:
    # Slugify defensively: callers (the retrieve skill) may pass note titles
    # instead of slugs. graph.jsonl edges are keyed by slug, so an unslugified
    # key here means `apply` can never match it.
    event = {
        "from": slugify(args.from_slug),
        "to": slugify(args.to_slug),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": args.query or "",
        "intent": args.intent or "operative",
    }
    with TRAVERSALS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(f"Recorded traversal: {event['from']} → {event['to']}")


def cmd_record_batch(pairs: list[tuple[str, str]], query: str = "", intent: str = "operative") -> int:
    """Record multiple traversals at once. Returns count written."""
    ts = datetime.now(timezone.utc).isoformat()
    count = 0
    with TRAVERSALS_FILE.open("a", encoding="utf-8") as f:
        for from_slug, to_slug in pairs:
            event = {
                "from": slugify(from_slug),
                "to": slugify(to_slug),
                "timestamp": ts,
                "query": query,
                "intent": intent,
            }
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
            count += 1
    return count


# ============================================================
# APPLY — update graph weights from traversals
# ============================================================

def load_graph() -> list[dict]:
    if not GRAPH_FILE.exists():
        raise SystemExit(f"No graph found at {GRAPH_FILE}")
    edges = []
    with GRAPH_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                edge = json.loads(line)
                if "weight" not in edge:
                    edge["weight"] = 1.0
                if "traversals" not in edge:
                    edge["traversals"] = 0
                edges.append(edge)
    return edges


def load_traversals() -> list[dict]:
    if not TRAVERSALS_FILE.exists():
        return []
    events = []
    with TRAVERSALS_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def cmd_apply(args: argparse.Namespace) -> None:
    edges = load_graph()
    traversals = load_traversals()

    if not traversals:
        print("No traversals to apply.")
        return

    # Build edge lookup: (from, to) → edge dict
    edge_map: dict[tuple[str, str], dict] = {}
    for e in edges:
        key = (e["from"], e["to"])
        edge_map[key] = e

    # Count traversals per edge
    traversal_counts: dict[tuple[str, str], int] = {}
    for t in traversals:
        key = (t["from"], t["to"])
        traversal_counts[key] = traversal_counts.get(key, 0) + 1

    # Apply reinforcement
    reinforced = 0
    for (from_s, to_s), count in traversal_counts.items():
        edge = edge_map.get((from_s, to_s))
        if edge is None:
            # Also check reverse (edges in graph are directional but
            # retrieval may traverse in either direction)
            edge = edge_map.get((to_s, from_s))
        if edge is None:
            continue
        for _ in range(count):
            edge["weight"] = min(edge["weight"] * REINFORCE_FACTOR, WEIGHT_CAP)
        edge["traversals"] = edge.get("traversals", 0) + count
        reinforced += 1

    # Apply decay — only to edges traversed at least once.
    # --decay-all restores the previous behaviour (every edge).
    decayed = 0
    skipped_untraversed = 0
    if not args.no_decay:
        for e in edges:
            if not getattr(args, "decay_all", False) and e.get("traversals", 0) <= 0:
                skipped_untraversed += 1
                continue
            old_w = e["weight"]
            e["weight"] = max(e["weight"] * DECAY_FACTOR, WEIGHT_FLOOR)
            if e["weight"] < old_w:
                decayed += 1

    # Write updated graph
    with GRAPH_FILE.open("w", encoding="utf-8") as f:
        for e in edges:
            # Round weight to avoid floating point noise
            e["weight"] = round(e["weight"], 4)
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # Archive instead of truncating (preservation rule: never delete history).
    # Truncating alone makes it impossible to re-simulate with the real sequence
    # of traversals later: only the aggregated counters would remain.
    if traversals:
        with APPLIED_FILE.open("a", encoding="utf-8") as f:
            for t_ev in traversals:
                t_ev = dict(t_ev)
                t_ev["applied_at"] = datetime.now(timezone.utc).isoformat()
                f.write(json.dumps(t_ev, ensure_ascii=False) + "\n")
    TRAVERSALS_FILE.write_text("", encoding="utf-8")

    # Stats
    strong = sum(1 for e in edges if e["weight"] >= STRONG_THRESHOLD)
    weak = sum(1 for e in edges if e["weight"] <= PRUNE_THRESHOLD)

    print(f"\nMyelination applied:")
    print(f"  Traversals processed: {len(traversals)}")
    print(f"  Edges reinforced:     {reinforced}")
    print(f"  Edges decayed:        {decayed}")
    print(f"  Skipped (never traversed): {skipped_untraversed}")
    print(f"  Strong (≥{STRONG_THRESHOLD}):        {strong}")
    print(f"  Weak (≤{PRUNE_THRESHOLD}):          {weak}")
    print(f"  Total edges:          {len(edges)}")



# ============================================================
# RECOMPUTE — re-derive weights from the base and the recorded traversals
# ============================================================

def cmd_recompute(args) -> None:
    """Recompute weight = base * REINFORCE_FACTOR^traversals for every edge.

    Why it exists: when REINFORCE_FACTOR (e.g. 1.05 -> 1.10) or STRONG_THRESHOLD
    (e.g. 1.5 -> 1.25) change, the weights already written were computed with
    the old factor, so changing the parameter reclassifies nothing — the weight
    is a derived value and has to be re-derived.

    The base is recovered by dividing by the historical factor (`--from-factor`).
    This is exact only if decay never ran on those edges (weight == base * old^t).
    """
    edges = load_graph()
    old = args.from_factor
    changed = 0
    for e in edges:
        t = e.get("traversals", 0)
        base = e["weight"] / (old ** t) if t else e["weight"]
        new_w = min(round(base * (REINFORCE_FACTOR ** t), 4), WEIGHT_CAP)
        if abs(new_w - e["weight"]) > 1e-9:
            changed += 1
        e["weight"] = new_w
    if args.apply:
        with GRAPH_FILE.open("w", encoding="utf-8") as f:
            for e in edges:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
    strong = [e for e in edges if e["weight"] >= STRONG_THRESHOLD]
    pairs = {frozenset((e["from"], e["to"])) for e in strong}
    print(f"edges recomputed: {changed} (factor {old} → {REINFORCE_FACTOR})")
    print(f"strong (>={STRONG_THRESHOLD}): {len(strong)} edges = {len(pairs)} distinct pairs")
    for e in sorted(strong, key=lambda e: -e["weight"])[:10]:
        print(f"   w={e['weight']:.3f} t={e.get('traversals',0)} [{e.get('type')}] {e['from'][:36]} → {e['to'][:36]}")
    print("(dry-run: --apply to write)" if not args.apply else "graph written")


# ============================================================
# REPORT — weight distribution and top/bottom edges
# ============================================================

def cmd_report(args: argparse.Namespace) -> None:
    edges = load_graph()
    traversals = load_traversals()
    if not edges:
        print("Graph is empty — nothing to report. Run indexer.py and autolink.py --all --write-graph first.")
        return

    weights = [e["weight"] for e in edges]
    total_traversals = sum(e.get("traversals", 0) for e in edges)

    strong = [e for e in edges if e["weight"] >= STRONG_THRESHOLD]
    weak = [e for e in edges if e["weight"] <= PRUNE_THRESHOLD]
    # The graph keeps parallel edges per type (relacionada_con + alimenta between
    # the same pair) and `record` reinforces both: counting edges inflates the
    # number, so distinct pairs are reported too.
    strong_pairs = {frozenset((e["from"], e["to"])) for e in strong}
    traversed_pairs = {frozenset((e["from"], e["to"])) for e in edges if e.get("traversals", 0) > 0}
    myelinated_types: dict[str, int] = {}
    for e in strong:
        myelinated_types[e["type"]] = myelinated_types.get(e["type"], 0) + 1

    print(f"\nMyelination report")
    print(f"{'=' * 60}")
    print(f"  Total edges:          {len(edges)}")
    print(f"  Pending traversals:   {len(traversals)}")
    print(f"  Total traversals:     {total_traversals}")
    print(f"  Weight range:         [{min(weights):.2f}, {max(weights):.2f}]")
    print(f"  Mean weight:          {sum(weights)/len(weights):.3f}")
    print(f"  Strong (≥{STRONG_THRESHOLD}):        {len(strong)} edges = {len(strong_pairs)} distinct pairs")
    print(f"  Weak (≤{PRUNE_THRESHOLD}):          {len(weak)}")
    print(f"  Traversed pairs:      {len(traversed_pairs)} (of {sum(1 for e in edges if e.get('traversals',0)>0)} edges)")

    if myelinated_types:
        print(f"\n  Myelinated by type:")
        for t, n in sorted(myelinated_types.items(), key=lambda x: -x[1]):
            print(f"    {t:20s} {n:>4}")

    # Top N strongest
    n = args.strongest or 10
    edges_by_weight = sorted(edges, key=lambda e: -e["weight"])
    print(f"\n  Top {n} strongest edges:")
    for e in edges_by_weight[:n]:
        trav = e.get("traversals", 0)
        print(f"    w={e['weight']:.2f}  t={trav:>3}  [{e['type']:15s}]  {e['from'][:40]} → {e['to'][:40]}")

    # Bottom N weakest
    n = args.weakest or 10
    print(f"\n  Bottom {n} weakest edges:")
    for e in edges_by_weight[-n:]:
        trav = e.get("traversals", 0)
        print(f"    w={e['weight']:.2f}  t={trav:>3}  [{e['type']:15s}]  {e['from'][:40]} → {e['to'][:40]}")


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command")

    # record
    p_rec = sub.add_parser("record", help="Log a traversal event")
    p_rec.add_argument("--from", dest="from_slug", required=True)
    p_rec.add_argument("--to", dest="to_slug", required=True)
    p_rec.add_argument("--query", default="")
    p_rec.add_argument("--intent", default="operative")

    # apply
    p_app = sub.add_parser("apply", help="Update graph weights from traversals")
    p_app.add_argument("--no-decay", action="store_true",
                       help="Skip decay step (reinforce only)")
    p_app.add_argument("--decay-all", action="store_true", dest="decay_all",
                       help="Decay every edge, including never-traversed ones (legacy behaviour)")

    # recompute
    p_rc = sub.add_parser("recompute", help="Re-derive weights with the current parameters")
    p_rc.add_argument("--from-factor", type=float, default=1.05,
                      help="reinforcement factor the current weights were written with")
    p_rc.add_argument("--apply", action="store_true")

    # report
    p_rep = sub.add_parser("report", help="Show weight distribution")
    p_rep.add_argument("--strongest", type=int, default=10)
    p_rep.add_argument("--weakest", type=int, default=10)

    args = parser.parse_args()

    if args.command == "record":
        cmd_record(args)
    elif args.command == "apply":
        cmd_apply(args)
    elif args.command == "recompute":
        cmd_recompute(args)
    elif args.command == "report":
        cmd_report(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
