# Steps 1–5 — Empty stub, Source Index, scan, insight sweep, features and duplicates

> The options for an empty Inbox stub, the Source Index check, the scope scan, the sweep for commonly-missed categories, structural feature detection, domain and search-term assignment, and the duplicate check. Read it when in doubt in any of Steps 1–5.

---

For empty shells, stop and present options to the user:

> "This source has no processable content yet: **[Source]** — only an empty stub in Inbox/.
>
> Options:
> **A) Expert synthesis** — I generate Literature Notes from my own knowledge of the book. Useful, but they don't reflect your reading.
> **B) Wait** — bring me your highlights or notes first.
>
> Which one?"

---

## Step 1: Source Index Check

Read `Resources/Source Index.md`. Find the row for this source.

- `vault_coverage: complete` → do NOT reprocess. Offer a second pass on practical/critical features if thin.
- `vault_coverage: partial-features` → second-pass mode: extract missing feature categories.
- `vault_coverage: partial` → resume where extraction left off.
- `vault_coverage: inbox-only` → process from scratch.
- Source not in index → add a row in Step 9.

---

## Step 2: Scan and Scope

Read the full source (markitdown cache + evidence bundle if available). Before extracting, answer internally:
- What domain? (from `Domains/` — do NOT invent new ones)
- What type? (theory, methodology, case study, research, how-to)
- What is the author's core argument?
- Who is the intended audience?
- Is this a book (long-form, merits tier assessment) or short-form?
- **If bundle available**: does the TOC match your reading? Are there sections you'd otherwise skip?

---

## Step 3: Identify Every Note-Worthy Insight

One Literature Note = one insight. Standard for "worth extracting":
- Changes how the user might think about something
- Provides evidence for/against an existing idea
- Introduces a framework or model worth remembering
- Is a specific principle or heuristic, not just a fact

**Scan explicitly for these commonly-missed categories** (the scanner prompt — this is what prevents extraction from only capturing theory):

- **Named case studies** (companies, projects, experiments)
- **Operational techniques** (interview scripts, observation protocols, scoring systems, workshop formats, canvas)
- **Templates / Canvas** (reusable visual or structural tools)
- **Trade-off discussions** ("when to use X vs Y", criteria matrices)
- **Anti-patterns and failure modes** (what NOT to do and WHY)
- **Identity moments** (passages linking behavior to identity)
- **Narrative moments** (stories with protagonist, tension, outcome) — memory anchors
- **Cross-domain implications** (insight applies beyond source's primary domain) → flag with secondary domain
- **Vault claim touched (internal, not written in the LN)** — while extracting each insight, note mentally which vault claim (LN, PN, documented practice, hypothesis) it affects and how: reinforces / qualifies / weakens / contradicts / adds benchmark / connects threads / creates question / none. This is raw material for the Step 10 Epistemic Delta; do not write it into the LN.

If the source is a business book and zero case studies, zero templates, zero trade-offs, zero anti-patterns were identified — only theory was extracted. Go back.

**Figure coverage check (bundle sources only):** If the evidence bundle reports ≥ 3 figures and zero are referenced across all extracted LNs (no Visual Reference sections, no figure mentions in Evidence fields), flag as a gap. Key figures in a paper are almost always note-worthy — either as standalone LNs or as evidence supporting other insights.

---

## Step 3.5: Structural Feature Detection (deterministic pre-scan)

Before extracting notes, scan the source text for structural features. This is a deterministic checklist — no judgment needed, just pattern matching:

| Feature | Signal to detect |
|---------|-----------------|
| `code-artifact` | Code blocks, code references, file paths, command-line examples, schema definitions |
| `diagnosis` | Negation/warning language: "don't", "avoid", "NOT for", "anti-pattern", "gotcha", "mistake", "failure" |
| `application` | Step-by-step lists, numbered sequences, how-to procedures, named case studies with implementation details |
| `decision` | Conditional/trade-off language: "if X then Y", "when to use", "vs", comparison tables, selection criteria |
| `factual` | Quantitative data, specific numbers, measurements, empirical results, statistics |
| `conceptual` | Metaphors, analogies, compressed principles, mental models, frameworks, "think of it as" |

Record detected features as a checklist. This checklist drives the Feature Coverage Audit in Step 7 — if the source contains code blocks but no note references code, something was missed.

**Why this phase exists**: the retired 7-layer system forced every note into exactly one category, which had poor metadata accuracy and created filler notes. Feature detection separates the scanner function (don't miss practical insights) from the classification function (label what a note contains). The scanner works; forced single-label classification doesn't.

---

## Step 4: Domain and Feature Assignment

For each candidate insight, assign:

**Features** (multi-label — a note can have zero, one, or many):
- `code-artifact` — contains or references code, templates, schemas, reusable tools
- `diagnosis` — describes anti-patterns, failure modes, what NOT to do
- `application` — practical how-to, case study, implementation guide
- `decision` — trade-off framework, selection criteria, when-to-use guidance
- `factual` — quantitative data, empirical evidence, specific measurements
- `conceptual` — mental model, compressed principle, analogy, framework

A note about a "cost control checklist with specific dollar amounts and a failure example" would get: `code-artifact`, `factual`, `diagnosis`, `application`. This is fine — multi-label captures what the note actually contains.

**Domain** — check the `Domains/` folder. Use an existing domain. If truly novel, STOP and ask the user before creating a new one.

**Search terms (4–6 per note, highest-leverage field in the whole system):**

Think: *what would the user type 6 months from now?* Include:
- Primary concept name
- Synonyms and adjacent concepts
- Domains where the idea applies
- The problem it solves (not just the solution)

A note about "segmenting by job vs. demographics" must have: `[[Jobs To Be Done]]`, `[[Market Segmentation]]`, `[[Customer Discovery]]`, `[[Positioning]]`, `[[User Research]]` — not just `[[Jobs To Be Done]]`.

---

## Step 5: Duplicate Check

Before writing each note, scan `Literature Notes/` for the same insight from another source.

- Same insight from another source → DO write the new LN (it's a new data point), AND flag it as a **convergence candidate** for `open-brain-promote` in the final report.
- Insight already captured as a Permanent Note → the new LN becomes supporting evidence. Reference the PN in the connectors callout.

Never skip the duplicate check — cross-source convergence is the raw signal for PN promotion.

When the convergence is real, also mark the direction: the new material *reinforces*, *qualifies* or *contradicts* the existing note. That mark is direct input to the Step 10 Epistemic Delta.

---
