---
module: module-1-enrichment
related_skills:
  - open-brain-enrich
  - open-brain-autolink
  - open-brain-retrieve
last_updated: 2026-10-06
---

# The Enrichment Pattern

## What It Is

The Enrichment Pattern is a systematic maintenance process for knowledge vaults. It treats findability and connectedness as ongoing operations — not something you set up once and forget.

The pattern addresses three failures that compound as a vault grows:

1. **[Retrieval decay](retrieval-decay.md)** — Notes become unfindable because their search metadata hasn't kept pace with how your thinking evolves
2. **[Term saturation](term-saturation.md)** — Search terms lose discriminative power as too many notes accumulate under the same tag
3. **[Knowledge graph noise](knowledge-graph-signal-noise.md)** — Connections between notes are all generic "mentions," making the graph structurally rich but semantically empty

The Enrichment Pattern solves all three with a single, repeatable process that operates on three layers.

---

## The Three Layers

### Layer 1: Search Term Expansion

**Goal:** Every note should be findable through at least 3 specific, resolvable search terms — terms with a page in `Search Terms/` that are not hubs. Extraction aims for 4–6; 3 is the floor below which a note becomes enrichment backlog.

Most notes are created with a title and maybe a tag or two. This captures what the note *is about*, but not how you'd *search for it* later. Search term expansion closes this gap by adding entry points that match future search intent.

**The four angles:**

| Angle | Question it answers | Example for a note on "Spaced Repetition" |
|---|---|---|
| Concept name | What is this about? | `spaced repetition`, `SRS` |
| Problem angle | What problem does this solve? | `forgetting what I learned`, `knowledge retention` |
| Inverse angle | What's the failure mode it prevents? | `cramming doesn't work`, `memory decay` |
| Domain crossing | Where else does this apply? | `language learning intervals`, `habit formation timing` |

**Quality test:** For each proposed search term, ask: *"If I searched for this term and found this note, would I think 'this is exactly what I needed'?"* If the answer is no, the term is too broad or too tangential.

**What to avoid:**
- Adding a synonym for every possible phrasing (use aliases for true synonyms instead)
- Adding terms that are technically accurate but nobody would search for
- Adding domain-crossing terms that are speculative rather than demonstrated in the note's content

### Layer 2: Term Decompression

**Goal:** No specific search term should be tagged on more than 20 notes. Above 10 it is yellow (watch); above 20 it is red (split). Hubs, and the terms directly under them, are judged against 150 instead — see [Term Saturation](term-saturation.md).

When a term accumulates too many notes, it needs to be decomposed into sub-terms. This is not re-tagging — the parent term stays. Sub-terms are added to notes that warrant the more specific framing.

**Splitting axes:**

```
Parent term: [[Feedback Loops]]

