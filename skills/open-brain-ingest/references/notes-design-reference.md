# REF and PAT notes — frontmatter, templates and assets

> Everything about Design References in one place: the two subtypes, frontmatter and body template for REF and PAT (Step 2), and the handling of visual and interactive assets (Step 5.5). Read it whenever triage resolves to Design Reference (REF or PAT).

---

## Design References — Note Subtypes

`Design References/` contains two note subtypes, each with distinct frontmatter. Both share the same canonical body template.

### REF — Design References (examples from real products/books)

Prefix: `REF —`. Captures a specific visual example from an existing product, book, or interface.

```yaml
---
type: design-reference
ref_type: pattern | source-example | brand-reference
category: "[visual-hierarchy | action-hierarchy | spacing | elevation | color | layout | ...]"
product: "Source product or book"
platform: [web | mobile | desktop | print]
sector: "[education | saas | ecommerce | ...]"
source: "[[Dossiers/Source Name]]"
source_lns:
  - "[[LN link]]"
primary_form: [annotated-example | screenshot | comparison]
visual_goal: "[guide attention | clarify decisions | show hierarchy | ...]"
cognitive_mode:
  - [compare | decide | notice | explain | persuade]
pattern_family: "[de-emphasis | action-hierarchy | spacing | elevation | ...]"
why_i_like_it: "One sentence — why the user saved this"
interactive_asset: "Design References/Assets/filename.html"   # optional — HTML/CSS/JS prototype
tags: []
related_principles:
  - "[[LN link]]"
skill_sequence:
  - skill: open-brain-ingest
    at: "YYYY-MM-DDTHH:MM"
date_captured: YYYY-MM-DD
---
```

### PAT — Visual Patterns (reusable abstract patterns)

Prefix: `PAT —`. Captures an abstract, reusable visual form independent of any product.

```yaml
---
type: visual-pattern
ref_type: pattern | source-example | brand-reference
category: "[matrix | slide | radar | contrast | ladder | scorecard | ...]"
pattern_family: "[2x2 | claim-proof | contrast | radar | ladder | ...]"
primary_form: "[matrix | framework | radar | annotated-example | ...]"
visual_goal: "[explain tradeoffs | persuade with one message | compare options | ...]"
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
skill_sequence:
  - skill: open-brain-ingest
    at: "YYYY-MM-DDTHH:MM"
date_captured: YYYY-MM-DD
---
```

### Body template (canonical — same for REF and PAT)

```markdown
# {{title}}

## Visual reference
![[Resources/Images/Source/filename.png]]
(PAT notes may omit the image if the pattern is abstract)

## Problem it solves
Describe the concrete visual failure this reference helps fix.
Don't just say it "looks good"; explain which confusion, noise, weak
hierarchy, loss of legibility or lack of memorability it corrects.

## Visual mechanism
Explain how it works: spacing, contrast, weight, position, repetition,
color, crop, hierarchy, rhythm, metaphor, format or composition.
This section must be able to teach the pattern without seeing the image.

## How to detect it in your own work
Turn the pattern into a diagnosis: which symptom appears when it is
missing, which quick test reveals it, and how you know you should
apply this pattern.

## Step-by-step application
1. First concrete move.
2. Second concrete move.
3. Third concrete move.
4. Visual check.

## Transfer to outputs
Explain how to use it in slides, carousels, annotated screenshots,
matrices, scorecards, visual posts or interfaces. Avoid generic
statements; name a concrete output situation.

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

---

## Step 5.5: Handle Visual Assets (Design References only)

When creating a Design Reference note:
1. If the user provides an image file → move/copy it to `Resources/Images/[Source Name]/` with a descriptive filename
2. Add the embed in the note body: `![[Resources/Images/Source Name/filename.png]]`
3. If the user provides an HTML/CSS/JS prototype → save it to `Design References/Assets/` with a descriptive filename and set `interactive_asset` in frontmatter
4. If no image is available → do NOT add a fake embed. Leave `## Visual reference` empty, set `visual_status: needs_assets`, and note in the report that the reference needs an image asset

Every REF note should have at least one image. PAT notes may not have images (they describe abstract forms).

### Visual Assets

Image assets live in `Resources/Images/` organized by source (e.g., `Resources/Images/Refactoring UI/`). Design reference notes embed them with Obsidian syntax: `![[Resources/Images/Source/filename.png]]`.

Interactive assets (HTML/CSS/JS prototypes) live in `Design References/Assets/` and are referenced via the `interactive_asset` frontmatter field. These are self-contained HTML files that demonstrate interactions, animations, or dynamic patterns that static images cannot capture. They open in a browser or can be embedded via iframe.
