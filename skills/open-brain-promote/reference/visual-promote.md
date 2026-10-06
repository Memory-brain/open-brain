# reference/visual-promote.md — Visual pipeline (REF/PAT)

> Reconstructed from the v9.4 monolith of `open-brain-promote`, for the same reason as
> `text-promote.md`. Where it and `SKILL.md` disagree, `SKILL.md` wins.

## Before using this pipeline: check there is material

**A visual catalog is usually small, and this mechanism only works with enough REFs.**
A cluster needs 3+ pieces of evidence sharing a `pattern_family`; with only a handful of
REFs in `Design References/`, almost no family will reach that.

Practical consequence: **before promoting a visual pattern, check that there is material.**
If the scan finds no cluster, say so and stop — the problem is capture, not promotion, and
proposing a PAT with two weak pieces of evidence spends the vault owner's gate on something
that does not deserve it.

**The atomic commands of this pipeline**: `--visual-endorse`, `--visual-reject`.

---

## Visual Promote Mode (v9.3)

**Trigger**: "visual promote", "promote patterns", "visual convergence", "PAT notes", "visual patterns"

Visual promote converts convergences between Design References (REFs) into Visual Pattern Notes (PATs). The PAT is the visual equivalent of a Permanent Note — an abstract, reusable pattern distilled from multiple concrete examples.

### V-Step 1: Visual Convergence Scan

Scan `Design References/` for REF notes (type: `design-reference`). Group by shared `pattern_family` values.

```bash
# Find all REFs and their pattern_family values
grep -l "type: design-reference" "Design References/"*.md
# For each, extract pattern_family
grep "pattern_family:" "Design References/REF"*.md
```

A cluster is ≥3 REFs from ≥2 distinct products that share at least one `pattern_family` value.

Also scan existing PAT notes to avoid duplicating an already-promoted pattern:
```bash
ls "Design References/PAT"*.md
```

If a PAT already exists for a `pattern_family` and has `endorsement_status: endorsed`, skip that cluster. If `endorsement_status: pending`, present it for endorsement instead of creating a new draft.

### V-Step 2: Visual Convergence Test (4 gates)

For each candidate cluster, apply all 4 gates:

| Gate | Question | Pass | Fail |
|------|----------|------|------|
| **Multi-product** | Do REFs come from ≥2 distinct products? | Stripe + Linear + a fitness app | 3 screens from the same app |
| **Multi-context** | Does the pattern appear across ≥2 sectors or platforms? | web + mobile, sports + SaaS | Only fintech dashboards |
| **Abstractable** | Can you teach the visual mechanism without naming any product? | "A numeral 3-5x larger than body text creates hierarchy without chrome" | "Stripe uses big numbers" |
| **Transferable** | Can the vault owner name ≥2 concrete outputs where the pattern applies? | slides + landing pages + carousels | "For design in general" |

Clusters that fail any gate → logged as "weak visual signals" in the report, not promoted.

### V-Step 3: Visual Promotion Brief

For each cluster that passes all 4 gates, generate the brief and present it to the vault owner. Do NOT write the PAT yet.

```markdown
# Visual Promotion Brief — [Pattern name as declarative phrase]

## Cluster detected
**pattern_family**: [shared value]
**REFs in cluster**: N

## Design References considered
- [[REF — Product A]] — platform: web, sector: SaaS — [what it demonstrates]
- [[REF — Product B]] — platform: mobile, sector: sports — [what it demonstrates]
- [[REF — Product C]] — platform: web, sector: sports — [what it demonstrates]

## Visual Convergence Test
| Gate | Result | Detail |
|------|--------|--------|
| Multi-product | ✅ | [N products: list] |
| Multi-context | ✅ | [platforms/sectors] |
| Abstractable | ✅ | [draft mechanism in 1-2 sentences, no product names] |
| Transferable | ✅ | [outputs: slides, dashboards, landing pages...] |

## Draft PAT — visual mechanism
[3-5 sentences describing HOW the pattern works visually. This must teach the pattern without showing any image. This is the quality bar.]

## Three questions for you
1. **Is it teachable?** — Can you explain this pattern to someone without showing the source images?
2. **Have you used it, or would you?** — Name a real output where you would apply this pattern.
3. **What do you see that the description does not capture?** — This goes into "Owner's eye" in the PAT.
```

Present and STOP. Wait for the vault owner.

### V-Step 4: The vault owner evaluates

Do NOT proceed without answers. Three outcomes:

- **Endorse** → proceed to V-Step 5 with `endorsement_status: endorsed`
- **Reject** → log rejection, do not create PAT
- **Iterate** → the vault owner requests changes to the mechanism description, outputs, or anti-patterns. Apply changes, re-present brief.

If the owner answers Q3 with specific observations, they go into a `## Owner's eye` section in the PAT body (analogous to `## Your extension` in PNs).

### V-Step 5: Write the PAT Note

**File**: `Design References/PAT — [Pattern name].md`

The title is a declarative phrase describing the visual mechanism.

