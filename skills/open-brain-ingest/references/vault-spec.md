# Vault Specification — shared reference

> Condensed vault specification: the 6-feature system, the 11 critical rules, the map of relationships between fields, the vault root, the folder → note type mapping and the folder tree. Read it when unsure which folder or `type` applies, which field points where, or before writing `features:`.

---

## 6-Feature System

| Feature | What it captures |
|---------|-----------------|
| factual | Data, facts, definitions — what is this? |
| conceptual | Mental models, analogies, compressed principles |
| application | Procedures, how-to, practical use |
| decision | Selection criteria, trade-offs, when to use what |
| diagnosis | Anti-patterns, failure modes, quality checks |
| code-artifact | Templates, tools, reproducible artifacts |

Literature Notes use multi-label `features:` (a list); Permanent Notes use a single `layer:` (one of 9 values). An LN can be both `factual` and `application`.

## Critical Rules

1. One idea per note
2. Every note has YAML frontmatter matching its schema
3. Every Permanent Note has a `layer` (one of 9 values); every Literature Note has `features` (a multi-label list)
4. Every Permanent Note links to 2+ others with reasons
5. Search Terms are canonical — check aliases before creating
6. New Domains are created only with the user's approval
7. Cases are the user's real experiences only
8. Increment `times_retrieved` when using a Permanent Note
9. Maturity: seed → growing → evergreen (earned, not assigned)
10. Rewrite, don't copy — Literature/Permanent Notes are written in the user's own words
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
| `source_project` | Inbox (research), Literature Note | Projects/Active/ |

## Vault Path
`$OPEN_BRAIN_VAULT` — set this environment variable to the root folder of your Obsidian vault. All paths in the skills are relative to it.

## Folder → Note Type Mapping

| Folder | Note Type | `type` value |
|--------|-----------|-------------|
| `Inbox/` | Raw captures | `inbox` |
| `Literature Notes/` | Extracted insights | `literature` |
| `Fleeting Notes/` | The user's own quick ideas | `fleeting` |
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

## Vault Structure

All notes go to the Obsidian vault directory (`$OPEN_BRAIN_VAULT`):

```
$OPEN_BRAIN_VAULT/
├── Inbox/           ← Inbox notes
├── Mentors/         ← mentor MOC notes
├── Search Terms/    ← concept MOC notes
├── Books/           ← book notes
├── Areas/           ← area MOC notes
├── Cases/           ← the user's own experiences
├── Design References/ ← visual patterns (PAT) and design references (REF)
```

Design Reference and Visual Pattern body headings (English, shared across skills): `## Visual reference`, `## Problem it solves`, `## Visual mechanism`, `## How to detect it in your own work`, `## Step-by-step application`, `## Transfer to outputs`, `## Anti-patterns`, `## Reusable rule`, `## Tests`. Full templates: `notes-design-reference.md`.

---
