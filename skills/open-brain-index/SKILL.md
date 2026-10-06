---
name: open-brain-index
description: 'Creates Source Outlines inside Dossier notes. Compressed representation of a book that eliminates
  the need to reload the original PDF. Triggers: index this book, create the outline, source outline, open-brain index'
metadata:
  folded_from_top_level:
    version: 9.2.0
  version: 9.2.0
  status: canonical
  consumes:
  - The source's text cache, already extracted (Resources/Extracted Text/)
  - The book tier already assessed (TOP/INTERESTING) by open-brain-extract
  - An existing Dossier (or the need to create one) to append the outline to
  produces:
  - A Source Outline appended inside the Dossier note
  - A chapter-by-chapter map (exhaustive mode) or a minimal summary (interesting mode)
  - Extraction status by feature and reprocessing notes for future sessions
---

# Open Brain — Index

Index is the long-term memory layer of the learning system. Transform a book that has been read and analyzed into a permanent, compressed representation — a **Source Outline** — that lives inside the Dossier note in the vault and eliminates the need to reload the original source in future sessions. A Source Outline is not a summary: it is a structured knowledge map dense enough to support future extraction, retrieval, and convergence detection without reading the original again.

---

## INPUT CONTRACT (verify before Step 0)

Paths are relative to the vault root, `$OPEN_BRAIN_VAULT`.

| Precondition | How to verify | If missing |
|---|---|---|
| **Source text cache exists** at `Resources/Extracted Text/{source-slug}.md` (or `.txt`) | File exists and mtime > source mtime | If the source is still in context from `open-brain-extract`, run markitdown to create the cache (see below). Do NOT read the binary a second time. |
| **Tier assessed** (TOP or INTERESTING) | Check the `open-brain-extract` report in the conversation OR ask the user | Run `open-brain-extract` first, or confirm tier explicitly |
| **Source not already outlined** for the requested chapters | Read Dossier at `Dossiers/[Title].md` | If exists, move to append mode (Step 0) |

**Double-read guard**: NEVER read the original PDF/epub if `Resources/Extracted Text/{source-slug}.md` (or `.txt`) exists and is current. The cache file is authoritative for this session.

**MarkItDown for cache creation**: When creating the text cache from a PDF/DOCX/PPTX, use `markitdown` (pip: `markitdown[pdf]`) instead of manual text extraction. It preserves headings, tables, and lists as structured Markdown. Run:
```bash
pip install 'markitdown[pdf]' --break-system-packages  # first time only
markitdown "/path/to/source.pdf" -o "$OPEN_BRAIN_VAULT/Resources/Extracted Text/{source-slug}.md"
```
Save with `.md` extension. If markitdown fails (scanned PDF, no text layer), fall back to page-image reading.

---

## When to Run

- **TOP tier book**: Run immediately, while the PDF is still in context (most token-efficient). Generate an exhaustive outline. `open-brain-extract` invokes this skill automatically for TOP sources.
- **INTERESTING tier book**: Run when the user explicitly requests it, or when a future session needs context from this book. Generate a minimal outline.
- **Updating an existing outline**: When a book was processed in multiple sessions (different chapters), update the existing outline rather than creating from scratch. Always append — never overwrite unprocessed sections.

---

## Step 0: Check for Existing Outline

**Location:** Source Outlines live **inside the Dossier note** in `Dossiers/`, not as separate files in `Resources/Source Outlines/`. Append to the Dossier; do not create a new file.

Check:
```
Dossiers/[Title].md    ← read the ## Source Outline section if it exists
```

Legacy path (older vaults only), readable for reference: `Resources/Source Outlines/[source-id] Outline.md` — but do NOT write there.

- If it exists: read it, identify which chapters are already covered, and update only the new sections.
- If it doesn't exist: create from scratch following the appropriate mode below.

The source-id follows the format: `[Author Last Name] [Year]` (e.g., `Clark Mayer 2016`, `Scott 2019`).

---

## Step 1: Determine Mode

Check the Book Tier from the `open-brain-extract` output in context, or ask the user if unclear.

- **TOP** → proceed to TOP Mode
- **INTERESTING** → proceed to INTERESTING Mode

---

## TOP Mode: Exhaustive Outline

For books with tier TOP (score ≥9/12). Goal: capture enough detail that future extraction sessions never need the original PDF.

### TOP Outline Structure

