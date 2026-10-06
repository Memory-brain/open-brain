---
name: "open-brain-enrich"
description: "Improves retrieval by adding search_terms, domains and connections to existing notes without touching their content. The plumbing (scan, audit, crowding, writing, report) is done by enrich-engine/enrich_engine.py reusing vault-scan; the AI GENERATES the candidate terms. Optional Phase 0: retrieval-gaps reads Resources/Retrieval Log.md and uses real usage evidence (queries that failed or were reformulated) to decide what to enrich, instead of only the static count of search_terms. Optional Phase 4: connect.py adds \"## Typed Connections\" to PNs to raise the graph's signal/noise. Triggers: improve the search terms, enrich, I can't find this note, open-brain enrich"
---

# Open Brain — Enrich (v3.3, engine + vault-scan)

Optimizes retrieval: enriches `search_terms`, adds secondary domains and proposes
splits of saturated terms. It does NOT change content — only metadata and links. The plumbing
lives in `$OPEN_BRAIN_ENGINES/enrich-engine/enrich_engine.py`, which **reuses the shared vault-scan library** (it does not
reimplement scanning). Your job as the AI: **generate the candidate search_terms** (the only
irreducible part) and decide secondary domains and how to split crowded terms.

Model: **the agent orchestrates · engine + vault-scan execute · any UI or dashboard consumes the reports.**

Requires `vault-scan/` installed under `$OPEN_BRAIN_ENGINES` (like autolink). The engine locates it on its own. All vault paths below are relative to `$OPEN_BRAIN_VAULT`. In the commands, `enrich-engine/…` and `autolink/…` are relative to `$OPEN_BRAIN_ENGINES` (run them from there or prefix the variable).

## Phase 0 — reactive enrich from usage evidence (optional)

The Retrieval Log written by `open-brain-retrieve` is meant to feed evidence-based enrichment. This
phase is a complement to Phases 1–3, not a substitute: those index by a static threshold
(how many search_terms does the note have?); this one indexes by real evidence (what did
the user search for, what did we return, what was missing?).

```bash
python3 "$OPEN_BRAIN_ENGINES/enrich-engine/enrich_engine.py" retrieval-gaps [--since YYYY-MM-DD]
python3 "$OPEN_BRAIN_ENGINES/enrich-engine/enrich_engine.py" mark-processed --json '{"entries":[{"entry_key":"<header>","classification":"indexing_fix|content_gap|not_actionable","note":"..."}]}'
```

`retrieval-gaps` extracts from the log the entries with `Outcome: partial/failure`, `Reformulation?: yes`,
or a repeated-failure marker, that are not already in `Resources/Vault Health/Retrieval Gaps
Processed.jsonl`. **It classifies nothing** — that is the AI's judgment (Phase 0.5), and experience
shows why it cannot be mechanized: in a first real run, almost all candidates were content or product gaps
("a note about X is missing", "a missing feature or tool for Y") and only a small minority were genuine indexing misses.
Triage per candidate:

- **`indexing_fix`**: the note(s) that should have answered DO exist, but their `search_terms`
  do not cover the angle of the query that failed or was reformulated. Generate the candidate terms
  as in normal Phase 2 and apply them with `apply` (Phase 3), citing the real query as evidence.
- **`content_gap`**: no note answers it. This is NOT an enrich fix — enrich does not
  change content. Report it as an ingest candidate or a `[!gap]` callout; do not touch search_terms.
- **`not_actionable`**: the "gap" is about a product/feature (a missing feature or tool, a
  view), not retrieval. Record it so it does not repeat, but it is not enrich's work.

After deciding each candidate, record it with `mark-processed` (by `entry_key` = the exact log
header) so the next run does not repeat it. A candidate that points to a decision the
user must make (e.g. duplicates to merge, misplaced notes) is marked and reported —
never resolved silently, even if it is technically "just metadata": moving/merging notes
is not.

## Phase 1 — the engine scans (no thinking needed)

