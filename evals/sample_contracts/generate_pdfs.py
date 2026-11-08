"""Render sample evaluation contracts from Markdown into multi-page text-based PDFs.

Generates clean, multi-page PDF documents with proper typography, headers,
footers, and clause numbering so they can be uploaded directly into the Mbiu
web UI or evaluation API.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pymupdf

BASE_DIR = Path(__file__).resolve().parent
MD_DIR = BASE_DIR / "markdown"
PDF_DIR = BASE_DIR / "pdf"

# A4 dimensions in points (595 x 842)
PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0
MARGIN_X = 54.0
MARGIN_TOP = 60.0
MARGIN_BOTTOM = 60.0
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN_X)


def strip_md_inline(text: str) -> str:
    """Strip inline Markdown markers (**bold**, *italic*, `code`) for clean plain text."""
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


def wrap_line(text: str, fontname: str, fontsize: float, max_width: float) -> list[str]:
    """Word-wrap a single paragraph to fit within max_width points."""
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        w = float(
            pymupdf.get_text_length(candidate, fontname=fontname, fontsize=fontsize)
        )
        if w <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def render_markdown_to_pdf(md_path: Path, pdf_path: Path) -> tuple[int, int]:
    """Render a Markdown contract file into a paginated text-based PDF.

    Returns:
        Tuple of (page_count, character_count).
    """
    raw_md = md_path.read_text(encoding="utf-8")
    lines = raw_md.splitlines()

    open_pdf: Any = pymupdf.open
    doc: Any = open_pdf()
    page: Any = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = MARGIN_TOP

    def new_page() -> Any:
        nonlocal page, y
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        y = MARGIN_TOP
        return page

    def ensure_space(needed: float) -> None:
        nonlocal y
        if y + needed > PAGE_HEIGHT - MARGIN_BOTTOM:
            new_page()

    for raw_line in lines:
        stripped = raw_line.strip()

        # Horizontal rule
        if stripped == "---":
            ensure_space(16)
            y += 6
            page.draw_line(
                (MARGIN_X, y),
                (PAGE_WIDTH - MARGIN_X, y),
                color=(0.75, 0.75, 0.75),
                width=0.6,
            )
            y += 10
            continue

        # Blank line
        if not stripped:
            y += 6
            continue

        # H1 Title (# ...)
        if stripped.startswith("# "):
            title_text = strip_md_inline(stripped[2:].strip())
            fontname = "helv"
            fontsize = 13.0
            wrapped = wrap_line(title_text, fontname, fontsize, CONTENT_WIDTH)
            ensure_space(len(wrapped) * 18 + 10)
            for wline in wrapped:
                page.insert_text(
                    (MARGIN_X, y + fontsize),
                    wline,
                    fontname=fontname,
                    fontsize=fontsize,
                )
                y += 18
            y += 6
            continue

        # H2 Section Heading (## ...)
        if stripped.startswith("## "):
            h2_text = strip_md_inline(stripped[3:].strip())
            fontname = "helv"
            fontsize = 11.0
            wrapped = wrap_line(h2_text, fontname, fontsize, CONTENT_WIDTH)
            ensure_space(len(wrapped) * 16 + 12)
            y += 4
            for wline in wrapped:
                page.insert_text(
                    (MARGIN_X, y + fontsize),
                    wline,
                    fontname=fontname,
                    fontsize=fontsize,
                )
                y += 15
            y += 4
            continue

        # Markdown Table Row (| ... |)
        if stripped.startswith("|") and stripped.endswith("|"):
            if re.match(r"^\|\s*[:\-]+", stripped):
                continue
            cells = [strip_md_inline(c.strip()) for c in stripped.strip("|").split("|")]
            row_text = "  |  ".join(cells)
            fontname = "helv"
            fontsize = 8.5
            wrapped = wrap_line(row_text, fontname, fontsize, CONTENT_WIDTH - 10)
            ensure_space(len(wrapped) * 12 + 4)
            for wline in wrapped:
                page.insert_text(
                    (MARGIN_X + 6, y + fontsize),
                    wline,
                    fontname=fontname,
                    fontsize=fontsize,
                )
                y += 12
            y += 2
            continue

        # Bullet / Sub-clause line
        indent = 0.0
        if stripped.startswith("- ") or re.match(r"^\([a-z0-9]+\)\s+", stripped):
            indent = 14.0

        clean_text = strip_md_inline(stripped)
        fontname = "helv"
        fontsize = 9.5
        line_height = 13.5
        wrapped = wrap_line(clean_text, fontname, fontsize, CONTENT_WIDTH - indent)
        ensure_space(len(wrapped) * line_height + 2)
        for wline in wrapped:
            page.insert_text(
                (MARGIN_X + indent, y + fontsize),
                wline,
                fontname=fontname,
                fontsize=fontsize,
            )
            y += line_height
        y += 2

    # Add page numbers in footer
    total_pages = len(doc)
    extracted_pages: list[str] = []
    for idx in range(total_pages):
        p: Any = doc[idx]
        footer = f"Page {idx + 1} of {total_pages}  |  Artist Copy: John Doe"
        p.insert_text(
            (MARGIN_X, PAGE_HEIGHT - 28),
            footer,
            fontname="helv",
            fontsize=8.0,
            color=(0.4, 0.4, 0.4),
        )
        extracted_pages.append(str(p.get_text("text")))

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(bytes(doc.tobytes()))
    full_text = "\n".join(extracted_pages)
    doc.close()
    return total_pages, len(full_text)


def main() -> None:
    """Render all Markdown contracts in markdown/ to pdf/."""
    md_files = sorted(MD_DIR.glob("*.md"))
    if not md_files:
        raise RuntimeError(f"No markdown files found in {MD_DIR}")

    for md_file in md_files:
        pdf_file = PDF_DIR / f"{md_file.stem}.pdf"
        pages, chars = render_markdown_to_pdf(md_file, pdf_file)
        sys.stdout.write(f"Generated {pdf_file.name}: {pages} pages, {chars:,} chars\n")


if __name__ == "__main__":
    main()
