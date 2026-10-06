# Support notes — Mentor, Search Term, Book

> Templates for the three support notes created in Step 4, plus the Mentor photo protocol (canonical naming, location, embed, the three photo_status scenarios and the report). Read it when a support note that doesn't exist yet must be created, or when touching a Mentor photo.

---

### Mentor note template:

```yaml
---
type: mentor
name: "Author Name"
search_terms:
  - "[[Relevant Term]]"
domains:
  - "[[Relevant Domain]]"
key_works:
  - "[[Book Title]]"
photo_status: pending      # one of: ok | nobg-missing | pending
dominant_color: ""         # hex, optional (fill it if you generate the colorbg image)
pastel_color: ""           # pastel hex for backgrounds (auto-generated)
created: YYYY-MM-DD
---

## Author Name

<!-- Brief description: who they are, why the user follows them, key ideas -->

<!-- Embed the photo once it exists in Mentors/images/ using Obsidian syntax:
     ![[Author Name.jpg]]
     Promote views and other renderers resolve it automatically. -->
```

### Mentor photo protocol

`Mentors/images/` is the only source of truth for mentor photos. Views that render mentors (e.g. the visual output of `open-brain-promote`) prioritize `<Author Name>_nobg.png` (photo without background) and fall back to the original if it doesn't exist. Additionally, `<Author Name>_colorbg.png` provides the mentor photo over a pastel background derived from the dominant color of the image.

Rules when creating a new Mentor:

1. **Canonical naming**: original photo is named `<Mentor Name>.<ext>` (with spaces and capitals matching the `.md`, e.g. `James Clear.jpg`). The no-background version is ALWAYS `.png` and ALWAYS shares the stem: `James Clear_nobg.png`. The pastel-background version follows the same convention: `James Clear_colorbg.png`.
2. **Location**: both in `Mentors/images/`. If a photo arrives from `Inbox/`, the vault root, `Resources/Images/` or anywhere else, MOVE it (don't copy) to `Mentors/images/`.
3. **Embed**: in the body of the `.md`, use `![[<Mentor Name>.<ext>]]` without path.
4. **Never block ingestion over a missing photo.** Three scenarios:
   - Have original + nobg + colorbg: `photo_status: ok`. Embed the original in body. Frontmatter should have `dominant_color` and `pastel_color`.
   - Have original but NO nobg: `photo_status: nobg-missing`. Embed anyway. Optionally generate the no-background and pastel-background images with any tool you like and fill the color fields; otherwise leave the status as is.
   - No photo at all: `photo_status: pending`. Do NOT invent a `![[...]]` pointing to a nonexistent file. Leave the body without an embed.
5. **Report**: at the end of ingest, list any Mentor with `photo_status` other than `ok`.

### Search Term note template:

```yaml
---
type: search-term
term: "Concept Name"
aliases:
  - "alternative name"
  - "another phrasing"
related_terms:
  - "[[Related Concept]]"
domains:
  - "[[Relevant Domain]]"
created: YYYY-MM-DD
---

## Concept Name

<!-- 2-3 sentence definition -->
```

### Book note template:

```yaml
---
type: book
title: "Book Title"
author: "[[Author Name]]"
search_terms:
  - "[[Term]]"
domains:
  - "[[Domain]]"
rating:
read: false
date_read:
literature_notes_count: 0
key_takeaway: ""
created: YYYY-MM-DD
---

## Book Title

<!-- Key themes, why this book matters -->
```
