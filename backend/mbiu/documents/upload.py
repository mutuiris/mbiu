"""In-memory upload validation for PDF contracts.

Enforces zero-storage security constraints: validates PDF magic bytes,
enforces file size caps, page count caps, and detects encryption/password protection
entirely in memory before any extraction or model processing.
"""

from dataclasses import dataclass

import pymupdf
from django.conf import settings

from mbiu.documents.errors import (
    EmptyPDFError,
    EncryptedPDFError,
    FileTooLargeError,
    InvalidPDFError,
    PageLimitExceededError,
)

PDF_MAGIC_BYTES = b"%PDF-"


@dataclass(frozen=True)
class UploadValidationResult:
    """Metadata describing a validated PDF document.

    Attributes:
        total_bytes: Total document size in bytes.
        page_count: Total number of pages in the PDF.
    """

    total_bytes: int
    page_count: int


def validate_upload(
    data: bytes,
    *,
    max_upload_mb: int | None = None,
    max_pages: int | None = None,
) -> UploadValidationResult:
    """Validate uploaded PDF bytes purely in memory against system limits.

    Never writes bytes to disk or temp files. Rejects invalid files with plain-language,
    artist-friendly error messages before any expensive processing or model calls.

    Args:
        data: Raw uploaded document bytes.
        max_upload_mb: Optional override for the maximum allowed upload size in MB.
            Defaults to settings.MAX_UPLOAD_MB.
        max_pages: Optional override for maximum allowed page count.
            Defaults to settings.MAX_PAGES.

    Returns:
        UploadValidationResult containing total byte length and page count.

    Raises:
        EmptyPDFError: If data is empty or page count is 0.
        FileTooLargeError: If data exceeds configured size in megabytes.
        InvalidPDFError: If magic bytes are invalid or PDF structure is corrupted.
        EncryptedPDFError: If document is password-protected or encrypted.
        PageLimitExceededError: If page count exceeds maximum allowable limit.
    """
    if not data:
        raise EmptyPDFError("The uploaded file is empty. Please upload a valid contract.")

    effective_max_mb = (
        max_upload_mb if max_upload_mb is not None else getattr(settings, "MAX_UPLOAD_MB", 10)
    )
    max_bytes = effective_max_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise FileTooLargeError(limit_mb=effective_max_mb)

    # Magic byte check: valid PDFs start with %PDF- header
    if not data.startswith(PDF_MAGIC_BYTES):
        raise InvalidPDFError(
            "This file does not appear to be a valid PDF document. "
            "Please check the file and upload it again."
        )

    # In-memory document inspection via PyMuPDF stream
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")  # type: ignore[no-untyped-call]
    except Exception as exc:
        raise InvalidPDFError(
            "This file does not appear to be a valid PDF document. "
            "Please check the file and upload it again."
        ) from exc

    try:
        if doc.is_encrypted or doc.needs_pass:
            raise EncryptedPDFError()

        page_count = len(doc)
        if page_count == 0:
            raise EmptyPDFError()

        effective_max_pages = (
            max_pages if max_pages is not None else getattr(settings, "MAX_PAGES", 40)
        )
        if page_count > effective_max_pages:
            raise PageLimitExceededError(limit_pages=effective_max_pages)

        return UploadValidationResult(
            total_bytes=len(data),
            page_count=page_count,
        )
    finally:
        doc.close()  # type: ignore[no-untyped-call]
