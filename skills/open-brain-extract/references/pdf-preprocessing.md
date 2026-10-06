# Steps 0.5 and 0.6 — PDF/DOCX/PPTX pre-processing and Evidence Bundle

> The full procedure for markitdown (text cache) and for `evidence_bundle.py` (metadata, TOC, figures, tables, page quality, warnings), with fallbacks and skip conditions. Read it when the source is a PDF, DOCX or PPTX.

---

### Step 0.5: PDF/DOCX/PPTX Pre-processing with MarkItDown

**When the source is a PDF, DOCX, or PPTX** (uploaded file, or linked via `link:` in an Inbox note with `raw_strategy: pdf-on-disk`), convert it to structured Markdown BEFORE reading it as context. This replaces reading the PDF as page images (lossy, token-heavy, loses structure).

**Tool**: `markitdown` (Microsoft, pip package `markitdown[pdf]`). Install it first: `pip install 'markitdown[pdf]' --break-system-packages`.

**Procedure**:

1. Check if a text cache already exists at `Resources/Extracted Text/{source-slug}.md` (or `.txt`). If it does and is current → skip, use the cache (the double-read guard still applies).
2. If no cache exists, run markitdown via bash:
   ```bash
   markitdown "/path/to/source.pdf" -o "$OPEN_BRAIN_VAULT/Resources/Extracted Text/{source-slug}.md"
   ```
3. The output is structured Markdown preserving headings, tables, lists, and links from the PDF. Save with `.md` extension to signal it's structured.
4. Read the `.md` cache file as your primary source for all subsequent steps. Do NOT re-read the binary PDF.

**Why this matters**: markitdown preserves document structure (headings → `#`, tables → Markdown tables, lists → bullet/numbered lists) that page-image reading destroys. The Markdown output is also 3-5x more token-efficient than raw text extraction, meaning more of the book fits in context.

**Fallback**: if markitdown fails (corrupt PDF, scanned-only with no text layer), fall back to reading the PDF as page images and note the limitation in the report. Suggest the user try the `markitdown-ocr` plugin with an LLM vision client for scanned PDFs.

---

### Step 0.6: Evidence Bundle (PDF sources only)

After markitdown text extraction (Step 0.5), run the evidence bundle builder to generate a structured JSON with all the evidence the LLM should have before writing LNs. This is a deterministic pre-processing step — no LLM involvement.

**Tool**: `$OPEN_BRAIN_ENGINES/engine/evidence_bundle.py` (requires `PyMuPDF`). Install once: `pip install PyMuPDF --break-system-packages`.

**Procedure**:

1. Run the evidence bundle builder:
   ```bash
   python3 "$OPEN_BRAIN_ENGINES/engine/evidence_bundle.py" build "/path/to/source.pdf" \
     --output "Resources/Extracted Text/{source-slug}_bundle.json" \
     --images "Resources/Images/{source-slug}/"
   ```
2. Read `bundle.json` alongside the markitdown text cache. The bundle contains:
   - **metadata**: title, authors, DOI, creation date (cross-check with Inbox note)
   - **toc**: table of contents with page numbers (use to verify section coverage in Step 7)
   - **figures**: inventory with page, bbox, extraction quality, surrounding text, and extracted image paths
   - **tables_detected**: pages with table-like structures
   - **page_text_quality**: per-page character count and scanned-page flags
   - **warnings**: issues the LLM should know about (scanned pages, truncated scans)

3. Use the bundle throughout extraction:
   - Step 2: cross-check your section scan against the TOC
   - Step 3: check figure count — each figure with `extraction_quality: high` is a Visual Reference candidate
   - Step 6.4: prefer bundle-extracted images (`images/fig_pN_M.ext`) over pre-existing page renders
   - Step 10: include bundle warnings in the report

**Skip conditions**: source is not a PDF on disk (web article, video, text paste), OR PyMuPDF is not available. If skipped, extraction proceeds normally without the bundle — the bundle is additive, never blocking.

---
