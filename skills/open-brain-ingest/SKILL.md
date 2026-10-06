---
name: open-brain-ingest
description: 'Entry gate of the vault: captures raw content from any source (Notion, URL, text, PDF, conversation) and creates the structured Obsidian note it calls for — Inbox, Case, Fleeting, Evergreen or Design Reference — with its triage, preservation tier, SurpriseFilter and wiring to Mentors/Search Terms/Books. It archives and catalogs the source; it does NOT pull notes out of it — that is open-brain-extract. Triggers: capture this, add to the vault, migrate this, save to Obsidian, put it in the Inbox, import from Notion, open-brain ingest.'
metadata:
  folded_from_top_level:
    version: 1.8.3
  version: 1.9.0
  status: canonical
  changelog: references/CHANGELOG.md
  requires_engine:
  - name: project_router.py
    version: unpinned
  - name: surprise.py
    version: unpinned
  consumes:
  - Raw content from any source (Notion, URL, text, PDF, conversation)
  - A triage decision on which note type it is (Inbox/Case/Fleeting/Evergreen/Design Reference)
  - A SurpriseFilter evaluation of how novel the content is
  produces:
  - Correctly structured Obsidian notes (Inbox, Case, REF/PAT, etc.)
  - Support notes created or linked (Mentors, Search Terms, Books) with bidirectional wiring
  - A seed note in Ideas/ when a Case could produce publishable content
  handoffs:
  - skill: open-brain-extract
    when: after capturing content in the Inbox, to extract insights as Literature Notes (the Capture phase
      of the CODE method followed by Extract)
    requires_approval: true
---
# Open Brain — Ingest

Ingest is the entry gate of the knowledge system. Take raw content from any source — Notion pages, URLs, text, PDFs, conversations — and create properly structured Obsidian notes in the vault following the vault specification. This handles the **Capture** phase of the CODE method. Do NOT extract insights or create Literature Notes here — that is `open-brain-extract`.

The vault root is `$OPEN_BRAIN_VAULT`; engine scripts live under `$OPEN_BRAIN_ENGINES`. All folder paths below are relative to the vault root.

**References in `references/`: loaded when the step asks, never before.** One invocation resolves **one** note type — read that file and no other. `note-inbox.md` when triage says Inbox · `note-case.md` when triage says Case (carries Step 6.5) · `notes-design-reference.md` when triage says REF or PAT (carries Step 5.5) · `support-notes.md` when a Mentor / Search Term / Book note must be created, or a mentor photo is involved · `surprisefilter.md` when the band is not green, the batch passes ~15 items, or a type's eligibility is unclear · `project-routing.md` when the source is a research report, the router answers anything but `high`, or you need to configure where projects live · `skill-sequence.md` when the content arrives chained from another skill · `notion-and-batch.md` only for a Notion migration or a batch import · `vault-spec.md` when in doubt about folder, `type`, `features`, the 11 critical rules, or which field points where · `CHANGELOG.md` for the version history.

---

## Step 0: Triage — What Type of Note Is This?

Run this decision tree before creating anything.

**Question 1: Who authored this content?**

| Author | Next question |
|--------|--------------|
| Someone else (article, book, video, podcast, tool) | → **Inbox** |
| The user (the vault owner) | → Go to Question 2 |

**Question 2: What kind of user-authored content is it?**

| Content type | Note type | Folder | Key signal |
|-------------|-----------|--------|------------|
| Real experience with situation, results, and learnings | **Case** | `Cases/` | The user did something, observed outcomes, drew conclusions |
| Quick thought, idea, or thing to investigate | **Fleeting Note** | `Fleeting Notes/` | Raw, unpolished |
| Polished, publishable content ready for an audience | **Evergreen** | `Evergreen/` | Finished guide, blog post draft, playbook meant to be shared publicly |
| External content to capture and process later | **Inbox** | `Inbox/` | From someone else's brain |

**Common trap**: When the user shares a link to an internal doc they authored (framework, operating model, process design), it is almost certainly a **Case** or **Evergreen**, not Inbox. Ask: "Did the user live this experience and learn from it?" If yes → Case. "Is this polished and ready to publish?" If yes → Evergreen.

**Question 3: Is this visual/design content?**

If the content is a screenshot, UI pattern, visual reference, design example, or annotated interface — regardless of author — evaluate:

| Content type | Note type | Folder | Prefix | Key signal |
|-------------|-----------|--------|--------|------------|
| Specific example from a real product, book, or interface | **Design Reference** | `Design References/` | `REF —` | Screenshot or annotated example from an existing product/book. Has a specific source. |
| Abstract reusable visual pattern (matrix, contrast, scorecard, etc.) | **Visual Pattern** | `Design References/` | `PAT —` | Describes a form that can be applied to multiple topics. No single source — it's a template. |
| Neither of the above | Route back to Question 1/2 | — | — | Not visual-first content |

**When ambiguous between REF and PAT**: REF has a specific product/book source and shows "how someone else did it." PAT has no single source and describes "a reusable shape for ideas." If a pattern was extracted FROM a reference, create both: the REF (with the image) and the PAT (with the abstract form).

