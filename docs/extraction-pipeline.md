---
module: module-2-extraction
related_skills:
  - open-brain-ingest
  - open-brain-extract
  - open-brain-index
last_updated: 2026-10-06
---

# The Extraction Pipeline: Ingest → Extract → Index

## What It Is

The extraction pipeline is a three-phase process for turning raw sources — books, articles, PDFs, research papers — into structured, reusable knowledge. Each phase has a distinct purpose, a defined output, and a clear handoff to the next phase.

The pipeline exists because the core problems in knowledge extraction are distinct and require different cognitive modes: deciding what to keep (capture triage), deciding whether a source earns notes and distilling them (admission and extraction), and mapping the source so you never need to reopen it (indexing). Collapsing these operations into a single undifferentiated "reading session" is the root cause of source overwhelm, the re-reading trap, and poorly granulated notes.

The pipeline separates them. The order matters: the source is admitted and extracted first, and the outline is built afterwards, from the full text and with the notes already written.

---

## Phase 1: Ingest — Capture, Triage and Wire

The ingest phase happens at capture time. Its purpose is to file the source correctly and decide how much of the original to keep. It does not extract notes from the source; that is the next phase.

**Note-type triage.** First, ingest decides what kind of note the material becomes: an Inbox note for external content to be processed, a Case for your own experience, a Fleeting note for a passing thought, an Evergreen note, or a design reference or pattern for visual material.

**Preservation tier.** An Inbox source then gets a tier that decides only how much raw text is stored:

| Tier | Criteria | What is preserved |
|---|---|---|
| TOP | Foundational; you'll cite or reprocess it | The full raw text, or the PDF already on disk, linked |
| INTERESTING | Solid and useful, but not foundational | Key extracts and highlights, plus the link |
| SKIP | Light reference or secondary source | The link plus a short paragraph of context |

The tier decision should take under 60 seconds. It is independent of the source's quality rating, and it is not the extraction decision — that comes in Phase 2.

**Novelty check.** Ingest scores the new material against the vault: novel (≥0.6) proceeds normally, a confirmation (0.3–0.6) shows you the overlapping notes, a likely duplicate (<0.3) shows you the closest existing note. The check advises; you can always override it, and the override is recorded on the note.

**Wiring.** Ingest routes the note to a project when one applies, records the chain of skills that touched it (`skill_sequence`), and creates or links the support notes it references — mentors (authors), search terms, books — in both directions.

**What this prevents**: Treating a landmark book and a blog post identically at capture. Storing full text you will never reread. Duplicating material the vault already has without noticing.

---

## Phase 2: Extract — Admit, Then Turn the Source into Atomic Notes

### The admission gate

Before any extraction, the source is scored on four criteria, 1–3 each: originality, density, contribution to *your* vault, and evidence. Contribution is checked against the vault rather than the topic: the retrieval engine is run on the source's central claim, and if three or more of the top ten results already say the same thing, contribution scores 1. Scoring uses the abstract, table of contents, headings and a skim.

| Score (/12) | Verdict | What happens |
|---|---|---|
| ≥ 9 | TOP | Full extraction, then a full source outline (Phase 3) automatically |
| 5–8 | INTERESTING | Full extraction; a minimal outline only if you ask |
| ≤ 4 | REJECT | No notes at all; the source is logged in `Resources/Rejected Sources.jsonl` and its Inbox note is kept, marked `vault_coverage: rejected` |

A source that scores lowest on both originality and contribution is rejected whatever its total. You can override the verdict either way, and the override is logged. If ten sources in a row are admitted, the extraction report warns that the gate may have stopped discriminating.

### Extraction

Extraction distills the source into discrete, reusable knowledge units — Literature Notes, one per insight, written at a granularity that allows each note to be linked, challenged, and synthesized independently. For PDFs and office documents, the text is converted once into a cached Markdown file, which becomes the authoritative text for the rest of the run, alongside an evidence bundle (structure and figure inventory). The binary is not re-read.

Extraction no longer sorts notes into layers (see [The Seven Extraction Layers](seven-extraction-layers.md) for why). Instead it:

1. **Sweeps** the full source for the content readers skip: named cases, operational techniques, templates, trade-offs, anti-patterns and failure modes, identity and narrative moments, cross-domain implications.
2. **Writes freely**, one idea per note. There is no target length per kind of note; the only size rule is that if the body grows past a short paragraph, it gets split.
3. **Tags afterwards** with zero, one or several features — `factual`, `conceptual`, `application`, `decision`, `diagnosis`, `code-artifact` — and audits feature coverage against what was detected in the source.

Every Literature Note follows a **three-voice contract**. The body is the author's voice: a faithful paraphrase with at least one literal quote where the wording matters. The AI's voice is confined to a `[!claude]` callout holding connectors only — links to other notes with one line of reason each, never analysis. Your voice goes in a `## Your extension` section that is created empty; a `voice_state` field records whether you have filled it, and a Literature Note cannot be promoted to a Permanent Note until you have. Each note also gets 4–6 search terms with the context of each, and is checked against existing notes for duplicates: the same insight from another source is still written, and flagged as a convergence that feeds promotion. Author (mentor) notes are linked to the notes they produced, in both directions.

### The quality gates

No single test decides when extraction is done. Several mechanical and judgment gates run in sequence:

