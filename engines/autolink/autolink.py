#!/usr/bin/env python3
"""
Open Brain — Autolink Graph Builder
Reads all vault notes, extracts wikilinks with their typed relations,
writes graph.jsonl.

Usage (from autolink/ dir):
    python3 autolink.py --all --write-graph
    python3 autolink.py --all --write-graph --quiet
"""
import os, re, json, pathlib, unicodedata, argparse, sys, datetime
from patterns import WIKILINK_RE, classify_relation

# Vault root: $OPEN_BRAIN_VAULT if set, otherwise the parent of this autolink/ folder.
VAULT = pathlib.Path(os.environ.get("OPEN_BRAIN_VAULT") or pathlib.Path(__file__).resolve().parent.parent)
ENTITIES_F = pathlib.Path(__file__).parent / "entities.json"
GRAPH_F    = pathlib.Path(__file__).parent / "graph.jsonl"

# Directories whose notes are graph entities (and edge sources).
# Conceptual source of truth: vaultscan.KNOWLEDGE_DIRS + CAPTURE_DIRS, plus
# "Search Terms". Keep in sync with indexer.py.
#
# "Search Terms", "Domains", "Playbooks", "Sources", "Ideas" and "Fleeting Notes"
# must stay in this list: this script drops every link whose target is not in
# entities.json, so a missing directory turns all links into it into "broken"
# links that never reach the graph.
# The TERMINAL_DIRS (Projects, Manuscripts, Published, Research) are left out on
# purpose: they add almost no edges and are outputs, not knowledge.
NOTE_DIRS = [
    "Permanent Notes",
    "Literature Notes",
    "Cases",
    "Dossiers",
    "Domains",
    "Mentors",
    "Playbooks",
    "Areas",
    "Sources",
    "Inbox",
    "Ideas",
    "Fleeting Notes",
    "Search Terms",
]

CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
CALLOUT_RE  = re.compile(r"> \[!claude\].*?(?=\n\n|\Z)", re.DOTALL | re.IGNORECASE)

# Frontmatter fields that already ARE a typed relation. They skip
# classify_relation: their type is not inferred from context, it is known.
FM_FIELD_RELATIONS = (("search_terms", "indexa_por"), ("domains", "pertenece_a"))

# Structural indexing edges. They do NOT count toward the signal/noise ratio:
# there are usually far more of them than claim edges, and including them would
# push the ratio close to 100% without a single connector improving. The metric
# exists to watch the verbs used in connectors; mixing the indexing layer into it
# is exactly how a metric gets broken.
INDEX_RELATIONS = {"indexa_por", "pertenece_a"}


