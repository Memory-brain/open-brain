# Step 6.4 — Visual Reference Embedding

> The full procedure: parsing pages from `source_ref`, searching for images in `Resources/Images/`, preference order between bundle images and page renders, embedding and skip conditions. Read it when the source is a PDF or a book with images.

---

## Step 6.4: Visual Reference Embedding (mandatory for PDF/book sources)

After writing each LN, check if visual assets exist for the referenced pages. This step connects the text extraction with the image extraction that already lives in `Resources/Images/`.

### Procedure

1. **Parse page numbers from `source_ref`.** Extract all page numbers from the reference string.
   - `"Author, 2018, pp. 238-241"` → pages [238, 239, 240, 241]
   - `"Author, 2024, p. 66"` → pages [66]
   - `"Author, 2024, pp. 21, 213-215"` → pages [21, 213, 214, 215]

2. **Determine the book image folder.** Map the source Dossier name to its image folder in `Resources/Images/`. Use the book's display name (e.g., `Refactoring UI`, `Practical UI`, `Laws of UX`). Check `Resources/Images/` for the matching subfolder. If no subfolder exists → skip, set `visual_status: needs_assets`.

3. **Search for matching images.** For each extracted page number, look for files matching:
   - **Bundle images first** (if an evidence bundle was generated): `fig_p{pagenum}_{idx}.{ext}` in `Resources/Images/{source-slug}/` — these are cropped to the figure bbox, not full-page captures
   - `*p{pagenum}*` (e.g., `refactoring-ui-p240-img01-I123.png`)
   - `page-{pagenum}.png` (e.g., `page-303.png`)
   - `*-p{pagenum:03d}*` (zero-padded variants)

   Prefer bundle-extracted images over pre-existing page renders (they're cropped to the actual figure). Among non-bundle images, prefer embedded images (`*-img*`) over full-page renders when both exist. Select the first matching image per page — if a page has multiple images, include all of them.

4. **Embed in the LN.** If ≥1 image found, add a `## Visual Reference` section between the `[!claude] Connectors` callout and `## Your extension`:

   ```markdown
   ## Visual Reference

   ![[Resources/Images/BookName/matched-image.png]]
   ```

   If multiple images match the page range, embed all of them in order.

5. **If no images found**, add `visual_status: needs_assets` to the LN frontmatter. Do NOT add an empty `## Visual Reference` section.

### Why this matters

Design books communicate through images — a note about "separation without borders" is crippled without the before/after example. The images already exist in `Resources/Images/` from prior PDF processing. This step closes the gap between text extraction and visual context, making every LN from a visual source self-contained.

### Skip conditions

- Source is not a PDF/book (articles, videos) → skip
- No `Resources/Images/{BookSlug}/` folder exists → skip, add `visual_status: needs_assets`
- LN already has a `## Visual Reference` section → skip (idempotent)

---