- **Lint.** Every batch of notes runs through a linter. BLOCK-level violations (missing description, domain, features or extension section, among others) keep the note out of the vault and are reported as a failed extraction of that insight; WARN-level ones are fixed or accepted and reported.
- **Enumerate, then account.** Before looking at the notes written, every cautionary or practical insight in the source is listed, then each is marked as captured (naming the note) or discarded (with a reason). Nothing drops silently. A gap is reported, never filled with a note written to occupy it.
- **Epistemic delta.** The report states, for each existing claim the source affects, one of nine delta types — reinforces, weakens, qualifies, contradicts, adds a benchmark, adds evidence, connects threads, creates a question, or no delta identified. Weakening, qualifying and contradicting deltas are appended to a review queue for your attention.
- **Reindex and alignment check.** The retrieval engine is reindexed and checked. If it fails, the report says so at the top and the extraction is not considered closed: the new notes are not retrievable yet.
- **The confrontation (careo).** Extraction ends with up to three questions put to you, one at a time: the clash with what you already believe, what to steal from the source's methods, and what to bet on. The AI loads each question with concrete notes and never answers it; your answers are captured verbatim. When you are not present, the questions are queued rather than skipped.

---

## Phase 3: Index — Map the Source So You Never Reopen It

Once a source has been extracted, open-brain-index builds a **source outline**: a structured knowledge map dense enough to support future extraction, retrieval and convergence detection without the original. It runs automatically after extracting a TOP source, and in a minimal mode on request for an INTERESTING one.

A source outline is not a summary. It tells you what's *in* the source and where. A full (TOP) outline contains:

- A book-level summary and the author's core framework
- A concept map of the 15–30 terms the source depends on
- A chapter-by-chapter map: central claim, concepts, evidence, operational content, narrative, connections to the vault, and gaps not yet extracted
- Cross-domain signals
- Extraction status and reprocessing notes

The outline is stored as a `## Source Outline` section inside the source's Dossier note (`Dossiers/[Title].md`). The minimal (INTERESTING) version is deliberately short: enough orientation to decide later whether the source deserves more.

**Why index after extracting**: by the time the outline is written, the source has been read in full, its notes exist, and the outline can record precisely what was captured and what remains. The outline's own test: could you run extraction again from the outline alone, without the original? For a TOP source the answer must be yes. Once it is, you can answer "what did this book say about X?" in under a minute without opening the source.

---

## The Process

| Phase | Input | Output | Time estimate |
|---|---|---|---|
| Ingest | Raw source (URL, PDF, book, article) | A typed note (usually Inbox) with preservation tier, novelty score, routing and support-note wiring | < 5 minutes |
| Extract | Inbox source | Admission score; if admitted, linted atomic notes with features, a coverage audit, an epistemic delta and the confrontation questions; if rejected, a logged rejection | 45–90 minutes (book), 15–30 minutes (article) |
| Index | Extracted TOP source (or INTERESTING, on request) | Source outline inside the Dossier note | 20–45 minutes |

Total time for a TOP-tier book: 1.5–2.5 hours. This is not a full re-read. It is a structured pass with explicit gates, ending in an outline that replaces the source.

---

## Cadence

**Ingest**: At capture time. Never save a source without assigning a preservation tier. The decision costs 60 seconds. Deferring it costs your future attention every time you see the source in your queue.

**Extract**: In dedicated sessions of 60–90 minutes, one source at a time, starting with the admission gate. Do not attempt to extract while reading for the first time — the first read is for comprehension, the extraction session is for distillation.

**Index**: Immediately after extracting a TOP source (it happens automatically), or later for an INTERESTING source when a future session needs its context.

---

## What It Is Not

**Not speed-reading**: The pipeline does not require reading faster. It requires reading with more specific extraction targets. You will likely read some sections more carefully (those covering frameworks and mechanisms) and some sections less carefully (narrative examples, transition sections) than you would in a normal read-through.

**Not highlights collection**: Saving highlights to Readwise or Kindle is not extraction. Highlights capture what the author said. Extraction produces atomic notes about what the ideas mean, in a structure that serves your future thinking rather than the author's narrative — with your own extension added before anything becomes permanent.

**Not AI summarization**: Running a PDF through an AI summarizer produces a compression of the original text. It does not produce the claim-titled, linked, feature-tagged notes that allow future synthesis. Summaries can help you score the admission gate; they are not a substitute for the extraction phase.

**Not a one-time activity**: A source's value to your vault changes as your domains evolve. A source you rejected or extracted lightly two years ago might warrant full extraction now that you're working intensively in that domain. The pipeline can be re-run, and the source outline's reprocessing notes tell you where to start.

---

## Measuring Impact

| Metric | Healthy range | What it indicates |
|---|---|---|
| Extraction rate | > 80% of admitted TOP sources fully extracted within 2 weeks of ingest | Pipeline is keeping up with capture |
| Rejection rate | Not zero over a run of ten sources | The admission gate is still discriminating |
| Re-reading rate | < 2 returns to any processed source per month | Source outlines are doing their job |
| Lint BLOCK rate | Falling over time | Notes are being written to contract the first time |
| Queue age | No unprocessed TOP-tier source older than 30 days | Triage is preventing accumulation |

---

## Related

- [Source Overwhelm: The Unprocessed Inbox Problem](source-overwhelm.md) — what capture triage and the admission gate prevent
- [Atomic Note Decomposition: Getting the Granularity Right](atomic-note-decomposition.md) — the theory behind one idea per note
- [The Seven Extraction Layers](seven-extraction-layers.md) — why extraction tags features instead of assigning layers
- [The Re-reading Trap: When Your Notes Fail as References](re-reading-trap.md) — what the index phase prevents
- [The Maturation Ladder: From Captured to Owned](maturation-ladder.md) — what happens to extraction outputs downstream
