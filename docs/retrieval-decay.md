---
module: module-1-enrichment
related_skills:
  - open-brain-enrich
  - open-brain-retrieve
last_updated: 2026-10-06
---

# Retrieval Decay in Knowledge Vaults

## The Problem

You wrote a note six months ago about a concept you understood well. Today, you need that note — but your search comes up empty. The note still exists. Your search query is reasonable. Yet the vault fails to surface it.

This is **retrieval decay**: the progressive loss of findability that affects knowledge vaults as they grow. It's not a storage problem — it's a discoverability problem.

Retrieval decay is the silent failure mode of every personal knowledge management system. It doesn't announce itself. You don't notice the notes you're not finding. You just gradually stop trusting the vault and start Googling things you already know you wrote down.

---

## Why It Happens

Retrieval decay has three root causes, and they compound each other:

### 1. Vocabulary drift

The way you think about a concept changes over time. Six months ago you wrote about "medication adherence." Today you search for "treatment compliance." Same concept, different framing. The note was indexed with the old vocabulary; your search uses the new one.

This is especially common in fast-moving domains like medicine, AI, or design — where terminology shifts quarterly.

### 2. Single-angle indexing

Most notes are indexed by what they're *about* — the topic, the concept name. But when you search, you often come from a *problem* angle ("how do I keep students engaged?") or an *inverse* angle ("what makes a class tune out?"). If the note only has the concept name as its search term, it misses these lateral approaches.

A note titled "Retrieval Practice in the Classroom" might be exactly what you need when you search for "why do students forget everything a week after the exam" — but without problem-angle search terms, it won't surface.

### 3. Metadata stagnation

Search terms are typically set when the note is created and never updated. But the vault around the note changes: new domains emerge, new connections form, the note's role in your thinking evolves. The metadata becomes a snapshot of how you thought about the note on day one — not how you'd search for it today.

---

## How to Detect It

Retrieval decay is measurable. The diagnostic signals are:

**Specific search terms per note.** Count only the terms that can actually discriminate: terms that resolve to a page in `Search Terms/` and are not hubs (a term that already has child terms, or a Domain). A broad parent term or a string with no page behind it adds no entry point. The floor is **3 specific, resolvable terms** per note; below it, the note is enrichment backlog. Extraction aims higher, at 4–6, covering the concept name, the problem it addresses, and at least one lateral angle.

**Retrieval frequency distribution.** If 80% of your retrievals hit the same 20% of notes, the rest of your vault is decaying. The "long tail" notes — often the most valuable because they hold non-obvious insights — are being buried.

**Failed and reformulated queries.** Log every retrieval with its outcome (success, partial, failure) and whether you had to reformulate. A rising failure rate is a signal worth reading, but it is not decay on its own. Each failure has to be triaged:

- **Indexing fix** — the note that should have answered exists, but its search terms miss the angle of the query. This is retrieval decay, and enrichment fixes it.
- **Content gap** — no note answers the question. No amount of metadata will help; the vault needs new material.
- **Not actionable** — the "gap" is about a missing tool or feature, not about retrieval.

In the reference vault, the first triage of real failed queries found that 8 of 9 were content gaps, not indexing misses. The same query failing twice or more within two weeks usually means a content gap too. Treat a failed search as evidence to classify, not as proof that the index has decayed.

---

## How to Fix It

The fix is **search term enrichment** — a systematic process of adding alternative entry points to existing notes.

### Enrichment strategies

**Problem-angle terms.** For every note, ask: "What problem would someone be trying to solve when they need this note?" A note about "Test-Driven Development" should also be findable via "how to refactor without fear" or "why the same bugs keep coming back."

**Inverse-angle terms.** What's the opposite or the thing to avoid? A note about "Progressive Disclosure in UI" should surface when searching for "information overload in long forms" or "cognitive load in complex interfaces."

**Domain-crossing terms.** Some notes are relevant to domains beyond the one they were created in. A note about "Spaced Repetition" lives in learning theory but is equally relevant to language learning, habit formation, and medical training. Adding cross-domain terms prevents siloing.

**Synonym consolidation.** If your vault uses both "myocardial infarction" and "heart attack" for the same concept, pick a canonical term and add aliases. Enrichment adds the alias — it doesn't rename the original.

### The process

0. **Start from evidence (optional)** — Read the retrieval log for failed or reformulated queries, triage each one as above, and enrich only the indexing fixes, citing the real query as the reason
1. **Diagnose** — Scan for notes below the threshold (fewer than 3 specific, resolvable terms), audit for broken term links and orphan domains, check term crowding, and find notes left without a child term after a split
2. **Propose** — Generate candidate terms using the strategies above, then resolve each one against the existing vocabulary: an alias maps to its canonical term, a hub is swapped for one of its children, and a genuinely new term is coined only if at least 2 notes justify it and it gets its own page
3. **Apply** — Write the terms, timestamp the enrichment, and report the changes. Mechanical guards refuse unpaged terms and protected fields; splitting a crowded term still needs your approval
4. **Type connections (optional)** — Add typed connections between Permanent Notes when you want to improve the graph's signal (see [Knowledge Graph Signal vs. Noise](knowledge-graph-signal-noise.md))

This is a maintenance operation, not a one-time fix. A healthy vault runs enrichment periodically — monthly or after a significant batch of new notes.

---

## The Compounding Effect

Retrieval decay compounds. Every unfound note is a missed connection — a link that should have been made, an insight that should have informed a decision. Over time, the vault splits into two populations: the "popular" notes that get found and linked frequently, and the "buried" notes that accumulate dust.

Enrichment reverses this. Each added search term is a new pathway into the note. Over time, enriched notes get found more often, which leads to more connections, which increases their visibility further. The compounding works in your favor — but only if you invest in the maintenance.

---

## Related

- [Term Saturation](term-saturation.md) — The inverse problem: when a search term is *too* findable
- [The Enrichment Pattern](enrichment-pattern.md) — The systematic process for solving retrieval decay
- [Knowledge Graph Signal vs. Noise](knowledge-graph-signal-noise.md) — How typed connections extend enrichment beyond search terms
