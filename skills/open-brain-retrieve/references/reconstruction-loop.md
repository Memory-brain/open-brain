# Step 4.5 — Iterative Reconstruction Loop (MRAgent)

> The three passes (standard retrieval, reverse traversal, graph traversal via autolink), the navigate-vs-answer decision and how reconstructed paths are logged. Read when the first pass is not enough.

---

## Step 4.5: Iterative Reconstruction Loop (MRAgent-inspired)

Standard retrieval (Steps 1–4 of Query Types 1–7) is a single-pass grep: search for `[[X]]` in search_terms, gather matching notes, rank, and respond. This works well for direct queries but misses notes reachable only through indirect paths — the vault equivalent of multi-hop reasoning.

The Iterative Reconstruction Loop adds a second (and optionally third) pass inspired by MRAgent's active memory reconstruction. The core insight: **found content reveals new search directions the initial query didn't know to look for.**

### When to activate

Activate the loop when:
- Query Type 1 returns **3 or fewer notes** (thin results suggest the query terms are too narrow)
- Query Type 2 (connections) — **always** (connection queries are inherently multi-hop)
- Query Type 7 (serendipity) — **always** (the whole point is finding unexpected paths)
- Any query where the initial pass returns notes but none are PNs (all LNs suggests the topic has not been compressed yet — traverse to find related PNs)

Skip the loop when:
- Initial pass returns 5+ notes including 2+ PNs (the vault already has strong coverage)
- Time-critical queries where the user explicitly asks for speed ("quick", "just give me the first thing")

### Pass 1: Standard retrieval (existing behavior)

Run the normal grep against search_terms and body content. This is the "cue" phase — the initial query terms are your first cues.

### Pass 2: Reverse traversal — Content reveals new cues

After Pass 1, the frontmatter pre-filter (step 5) has already ranked all candidates by `description` relevance — **read the full body of the top 3 notes** (by that ranking). From each note, extract:

1. **Their search_terms**: wikilinks in the `search_terms:` frontmatter field that were NOT in the original query
2. **Connector wikilinks**: notes referenced in `> [!claude] Connectors` blocks (these are the assistant's own cross-references — high signal)
3. **Body wikilinks**: `[[Note]]` references in the note body (lower signal, but useful for multi-hop)
4. **search_context relations** (if present): the `relation` field tells you WHY a term connects to this note — use it to filter relevant terms

Deduplicate the new terms against the original query terms. Run a **second grep** with the top 5 new terms (prioritize Connector wikilinks > search_terms > body wikilinks).

Notes found in Pass 2 that were NOT in Pass 1 are **reconstruction candidates**. Tag them in the response: `(via reconstruction from [[Source Note]])` so the user sees the provenance.

### Pass 3: Graph traversal via autolink (conditional)

If Pass 1+2 surfaced PNs, consult `autolink/graph.jsonl` (in `$OPEN_BRAIN_ENGINES/autolink/`) for typed edges leading to notes the grep would not find. This is the "navigate" phase — using the vault's relational structure.

**Procedure:**

1. For each PN found in Pass 1 or Pass 2, query graph.jsonl for edges where that PN is source OR target
2. Filter by edge type — only follow high-signal relations (edge-type identifiers are kept as the engine writes them):
   - `extiende` (extends) — the connected note builds on the found note
   - `contradice` / `refuta` (contradicts / refutes) — tension is always worth surfacing
   - `cross_domain` — the most valuable for non-obvious connections
   - `alimenta` (feeds) — the connected note feeds into the found note
   - `operacionaliza` (operationalizes) — the connected note makes the found note practical
   - `refuerza` (reinforces) — the connected note reinforces the same mechanism from a different angle
3. For edges with `weight > 1.0` (myelinated — frequently traversed), boost priority
4. Read the connected notes. If relevant to the original query, include them tagged: `(via graph: [edge_type] from [[Source PN]])`

**Implementation** — two options depending on how many seeds you have:

```bash
# Option A: single-seed query (1 PN at a time)
python3 "$OPEN_BRAIN_ENGINES/autolink/query.py" cases-of "<PN slug>" --json

# Option B: batch multi-seed hop (when you have 3+ PNs from Pass 1+2 — more efficient)
python3 "$OPEN_BRAIN_ENGINES/autolink/graph_hop.py" --seeds "Title 1" "Title 2" "Title 3" --max 5 --json
```

`graph_hop.py` walks 1 hop from all seeds simultaneously and deduplicates neighbors, returning the top-N by edge signal. Prefer it when Pass 1+2 surfaced 3+ PNs — one call replaces N serial `query.py` calls. If neither script is available, grep `graph.jsonl` directly.

### Navigate vs Answer decision

After each pass, evaluate: **do I have enough evidence to synthesize a response, or should I keep navigating?**

- If the accumulated notes cover the query with 1+ PN and evidence from multiple sources → **Answer mode**: stop iterating, synthesize
- If still only LNs or single-source coverage → **Navigate mode**: continue to next pass
- Maximum 3 passes total (Pass 1 + Pass 2 + Pass 3). Never iterate beyond 3 — diminishing returns

### What this changes in existing Query Types

| Query Type | Before | After |
|---|---|---|
| QT1 "What do I know about X?" | Steps 3-4 grep once | Steps 3-4 grep once, then reconstruction loop if thin |
| QT2 "Connections A and B" | Steps 1-4 find notes for each concept | Always run reconstruction — connections ARE multi-hop |
| QT7 Serendipity | Invert heuristics on single-pass results | Always run reconstruction — serendipity IS exploration |
| QT8 Visual | No change — visual retrieval uses its own ranking | |

### Logging reconstructed paths

In the Retrieval Log (Step 10), add two fields:
```markdown
**Reconstruction passes**: N (1 = standard only, 2 = +reverse traversal, 3 = +graph)
**Reconstruction yield**: M notes added (list the notes found only through reconstruction)
```

For myelination (Step 11), list every note used substantively — including those found through reconstruction — in `Notas usadas sustantivamente`, so the graph learns from multi-hop retrieval, not just direct matches.

---