**When ambiguous: ASK the user.** Say: "This looks like it could be a Case (your real experience) or an Inbox capture. Which fits better?"

---

## Step 0.5: Tier the Source (Inbox only) — RAW Preservation Strategy

Once triage decides this is Inbox (external content), tier the source before capturing. The tier decides how much of the original to preserve.

| Tier | What it looks like | RAW strategy |
|------|--------------------|--------------|
| **TOP** | Foundational source: book chapter, landmark essay, deep technical doc, a source the user will cite or reprocess. High likelihood of revisiting. | Save full RAW text in `Inbox/Raw/<title>.md` (or `.txt` for very long docs). Inbox note links to the RAW file. Link to original URL also kept. |
| **INTERESTING** | Solid article, podcast transcript, useful thread. Worth keeping highlights but not the whole text. | Save key extracts / highlights in the Inbox note body, plus the URL. |
| **SKIP** | Light reference, quick capture, secondary source. The user may never reread the original. | URL + 1 short paragraph of context in the Inbox note. No RAW. |

When the tier is genuinely ambiguous, ASK the user.

**Books and PDFs**: when the user provides a PDF already on disk, link to it via `link:` and skip the RAW copy — the PDF itself IS the RAW. Mark the Inbox note with `raw_strategy: pdf-on-disk`.

**Tier is independent of `rating`**: rating is about quality, tier is about preservation strategy.

Add to Inbox frontmatter:
```yaml
tier: top | interesting | skip
raw_strategy: full | highlights | link-only | pdf-on-disk
raw_path: "Inbox/Raw/[title].md"   # only if raw_strategy: full
```

---

## Step 0.7: SurpriseFilter — Novelty Check (mandatory for Inbox and Cases)

Before creating any note, evaluate whether this content brings genuinely new knowledge to the vault. Runs for **Inbox** and **Case** notes only — skip Fleeting Notes, Design References, and Mentor/Search Term/Book support notes.

```bash
cd "$OPEN_BRAIN_ENGINES/autolink"
python3 surprise.py evaluate \
    --title "<proposed note title>" \
    --terms "<comma-separated search terms>" \
    --mentor "<author name>" \
    --type inbox
```

| Band | Score | Action |
|------|-------|--------|
| 🟢 **Novel** | ≥0.6 | Proceed with normal ingestion |
| 🟡 **Confirmation** | 0.3–0.6 | Show the user the overlapping notes; ask whether to create anyway or link from the existing ones |
| 🔴 **Duplicate** | <0.3 | Show the user the most similar note; ask whether this is already covered |

Every Inbox and Case note created after the evaluation carries `novelty_score: 0.XXX` and `novelty_band: novel | confirmation | duplicate-override` in its frontmatter. **The user can ALWAYS override — the filter advises, it never blocks**; an override is written into the band so the system remembers the decision. In a batch, run the filter once per item and present one summary table at the end instead of asking item by item — and **every ~15 items, re-read the triage criterion in one sentence before continuing**: in a long batch it holds at the start and dilutes towards the end.

Literal wording of the two questions, the batch summary format and the rationale for the mid-batch reminder: `references/surprisefilter.md`.

---

## Step 0.8: Project Routing (Cases, Output Content, and Research Reports)

If Step 0 decided this is a **Case**, any **output/deliverable** (plan, audit, roadmap, design doc, presentation, spec, etc.), or an **Inbox note originating from a deep-research run**, run the project router. **Does NOT apply to**: regular Inbox notes, Fleeting Notes, Design References, Mentors, Search Terms, Books. If your vault has no project folders, skip this step.

```bash
python3 "$OPEN_BRAIN_ENGINES/engine/project_router.py" \
  --vault "$OPEN_BRAIN_VAULT" \
  --query "<title + context + topic of the content being ingested>"
```

| `confidence` | Action |
|---|---|
| `high` | Add `project: "[[Projects/Active/{name}/README]]"` to the note's frontmatter |
| `medium` | Add the field and tell the user: *"I've linked this note to the project {name}. Correct?"* |
| `low` | Ask the user before adding the field |
| `none` (ask_user) | Ask the user which project this belongs to, or whether to create a new one |
| `none` (zettelkasten) | No project field needed — proceed as normal |

**Notes stay in Zettelkasten folders. Only artifacts go to project folders.** A Case lives in `Cases/` with the `project:` link; output artifacts (.pptx, .docx, .html, .pdf) go to `Projects/Active/{name}/Outputs/`; a deep-research report .md goes to `Projects/Active/{name}/Research/` while its Inbox note stays in `Inbox/` with `source_project:`. **Research without a project is an error** — if the source is a deep-research output, read `references/project-routing.md` before acting. That file also explains how to point the router at a different projects folder.

---

## Step 0.9: Trace — `skill_sequence`

Every note created here (Inbox, Case, REF, PAT) carries a `skill_sequence:` field with at least one entry:

```yaml
skill_sequence:
  - skill: open-brain-ingest
    at: "YYYY-MM-DDTHH:MM"
```

