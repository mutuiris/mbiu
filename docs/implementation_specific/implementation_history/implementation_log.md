# Mbiu — Implementation Log

This document serves as the chronological audit trail and engineering log for all implementation tickets completed in the Mbiu repository.

---

## Log Protocol

1. **At Ticket Completion:** When completing a ticket according to [sprint.md](file:///c:/git/mbiu/docs/implementation_specific/instructions/sprint.md), add a new log entry below using the [Entry Template](#entry-template).
2. **Post-Review Refinements:** When changes are implemented following a code review from [code_review.md](file:///c:/git/mbiu/docs/implementation_specific/instructions/code_review.md), record those updates under the `### Code Review & Refinements` section of the corresponding ticket entry, and mark them resolved in the review file.
3. **Traceability:** Always list exact modified/created files and the commands run with their results (`just test`, `just lint`, `just typecheck`).

---

### Entry Template

```markdown
## [MB-XXX] — [Ticket Title]

- **Date:** YYYY-MM-DD
- **Owner:** [Steve / Addy / Mercyline / Bernadette]
- **Branch:** `[branch-name]`
- **Status:** Ready for Review
- **Review Document:** [link to code review file in code_reviews/]

### What Was Done
- Concrete summary of modified and created files
- Service endpoints, data structures, or UI components added

### Key Technical Details & Architecture References
- Specific sections referenced in `docs/problem_architecture_planning/`
- Privacy invariants enforced (zero contract storage, memory-only extraction, `store=False`)
- Model validation rules enforced (exact substring quote validation, code-calculated shillings)
- Edge cases and error handling for musician user experience

### Verification & Test Results
- Quality commands run:
  - `just test`: outcomes and test counts
  - `just lint`: ruff and eslint output
  - `just typecheck`: mypy and tsc output
- Synthetic contract test scenarios verified

### Code Review & Refinements
*(Add updates here after code review)*
- **Review Date:** YYYY-MM-DD
- **Reviewer:** Mbiu Code Reviewer
- **Changes Implemented:**
  - Fixed [Issue description]: modified `...` to ...
  - Checkbox marked `[x]` in review file

### Next Developer / Maintenance Guide
- Dependencies or context needed by whoever builds downstream tickets.
```

---

## Ticket Implementation History

## [MB-02] — Upload checks and safe PDF text extraction

- **Date:** 2026-11-03
- **Owner:** Steve
- **Branch:** `feat/mbiu-build`
- **Status:** Approved
- **Review Document:** [MB-02 Code Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-02-upload-checks.md)

### What Was Done
- **Document upload validation service (`backend/mbiu/documents/upload.py`):**
  - Validates `%PDF-` magic bytes in memory.
  - Enforces file size ceilings against `MAX_UPLOAD_MB`.
  - Enforces page count ceilings against `MAX_PAGES`.
  - Detects encrypted / password-protected documents via PyMuPDF in-memory stream without touching disk.
  - Returns structured `UploadValidationResult(total_bytes, page_count)`.
- **Bot protection verification service (`backend/mbiu/security/turnstile.py`):**
  - Implements synchronous (`verify_turnstile_token`, `validate_turnstile_token`) and asynchronous (`async_verify_turnstile_token`) verification against Cloudflare's `siteverify` endpoint.
  - Provides native fast-path support for Cloudflare's standard dev test keys (`1x0000000000000000000000000000000AA` always-pass, `2x0000000000000000000000000000000AA` always-fail) to enable offline dev and hermetic CI testing.
  - Injects `httpx.Client` / `httpx.AsyncClient` support for testability.
- **In-memory PDF text extraction engine (`backend/mbiu/documents/extract.py` and `backend/mbiu/documents/extractor_worker.py`):**
  - Implements isolated subprocess worker execution receiving raw PDF bytes via standard input pipe and outputting structured JSON via standard output pipe.
  - Strictly enforces the zero-contract-storage invariant: no PDF bytes or extracted text ever touch disk or temporary files.
  - Enforces memory limit via `resource.setrlimit` (POSIX) and `psutil` memory inspection.
  - Enforces an adaptive extraction timeout budget scaling with page count (`base_timeout_s + page_count * per_page_timeout_s`).
  - Returns `ExtractedDocument` with per-page exact character offsets (`start_offset`, `end_offset`), text layers, and explicit `skipped_pages` list for scanned/image-only pages.
  - Detects scanned/photo PDFs where all pages lack text layers and raises `ScannedPDFError`.
- **Domain error hierarchy (`backend/mbiu/documents/errors.py`):**
  - Defines `DocumentError` base class and artist-friendly subclasses: `InvalidPDFError`, `FileTooLargeError`, `PageLimitExceededError`, `EncryptedPDFError`, `ScannedPDFError`, `EmptyPDFError`, `ExtractionTimeoutError`, `ExtractionMemoryError`, and `ExtractionFailedError`.
  - All errors provide plain, kind artist messages.
- **Settings & dependencies:**
  - Added `MAX_UPLOAD_MB`, `MAX_PAGES`, `TURNSTILE_SECRET_KEY`, and `TURNSTILE_VERIFY_URL` to `backend/config/settings.py` and `.env.example`.
  - Added `pymupdf` and `httpx` to dependencies adhering to the 14-day publication age rule.
- **Test suite (`backend/tests/`):**
  - Added in-memory synthetic PDF factories (`backend/tests/pdf_factories.py`).
  - Added comprehensive test suites: `test_upload.py`, `test_extract.py`, and `test_turnstile.py`.

### Key Technical Details & Architecture References
- **Architecture doc reference:** Sections 2 ("Upload and check", "Extract text"), "Reliability" (time budget & subprocess limits), and "Privacy and security" (Zero contract storage, Turnstile before model calls).
- **Zero Contract Storage invariant:** PyMuPDF operates on `stream=data` in-memory. Subprocess communication is conducted over OS pipe streams (`stdin`/`stdout`). Verified via `test_zero_contract_storage_in_temp_directory` that 0 files are written to the temp directory.
- **Character offset invariants:** `PageText` objects maintain exact character offsets that guarantee `full_text[page.start_offset:page.end_offset] == page.text`, ensuring downstream clause segmentation (MB-03) has exact substring coordinates.
- **Scanned page detection:** Empty text layers are marked `has_text = False` and tracked in `skipped_pages` to avoid silent omission. Fully scanned documents raise `ScannedPDFError`.

### Verification & Test Results
- Quality commands run:
  - `just test`: 26 passed in 43.63s (`test_health.py`, `test_upload.py`, `test_extract.py`, `test_turnstile.py`).
  - `just lint`: 100% pass across backend (`ruff check` and `ruff format --check`) and frontend (`eslint`).
  - `just typecheck`: 100% pass across backend (`mypy` in strict mode) and frontend (`tsc --noEmit`).
- Synthetic scenarios verified:
  - Valid text contract extraction with character offsets.
  - Image-only scanned PDF (triggers `ScannedPDFError`).
  - Mixed document with scanned signature page (tracks `skipped_pages=[2]`).
  - Encrypted / password-protected PDF (triggers `EncryptedPDFError`).
  - Non-PDF renamed to `.pdf` (fails magic bytes with `InvalidPDFError`).
  - PDF over size limit (triggers `FileTooLargeError`).
  - PDF over page count cap (triggers `PageLimitExceededError`).
  - Subprocess timeout budget exceeded (triggers `ExtractionTimeoutError`).
  - Subprocess memory ceiling exceeded (triggers `ExtractionMemoryError`).
  - Zero temp file leakage assertion.
  - Turnstile verification (dev test keys, live mock success/failure, network errors, timeouts, sync/async).

### Code Review & Refinements
- **Review Date:** 2026-11-03
- **Reviewer:** Mbiu Code Reviewer
- **Outcome:** Approved (Score: 5/5)
- **Review Document:** [MB-02 Code Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-02-upload-checks.md)
- **Changes Implemented:**
  - Preserved default kind `user_message` on `ExtractionFailedError` by introducing an optional `details: str | None = None` attribute for low-level diagnostics. Updated `extract.py` to pass internal worker exit codes / messages to `details` rather than overriding `user_message`.
  - Marked Issue 1 `[x] Fixed` in review file.

### Next Developer / Maintenance Guide
- Downstream ticket `MB-03` (Clause splitter) should consume `ExtractedDocument` from `extract_text_from_pdf` (or `extract_text_in_process`). Each `PageText` provides `page_number`, `start_offset`, `end_offset`, `text`, and `has_text`.
- Downstream ticket `MB-05` (Evaluation stream endpoint) can use `validate_upload`, `extract_text_from_pdf`, and `validate_turnstile_token` as the initial pipeline stages before calling clause segmentation and orchestrating stream events.

---

## [MB-03] — Clause splitter with property tests

- **Date:** 2026-11-03
- **Owner:** Steve
- **Branch:** `feat/mbiu-build`
- **Status:** Approved
- **Review Document:** [MB-03 Code Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-03-clause-splitter.md)

### What Was Done
- **Universal clause segmentation engine (`backend/mbiu/documents/segment.py`):**
  - Consumes `ExtractedDocument` (produced by MB-02) and segments contract text into structured clauses.
  - Recognizes hierarchical decimal numbering (`1.`, `1.1`, `1.1.1`), explicit markers (`Clause 1`, `Section 2`), parenthesized letters (`(a)`, `(b)`), Roman numerals (`(i)`, `(ii)`), recital markers (`(A)`, `(B)`), and layout/heading blocks.
  - Assigns unique, clean hierarchical `clause_id`s (e.g. `1`, `1.1`, `1.1(a)`, `1.1(a)(i)`, `recital_A`, `schedule_1_1.1`).
  - Preserves Schedules, Annexes, Exhibits, Appendices as distinct sections with distinct section names (e.g. `Schedule 1: RECORDING BUDGET`, `Annex A`).
  - Extracts titles and headings from inline and standalone patterns (e.g. `Royalties. The Company shall...` -> `title = "Royalties"`).
  - Maintains strict character offsets ensuring `full_text[clause.start_offset : clause.end_offset] == clause.text` down to the exact byte.
  - Maintains multi-page span provenance: clauses spanning page boundaries retain all relevant 1-indexed page numbers.
  - Provides `segment_text` convenience function for corpus templates and testing, delegating directly to `segment_document`.
- **Defined-terms extraction for whole-contract mapping:**
  - Extracts defined terms from explicit definitions clauses (`"Net Receipts" means...`, `"Advance": sum of...`, `"Territory" - Kenya...`).
  - Extracts inline parenthetical definitions (`...Jane Doe (the "Artist")...`, `...recordings (the "Masters")...`).
  - Returns `defined_terms: dict[str, str]` mapping normalized term strings to definitions.
  - Returns `defined_terms_detailed: list[DefinedTerm]` with exact character offsets, source clause IDs, and page numbers.
  - Provides `get_definition(term: str)` helper with case-insensitive and surrounding quotation mark tolerance.
- **Dependencies & exports:**
  - Added `hypothesis==6.170.5` to dev dependencies in `backend/pyproject.toml` adhering to the 14-day publication rule.
  - Exported `Clause`, `DefinedTerm`, `SegmentedDocument`, `segment_document`, and `segment_text` from `backend/mbiu/documents/__init__.py`.
- **Comprehensive test suite (`backend/tests/test_segment.py`):**
  - **Hypothesis property tests:**
    * Offsets slice back exactly: for every clause, `full_text[c.start_offset : c.end_offset] == c.text`.
    * Clauses never overlap in character offset ranges (`c1.end_offset <= c2.start_offset`).
    * Clauses spanning page breaks keep all touched page numbers.
  - **Synthetic contract scenarios:**
    * Synthetic Recording Contract (preamble, recitals, decimal clauses, lettered subclauses, Roman numerals, multiple schedules, defined terms).
    * Synthetic Gig Contract (unnumbered headings, inline defined terms, layout paragraph cues).
    * Synthetic Producer Contract (Roman numerals, Annex A deliverables, fee structures).
  - **Edge cases & invariants:**
    * Empty strings and whitespace-only inputs.
    * Single-paragraph contracts.
    * Long clauses spanning 3 pages.
    * Documents with skipped/scanned pages.
    * End-to-end integration with PyMuPDF in-memory text extraction (`extract_text_in_process`).
    * Zero contract storage assertion: 0 temporary files created during segmentation.

### Key Technical Details & Architecture References
- **Architecture reference:** Part 3 ("What happens to one upload" -> Step 3 "Split into clauses", Step 4 "Whole-contract check"), and Part 6 Ticket MB-03.
- **Zero Contract Storage invariant:** Operates entirely in memory from `ExtractedDocument` or strings. Does not write to disk, temp files, databases, or logs.
- **Model Output Proposal invariant:** Downstream models must quote clauses exactly; this is only possible because the splitter guarantees exact substring slicing `full_text[start:end] == text` and non-overlapping boundaries.
- **No Clause Judged Alone invariant:** Defined terms extraction provides the foundation for MB-14 whole-contract cross-referencing and overrides.

### Verification & Test Results
- Quality commands run:
  - `just test`: 39 passed in 31.10s (`test_health.py`, `test_upload.py`, `test_extract.py`, `test_turnstile.py`, `test_segment.py`).
  - `just lint`: 100% pass across backend (`ruff check`, `ruff format --check` over 22 files) and frontend (`eslint`).
  - `just typecheck`: 100% pass across backend (`mypy` strict over 22 files) and frontend (`tsc --noEmit`).
- All 3 Hypothesis property tests passed across 50 randomly generated contract structures.

### Code Review & Refinements
- **Review Date:** 2026-11-03
- **Reviewer:** Mbiu Code Reviewer
- **Outcome:** Approved (Score: 5/5)
- **Review Document:** [MB-03 Code Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-03-clause-splitter.md)
- **Changes Implemented:** None required. All acceptance criteria and invariants are rigorously satisfied.

### Next Developer / Maintenance Guide
- Downstream ticket `MB-05` (Evaluation stream endpoint) can consume `segment_document(extracted_doc)` to generate the `document` event containing `clause_id`, `original_text`, `pages`, and `sections`.
- Downstream ticket `MB-12` (Corpus pipeline I: fetch, store, parse, split) can use `segment_document` or `segment_text` directly on parsed standard templates.
- Downstream ticket `MB-14` (Whole-contract map) can consume `segmented.defined_terms` and `segmented.defined_terms_detailed` to build deterministic links and link clauses to defined term definitions.

## [MB-10] — Corpus database & startup snapshot

- **Date:** 2026-11-03
- **Owner:** Steve
- **Branch:** `feat/mbiu-build`
- **Status:** Approved
- **Review Document:** [MB-10 Code Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-10-corpus-database.md)

### What Was Done
- **Corpus models (`backend/mbiu/corpus/models.py`):**
  - Implemented the ONLY four application tables:
    1. `ReferenceSource` (`reference_sources`): metadata for source documents and standards (title, url, license, reviewing_body, contract_type, jurisdiction).
    2. `CorpusVersion` (`corpus_versions`): versioned corpus releases with a single active pointer enforced via database-level `UniqueConstraint(fields=["is_active"], condition=Q(is_active=True))`. Enforced immutability for published versions (published versions cannot edit `version_tag`, `embedding_model_id`, or `embedding_dim`). Added `activate_version()` class method for atomic version flipping.
    3. `ReferenceChunk` (`reference_chunks`): reviewed standard template clauses linked to `CorpusVersion` and `ReferenceSource`, with `text`, `topic`, `contract_type`, `jurisdiction`, `drafted_for`, `metadata`, and 768-dim `VectorField` embeddings powered by `pgvector`.
    4. `PipelineCheckResult` (`pipeline_check_results`): automated quality check records attached to versions (check_name, passed, details, checked_at).
  - Explicitly verified ZERO user contract tables exist.
- **Initial migration (`backend/mbiu/corpus/migrations/0001_initial.py`):**
  - Includes `VectorExtension()` to initialize the pgvector extension on PostgreSQL.
  - Creates the four application tables and sets up database constraints.
  - Implements `PostgresRunSQL` to enable Row Level Security (RLS) on all four tables in Supabase/PostgreSQL while conditionally skipping on SQLite for fast hermetic local testing.
- **In-memory startup snapshot loader (`backend/mbiu/corpus/loader.py`):**
  - Implemented thread-safe `load_corpus_snapshot()` which loads the active version and its chunks from the database into in-memory structures:
    * 2D `np.ndarray` of shape `(N, embedding_dim)` and dtype `float32`.
    * Tuple of `ChunkMetadata` records.
    * Fast dictionary index `by_id: dict[str, ChunkMetadata]`.
  - Implemented accessors `get_active_corpus_snapshot()` and `clear_corpus_snapshot()`.
  - Configured `backend/mbiu/corpus/apps.py` `CorpusConfig.ready()` to attempt snapshot loading at startup, safely bypassing during management commands (`makemigrations`, `migrate`, `pytest`, `mypy`).
- **Readiness endpoint update (`backend/mbiu/health.py`):**
  - Updated `/readyz` to check both database connectivity and the presence of the active in-memory corpus snapshot.
  - Returns 503 with `"corpus"` in `failed` list when no snapshot is loaded or no version is active.
  - Returns 503 with `"database"` in `failed` list when database connectivity fails.
  - Returns 200 `{"status": "ready"}` when both database and corpus snapshot are ready.
- **Dependencies & Settings (`backend/pyproject.toml`, `backend/config/settings.py`):**
  - Added `numpy>=2.5.4` and `pgvector>=0.5.1` to dependencies respecting the 14-day publication rule.
  - Updated `config/settings.py`: added `database_direct_url`, SQLite URL support in `_database()`, `connect_timeout: 3` in PostgreSQL connection options, and registered `"pgvector.django"` and `"mbiu.corpus"` in `INSTALLED_APPS`.
  - Created `backend/manage.py` for administrative commands.
- **CI & Test Harness (`.github/workflows/ci.yml`, `backend/tests/conftest.py`):**
  - Added `pgvector/pgvector:pg17` service container to `ci.yml` for real PostgreSQL integration in CI.
  - Configured `conftest.py` with fast connection probe that falls back to in-memory SQLite if PostgreSQL is not running locally, ensuring instant, zero-setup developer iteration.
- **Comprehensive test suite (`backend/tests/test_corpus.py`, `backend/tests/test_health.py`):**
  - Added 12 new corpus tests and 4 new health check tests (total test count increased from 39 to 55).
  - Verified Zero Contract Storage invariant: asserted exactly 4 models exist, checked table names, and confirmed no fields exist for user uploads, user text, or user results.
  - Verified single active version database constraint and atomic version activation.
  - Verified immutability of published corpus versions.
  - Verified relationships across all models.
  - Verified in-memory loader: numpy embedding array shape `(3, 768)`, dtype `float32`, chunk metadata, and ID lookups.
  - Verified `/readyz` failure modes (missing corpus, unreachable DB, both failed) and 200 ready state.

### Key Technical Details & Architecture References
- **Architecture reference:** Part 3 ("How it fits together": "Supabase Postgres with pgvector holds the reference corpus, which the API loads into memory once at startup, so the database is never on the request path") and Part 6 Ticket MB-10.
- **Zero Contract Storage invariant:** Only reviewed public templates and reference sources are stored in the database. No user contracts, uploaded PDFs, extracted text, or evaluation results are ever written to the database. Verified via `test_zero_contract_storage_database_schema`.
- **Database Never on Request Path:** User contract evaluation requests query the in-memory `CorpusSnapshot` (numpy embeddings and metadata dictionary), completely isolating the database from the evaluation request path.
- **Single Active Version Invariant:** Enforced at both the Django model validation level and PostgreSQL database constraint level with a partial unique index (`WHERE is_active = True`).
- **Row Level Security (RLS):** Enabled via migration on all four application tables.

### Verification & Test Results
- Quality commands run:
  - `just test`: 55 passed in 35.20s (100% pass across all tests, zero regressions).
  - `just lint`: 100% pass across backend (`ruff check`, `ruff format --check` over 31 files) and frontend (`eslint`).
  - `just typecheck`: 100% pass across backend (`mypy` strict over 31 files) and frontend (`tsc --noEmit`).

### Code Review & Refinements
- **Review Date:** 2026-11-03
- **Reviewer:** Mbiu Code Reviewer
- **Outcome:** Approved (Score: 5/5)
- **Review Document:** [MB-10 Code Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-10-corpus-database.md)
- **Changes Implemented:** None required. All acceptance criteria and invariants are rigorously satisfied.

### Next Developer / Maintenance Guide
- Downstream ticket `MB-12` (Corpus pipeline I: fetch, store, parse, split) and `MB-13` (Corpus pipeline II: tag, check, embed, publish) can write parsed standard templates to `ReferenceSource` and `ReferenceChunk`, evaluate them using `PipelineCheckResult`, create a new `CorpusVersion`, and call `CorpusVersion.activate_version()` to atomically publish the release.
- Downstream ticket `MB-16` (Retrieval and impact order) will consume `get_active_corpus_snapshot()` to perform in-memory vector similarity searches using `snapshot.embeddings` and retrieve matching chunk metadata via `snapshot.chunks` or `snapshot.get_chunk(chunk_id)`.

## [MB-13] — Corpus pipeline II: tag, check, embed, publish

- **Date:** 2026-11-03
- **Owner:** Steve
- **Branch:** `feat/mbiu-build`
- **Status:** Approved
- **Review Document:** [MB-13 Code Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-13-corpus-pipeline-enrichment.md)

### What Was Done
- **Clause Tagging & Dual-Tagger Consensus Module (`backend/mbiu/corpus/pipeline/tag.py`):**
  - Implemented structured tag schemas: `ClauseTags(contract_type, topic, jurisdiction, drafted_for)` and `TaggingResult`.
  - Built `HeuristicClauseTagger` for fast, deterministic rule-based tagging covering 12 canonical legal topics (`royalties`, `advances_recoupment`, `grant_of_rights`, `term_duration`, `exclusivity`, `accounting_audit`, `termination`, `warranties_indemnities`, `moral_rights`, `governing_law_jurisdiction`, `dispute_resolution`, `boilerplate`), 8 contract types, and 3 drafting perspectives (`label`, `artist`, `neutral`).
  - Built `DualTaggerConsensus` evaluating consensus between two independent taggers; only clauses where both taggers agree on all four attributes are accepted into the published corpus.
- **Automated Quality Checks Engine (`backend/mbiu/corpus/pipeline/checks.py`):**
  - Implemented all six non-negotiable automated quality checks with structured outcomes recorded in `PipelineCheckResult`:
    1. `validate_metadata`: ensures license, jurisdiction, and reviewing body are present and verified against allowable open/reusable licenses (`CC BY 4.0`, `CC0`, `Kenya Copyright Act (Cap. 130)`, `WIPO reference standard`, etc.). Rejects missing, blank, or proprietary licenses ("All Rights Reserved").
    2. `validate_template_nature`: validates operative contract wording and rejects signed agreements with execution blocks, marketing copy, and informal blog posts.
    3. `scan_for_pii`: high-precision scanner detecting real personal emails, Kenyan & international phone numbers, street addresses, P.O. Box addresses, and national ID/passport numbers while preserving legitimate template placeholders (`[Artist Name]`, `<Record Company>`, `Jane Doe`, `Party A`).
    4. `check_language`: validates text is English using comprehensive English lexical frequency analysis and rejects non-English text (Swahili, French, German).
    5. `check_deduplication`: MinHash / n-gram Jaccard near-duplicate detector (3-gram word shingles) removing redundant templates and recording deduplication metrics.
    6. `check_tag_consensus`: verifies dual-tagger agreement across all accepted clauses.
  - Implemented `run_all_checks` orchestrating all six checks.
- **Corpus Clause Embedding Module (`backend/mbiu/corpus/pipeline/embed.py`):**
  - Formatted embedding inputs strictly according to the EmbeddingGemma 2 spec: `title: {title} | text: {content}`.
  - Implemented `EmbeddingEngine` producing 768-dimensional float32 unit-length embeddings ($L_2$ norm = 1.0) with zero NaN/Inf values.
  - Implemented `compute_clause_commonality` calculating cosine similarity dot-product matrices to group similar clauses and annotate metadata with cluster size, pattern frequency, and commonality flags.
  - Implemented model revision and vector dimension compatibility guards preventing mixing vectors across different revisions or dimensions.
- **Publishing & Orchestration Module (`backend/mbiu/corpus/pipeline/publish.py`):**
  - Built `CorpusPublisher.publish_version(...)`:
    * Validates tag uniqueness and immutability.
    * Evaluates dual-tagging consensus.
    * Runs all 6 quality checks; aborts on any failure.
    * Generates 768-dim float32 unit embeddings.
    * Calculates pattern commonality scores.
    * Atomically persists `CorpusVersion`, `ReferenceSource`, `ReferenceChunk`, and `PipelineCheckResult` records.
    * Atomically activates version via `CorpusVersion.activate_version()`.
    * Reloads in-memory snapshot via `load_corpus_snapshot()`.
- **CLI Runner & Entrypoint (`backend/mbiu/corpus/pipeline/runner.py`, `backend/mbiu/corpus/pipeline/__main__.py`):**
  - Exposed CLI command `python -m mbiu.corpus.pipeline --version-tag <tag> [--dry-run] [--no-activate] [--sources <path>]`.
  - Built default synthetic standards factory (`get_default_synthetic_standards()`) for bootstrap and testing.
- **Scheduled Pipeline Workflow (`.github/workflows/corpus-pipeline.yml`):**
  - Added scheduled weekly (Sunday 00:00 UTC) and manual `workflow_dispatch` GitHub Actions workflow to run the corpus pipeline and keep the Supabase database active.
- **Comprehensive Colocated Test Suite (`backend/tests/test_corpus_pipeline.py`):**
  - 30 tests covering all individual checks (passing and failing fixtures), tagging consensus, embedding formatting/normalization, commonality grouping, atomic E2E publishing, snapshot reloading, and the Zero Contract Storage invariant.

### Key Technical Details & Architecture References
- **Architecture doc reference:** Part 3 ("How it fits together: ...scheduled corpus pipeline publishes new corpus versions") and Part 6 Ticket MB-13.
- **Non-Negotiable Project Invariants Enforced:**
  - *Zero Contract Storage Invariant:* Corpus pipeline processes reviewed template standards ONLY. Verified by `test_zero_contract_storage_pipeline_isolation` that no user contracts, uploads, or user sessions exist in the pipeline.
  - *Storage Off at AI Providers:* Model taggers and verification checks run with `store=False`.
  - *Decisions From Reviewed Templates Only:* Only clauses passing all six quality checks and verified licenses are published into the corpus.
  - *Vector Revision Protection:* Enforces identical model ID and dimensionality (768), rejecting vector mixing.
  - *Single Active Pointer:* Versions are atomically flipped via `CorpusVersion.activate_version()`, and the in-memory snapshot is refreshed immediately.

### Verification & Test Results
- Quality commands run:
  - `just test`: 85 passed in 37.66s (100% pass across all tests, zero regressions).
  - `just lint`: 100% pass across backend (`ruff check`, `ruff format --check` over 39 files) and frontend (`eslint`).
  - `just typecheck`: 100% pass across backend (`mypy` strict over 39 files) and frontend (`tsc --noEmit`).

### Code Review & Refinements
- **Review Date:** 2026-11-03
- **Reviewer:** Mbiu Code Reviewer
- **Outcome:** Approved (Score: 5/5)
- **Review Document:** [MB-13 Code Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-13-corpus-pipeline-enrichment.md)
- **Changes Implemented:**
  - Added `.github/workflows/corpus-pipeline.yml` configured for weekly cron execution and manual `workflow_dispatch` triggers to automate corpus publishing checks and prevent Supabase free project pausing.
  - Marked item resolved in review file.

### Next Developer / Maintenance Guide
- Downstream ticket `MB-16` (Retrieval and impact order) will consume `get_active_corpus_snapshot()` to perform vector search over `snapshot.embeddings` (768 float32 dimensions) and retrieve chunks by `topic`, `contract_type`, and `jurisdiction`.
- Downstream ticket `MB-18` (Comparison and summary) will use reference chunks and their commonality scores (`chunk.metadata["commonality"]`) to evaluate whether user contract clauses adhere to common or unusual patterns.

---

## [MB-17] — Verification rules

- **Date:** 2026-11-03
- **Owner:** Steve
- **Branch:** `feat/mbiu-build`
- **Status:** Approved
- **Review Document:** [MB-17 Code Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-17-verification-rules.md)

### What Was Done
- **Dedicated Verification Rules Engine (`backend/mbiu/evaluation/verify.py`):**
  - Built dedicated verification functions for all eight non-negotiable rules:
    1. `verify_verbatim_quotes`: Enforces that `key_quote` and all cited `evidence` quotes are exact substrings (whitespace-normalized) of the sent clause text and reference template texts. Rejects altered or hallucinated quotations.
    2. `verify_grounded_ids`: Validates that target clause IDs, linked clause IDs, evidence chunk IDs, and pattern IDs strictly belong to the request context. Rejects untyped norm words ("industry standard", "customary") in comparison notes unless code placeholders (e.g. `{{freq:PXX}}`) are used.
    3. `verify_grounded_numbers`: Audits every number, percentage, and duration cited in proposal fields (`title`, `plain_language`, `why_it_matters`, `comparison_note`, `questions`) against the sent clause text, linked clauses, and cited evidence excerpts. Excludes code-calculated Kenyan Shilling illustrative examples when explicitly labelled.
    4. `verify_no_legal_conclusions`: Blocks forbidden legal validity, advice, and evaluative phrases ("illegal", "unlawful", "unenforceable", "void", "fair", "unfair", "safe", "guaranteed", "you should sign", "don't sign", "valid in court", etc.). Enforces objective modal tone in `why_it_matters` (must include "may" or "could") and rejects imperative commands ("you must", "demand", "refuse").
    5. `verify_plain_language`: Computes Flesch-Kincaid Grade Level via pure-Python deterministic syllable analysis. Enforces that industry legal/music jargon terms ("net receipts", "recoupable", "in perpetuity", "cross-collateralization", "indemnity", etc.) must be defined either in `jargon_definitions` or inline on the card.
    6. `verify_phone_friendly_length`: Enforces strict character limits per card section: `title` (<= 45), `plain_language` (<= 200), `why_it_matters` (<= 280), `comparison_note` (<= 280), and each question (<= 120).
    7. `verify_usable_questions`: Enforces that suggested questions end with "?", are at least 15 characters, and ask for specific, actionable terms (caps, rates, reversion windows, accounting frequencies). Rejects vague boilerplate questions ("What does this mean?", "Is this good?"). Limits questions to at most 3 per card.
    8. `verify_comparable_money`: Enforces that monetary comparisons explicitly specify calculation basis ("gross" or "net") on both sides; incompatible or missing bases fail, triggering fallback to `cannot_compare`.
- **Orchestration, Repair Feedback, & Fallback Workflow (`repair_and_verify`):**
  - `verify_proposal`: Executes all 8 rules, aggregates `RuleViolation` items, and assigns deterministic labels (`typical`, `unusual`, `worth_asking_about`, `cannot_compare`) when all rules pass.
  - `generate_repair_feedback`: Produces structured feedback naming failed rules specifically and providing clear repair instructions for the model.
  - `repair_and_verify`: Executes initial verification; allows exactly one repair attempt with feedback; if verification fails after repair, deterministically falls back to outcome `cannot_compare` (⚪ Couldn't compare) with a safe fallback card. Never falls back to `matches_standard` or `typical`.
  - Observability Counters: Thread-safe failure counters per rule (`get_rule_failure_counts`, `reset_rule_failure_counters`, `record_rule_failure`) ready for export to metrics (MB-29).
- **Comprehensive Colocated Test Suite (`backend/tests/test_verify.py`):**
  - 65 comprehensive tests covering all 8 rules (passing and failing fixtures), hallucinated numbers/IDs/quotes, forbidden legal advice, missing question marks, ungrounded jargon, phone length limits, single-attempt repair success, double-failure fallback, failure counters, and the zero-contract-storage invariant.

### Key Technical Details & Architecture References
- **Architecture doc reference:** Lines 333-345 ("Table: Verification Rules", "Model output is a proposal, not a result") and Ticket MB-17.
- **Non-Negotiable Project Invariants Enforced:**
  - *Zero Contract Storage Invariant:* Operates strictly in memory on strings and dataclasses. Verified via `test_zero_contract_storage_during_verification` that 0 files are written to temp directory or disk.
  - *Decisions From Reviewed Templates Only:* Model cannot invent outside norms. Any ungrounded comparison or second verification failure defaults to `cannot_compare`.
  - *Model Output is a Proposal, Not a Result:* All quotes are verified by code as exact substrings before reaching the musician. Arithmetic and shillings examples are computed by code.
  - *The Four Labels (No Green Label):* Strictly enforces `typical`, `unusual`, `worth_asking_about`, and `cannot_compare`. "Typical" never implies safe.
  - *Synthetic Contracts Only:* All test fixtures utilize synthetic contract clauses.

### Verification & Test Results
- Quality commands run:
  - `just test`: 150 passed in 35.83s (100% pass across all tests, zero regressions).
  - `just lint`: 100% pass across backend (`ruff check`, `ruff format --check` over 42 files) and frontend (`eslint`).
  - `just typecheck`: 100% pass across backend (`mypy` strict over 42 files) and frontend (`tsc --noEmit`).

### Code Review & Refinements
- **Review Date:** 2026-11-03
- **Reviewer:** Mbiu Code Reviewer
- **Outcome:** Approved (Score: 5/5)
- **Review Document:** [MB-17 Code Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-17-verification-rules.md)
- **Changes Implemented:**
  - Removed ticket ID reference from inline comment in `verify.py#L334` per repository hygiene rules.
  - Marked Issue 1 `[x] Fixed` in review file.

### Next Developer / Maintenance Guide
- Downstream ticket `MB-18` (Comparison, budgets, missing protections and summary) will invoke `repair_and_verify` or `verify_proposal` on candidate batches produced by the Gemini adapter (MB-04) and OpenAI failover (MB-20).
- Downstream ticket `MB-29` (Observability) will expose `get_rule_failure_counts()` as OpenTelemetry metric counters (`mbiu_verification_failures_total{rule="..."}`).

---

## [MB-18] — Comparison, budgets, missing protections and summary

- **Date:** 2026-11-03
- **Owner:** Steve
- **Branch:** `feat/mbiu-build`
- **Status:** Approved
- **Review Document:** [MB-18 Code Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-18-comparison-summary.md)

### What Was Done
- **Batching & Concurrency Engine (`backend/mbiu/evaluation/budgets.py`):**
  - Topic classification and impact ordering: Prioritizes clauses by impact: Money (100) and Ownership (90) first, followed by Term (80), Exclusivity (70), and Termination (60); Boilerplate (10) evaluated last. Stable sorting preserves original document order within identical priority tiers.
  - Clause Batching: Partitions clauses into balanced batches of 4-8 clauses (default `settings.BATCH_SIZE = 6`), dynamically balancing items to eliminate orphan batches when total clauses >= 4.
  - Concurrency Control: Implements `run_evaluation_batches` using `asyncio.Semaphore(settings.LLM_CONCURRENCY)` (default 4).
  - Time & Token Budgets: `EvaluationBudgetTracker` enforces per-batch time limits (`settings.BATCH_TIMEOUT_S = 30.0s`), incremental contract deadline scaling with clause count (`settings.DEADLINE_PER_CLAUSE_S = 3.0s`, capped at `settings.DEADLINE_CAP_S = 300.0s`), and overall contract token ceilings (`settings.TOKEN_BUDGET_PER_CONTRACT = 400,000`).
  - Budget Exhaustion Handling: When token or time budgets expire, remaining clauses are safely converted into status `not_checked` with the artist-friendly plain language message:
    `"Mbiu checked the most important clauses first. N clauses aren't checked yet."`
- **Comparison & Reverse Check Engine (`backend/mbiu/evaluation/comparison.py`):**
  - Result Card Model: `ClauseEvaluationResult` carrying clause provenance (`clause_id`, `pages`, `original_text`), evaluation status, 6 comparison outcomes, 4 non-negotiable labels, phone-friendly plain-language text, impact inputs, fairer wording, and evidence citations.
  - Missing Reviewed Standard Guard: If the detected contract type lacks a reviewed standard in the corpus snapshot, emits outcome `cannot_compare` (⚪ Couldn't compare) with kind explanation:
    `"Mbiu doesn't have a reviewed standard for this kind of contract yet, so it can explain these clauses but not compare them."`
  - Template Disagreements: `format_template_disagreement` formats clear evidence differences:
    `"Standard templates differ here: one gives X, another Y. Your contract gives Z."`
  - Impact Inputs (Shillings Calculation): `validate_impact_inputs` extracts `rate`, `money_basis`, `deductions`, and exact verbatim `quote` for frontend arithmetic. Strictly enforces that the model never does arithmetic in shillings.
  - Fairer Wording Extraction: `extract_fairer_wording` validates that fairer wording matches an exact substring of a reviewed template chunk, unchanged.
  - Verification Orchestration: `evaluate_clause_with_verification` routes every candidate proposal through MB-17 `repair_and_verify` to guarantee zero hallucinations, grounded numbers, and phone-friendly plain language.
  - Reverse Check (Missing Protections): `check_missing_protections` scans the contract for standard protective clauses present in reviewed templates (annual audit rights, accounting statement frequency, termination for uncured breach/non-payment, prior written approval for deductions, rights reversion). Emits outcome `missing_from_contract` and label `worth_asking_about` (🟠 Worth asking about) with objective, cautious phrasing ("We didn't find...").
- **Evaluation Summary Generator (`backend/mbiu/evaluation/summary.py`):**
  - `EvaluationSummary` dataclass and `generate_evaluation_summary`:
    - `top_asks`: Top 3 negotiation questions ranked by impact on money and ownership.
    - `contract_issues`: Contract-wide overrides and conflicts passed from contract map.
    - `missing_protections`: Protections detected as absent by the reverse check.
    - `good_news`: Clauses that match or exceed the standard (`matches_standard` or `better_for_you`).
    - `matches_count`: Count of clauses matching reference standards.
    - `skipped_pages`: Pages skipped during PDF extraction.
    - `ask_list`: Consolidated, deduplicated checklist of all negotiation questions.
    - `clauses_not_checked`: Count of clauses left unchecked upon budget exhaustion.
    - `label_counts`: Grand totals for `typical`, `unusual`, `worth_asking_about`, and `cannot_compare`.
    - `versions`: `EvaluationVersions` (`schema_version="1.0.0"`, `prompt_version="2026.1"`, `model_version="gemini-3.8-flash"`, `corpus_version="v2026.10"`).
  - Backwards-compatible aliases: `top_questions`, `contract_wide_issues`, `not_found_items`, `all_questions`.
- **Settings & Config (`backend/config/settings.py`):**
  - Added `BATCH_SIZE`, `LLM_CONCURRENCY`, `TOKEN_BUDGET_PER_CONTRACT`, `BATCH_TIMEOUT_S`, `DEADLINE_PER_CLAUSE_S`, and `DEADLINE_CAP_S` to `Env` and module exports.
- **Test Suite (`backend/tests/test_comparison.py` & `test_summary.py`):**
  - 22 comprehensive colocated tests verifying impact ordering, batch sizing, token/time exhaustion, async batch runner timeouts, impact inputs without model arithmetic, exact template fairer wording, template disagreement formatting, missing standard handling, reverse check missing protection detection, summary generation with top 3 asks, and zero contract storage.

### Key Technical Details & Architecture References
- **Architecture References:** Lines 143-175 ("Evaluation request flow", "Long contracts"), Lines 280-332 ("Comparison outcomes", "Fields per clause result", "Summary fields"), and Ticket MB-18 in `Mbiu Build Tickets.md`.
- **Non-Negotiable Project Invariants Enforced:**
  - *Zero Contract Storage Invariant:* Operates strictly in memory. Verified via `test_zero_contract_storage_during_comparison` and `test_zero_contract_storage_summary` that 0 files are written to disk, databases, or temporary directories.
  - *Storage Off at AI Providers:* All evaluation structures and runner adapters adhere to `store=False`.
  - *Decisions From Reviewed Templates Only:* Comparisons are made exclusively against reference template chunks in the corpus snapshot; missing standard emits `cannot_compare`.
  - *Model Output is a Proposal, Not a Result:* All quotes and deductions are validated as exact substrings; model arithmetic is strictly blocked from the request path.
  - *The Four Labels (No Green Label):* Strictly maps results to `typical`, `unusual`, `worth_asking_about`, and `cannot_compare`.
  - *Synthetic Contracts Only:* All tests and fixtures use synthetic music agreements.

### Verification & Test Results
- Quality commands run:
  - `just test`: 172 passed in 37.84s (100% pass across all tests, zero regressions).
  - `just lint`: 100% pass across backend (`ruff check`, `ruff format --check` over 47 files) and frontend (`eslint`).
  - `just typecheck`: 100% pass across backend (`mypy` strict over 47 files) and frontend (`tsc --noEmit`).

### Code Review & Refinements
- **Review Date:** 2026-11-03
- **Reviewer:** Mbiu Code Reviewer
- **Outcome:** Approved (Score: 5/5)
- **Review Document:** [MB-18 Code Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-18-comparison-summary.md)
- **Changes Implemented:**
  - Replaced in-place list mutation during deduction pruning in `validate_impact_inputs` with list comprehension filtering to avoid skipping adjacent ungrounded terms.
  - Converted `run_evaluation_batches` from sequential loop into true concurrent worker queue execution with token reservations, enabling concurrent batch evaluation under `settings.LLM_CONCURRENCY` while preserving budget limits and batch ordering.
  - Removed orphaned dead code expression `total_clauses - processed_count` from `budgets.py`.
  - Marked all 3 review items `[x] Fixed` in review file.

### Next Developer / Maintenance Guide
- Downstream ticket `MB-21` (Full result card & shillings calculator) will use `ClauseEvaluationResult.impact_inputs` (`rate`, `money_basis`, `deductions`, `quote`) to run client-side Kenyan Shillings calculations on user-provided sample revenues.
- Downstream ticket `MB-25` (PDF report & sharing) will consume `EvaluationSummary` (`top_asks`, `good_news`, `missing_protections`, `ask_list`) to format client-side exportable PDF reports and WhatsApp share messages.

---

## [MB-26] — Refresh protection and resuming unfinished clauses

- **Date:** 2026-11-03
- **Owner:** Steve
- **Branch:** `feat/mbiu-build`
- **Status:** Approved
- **Review Document:** [MB-26 Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-26-refresh-protection.md)

### What Was Done
- **Stateless Clause Evaluation Endpoint (`backend/mbiu/evaluation/views.py`):**
  - Created `POST /api/v1/clause-evaluations` view mounted in `config/urls.py` (`api/v1/clause-evaluations` and `api/v1/clause-evaluations/`).
  - Accepts a JSON payload containing `clauses` resent by the browser (each with `clause_id`, `text`, `pages`, optional `title` and `section`), optional `contract_type`, and optional `defined_terms`.
  - Evaluates clauses statelessly using the MB-18 comparison and MB-17 verification engines.
  - Streams newline-delimited JSON (NDJSON) events (`progress`, `clause_result`, `clause_failed`, `done`) with `Cache-Control: no-store, no-cache, must-revalidate` and `Content-Type: application/x-ndjson`.
  - Supports non-streaming JSON mode when requested via `Accept: application/json` and `stream != true`.
  - Enforces input validation: returns 400 Bad Request for malformed JSON, empty clauses list, missing clauses, or missing clause_id/text.
  - Enforces HTTP method restrictions: returns 405 Method Not Allowed for non-POST requests.
  - Enforces reviewed standard check: emits `cannot_compare` (⚪ Couldn't compare) with `NO_STANDARD_FOR_TYPE_MESSAGE` for contract types without reviewed standards (e.g. podcast_host).
  - Performs Reverse Check (`check_missing_protections`) and outputs consolidated `EvaluationSummary` in the final `done` event.
- **Tab-only sessionStorage Management (`frontend/src/lib/keep-tab.ts`):**
  - Implemented tab-only `sessionStorage` management for evaluation state (`TabEvaluationState`).
  - Explicit opt-in toggle, off by default: `"Keep my results if this page reloads. Leave this off on a shared phone."`
  - 60-minute TTL: cached results older than 60 minutes automatically expire and are purged upon access.
  - Explicit clearing: `clearTabResults()` immediately purges stored results. Disabling opt-in via `setKeepTabOptIn(false)` also purges stored results.
  - No opt-in restore behavior: returns `saved: false, optedIn: false` with the exact required message: `"Your results weren't saved on this device. Upload the contract again to see them."`
  - Complete TypeScript interfaces: `TabClause`, `TabEvaluationCard`, `TabEvaluationSummary`, `TabEvaluationState`, `TabRestoreResult`.
  - Safe for SSR: defensive environment checks prevent errors in non-browser/server environments.
- **Refresh Protection & Clause Resumption (`frontend/src/lib/refresh-protection.ts`):**
  - Accidental reload protection: `beforeunload` confirmation dialog handler and `useRefreshProtection(isActive)` React hook.
  - Accidental pull-to-refresh protection on mobile: CSS `overscroll-behavior-y: contain` helper (`getOverscrollContainmentStyle` and `applyOverscrollContainment`).
  - Resuming unfinished clauses: `resumeUnfinishedClauses(options)` computes unfinished or failed clauses from the document clause list (`getUnfinishedClauses`), sends only those clauses to `POST /api/v1/clause-evaluations`, and parses the streaming NDJSON response.
  - Stream drop resilience: if the connection drops or fails mid-stream, preserves all cards arrived so far and saves updated state to `sessionStorage` (if opted in).
- **Backend Tests (`backend/tests/test_clause_evaluations_endpoint.py`):**
  - 11 comprehensive tests verifying NDJSON streaming, JSON response mode, URL routing with/without trailing slash, unreviewed contract type handling, empty clauses list (400), missing clauses field (400), malformed JSON (400), invalid clause structure (400), method not allowed (405), and zero contract storage with no database rows or temporary files created.
- **Frontend Tests (`frontend/tests/keep-tab.test.ts` & `frontend/tests/refresh-protection.test.ts`):**
  - 16 unit tests running natively via Node.js 24 test runner (`node --test --experimental-strip-types`), testing opt-in default, opt-in toggling, saving/restoring, 60-minute TTL expiration, explicit clearing, beforeunload handling, overscroll styling, unfinished clause filtering, NDJSON line parsing, and streaming resumption with network drop resilience.
- **Build & Quality Gates (`justfile` & `frontend/package.json`):**
  - Updated `justfile` test recipe to run both backend pytest and frontend test suite: `just test`.
  - Added `"test": "node --test --experimental-strip-types tests/**/*.test.ts"` to `frontend/package.json`.
  - Enabled `"allowImportingTsExtensions": true` in `frontend/tsconfig.json` for seamless TypeScript typechecking with ESM.

### Key Technical Details & Architecture References
- **Architecture References:** Lines 160-162 ("Retries use POST /api/v1/clause-evaluations: the browser resends only the clause texts it holds for failed or unchecked clauses, and the server evaluates them statelessly"), Lines 388-403 ("If the page is refreshed by mistake: Prevent it, Make saving easy, Keep for this tab"), and Ticket MB-26 in `Mbiu Build Tickets.md`.
- **Non-Negotiable Project Invariants Enforced:**
  - *Zero Contract Storage Invariant:* Operates strictly in memory. Verified via `test_clause_evaluations_zero_contract_storage` that no database rows (ReferenceChunk, CorpusVersion) or temp files are created during evaluation, and `Cache-Control: no-store, no-cache, must-revalidate` is strictly returned.
  - *Stateless Backend:* No database job tables, sessions, or queues on the request path. Retries resend clause text; the browser retains state in tab sessionStorage when opted in.
  - *Storage Off at AI Providers:* Stateless comparison architecture conforms to `store=False`.
  - *Decisions From Reviewed Templates Only:* Comparisons strictly ground against reviewed standards; unreviewed types return `cannot_compare` (⚪ Couldn't compare).
  - *Model Output is a Proposal, Not a Result:* All quotes are verified exact substrings; labels adhere strictly to the 4 valid labels with no green label.
  - *Synthetic Contracts Only:* All tests and fixtures use synthetic music agreements.

### Verification & Test Results
- Quality commands run:
  - `just test`:
    - Backend: 183 passed in 43.13s (100% pass rate).
    - Frontend: 16 passed in 0.51s (100% pass rate).
  - `just lint`:
    - Backend: `ruff check .` (all checks passed) and `ruff format --check .` (49 files already formatted).
    - Frontend: `eslint` (all checks passed).
  - `just typecheck`:
    - Backend: `mypy .` (success: no issues found in 49 source files).
    - Frontend: `tsc --noEmit` (success: 0 errors).

### Code Review & Refinements
- **Review Date:** 2026-11-03
- **Reviewer:** Mbiu Code Reviewer
- **Outcome:** Approved (Score: 5/5)
- **Review Document:** [MB-26 Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-26-refresh-protection.md)
- **Changes Implemented:** Cleaned up `backend/mbiu/evaluation/views.py#L487` exception handler to wrap exception types as a tuple `except (json.JSONDecodeError, UnicodeDecodeError):`. All acceptance criteria and invariants are rigorously satisfied.

### Next Developer / Maintenance Guide
- Downstream frontend tickets `MB-07` (Live results page), `MB-21` (Full result card & shillings calculator), and `MB-27` (Phone layouts, accessibility, e2e tests) can import `useRefreshProtection`, `getOverscrollContainmentStyle`, `restoreTabResults`, and `resumeUnfinishedClauses` to handle page refreshes, mobile swipe-to-refresh prevention, and dropped stream recovery seamlessly.




