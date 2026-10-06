#!/usr/bin/env python3
"""
evidence_bundle.py — deterministic plumbing for open-brain-extract v9.5.

Pre-processes a PDF with PyMuPDF and produces a JSON bundle with all the
structural evidence the LLM needs before extracting Literature Notes:
  - Document metadata (title, authors, DOI, dates)
  - Table of contents (TOC)
  - Figure inventory with image extraction
  - Table detection (line-based heuristic)
  - Text quality per page (scanned-page detection)
  - Text surrounding each figure, for semantic context

The AI keeps the judgment: deciding what is note-worthy, assigning layers,
writing the LNs. This script only gathers evidence.

Commands:
  build <pdf_path> --output <bundle.json> [--images <dir>] [--max-pages 200]
  inspect <bundle.json>

Dependencies: PyMuPDF (pip install PyMuPDF --break-system-packages)
"""

# `X | None` in annotations is 3.10+; on Python 3.9 the module would crash at
# import. With this future import annotations are not evaluated.
from __future__ import annotations


import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# --- safe import of PyMuPDF ---
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Collapse whitespace, strip null bytes."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\x00", "")).strip()


def _surrounding_text(page_text: str, bbox_y_center: float, page_height: float,
                      window_chars: int = 300) -> str:
    """Extract text around a vertical position on the page (rough heuristic)."""
    if not page_text:
        return ""
    # Estimate character position from vertical fraction
    frac = bbox_y_center / max(page_height, 1)
    center = int(frac * len(page_text))
    start = max(0, center - window_chars // 2)
    end = min(len(page_text), center + window_chars // 2)
    return _clean_text(page_text[start:end])


def _classify_extraction_quality(pix_width: int, pix_height: int) -> str:
    """Heuristic quality classification for an extracted image."""
    area = pix_width * pix_height
    if area >= 100_000:
        return "high"
    elif area >= 25_000:
        return "medium"
    else:
        return "low"


# ---------------------------------------------------------------------------
# Core: build the evidence bundle
# ---------------------------------------------------------------------------

def build_bundle(pdf_path: str, images_dir: str | None = None,
                 max_pages: int = 200) -> dict:
    """
    Build a structured evidence bundle from a PDF.

    Returns a dict ready for JSON serialisation.
    """
    if not HAS_PYMUPDF:
        return {
            "error": "PyMuPDF not installed. Run: pip install PyMuPDF --break-system-packages",
            "fallback": True,
        }

    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        return {"error": f"PDF not found: {pdf_path}"}

    doc = fitz.open(str(pdf_path))

    # --- metadata ---
    meta = doc.metadata or {}
    metadata = {
        "title": _clean_text(meta.get("title", "")),
        "author": _clean_text(meta.get("author", "")),
        "subject": _clean_text(meta.get("subject", "")),
        "creator": _clean_text(meta.get("creator", "")),
        "creation_date": meta.get("creationDate", ""),
        "mod_date": meta.get("modDate", ""),
        "keywords": _clean_text(meta.get("keywords", "")),
    }

    # Try to extract DOI from first 3 pages
    doi = ""
    for i in range(min(3, len(doc))):
        text = doc[i].get_text()
        doi_match = re.search(r"10\.\d{4,}/[^\s]+", text)
        if doi_match:
            doi = doi_match.group(0).rstrip(".,;)")
            break
    metadata["doi"] = doi

    # --- TOC ---
    raw_toc = doc.get_toc()  # [[level, title, page], ...]
    toc = [
        {"level": entry[0], "title": _clean_text(entry[1]), "page": entry[2]}
        for entry in raw_toc
    ]

    # --- per-page analysis + figure extraction ---
    figures = []
    tables_detected = []
    page_quality = []
    fig_index = 0
    pages_to_scan = min(len(doc), max_pages)

    # Prepare images dir
    if images_dir:
        images_dir = Path(images_dir)
        images_dir.mkdir(parents=True, exist_ok=True)

    for page_num in range(pages_to_scan):
        page = doc[page_num]
        page_text = page.get_text()
        char_count = len(page_text.strip())
        is_scanned = char_count < 100  # heuristic: very little text → scanned

        page_quality.append({
            "page": page_num + 1,  # 1-indexed for human readability
            "char_count": char_count,
            "is_scanned": is_scanned,
        })

        # --- extract images from page ---
        image_list = page.get_images(full=True)
        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
            except Exception:
                continue

            if not base_image or not base_image.get("image"):
                continue

            img_width = base_image.get("width", 0)
            img_height = base_image.get("height", 0)

            # Skip tiny images (icons, decorations)
            if img_width < 80 or img_height < 80:
                continue

            quality = _classify_extraction_quality(img_width, img_height)
            ext = base_image.get("ext", "png")

            # Determine extraction path
            extracted_path = None
            if images_dir:
                fname = f"fig_p{page_num + 1}_{img_idx}.{ext}"
                out_path = images_dir / fname
                try:
                    out_path.write_bytes(base_image["image"])
                    extracted_path = str(out_path)
                except Exception as e:
                    extracted_path = f"EXTRACTION_FAILED: {e}"

            # Get surrounding text for semantic context
            # Use image position if available via get_image_rects
            try:
                rects = page.get_image_rects(xref)
                if rects:
                    bbox = rects[0]
                    bbox_y_center = (bbox.y0 + bbox.y1) / 2
                    context = _surrounding_text(
                        page_text, bbox_y_center, page.rect.height
                    )
                    bbox_list = [round(bbox.x0, 1), round(bbox.y0, 1),
                                 round(bbox.x1, 1), round(bbox.y1, 1)]
                else:
                    context = ""
                    bbox_list = None
            except Exception:
                context = ""
                bbox_list = None

            figures.append({
                "index": fig_index,
                "page": page_num + 1,
                "bbox": bbox_list,
                "width": img_width,
                "height": img_height,
                "extracted_path": extracted_path,
                "extraction_quality": quality,
                "surrounding_text": context[:500],  # cap length
            })
            fig_index += 1

        # --- table detection heuristic ---
        # Look for grid-like drawings (many short horizontal + vertical lines)
        drawings = page.get_drawings()
        h_lines = 0
        v_lines = 0
        for d in drawings:
            for item in d.get("items", []):
                if item[0] == "l":  # line
                    p1, p2 = item[1], item[2]
                    dx = abs(p2.x - p1.x)
                    dy = abs(p2.y - p1.y)
                    if dy < 2 and dx > 30:
                        h_lines += 1
                    elif dx < 2 and dy > 15:
                        v_lines += 1
        if h_lines >= 4 and v_lines >= 2:
            tables_detected.append({
                "page": page_num + 1,
                "h_lines": h_lines,
                "v_lines": v_lines,
                "confidence": "high" if h_lines >= 8 else "medium",
            })

    # --- scanned page warnings ---
    warnings = []
    scanned_pages = [p["page"] for p in page_quality if p["is_scanned"]]
    if scanned_pages:
        if len(scanned_pages) <= 5:
            warnings.append(
                f"Pages {scanned_pages} appear scanned with low text extraction"
            )
        else:
            warnings.append(
                f"{len(scanned_pages)} pages appear scanned (first: {scanned_pages[:5]})"
            )

    if len(doc) > max_pages:
        warnings.append(
            f"PDF has {len(doc)} pages; figure scan limited to first {max_pages}"
        )

    total_pages = len(doc)
    doc.close()

    return {
        "source_file": str(pdf_path.name),
        "page_count": total_pages,
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "metadata": metadata,
        "toc": toc,
        "figures": figures,
        "figure_count": len(figures),
        "tables_detected": tables_detected,
        "page_text_quality": page_quality,
        "scanned_page_count": len(scanned_pages),
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Inspect: pretty-print a bundle
# ---------------------------------------------------------------------------

def inspect_bundle(bundle_path: str) -> None:
    """Print a human-readable summary of an evidence bundle."""
    with open(bundle_path) as f:
        bundle = json.load(f)

    if "error" in bundle:
        print(f"⚠️  Bundle error: {bundle['error']}")
        return

    print(f"📄 {bundle['source_file']} — {bundle.get('page_count', '?')} pages")
    print(f"   Built: {bundle.get('built_at', '?')}")

    meta = bundle.get("metadata", {})
    if meta.get("title"):
        print(f"   Title: {meta['title']}")
    if meta.get("author"):
        print(f"   Author: {meta['author']}")
    if meta.get("doi"):
        print(f"   DOI: {meta['doi']}")

    toc = bundle.get("toc", [])
    print(f"\n📑 TOC: {len(toc)} entries")
    for entry in toc[:15]:
        indent = "  " * entry["level"]
        print(f"   {indent}{entry['title']} (p.{entry['page']})")
    if len(toc) > 15:
        print(f"   ... and {len(toc) - 15} more")

    figs = bundle.get("figures", [])
    print(f"\n🖼️  Figures: {len(figs)}")
    for fig in figs[:10]:
        q = fig.get("extraction_quality", "?")
        path = fig.get("extracted_path", "not saved")
        ctx = fig.get("surrounding_text", "")[:80]
        print(f"   [{q}] p.{fig['page']} {fig['width']}×{fig['height']}  {path}")
        if ctx:
            print(f"         \"{ctx}...\"")
    if len(figs) > 10:
        print(f"   ... and {len(figs) - 10} more")

    tables = bundle.get("tables_detected", [])
    print(f"\n📊 Tables detected: {len(tables)}")
    for t in tables:
        print(f"   p.{t['page']} ({t['confidence']} confidence)")

    scanned = bundle.get("scanned_page_count", 0)
    if scanned:
        print(f"\n⚠️  Scanned pages: {scanned}")

    warnings = bundle.get("warnings", [])
    if warnings:
        print(f"\n⚠️  Warnings:")
        for w in warnings:
            print(f"   - {w}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evidence bundle builder for open-brain-extract"
    )
    sub = parser.add_subparsers(dest="command")

    # build
    p_build = sub.add_parser("build", help="Build evidence bundle from PDF")
    p_build.add_argument("pdf_path", help="Path to the PDF file")
    p_build.add_argument("--output", "-o", required=True,
                         help="Output path for bundle.json")
    p_build.add_argument("--images", "-i", default=None,
                         help="Directory to save extracted figure images")
    p_build.add_argument("--max-pages", type=int, default=200,
                         help="Max pages to scan for figures (default: 200)")

    # inspect
    p_inspect = sub.add_parser("inspect", help="Inspect an existing bundle")
    p_inspect.add_argument("bundle_path", help="Path to bundle.json")

    args = parser.parse_args()

    if args.command == "build":
        bundle = build_bundle(args.pdf_path, args.images, args.max_pages)
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(bundle, f, indent=2, ensure_ascii=False)
        if "error" in bundle:
            print(f"⚠️  {bundle['error']}", file=sys.stderr)
            sys.exit(1)
        print(f"✅ Bundle saved: {out}")
        print(f"   {bundle['figure_count']} figures, "
              f"{len(bundle['toc'])} TOC entries, "
              f"{len(bundle['tables_detected'])} tables, "
              f"{bundle['scanned_page_count']} scanned pages")

    elif args.command == "inspect":
        inspect_bundle(args.bundle_path)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
