"""Render synthetic contracts to real PDFs with page provenance.

PyMuPDF is already the repository's PDF library. Text is inserted line by line
so the builder knows which page each clause occupies, which is what the ground
truth sidecar records.
"""

from __future__ import annotations

import textwrap
from collections.abc import Sequence
from dataclasses import dataclass

import pymupdf

from evals.generator.templates import TemplateClauseSpec

PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0
LEFT_MARGIN = 60.0
TOP_MARGIN = 72.0
BOTTOM_MARGIN = 60.0
BODY_SIZE = 10.0
HEADING_SIZE = 11.0
LINE_HEIGHT = 14.0
WRAP_WIDTH = 92
FIXED_CREATION_DATE = "D:20260101000000Z"


@dataclass(frozen=True)
class RenderedPdf:
    """Rendered PDF bytes plus the pages each clause occupies."""

    content: bytes
    clause_pages: dict[str, tuple[int, ...]]
    page_count: int


class _PageWriter:
    """A very small top-down text layout engine for synthetic contracts."""

    def __init__(self, document: pymupdf.Document) -> None:
        self._document = document
        self._page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        self._page_number = 1
        self._y = TOP_MARGIN

    @property
    def page_number(self) -> int:
        """The one-based number of the page currently being written."""
        return self._page_number

    def ensure_space(self, line_count: int = 1) -> None:
        """Start a new page when ``line_count`` more lines would overflow."""
        if self._y + line_count * LINE_HEIGHT > PAGE_HEIGHT - BOTTOM_MARGIN:
            self._page = self._document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            self._page_number += 1
            self._y = TOP_MARGIN

    def heading(self, text: str) -> None:
        """Write a bold contract heading."""
        self.ensure_space(2)
        self._page.insert_text(
            (LEFT_MARGIN, self._y),
            text,
            fontname="hebo",
            fontsize=HEADING_SIZE,
        )
        self._y += LINE_HEIGHT + 2

    def line(
        self, text: str, *, fontname: str = "helv", size: float = BODY_SIZE
    ) -> None:
        """Write one already-wrapped line."""
        self.ensure_space()
        self._page.insert_text(
            (LEFT_MARGIN, self._y), text, fontname=fontname, fontsize=size
        )
        self._y += LINE_HEIGHT

    def paragraph(self, text: str) -> None:
        """Wrap and write a paragraph."""
        for line in textwrap.wrap(
            text,
            width=WRAP_WIDTH,
            break_long_words=False,
            break_on_hyphens=False,
        ):
            self.line(line)

    def blank(self, lines: float = 1.0) -> None:
        """Advance the cursor without writing text."""
        self._y += LINE_HEIGHT * lines


def render_contract(title: str, clauses: Sequence[TemplateClauseSpec]) -> RenderedPdf:
    """Render one synthetic contract and record each clause's page span."""
    document = pymupdf.open()  # type: ignore[no-untyped-call]
    try:
        document.set_metadata(
            {
                "title": title,
                "author": "Mbiu synthetic contract generator",
                "subject": "Golden set; synthetic only",
                "keywords": "synthetic, evaluation, recording agreement",
                "creator": "evals.generator.build",
                "producer": "PyMuPDF",
                "creationDate": FIXED_CREATION_DATE,
                "modDate": FIXED_CREATION_DATE,
            }
        )
        writer = _PageWriter(document)
        writer.heading("SYNTHETIC RECORDING AGREEMENT")
        writer.line("Golden set. Synthetic only. Not a real contract.", size=9)
        writer.blank()
        writer.paragraph(title)
        writer.paragraph(
            "This synthetic agreement is generated from the reviewed recording template "
            "so that its correct evaluation is known by construction."
        )
        writer.blank()

        clause_pages: dict[str, tuple[int, ...]] = {}
        for clause in clauses:
            writer.ensure_space(3)
            start_page = writer.page_number
            writer.heading(f"{clause.clause_id} {clause.heading}")
            writer.paragraph(clause.text)
            writer.blank(0.5)
            end_page = writer.page_number
            clause_pages[clause.clause_id] = tuple(range(start_page, end_page + 1))

        content = bytes(
            document.tobytes(  # type: ignore[no-untyped-call]
                garbage=4, deflate=True, clean=True, no_new_id=True
            )
        )
        return RenderedPdf(
            content=content,
            clause_pages=clause_pages,
            page_count=writer.page_number,
        )
    finally:
        document.close()  # type: ignore[no-untyped-call]
