"""Document processing package for Mbiu.

Provides in-memory upload validation, PyMuPDF-based text extraction,
and clause segmentation for incoming contracts.
"""

import sys

# pymupdf imports its optional add-ons (and onnxruntime) when they are installed.
# Mbiu uses neither, and on a slow CPU they take over a minute to load.
for _addon in ("pymupdf.layout", "pymupdf4llm"):
    sys.modules.setdefault(_addon, None)  # type: ignore[arg-type]

from mbiu.documents.extract import (  # noqa: E402
    ExtractedDocument,
    PageText,
    extract_text_from_pdf,
    extract_text_in_process,
)
from mbiu.documents.segment import (  # noqa: E402
    Clause,
    DefinedTerm,
    SegmentedDocument,
    segment_document,
    segment_text,
)
from mbiu.documents.upload import UploadValidationResult, validate_upload  # noqa: E402

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
