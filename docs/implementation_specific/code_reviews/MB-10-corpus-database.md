# Code Review: MB-10 — Corpus database and startup snapshot

> **Date:** 2026-11-03  
> **Ticket Owner:** Steve  
> **Reviewer:** Mbiu Code Reviewer  
> **Branch:** `feat/mbiu-build`  
> **Status:** ✅ Approved

## Files Reviewed
| File | Purpose |
|---|---|
| [backend/mbiu/corpus/models.py](file:///c:/git/mbiu/backend/mbiu/corpus/models.py) | Definitions of the four corpus application models (`ReferenceSource`, `CorpusVersion`, `ReferenceChunk`, `PipelineCheckResult`) with single active version constraints and immutability rules |
| [backend/mbiu/corpus/migrations/0001_initial.py](file:///c:/git/mbiu/backend/mbiu/corpus/migrations/0001_initial.py) | Initial migration enabling `VectorExtension`, establishing table schemas and unique constraints, and enabling Row Level Security (RLS) on Postgres |
| [backend/mbiu/corpus/loader.py](file:///c:/git/mbiu/backend/mbiu/corpus/loader.py) | Thread-safe in-memory corpus snapshot loader and accessors (`load_corpus_snapshot`, `get_active_corpus_snapshot`, `clear_corpus_snapshot`) |
| [backend/mbiu/corpus/apps.py](file:///c:/git/mbiu/backend/mbiu/corpus/apps.py) | AppConfig `ready()` hook attempting startup snapshot loading, safely bypassing CLI/test commands |
| [backend/mbiu/health.py](file:///c:/git/mbiu/backend/mbiu/health.py) | Readiness probe `/readyz` checking DB connectivity and loaded active corpus snapshot |
| [backend/config/settings.py](file:///c:/git/mbiu/backend/config/settings.py) | Added direct URL setting, connection options (`connect_timeout: 3`), SQLite fallback parsing, and registered `"pgvector.django"` & `"mbiu.corpus"` |
| [backend/pyproject.toml](file:///c:/git/mbiu/backend/pyproject.toml) | Added `numpy>=2.5.4` and `pgvector>=0.5.1` dependencies; ruff ignore for migrations |
| [.github/workflows/ci.yml](file:///c:/git/mbiu/.github/workflows/ci.yml) | Added `pgvector/pgvector:pg17` service container and configured database environment |
| [backend/tests/conftest.py](file:///c:/git/mbiu/backend/tests/conftest.py) | Test harness configuring automated fallback to in-memory SQLite when Postgres is unavailable locally |
| [backend/tests/test_corpus.py](file:///c:/git/mbiu/backend/tests/test_corpus.py) | Comprehensive test suite for corpus models, zero storage invariant, immutability, atomic version activation, and in-memory loader |
| [backend/tests/test_health.py](file:///c:/git/mbiu/backend/tests/test_health.py) | Unit tests verifying `/readyz` failure modes and 200 ready transitions |
| [backend/manage.py](file:///c:/git/mbiu/backend/manage.py) | Django management CLI entrypoint |

## Summary
The implementation of ticket MB-10 strictly fulfills all architectural and privacy specifications laid out in the Mbiu system architecture and ticket definitions. It creates exactly four database tables for reference standard templates and metadata, with zero tables or columns for user contracts or evaluation results. The startup snapshot loader reads the active corpus release once into memory (numpy `float32` embeddings and metadata dictionaries), keeping the database off the request path during evaluation. All verification gates (`just test`, `just lint`, `just typecheck`) pass cleanly.

## ✅ What's Good
| Aspect | Notes |
|---|---|
| **Privacy & Invariants** | **Strict Zero Contract Storage:** Audited schema contains exactly the 4 allowed tables (`reference_sources`, `corpus_versions`, `reference_chunks`, `pipeline_check_results`). No tables or columns exist for uploaded files, raw contract text, or evaluation results. Tested explicitly via `test_zero_contract_storage_database_schema`. |
| **Database Off Request Path** | `CorpusSnapshot` encapsulates embeddings as a 2D `np.ndarray` of shape `(N, embedding_dim)` and metadata in indexed frozen dataclasses, allowing downstream retrieval (MB-16) to execute entirely in-process without DB queries. |
| **Single Active Version Guarantee** | Enforced at both the Django model `clean()` level and PostgreSQL partial unique index level (`UniqueConstraint` on `is_active=True`). Atomic version switching is implemented safely via `activate_version()` with `select_for_update()`. |
| **Corpus Immutability** | Published versions cannot modify `version_tag`, `embedding_model_id`, or `embedding_dim` in place, ensuring that references and evaluations are reproducible and auditable. |
| **Row Level Security (RLS)** | Migration enables RLS on all 4 tables in Postgres/Supabase via `PostgresRunSQL`, while cleanly bypassing SQLite during local test execution. |
| **Readiness Integration** | `/readyz` correctly reports 503 with `"corpus"` in `failed` if no snapshot is loaded, and returns 200 `{"status": "ready"}` when both DB and corpus are operational. |
| **Developer Experience & CI** | Dual support for GitHub Actions Postgres service container (`pgvector/pgvector:pg17`) and zero-setup local SQLite fallback in `conftest.py`. |

## ⚠️ Issues to Fix
*None.* The implementation satisfies all acceptance criteria without regressions or blocking defects.

## Code Quality Scores
| Metric | Score | Notes |
|---|---|---|
| Readability & Structure | ⭐⭐⭐⭐⭐ | Clean, idiomatic Django and typing; clean separation between models, migrations, and in-memory loader |
| Test Coverage & Quality | ⭐⭐⭐⭐⭐ | 16 new tests covering schema invariants, constraints, immutability, loader behavior, DB errors, and readiness probe integration (55 passed total) |
| Privacy & Invariants Compliance | ⭐⭐⭐⭐⭐ | Zero contract storage strictly enforced and programmatically asserted |
| Architectural Alignment | ⭐⭐⭐⭐⭐ | Matches architecture specifications: 4 tables, pgvector column, in-memory startup snapshot, RLS |
| Error Handling & Resilience | ⭐⭐⭐⭐⭐ | Thread-safe snapshot caching, graceful fallback in `ready()`, robust error handling for missing/empty versions and DB connection failures |

## Acceptance Criteria Verification
| Acceptance Criterion | Implemented? | Notes |
|---|---|---|
| 4 application tables (`reference_sources`, `reference_chunks`, `corpus_versions`, `pipeline_check_results`) | Yes | Defined in `models.py` and migration `0001_initial.py`; zero user contract tables exist |
| Single active corpus version pointer | Yes | Enforced at application validation level and via database unique constraint; atomic activation via `activate_version()` |
| Published versions immutable | Yes | Verified in `CorpusVersion.clean()` and unit tested in `test_published_corpus_version_is_immutable` |
| Migration with pgvector vector extension | Yes | Initial migration includes `VectorExtension()` and 768-dim `VectorField` |
| Migrations support `DATABASE_DIRECT_URL` | Yes | `direct` database alias configured in `settings.py` |
| Startup loader loads active version into memory (numpy + metadata) | Yes | `load_corpus_snapshot()` loads active chunks into `np.ndarray` and `ChunkMetadata` |
| `/readyz` returns 503 with `"corpus"` in `failed` when no version is active | Yes | Verified in `test_readyz_fails_when_corpus_snapshot_not_loaded` and `test_readyz_integration_with_database_and_corpus_loader` |
| Row Level Security (RLS) enabled on all 4 tables | Yes | Migration runs `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` via `PostgresRunSQL` |
| CI includes real Postgres service container | Yes | Configured in `.github/workflows/ci.yml` with `pgvector/pgvector:pg17` |

## Verdict
**✅ Approved.** All acceptance criteria, architectural invariants, and verification gates are satisfied with excellence. Steve is instructed to create the local commit:
`git commit -m "feat/impl: [MB-10] Corpus database & startup snapshot - review approved"`
*(Reminder: Do not push to remote).*
