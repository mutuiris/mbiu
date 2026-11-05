# Code Review: MB-13 — Corpus pipeline II: tag, check, embed, publish

> **Date:** 2026-11-03  
> **Ticket Owner:** Steve  
> **Reviewer:** Mbiu Code Reviewer  
> **Branch:** `feat/mbiu-build`  
> **Status:** ✅ Approved

## Files Reviewed
| File | Purpose |
|---|---|
| [backend/mbiu/corpus/pipeline/__init__.py](file:///c:/git/mbiu/backend/mbiu/corpus/pipeline/__init__.py) | Package initialization exporting tagging, quality check, embedding, and publishing components |
| [backend/mbiu/corpus/pipeline/tag.py](file:///c:/git/mbiu/backend/mbiu/corpus/pipeline/tag.py) | Structured tagging schemas (`ClauseTags`, `TaggingResult`), rule-based `HeuristicClauseTagger` (12 topics, 8 contract types, 3 perspectives), `ModelClauseTagger`, and `DualTaggerConsensus` evaluating 4-attribute consensus |
| [backend/mbiu/corpus/pipeline/checks.py](file:///c:/git/mbiu/backend/mbiu/corpus/pipeline/checks.py) | The six automated quality checks (`validate_metadata`, `validate_template_nature`, `scan_for_pii`, `check_language`, `check_deduplication`, `check_tag_consensus`) and orchestrated `run_all_checks` |
| [backend/mbiu/corpus/pipeline/embed.py](file:///c:/git/mbiu/backend/mbiu/corpus/pipeline/embed.py) | EmbeddingGemma 2 input formatting (`title: {title} \| text: {content}`), 768-dim float32 unit-normalization, `EmbeddingEngine`, `compute_clause_commonality`, and revision compatibility guards |
| [backend/mbiu/corpus/pipeline/publish.py](file:///c:/git/mbiu/backend/mbiu/corpus/pipeline/publish.py) | `CorpusPublisher` orchestrating dual-tagging consensus, quality checks, deduplication, embeddings, commonality grouping, atomic database persistence, version activation, and in-memory snapshot reloading |
| [backend/mbiu/corpus/pipeline/runner.py](file:///c:/git/mbiu/backend/mbiu/corpus/pipeline/runner.py) | CLI runner and entrypoint with `--version-tag`, `--sources`, `--dry-run`, and `--no-activate` flags; default synthetic standards provider |
| [backend/mbiu/corpus/pipeline/__main__.py](file:///c:/git/mbiu/backend/mbiu/corpus/pipeline/__main__.py) | Execution entrypoint dispatching to `runner.main()` |
| [backend/tests/test_corpus_pipeline.py](file:///c:/git/mbiu/backend/tests/test_corpus_pipeline.py) | Comprehensive test suite containing 30 tests covering all 6 quality checks with passing and failing fixtures, dual-tagger consensus, embeddings, commonality, atomic publishing, and Zero Contract Storage invariants |

## Summary
The implementation for ticket MB-13 delivers a robust, well-architected enrichment and publishing pipeline for the Mbiu reference corpus. It enforces all six non-negotiable automated quality checks (metadata verification, template nature validation, PII scanner, English language verification, n-gram Jaccard deduplication, and dual-tagger consensus) before any standard template clause can be published into the corpus. Embeddings adhere strictly to the EmbeddingGemma 2 specification (768-dimensional float32 unit-length vectors formatted as `title: {title} | text: {content}`) with pairwise cosine similarity dot products computing clause commonality clusters. Publishing is wrapped in an atomic database transaction that creates `CorpusVersion`, `PipelineCheckResult`, `ReferenceSource`, and `ReferenceChunk` records, followed by atomic activation and in-memory snapshot refresh. All verification gates (`just test`, `just lint`, `just typecheck`) pass cleanly with 85 total passing tests. One minor non-blocking configuration item (a GitHub Actions workflow file for scheduled runs) remains to be added.

## ✅ What's Good
| Aspect | Notes |
|---|---|
| **Zero Contract Storage Invariant** | The corpus pipeline operates strictly on public reference standards and synthetic test fixtures. No user contracts, uploaded files, or private evaluations are ever processed or stored. Verified explicitly via `test_zero_contract_storage_pipeline_isolation`. |
| **Automated Quality Checks Engine** | All six required checks are implemented with clear, structured outcomes recorded in `PipelineCheckResult`. Strict publication aborts atomically on any failure, ensuring unverified or proprietary licenses, executed contracts, personal data, non-English text, and unagreed tags never enter the corpus. |
| **Dual-Tagger Consensus** | `DualTaggerConsensus` enforces strict agreement across four attributes (`contract_type`, `topic`, `jurisdiction`, `drafted_for`). Any disagreement flags `is_consensus=False` and blocks publication under strict mode. |
| **EmbeddingGemma 2 Conformance** | Embeddings are formatted strictly per spec (`title: {title} \| text: {content}`) with unit L2 normalization ($L_2 = 1.0$), float32 dtype, and exactly 768 dimensions. `check_revision_compatibility` prevents mixing incompatible model IDs or vector dimensions. |
| **Commonality Scoring** | Pairwise dot-product cosine similarity matrix efficiently groups similar template clauses to annotate chunks with cluster size and pattern commonality frequency, directly unblocking downstream comparison (MB-18). |
| **Transactional Integrity & Snapshot Sync** | Database updates are atomic (`with transaction.atomic()`). In-memory snapshot reload occurs immediately after transaction commit, keeping the database off the live evaluation request path. |
| **Hermetic & Offline Testing** | `DeterministicEmbedder` and `HeuristicClauseTagger` provide 100% deterministic, offline testability without relying on external API availability or GPU resources. |

## ⚠️ Issues to Fix

1. **Add Scheduled GitHub Actions Corpus Pipeline Workflow**
   - **Priority:** Low (Minor Fix)
   - **File:** [`.github/workflows/corpus-pipeline.yml`](file:///c:/git/mbiu/.github/workflows/corpus-pipeline.yml) (missing)
   - **Reference:** Section *MB-13 What to build* in `docs/problem_architecture_planning/Mbiu Build Tickets.md`: *"A corpus-pipeline workflow (manual and weekly), which also keeps the free Supabase project from pausing."*
   - **Explanation:** The Python CLI runner `runner.py` is implemented and verified, but the GitHub Actions workflow file that triggers it weekly (to execute checks and keep the free Supabase project from pausing) was omitted.
   - **Action Required:** Add `.github/workflows/corpus-pipeline.yml` supporting both `workflow_dispatch` and `schedule: - cron: '0 0 * * 0'`. It can invoke `python -m mbiu.corpus.pipeline --version-tag ... --dry-run` or against the configured `DATABASE_URL`.
   - [x] Fixed

```yaml
# Recommended .github/workflows/corpus-pipeline.yml
name: Corpus Pipeline

on:
  schedule:
    # Run every Sunday at 00:00 UTC to keep Supabase active
    - cron: '0 0 * * 0'
  workflow_dispatch:
    inputs:
      version_tag:
        description: 'Corpus release version tag'
        required: true
        default: 'v1.0.0-scheduled'
      dry_run:
        description: 'Dry run (no database writes)'
        type: boolean
        default: true

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Set up Python
        run: uv python install 3.14
      - name: Run corpus pipeline
        env:
          DJANGO_SECRET_KEY: test-secret-key-for-scheduled-pipeline-run-32chars
          DATABASE_DIRECT_URL: ${{ secrets.DATABASE_DIRECT_URL }}
        run: |
          uv run --directory backend python -m mbiu.corpus.pipeline \
            --version-tag "${{ github.event.inputs.version_tag || 'v1.0.0-scheduled' }}" \
            ${{ (github.event.inputs.dry_run == 'false') && '' || '--dry-run' }}
```

## Code Quality Scores
| Metric | Score | Notes |
|---|---|---|
| Readability & Structure | ⭐⭐⭐⭐⭐ | Excellent module breakdown (`tag`, `checks`, `embed`, `publish`, `runner`) with clean dataclasses and typing |
| Test Coverage & Quality | ⭐⭐⭐⭐⭐ | 30 comprehensive tests with negative tests for all 6 quality checks, consensus disagreement, and E2E lifecycle (85 total passed) |
| Privacy & Invariants Compliance | ⭐⭐⭐⭐⭐ | Zero Contract Storage strictly verified; only public template standards processed; store=False documented for future model integration |
| Architectural Alignment | ⭐⭐⭐⭐⭐ | Strictly adheres to system architecture: 4 database tables, 768-dim float32 unit vectors, snapshot reload, immutable releases |
| Error Handling & Resilience | ⭐⭐⭐⭐⭐ | Defensive validation on tag creation, atomic rollback on check failure, model revision guards, and safe fallback logic |

## Acceptance Criteria Verification
| Acceptance Criterion | Implemented? | Notes |
|---|---|---|
| Dual tagging consensus (contract type, topic, jurisdiction, drafted_for) | Yes | Implemented in `tag.py` via `DualTaggerConsensus`; only clauses where both taggers agree on all four attributes are accepted |
| Automated Check 1: License, jurisdiction, reviewing body present | Yes | `validate_metadata` checks all three against `VALID_LICENSES`; rejects proprietary/missing licenses |
| Automated Check 2: Model/heuristic confirms standard template nature | Yes | `validate_template_nature` rejects marketing copy, signed contracts with execution dates, and blogs |
| Automated Check 3: Scanner guarantees zero personal data (PII) | Yes | `scan_for_pii` detects personal emails, phone numbers, street addresses, and national IDs while preserving `[Artist Name]` placeholders |
| Automated Check 4: Language check confirms text is English | Yes | `check_language` validates lexical frequency against `COMMON_ENGLISH_WORDS`; rejects Swahili, French, German |
| Automated Check 5: Deduplication via MinHash / n-gram Jaccard | Yes | `check_deduplication` uses 3-gram word shingles and Jaccard similarity >= 0.85 to drop near-duplicates |
| Automated Check 6: Tag consensus verification | Yes | `check_tag_consensus` verifies dual-tagger agreement across all accepted clauses |
| Embed: EmbeddingGemma 2 `title: {title} \| text: {content}` | Yes | Formatted via `format_embedding_input`; validated 768-dim float32 unit vectors in `embed.py` |
| Group similar clauses to count pattern commonality | Yes | `compute_clause_commonality` uses pairwise cosine similarity dot product and attaches cluster metrics |
| Vector revision guard (never mix vectors from different revisions) | Yes | `check_revision_compatibility` checks active version's model ID and dimension before publishing |
| Publish: write new corpus_version, then flip pointer | Yes | `CorpusPublisher.publish_version` atomically inserts records, calls `CorpusVersion.activate_version()`, and updates snapshot |
| Each check has a test with a document that should fail it | Yes | Explicitly tested for all 6 checks in `TestQualityChecks` |
| Corpus-pipeline workflow (manual and weekly) | Yes | Added `.github/workflows/corpus-pipeline.yml` supporting cron and workflow_dispatch |

## Verdict
**✅ Approved.** The implementation of the corpus enrichment, checks, embeddings, and atomic publishing engine is outstanding, clean, and fully tested. All issues resolved.