```yaml
---
type: visual-pattern
ref_type: pattern
category: [inferred from cluster]
pattern_family:
  - [shared value that triggered convergence]
  - [additional families if applicable]
primary_form: [inferred from REFs]
visual_goal: [synthesized from REFs' visual_goal values]
cognitive_mode:
  - [union of REFs' cognitive_mode values]
emotional_tone:
  - [inferred]
density: [low | medium | high]
text_to_visual_ratio: [estimated 0.0-1.0]
reuse_score: [1-5, based on multi-context breadth]
output_targets:
  - [concrete outputs from the owner's Q2 answer + inferred]

# Traceability
linked_refs:
  - "[[REF — Source 1]]"
  - "[[REF — Source 2]]"
  - "[[REF — Source 3]]"
refs_excluded_with_reason:
  - "[[REF — X]] — too product-specific, not generalizable"
linked_pns:
  - "[[PN that explains WHY this pattern works]]"
convergence_test:
  multi_product: true
  multi_context: true
  abstractable: true
  transferable: true

# Endorsement
endorsement_status: pending | endorsed    # set based on V-Step 4
endorsed_at: YYYY-MM-DD                  # date of endorsement (empty while pending)
endorsed_via: visual-promote-by-convergence
endorsement_note: "[the owner's Q3 answer if provided]"
endorsement_evidence: N                  # count of linked_refs

# Lifecycle
date_captured: YYYY-MM-DD
times_retrieved: 0
last_used_in_output:
# maturity: do NOT write it — derived by vault-scan (see G6 in SKILL.md)
created: YYYY-MM-DD
---
```

### Body structure

```markdown
# [Pattern name — declarative, teachable]

## Visual reference

### Evidence 1 — [Product] ([platform])
![[path/to/image1.png]]
[1 line: what this image demonstrates about the pattern]

### Evidence 2 — [Product] ([platform])
![[path/to/image2.png]]
[1 line]

### Evidence N...

---

## Problem it solves
[What visual failure this pattern corrects. Not "it looks good" — what confusion, noise, or hierarchy loss it eliminates.]

## Visual mechanism
[HOW it works: scale, contrast, spacing, position, color, composition. MUST teach the pattern without seeing any image. This is the section the AI consumes to generate design.md.]

## How to detect it in your own work
[Symptoms when the pattern is missing. Quick diagnostic tests.]

## Step-by-step application
[Concrete steps to implement from scratch. Numbered, actionable.]

## Transfer to outputs
[How to use in: slides, carousels, dashboards, landing pages, interfaces, executive memos. Name concrete situations, not generics.]

## Anti-patterns
[Common mistakes when misapplying the pattern. Minimum 3.]

## Reusable rule
[One operational sentence you (or the AI) can remember while designing.]

## Owner's eye
[The vault owner's Q3 answer — what they see that the description misses. Left empty if they had nothing to add. Analogous to "Your extension" in PNs.]

## Tests
[Visual checks to validate the pattern is correctly applied. Minimum 3.]
```

### V-Step 6: Link Back to Source REFs

For each REF in `linked_refs`, add to its frontmatter:
```yaml
promoted_to: "[[PAT — Pattern Name]]"
```

This creates bidirectional traceability: PAT → REFs via `linked_refs`, REFs → PAT via `promoted_to`.

### V-Step 7: Update Typed Knowledge Graph (silent)

Same as text promote — fire-and-forget:
```bash
GRAPH_SCRIPT="$OPEN_BRAIN_ENGINES/autolink/update_graph.py"
if [ -f "$GRAPH_SCRIPT" ]; then
  python3 "$GRAPH_SCRIPT" "<absolute path to PAT file>" --quiet 2>/dev/null || true
fi
```

### V-Step 8: Report

```
## ✅ Visual Pattern created: [[PAT — Pattern Name]]

**Endorsement**: [endorsed by the vault owner / pending review]
**REFs evaluated**: N (M used, K excluded)
**Convergence test**: ✅ multi-product · ✅ multi-context · ✅ abstractable · ✅ transferable
**Output targets**: [list from Q2]
**Owner's eye**: [recorded / no additional observations]

**Next step (if applicable)**:
- Pending new cluster: [...]
- Endorse pending PATs: [list if any exist]
```

---

## Visual Atomic Commands (v9.3)

### --visual-endorse [[PAT]]

1. Find the PAT in `Design References/`. Verify `endorsement_status: pending`.
2. Present the PAT with its images and mechanism. Ask the 3 endorsement questions.
3. Update frontmatter: `endorsement_status: endorsed`, `endorsed_at: <today>`, `endorsed_via: visual-promote-atomic-endorse`.

### --visual-reject [[PAT]] (reason)

1. Find the PAT. Ask for reason if not provided.
2. Move: `Design References/PAT — X.md` → `Design References/Rejected/PAT — X.md`.
3. Update frontmatter: `endorsement_status: rejected`, `rejected_at`, `rejected_reason`.
4. Do NOT delete. Do NOT remove `promoted_to` from source REFs (broken link = correct signal).

---
