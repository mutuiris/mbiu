"""Unit tests for safe in-memory PDF text extraction.

Enforces zero-storage invariants (verifying 0 temp files written during extraction),
subprocess isolation, timeout budgets, memory ceilings, and scanned/image page detection.
"""

import tempfile
from pathlib import Path

import pytest

from mbiu.documents.errors import (
    EncryptedPDFError,
    ExtractionMemoryError,
    ExtractionTimeoutError,
    ScannedPDFError,
)
from mbiu.documents.extract import extract_text_from_pdf, extract_text_in_process
from tests.pdf_factories import (
    create_synthetic_encrypted_pdf,
    create_synthetic_scanned_pdf,
    create_synthetic_text_pdf,
)


def test_extract_valid_text_pdf() -> None:
    """Valid synthetic contract extracts page texts with exact character offsets."""
    page1 = "1. Grant of Rights\nThe Artist grants exclusive distribution rights."
    page2 = "2. Recoupment\nRecording costs shall be recoupable from artist royalties only."

    pdf_bytes = create_synthetic_text_pdf([page1, page2])
    extracted = extract_text_from_pdf(pdf_bytes, page_count=2)

    assert extracted.total_pages == 2
    assert extracted.skipped_pages == []
    assert len(extracted.pages) == 2

    p1, p2 = extracted.pages
    assert p1.page_number == 1
    assert p1.has_text is True
    assert "Grant of Rights" in p1.text
    assert extracted.full_text[p1.start_offset : p1.end_offset] == p1.text

    assert p2.page_number == 2
    assert p2.has_text is True
    assert "Recoupment" in p2.text
    assert extracted.full_text[p2.start_offset : p2.end_offset] == p2.text

    assert extracted.full_text == p1.text + p2.text


def test_extract_scanned_pdf_raises_error() -> None:
    """An image-only synthetic PDF with no text layer raises ScannedPDFError with kind message."""
    pdf_bytes = create_synthetic_scanned_pdf(page_count=2)

    with pytest.raises(ScannedPDFError) as exc_info:
        extract_text_from_pdf(pdf_bytes, page_count=2)

    assert exc_info.value.code == "scanned_pdf"
    assert (
        exc_info.value.user_message == "This PDF is a photo or scan, so Mbiu can't read the text. "
        "If you have the original document file, upload that instead."
    )


def test_extract_partially_scanned_pdf_tracks_skipped_pages() -> None:
    """PDF with a scanned page between text pages tracks the scanned page in skipped_pages."""
    import pymupdf

    doc = pymupdf.open()
    try:
        # Page 1: Text
        p1 = doc.new_page()
        p1.insert_text((50, 72), "Clause 1: Scope of Engagement")

        # Page 2: Image/drawing only (no text)
        p2 = doc.new_page()
        p2.draw_rect(pymupdf.Rect(50, 50, 300, 300), color=(0.1, 0.1, 0.1), fill=(0.8, 0.8, 0.8))

        # Page 3: Text
        p3 = doc.new_page()
        p3.insert_text((50, 72), "Clause 2: Compensation")

        pdf_bytes = bytes(doc.tobytes())
    finally:
        doc.close()

    extracted = extract_text_from_pdf(pdf_bytes, page_count=3)

    assert extracted.total_pages == 3
    assert extracted.skipped_pages == [2]
    assert len(extracted.pages) == 3

    assert extracted.pages[0].has_text is True
    assert extracted.pages[1].has_text is False
    assert extracted.pages[1].text == ""
    assert extracted.pages[2].has_text is True

    # Slices still match full_text perfectly
    for page in extracted.pages:
        assert extracted.full_text[page.start_offset : page.end_offset] == page.text


def test_extract_encrypted_pdf() -> None:
    """Encrypted PDF raises EncryptedPDFError during extraction."""
    encrypted_bytes = create_synthetic_encrypted_pdf(password="secret")

    with pytest.raises(EncryptedPDFError) as exc_info:
        extract_text_from_pdf(encrypted_bytes, page_count=1)

    assert exc_info.value.code == "encrypted_pdf"


def test_extract_timeout_handling() -> None:
    """Extraction exceeding configured time budget raises ExtractionTimeoutError."""
    pdf_bytes = create_synthetic_text_pdf(["Some synthetic contract text for timeout test."])

    # Enforce an impossibly tiny timeout to trigger timeout handling in the subprocess
    with pytest.raises(ExtractionTimeoutError) as exc_info:
        extract_text_from_pdf(pdf_bytes, page_count=1, timeout_s=0.000001)

    assert exc_info.value.code == "extraction_timeout"
    assert "took longer than expected" in exc_info.value.user_message


def test_extract_memory_limit_handling() -> None:
    """Worker exceeding memory limit raises ExtractionMemoryError."""
    pdf_bytes = create_synthetic_text_pdf(["Memory limit synthetic test."])

    # Enforce a 1 MB limit which resident Python process immediately exceeds
    with pytest.raises(ExtractionMemoryError) as exc_info:
        extract_text_from_pdf(pdf_bytes, page_count=1, max_memory_mb=1)

    assert exc_info.value.code == "extraction_memory_limit"
    assert "exceeded" in exc_info.value.user_message


def test_zero_contract_storage_in_temp_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Zero Contract Storage invariant: verify 0 files are written to temp directory."""
    isolated_temp = tmp_path / "extraction_temp"
    isolated_temp.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("TEMP", str(isolated_temp))
    monkeypatch.setenv("TMP", str(isolated_temp))
    monkeypatch.setattr(tempfile, "tempdir", str(isolated_temp))

    canary_text = "CANARY_CONFIDENTIAL_INVARIANT_ZERO_STORAGE_12345"
    pdf_bytes = create_synthetic_text_pdf(
        [
            "Strict Zero Contract Storage Invariant Verification.",
            f"No contract text ({canary_text}) must ever be written to disk or temp directories.",
        ]
    )

    extracted = extract_text_from_pdf(pdf_bytes, page_count=2)
    assert extracted.total_pages == 2

    # Verify isolated temp directory remains empty of any extraction files
    # (ignoring OS/antivirus hooks like _avast_ if present)
    created_files = [f for f in isolated_temp.iterdir() if f.name != "_avast_"]
    assert created_files == [], f"Temp directory leaked files during extraction: {created_files}"

    # Also verify in-process extraction is strictly memory-only
    in_process_extracted = extract_text_in_process(pdf_bytes)
    assert in_process_extracted.total_pages == 2

    created_files_after_in_process = [f for f in isolated_temp.iterdir() if f.name != "_avast_"]
    assert created_files_after_in_process == [], (
        f"In-process extraction leaked files: {created_files_after_in_process}"
    )


def test_extract_in_process() -> None:
    """Direct in-process extraction extracts text accurately without spawning subprocess."""
    page_text = "Clause 1. Master Recording Rights"
    pdf_bytes = create_synthetic_text_pdf([page_text])

    extracted = extract_text_in_process(pdf_bytes)

    assert extracted.total_pages == 1
    assert extracted.skipped_pages == []
    assert len(extracted.pages) == 1
    assert "Master Recording Rights" in extracted.pages[0].text
    assert extracted.full_text == extracted.pages[0].text
