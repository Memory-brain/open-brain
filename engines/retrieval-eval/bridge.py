#!/usr/bin/env python3
"""bridge — the channel that reproduces the vault's real architecture.

retrieve.md says "Always start from structured entry points — never browse
folders randomly": the agent does not look for the note, it looks for the HUB
(Search Terms, Domains) and walks down from there to the notes. The vault's
Search Terms are exactly that. This channel makes it deterministic:

    query --(lexical + LSA over the hubs)--> hubs --(backlinks)--> notes

The query->hub match IS lexically viable: hubs are short topical vocabulary
("Visual Hierarchy", "Button Hierarchy"), not claims. It is the bridge that
direct BM25 over notes cannot cross.

The log's gold is overwhelmingly Permanent + Literature Notes, so hubs are a
bridge and never a candidate: HUB_FOLDERS are excluded from candidates, and
vice versa.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict

import rlib

HUB_FOLDERS = {"Search Terms", "Domains"}
NON_CANDIDATE = {"Search Terms", "Mentors", "Skills", "Tasks"}
LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def is_candidate(folder):
    return folder not in NON_CANDIDATE


def build(root, ix, path):
    """hub_norm -> [rel of the notes that reference it], by wikilink or by
    frontmatter search_terms."""
    hubs = {}
    for i, d in enumerate(ix.docs):
        if d["folder"] in HUB_FOLDERS:
            hubs[rlib.norm_title(d["title"])] = i
    back = defaultdict(set)
    for note in rlib.iter_notes(root):
        if not is_candidate(note["folder"]) or note["rel"] not in ix.by_rel:
            continue
        refs = set(LINK_RE.findall(note["body"])) | set(note["search_terms"])
        for r in refs:
            key = rlib.norm_title(r)
            if key in hubs:
                back[key].add(note["rel"])
    data = {"hubs": {k: v for k, v in hubs.items()},
            "back": {k: sorted(v) for k, v in back.items()},
            "fingerprint": ix.fingerprint()}
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return {"hubs": len(hubs), "fingerprint": ix.fingerprint(),
            "hubs_with_backlinks": len(back),
            "backlinks_total": sum(len(v) for v in back.values())}


class Bridge(object):
    def __init__(self, path, ix, lsa_model=None):
        raw = json.load(open(path, encoding="utf-8"))
        if raw.get("fingerprint") != ix.fingerprint():
            raise RuntimeError(
                "bridge.json is out of sync with the index. "
                "Rebuild: python3 eval_retrieval.py index")
        self.hubs = raw["hubs"]
        self.back = raw["back"]
        self.ix = ix
        self.lsa = lsa_model
        self.hub_idx = {v: k for k, v in self.hubs.items()}

    def top_hubs(self, query, n=8):
        """Hubs closest to the query. Lexical (BM25 restricted to hubs) + LSA."""
        scored = defaultdict(float)
        for rel, s in self.ix.bm25(query, k=400):
            i = self.ix.by_rel.get(rel)
            if i is not None and i in self.hub_idx:
                scored[self.hub_idx[i]] += s
        if self.lsa:
            for rel, s in self.lsa.search(query, k=400):
                i = self.ix.by_rel.get(rel)
                if i is not None and i in self.hub_idx:
                    scored[self.hub_idx[i]] += 6.0 * s
        return sorted(scored.items(), key=lambda x: (-x[1], x[0]))[:n]

    def search(self, query, k=100, n_hubs=8):
        hubs = self.top_hubs(query, n=n_hubs)
        if not hubs:
            return []
        sc = defaultdict(float)
        hits = defaultdict(list)
        for hkey, hs in hubs:
            notes = self.back.get(hkey, [])
            if not notes:
                continue
            # a hub with 300 backlinks discriminates less than one with 5
            w = hs / (1.0 + (len(notes) / 25.0))
            for rel in notes:
                sc[rel] += w
                hits[rel].append(hkey)
        ranked = sorted(sc.items(), key=lambda x: (-x[1], -len(hits[x[0]]), x[0]))
        return [(rel, round(s, 4)) for rel, s in ranked[:k]]
