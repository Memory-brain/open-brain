#!/usr/bin/env python3
"""
Open Brain — Graph Query Engine
Queries graph.jsonl for insight patterns.

Usage:
    python3 query.py contradictions
    python3 query.py fertile --type permanent
    python3 query.py cross-domain
    python3 query.py orphans
    python3 query.py sandwich
    python3 query.py cases-of "slug-or-title"
    python3 query.py myelinated
    python3 query.py clusters

Flags: --limit N  --type T  --json
"""
import json, pathlib, sys, argparse, unicodedata, re
from collections import defaultdict

AUTOLINK = pathlib.Path(__file__).parent
GRAPH_F  = AUTOLINK / "graph.jsonl"
HYPEREDGES_F = AUTOLINK / "hyperedges.jsonl"

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")

def load_graph():
    if not GRAPH_F.exists():
        print("❌ graph.jsonl not found. Run autolink.py --all --write-graph first.")
        sys.exit(1)
    edges = []
    for line in GRAPH_F.read_text(encoding="utf-8").splitlines():
        if line.strip():
            edges.append(json.loads(line))
    return edges

def load_hyperedges():
    if not HYPEREDGES_F.exists():
        return []
    result = []
    for line in HYPEREDGES_F.read_text(encoding="utf-8").splitlines():
        if line.strip():
            result.append(json.loads(line))
    return result

# ── QUERIES ─────────────────────────────────────────────────────────────────

def q_contradictions(edges, limit=20, note_type=None, as_json=False):
    """Find notes in tension (contradice/refuta edges)."""
    tension_types = {"contradice", "refuta"}
    pairs = []
    for e in edges:
        if e["type"] in tension_types:
            pairs.append(e)

    if note_type:
        pairs = [e for e in pairs if note_type.lower() in e.get("from_title", "").lower() or
                 note_type.lower() in e.get("to_title", "").lower()]

    pairs = pairs[:limit]
    if as_json:
        print(json.dumps(pairs, ensure_ascii=False, indent=2))
        return

    print(f"⚡ Contradictions / tensions ({len(pairs)} found):\n")
    for e in pairs:
        print(f"  [{e['type'].upper()}] {e['from_title']}")
        print(f"    → {e['to_title']}")
        print()

def q_fertile(edges, limit=20, note_type="permanent", as_json=False):
    """Find most-connected notes (weighted fertility)."""
    out_count   = defaultdict(int)
    out_weight  = defaultdict(float)
    out_titles  = {}

    for e in edges:
        if e["type"] not in ("menciona", "cita"):
            src = e["from"]
            out_count[src] += 1
            out_weight[src] += e.get("weight", 1.0)
            out_titles[src] = e.get("from_title", src)

    in_count = defaultdict(int)
    for e in edges:
        in_count[e["to"]] += 1

    nodes = list(set(out_count.keys()) | set(in_count.keys()))
    scored = []
    for n in nodes:
        score = out_count[n] * out_weight.get(n, out_count[n])
        scored.append((n, score, out_count[n], in_count[n], out_titles.get(n, n)))

    scored.sort(key=lambda x: -x[1])

    if note_type:
        # Filter by type heuristic based on slug patterns
        pass  # type filtering would need entities.json; skip for now

    scored = scored[:limit]

    if as_json:
        result = [{"slug": s, "score": sc, "out": o, "in": i, "title": t}
                  for s, sc, o, i, t in scored]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"🌱 Fertile nodes (top {len(scored)}):\n")
    for slug, score, out, inc, title in scored:
        print(f"  {title}")
        print(f"    score={score:.1f}  out={out}  in={inc}")
        print()

def q_cross_domain(edges, limit=20, as_json=False):
    """Find cross-domain connections."""
    xd = [e for e in edges if e["type"] == "cross_domain"][:limit]

    if as_json:
        print(json.dumps(xd, ensure_ascii=False, indent=2))
        return

    print(f"🌐 Cross-domain connections ({len(xd)} found):\n")
    for e in xd:
        print(f"  {e['from_title']}")
        print(f"    ↔ {e['to_title']}")
        print()

def q_orphans(edges, limit=20, as_json=False):
    """Find permanent/case notes with no incoming signal edges."""
    has_in = set()
    for e in edges:
        if e["type"] not in ("menciona", "cita"):
            has_in.add(e["to"])

    all_nodes = set()
    for e in edges:
        all_nodes.add(e["from"])

    orphans = []
    for n in all_nodes:
        if n not in has_in:
            # Find title
            title = n
            for e in edges:
                if e["from"] == n:
                    title = e.get("from_title", n)
                    break
            orphans.append((n, title))

    orphans = orphans[:limit]

    if as_json:
        print(json.dumps([{"slug": s, "title": t} for s, t in orphans], ensure_ascii=False, indent=2))
        return

    print(f"🏝️  Orphan nodes (no incoming signal edges, top {len(orphans)}):\n")
    for slug, title in orphans:
        print(f"  {title}")

