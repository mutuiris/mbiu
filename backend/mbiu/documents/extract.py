"""Safe in-memory PDF text extraction using PyMuPDF in an isolated subprocess.

Enforces zero-storage invariants: bytes are extracted strictly in memory.
Enforces reliability invariants: limits memory allocation and sets an adaptive timeout
that scales with the page count. Pages without a text layer are explicitly tracked as skipped.
"""

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from mbiu.documents.errors import (
    EncryptedPDFError,
    ExtractionFailedError,
    ExtractionMemoryError,
    ExtractionTimeoutError,
    ScannedPDFError,
)
from mbiu.documents.extractor_worker import extract_pages_dict_from_bytes


@dataclass(frozen=True)
class PageText:
    """Extracted text and character offsets for a single PDF page.

    Attributes:
        page_number: 1-indexed page number.
        text: Raw extracted text of the page.
        start_offset: Character start offset within full combined document text.
        end_offset: Character end offset within full combined document text.
        has_text: True if page contains an extractable text layer, False if blank or scanned.
    """

    page_number: int
    text: str
    start_offset: int
    end_offset: int
    has_text: bool


@dataclass(frozen=True)
class ExtractedDocument:
    """Complete in-memory text extraction result for a contract PDF.

    Attributes:
        pages: List of PageText objects for all pages in order.
        full_text: Concatenated raw text of all pages in the document.
        total_pages: Total number of pages inspected.
        skipped_pages: 1-indexed page numbers of pages lacking an extractable text layer.
    """

    pages: list[PageText]
    full_text: str
    total_pages: int
    skipped_pages: list[int]


def extract_text_in_process(
    pdf_bytes: bytes,
    *,
    max_memory_mb: int = 512,
) -> ExtractedDocument:
    """Extract PDF text directly in the current process.

    Useful for in-memory unit tests or lightweight extraction where process
    isolation is handled by an external container boundary.

    Args:
        pdf_bytes: Raw bytes of the PDF contract.
        max_memory_mb: Memory ceiling in megabytes.

    Returns:
        ExtractedDocument containing pages, full text, and skipped pages.

    Raises:
        EncryptedPDFError: If PDF is encrypted.
        ScannedPDFError: If all pages lack a text layer.
        ExtractionMemoryError: If memory ceiling is exceeded.
    """
    data = extract_pages_dict_from_bytes(pdf_bytes, max_memory_mb=max_memory_mb)
    pages = [
        PageText(
            page_number=p["page_number"],
            text=p["text"],
            start_offset=p["start_offset"],
            end_offset=p["end_offset"],
            has_text=p["has_text"],
        )
        for p in data["pages"]
    ]
    return ExtractedDocument(
        pages=pages,
        full_text=data["full_text"],
        total_pages=data["total_pages"],
        skipped_pages=data["skipped_pages"],
    )


def extract_text_from_pdf(
    pdf_bytes: bytes,
    *,
    page_count: int | None = None,
    base_timeout_s: float = 10.0,
    per_page_timeout_s: float = 0.5,
    max_memory_mb: int = 512,
    timeout_s: float | None = None,
    use_subprocess: bool = True,
) -> ExtractedDocument:
    """Extract text and character offsets from PDF bytes in an isolated subprocess.

    Spawns a worker subprocess that processes the PDF purely in memory, enforcing
    both a page-scaled time limit and a resident memory ceiling.

    Args:
        pdf_bytes: Raw bytes of the uploaded PDF contract.
        page_count: Optional page count (e.g. from upload validation) to scale timeout.
        base_timeout_s: Base timeout budget in seconds (default 10.0s).
        per_page_timeout_s: Additional timeout budget per page in seconds (default 0.5s).
        max_memory_mb: Maximum memory allowed for the extraction worker (default 512MB).
        timeout_s: Explicit timeout override in seconds.
        use_subprocess: If False, extracts directly in-process.

    Returns:
        ExtractedDocument containing page details, character offsets, and skipped pages.

    Raises:
        ExtractionTimeoutError: If extraction exceeds the calculated time limit.
        ExtractionMemoryError: If worker exceeds memory limit.
        ScannedPDFError: If all pages in the PDF are photos/scans lacking text layers.
        EncryptedPDFError: If document is password-protected.
        ExtractionFailedError: If worker encounters an unexpected crash or error.
    """
    if not use_subprocess:
        return extract_text_in_process(pdf_bytes, max_memory_mb=max_memory_mb)

    effective_timeout: float
    if timeout_s is not None:
        effective_timeout = timeout_s
    elif page_count is not None:
        effective_timeout = max(base_timeout_s, base_timeout_s + (page_count * per_page_timeout_s))
    else:
        # Fallback to standard 40-page budget ceiling
        effective_timeout = base_timeout_s + (40 * per_page_timeout_s)

    backend_dir = Path(__file__).resolve().parents[2]
    worker_env = os.environ.copy()
    existing_pythonpath = worker_env.get("PYTHONPATH", "")
    worker_env["PYTHONPATH"] = (
        f"{backend_dir}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(backend_dir)
    )

    cmd = [
        sys.executable,
        "-m",
        "mbiu.documents.extractor_worker",
        "--max-memory-mb",
        str(max_memory_mb),
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=worker_env,
        )
    except Exception as exc:
        raise ExtractionFailedError(
            f"Failed to spawn PDF extraction worker subprocess: {exc}"
        ) from exc

    try:
        stdout_bytes, stderr_bytes = proc.communicate(
            input=pdf_bytes,
            timeout=effective_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        proc.communicate()
        raise ExtractionTimeoutError() from exc

    if proc.returncode != 0:
        # Attempt to parse structured error JSON from stdout
        if stdout_bytes:
            try:
                err_data = json.loads(stdout_bytes.decode("utf-8"))
                err_type = err_data.get("error_type")
                if err_type == "ScannedPDFError":
                    raise ScannedPDFError()
                if err_type == "EncryptedPDFError":
                    raise EncryptedPDFError()
                if err_type in ("ExtractionMemoryError", "MemoryError"):
                    raise ExtractionMemoryError()
                raise ExtractionFailedError(
                    details=err_data.get("message", "Extraction worker failed.")
                )
            except json.JSONDecodeError, KeyError:
                pass

        # Check stderr or return code for memory signals
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")
        if "MemoryError" in stderr_text or proc.returncode in (-9, 137, 3221225477):
            raise ExtractionMemoryError()

        raise ExtractionFailedError(
            details=f"PDF extraction worker exited with error code {proc.returncode}."
        )

    try:
        data = json.loads(stdout_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ExtractionFailedError(details="Invalid extraction worker output format.") from exc

    pages = [
        PageText(
            page_number=p["page_number"],
            text=p["text"],
            start_offset=p["start_offset"],
            end_offset=p["end_offset"],
            has_text=p["has_text"],
        )
        for p in data["pages"]
    ]

    total_pages = int(data["total_pages"])
    skipped_pages = [int(p) for p in data["skipped_pages"]]

    if total_pages > 0 and len(skipped_pages) == total_pages:
        raise ScannedPDFError()

    return ExtractedDocument(
        pages=pages,
        full_text=str(data["full_text"]),
        total_pages=total_pages,
        skipped_pages=skipped_pages,
    )
