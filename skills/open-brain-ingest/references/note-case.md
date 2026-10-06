# Case note — frontmatter, body and content hook

> Frontmatter and body template for the `case` type (Situation / What happened / What I learned / Connections), plus Step 6.5 (Content Pipeline Hook): the question asked when closing a Case and the seed note created in Ideas/. Read it whenever triage resolves to Case.

---

### Case frontmatter:

```yaml
---
type: case
case_type: success | challenge | mixed | failure | experiment
title: "Descriptive title"
domains:
  - "[[Domain Name]]"
search_terms:
  - "[[Term 1]]"
  - "[[Term 2]]"
features:
  - application
context: "Where this happened — company, project, team"
date_occurred: YYYY or YYYY-QN
principles_validated:
  - "[[Permanent Note title]]"
principles_challenged: []
confidence: high | medium | low
skill_sequence:
  - skill: open-brain-ingest
    at: "YYYY-MM-DDTHH:MM"
created: YYYY-MM-DD
---

## Situation
[Context: what was the problem or opportunity]

## What happened
[What the user did, the key decisions, and the results]

## What I learned
[Lessons learned, insights, what surprised the user — written in the first person, in the user's voice]

## Connections
[Links to Permanent Notes this case validates or challenges]
```

## Step 6.5: Content Pipeline Hook (Case-only)

If a **Case** was just created, ask the user one question before closing:

> "Could this case seed publishable content? If so, in what format — social post / article / talk or presentation / internal team doc?"

If yes, create a 3-line note in `Ideas/` with:
- `idea`: 1-line description
- `seed_case`: `[[<this case>]]`
- `seed_pns`: empty for now
- `format`: post / article / talk / internal
- `status`: seed
- `created`: today
- `notes`: free text — why this could be content
- `project`: `"[[Projects/Active/{name}/README]]"` — if the Case got a project in Step 0.8, inherit it here

Ideas go directly to `Ideas/`. If the idea has a `project:` field, the idea note still lives in `Ideas/` but is linked to the project.

---
