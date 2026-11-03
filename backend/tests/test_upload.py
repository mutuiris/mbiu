"""Unit tests for document upload validation and constraints.

Verifies file size limits, page count caps, encryption detection, and magic bytes
using purely synthetic in-memory PDFs.
"""

import pytest

from mbiu.documents.errors import (
    EmptyPDFError,
    EncryptedPDFError,
    FileTooLargeError,
    InvalidPDFError,
    PageLimitExceededError,
)
from mbiu.documents.upload import validate_upload
from tests.pdf_factories import (
    create_synthetic_encrypted_pdf,
    create_synthetic_multipage_pdf,
    create_synthetic_text_pdf,
)


def test_valid_pdf_upload() -> None:
    """A valid synthetic PDF passes validation and returns correct metadata."""
    pdf_bytes = create_synthetic_text_pdf(
        [
            "1. Definitions\nNet Receipts means actual cash received.",
            "2. Royalties\n15% royalty on gross receipts.",
        ]
    )
    result = validate_upload(pdf_bytes)

    assert result.total_bytes == len(pdf_bytes)
    assert result.page_count == 2


def test_non_pdf_renamed_as_pdf() -> None:
    """Non-PDF content renamed as .pdf fails magic bytes and raises InvalidPDFError."""
    fake_pdf_data = b"This is a text file maliciously or accidentally named contract.pdf"

    with pytest.raises(InvalidPDFError) as exc_info:
        validate_upload(fake_pdf_data)

    assert exc_info.value.code == "invalid_pdf"
    assert "does not appear to be a valid PDF" in exc_info.value.user_message


def test_empty_bytes_upload() -> None:
    """Empty byte input raises EmptyPDFError."""
    with pytest.raises(EmptyPDFError) as exc_info:
        validate_upload(b"")

    assert exc_info.value.code == "empty_pdf"


def test_corrupted_pdf_structure() -> None:
    """Bytes with %PDF- header but malformed structure raise InvalidPDFError."""
    corrupted_data = b"%PDF-1.7\nCorrupted garbage data that is not a valid PDF trailer."

    with pytest.raises(InvalidPDFError) as exc_info:
        validate_upload(corrupted_data)

    assert exc_info.value.code == "invalid_pdf"


def test_oversize_file_upload() -> None:
    """File exceeding the MAX_UPLOAD_MB limit raises FileTooLargeError."""
    pdf_bytes = create_synthetic_text_pdf(["Synthetic Clause 1"])

    # Enforce a tiny max_upload_mb to trigger error without allocating gigabytes in RAM
    with pytest.raises(FileTooLargeError) as exc_info:
        validate_upload(pdf_bytes, max_upload_mb=0)

    assert exc_info.value.code == "file_too_large"
    assert "larger than Mbiu can check right now" in exc_info.value.user_message


def test_page_cap_exceeded() -> None:
    """PDF exceeding MAX_PAGES limit raises PageLimitExceededError with kind message."""
    pdf_bytes = create_synthetic_multipage_pdf(page_count=5)

    with pytest.raises(PageLimitExceededError) as exc_info:
        validate_upload(pdf_bytes, max_pages=3)

    assert exc_info.value.code == "page_limit_exceeded"
    assert exc_info.value.limit_pages == 3
    assert "limit: 3 pages" in exc_info.value.user_message
    assert (
        exc_info.value.user_message
        == "This file is larger than Mbiu can check right now (limit: 3 pages). Try a smaller file."
    )


def test_encrypted_pdf_rejected() -> None:
    """Encrypted/password-protected PDF raises EncryptedPDFError with exact artist message."""
    encrypted_bytes = create_synthetic_encrypted_pdf(password="secret_pass")

    with pytest.raises(EncryptedPDFError) as exc_info:
        validate_upload(encrypted_bytes)

    assert exc_info.value.code == "encrypted_pdf"
    assert (
        exc_info.value.user_message
        == "This PDF is password-protected. Remove the password and upload it again."
    )
