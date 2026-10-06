# Query Type 8 — Visual Retrieval

> The complete visual track: activation, scope, two-tier rerank, output format, image rules, mixed text+visual queries, Design Reference frontmatter fields and what the track does NOT do. Read only when rule 6 of the classifier fires.

---

## Query Type 8: Visual Retrieval — "What Form Can Represent This Idea?"

This is the second track of retrieval. While Query Types 1–7 answer "what do I know?", Query Type 8 answers "what shape should this idea take visually?".

### When to activate

Activate Visual Retrieval when intent = **Visual**, or when ANY query — regardless of which primary intent it already matched (Operative, Critical, Expressive, Exploratory, Serendipity) — includes a visual output need: "slide", "carousel", "image", "design", "designer", "interface", "how do I represent it", "doesn't look powerful", "I want it to be visual".

**This is additive, not conditional on primary intent.** A query classified Critical because it contains "challenge" still activates Query Type 8 if it also contains a visual-need phrase. Do not treat "the query already has an intent" as a reason to skip this check — check every query for a visual need before finalizing the response plan, even ones that look purely textual/critical at a glance.

### Scope

Visual Retrieval searches a different set of folders:
- **Primary**: `Design References/*.md` — both REF (design references from products/books) and PAT (reusable visual patterns)
- **Secondary**: `Resources/Images/**` — the actual image assets
- **Tertiary**: Permanent Notes and Literature Notes linked from design references via `linked_pns` and `source_lns`

### Visual Rerank

Standard text retrieval ranks by `confidence`, `maturity`, `times_retrieved`. Visual retrieval uses a two-tier system: first by endorsement status (hard tier), then by signal match within each tier.

#### Tier 1 — Endorsement Priority (hard ranking)

```
1. endorsed PATs     ← highest priority — user-validated abstract patterns
2. pending PATs      ← auto-generated, not yet validated
3. REFs              ← concrete examples from real products
4. LNs with Visual reference  ← textual principles with book page scans
```

An endorsed PAT ALWAYS ranks above a pending PAT, which ALWAYS ranks above a REF, regardless of signal match scores. Within each tier, the signal stack below applies.

#### Tier 2 — Signal Match (within-tier ranking)

1. **`visual_goal` match**: does the note's visual goal align with the query? (e.g., query about "tradeoffs" → boost notes with `visual_goal: explain tradeoffs` or `visual_goal: clarify decisions`)
2. **`pattern_family` match**: does the pattern type fit? (e.g., "comparison" → `pattern_family: 2x2` or `pattern_family: contrast`)
3. **`output_targets` match**: does the note target the output the user needs? (e.g., "carousel" → boost notes with `social-carousel` in `output_targets`)
4. **`reuse_score`**: higher reuse_score = more versatile pattern → rank higher for generic visual queries
5. **`primary_form`**: prefer notes whose form matches the ask (e.g., "matrix" → `primary_form: matrix`)
6. **`linked_pns` overlap**: if text retrieval already surfaced specific PNs, boost design references that link to them
7. **`source_lns` / `linked_refs` overlap**: if the query topic has LNs or REFs, boost notes that link to them
8. **`endorsement_evidence`**: for PATs, higher evidence count (more source REFs) = stronger pattern

#### Retrieval increment rules

- `times_retrieved` increments on PAT and REF notes when surfaced in visual retrieval
- endorsed PATs increment on every visual retrieval hit (they are the primary visual knowledge)
- REFs linked from a surfaced PAT do NOT increment individually (the PAT represents them)

### Output format for Visual Retrieval

When returning visual results, use this structure instead of the standard text response:

```markdown
## Retrieved thesis
- [[PN relevant to the topic]]

## Candidate visual forms
1. [[PAT — Pattern Name]] (reuse_score: N, visual_goal: X)
   → why it fits: [1 line]
2. [[REF — Reference Name]] (visual_goal: X, pattern_family: Y)
   → why it fits: [1 line]

## Anchor image
![[Resources/Images/Source/filename.png]]

## Problem it solves
[From the "Problem it solves" section of the most relevant note]

## Visual mechanism
[From the "Visual mechanism" section — how the pattern works without seeing the image]

## How to detect it
[From the "How to detect it in your own work" section — symptom + quick test]

## Step-by-step application
[From the "Step-by-step application" section of the note, adapted to the concrete case]

## Anti-patterns to avoid
[From the "Anti-patterns" section of the most relevant note]

## Reusable rule
[The "Reusable rule" of the most relevant note — 1 operational sentence]
```

### Image surfacing rules

Every visual retrieval result MUST include at least one image or declare its absence:
- If the design reference note contains `![[path]]` embeds → **read the image using the Read tool** and include the embed path in the response
- If the note references an asset in `Resources/Images/` → include the Obsidian embed: `![[Resources/Images/Source/filename.png]]`
- If the note has an `interactive_asset` field → mention it and provide the path so the user can open the HTML prototype in a browser
- If no image exists for the best-matching pattern → declare: `visual_status: needs_assets` and suggest what kind of image the user should capture

The rule: **every visual result must bring at least one anchor image or declare `visual_status: needs_assets`.**

### Visual + Text combined queries

When intent is mixed (e.g., "what do I know about AI trade-offs and how do I represent it in a carousel"):

1. Run text retrieval first → get PNs, LNs, synthesis
2. Run visual retrieval → match design references using `linked_pns` overlap with step 1 results + `visual_goal` + `output_targets`
3. Present in two sections:

```markdown
## What you know (Text Retrieval)
[Standard retrieval output with PN/LN synthesis]

## How to represent it (Visual Retrieval)
[Visual retrieval output with PAT/REF, images, and application]
```

### Frontmatter fields recognized in Design References

Two note types live in `Design References/`:

**REF — Design References** (examples from real products/books):
```yaml
type: design-reference
ref_type: pattern | source-example | brand-reference
category: [visual-hierarchy | action-hierarchy | spacing | ...]
product: [source product or book]
source: "[[Dossiers/Source]]"
source_lns: ["[[LN link]]"]
primary_form: [annotated-example | screenshot | comparison]
visual_goal: [guide attention | clarify decisions | ...]
cognitive_mode: [compare | decide | notice | ...]
pattern_family: [de-emphasis | action-hierarchy | spacing | ...]
why_i_like_it: "..."
interactive_asset: "Design References/Assets/filename.html"   # optional
tags: [...]
related_principles: ["[[LN link]]"]
```

**PAT — Visual Patterns** (reusable abstract patterns):
```yaml
type: visual-pattern
ref_type: pattern | source-example | brand-reference
category: [matrix | slide | radar | ...]
pattern_family: [2x2 | claim-proof | contrast | ...]
primary_form: [matrix | framework | radar | ...]
visual_goal: [explain tradeoffs | persuade with one message | ...]
cognitive_mode: [compare | decide | explain | persuade]
emotional_tone: [clarity | confidence | ...]
density: [low | medium | high]
text_to_visual_ratio: [0.0 - 1.0]
reuse_score: [1-5]
output_targets: [social-carousel | keynote-slide | obsidian-canvas | ...]
interactive_asset: "Design References/Assets/filename.html"   # optional
linked_pns: ["[[PN link]]"]
```

### What Visual Retrieval does NOT do

- Does NOT create or modify design reference notes
- Does NOT generate images — it retrieves existing assets
- Does NOT replace text retrieval — it complements it
- Does NOT increment `times_retrieved` on PNs surfaced through visual rerank (only text retrieval increments)

---
