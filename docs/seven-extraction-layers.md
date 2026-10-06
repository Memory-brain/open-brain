---
module: module-2-extraction
related_skills:
  - open-brain-extract
  - open-brain-synthesize
  - open-brain-health
last_updated: 2026-10-06
---

# The Seven Extraction Layers: What a Source Contains, and Why Layers Stopped Being Slots

Most knowledge workers extract from sources in roughly the same way: they capture what seems important, save quotable passages, note core concepts, and summarize key arguments. They extract what the source *says*. What they almost never extract is what the source *shows you how to do*, what failure modes it identifies, what decisions it makes explicit, or what structural representations it offers for thinking differently about a domain.

The seven layers below name those kinds of content. They remain a useful map of what a good source contains, and of what extraction tends to skip. But they have a history in this system worth telling plainly. Extraction was once organized around them: every note had to be assigned to exactly one layer, and a source was "complete" when every layer had notes. That design was retired, because it produced wrong labels and filler notes. Extraction now writes notes freely and tags them afterwards with multi-label features, and the layer taxonomy survives in one place — the `layer:` field on Permanent Notes.

This document describes the seven layers, why single-layer slotting failed, what replaced it, and where the layers still do work.

---

## The Core Problem with Single-Kind Extraction

The default extraction behavior is heavily weighted toward Layer 1 (knowledge) and occasionally Layer 2 (compression). These are the easiest layers to extract because they correspond to what the source is explicitly saying. The author wrote the concept down; you copy or rephrase it.

The problem is not that knowledge extraction is wrong. It is that knowledge without the other layers is inert. You can accumulate a large knowledge base — hundreds of notes on hundreds of concepts — and still be unable to make better decisions, recognize failure modes faster, or apply frameworks to novel situations. The knowledge is there. It doesn't activate.

The layers that complete knowledge and make it actionable — mental models (how to think), applications (when it actually worked), artifacts (ready-to-use tools), decisions (when to use what), and diagnoses (what goes wrong) — are present in most high-quality sources. They are present as examples, footnotes, caveats, case studies, and cautionary tales. They are rarely the headline content, and that is why they get missed.

---

## The Seven Layers

The numbering is historical; it is not an order of importance or a sequence to work through.

### Layer 1 — Knowledge

**What it captures:** Foundational facts, core concepts, definitions, frameworks, and explicit claims. What the source is saying.

**What it enables:** Reference material, conceptual vocabulary, the ability to recognize and describe ideas in the domain.

**The risk:** Knowledge without the other layers is inert. You know the concept but can't use it. The note becomes a reference you consult but never act from.

**Example:** A source on product pricing theory yields notes on price anchoring, willingness-to-pay estimation, and the psychology of round numbers. All correct. All Layer 1. Without Layer 4 (how these were applied in a specific pricing decision) or Layer 6 (when anchoring backfires vs. when it works), the knowledge is hard to apply with confidence.

### Layer 2 — Compression

**What it captures:** The 20% that captures 80% of the value. Irreducible principles, rules of thumb, and heuristics that a practitioner could carry in their head and use under time pressure. Not summaries — distillations.

**The test for compression:** Could you explain this to someone in 3 minutes and leave them with something genuinely useful? If you need 15 minutes to convey the core insight, you haven't compressed it yet.

**What it enables:** Fast recall in conversation and under pressure. Teaching. The compression layer is what allows you to actually use knowledge in real-time, rather than needing to re-read notes before each application.

**The risk:** Knowledge without compression is difficult to use under pressure. The note exists but takes too long to access and deploy.

**Example:** A 400-page book on organizational design compresses to roughly five principles that experienced practitioners actually carry in their heads. The book contains all the evidence, case studies, and nuance. The compression layer contains what they'd tell a junior colleague in the hallway.

### Layer 3 — Mental Models

**What it captures:** Spatial and structural representations of how ideas relate. Cause-effect chains, matrices, spectra, feedback loops, forcing functions. Not what the source says — how the source thinks.

**What it enables:** Cross-domain transfer and pattern recognition. A mental model is more valuable than content because it applies beyond the specific topic it was extracted from.

