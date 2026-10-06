---
module: module-2-extraction
related_skills:
  - open-brain-retrieve
  - open-brain-extract
  - open-brain-promote
last_updated: 2026-10-06
---

# The Autonomous Research Loop: Filling Knowledge Gaps Without Reading Everything

## What It Is

You've identified a gap in your knowledge base: your notes on experiment design are thin, and an upcoming project requires you to reason carefully about sample sizes and significance thresholds. The traditional response is to find a book, read it over several weeks, and take notes. That works, but it's slow — and it produces many notes when what you actually need is a handful of high-quality answers to specific questions.

The **Autonomous Research Loop** is an alternative: a structured practice that investigates a specific topic through multiple rounds of web search, evaluates what it finds against your existing knowledge, and integrates only the genuinely new and well-supported findings — not as a summary dump, but as atomic notes properly connected to what you already know.

The design principle that makes it work: **every research round should produce fewer notes than the one before**. The first round maps the territory broadly; subsequent rounds go narrow and specific. The final output is not a comprehensive summary of everything that exists on the topic — it's the minimum set of high-quality notes that genuinely fill the gap you started with. A three-round research loop that produces four notes is a success. A three-round loop that produces fifteen notes is a sign that quality criteria were not applied.

None of the shipped skills runs this loop end to end; it is a practice you run with an AI assistant and a web search tool, using the shipped skills for the vault-facing steps: retrieval for the pre-flight, extraction conventions for the notes it writes, and promotion for anything that might become permanent. The parameters below are the ones that have held up in practice.

---

## The Phases

### Phase 1: Pre-flight

Before searching anywhere external, query your own knowledge base. This step is non-optional and frequently skipped.

Start with the vault's hot cache (the short list of active threads, if you keep one), then run an exploratory retrieval query on the gap. The goal of pre-flight is to establish what you actually know versus what you think you know about the topic. You may discover you have half of what you need and only need a quick single round. You may discover that your existing notes are outdated and the gap is wider than expected. Either finding changes how you run the subsequent search rounds.

Pre-flight produces three outputs:
- A statement of the specific gap: not "I need to know about statistics" but "I need to understand how to determine minimum detectable effect before running an experiment"
- A count of existing relevant notes, with their current maturity level
- A brief that fixes the run: a quick single round (3–5 sources) or the full loop (3 rounds, 8–12 sources); the angle to research; the output (Literature Notes only, or Literature Notes plus Permanent Note candidates); and the domain. Absent a reason to do otherwise, run the full loop with Permanent Note candidates.

If existing notes cover 70% or more of the question, stop here. If an existing note is missing a connection that would have surfaced the answer, add it, and consider the gap addressed. A research run that produces no notes is a successful pre-flight.

### Phase 2: Iterative Rounds

Each round has a distinct objective. Running all three rounds on the same question with the same approach is redundant. Running the wrong round first wastes effort.