If the content already came from another skill in the same session (e.g. a research skill handed over a finding now being ingested), **prepend** that entry instead of starting from scratch. The field triggers nothing, chains nothing and is not maintained by hand: each skill appends its own entry to the list the note already carried. Why it exists (closing the trace loop): `references/skill-sequence.md`.

---

## Step 1: Read the Source

If it's a **PDF/DOCX/PPTX file**: use `markitdown` to convert to structured Markdown before reading. This preserves headings, tables, and lists that raw text extraction destroys.
```bash
pip install 'markitdown[pdf]' --break-system-packages  # first time only
markitdown "/path/to/file.pdf" -o "$OPEN_BRAIN_VAULT/Resources/Extracted Text/{source-slug}.md"
```
Read the generated `.md` file as the source content. If the triage result is Inbox with `raw_strategy: pdf-on-disk`, also keep the original PDF linked via `link:`.

If it's a **Notion page**: fetch the page content. Extract:
- Title
- Database properties (Type, Tags, Rating, Links, Relations)
- Body content (text, highlights, quotes)
- Related items (linked databases, mentions)

If it's a **URL/text/other**: read whatever the user provides. Identify source type, author, and key topics.

---

## Step 2: Map to Vault Schema

**Read only the template file for the type resolved in Step 0.**

| Note type from Step 0 | Template file |
|---|---|
| Inbox | `references/note-inbox.md` |
| Case | `references/note-case.md` |
| Design Reference (`REF —`) or Visual Pattern (`PAT —`) | `references/notes-design-reference.md` |
| Mentor, Search Term, Book (support notes — Step 4) | `references/support-notes.md` |

---

## Step 3: Check for Existing Supporting Notes

Before creating new Mentor, Search Term, or Book notes, check if they already exist:

1. **Search Terms**: Look in `Search Terms/` folder. Also check `aliases` in existing notes — different phrasings of the same concept should converge to one node, not create duplicates.
2. **Mentors**: Look in `Mentors/` folder. Same person = same note, even if name varies slightly.
3. **Books**: Look in `Books/` folder. Check by title and author.

---

## Step 4: Create Missing Supporting Notes — Bidirectional Wiring

Every Mentor must have its books in `key_works`. Every Source/Book must have its author in `author`. If either side is missing the other, the link is unidirectional and the graph view will misleadingly suggest the Mentor has no work attached.

**When creating a Mentor**: include `key_works: [[<source/book just created>]]`.

**When touching an existing Mentor for a new source**: open the Mentor file, append the new `[[Source]]` to `key_works`.

**When creating a Source/Book/Dossier**: `author: [[<mentor>]]` is mandatory. If the author is unknown, use `[[Unknown]]`.

If you cannot decide whether two near-duplicate names are the same person (e.g., "Marty Cagan" vs "Martin Cagan"), STOP and ask the user.

Templates for the three support notes, plus the Mentor photo protocol: `references/support-notes.md`.

---

## Step 5: Create the Inbox Note

Write the note to `Inbox/[Title].md` with:
- Complete frontmatter following the schema
- Body containing all raw captured content
- Wikilinks to all supporting notes (mentors, search terms, books)

For a Design Reference, Step 5.5 — images, interactive assets, and the rule that a REF without an image is reported and never faked — is in `references/notes-design-reference.md`.

---

## Step 6: Report

Tell the user exactly what was created:
- The Inbox note (title, source_type, **tier**, **raw_strategy**, search_terms assigned)
- Any new supporting notes created (mentors, search terms, books)
- Any existing notes linked to
- **Bidirectional links verified**: confirm that Mentor → key_works and Source → author both point at each other
- **Project routing result** (if applicable): which project was assigned, whether the research report was moved to `Projects/Active/{name}/Research/`
- Flag any decisions the user should verify

If a **Case** was just created, close with Step 6.5 — the content-pipeline question and the seed note in `Ideas/`: `references/note-case.md`. If the source was Notion or the ingestion was a batch, the property mapping and the two-pass procedure are in `references/notion-and-batch.md`.

---

## File Naming

- Inbox notes: `Title of the source.md`
- Mentors: `Author Name.md`
- Search Terms: `Concept Name.md`
- Books: `Book Title.md`
- No special characters that break file systems (avoid: / \ : * ? " < > |)

---

## What Not To Do

- Do NOT extract insights or create Literature Notes (that's `open-brain-extract`)
- Do NOT create Permanent Notes (that's `open-brain-promote`)
- Do NOT create Domain Index notes (that's `open-brain-synthesize`)
- Do NOT fabricate Case notes from external content — Cases must reflect the user's real experiences
- Do NOT create Fleeting Notes unless the user explicitly dictates a quick thought to capture
- Do NOT create new Domains without asking the user first
- Do NOT mark `processed: true` on Inbox notes (`open-brain-extract` does that)
- Do NOT default to Inbox without running the Step 0 triage
- Do NOT create Design Reference notes without running the Question 3 triage — not everything visual goes to Design References/
- Do NOT skip Step 0.7 SurpriseFilter for Inbox and Case notes — always evaluate novelty before creating
- Do NOT block ingestion based on SurpriseFilter alone — the user can always override, the filter advises not blocks