**The risk:** Mental models are often implicit in a source — visible in how the author reasons rather than stated as "here is the model." Readers who extract only explicit claims miss the models entirely.

**Example:** A source on software architecture contains an explicit discussion of coupling and cohesion in codebases. But the underlying mental model — that components with high interdependence should be close together, and components that change independently should be separated — applies to organizational design, team structure, curriculum sequencing, and supply chains. If you extract the model, you gain a thinking tool that works across domains. If you extract only the software-specific claims, you get a fact about code.

**Example from strategy:** A source on competitive positioning doesn't just say "differentiate from competitors." The mental model embedded in the argument is a two-by-two: commoditization risk increases as products become more substitutable, and escape requires either moving up the value chain or owning a customer relationship competitors can't access. That model applies to careers, to partnerships, and to platform strategies. The source may never state it as a matrix. You have to extract the structure from the prose.

### Layer 4 — Application

**What it captures:** Named case studies, concrete implementations, specific companies or projects where the concept was applied in real conditions. Not abstract examples — actual instances with names, outcomes, and conditions.

**What it enables:** Grounding abstract concepts in reality. The evidence layer for arguments you'll need to make later. The ability to say "this worked for Spotify when they did X" rather than "theoretically, this approach should work."

**The risk if skipped:** Case studies and examples feel like "mere illustrations" during extraction — supporting material rather than core content. They are not. They are the proof that the concept works, the evidence of the conditions under which it succeeds and fails, and the story that makes the concept memorable and communicable. Sources that provide named applications are rarer and more valuable than sources that only discuss concepts abstractly, and those applications are among the most actionable things you can extract.

**Example:** A source on feedback loops in product development discusses the concept abstractly and then provides a detailed account of how a specific company shortened their feedback loop from quarterly reviews to weekly deployments. The abstract concept is Layer 1. The named implementation — the specific company, what they changed, what happened — is Layer 4. Someone who needs to make a case for shorter feedback cycles in their own organization needs Layer 4 to be persuasive, not Layer 1.

### Layer 5 — Artifact

**What it captures:** Reusable tools, templates, formats, processes, checklists, canvases, decision matrices. Things you can use immediately without re-reading the source.

**The defining transformation:** A process described in prose becomes an artifact when rendered as a checklist. A framework becomes an artifact when rendered as a canvas. An evaluation method becomes an artifact when rendered as a scoring rubric. The conversion requires effort that most readers don't perform — and that effort is precisely why artifacts are rare in note-taking systems and extraordinarily valuable when they exist.

**What it enables:** Immediate practical use. The artifact layer transforms the vault from a reference library into a toolkit. A source that was processed down to a usable template stays in active use for years after the reading. A source that was processed only for knowledge claims is consulted once and forgotten.

**Example:** A book on conducting customer interviews contains chapters explaining the importance of non-leading questions, the value of silence, and the failure mode of asking about hypothetical preferences rather than past behavior. All of this is Layer 1. But embedded in the discussion are the ingredients of a specific interview protocol: opening questions to build rapport, a core set of past-behavior questions, follow-up probes for unpacking motivation, and closing questions to invite referrals. The artifact is the interview guide — a one-page format you can use the day after reading, without re-reading the book.

### Layer 6 — Decision

**What it captures:** Explicit criteria for choosing between alternatives. When to use approach A versus approach B. Under what conditions is one framework better suited than another? What trade-offs does each path carry, and which trade-off profile matches which situation?

**What it enables:** Faster, better-reasoned decisions in practice. Without the decision layer, the vault contains knowledge about multiple competing approaches but provides no guidance on choosing between them. With it, the vault becomes a decision support system rather than a reference library.

**The risk if skipped:** Decision criteria are rarely stated as the main argument in a source. They appear in caveats ("this approach works well when X, but falls apart when Y"), in footnotes, in comparative discussions, and in the "limitations" sections that most readers skim. A reader focused on capturing the main claims misses the boundary conditions that tell you when those claims apply.

**Example:** A source on organizational restructuring argues for cross-functional teams over functional departments. Layer 1 extraction captures the argument and its supporting evidence. Layer 6 extraction captures the conditions under which the argument holds — company size, rate of product change, geographic distribution, existing culture — and the conditions under which functional departments outperform cross-functional teams. The decision layer is what allows you to use the source in a specific situation rather than applying the recommendation universally and incorrectly.