```bash
python3 "$OPEN_BRAIN_ENGINES/enrich-engine/enrich_engine.py" scan                    # distribution + notes under threshold (default 3 specific, resolvable terms)
python3 "$OPEN_BRAIN_ENGINES/enrich-engine/enrich_engine.py" audit "<note>"          # resolved/broken search_terms, orphan domains
python3 "$OPEN_BRAIN_ENGINES/enrich-engine/enrich_engine.py" crowding                # saturated terms (via vault-scan)
python3 "$OPEN_BRAIN_ENGINES/enrich-engine/enrich_engine.py" registry                # active domains
python3 "$OPEN_BRAIN_ENGINES/enrich-engine/enrich_engine.py" split-orphans [--parent P] [--all]   # notes with a hub but none of its children
```

`scan` threshold is configurable (strict 6 / default 3 / --threshold N). The default is `MIN_SPECIFIC = 3`
in the engine: the enrichment floor is ≥3 specific, resolvable terms (hubs and terms without a page don't count).
Extraction writes 4–6 terms (lint L05 warns below 4 written), so a note can pass L05 and still sit under this
floor if some of its terms are hubs or unpaged; a higher threshold in enrich would count as backlog notes that already meet the contract. `audit` flags search_terms with a broken link and
domains that are not in the registry (orphan domains → do NOT touch them, it reports them).

A term without a page in `Search Terms/`, or a hub (a term with children, or a Domain), **does not count**.
Always measure with `scan` (specific-resolvable terms), never with the number of strings or the
`needs_enrichment` flag.

## Phase 2 — YOU generate the terms (judgment, irreducible)

For each note under the threshold, read its body and generate candidate search_terms thinking like
the user when they search: the inverse (what to avoid), the domain angle, the problem angle (not just
the name of the solution), the synonym (use the canonical one if a Search Term already exists). Quality test:
"if the user searched for X and found this note, would they think 'exactly what I needed'?".
Run the candidates through `resolve-terms`: `alias` → canon, `near` → judgment, `hub` → exists but does not
count (add one of its `children`), `free` → only coined if ≥2 notes justify it, and with a page.

For **crowded** terms (red in crowding): decide the split by sub-topic / domain /
context (e.g. `[[Agent Memory]]` → Episodic / Semantic / Filesystem). Keep the parent term.
Do NOT auto-split without the user's approval.

**Mandatory close of every split**: when children are created, the parent becomes a hub and no longer counts
as specific. After applying the split, run

```bash
python3 "$OPEN_BRAIN_ENGINES/enrich-engine/enrich_engine.py" split-orphans --parent "<Parent>" --all
```

and assign a child to **every** note it returns, not only the sampled ones. Without this step a
split silently leaves many notes with one specific term fewer. Without `--parent` it lists every hub; without
`--all` only the notes that fell below the minimum.

## Phase 3 — the engine writes what you decided

```bash
python3 "$OPEN_BRAIN_ENGINES/enrich-engine/enrich_engine.py" apply --json '{"note":"<path>","add_search_terms":[...],"add_domains":[...]}'
python3 "$OPEN_BRAIN_ENGINES/enrich-engine/enrich_engine.py" report --json '{"markdown":"<the report>"}'
```

`apply` adds terms/domains (without duplicating) + `enriched: <date>`, and **refuses** to touch
any protected field (layer, confidence, maturity, times_retrieved, and the visual fields of
Design References), terms without a page (unless `--allow-new`) and Domain hubs the note does not
declare (rule H2, unless `--allow-hub-mismatch`). `report` persists to
`Resources/Vault Health/Enrichment Reports/`. `apply` takes ~3–4 s per note (it loads the registry):
for large batches, parallelize and make it resumable, because every shell call has a time limit.

**needs_enrichment**: if the note had `needs_enrichment: true`, `apply` recomputes
the specific-resolvable terms after merging the new ones and, if it reaches the threshold (default ≥3,
override with `--needs-enrichment-threshold`), sets the flag to `false`. If it is still below, it leaves it
at `true` on purpose — it is still real backlog. The output JSON includes
`specific_resolvable_after` and `cleared_needs_enrichment` so you can see it at once.

## Token tracking (mandatory after every invocation)

When Phase 3 is done, estimate and record the token cost of the enrich session:
- `input_tokens`: Σ characters of notes read (bodies) ÷ 4.
- `output_tokens`: Σ characters of generated search_terms + apply JSON ÷ 4.
- Append an entry to the end of `Resources/Vault Health/Enrich Cost Log.jsonl`:
  ```jsonl
  {"date":"YYYY-MM-DD","notes_enriched":N,"input_tokens":N,"output_tokens":N,"crowded_splits":N}
  ```
  Create the file if it does not exist. This feeds M1 (indexing cost) of the eval protocol (`open-brain-eval`).

## Phase 4 — Typed Connections (optional, `--connections`)

Problem: wikilinks in PNs often have the form `[[X]] — description` (context AFTER the link),
so autolink cannot classify the relation type and records everything as `menciona` (mentions). Result:
a low signal/noise ratio.

Solution: `autolink/connect.py` adds a `## Typed Connections` section at the end of each PN with
sentences that put the verb BEFORE the link:

```
- Feeds [[X]] because the mechanism it describes triggers the effect described here.
- Refines [[Y]] by narrowing the activation condition to the scarcity context.
```

autolink.py has a LAYER 0 that processes `## Typed Connections` FIRST, before the main body,
so its types take precedence over any earlier mention of the same target.

**Workflow:**

```bash
# 1. See current coverage
python3 "$OPEN_BRAIN_ENGINES/autolink/connect.py" status

# 2. Export untyped PN→PN pairs (up to 50 PNs, 6 targets each)
python3 "$OPEN_BRAIN_ENGINES/autolink/connect.py" scan --limit 50 --json > /tmp/scan_batch.json

# 3. Classify with the LLM (you): for each pair, decide the relation type.
#    Use the prompt in connect.py's docstring. Output: JSON with "type" and "sentence".

# 4. Write the classified connections to the vault
python3 "$OPEN_BRAIN_ENGINES/autolink/connect.py" apply --json '<payload_json>'

# 5. Regenerate the graph to see the impact on signal/noise
python3 "$OPEN_BRAIN_ENGINES/autolink/autolink.py" --all --write-graph --quiet
```

**Classification prompt (for the LLM):**
> For each source→target pair, classify the relation. Use ONLY these type identifiers (strongest first):
> refuta, contradice, refina, extiende, depende_de, ejemplifica, validado_por, aplica_a, alimenta,
> operacionaliza, sintetiza_desde, cross_domain (refutes, contradicts, refines, extends, depends_on, exemplifies,
> validated_by, applies_to, feeds, operationalizes, synthesized_from, cross_domain). If it is not more specific than
> "mentions" → use "skip".
> Write a sentence in the language of the source note with the verb BEFORE the link:
> `"{Capitalized verb} [[{title}]] {justification ≤12 words}."`
> Return the same JSON as the scan with "type" and "sentence" added to each target.

**Rules:**
- Only types in connect.py's VALID_TYPES list (skip, relacionada_con, menciona → ignored)
- The sentence MUST have the typed verb BEFORE the `[[link]]` so autolink detects it
- Max 6 connections per PN — prioritize the semantically richest
- Do NOT create generic connections ("related to") — if the relation is not clear, skip

## What lives in the engine (no longer in this prompt)

Selection of under-indexed notes and distribution · search_terms audit (resolved/broken)
· domain registry + orphan-domain detection · crowding (via vault-scan) · resolve-terms
with a `hub` bucket · split-orphans · safe frontmatter writing with a protected-fields guard
· clearing `needs_enrichment` when the note reaches the threshold · extraction of candidates with
Retrieval Log evidence and their processed ledger · report persistence.

## Rules (judgment / policy)

- NEVER change the title or content (author's body, Evidence, Source pointer, `[!claude] Connectors`, Your extension). Metadata only.
- Do NOT remove existing search_terms or connections.
- Do NOT add speculative domains — only a direct, clear connection.
- Do NOT create a Search Term for every synonym — use `aliases`.
- Do NOT force rule H2 with `--allow-hub-mismatch` in bulk: if the note does not declare the parent domain, leave the hub out.
- Orphan domains: report them for `open-brain-synthesize`, NEVER map them silently.
- Typed Connections (Phase 4) only when the user explicitly asks to improve the graph's signal/noise.
- Phases 2–3 are NOT run on Design References (they use linked_pns/source_lns).
- Practical note: the real backlog is usually free terms used by a single note, and crowding. Before
  attributing a backlog to extract, separate the causes: threshold, hubs, batches that did not go through the lint
  (`generated_by` without an engine stamp) and free terms.
