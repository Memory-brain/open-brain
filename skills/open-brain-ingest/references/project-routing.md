# Step 0.8 — Project Routing (full guide)

> Read this when the content is a research report, when the router returns `medium` / `low` / `none`, when you are unsure whether an artifact belongs in a project folder, or when you first set up routing for your vault.

---

## What project routing is for

Most notes in the vault are organized by *what they are* (Inbox, Literature, Permanent, Cases…), not by *what they were for*. Project routing adds a thin, optional link from a note to the project it served, without moving the note out of its Zettelkasten folder. That keeps the knowledge reusable across projects while still letting you answer "what did I produce or learn for project X?".

If you do not organize work into projects, skip this step entirely — nothing else in the pipeline depends on it.

---

## Configuring where projects live

The router assumes one folder per active project, each with a `README.md` that describes it:

```
Projects/
└── Active/
    ├── Website Redesign/
    │   ├── README.md        ← what the project is, goals, key terms
    │   ├── Outputs/         ← deliverables (.pptx, .docx, .html, .pdf)
    │   └── Research/        ← deep-research reports routed here
    └── Onboarding Course/
        └── README.md
```

- **Default root**: `Projects/Active/` relative to `$OPEN_BRAIN_VAULT`.
- **Different layout?** Point the router at your own folder (e.g. `Work/Current/`) and use that path everywhere this guide says `Projects/Active/`. Keep the `{name}/README.md` convention: the `project:` field always links to the project's README, and the router matches the query against README contents.
- **Better matches**: the router scores your query against each README. A README that states the project's goal, audience and three to five key terms routes far more reliably than an empty one.
- **Archived projects**: move them out of the active root (e.g. to `Projects/Archive/`). The router only considers active projects, so stale projects stop attracting new notes.

---

## Which content is routed

Run the router when Step 0 determined the content is:

- a **Case** (the user's own experience),
- any **output/deliverable** (plan, audit, roadmap, design doc, presentation, spec, etc.), or
- an **Inbox note originating from a deep-research run**.

**Does NOT apply to**: regular (non-research) Inbox notes, Fleeting Notes, Design References, Mentors, Search Terms, Books — these go to their standard Zettelkasten folders regardless of project context.

## How to run

```bash
python3 "$OPEN_BRAIN_ENGINES/engine/project_router.py" \
  --vault "$OPEN_BRAIN_VAULT" \
  --query "<title + context + topic of the content being ingested>"
```

## Act on the result

| `confidence` | Action |
|---|---|
| `high` | Add `project: "[[Projects/Active/{name}/README]]"` to the note's frontmatter. Case notes still live in `Cases/` (preserving the Zettelkasten structure); the project field links them. Output artifacts (.pptx, .docx, .html, .pdf) go directly to `Projects/Active/{name}/Outputs/`. |
| `medium` | Add the project field but tell the user: *"I've linked this note to the project {name}. Correct?"* |
| `low` | Ask the user before adding the project field. |
| `none` (ask_user) | Ask the user which project this belongs to, or whether to create a new one. |
| `none` (zettelkasten) | No project field needed — proceed as normal. |

## Research report handling

A source counts as a deep-research output when it contains `## Sources` or `## Research Question` sections, or the user says explicitly that it comes from a research run for a given project.

1. Run the project router as usual.
2. If a project is detected:
   - **The research report file** (the .md produced by the research run) moves to `Projects/Active/{name}/Research/`. Create the `Research/` subfolder if it doesn't exist.
   - **The Inbox note** stays in `Inbox/` but gets `source_project: "[[Projects/Active/{name}/README]]"` in its frontmatter, and `research_report_path:` pointing at the moved file.
3. If no project is detected: ask the user which project this research belongs to. Research without a project is an error — a deep-research run always serves a purpose.

## Key principle

**Notes stay in Zettelkasten folders. Only artifacts go to project folders.** Examples:

- A Case about running a website redesign lives in `Cases/` with `project: "[[Projects/Active/Website Redesign/README]]"` in its frontmatter.
- The slide deck presented at that project's kickoff lives in `Projects/Active/Website Redesign/Outputs/`.
- A deep-research report on community garden layouts lives in `Projects/Active/Garden Course/Research/`, while its Inbox note stays in `Inbox/` with `source_project:` set.

---
