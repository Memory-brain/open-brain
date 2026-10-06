---
module: module-2-extraction
related_skills:
  - open-brain-ingest
  - open-brain-extract
last_updated: 2026-10-06
---

# Source Overwhelm: The Unprocessed Inbox Problem

## The Problem

You have a folder of 20 PDFs you meant to process. A Kindle library with 5 books you finished but never converted to notes. Thirty browser tabs saved to Instapaper or Readwise. You know the material is valuable. You keep adding to the pile. Nothing gets extracted.

This is **source overwhelm**: the state where your capture rate permanently outpaces your processing rate, and the gap between "saved" and "understood" keeps widening. The pile doesn't feel like a problem until you notice you haven't actually produced a single note in three weeks — and the queue is longer than when you started.

Tiago Forte's CODE method (Capture, Organize, Distill, Express) put the importance of systematic capture on the map. The problem it described was real: knowledge workers were losing things they'd read, failing to connect insights across sources, and starting from scratch on topics they'd already studied. Source overwhelm is what happens in the other direction — when capture runs without the extraction engine that should follow it. Forte's contribution made the inbox necessary; this document addresses what happens when the inbox is all you build.

The trap is subtle because capturing feels productive. You found something worth reading. You saved it. The system registered an action. But saving is not learning, and an unprocessed source is not knowledge — it's a promise you haven't kept yet. A knowledge system full of unprocessed sources is not a knowledge system. It's an anxiety system.

---

## Why It Happens

### The capture reflex

Saving is frictionless. Most modern tools make it a single click: save to Notion, highlight in Kindle, clip to Readwise. The effort required to capture is so low that there's no natural check on accumulation. Processing a source, by contrast, requires 30 minutes to 2 hours of focused work. The asymmetry is structural — capture will always be faster than processing unless you deliberately throttle capture.

### The all-or-nothing fallacy

Many people unconsciously treat "processing a source" as synonymous with "reading it completely and carefully." A 300-page book feels like it requires a 300-page investment before you can extract anything from it. This is false, but the feeling is real — and it causes paralysis. If you can't do the source justice right now, you defer it. The book goes back to the pile. The pile grows.

### No triage system

Without a triage layer, every source carries equal weight. A landmark book that will define your thinking gets treated the same as a blog post you found mildly interesting. When everything is equally important, nothing gets prioritized, and the queue becomes an undifferentiated mass that's impossible to approach systematically.

---

## How to Detect It

| Signal | Measurement |
|---|---|
| Queue age | How many days since your oldest unprocessed capture? More than 14 days is a warning sign. More than 30 is a structural problem. |
| Extraction rate | What percentage of sources captured in the last 30 days were converted into at least one note? Below 20% indicates an overwhelm pattern. |
| Guilt signal | Do you feel anxious when you open your reading app? Do you avoid looking at your saved items? Emotional avoidance is a reliable indicator. |
| Re-capture rate | How often do you re-save something you already saved? This indicates the original capture never became usable knowledge. |

---

## How to Fix It

The fix is not to process faster — it's to decide deliberately what to keep and what earns extraction.

**Step 1: Separate the two triage decisions**

There are two different questions, and they are answered at two different moments.

*At capture: how much of the original do I keep?* Every captured source gets a preservation tier. It decides only how much raw text is stored, not whether you will extract from it:

| Tier | What it looks like | What is preserved |
|---|---|---|
| TOP | Will reference multiple times; core to a domain you actively work in | The full raw text (or the PDF already on disk, linked) |
| INTERESTING | Worth a pass; relevant but not foundational | Key extracts and highlights, plus the link |
| SKIP | Interesting in the moment but not domain-relevant | The link plus a short paragraph of context |

This decision should take under 60 seconds. It is independent of how good you think the source is: a brilliant source you will never need verbatim can be SKIP for preservation.

Capture also runs a novelty check against the vault. A source that scores as novel (≥0.6) goes in normally; a confirmation (0.3–0.6) shows you the notes it overlaps with; a likely duplicate (<0.3) shows you the closest existing note and asks whether it is already covered. The check advises and never blocks — you can always override it, and the override is recorded.

*At extraction: is this source worth notes at all?* Before any extraction, an admission gate scores the source on four criteria, 1–3 each: originality, density, contribution to *your* vault (checked by running the retrieval engine on the source's central claim — if several of the top results already say the same thing, contribution is low) and evidence. Scoring uses the abstract, table of contents, headings and a skim, not a full read:

| Score (/12) | Verdict | Extraction commitment |
|---|---|---|
| ≥ 9 | TOP | Full extraction into atomic notes, then a full source outline |
| 5–8 | INTERESTING | Full extraction into atomic notes; a minimal outline only if you ask for one |
| ≤ 4 | REJECT | No notes at all — not a partial extraction, not "the best three" |

A redundancy veto overrides the sum: a source that scores lowest on both originality and contribution is rejected whatever its total. A rejected source is not deleted: it is logged in `Resources/Rejected Sources.jsonl`, and its Inbox note is kept and marked `vault_coverage: rejected`. You can override the verdict in either direction, and the log records that you did and why.

The gate also watches itself. If ten sources in a row are admitted (score ≥5), it says so in the extraction report: a gate that never rejects may have stopped discriminating. The warning prompts a review of the threshold; it does not change anything by itself.

**Step 2: Decouple extraction depth from reading depth**

A TOP-tier book does not require a complete re-read before extraction. Extracting a 300-page book should take 45–90 minutes, and about 1.5–2.5 hours including ingest and indexing, not 8. This is possible because extraction targets specific things — claims, frameworks, principles, failure modes — not comprehensive coverage. You are not summarizing the book. You are mining it for the ideas that survive compression.

**Step 3: Process what is ready first, and close the rest explicitly**

Work the queue in order of readiness rather than guilt: sources whose full text you already have on disk first, then those you can fetch, then the ones closest to what you are actively working on, and only then the oldest. A source that has sat for weeks without reaching the front of that order is a candidate for the admission gate, not for deletion: score it, and if it does not earn notes, reject it on the record. A logged rejection clears the false obligation and keeps the trail; a deleted source leaves no trace of why it was dropped.

---

## Related

- [Atomic Note Decomposition: Getting the Granularity Right](atomic-note-decomposition.md) — once you start extracting, this problem hits next
- [The Re-reading Trap: When Your Notes Fail as References](re-reading-trap.md) — what happens when extraction is incomplete
- [The Extraction Pipeline: Ingest → Extract → Index](extraction-pipeline.md) — the full system that prevents overwhelm from recurring
- [Where Open Brain Fits in the PKM Landscape](pkm-genealogy.md) — Forte's CODE/PARA contribution and where Open Brain diverges
