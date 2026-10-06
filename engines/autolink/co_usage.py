#!/usr/bin/env python3
"""co_usage.py — co-usage edges derived from the Retrieval Log.

WHY: notes you used TOGETHER in the same retrieval session often have no edge
between them in graph.jsonl, so (a) `myelinate.py apply` cannot reinforce
anything — the recorded traversals match no edge — and (b) `graph_hop.py`
cannot reach one from the other. The graph connects what notes cite; it does
not connect what usage shows belongs together. This script adds that second
source.

WHAT IT DOES: reads `Resources/Retrieval Log.md`, takes the `Notas usadas
sustantivamente` (notes used substantively) of each entry, forms every pair and
writes them as `co_usada` edges in `autolink/co-usage.jsonl`. `traversals` =
number of log entries in which the pair appeared together (literally what
graph_hop.py calls "empirically co-used"). `merge` injects them into graph.jsonl.

WHY A SEPARATE FILE: `autolink.py --write-graph` rebuilds graph.jsonl from the
notes and `update_graph.py` rewrites the touched note's edges; an edge added by
hand to graph.jsonl dies on the next pass. co-usage.jsonl is the source of
truth, regenerable from the log, and both scripts read it.

Title resolution: log wikilinks often fail to resolve (titles shortened when
writing, renamed notes). They are resolved on READ with
retrieval-eval/rlib.Resolver (unique prefix), never by rewriting the log.
`build` requires the retrieval-eval engine (`$OPEN_BRAIN_ENGINES/retrieval-eval/rlib.py`).

Usage:
  python3 autolink/co_usage.py build          # log -> co-usage.jsonl (idempotent)
  python3 autolink/co_usage.py merge          # co-usage.jsonl -> graph.jsonl (idempotent)
  python3 autolink/co_usage.py build merge    # both
  python3 autolink/co_usage.py report         # how many edges, how many new, top pairs
  python3 autolink/co_usage.py metrics        # flat JSON for Meta/metrics.json (panel)
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Vault root: $OPEN_BRAIN_VAULT if set, otherwise the parent of this autolink/ folder.
VAULT = Path(os.environ.get("OPEN_BRAIN_VAULT") or HERE.parent)
# Engines directory (where retrieval-eval/ lives): defaults to the vault root.
ENGINES = Path(os.environ.get("OPEN_BRAIN_ENGINES") or HERE.parent)
GRAPH_F = HERE / "graph.jsonl"
COUSAGE_F = HERE / "co-usage.jsonl"
EDGE_TYPE = "co_usada"

sys.path.insert(0, str(HERE))
from graph_hop import slugify  # same key graph.jsonl uses  # noqa: E402

sys.path.insert(0, str(ENGINES / "retrieval-eval"))
try:
    import rlib  # noqa: E402
except ImportError:  # pragma: no cover
    rlib = None


def _resolver():
    """Resolver from log wikilinks -> real note. Requires the retrieval-eval
    index; if it does not exist, falls back to exact title matching."""
    if rlib is None:
        return None
    ix_path = ENGINES / "retrieval-eval" / ".cache" / "index.json"
    if not ix_path.exists():
        return None
    ix = rlib.Index.load(str(ix_path))
    return rlib.Resolver(ix, str(VAULT))


def _titles_by_norm():
    """Fallback without retrieval-eval: normalized title -> real title."""
    out = {}
    for p in VAULT.rglob("*.md"):
        if any(part.startswith(".") or part in ("node_modules", "_to_delete") for part in p.parts):
            continue
        key = _norm(p.stem)
        out.setdefault(key, p.stem)
    return out


def _norm(s):
    import re
    import unicodedata
    s = s.split("|")[0].split("/")[-1].replace("…", " ").replace("...", " ").lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def cmd_build():
    if rlib is None:
        raise SystemExit("retrieval-eval/rlib.py not found — install the retrieval-eval engine next to autolink/ (or set OPEN_BRAIN_ENGINES)")
    entries = rlib.parse_log(str(VAULT))
    rs = _resolver()
    fallback = None if rs else _titles_by_norm()
    pair_count = Counter()
    pair_dates = defaultdict(set)
    titles = {}
    unresolved = Counter()
    for e in entries:
        used = []
        for lk in e["used"]:
            if rs:
                rel, st = rs.resolve(lk)
                if not rel or st == "outside_corpus":
                    unresolved[st] += 1
                    continue
                title = os.path.basename(rel)[:-3]
            else:
                title = fallback.get(_norm(lk))
                if not title:
                    unresolved["missing"] += 1
                    continue
            used.append(title)
        used = sorted(set(used))
        for a, b in combinations(used, 2):
            sa, sb = slugify(a), slugify(b)
            if sa == sb:
                continue
            key = (sa, sb)
            pair_count[key] += 1
            pair_dates[key].add(e["date"])
            titles[sa], titles[sb] = a, b
    lines = []
    for (sa, sb), n in sorted(pair_count.items(), key=lambda x: (-x[1], x[0])):
        lines.append(json.dumps({
            "from": sa, "from_title": titles[sa],
            "to": sb, "to_title": titles[sb],
            "type": EDGE_TYPE, "weight": 1.0, "traversals": n,
            "sessions": sorted(pair_dates[(sa, sb)]),
            "source": "Resources/Retrieval Log.md",
        }, ensure_ascii=False))
    COUSAGE_F.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(json.dumps({"ok": True, "entries": len(entries), "pairs": len(pair_count),
                      "pairs_repeated": sum(1 for n in pair_count.values() if n > 1),
                      "unresolved_links": dict(unresolved), "out": str(COUSAGE_F)},
                     ensure_ascii=False, indent=1))


def load_cousage():
    if not COUSAGE_F.exists():
        return []
    out = []
    for line in COUSAGE_F.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def graph_edge_from(e):
    """Canonical graph.jsonl shape (without the source-traceability fields,
    but WITH sessions: without it, a leave-one-session-out evaluation would have
    to join graph.jsonl and co-usage.jsonl by hand)."""
    return {k: e[k] for k in ("from", "from_title", "to", "to_title", "type", "weight",
                              "traversals", "sessions")}


def cmd_merge():
    if not GRAPH_F.exists():
        raise SystemExit("graph.jsonl not found — run indexer.py and autolink.py --all --write-graph first")
    graph = [json.loads(l) for l in GRAPH_F.read_text(encoding="utf-8").splitlines() if l.strip()]
    existing = {(g["from"], g["to"], g.get("type")) for g in graph}
    # pairs already connected by ANY type, in any direction: there the
    # co-usage edge adds no reach to graph_hop, but it does add usage evidence
    # (traversals) that myelinate can reinforce -> it is added anyway.
    added, updated = 0, 0
    by_key = {(g["from"], g["to"], g.get("type")): g for g in graph}
    for e in load_cousage():
        k = (e["from"], e["to"], EDGE_TYPE)
        if k in by_key:
            g = by_key[k]
            changed = False
            if g.get("traversals", 0) < e["traversals"]:
                g["traversals"] = e["traversals"]
                changed = True
            # sessions: co-usage.jsonl is the source of truth (build rebuilds it
            # entirely every time), so it is synced by union instead of only
            # growing with traversals — this is what backfills existing
            # co_usada edges that graph.jsonl did not carry yet.
            merged_sessions = sorted(set(g.get("sessions", [])) | set(e.get("sessions", [])))
            if merged_sessions != g.get("sessions", []):
                g["sessions"] = merged_sessions
                changed = True
            if changed:
                updated += 1
            continue
        graph.append(graph_edge_from(e))
        existing.add(k)
        added += 1
    if added or updated:
        GRAPH_F.write_text("\n".join(json.dumps(g, ensure_ascii=False) for g in graph) + "\n",
                           encoding="utf-8")
    print(json.dumps({"ok": True, "added": added, "updated": updated,
                      "graph_edges": len(graph)}, indent=1))


def _load_graph_or_empty():
    if not GRAPH_F.exists():
        return []
    return [json.loads(l) for l in GRAPH_F.read_text(encoding="utf-8").splitlines() if l.strip()]


def cmd_report():
    cu = load_cousage()
    graph = _load_graph_or_empty()
    any_edge = set()
    for g in graph:
        if g.get("type") != EDGE_TYPE:
            any_edge.add((g["from"], g["to"])); any_edge.add((g["to"], g["from"]))
    novel = [e for e in cu if (e["from"], e["to"]) not in any_edge]
    print(json.dumps({
        "co_usage_edges": len(cu),
        "pairs_without_any_other_edge": len(novel),
        "pct_novel": round(100.0 * len(novel) / len(cu), 1) if cu else None,
        "in_graph": sum(1 for g in graph if g.get("type") == EDGE_TYPE),
        "top_pairs": [{"n": e["traversals"], "a": e["from_title"][:60], "b": e["to_title"][:60]}
                      for e in cu[:8]],
    }, ensure_ascii=False, indent=1))


def cmd_metrics():
    """Flat output for Meta/metrics.json. The number that matters: what fraction of
    the traversals myelination already recorded matches some graph edge today.
    Without co-usage edges it is typically very low. If it drops, someone
    regenerated the graph without `merge`."""
    import datetime
    graph = _load_graph_or_empty()
    edges = set()
    for g in graph:
        edges.add((g["from"], g["to"])); edges.add((g["to"], g["from"]))
    cu = load_cousage()
    cu_set = set()
    for e in cu:
        cu_set.add((e["from"], e["to"])); cu_set.add((e["to"], e["from"]))
    tr_f = HERE / "traversals.jsonl"
    pairs = set()
    if tr_f.exists():
        for l in tr_f.read_text(encoding="utf-8").splitlines():
            if l.strip():
                t = json.loads(l); pairs.add((t["from"], t["to"]))
    matched = sum(1 for p in pairs if p in edges)
    other = {(g["from"], g["to"]) for g in graph if g.get("type") != EDGE_TYPE}
    other |= {(b, a) for a, b in other}
    novel = sum(1 for e in cu if (e["from"], e["to"]) not in other)
    print(json.dumps({
        "schema": "co-usage-metrics/1",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "vault": str(VAULT),
        "traversals_pairs": len(pairs), "traversals_matched": matched,
        "pct_matched": round(matched / len(pairs), 4) if pairs else None,
        "co_usage_edges": len(cu), "in_graph": sum(1 for g in graph if g.get("type") == EDGE_TYPE),
        "novel_pct": round(novel / len(cu), 4) if cu else None,
        "detail": "%d/%d pairs recorded by myelinate match an edge · %d co_usada edges, %s without any other edge" % (
            matched, len(pairs), len(cu), ("%.1f %%" % (100.0 * novel / len(cu))) if cu else "—"),
    }, ensure_ascii=False, indent=1))


def main():
    cmds = sys.argv[1:] or ["report"]
    for c in cmds:
        {"build": cmd_build, "merge": cmd_merge, "report": cmd_report, "metrics": cmd_metrics}.get(
            c, lambda: (_ for _ in ()).throw(SystemExit("unknown command: " + c + " (use build, merge, report, metrics)")))()


if __name__ == "__main__":
    main()
