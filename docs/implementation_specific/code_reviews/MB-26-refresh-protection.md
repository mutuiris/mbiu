# Code Review: MB-26 — Refresh protection and resuming unfinished clauses

> **Date:** 2026-11-03  
> **Ticket Owner:** Steve  
> **Reviewer:** Mbiu Code Reviewer  
> **Branch:** `feat/mbiu-build`  
> **Status:** ✅ Approved

## Files Reviewed
| File | Purpose |
|---|---|
| [`backend/config/urls.py`](file:///c:/git/mbiu/backend/config/urls.py) | Mounted `POST /api/v1/clause-evaluations` and `/api/v1/clause-evaluations/` pointing to `clause_evaluations_view`. |
| [`backend/mbiu/evaluation/__init__.py`](file:///c:/git/mbiu/backend/mbiu/evaluation/__init__.py) | Exported `clause_evaluations_view` and `generate_clause_evaluation_events`. |
| [`backend/mbiu/evaluation/views.py`](file:///c:/git/mbiu/backend/mbiu/evaluation/views.py) | Stateless clause evaluation endpoint. Streams newline-delimited JSON (NDJSON) events (`progress`, `clause_result`, `clause_failed`, `done`) with `Cache-Control: no-store`. Evaluates clauses in-memory using MB-17/18 comparison engines; handles unreviewed types with `cannot_compare`; executes reverse checks; returns 400/405 for invalid requests. |
| [`frontend/src/lib/keep-tab.ts`](file:///c:/git/mbiu/frontend/src/lib/keep-tab.ts) | Tab-only `sessionStorage` management for evaluation state. Enforces explicit opt-in toggle (default off), 60-minute TTL expiration, explicit clearing (`clearTabResults`), and exact non-saved explanation message. Safe for SSR and zero server storage. |
| [`frontend/src/lib/refresh-protection.ts`](file:///c:/git/mbiu/frontend/src/lib/refresh-protection.ts) | Accidental reload protection via `beforeunload` dialog and React hook `useRefreshProtection`; mobile pull-to-refresh prevention with CSS `overscroll-behavior-y: contain`; streaming resumption (`resumeUnfinishedClauses`) that sends only unfinished/failed clauses, parses NDJSON streams, and preserves arrived cards on stream drops. |
| [`backend/tests/test_clause_evaluations_endpoint.py`](file:///c:/git/mbiu/backend/tests/test_clause_evaluations_endpoint.py) | 11 comprehensive tests verifying NDJSON streaming, JSON response mode, URL routing with/without trailing slash, unreviewed contract type handling, input validation errors (empty clauses, missing clauses, malformed JSON, invalid clause structure, method not allowed), and zero contract storage with no database rows or temporary files created. |
| [`backend/tests/test_verify.py`](file:///c:/git/mbiu/backend/tests/test_verify.py) | Refined zero-storage canary assertion to inspect for contract markers in temp directory files, preventing false positive failures caused by concurrent external OS temp file creation. |
| [`frontend/tests/keep-tab.test.ts`](file:///c:/git/mbiu/frontend/tests/keep-tab.test.ts) | 9 unit tests verifying opt-in default, opt-in toggling, saving/restoring, 60-minute TTL expiration, explicit clearing, and not-saved message. |
| [`frontend/tests/refresh-protection.test.ts`](file:///c:/git/mbiu/frontend/tests/refresh-protection.test.ts) | 7 unit tests verifying beforeunload prevention, overscroll style helper, unfinished clause calculation, NDJSON chunk parsing, resumption of only unfinished clauses, and preservation of arrived cards upon mid-stream network drops. |
| [`frontend/package.json`](file:///c:/git/mbiu/frontend/package.json) | Configured `"type": "module"` and added `"test": "node --test --experimental-strip-types tests/**/*.test.ts"` for fast, zero-dependency Node.js native testing. |
| [`frontend/tsconfig.json`](file:///c:/git/mbiu/frontend/tsconfig.json) | Enabled `"allowImportingTsExtensions": true` for clean ESM module resolution with TypeScript extensions. |
| [`justfile`](file:///c:/git/mbiu/justfile) | Updated `test:` recipe to execute both backend pytest and frontend test runner. |

## Summary
The implementation of **MB-26** provides robust multi-layered refresh protection, tab-only session preservation, and stateless clause resumption across the backend and frontend. The backend endpoint `POST /api/v1/clause-evaluations` operates strictly statelessly and in memory, streaming NDJSON events with `Cache-Control: no-store` headers and zero database or disk persistence. The frontend provides accidental refresh guards (`beforeunload` confirmation, `overscroll-behavior-y: contain`), an explicit opt-in toggle (off by default) storing results in tab-only `sessionStorage` with a 60-minute TTL, and resumption logic that queries only unfinished or failed clauses while retaining all previously arrived cards if a stream drops. All quality gates pass cleanly across backend and frontend (`just test`, `just lint`, `just typecheck`).

## ✅ What's Good
| Aspect | Notes |
|---|---|
| **Zero Contract Storage Invariant** | Backend evaluation operates completely in memory with `Cache-Control: no-store, no-cache, must-revalidate`. Confirmed by `test_clause_evaluations_zero_contract_storage` that no database rows (ReferenceChunk, CorpusVersion) or temp files are created. Frontend utilizes tab-only `sessionStorage`, cleared upon tab closure or after 60 minutes, with zero persistent storage or server tracking. |
| **Accidental Refresh Protection** | Accidental refresh is defended on two fronts: `beforeunload` confirmation dialogs active while results/chat are displayed, and CSS `overscroll-behavior-y: contain` to prevent mobile pull-to-refresh gestures. |
| **Tab-Only SessionStorage & Privacy Invariant** | Strictly conforms to Rule 1: opt-in is off by default with the exact mandated notice text (*"Keep my results if this page reloads. Leave this off on a shared phone."*); cached state automatically expires after 60 minutes (`KEEP_TAB_TTL_MS = 3600000`); disabling opt-in or invoking `clearTabResults()` immediately purges storage; and unopted reloads display the exact required explanatory message (*"Your results weren't saved on this device. Upload the contract again to see them."*). |
| **Stateless Resumption & Stream Drop Resilience** | `resumeUnfinishedClauses` computes only unfinished or failed clauses (`getUnfinishedClauses`), sends only those clauses to `POST /api/v1/clause-evaluations`, and progressively saves arriving cards. Mid-stream connection drops preserve all cards received so far. |
| **Model Output as Proposal & The Four Valid Labels** | Downstream model outputs are verified via MB-17 verification rules; unreviewed contract types (e.g. `podcast_host`) emit `cannot_compare` with `NO_STANDARD_FOR_TYPE_MESSAGE`; and TypeScript models enforce the four valid labels (`typical`, `unusual`, `worth_asking_about`, `cannot_compare`) with no green labels. |
| **Reverse Check Integration** | Stateless evaluation automatically runs `check_missing_protections` on the evaluated clauses and outputs a consolidated `EvaluationSummary` in the final `done` event. |
| **Comprehensive Test Coverage** | 11 backend tests (streaming, non-streaming JSON, trailing slashes, validation errors, 405 methods, zero-storage canary) and 16 frontend tests (Node.js 24 test runner) covering opt-in, TTL expiration, clearing, overscroll, unfinished filtering, NDJSON parsing, and network drop recovery. |

## ⚠️ Issues to Fix

1. **Standardize exception tuple syntax in `clause_evaluations_view`**
   - **Priority:** Low
   - **File:** [`backend/mbiu/evaluation/views.py#L487`](file:///c:/git/mbiu/backend/mbiu/evaluation/views.py#L487)
   - **Reference:** PEP 8 and Python cross-version compatibility.
   - **Explanation:** Line 487 currently specifies `except json.JSONDecodeError, UnicodeDecodeError:`. While accepted in Python 3.14, catching multiple exception types in Python standard syntax requires a parenthesized tuple: `except (json.JSONDecodeError, UnicodeDecodeError):`. Without parentheses, in earlier Python runtimes this is either a `SyntaxError` or misinterprets `UnicodeDecodeError` as the target exception variable name.
   - **Action Required:** Wrap the exception types in parentheses:
     ```python
     except (json.JSONDecodeError, UnicodeDecodeError):
         return JsonResponse({"error": "Invalid JSON request body."}, status=400)
     ```
   - [ ] Fixed

2. **Update developer `just.ps1` runner script to include frontend tests**
   - **Priority:** Low (Developer Environment Hygiene)
   - **File:** `C:\Users\Steve Wanangwe\AppData\Roaming\npm\just.ps1`
   - **Reference:** Definition of Done and Quality Gate Automation.
   - **Explanation:** The repository's [`justfile`](file:///c:/git/mbiu/justfile#L28-L30) was updated so `test:` runs both `pytest` and `pnpm --dir frontend test`. However, the local Windows developer wrapper script `just.ps1` only executes pytest under `"test"` and immediately exits with `$LASTEXITCODE`. Updating `just.ps1` to run `pnpm --dir frontend test` will ensure running `just test` locally on Windows executes both test suites synchronously, matching what `just lint` and `just typecheck` already do.
   - **Action Required:** Update `"test"` in `just.ps1`:
     ```powershell
     "test" {
         & uv run --directory backend pytest @RemainingArgs
         if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
         & pnpm --dir frontend test
         exit $LASTEXITCODE
     }
     ```
   - [ ] Fixed

## Code Quality Scores
| Metric | Score | Notes |
|---|---|---|
| Readability & Structure | ⭐⭐⭐⭐⭐ | Clean modular separation between storage (`keep-tab.ts`), stream resumption (`refresh-protection.ts`), and stateless views (`views.py`) |
| Test Coverage & Quality | ⭐⭐⭐⭐⭐ | 11 backend tests + 16 frontend unit tests covering opt-in, TTL, overscroll, NDJSON streaming, and network drop recovery |
| Privacy & Invariants Compliance | ⭐⭐⭐⭐⭐ | Zero contract storage strictly maintained; `Cache-Control: no-store`; tab-only `sessionStorage`; 60-min TTL; no green label; synthetic contracts only |
| Architectural Alignment | ⭐⭐⭐⭐⭐ | Strict alignment with Part 3 lines 160-162 and lines 388-403 of system architecture specifications |
| Error Handling & Resilience | ⭐⭐⭐⭐⭐ | Kind artist messages on unreviewed types; 400 Bad Request on invalid payloads; graceful state preservation on dropped streams |

## Acceptance Criteria Verification
| Acceptance Criterion | Implemented? | Notes |
|---|---|---|
| Backend `POST /api/v1/clause-evaluations` re-evaluates specific clauses | Yes | Implemented in `views.py`; mounted in `urls.py`; streams NDJSON `progress`, `clause_result`, `clause_failed`, `done` |
| Confirmation dialog (`beforeunload`) while results/chat on screen | Yes | Implemented via `beforeUnloadConfirmationHandler` and `useRefreshProtection` hook |
| Mobile pull-to-refresh prevention (`overscroll-behavior-y: contain`) | Yes | Implemented via `getOverscrollContainmentStyle` and `applyOverscrollContainment` |
| Opt-in switch for tab-only storage (off by default) | Yes | Implemented via `getKeepTabOptIn`, `setKeepTabOptIn`, matching exact notice text |
| Results kept in `sessionStorage` for tab only, cleared on tab close, 60 min, or Clear now | Yes | Implemented in `keep-tab.ts` (`KEEP_TAB_TTL_MS = 3600000`, `clearTabResults`) |
| Non-opt-in restore message: *"Your results weren't saved on this device. Upload the contract again to see them."* | Yes | Exact message returned by `restoreTabResults()` when not opted in |
| Stream drop resilience: keep what arrived and resume only unfinished clauses | Yes | `resumeUnfinishedClauses` preserves arrived cards in state and storage upon stream failure |
| Reverse check & summary in done event | Yes | `check_missing_protections` and `generate_evaluation_summary` attached to `done` event |
| Verification gates pass (`just test`, `just lint`, `just typecheck`) | Yes | Backend: 183 passed; Frontend: 16 passed; Lint: clean; Typecheck: clean |

## Verdict
**✅ Approved.** Ticket MB-26 fulfills all architectural, privacy, and UX requirements. Accidental refresh protection, 60-minute tab-only sessionStorage, stateless clause resumption, and network drop resilience are robustly implemented and tested. The two low-priority items (exception tuple parentheses and local `just.ps1` test command) are non-blocking and can be addressed during standard maintenance. Ready for local commit.
