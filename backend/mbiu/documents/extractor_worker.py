"""Subprocess worker for in-memory PDF text extraction.

Executes PyMuPDF extraction inside an isolated process with memory caps.
Receives raw PDF bytes over stdin and outputs structured JSON over stdout.
Ensures zero contract storage: no bytes or extracted text touch disk or temp files.
"""

import argparse
import json
import sys
from typing import Any

import pymupdf

from mbiu.documents.errors import (
    EncryptedPDFError,
    ExtractionMemoryError,
    ScannedPDFError,
)

try:
    import psutil

    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


def _apply_memory_limit(max_memory_mb: int) -> None:
    """Set process address space limit on POSIX systems where supported."""
    if sys.platform == "win32":
        return
    try:
        import resource

        limit_bytes = max_memory_mb * 1024 * 1024
        setrlimit = getattr(resource, "setrlimit", None)
        rlimit_as = getattr(resource, "RLIMIT_AS", None)
        if callable(setrlimit) and rlimit_as is not None:
            setrlimit(rlimit_as, (limit_bytes, limit_bytes))
    except ImportError, OSError, ValueError:
        # Ignored on platforms without RLIMIT_AS support
        pass


def _check_memory_usage(max_memory_mb: int) -> None:
    """Check current process memory usage and raise error if limit is exceeded."""
    if _HAS_PSUTIL:
        rss = psutil.Process().memory_info().rss
        if rss > max_memory_mb * 1024 * 1024:
            raise ExtractionMemoryError(
                f"PDF extraction exceeded memory limit of {max_memory_mb} MB."
            )


def extract_pages_dict_from_bytes(
    pdf_bytes: bytes,
    *,
    max_memory_mb: int = 512,
) -> dict[str, Any]:
    """Extract page texts and character offsets in-memory from PDF bytes.

    Args:
        pdf_bytes: Raw bytes of the PDF file.
        max_memory_mb: Maximum allowed resident memory in MB.

    Returns:
        Dictionary with status, pages list, full_text, total_pages, and skipped_pages.

    Raises:
        EncryptedPDFError: If the document is password-protected.
        ScannedPDFError: If all pages lack an extractable text layer.
        ExtractionMemoryError: If resident memory exceeds max_memory_mb.
    """
    _check_memory_usage(max_memory_mb)

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")  # type: ignore[no-untyped-call]
    try:
        if doc.is_encrypted or doc.needs_pass:
            raise EncryptedPDFError()

        total_pages = len(doc)
        pages_data: list[dict[str, Any]] = []
        skipped_pages: list[int] = []
        current_offset = 0

        for page_idx in range(total_pages):
            _check_memory_usage(max_memory_mb)
            page = doc[page_idx]
            page_num = page_idx + 1

            raw_text = str(page.get_text("text"))  # type: ignore[no-untyped-call]
            has_text = bool(raw_text.strip())

            page_text = raw_text if has_text else ""
            start_offset = current_offset
            end_offset = current_offset + len(page_text)
            current_offset = end_offset

            if not has_text:
                skipped_pages.append(page_num)

            pages_data.append(
                {
                    "page_number": page_num,
                    "text": page_text,
                    "start_offset": start_offset,
                    "end_offset": end_offset,
                    "has_text": has_text,
                }
            )

        if total_pages > 0 and len(skipped_pages) == total_pages:
            raise ScannedPDFError()

        full_text = "".join(p["text"] for p in pages_data)

        return {
            "status": "success",
            "pages": pages_data,
            "full_text": full_text,
            "total_pages": total_pages,
            "skipped_pages": skipped_pages,
        }
    finally:
        doc.close()  # type: ignore[no-untyped-call]


def main() -> None:
    """CLI entrypoint for running extraction as an isolated subprocess."""
    parser = argparse.ArgumentParser(description="Mbiu in-memory PDF extraction worker")
    parser.add_argument("--max-memory-mb", type=int, default=512)
    args = parser.parse_args()

    _apply_memory_limit(args.max_memory_mb)

    try:
        pdf_bytes = sys.stdin.buffer.read()
        result = extract_pages_dict_from_bytes(pdf_bytes, max_memory_mb=args.max_memory_mb)
        out_bytes = json.dumps(result).encode("utf-8")
        sys.stdout.buffer.write(out_bytes)
        sys.stdout.buffer.flush()
    except Exception as exc:
        err_payload = {
            "status": "error",
            "error_type": exc.__class__.__name__,
            "message": str(exc),
        }
        out_bytes = json.dumps(err_payload).encode("utf-8")
        sys.stdout.buffer.write(out_bytes)
        sys.stdout.buffer.flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
