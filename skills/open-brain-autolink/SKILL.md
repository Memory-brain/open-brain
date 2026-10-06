---
name: open-brain-autolink
description: 'Regenerates the typed knowledge graph (autolink/graph.jsonl). Runs silently after note-creating
  operations. Triggers: regenerate the graph, update autolink, open-brain autolink'
metadata:
  version: null
  status: canonical
  status_note: No version declared yet.
  requires_engine:
  - name: autolink.py
    version: unpinned
  - name: hyperedge.py
    version: unpinned
  - name: indexer.py
    version: unpinned
  - name: myelinate.py
    version: unpinned
  - name: query.py
    version: unpinned
  - name: surprise.py
    version: unpinned
  consumes:
  - A vault with notes connected by wikilinks
  - Automatic invocation after operations that create/modify notes (promote, escribir, extract, enrich,
    health)
  produces:
  - Typed graph graph.jsonl (~18 relation types)
  - entities.json with slug/type/domain/aliases per note
  - hyperedges.jsonl (n-ary clusters) and traversals.jsonl (myelination)
  - Novelty/duplication assessment of incoming content (SurpriseFilter)
  handoffs:
  - skill: open-brain-graph
    when: to answer relational questions by querying the freshly regenerated graph
    requires_approval: true
  - skill: open-brain-escribir
    when: to find PNs that contradict/are in tension with a claim while writing
    requires_approval: true
  - skill: open-brain-health
    when: to detect orphan notes and broken wikilinks using the graph
    requires_approval: true
  - skill: open-brain-promote
    when: when creating a PN, to check which existing PNs contradict or extend the new one
    requires_approval: true
---

# Open Brain — Autolink

Regenerates and maintains the vault's typed graph. This is the engine that classifies every wikilink between notes into ~18 relation types (contradicts, extends, refutes, cross_domain, etc.) by reading the verbs around each `[[link]]`. It does not use an LLM — it is a deterministic Python pipeline.

## Resolving paths — MANDATORY, read this before doing ANYTHING

- `$OPEN_BRAIN_VAULT` = the root of your Markdown vault. Notes are read from there.
- `$OPEN_BRAIN_ENGINES` = the directory holding the engine scripts. Autolink lives in `$OPEN_BRAIN_ENGINES/autolink/`, and its outputs (`graph.jsonl`, `entities.json`, `hyperedges.jsonl`, `traversals.jsonl`) are written next to the scripts in that same directory.

If your agent runs file tools and shell in different environments (e.g. a sandbox that mounts the vault under another path), resolve each variable separately for each context: file tools use the host path, the shell uses the mounted path.

**Checking that autolink exists (Step 0):**

1. Try to `Read` `$OPEN_BRAIN_ENGINES/autolink/graph.jsonl`.
   If it returns content → autolink exists and has a graph. Continue.
2. If Read fails, try to `Read` `$OPEN_BRAIN_ENGINES/autolink/indexer.py`. If it exists → the scripts
   are there but the graph has not been generated. Run the pipeline (Steps 1 + 2 below).
3. If both fail → the autolink engine is not installed. Tell the user it needs to be installed under `$OPEN_BRAIN_ENGINES/autolink/`.

**NEVER declare that autolink does not exist without having tried the COMPLETE and CORRECT path.**
The most common mistake is running `ls autolink/` without the full path, or using the file-tools
path in the shell (or vice versa). Each context has its own path.

## When it runs

### Explicit invocation

The user says "regenerate the graph", "update autolink", "open-brain autolink", "index the relations", "rebuild the graph".

### Automatic (chained) invocation

Run automatically after operations that create or modify notes with typed connections:

| After... | What to do |
|---|---|
| `open-brain promote` (new PN created) | Regenerate full graph |
| `open-brain escribir` (write-back created a new note) | Regenerate full graph |
| `open-brain extract` (batch of LNs created) | Regenerate full graph |
| `open-brain enrich` (connections added to existing notes) | Regenerate full graph |
| `open-brain health` (notes repaired/moved) | Regenerate full graph |