def q_sandwich(edges, limit=20, as_json=False):
    """Find Cases that connect ≥2 PNs (sandwich pattern)."""
    case_targets = defaultdict(set)
    case_titles  = {}
    for e in edges:
        # Heuristic: Cases folder slugs often start with "case-" or contain "case"
        # Better: detect by path but we only have slug here
        # Use from_title heuristic
        title = e.get("from_title", "")
        if e["type"] not in ("menciona", "cita"):
            case_targets[e["from"]].add(e["to"])
            case_titles[e["from"]] = title

    sandwiches = [(slug, targets, case_titles[slug])
                  for slug, targets in case_targets.items()
                  if len(targets) >= 2]
    sandwiches.sort(key=lambda x: -len(x[1]))
    sandwiches = sandwiches[:limit]

    if as_json:
        result = [{"slug": s, "connects": list(t), "title": ti, "count": len(t)}
                  for s, t, ti in sandwiches]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"🥪 Sandwich nodes (connect ≥2 PNs, top {len(sandwiches)}):\n")
    for slug, targets, title in sandwiches:
        print(f"  {title}  [{len(targets)} connections]")
        for t in list(targets)[:5]:
            print(f"    → {t}")
        print()

def q_cases_of(edges, target_slug, limit=20, as_json=False):
    """Find notes that point to a given PN."""
    target = slugify(target_slug)
    results = [e for e in edges if e["to"] == target or
               e.get("to_title", "").lower() == target_slug.lower()]
    results = results[:limit]

    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    print(f"🎯 Notes referencing '{target_slug}' ({len(results)} found):\n")
    for e in results:
        print(f"  [{e['type'].upper()}] {e['from_title']}")

def q_myelinated(edges, limit=20, as_json=False):
    """Show myelination state — strongest and weakest edges."""
    strong = [e for e in edges if e.get("weight", 1.0) >= 1.5]
    weak   = [e for e in edges if e.get("weight", 1.0) <= 0.5]
    strong.sort(key=lambda x: -x.get("weight", 1.0))
    weak.sort(key=lambda x: x.get("weight", 1.0))

    if as_json:
        print(json.dumps({"strong": strong[:limit], "weak": weak[:limit]}, ensure_ascii=False, indent=2))
        return

    print(f"🧬 Myelination state\n")
    print(f"  Strong edges (weight ≥ 1.5): {len(strong)}")
    for e in strong[:limit]:
        print(f"    {e['from_title']} → {e['to_title']}  w={e.get('weight',1.0):.2f} traversals={e.get('traversals',0)}")
    print(f"\n  Weak edges (weight ≤ 0.5): {len(weak)}")
    for e in weak[:5]:
        print(f"    {e['from_title']} → {e['to_title']}  w={e.get('weight',1.0):.2f}")

def q_clusters(edges, limit=20, cluster_type=None, as_json=False):
    """Show hyperedges / convergence clusters."""
    hyperedges = load_hyperedges()
    if cluster_type:
        hyperedges = [h for h in hyperedges if h.get("type") == cluster_type]
    hyperedges = hyperedges[:limit]

    if as_json:
        print(json.dumps(hyperedges, ensure_ascii=False, indent=2))
        return

    if not hyperedges:
        print("ℹ️  No hyperedges found. Run hyperedge.py detect to find candidates.")
        return

    print(f"🔮 Clusters / hyperedges ({len(hyperedges)}):\n")
    for h in hyperedges:
        print(f"  [{h.get('type','?').upper()}] {h.get('thesis','(no thesis)')}")
        for m in h.get("members", []):
            print(f"    • {m}")
        print()

# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Open Brain graph queries")
    parser.add_argument("query", choices=[
        "contradictions", "fertile", "cross-domain", "orphans",
        "sandwich", "cases-of", "myelinated", "clusters"
    ])
    parser.add_argument("target", nargs="?", help="Target slug for cases-of")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--type", dest="note_type", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    edges = load_graph()
    print(f"📦 Loaded {len(edges)} edges from graph.jsonl\n")

    q = args.query
    if q == "contradictions":
        q_contradictions(edges, args.limit, args.note_type, args.json)
    elif q == "fertile":
        q_fertile(edges, args.limit, args.note_type, args.json)
    elif q == "cross-domain":
        q_cross_domain(edges, args.limit, args.json)
    elif q == "orphans":
        q_orphans(edges, args.limit, args.json)
    elif q == "sandwich":
        q_sandwich(edges, args.limit, args.json)
    elif q == "cases-of":
        if not args.target:
            print("❌ cases-of requires a target slug/title")
            sys.exit(1)
        q_cases_of(edges, args.target, args.limit, args.json)
    elif q == "myelinated":
        q_myelinated(edges, args.limit, args.json)
    elif q == "clusters":
        q_clusters(edges, args.limit, args.note_type, args.json)

if __name__ == "__main__":
    main()
