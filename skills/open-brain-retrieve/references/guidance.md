# Output Mode — Guidance Synthesis

> The second output mode: instead of ranked notes, synthesized guidance for the consumer's task. When to use it and the gating rules from the paper (Zhou et al. 2026).

---

## Output Mode: Guidance Synthesis (GS)

Orthogonal to the six intents: any retrieval can return in one of two output modes.

- **notes** (default): the classic output — ranked notes with links, for the user to read and navigate themselves.
- **guidance**: the search agent reads the retrieved notes and writes **task-specific guidance** — synthesized prose telling the consumer exactly what applies to their task and how, with citations. The consumer never sees raw note bodies.

Why this exists: in Zhou et al. 2026, serving synthesized guidance instead of files was the cheapest variant per solved task in both executor tiers, and the advantage grows the weaker the consumer. Raw notes demand a reader strong enough to digest them; guidance protects weaker/cheaper consumers and shortens their episodes.

### When to use guidance mode

1. **Another skill is the consumer** (e.g. `open-brain-escribir`, `open-brain-course`, `open-brain-panel`, or any writing/reporting skill you use): default to guidance. Those skills should receive "here is what the vault says that applies to YOUR task", not a pile of notes to re-read.
2. The user asks for it: "give me guidance for", "guidance mode", "synthesize for this task", "what does the vault tell me for doing X".
3. The user asks a knowledge question conversationally and the answer spans >5 notes — offer guidance mode instead of dumping links.

### Rules (from the paper's gating discipline)

- **Cite only what clearly applies** to the task — not liberally. An entry that "might be related" stays out; precision over recall here.
- Every claim in the guidance carries its wikilink — attribution stays verifiable.
- Guidance is written fresh per task; never cached or reused across tasks.
- Retrieval mechanics stay identical (entry points, intents, rerank, myelination) — only the *output* changes.
- Log it: Retrieval Log entry gets `**Output mode**: guidance`.

---