By sub-theme:    [[Positive Feedback Loops]], [[Negative Feedback Loops]], [[Delayed Feedback]]
By domain:       [[Feedback Loops in Product]], [[Feedback Loops in Learning]], [[Feedback Loops in Teams]]
By specificity:  [[Feedback Loop Design]], [[Feedback Loop Measurement]], [[Feedback Loop Failure Modes]]
By problem/sol:  [[When Feedback Loops Break]], [[Building Effective Feedback Loops]]
```

**Decision criteria for which axis to use:**

- If the notes under the term cover different sub-topics → split by sub-theme
- If the notes apply the same concept to different fields → split by domain
- If the notes range from abstract to concrete → split by specificity
- If the notes mix diagnosis and prescription → split by problem/solution

**Rule:** Only coin a sub-term if at least 2 notes justify it, and create its page in `Search Terms/` at the same time. Below that, the split adds taxonomy overhead without retrieval benefit.

**Close the split.** Once the parent has children it becomes a hub and stops counting as a specific term. After every split, find each note that carries the parent but no child, and give it a child term — all of them, not a sample.

### Layer 3: Connection Typing

**Goal:** Raise the share of claim edges that are neither `mentions` nor `cites`. Frontmatter edges (note → search term, note → domain) are left out of the ratio. Below 15% is flagged as low.

This layer classifies the relationships between notes using a controlled vocabulary: `refutes`, `contradicts`, `refines`, `extends`, `depends_on`, `exemplifies`, `validated_by`, `applies_to`, `feeds`, `operationalizes`, `synthesizes_from`, `cross_domain`.

Connection typing is the most labor-intensive layer and delivers the most long-term value. It turns the knowledge graph from a visual novelty into a queryable reasoning structure.

**The sentence-first pattern:**

```markdown
## Typed Connections
- Extends [[Cognitive Load Theory]] to sequential decision-making under time pressure.
- Contradicts [[Information Abundance Hypothesis]] in expert-domain contexts.
- Validated by [[Sweller 1988 Experiment]] across three task complexity levels.
```

The relationship verb comes *before* the wikilink. This makes the connection human-readable and machine-parseable simultaneously.

**Scope of typing:** Only Permanent Note → Permanent Note pairs are typed, with at most 6 typed connections per Permanent Note. Cross-domain pairs are the most valuable to type. This layer is optional and runs when you ask to improve the graph's signal; it is not part of the routine enrichment cycle.

---

## The Process

Enrichment runs as a cycle of five phases. Phase 0 and Phase 4 are optional; Phases 1–3 are the routine pass.

### Phase 0: Start from evidence (optional)

The static scan only knows how many terms a note has. The retrieval log knows what you actually searched for and failed to find. This phase reads the log (`Resources/Retrieval Log.md`) for queries with a partial or failed outcome, or that had to be reformulated, and triages each one:

- **Indexing fix** — the right note exists but its terms miss the query's angle. Enrich it, citing the real query as evidence.
- **Content gap** — no note answers. Enrichment changes metadata, not content, so this goes to capture instead.
- **Not actionable** — the gap is about a missing tool or feature, not retrieval.

Each processed entry is recorded in a ledger (`Resources/Vault Health/Retrieval Gaps Processed.jsonl`) so the next run does not repeat it. The triage is judgment, not mechanics: in the reference vault, 8 of the first 9 failed queries were content gaps, not indexing misses.

### Phase 1: Diagnose

Run a diagnostic scan across the vault. The scan produces:

- **Distribution of search terms per note** — Identify notes below threshold (fewer than 3 specific, resolvable terms; hubs and unpaged terms don't count)
- **Term audit** — For a given note, which terms resolve, which are broken links, which domains are orphans
- **Crowding report** — Terms with too many notes, ranked by severity and tagged by tier
- **Domain registry** — Active domains and orphan domains (domains referenced in notes but not in the registry). Orphans are reported, never silently mapped
- **Split orphans** — Notes that carry a hub term but none of its children

The diagnosis tells you where to focus. Don't enrich everything at once — start with the most impactful gaps.

### Phase 2: Propose

Generate candidate changes for each identified gap:

- New search terms for under-indexed notes (Layer 1). Each candidate is resolved against the existing vocabulary before it is written: an alias maps to its canonical term, a near match needs a judgment call, a hub is replaced by one of its children, and a free term is coined only if at least 2 notes justify it and it gets a page
- Sub-term splits for saturated terms (Layer 2)

Every proposal includes a rationale: why this term, why this split.

### Phase 3: Apply

Write the changes to note metadata:

- Add search terms and secondary domains to frontmatter, without duplicates
- Timestamp the enrichment (`enriched: <date>`)
- Clear a note's `needs_enrichment` flag once it reaches the threshold; leave it set if the note is still below
- Persist a report of all changes in `Resources/Vault Health/Enrichment Reports/`, and append the session's token cost to `Resources/Vault Health/Enrich Cost Log.jsonl`

**Where the human is in the loop.** Search terms are generated by the AI and written directly; the safeguards on that path are mechanical. The writer refuses protected fields (`layer`, `confidence`, `maturity`, `times_retrieved`, and the visual fields of design references), refuses terms that have no page unless explicitly allowed, and refuses to add a hub term from a domain the note does not declare. Your explicit approval is required for the decisions that change the taxonomy: splitting a crowded term, coining a domain, and anything that would move or merge notes.

What to check when you review a split:

- Does the split create sub-terms I'd recognize? (Not academic categories I'd never use)
- Would I actually search for each sub-term? (Not how someone else might search)

### Phase 4: Typed Connections (optional)

When you ask to improve the graph's signal, a separate pass scans untyped Permanent Note → Permanent Note pairs, classifies each relationship, and appends a `## Typed Connections` section with sentence-first entries (at most 6 per note). It is not part of Phase 3, and it does not run on its own.

---

## Cadence

Enrichment is maintenance, not a one-time operation. Recommended cadence:

| Vault size | Cadence | Focus |
|---|---|---|
| < 200 notes | Quarterly | Layer 1 only (search terms) |
| 200–500 notes | Monthly | Layers 1–2 (terms + decompression) |
| 500–1,000 notes | Biweekly | All three layers |
| 1,000+ notes | Weekly | Rotating focus by domain |

The cadence should increase after large ingestion events (processing a new book, batch-importing notes from a course, migrating from another tool).

---

## What Enrichment Is Not

**It's not reorganization.** Enrichment doesn't move notes, change titles, merge duplicates, or restructure folders. Those are separate operations with different risk profiles.

**It's not content editing.** The core insight, evidence, and argument in a note are never touched. Enrichment operates exclusively on metadata and connection layers.

**It's not unguarded tagging.** The AI generates the terms, but each one has to pass the quality test, resolve to an existing page or earn a new one, and get past the writer's guards. Without those checks, automated enrichment tends toward plausible but unused terms.

**It's not a substitute for good capture.** If notes are captured with poor structure or unclear insights, enrichment can make them more findable — but it can't make them more useful. Quality at capture is a prerequisite.

---

## Measuring Impact

**Retrieval success rate:** After enrichment, the queries triaged as indexing fixes should now succeed. Track before/after for those queries; content gaps will not move, and should not be expected to.

**Search term distribution:** Measure specific, resolvable terms, not raw strings. The distribution should shift from bimodal (many notes with 1–2 terms, few with 6+) toward most notes at 4–6, with none below 3.

**Crowding reduction:** Saturated terms should drop below threshold after splitting. Track the number of red terms (above 20 notes for flat terms).

**Graph signal ratio:** The share of claim edges that are neither `mentions` nor `cites` (frontmatter edges excluded) should increase over time, and should not sit below 15%. That 15% floor is autolink's own warning on typed links; the eval scorecard's ≥ 20% green band is a separate check, so a vault can clear one and still miss the other.

---

## Related

- [Retrieval Decay](retrieval-decay.md) — The core problem that Layer 1 solves
- [Term Saturation](term-saturation.md) — The core problem that Layer 2 solves
- [Knowledge Graph Signal vs. Noise](knowledge-graph-signal-noise.md) — The core problem that Layer 3 solves
