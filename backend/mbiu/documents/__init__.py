"""Document processing package for Mbiu.

Provides in-memory upload validation, PyMuPDF-based text extraction,
and clause segmentation for incoming contracts.
"""

from mbiu.documents.extract import (
    ExtractedDocument,
    PageText,
    extract_text_from_pdf,
    extract_text_in_process,
)
from mbiu.documents.segment import (
    Clause,
    DefinedTerm,
    SegmentedDocument,
    segment_document,
    segment_text,
)
from mbiu.documents.upload import UploadValidationResult, validate_upload

__all__ = [
    "Clause",
    "DefinedTerm",
    "ExtractedDocument",
    "PageText",
    "SegmentedDocument",
    "UploadValidationResult",
    "extract_text_from_pdf",
    "extract_text_in_process",
    "segment_document",
    "segment_text",
    "validate_upload",
]