Regeneration takes ~5 seconds for ~4,000 notes. It is cheap. When in doubt, regenerate.

Do not chain after:
- `open-brain retrieve` (read-only, does not modify notes)
- `open-brain flashcards` (does not modify notes)
- `open-brain analyze` (produces output in the conversation, not in the vault)

### Suggested regeneration

If the graph is older than 7 days (`graph.jsonl` modification date), suggest regenerating at the start of any operation that queries it (graph, escribir step 2).

## Pipeline

Autolink lives in `$OPEN_BRAIN_ENGINES/autolink/`. Scripts in sequence:

### Step 1 — Index the vault

```bash
cd "$OPEN_BRAIN_ENGINES/autolink"
python3 indexer.py
```

Reads every note in the vault. Generates `entities.json` with slug, type, domain and aliases for each note. Takes <1 second.

### Step 2 — Build the graph

```bash
python3 autolink.py --all --write-graph --quiet
```

Reads each note, detects wikilinks in the body (excluding frontmatter and code blocks), looks at the ~80 characters before each wikilink, and assigns a relation type from a prioritized cascade. The type identifiers are written exactly as the engine emits them:

```
refuta > contradice > refina > extiende > depende_de > ejemplifica >
validado_por > aplica_a > alimenta > se_ancla_en > refuerza >
operacionaliza > relacionada_con > cita > menciona
```

(refutes > contradicts > refines > extends > depends_on > exemplifies > validated_by > applies_to > feeds > anchors_in > reinforces > operationalizes > related_to > cites > mentions.)

Plus 3 structural patterns evaluated before the cascade:
- `cross_domain` — "Cross-domain (X ↔ Y): [[Z]]"
- `sintetiza_desde` (synthesized from) — "Synthesized from [[X]]"
- `sintetizada_en` (synthesized into) — "synthesized into [[X]]"

Generates `graph.jsonl` with the typed edges. Takes ~3–5 seconds.

### Step 3 — Verify (optional)

After regenerating, report briefly to the user:
- Total number of notes indexed
- Total number of edges
- Type distribution (how many `contradice`, `extiende`, `cross_domain`, etc. vs how many `menciona`)
- Signal/noise ratio: percentage of edges that are NOT `menciona` or `cita`

If the signal/noise ratio is low (<15%), suggest that when writing connections in PNs the user puts strong verbs (Contradicts, Extends, Refutes, Exemplifies) before the link instead of "Related to".

## Queries available after regenerating

Once the graph is regenerated, the queries are available to other skills. The `query.py` queries:

```bash
python3 query.py contradictions       # PNs in tension
python3 query.py fertile --type permanent  # most fertile root PNs (weighted by myelination)
python3 query.py cross-domain         # connections between domains
python3 query.py orphans              # PNs with no incoming relations
python3 query.py sandwich             # Cases connecting ≥2 PNs
python3 query.py cases-of "Slug"      # Cases of a specific PN
python3 query.py myelinated           # strongest/weakest edges by usage
python3 query.py clusters             # hyperedges / n-ary convergences
```

Flags: `--limit N`, `--type T` (permanent, case, literature...), `--json`.

## Hyperedges — n-ary clusters

The binary edges in `graph.jsonl` represent 1:1 relations. When 3+ notes converge on a single thesis, that convergence is poorly captured by pairs — it needs a **hyperedge**: an atomic entry grouping N members under a shared thesis.

### File: `hyperedges.jsonl`

Lives in `autolink/`, separate from `graph.jsonl`. It does not modify it. Each line:

```json
{"id": "he_001", "type": "convergence", "members": ["slug1", "slug2", "slug3"], "thesis": "What they converge on", "source_skill": "synthesize", "strength": 1.0, "created": "YYYY-MM-DD"}
```