**Round 1 — Broad scan:** Map the territory. Run 2–3 searches using different phrasings of the same question — not synonyms, but genuinely different framings (e.g., the practitioner's framing vs. the academic framing vs. the "how do I do this" framing) — then fetch the top 3–4 sources, preferring academic over practitioner over news over opinion. The goal is to identify the 3-4 central claims that appear across multiple sources. These repeated claims are the strongest candidates for notes.

During Round 1, track: evidence quality (empirical data vs. opinion vs. anecdote), contradictions with your existing knowledge, and the specific sub-questions that weren't answered. The unanswered sub-questions become Round 2's targets.

Stop Round 1 when: you're seeing the same claims repeated without new substance, or you have 3-4 strong note candidates.

**Round 2 — Gap filling:** Target what Round 1 didn't cover. If Round 1 found theory but no practical cases, search for cases specifically. If it found general principles but no domain-specific application, search for that application. The objective is not more coverage — it's the specific type of evidence that's missing.

Round 2 should be shorter than Round 1. If Round 2 keeps generating new questions and new note candidates, you may be researching a topic too broad for a single loop. Break it into two separate research questions.

**Round 3 — Synthesis prep:** Stop adding new sources. Instead, look at what you have from Round 1 and Round 2 and ask: do these findings contradict each other? If so, which has better evidence? Do any findings align with specific notes in your existing knowledge base, confirming them? Are there convergences — different sources arriving at the same conclusion from different angles — that deserve their own note as a "multiply-confirmed principle"?

Round 3 may produce zero new note candidates and one synthesis note. That's the correct output.

### Phase 3: Adversarial Quality Gate

Before writing any note, every candidate from Rounds 1 and 2 must pass a deletion test: **if this note were deleted, would any retrieval, convergence or connection be lost?** If nothing would be lost, the note is not written. Three questions help answer it:

**Is it novel?** Compare against existing vault coverage. A finding that only confirms something you already have in a mature note doesn't need to become a new note.

**Is the evidence sufficient?** Distinguish between: empirical research, practitioner consensus, single expert opinion, and unattributed assertion. Label the evidence type in the note. Speculation is not an acceptable evidence type for a research note, and a claim supported by a single source is marked `confidence: low`.

**Would it change how you act?** A note that's interesting but changes nothing about how you approach decisions is a collector's note — it feels like knowledge but functions as reading history.

Candidates that fail the gate are not created. The loop also never overwrites existing notes: it may add a connection to an existing note, or flag a `[!contradiction]` where a finding conflicts with one, and leave the decision to you.

### Phase 4: Integration

The surviving findings enter the vault the same way any source does:

- **Web-sourced Literature Notes** carry a `WEB -` prefix, so a health check can spot a vault leaning too heavily on web sources.
- **Permanent Note proposals** go through the four-part convergence test used for promotion (multiple sources, different framings, specific enough to act on, a concrete counterfactual). They are proposed, never written directly.
- **A trace of the run**: an Inbox note recording the research session (topic and date), the source index updated with what was read, and the hot cache updated if the gap belonged to an active thread.
- **An activation step that blocks closing the run**: before the session ends, you answer what the findings change for you. As with extraction, your extension of a note is what allows it to be promoted later.

---

## The Process

| Stage | Goal | Searches | Notes typically produced |
|---|---|---|---|
| Pre-flight | Vault gap assessment | 0 (internal query only) | 0 — gap statement and run decision |
| Round 1 | Territory map | 2–3 (then fetch 3–4 sources) | 2–4 candidates |
| Round 2 | Gap filling | 2–3 | 1–3 candidates |
| Round 3 | Synthesis prep | 1–2 targeted | 0–1 synthesis candidate |
| Quality gate | Candidate screening | 0 | Final note set (aim for 4–8; never more than 8 unless you ask) |

A complete three-round loop with quality gate and integration takes 45-90 minutes. A pre-flight that cancels the loop takes 10-15 minutes and is always worth running first.

---

## Cadence

Run a research loop when:

- A vault health check identifies a domain where note coverage is below threshold relative to its importance in your gap map
- A retrieval query returns no relevant results, even after trying multiple search angles
- You're preparing work that requires reasoning about a topic and realize mid-way that your existing notes don't cover the question you're actually asking
- A synthesis session reveals a claim you're making that has no supporting notes in the vault

Do not run research loops on a fixed schedule. The trigger should be a specific gap, not a calendar reminder. A research loop without a defined gap question produces unfocused reading, which is exactly what the methodology is designed to avoid.

---

## What It Is Not

**Not a substitute for deep reading.** The research loop is efficient for filling specific gaps. It is not the right tool for developing genuine expertise in a new domain. If you're starting from scratch in a field, read a book — the research loop assumes you have enough existing knowledge to evaluate sources critically. Without that foundation, you can't apply the quality gate.

**Not AI summarization.** Asking a language model to summarize a topic and saving the summary as a note is not a research loop. The research loop requires you to evaluate sources, compare claims, and make decisions about what earns a place in your vault. A saved summary is not a note — it's an excerpt. It doesn't connect to your existing knowledge, doesn't carry evidence quality labels, and can't be updated as your understanding evolves.

**Not content research.** If you're looking for material to cite in a blog post, that's a different workflow. The research loop builds knowledge into your vault for your future reasoning. It is not optimized for producing citable sources or quotable content.

---

## Measuring Impact

Track these signals after implementing the methodology:

**Coverage rate in targeted domains.** Before and after a research loop, assess whether the specific gap question can now be answered from vault notes alone. A loop that fills the stated gap is a success regardless of how many notes it produced.

**Cross-link rate of new notes.** New notes that connect to two or more existing notes are better integrated than isolated ones. A high cross-link rate means the research loop is adding to your knowledge network, not just adding to your note count.

**Quality gate rejection rate.** If 80% of your Round 1 candidates are passing the quality gate, your criteria are probably too loose. A healthy rejection rate is 40-60% — meaning roughly half the things that look interesting in the first pass don't actually earn a note once scrutinized.

**Time to answer.** After a research loop, measure how long it takes to answer the original gap question from your vault. If the answer is still slow or uncertain, the loop identified topics but didn't resolve the question.

---

## Related

- [Reactive Knowledge Accumulation](reactive-knowledge-accumulation.md) — the problem this methodology addresses
- [Domain Blindness](domain-blindness.md) — how to detect the gaps that make research loops necessary
- [The Extraction Pipeline](extraction-pipeline.md) — how findings from research loops move into permanent notes
