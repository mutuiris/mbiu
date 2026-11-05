# Code Review: MB-02 — Upload checks & safe PDF text extraction

> **Date:** 2026-11-03  
> **Ticket Owner:** Steve  
> **Reviewer:** Mbiu Code Reviewer  
> **Branch:** `feat/mbiu-build`  
> **Status:** ✅ Approved

## Files Reviewed
| File | Purpose |
|---|---|
| `backend/mbiu/documents/upload.py` | In-memory upload validation (%PDF- magic bytes, size cap, page cap, encryption check) |
| `backend/mbiu/documents/errors.py` | Typed domain exception hierarchy with kind, plain-language artist messages |
| `backend/mbiu/documents/extract.py` | Isolated subprocess orchestrator for in-memory text extraction with timeout and memory budgets |
| `backend/mbiu/documents/extractor_worker.py` | Worker subprocess executing PyMuPDF extraction over stdin/stdout pipes |
| `backend/mbiu/security/turnstile.py` | Cloudflare Turnstile bot verification service (sync & async, dev test keys, injected clients) |
| `backend/config/settings.py` | Added `MAX_UPLOAD_MB`, `MAX_PAGES`, `TURNSTILE_SECRET_KEY`, `TURNSTILE_VERIFY_URL` |
| `.env.example` | Added environment variable defaults for upload limits and Turnstile verification |
| `backend/pyproject.toml` | Pinned `pymupdf` and `httpx` dependencies adhering to the 14-day rule; configured mypy overrides |
| `backend/tests/pdf_factories.py` | Synthetic in-memory PDF factories (text, scanned/rectangles, encrypted, multi-page) |
| `backend/tests/test_upload.py` | Unit tests for upload validation constraints (magic bytes, limits, encryption) |
| `backend/tests/test_extract.py` | Unit tests for PDF extraction, offsets, timeouts, memory limits, and zero temp file leakage |
| `backend/tests/test_turnstile.py` | Unit tests for Turnstile token verification (fast-paths, mock HTTP transports, errors) |

## Summary
The implementation of ticket **MB-02** adheres rigorously to all Mbiu architectural requirements, zero-contract-storage invariants, and privacy constraints. PDF validation and extraction operate strictly in-memory using OS pipe streams without writing any bytes to disk or temporary files. Error messages provide empathetic, plain-language explanations for Kenyan musicians without leaking technical jargon or raw document data. The test suite is 100% synthetic, thoroughly covering edge cases (scanned documents, memory caps, time budgets, corrupted headers, and encryption), and all verification gates (`just test`, `just lint`, `just typecheck`) pass cleanly.

## ✅ What's Good
| Aspect | Notes |
|---|---|
| Privacy & Invariants | Strict conformance to the Zero Contract Storage invariant: PyMuPDF operates on in-memory byte buffers (`stream=data`). Subprocess isolation uses OS stdin/stdout pipes without temporary intermediate files. Verified by `test_zero_contract_storage_in_temp_directory` asserting 0 leaked files in `$TEMP`. |
| Architectural Compliance | Implements all requirements from Section 2 ("Upload and check", "Extract text") and "Reliability" of `Mbiu_ system architecture and tooling.md`. Extraction timeout dynamically scales with page count (`base_timeout_s + page_count * per_page_timeout_s`). Scanned/image-only pages are explicitly recorded in `skipped_pages` rather than dropped silently. Fully scanned PDFs raise `ScannedPDFError`. |
| Substring Invariants | `PageText` objects maintain exact character offsets guaranteeing `full_text[page.start_offset:page.end_offset] == page.text`, ensuring downstream clause segmentation (MB-03) has mathematically exact substring coordinates for model quote verification. |
| Bot Protection | `turnstile.py` supports both sync and async verification, cleanly handles Cloudflare's always-pass (`1x0000000000000000000000000000000AA`) and always-fail (`2x0000000000000000000000000000000AA`) test keys for offline development and hermetic CI testing, and accepts custom `httpx.Client`/`AsyncClient` instances for mocking. |
| Test Quality & Synthetic Data | Entirely synthetic test contracts created programmatically in memory via `tests/pdf_factories.py`. Zero real contracts used. Comprehensive edge case testing across corrupted magic bytes, page limits, memory ceilings, subprocess timeouts, and network failures. |
| Code Hygiene & Types | Strict type annotations throughout passing `mypy --strict`. Clean Google docstrings and 100% compliance with `ruff` and `eslint`. |