Three types:
- **convergence** — Multiple LNs/PNs point to the same insight.
- **tension_cluster** — Multiple notes in productive tension (they don't refute each other, but pull in different directions).
- **application_bundle** — A Case + multiple PNs it operationalizes.

### Script: `hyperedge.py`

Three commands:

```bash
# Add a hyperedge (minimum 3 members)
python3 hyperedge.py add \
    --members "slug1" "slug2" "slug3" \
    --type convergence \
    --thesis "What they converge on" \
    --source synthesize

# Query hyperedges (filterable by type and member)
python3 hyperedge.py query
python3 hyperedge.py query --type convergence
python3 hyperedge.py query --member "slug1" --json

# Detect candidate clusters in graph.jsonl (does NOT auto-create)
python3 hyperedge.py detect
python3 hyperedge.py detect --limit 10 --json
```

`detect` scans `graph.jsonl` for groups of 3+ nodes connected to the same hub via edges of type `alimenta/extiende/operacionaliza/sintetiza_desde`. It reports candidates but **does not create** hyperedges — the user decides which ones are worth it.

### `clusters` query in query.py

```bash
python3 query.py clusters                    # all hyperedges
python3 query.py clusters --type convergence # filter by type
python3 query.py clusters --json             # JSON output
```

### When to create hyperedges

| Moment | Who |
|---|---|
| `open-brain synthesize` detects convergence of 3+ PNs | `source_skill: synthesize` |
| `open-brain promote` creates a PN that converges with 2+ existing ones | `source_skill: promote` |
| The user explicitly asks for it | `source_skill: manual` |

### What hyperedges do NOT do

- **They do not replace binary edges.** They are an additional layer. `graph.jsonl` remains the source of truth for 1:1 relations.
- **They are not auto-created.** `detect` suggests, the user confirms.
- **They do not modify notes.** They are graph metadata, not vault content.

## Who consumes the graph

| Skill | How it uses it |
|---|---|
| **graph** | Answers relational questions (contradictions, fertile, cross-domain, sandwiches) |
| **escribir** | Step 2 — finds PNs that contradict/are in tension with the claim to feed the mentor's questions |
| **health** | Detects orphan notes, broken wikilinks, disconnected zones |
| **enrich** | Identifies notes with few typed connections to improve |
| **promote** | When creating a PN, can check which existing PNs contradict or extend the new one |

## What autolink does NOT do

- **It does not write to notes.** It is read-only over the vault. Writing typed connections is done by the skills that create/modify notes (promote, escribir, enrich).
- **It does not use an LLM.** It is deterministic. If a type is assigned wrongly, the fix is to edit `patterns.py` — not to ask the assistant to fix it.
- **It does not replace open-brain-graph.** Autolink regenerates the graph; graph queries and interprets it for the user. They are complementary.

## Myelination — reinforcing traversed edges

Inspired by neuron (Z-Sigma): graph edges traversed during retrieval are reinforced; edges that fall out of use decay. The most used knowledge paths get stronger over time.

### Components

1. **`myelinate.py`** in `autolink/` — three commands:
   - `record` — records a traversal in `traversals.jsonl`
   - `apply` — reinforces edges (×1.10 per traversal), applies decay (×0.98) only to edges that have been traversed at least once, updates `graph.jsonl`
   - `report` — shows the weight distribution and myelinated edges

2. **`traversals.jsonl`** — append-only log. Each line: `{"from": "slug", "to": "slug", "timestamp": "ISO", "query": "...", "intent": "operative"}`.

3. **`graph.jsonl`** — two optional fields per edge: `weight` (default 1.0) and `traversals` (default 0). Autolink preserves these when regenerating.

4. **`query.py myelinated`** — query to see the state of myelination.

### When it runs

| Moment | Action |
|---|---|
| During `open-brain-retrieve` (Step 10/11) | `log_entry.py close` records a traversal for every pair of notes listed as used substantively (PN↔PN, LN↔LN or mixed) |
| After `autolink --write-graph` | `myelinate.py apply` to update weights |
| In `open-brain-health` (Check 18) | `myelinate.py report` + `myelinate.py apply` if there are pending traversals |
| Periodically | `myelinate.py apply` as the graph's "sleep cycle" |

### Integration with open-brain-retrieve

Retrieve records traversals automatically when it closes its log entry:
1. The notes used substantively in the response are listed in the log entry.
2. Every co-used pair is recorded as a traversal (any note type; pairs without an edge in `graph.jsonl` are ignored at `apply` time).
3. **Serendipity mode is recorded too** — myelination tracks actual usage independently of `times_retrieved` (which skips Serendipity), so the graph learns even from exploratory retrieval.
4. Queries about the system itself (closed with `--origen_uso auditoría`) are not recorded.
5. Retrieve never runs `apply`.

### Parameters

| Param | Value | Effect |
|---|---|---|
| `REINFORCE_FACTOR` | 1.10 | ×1.10 per traversal |
| `DECAY_FACTOR` | 0.98 | ×0.98 per apply cycle, only on edges traversed at least once (never-traversed edges keep their weight) |
| `WEIGHT_CAP` | 2.0 | Maximum |
| `WEIGHT_FLOOR` | 0.1 | Minimum (never 0) |
| `STRONG_THRESHOLD` | 1.25 | Edge counts as "myelinated" |
| `PRUNE_THRESHOLD` | 0.3 | Pruning candidate |

### Effect on queries

- `fertile` ranks by **weighted fertility** (count × avg_weight). PNs with myelinated edges rise.
- `myelinated` shows the state of the graph.
- `contradictions` does not change.

---

## SurpriseFilter — novelty gate for ingest

Inspired by neuron (Z-Sigma): assesses the novelty of incoming content BEFORE a note is created in the vault. It uses discrete vault signals instead of vector embeddings — deterministic, no LLM.

### Components

1. **`surprise.py`** in `autolink/` — two commands:
   - `evaluate` — assesses the novelty of proposed content (title + terms + mentor)
   - `stats` — shows vault coverage statistics

2. **Three signals** (weights sum to 1.0):
   - `search_terms overlap` (0.50) — how many proposed terms already exist in notes
   - `title similarity` (0.35) — trigram Jaccard against existing titles
   - `mentor saturation` (0.15) — diminishing returns for an over-represented mentor

3. **Three bands** (as in neuron):
   - **Novel** (≥0.6) — proceed with ingest
   - **Confirmation** (0.3–0.6) — reinforces existing knowledge → suggest linking
   - **Duplicate** (<0.3) — near-duplicate → warn the user

### Usage

```bash
python3 surprise.py evaluate \
    --title "Proposed title" \
    --terms "Term1,Term2,Term3" \
    --mentor "Author" \
    --type inbox

python3 surprise.py stats
```

### Who consumes it

| Skill | How it uses it |
|---|---|
| **ingest** (Step 0.7) | Assesses novelty before creating Inbox/Case notes |
| **health** | Can use `stats` to diagnose term/mentor saturation |

### What SurpriseFilter does NOT do

- **It does not block.** The user can always override.
- **It does not use an LLM.** It is deterministic — trigrams + counts.
- **It does not modify existing notes.** It only reads the vault.
- **It does not assess Design References or Fleeting Notes** — only Inbox and Cases.

---

## Future work

Not yet implemented:
1. Write mode (`--write`) that writes relations into frontmatter.
2. Stale reconciliation — remove relations that no longer exist in the text.
3. Integration with promote — every new PN goes through here automatically.
4. Advanced queries.
5. **Synaptic pruning** — archive PNs whose edges persistently decay below `PRUNE_THRESHOLD`.

Item 3 is already partially implemented through this skill's automatic chaining.
