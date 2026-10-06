# Inbox note — frontmatter and rules

> Full frontmatter for the `inbox` type and its key rules (processed, search_terms, mentor, body, source_project, source_type). Read it whenever triage resolves to Inbox, before writing the note.

---

### Inbox frontmatter:

```yaml
---
type: inbox
source_type: article | book | video | podcast | course | tool | tweet | conversation | research-report | other
title: "Descriptive title"
mentor: "[[Author Name]]"
search_terms:
  - "[[Term 1]]"
  - "[[Term 2]]"
areas:
  - "[[Area Name]]"
link: "https://..."
tier: top | interesting | skip
raw_strategy: full | highlights | link-only | pdf-on-disk
raw_path: "Inbox/Raw/[title].md"
source_project: ""              # populated by the project router for research reports
research_report_path: ""        # path to the .md in Projects/Active/{name}/Research/ if applicable
rating:
processed: false
skill_sequence:
  - skill: open-brain-ingest
    at: "YYYY-MM-DDTHH:MM"
created: YYYY-MM-DD
---
```

Key rules:
- `processed` is always `false` on creation — `open-brain-extract` sets it to `true` later
- `search_terms` needs at least one entry
- `mentor` links to a person, not a publication. Use `[[Unknown]]` if unclear
- The body contains the raw capture: highlights, quotes, notes, links
- `source_project` is only populated for research reports routed via Step 0.8
- `source_type: research-report` signals this Inbox note came from a deep-research run