def fm_field_block(fm_text: str, field: str) -> str:
    """YAML block of a list field, up to the next top-level key."""
    m = re.search(rf"^{field}:(.*?)(?=^\S|\Z)", fm_text, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else ""

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")

def load_existing_weights() -> dict:
    """Load existing edge weights from graph.jsonl to preserve myelination.

    An edge's identity is `(from, to, type)`, same as in `update_graph.py`
    (`edge_key`). Keying only by `(from, to)` is a bug: two edges between the
    same pair of notes but of different types would share an entry and the last
    one read would overwrite the other. That happens routinely — `co_usada`
    coexists by construction with the typed edge of the same pair — and when
    their weights or traversals differ, a regeneration would erase real
    myelination. The number of such pairs grows with co-usage, which is exactly
    what myelinate.py feeds.
    """
    weights = {}
    if not GRAPH_F.exists():
        return weights
    try:
        for line in GRAPH_F.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            edge = json.loads(line)
            key = (edge["from"], edge["to"], edge.get("type"))
            weights[key] = {
                "weight": edge.get("weight", 1.0),
                "traversals": edge.get("traversals", 0),
            }
    except Exception:
        pass
    return weights

ORPHANS_F = pathlib.Path(__file__).parent / "myelination-orphans.jsonl"


def load_orphans() -> dict:
    """Myelination of edges that are no longer generated.

    WHY IT EXISTS. On a regeneration, some edges with traversals disappear —
    not weakened, absent. Typically they are `co_usada` edges no longer present
    in `co-usage.jsonl` (the graph correctly mirrors its source), or a typed edge
    whose relation stopped being declared in the note while both nodes still
    exist (so it is not a rename: the relation itself disappeared).

    An edge ceasing to exist when its relation stops being declared is correct.
    Losing what was learned about it is not: if the relation is declared again
    later, it would come back with `traversals: 0` and months of use would be
    silently lost. So it is kept here, never deleted, and restored automatically
    if the edge reappears.
    """
    if not ORPHANS_F.exists():
        return {}
    out = {}
    try:
        for line in ORPHANS_F.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            out[(e["from"], e["to"], e.get("type"))] = e
    except (OSError, ValueError):
        return {}
    return out


def save_orphans(orphans: dict) -> None:
    try:
        ORPHANS_F.write_text(
            "\n".join(json.dumps(v, ensure_ascii=False)
                      for v in orphans.values()) + "\n", encoding="utf-8")
    except OSError:
        pass


def extract_edges(path: pathlib.Path, entities: dict) -> list:
    """Extract typed edges from a note file."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    src_title = path.stem
    src_slug  = slugify(src_title)

    # The frontmatter is NOT discarded. `search_terms:` and `domains:` are the
    # vault's indexing layer and live exactly there. Stripping the frontmatter
    # before looking for wikilinks means every search_term that enrich writes
    # produces zero edges: enrich writes where the indexer does not read, and
    # health — which does count frontmatter — reports green while the graph is
    # empty. Two systems measuring different things on the same vault.
    fm_m = FRONTMATTER_RE.match(raw)
    fm_text = fm_m.group(0) if fm_m else ""
    body = raw[fm_m.end():] if fm_m else raw
    # Strip code blocks
    body = CODE_BLOCK_RE.sub("", body)

    edges = []
    seen = set()

    # (link_text, relation). Frontmatter first, with a fixed structural relation.
    candidates = []
    for field, rel in FM_FIELD_RELATIONS:
        for m in WIKILINK_RE.finditer(fm_field_block(fm_text, field)):
            candidates.append((m.group(1).strip(), rel))
    for m in WIKILINK_RE.finditer(body):
        link_text = m.group(1).strip()
        # Get ~80 chars before the [[
        start = m.start()
        context = body[max(0, start - 80):start]
        candidates.append((link_text, classify_relation(context, link_text)))

    for link_text, rel in candidates:
        # [[Folder/Note]] is valid Obsidian syntax and resolves by basename.
        # slugify() of the full path matches no entity, so without this every
        # such link would be dropped as broken — including the whole
        # LN -> Dossier column. Resolving by basename is what Obsidian does.
        target = link_text.rsplit("/", 1)[-1] if "/" in link_text else link_text
        tgt_slug = slugify(target)
        tgt_title = target

        # Skip self-links
        if tgt_slug == src_slug:
            continue

        # Skip if target not in entities (broken link)
        if tgt_slug not in entities and tgt_title not in entities:
            continue

        edge_key = (src_slug, tgt_slug, rel)
        if edge_key in seen:
            continue
        seen.add(edge_key)

        edges.append({
            "from": src_slug,
            "from_title": src_title,
            "to": tgt_slug,
            "to_title": tgt_title,
            "type": rel,
            "weight": 1.0,
            "traversals": 0,
        })

    return edges

def main():
    parser = argparse.ArgumentParser(description="Build Open Brain typed graph")
    parser.add_argument("--all", action="store_true", help="Process all note directories")
    parser.add_argument("--write-graph", action="store_true", help="Write graph.jsonl")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    if not VAULT.is_dir():
        print(f"❌ Vault not found: {VAULT} (set OPEN_BRAIN_VAULT)")
        sys.exit(1)
    if not ENTITIES_F.exists():
        print("❌ entities.json not found. Run indexer.py first.")
        sys.exit(1)

    entities = json.loads(ENTITIES_F.read_text(encoding="utf-8"))
    if not args.quiet:
        print(f"📦 Loaded {len(entities)} entities")

    # Preserve existing myelination weights
    existing_weights = load_existing_weights()

    all_edges = []
    notes_processed = 0

    for d in NOTE_DIRS:
        folder = VAULT / d
        if not folder.exists():
            continue
        for md in folder.rglob("*.md"):
            edges = extract_edges(md, entities)
            all_edges.extend(edges)
            notes_processed += 1

    # Co-usage edges (autolink/co-usage.jsonl, derived from the Retrieval Log).
    # They do not come from the notes, so --write-graph would erase them on
    # every rebuild unless they are re-added here. See co_usage.py.
    try:
        import co_usage as _cu
        _n = 0
        for _e in _cu.load_cousage():
            all_edges.append(_cu.graph_edge_from(_e)); _n += 1
        if _n and not args.quiet:
            print(f"   + {_n} co_usada edges from co-usage.jsonl")
    except Exception as _ex:  # never block the rebuild because of this
        if not args.quiet:
            print(f"   (co-usage not added: {_ex})")

    # Apply existing weights
    orphans = load_orphans()
    restored = 0
    for edge in all_edges:
        key = (edge["from"], edge["to"], edge.get("type"))
        if key in existing_weights:
            edge["weight"] = existing_weights[key]["weight"]
            edge["traversals"] = existing_weights[key]["traversals"]
        elif key in orphans:
            # The edge is declared again: recover what it had learned.
            o = orphans.pop(key)
            edge["weight"] = o.get("weight", 1.0)
            edge["traversals"] = o.get("traversals", 0)
            restored += 1

    # Myelination whose edge is gone: to the graveyard, not into the void.
    live = {(e["from"], e["to"], e.get("type")) for e in all_edges}
    new_orphans = 0
    for key, w in existing_weights.items():
        if key in live:
            continue
        if w.get("traversals", 0) > 0 or w.get("weight", 1.0) > 1.0:
            prev = orphans.get(key)
            # "huerfana_desde" = "orphaned since" (field name kept for compatibility).
            row = {"from": key[0], "to": key[1], "type": key[2],
                   "weight": w.get("weight", 1.0),
                   "traversals": w.get("traversals", 0),
                   "huerfana_desde": datetime.date.today().isoformat()}
            if prev:
                # keep the highest values: an orphan loses nothing by becoming one again
                row["weight"] = max(row["weight"], prev.get("weight", 1.0))
                row["traversals"] = max(row["traversals"], prev.get("traversals", 0))
                row["huerfana_desde"] = prev.get("huerfana_desde", row["huerfana_desde"])
            else:
                new_orphans += 1
            orphans[key] = row

    if args.write_graph and (orphans or ORPHANS_F.exists()):
        save_orphans(orphans)
    if not args.quiet and (restored or new_orphans or orphans):
        print(f"   myelination: {restored} restored from the graveyard, "
              f"{new_orphans} new orphans, {len(orphans)} in total")

    if args.write_graph:
        lines = [json.dumps(e, ensure_ascii=False) for e in all_edges]
        GRAPH_F.write_text("\n".join(lines) + "\n", encoding="utf-8")
        if not args.quiet:
            print(f"✅ Wrote {len(all_edges)} edges → graph.jsonl")

    if not args.quiet:
        # Distribution
        from collections import Counter
        dist = Counter(e["type"] for e in all_edges)
        print("\n📊 Edge distribution:")
        for rel, count in dist.most_common():
            print(f"   {rel:<25} {count:>5}")

        # The ratio is computed ONLY over claim edges (those that come from a
        # verb in the body). Indexing edges are reported separately.
        index_n = sum(v for k, v in dist.items() if k in INDEX_RELATIONS)
        claim   = {k: v for k, v in dist.items() if k not in INDEX_RELATIONS}
        signal  = sum(v for k, v in claim.items() if k not in ("menciona", "cita"))
        total   = sum(claim.values())
        ratio   = signal / total * 100 if total else 0
        print(f"\n🔖 Index edges (frontmatter): {index_n}")
        print(f"🎯 Signal/noise ratio: {ratio:.1f}% ({signal}/{total} non-trivial claim edges)")

        if ratio < 15:
            print("⚠️  Signal/noise < 15% — consider using stronger verbs in connectors")
            print("   (Contradicts, Extends, Refutes, Illustrates instead of 'Related to')")

    print(f"\n✅ Done: {notes_processed} notes processed, {len(all_edges)} edges built")

if __name__ == "__main__":
    main()