```markdown
---
source_id: [Author Last Name Year]
title: [Full title]
author: [Author name(s)]
type: source-outline
tier: top
tier_score: [X/12]
date_indexed: [YYYY-MM-DD]
chapters_covered: [list of chapter numbers/names]
chapters_pending: [list of chapters not yet processed, or "none"]
last_updated: [YYYY-MM-DD]
---

# Source Outline: [Title]

## Book-Level Summary
[3-5 sentences: core thesis, author's main argument, intended audience, what makes this book distinct from others in the domain.]

## Author's Core Framework
[The single most important conceptual structure the author introduces. Name it, describe its components, explain how they relate. Use a table if the framework has multiple dimensions.]

## Concept Map
[All key terms the author introduces, grouped by relationship. Format:
- **[Term]**: [Plain-language definition in 1-2 sentences. How the author uses it specifically — may differ from common usage.]
Include 15-30 terms for a full book.]

## Chapter-by-Chapter Map

### Chapter [N]: [Title]
- **Central claim**: [1-2 sentences — what is the author arguing or teaching in this chapter?]
- **Key concepts introduced**: [bullet list of new terms or frameworks first appearing here]
- **Critical evidence**: [specific data, studies, experiments, or cases cited. Include numbers where relevant.]
- **Operational content**: [scripts, checklists, protocols, exercises — if any. Describe enough to reconstruct without the book.]
- **Memorable narrative**: [If the chapter contains a key story or case, 2-3 sentences capturing protagonist, tension, outcome.]
- **Connections to other chapters**: [What does this chapter set up? What does it depend on from earlier?]
- **Gaps / not yet extracted**: [Aspects of this chapter not yet turned into Literature Notes — signals what future extraction should target.]

[Repeat for each chapter]

## Cross-Domain Signals
[Insights from this book that clearly apply beyond its primary domain. Format:
- **[Insight]** → applies to [domain] because [reason]
These are the high-value convergence candidates for open-brain-promote.]

## Extraction Status
[Literature Notes from this source, counted by `features` — the same multi-label set `open-brain-extract` tags. A note with several features counts once in each row, so the column does not sum to the LN total; state that total separately. "Pending" = insights of that feature identified in the chapter map but not yet extracted.]

**Literature Notes created**: N (prefix `[XX]`)

| Feature | Notes Created | Notes Pending |
|---------|--------------|---------------|
| factual | X | Y |
| conceptual | X | Y |
| application | X | Y |
| decision | X | Y |
| diagnosis | X | Y |
| code-artifact | X | Y |

## Reprocessing Notes
[Anything future-Claude should know before running another extraction session on this book. Known gaps, sections worth revisiting, chapters that were skimmed vs. read carefully.]
```

---

## INTERESTING Mode: Minimal Outline

For books with tier INTERESTING (score 5-8/12). Goal: fast orientation for future sessions — enough context to decide whether to extract more.

### INTERESTING Outline Structure

```markdown
---
source_id: [Author Last Name Year]
title: [Full title]
author: [Author name(s)]
type: source-outline
tier: interesting
tier_score: [X/12]
date_indexed: [YYYY-MM-DD]
chapters_covered: [list]
chapters_pending: [list or "none"]
last_updated: [YYYY-MM-DD]
---

# Source Outline: [Title]

## Core Thesis
[3-5 sentences: what does the book argue, what problem does it solve, what's the main takeaway?]

## Key Concepts (5-8 max)
- **[Concept]**: [1 sentence definition]

## Chapter Map
| Chapter | Central Claim (1 line) | Extraction Priority |
|---------|----------------------|---------------------|
| [N]: [Title] | [one-line claim] | high / medium / low |

Extraction priority: high = rich content, extract first; medium = useful but not urgent; low = mostly context/background.

## Strongest Extraction Candidates
[2-4 bullet points identifying where the most valuable Literature Notes would come from, and which `features` they'd likely carry (factual, conceptual, application, decision, diagnosis, code-artifact).]

## Reprocessing Notes
[What to know before running another session: known gaps, chapters skimmed, anything that might surprise.]
```

---

## Step 2: Write the Outline

Write the full outline following the appropriate mode. Use only information that is verifiably in the source — do not infer or extend the author's claims.

For TOP Mode: be exhaustive on the chapter map. Sparse chapter maps defeat the purpose.
For INTERESTING Mode: be ruthlessly selective. If tempted to write more, cut instead.

---

## Step 3: Save the Outline

**Merge into the Dossier; do NOT create a separate file.**

Target: `Dossiers/[Title].md`. Procedure:

1. If the Dossier exists: append the outline content under a `## Source Outline` heading at the end of the body (after existing sections). Add the outline's frontmatter fields (`tier`, `tier_score`, `date_indexed`, `chapters_covered`, `chapters_pending`, `last_updated`) to the Dossier's own frontmatter — merge, don't overwrite.
2. If the Dossier does NOT exist: create it using `Templates/Dossier.md` (or, if your vault has no such template, a note with `type: dossier`, `title`, `author` and `created` in its frontmatter), fill the metadata, then add the `## Source Outline` section with the generated outline body.
3. Never write to `Resources/Source Outlines/` — that legacy folder is read-only.

If updating an existing outline:
- Update `last_updated` in the Dossier's frontmatter
- Update `chapters_covered` and `chapters_pending`
- Add new chapter entries to the Chapter Map under `## Source Outline`
- Update the Extraction Status table by feature (TOP mode) — recount from the source's LNs (`ln_prefix`) rather than adding by hand
- Append to Reprocessing Notes, don't overwrite

---

## Step 4: Report

```
## ✅ Source Outline Created — [Title]

**Tier**: [TOP / INTERESTING] ([X/12])
**Mode**: [Exhaustive / Minimal]
**Chapters covered**: [list]
**Chapters pending**: [list or "none"]
**Saved to**: Dossiers/[Title].md (## Source Outline section)

**What this enables**: In future sessions, load the Outline instead of the PDF. Token cost: ~[estimated tokens] vs. ~[PDF tokens]. Reduction: ~[X]%.

**Next step**: [If chapters pending → "Load chapters [N-M] in a new session to complete the outline." | If complete → "Outline is complete. Future extractions can use this file as primary source."]
```

---

## Key Principles

**The Outline replaces the PDF, not supplements it.** If a future session would still need the PDF to answer a question, the Outline is incomplete. Test by asking: "Could I run open-brain-extract from this Outline alone?" For TOP mode, the answer must be yes.

**Chapters pending are not failures.** Books are often processed across multiple sessions. The Outline is designed to be updated incrementally. A partial Outline is still useful.

**Never invent content.** If a chapter wasn't read, mark it as pending. Don't synthesize or interpolate what a chapter "probably" contains.

**TOP mode is worth the cost.** A TOP book will be referenced 5-10 times in the vault's life. Paying ~1000 tokens now to create the Outline saves 50,000+ tokens over the vault's lifetime.
