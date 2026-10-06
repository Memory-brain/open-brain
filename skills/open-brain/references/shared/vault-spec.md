# Open Brain — Vault Quick Reference for Skills

This is a condensed reference of the vault specification. Every skill that reads or writes to the vault should follow these rules. The fuller specification ships with the `open-brain-ingest` skill (`references/vault-spec.md`); if the two disagree, that one wins.

## Vault Path
`$OPEN_BRAIN_VAULT` (all folder paths below are relative to it).

## Folder → Note Type Mapping

| Folder | Note Type | `type` value |
|--------|-----------|-------------|
| `Inbox/` | Raw captures | `inbox` |
| `Literature Notes/` | Extracted insights | `literature` |
| `Fleeting Notes/` | Your own ideas | `fleeting` |
| `Permanent Notes/` | Atomic distilled ideas | `permanent` |
| `Evergreen/` | Publishable content | `evergreen` |
| `Domains/` | Domain index notes | `domain-index` |
| `Cases/` | Real experiences | `case` |
| `Mentors/` | Author/thinker MOCs | `mentor` |
| `Search Terms/` | Concept MOCs | `search-term` |
| `Books/` | Book notes | `book` |
| `Areas/` | Life area MOCs | (area) |
| `Resources/` | External assets | (varies) |
| `Design References/` | Visual patterns & design references | `design-reference` or `visual-pattern` |

## Design References — Note Subtypes

`Design References/` contains two note subtypes, each with distinct frontmatter:

### REF — Design References (examples from real products/books)

Prefix: `REF —`. Captures a specific visual example from an existing product, book, or interface.

```yaml
---
type: design-reference
ref_type: pattern | source-example | brand-reference
category: [visual-hierarchy | action-hierarchy | spacing | elevation | color | layout | ...]
product: "Source product or book"
platform: [web | mobile | desktop | print]
sector: [education | saas | ecommerce | ...]
source: "[[Dossiers/Source Name]]"
source_lns:
  - "[[LN link]]"
primary_form: [annotated-example | screenshot | comparison]
visual_goal: [guide attention | clarify decisions | show hierarchy | ...]
cognitive_mode:
  - [compare | decide | notice | explain | persuade]
pattern_family: [de-emphasis | action-hierarchy | spacing | elevation | ...]
why_i_like_it: "One sentence — why you saved this"
interactive_asset: "Design References/Assets/filename.html"   # optional — HTML/CSS/JS prototype
tags: [...]
related_principles:
  - "[[LN link]]"
date_captured: YYYY-MM-DD
---
```

Body structure (canonical template):

```markdown
# {{title}}

## Visual reference
![[Resources/Images/Source/filename.png]]

## Problem it solves
Describe the concrete visual failure this reference helps fix.
Do not just say it "looks good"; explain which confusion, noise, weak
hierarchy, loss of legibility or lack of memorability it corrects.

## Visual mechanism
Explain how it works: spacing, contrast, weight, position, repetition,
color, crop, hierarchy, rhythm, metaphor, format or composition.
This section must be able to teach the pattern without the image.

## How to detect it in your own work
Turn the pattern into a diagnosis: which symptom appears when it is missing,
which quick test reveals it, and how you know you should apply
this pattern.

## Step-by-step application
1. First concrete move.
2. Second concrete move.
3. Third concrete move.
4. Visual check.

## Transfer to outputs
Explain how to use it in slides, carousels, annotated screenshots,
matrices, scorecards, visual posts or interfaces. Avoid generic answers;
name a concrete output situation.

## Anti-patterns
* Typical mistake 1.
* Typical mistake 2.
* Typical mistake 3.

## Reusable rule
One operational sentence you can remember while designing.

## Tests
* Test 1.
* Test 2.
* Test 3.
```

### PAT — Visual Patterns (reusable abstract patterns)

Prefix: `PAT —`. Captures an abstract, reusable visual form independent of any product.