## ⚠️ Issues to Fix
1. **Preserve Default Artist Message on Worker Extraction Failure**
   - **Priority:** Low (Non-blocking refinement)
   - **File:** `backend/mbiu/documents/extract.py#L200` and `backend/mbiu/documents/extract.py#L209`
   - **Reference:** Section 2 ("Upload and check") in `Mbiu_ system architecture and tooling.md`
   - **Explanation:** In `extract_text_from_pdf`, when the worker subprocess exits unexpectedly or returns an unclassified error, `ExtractionFailedError` is instantiated with the raw technical string (e.g., `err_data.get("message")` or `f"PDF extraction worker exited with error code {proc.returncode}."`). Because `ExtractionFailedError` passes its first argument directly to `DocumentError.user_message`, any low-level exception details could become the musician-facing message instead of the kind default (`"Mbiu was unable to extract text from this PDF. Please check the document format and try again."`).
   - **Action Required:** Keep the default kind `user_message` for `ExtractionFailedError` and store technical exception messages in a distinct `technical_details` attribute or log field when wiring up error responses in MB-05.
   - [x] Fixed

## Code Quality Scores
| Metric | Score | Notes |
|---|---|---|
| Readability & Structure | ⭐⭐⭐⭐⭐ | Exceptionally clear separation between validation, subprocess worker, and public extraction API. |
| Test Coverage & Quality | ⭐⭐⭐⭐⭐ | 26 unit tests covering all edge cases, fault injection (memory limit, timeout, corruption), and zero temp file leakage. |
| Privacy & Invariants Compliance | ⭐⭐⭐⭐⭐ | Strictly memory-only, no disk I/O, no logging of contract text or filenames, synthetic test data only. |
| Architectural Alignment | ⭐⭐⭐⭐⭐ | Exact adherence to Mbiu system architecture specifications and reliable time/memory budgets. |
| Error Handling & Resilience | ⭐⭐⭐⭐⭐ | Artist-friendly, empathetic error messages matching specification verbatim. Subprocess timeouts properly killed. |

## Acceptance Criteria Verification
| Acceptance Criterion | Implemented? | Notes |
|---|---|---|
| Magic byte validation (%PDF-) in memory | Yes | Handled in `upload.py` via `data.startswith(PDF_MAGIC_BYTES)` before any PDF parsing. |
| Size cap against `MAX_UPLOAD_MB` | Yes | Enforced before parsing; configured in `settings.py` (default 10 MB). |
| Page cap against `MAX_PAGES` | Yes | Inspected via PyMuPDF in memory; configured in `settings.py` (default 40 pages). |
| Encryption / password detection | Yes | Checks `doc.is_encrypted or doc.needs_pass` in memory; raises `EncryptedPDFError`. |
| Subprocess PDF text extraction with memory & time limits | Yes | Spawns `extractor_worker.py` over stdin/stdout with `psutil`/`RLIMIT_AS` memory check and adaptive timeout budget. |
| Character offsets and skipped pages tracking | Yes | Returns `ExtractedDocument` with `PageText` start/end offsets and `skipped_pages` list. |
| Scanned PDF detection | Yes | Detects when all pages lack text layers and raises `ScannedPDFError`. |
| Cloudflare Turnstile verification with dev test keys | Yes | Implemented in `turnstile.py` with fast-paths for test keys and mock transport injection. |
| Exact artist-facing error messages | Yes | Verbatim match for Scanned, Encrypted, and File Too Large error texts. |
| Zero contract storage verified in tests | Yes | `test_zero_contract_storage_in_temp_directory` confirms zero files written to disk/tempdir. |
| Quality gates pass (`just test`, `just lint`, `just typecheck`) | Yes | 26 tests passed in 28.09s; ruff, eslint, mypy strict, and tsc all pass cleanly. |

## Verdict
✅ **Approved.** The implementation is clean, robust, and completely adheres to Mbiu's privacy and architectural invariants. The ticket owner may proceed with the local commit gate.
