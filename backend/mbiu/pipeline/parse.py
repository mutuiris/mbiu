"""Parse PDF and DOCX templates with Docling and reject low-quality output."""

import importlib
import io
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mbiu.pipeline.errors import (
    DocumentParseError,
    DocumentQualityError,
    UnsupportedDocumentError,
)
from mbiu.pipeline.models import FetchedDocument, ParsedDocument, ParsedTable

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = frozenset({".pdf", ".docx"})
_REPLACEMENT_CHARACTER = "\ufffd"

_Extractor = Callable[[FetchedDocument], ParsedDocument]


@dataclass(frozen=True)
class ParseQualityPolicy:
    """Thresholds for the fail-closed parser quality gate."""

    min_characters: int = 200
    max_replacement_ratio: float = 0.01
    max_control_ratio: float = 0.02
    min_letter_ratio: float = 0.45
    min_ocr_confidence: float = 0.60


def assess_quality(
    parsed: ParsedDocument,
    policy: ParseQualityPolicy | None = None,
) -> str | None:
    """Return a rejection reason when parsed text is unusable, otherwise None."""
    active = policy or ParseQualityPolicy()
    text = parsed.text.strip()
    if not text:
        return "empty_text"
    if len(text) < active.min_characters:
        return "too_short"
    if parsed.ocr_confidence is not None and parsed.ocr_confidence < active.min_ocr_confidence:
        return "low_ocr_confidence"

    size = len(text)
    replacement_ratio = text.count(_REPLACEMENT_CHARACTER) / size
    if replacement_ratio > active.max_replacement_ratio:
        return "garbled_encoding"

    control_ratio = (
        sum(1 for char in text if not char.isprintable() and char not in "\n\r\t") / size
    )
    if control_ratio > active.max_control_ratio:
        return "garbled_control_characters"

    letter_ratio = sum(1 for char in text if char.isalpha()) / size
    if letter_ratio < active.min_letter_ratio:
        return "garbled_text"
    return None


class DoclingParser:
    """Convert PDF and DOCX files with Docling and enforce the quality gate."""

    def __init__(
        self,
        *,
        extractor: _Extractor | None = None,
        policy: ParseQualityPolicy | None = None,
    ) -> None:
        """Allow a test extractor to replace Docling while keeping the gate active."""
        self._extractor = extractor
        self._policy = policy or ParseQualityPolicy()

    def parse(self, document: FetchedDocument) -> ParsedDocument:
        """Parse ``document`` and reject garbled or low-confidence results.

        Raises:
            UnsupportedDocumentError: If the filename is not PDF or DOCX.
            DocumentParseError: If Docling fails.
            DocumentQualityError: If the quality gate rejects the output.
        """
        if Path(document.filename).suffix.lower() not in SUPPORTED_SUFFIXES:
            raise UnsupportedDocumentError(f"unsupported template type: {document.filename}")

        extractor = self._extractor or _extract_with_docling
        try:
            parsed = extractor(document)
        except DocumentParseError:
            raise
        except Exception as exc:
            raise DocumentParseError(f"Docling could not parse {document.filename}") from exc

        reason = assess_quality(parsed, self._policy)
        if reason is not None:
            raise DocumentQualityError(reason)
        return parsed


def _extract_with_docling(document: FetchedDocument) -> ParsedDocument:
    try:
        converter_module = importlib.import_module("docling.document_converter")
        base_models = importlib.import_module("docling.datamodel.base_models")
    except ImportError as exc:
        raise DocumentParseError("Docling is not installed in this environment") from exc

    try:
        converter = converter_module.DocumentConverter()
        stream = base_models.DocumentStream(
            name=document.filename,
            stream=io.BytesIO(document.content),
        )
        result = converter.convert(stream)
        doc = result.document
        text = str(doc.export_to_markdown())
    except Exception as exc:
        raise DocumentParseError(f"Docling could not parse {document.filename}") from exc

    return ParsedDocument(
        text=text,
        headings=_headings(doc),
        tables=_tables(doc),
        page_count=_page_count(doc),
        ocr_confidence=_ocr_confidence(doc),
    )


def _headings(doc: Any) -> list[str]:
    headings: list[str] = []
    texts = _attr(doc, "texts", [])
    if not isinstance(texts, (list, tuple)):
        return headings
    for item in texts:
        label = _attr(item, "label", "")
        label_name = _attr(label, "value", label)
        if not isinstance(label_name, str):
            continue
        lowered = label_name.lower()
        if "heading" not in lowered and "title" not in lowered:
            continue
        text = _attr(item, "text", "")
        if isinstance(text, str) and text.strip():
            headings.append(text.strip())
    return headings


def _tables(doc: Any) -> list[ParsedTable]:
    tables: list[ParsedTable] = []
    raw_tables = _attr(doc, "tables", [])
    if not isinstance(raw_tables, (list, tuple)):
        return tables
    for table in raw_tables:
        try:
            frame = table.export_to_dataframe()
            rows = [[str(cell) for cell in row] for row in frame.values.tolist()]
        except Exception:
            logger.warning("Skipping a table Docling could not export")
            continue
        if rows:
            tables.append(ParsedTable(rows=rows))
    return tables


def _page_count(doc: Any) -> int:
    pages = _attr(doc, "pages", None)
    if isinstance(pages, (list, tuple, dict)) and pages:
        return len(pages)
    return 1


def _ocr_confidence(doc: Any) -> float | None:
    value = _attr(doc, "ocr_confidence", None)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _attr(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)