```yaml
---
type: visual-pattern
ref_type: pattern | source-example | brand-reference
category: [matrix | slide | radar | contrast | ladder | scorecard | ...]
pattern_family: [2x2 | claim-proof | contrast | radar | ladder | ...]
primary_form: [matrix | framework | radar | annotated-example | ...]
visual_goal: [explain tradeoffs | persuade with one message | compare options | ...]
cognitive_mode:
  - [compare | decide | explain | persuade]
emotional_tone:
  - [clarity | confidence | urgency | curiosity | ...]
density: [low | medium | high]
text_to_visual_ratio: [0.0 - 1.0]
reuse_score: [1-5]
output_targets:
  - [social-carousel | keynote-slide | obsidian-canvas | executive-memo | ...]
interactive_asset: "Design References/Assets/filename.html"   # optional — HTML/CSS/JS prototype
linked_pns:
  - "[[PN link]]"
date_captured: YYYY-MM-DD
---
```

Body structure (canonical template — same as REF):

```markdown
# {{title}}

## Visual reference
![[path/to/asset.png]]
(PAT notes may omit this if the pattern is abstract)

## Problem it solves
Which concrete visual failure this pattern solves.

## Visual mechanism
How it works: spacing, contrast, weight, composition, rhythm, etc.
It must teach the pattern without the image.

## How to detect it in your own work
Which symptom appears when it is missing. Which quick test reveals it.

## Step-by-step application
1. First concrete move.
2. Second concrete move.
3. Third concrete move.
4. Visual check.

## Transfer to outputs
How to use it in slides, carousels, annotated screenshots, matrices,
scorecards, visual posts or interfaces. Name a concrete situation.

## Anti-patterns
* Typical mistake 1.
* Typical mistake 2.
* Typical mistake 3.

## Reusable rule
One operational sentence you can remember while designing.

## Tests
* Test 1.
* Test 2.
* Test 3.
```

### Visual Assets

Image assets live in `Resources/Images/` organized by source (e.g., `Resources/Images/Refactoring UI/`). Design reference notes embed them with Obsidian syntax: `![[Resources/Images/Source/filename.png]]`.

Interactive assets (HTML/CSS/JS prototypes) live in `Design References/Assets/` and are referenced via the `interactive_asset` frontmatter field. These are self-contained HTML files that demonstrate interactions, animations, or dynamic patterns that static images cannot capture. They open in a browser or can be embedded via iframe.

## 9-Layer System

| Layer | Skill Phase | What it answers |
|-------|------------|----------------|
| knowledge | open-brain-analyze | What is this? |
| compression | open-brain-analyze | 20% that captures 80% |
| mental-model | open-brain-analyze | How experts think |
| application | open-brain-execute | How to use in practice |
| artifact | open-brain-execute | Tools/templates |
| decision | open-brain-execute | Better decisions |
| diagnosis | open-brain-improve | Am I doing this well? |
| coaching | open-brain-improve | How to level up |
| practice | open-brain-improve | How to train |

## Critical Rules

1. One idea per note
2. Every note has YAML frontmatter matching its schema
3. Every Permanent Note has a `layer` (one of 9 values); every Literature Note has `features` (a multi-label list)
4. Every Permanent Note links to 2+ others with reasons
5. Search Terms are canonical — check aliases before creating
6. Domains are created only with the vault owner's authorization
7. Cases are the vault owner's real experiences only
8. Increment `times_retrieved` when using a Permanent Note
9. Maturity: seed → growing → evergreen (earned, not assigned)
10. Rewrite, don't copy — Literature/Permanent Notes in the vault owner's voice
11. Every Design Reference must have at least one image embed or declare `visual_status: needs_assets`

## Relationship Map

| Field | Found in | Points to |
|-------|----------|-----------|
| `source` | Literature Note | Inbox/Book |
| `sources` | Permanent, Evergreen | Literature Notes, Cases |
| `mentor` | Inbox, Literature | Mentors/ |
| `search_terms` | All types | Search Terms/ |
| `domains` | Lit, Permanent, Case, Evergreen | Domains/ |
| `areas` | Inbox, Evergreen | Areas/ |
| `principles_validated` | Case | Permanent Notes |
| `principles_challenged` | Case | Permanent Notes |
| `key_works` | Mentor | Books/ |
| `related_terms` | Search Term | Search Terms/ |
| `source_lns` | Design Reference (REF) | Literature Notes |
| `linked_pns` | Design Reference (PAT) | Permanent Notes |
| `related_principles` | Design Reference (REF) | Literature Notes |
