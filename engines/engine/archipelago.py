#!/usr/bin/env python3
"""
archipelago.py — deterministic engine for grouping writing islands
(Islands & Bridges, used by open-brain-escribir).

Groups orphan islands (Fleeting Notes with `island: true` and no `manuscript:`)
by shared signal — touched LNs, domains, search terms/keywords, and typed edges
from autolink/graph.jsonl when available — and proposes at most TWO groups per
run: "these N islands look like the same piece". It writes nothing into the
notes: you decide whether a group fits and, if so, open the manuscript yourself
by writing the core idea. If a group does not fit, the islands stay orphaned
with no penalty — no automatic retry, no punishment.

It does not generate text: it does not propose a core idea, nor classify
communicates/contradicts/extends (that is the mapping session, with the islands
already on the table). It only groups.

Command:
  python3 archipelago.py             -> prints and writes the weekly proposal
  python3 archipelago.py --json      -> same, as JSON (to call from another skill)

Autodetects the vault (OPEN_BRAIN_VAULT or VAULT_ROOT override). Degrades
gracefully: 0 islands or 0 groups of 3+ is a valid result, not an error.
"""

# `X | None` in annotations is 3.10+; on Python 3.9 the module would crash at
# import. With this future import annotations are not evaluated.
from __future__ import annotations

import os
import re
import sys
import json
import glob
import datetime
from pathlib import Path
from collections import defaultdict

VAULT_MARKERS = ("Permanent Notes", "Literature Notes")
EXCLUDE_SEGMENTS = ("backups-", "_to_delete", ".git", "node_modules")
MAX_GROUPS_PER_RUN = 2
MIN_ISLANDS_PER_GROUP = 3

# A useful group is "these 3-4 islands look like the same piece". Above this
# size it is not a piece, it is a folder: it is reported as a signal that is
# too coarse and not proposed. (Once islands inherit `domains` from their LN, a
# single broad domain can otherwise glue dozens of islands into one group.)
MAX_ISLANDS_PER_GROUP = 8

# A domain that covers almost every island distinguishes nothing. Same
# principle as a search engine's idf: the signal is in what is rare. The
# threshold is over each run's orphan-island population, not a fixed list of
# domains, so there is nothing to maintain.
HUB_DOMAIN_SHARE = 0.30


def find_vault() -> Path | None:
    for k in ("OPEN_BRAIN_VAULT", "VAULT_ROOT"):
        env = os.environ.get(k)
        if env and Path(env).exists():
            return Path(env)
    here = Path(__file__).resolve()
    candidates = []
    for ancestor in [here.parent, *here.parents]:
        if all((ancestor / m).is_dir() for m in VAULT_MARKERS):
            if not any(seg in str(ancestor) for seg in EXCLUDE_SEGMENTS):
                candidates.append(ancestor)
    return candidates[0] if candidates else None


def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    fm_raw = m.group(1)
    fm = {}
    # simple scalar fields
    for key in ("island", "manuscript", "source", "created", "origin"):
        km = re.search(rf'^{key}:\s*"?(.*?)"?\s*$', fm_raw, re.M)
        if km:
            fm[key] = km.group(1).strip()
    # lists (lns_touched, domains, search_terms, keywords)
    for key in ("lns_touched", "domains", "search_terms", "keywords"):
        block = re.search(rf"^{key}:\n((?:\s+-.*\n)+)", fm_raw, re.M)
        if block:
            items = [l.strip("- \n").strip('"') for l in block.group(1).splitlines()]
            fm[key] = [re.sub(r"^\[\[|\]\]$", "", i) for i in items]
    return fm


def load_orphan_islands(vault: Path):
    islands = []
    for path in glob.glob(str(vault / "Fleeting Notes" / "*.md")):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        fm = parse_frontmatter(text)
        if fm.get("island", "").lower() != "true":
            continue
        if fm.get("manuscript"):
            continue  # no longer orphaned
        islands.append({"path": path, "name": Path(path).stem, **fm})
    return islands