**Example from product development:** A source on A/B testing contains both advocacy for running tests and a discussion of when testing is the wrong approach (markets too small for significance, changes too coupled to test independently, strategic decisions where data can't reduce uncertainty). The Layer 6 extraction captures the decision tree: use A/B testing when X, use qualitative research when Y, use judgment when Z. This is directly actionable in a way the advocacy layer is not.

### Layer 7 — Diagnosis

**What it captures:** Anti-patterns, failure modes, warning signs, and common mistakes. What the source says not to do, and more importantly, why certain approaches fail in specific conditions.

**What it enables:** Pattern-matching against failure before it happens. Error prevention in real time. Retrospective analysis when something has already gone wrong. The diagnosis layer turns the vault into an early warning system.

**The risk if skipped:** Failure mode descriptions are systematically underweighted by readers because success patterns feel more important and more actionable. This intuition is wrong. In practice, most errors are well-documented in the literature — someone has already made this mistake and written about it. Sources that describe failure modes are rarer than sources that describe success patterns, and they are often more valuable because the failure mode is what you are most likely to encounter.

**Example:** A source on product positioning describes a strong positioning framework in Layers 1 and 2. The same source contains a section on the five most common positioning failures: competing on features in a market where buyers don't evaluate features; repositioning without changing the product; targeting an audience too broad to develop compelling messaging; using jargon the buyer doesn't recognize; and making claims competitors have already made first. This Layer 7 content is more immediately actionable for most practitioners than the success framework, because the failure modes describe exactly what their current positioning probably looks like.

**Example from management:** Sources on performance feedback almost universally describe the failure mode of delayed feedback — waiting for quarterly reviews to deliver information the employee needed three months earlier. This failure mode is documented exhaustively. A manager who extracts Layer 7 from these sources builds a personal early-warning system: when they notice they are avoiding a conversation, the diagnosis layer fires and prompts an intervention before the delay becomes costly.

---

## Layer Summary

| Layer | What it captures | What it enables | Most commonly skipped? | Closest extraction feature today |
|---|---|---|---|---|
| Knowledge | Facts, concepts, frameworks | Reference, conceptual vocabulary | Rarely | `factual` |
| Compression | Irreducible principles, heuristics | Fast recall, teaching, real-time use | Sometimes | none — compression happens at promotion, not extraction |
| Mental Models | Structural representations, cause-effect chains | Transfer, pattern recognition across domains | Often | `conceptual` |
| Application | Named cases, concrete examples with conditions | Grounding, evidence for arguments | Often | `application` |
| Artifact | Reusable tools, templates, processes | Immediate practical use, toolkit | Frequently | `code-artifact` |
| Decision | Criteria for choosing between alternatives | Decision support, boundary conditions | Frequently | `decision` |
| Diagnosis | Failure modes, anti-patterns, warning signs | Error prevention, retrospective analysis | Very frequently | `diagnosis` |

The mapping is loose on purpose: a literature note can carry several features at once, while a Permanent Note carries exactly one `layer`.

---

## Why the Kinds of Content Compound

The kinds of content are not independent — they produce their full value in combination.

A mental model without applications is untested speculation. You don't know if the model actually maps to how the world works until you see named instances where it predicted correctly.

An application without the underlying concept can't be adapted. You can replicate what the case study did, but you can't modify it intelligently when your conditions differ.

A decision criterion without the companion diagnosis of when it fails is overconfident. Knowing when to use approach A means nothing without knowing the failure mode that catches practitioners who use it incorrectly.

A compressed principle without the knowledge it distills is decontextualized. You lose the ability to explain it or defend it when challenged.

This is why the layers are worth knowing. It is not a reason to demand all seven from every source: many good sources simply do not contain an artifact or a decision rule, and that absence is a fact about the source.

---

## Why Single-Layer Slotting Was Retired

The original extraction design asked a question before every note: *which one of the seven layers is this?* Two things went wrong.

**The labels were unreliable.** Real insights rarely belong to one kind. A named case that reveals a failure mode is both an application and a diagnosis; a checklist that encodes a choice is both an artifact and a decision. Forcing one label meant picking arbitrarily, and the labels could not be trusted: in the reference vault, single-layer classification had 29% metadata accuracy.

**The slots created filler.** Once every source was expected to fill all seven layers, an empty layer looked like unfinished work. Coverage reports pointed at the empty slots, and notes got written to occupy them rather than because the source had something to say there. In the reference vault, one coverage-driven batch produced 10 such notes to fill empty layers; 9 of them were never retrieved afterwards. A note written to fill a slot costs maintenance forever and returns nothing.

The rule that came out of this: **never create a note to fill a slot. A gap in the coverage table is information about the source, not a task.**

---

## What Replaced It

Extraction (open-brain-extract) now works in three moves:

1. **Sweep for the content that gets missed.** Before writing, the source is read in full and explicitly swept for the categories readers skip: named cases, operational techniques, templates and canvases, trade-offs, anti-patterns and failure modes, moments of identity or narrative, and cross-domain implications. This is where the spirit of the layers lives on — as a search list, not a quota.
2. **Write freely, one idea per note.** Each insight becomes its own note, without being forced into a category first.
3. **Tag afterwards with features.** Each note gets zero, one or several of six features: `factual`, `conceptual`, `application`, `decision`, `diagnosis`, `code-artifact`. The same features are detected in the source, and a coverage audit compares the two.

The audit is where the old intuition behind the layers remains useful. A source with detected practical features (applications, decisions, diagnoses, artifacts) that appear in zero notes has been skimmed, not extracted, and the extractor looks again. But "look again" means finding content the source actually has. Before reporting, every cautionary or practical insight in the source is enumerated and accounted for, one by one, as either captured (naming the note) or discarded (with a reason). What the source does not contain is reported as a gap and left empty.

---

## Where the Layers Still Live

The layer taxonomy survives on **Permanent Notes**, where it is applied once, deliberately, at promotion time, to a note whose idea is already settled. Every Permanent Note carries a required `layer:` field, and the vocabulary has grown to nine values: the seven above (`knowledge`, `compression`, `mental-model`, `application`, `artifact`, `decision`, `diagnosis`) plus `coaching` and `practice`, the kinds of content the learning skills produce (open-brain-improve builds diagnosis, coaching and practice for a topic).

On Permanent Notes the label is useful because it describes distilled knowledge, not raw extraction:

- **open-brain-synthesize** reports layer coverage per domain, with its gaps, as part of the domain report and competency map. A domain with many mental models and no diagnoses tells you what kind of thinking it still lacks.
- **open-brain-health** checks that every Permanent Note has a `layer`, and surfaces layer gaps as maintenance findings.

A layer gap at the domain level is a reason to look for sources or practice that would fill it. It is never a reason to go back to an already-extracted source and write a note into the empty slot.

---

## The Most Common Extraction Failure: The Knowledge-Only Trap

The most frequent pattern in knowledge management systems is a large collection of conceptual and factual notes — concepts, summaries, quotations — with very few applications, almost no artifacts, sparse decision criteria, and almost no diagnoses.

The collection feels substantive because it is large. The individual notes feel valuable because the concepts are real. But the system as a whole doesn't make its owner a faster or better decision-maker, because the content that connects knowledge to action is absent.

Correcting this is not primarily about reading more sources, and it is not about filling empty layers. It is about extracting better the first time: sweeping each source for the practical content it really contains, and accounting for every cautionary and practical insight before calling the extraction done.

---

## Relationship to Other Documents

How extraction fits into the full pipeline is described in [The Extraction Pipeline: Ingest → Extract → Index](extraction-pipeline.md). The failure mode of a knowledge collection that is large but not actionable is described in [The Literature Note Graveyard](literature-note-graveyard.md). The decomposition of complex ideas into atomic notes that can be individually cross-linked and reused is described in [Atomic Note Decomposition: Getting the Granularity Right](atomic-note-decomposition.md). The specific danger of re-reading as a substitute for extraction is described in [The Re-reading Trap: When Your Notes Fail as References](re-reading-trap.md).