def load_autolink_edges(vault: Path):
    """slug -> set(connected slugs), only if the graph exists."""
    graph_path = vault / "autolink" / "graph.jsonl"
    edges = defaultdict(set)
    if not graph_path.exists():
        return edges
    try:
        with open(graph_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                a, b = rec.get("from"), rec.get("to")
                if a and b:
                    edges[a].add(b)
                    edges[b].add(a)
    except OSError:
        pass
    return edges


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"\[\[|\]\]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def shared_signal(a: dict, b: dict, autolink_edges, hub_domains=frozenset()) -> list[str]:
    """Returns the reasons a and b group together; empty if none."""
    reasons = []
    lns_a, lns_b = set(a.get("lns_touched", [])), set(b.get("lns_touched", []))
    common_lns = lns_a & lns_b
    if common_lns:
        reasons.append(f"shared LN: {', '.join(sorted(common_lns))}")
    dom_a, dom_b = set(a.get("domains", [])), set(b.get("domains", []))
    common_dom = (dom_a & dom_b) - set(hub_domains)
    if common_dom:
        reasons.append(f"shared domain: {', '.join(sorted(common_dom))}")
    terms_a = set(a.get("search_terms", []) + a.get("keywords", []))
    terms_b = set(b.get("search_terms", []) + b.get("keywords", []))
    common_terms = terms_a & terms_b
    if common_terms:
        reasons.append(f"shared search term: {', '.join(sorted(common_terms))}")
    if autolink_edges:
        slugs_a = {slugify(x) for x in lns_a}
        slugs_b = {slugify(x) for x in lns_b}
        for sa in slugs_a:
            if autolink_edges.get(sa, set()) & slugs_b:
                reasons.append("autolink edge between their LNs")
                break
    return reasons


def cluster_islands(islands: list[dict], autolink_edges):
    """Simple union-find over the shared signal."""
    n = len(islands)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    dom_count = defaultdict(int)
    for isl in islands:
        for d in set(isl.get("domains", [])):
            dom_count[d] += 1
    hub_domains = frozenset(d for d, c in dom_count.items()
                            if n and c >= max(3, HUB_DOMAIN_SHARE * n))

    pair_reasons = {}
    for i in range(n):
        for j in range(i + 1, n):
            reasons = shared_signal(islands[i], islands[j], autolink_edges, hub_domains)
            if reasons:
                union(i, j)
                pair_reasons[(i, j)] = reasons

    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)

    clusters = []
    oversized = []
    for members in groups.values():
        if len(members) < MIN_ISLANDS_PER_GROUP:
            continue
        if len(members) > MAX_ISLANDS_PER_GROUP:
            oversized.append(len(members))
            continue
        reasons = set()
        for i in members:
            for j in members:
                if i < j and (i, j) in pair_reasons:
                    reasons.update(pair_reasons[(i, j)])
        clusters.append({
            "islands": [islands[i] for i in members],
            "reasons": sorted(reasons),
        })
    # sort by size, descending (strongest group first)
    clusters.sort(key=lambda c: -len(c["islands"]))
    return clusters[:MAX_GROUPS_PER_RUN], {"hub_domains": sorted(hub_domains),
                                           "oversized_groups": oversized}


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return
    as_json = "--json" in sys.argv
    vault = find_vault()
    if vault is None:
        print(json.dumps({"error": "vault not found"}) if as_json else "Vault not found — set OPEN_BRAIN_VAULT")
        sys.exit(1)

    islands = load_orphan_islands(vault)
    autolink_edges = load_autolink_edges(vault)
    if islands:
        clusters, diag = cluster_islands(islands, autolink_edges)
    else:
        clusters, diag = [], {"hub_domains": [], "oversized_groups": []}

    today = datetime.date.today().isoformat()
    result = {
        "date": today,
        "orphan_islands_total": len(islands),
        "groups_proposed": len(clusters),
        "hub_domains_ignored": diag["hub_domains"],
        "groups_dropped_for_size": diag["oversized_groups"],
        "groups": [
            {
                "size": len(c["islands"]),
                "islands": [i["name"] for i in c["islands"]],
                "reasons": c["reasons"],
            }
            for c in clusters
        ],
    }

    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # readable report + persisted
    lines = [f"# Archipelago — proposal for {today}", ""]
    lines.append(f"Orphan islands in the vault: **{len(islands)}**.")
    lines.append("")
    if not islands:
        lines.append("No orphan islands yet — nothing to group. Not an error: it is the expected state until the careo (open-brain-extract v10.11+) or `open-brain-escribir` produces the first one.")
    elif not clusters:
        lines.append(f"No combination of {MIN_ISLANDS_PER_GROUP}+ islands shares an LN, domain, search term or autolink edge within the size cap ({MAX_ISLANDS_PER_GROUP}) yet. More islands or more signal (filled-in `lns_touched`/`domains`) are needed before this engine can propose anything.")
    else:
        for idx, c in enumerate(clusters, 1):
            lines.append(f"## Group {idx} — {len(c['islands'])} islands look like the same piece")
            lines.append("")
            for i in c["islands"]:
                lines.append(f"- `{i['name']}`")
            lines.append("")
            lines.append(f"Why they group: {'; '.join(c['reasons'])}.")
            lines.append("")
        lines.append("If one of these groups fits, you write the core idea — one sentence (point of view + consequences) — and that is where the manuscript is born, with these islands already inside and `ship_by` at 21 days. If it does not fit, the islands stay orphaned with no penalty.")

    if diag["oversized_groups"]:
        sizes = ", ".join(str(s) for s in sorted(diag["oversized_groups"], reverse=True))
        n_groups = len(diag["oversized_groups"])
        plural = "s" if n_groups != 1 else ""
        lines.append("")
        verb = "were" if n_groups != 1 else "was"
        lines.append(
            f"Also, {n_groups} group{plural} with real signal (shared LN/domain/search term/autolink) "
            f"{verb} left out for exceeding the cap of {MAX_ISLANDS_PER_GROUP} islands "
            f"(size{'s' if n_groups != 1 else ''}: {sizes}). They are not listed here on purpose — a group that "
            f"big is usually a folder, not a piece — but it is real signal waiting for manual review. "
            f"Run `python3 engine/archipelago.py --json` to see which islands they are."
        )

    report = "\n".join(lines) + "\n"
    out_dir = vault / "Resources" / "Vault Health"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"Archipelago — Proposal — {today}.md"
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
    except PermissionError:
        os.chmod(out_path, 0o644)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)

    print(report)
    print(f"(Saved to {out_path})")


if __name__ == "__main__":
    main()
