# Code Review: MB-18 — Comparison, budgets, missing protections & summary

> **Date:** 2026-11-03  
> **Ticket Owner:** Steve  
> **Reviewer:** Mbiu Code Reviewer  
> **Branch:** `feat/mbiu-build`  
> **Status:** ✅ Approved

## Files Reviewed
| File | Purpose |
|---|---|
| [`backend/config/settings.py`](file:///c:/git/mbiu/backend/config/settings.py) | Added settings for batch sizing (`BATCH_SIZE=6`), concurrency (`LLM_CONCURRENCY=4`), token budgets (`TOKEN_BUDGET_PER_CONTRACT=400,000`), per-batch timeout (`BATCH_TIMEOUT_S=30.0`), and contract evaluation deadlines (`DEADLINE_PER_CLAUSE_S=3.0`, `DEADLINE_CAP_S=300.0`). |
| [`backend/mbiu/evaluation/__init__.py`](file:///c:/git/mbiu/backend/mbiu/evaluation/__init__.py) | Exported public symbols for budgets, impact classification, batch creation, comparison outcomes, reverse checks, and summary models. |
| [`backend/mbiu/evaluation/budgets.py`](file:///c:/git/mbiu/backend/mbiu/evaluation/budgets.py) | Impact ordering engine (Money/Ownership prioritized over Boilerplate), balanced clause batching (4–8 items), token/time budget tracker, and asynchronous batch runner. |
| [`backend/mbiu/evaluation/comparison.py`](file:///c:/git/mbiu/backend/mbiu/evaluation/comparison.py) | Result card model (`ClauseEvaluationResult`), verification orchestration with MB-17, missing reviewed standard fallback, template disagreement formatting, impact inputs validation (code shillings calculation), fairer wording extraction, and reverse check for missing protections. |
| [`backend/mbiu/evaluation/summary.py`](file:///c:/git/mbiu/backend/mbiu/evaluation/summary.py) | Consolidated evaluation summary generator (`EvaluationSummary`), top 3 asks ranking by impact on money/ownership, good news compilation, ask list checklist, and provenance versions. |
| [`backend/tests/test_comparison.py`](file:///c:/git/mbiu/backend/tests/test_comparison.py) | 17 focused unit tests covering impact ordering, batch sizing, budget exhaustion, async timeout handling, impact inputs, template disagreements, reverse checks, and zero-storage invariants. |
| [`backend/tests/test_summary.py`](file:///c:/git/mbiu/backend/tests/test_summary.py) | 5 comprehensive tests covering summary generation, top asks ranking, label counts, architectural property aliases, and zero-storage invariants. |

## Summary
The implementation of **MB-18** establishes the core comparison, budgeting, missing protections, and summary aggregation layer for the Mbiu platform. It implements impact-based clause ordering ensuring high-stakes provisions (Money, Ownership, Term, Exclusivity, Termination) are evaluated before operational boilerplate, dynamic batching (4–8 clauses per batch), contract-level token and time budget tracking with artist-friendly exhaustion messaging, and reverse checks detecting absent standard protections. All model outputs are treated strictly as proposals routed through MB-17 verification; arithmetic in shillings is strictly reserved for code execution via validated `MoneyExampleInputs`; fairer wording is verified as exact, unaltered template substrings; and the summary generator isolates the top 3 questions impacting money and ownership. All verification gates (`just test`, `just lint`, `just typecheck`) pass cleanly with 172 tests and zero warnings. A few minor implementation issues should be addressed to ensure true batch concurrency and prevent list mutation during deduction pruning.

## ✅ What's Good
| Aspect | Notes |
|---|---|
| **Zero Contract Storage Invariant** | Evaluation results, batches, comparisons, and summaries operate strictly in memory. Confirmed by `test_zero_contract_storage_during_comparison` and `test_zero_contract_storage_summary` that 0 temporary files or database records are created. |
| **Model Output as Proposal & Code Shillings Arithmetic** | The model is strictly prevented from executing arithmetic in shillings. `validate_impact_inputs` parses rate, basis, deductions, and exact verbatim quotes for frontend calculation. Fairer wording is verified as an exact template substring unchanged. |
| **Four Labels & Zero Green Label** | Strictly adheres to the four approved labels: `typical` (🔵 Typical), `unusual` (🟡 Unusual), `worth_asking_about` (🟠 Worth asking about), and `cannot_compare` (⚪ Couldn't compare). Zero green labels are present. |
| **Reverse Check & Objective Tone** | `check_missing_protections` scans for 5 standard protective clauses (audit rights, accounting frequency, termination on non-payment, written deduction approvals, rights reversion) and emits `worth_asking_about` with cautious, objective phrasing ("We didn't find..."). |
| **Impact Ordering & Budget Exhaustion Messaging** | Stable sorting prioritizes Money (100) and Ownership (90) over Boilerplate (10). Budget exhaustion triggers the exact required plain-language notification: *"Mbiu checked the most important clauses first. N clauses aren't checked yet."* |
| **Consolidated Summary & Top 3 Asks** | `generate_evaluation_summary` aggregates label counts, good news, missing protections, unchecked clauses, and isolates the top 3 actionable negotiation questions ranked by money/ownership impact. Backwards-compatible aliases (`top_questions`, `contract_wide_issues`, `not_found_items`, `all_questions`) preserve architectural parity. |
| **Test Quality & Synthetic Scenarios** | 22 colocated tests verifying positive and negative fixtures, edge cases, and invariants using 100% synthetic contracts. |

## ⚠️ Issues to Fix

1. **Fix in-place mutation of `deductions` list during iteration in `validate_impact_inputs`**
   - **Priority:** Medium
   - **File:** [`backend/mbiu/evaluation/comparison.py#L228-L233`](file:///c:/git/mbiu/backend/mbiu/evaluation/comparison.py#L228-L233)
   - **Reference:** Section *Model output is a proposal, not a result* in `Mbiu_ system architecture and tooling.md`
   - **Explanation:** In `validate_impact_inputs`, the loop iterates over `deductions` while calling `deductions.remove(d)`. In Python, removing an item from a list during iteration shifts subsequent elements left, causing the loop index to skip the immediately following element. If candidate inputs contain consecutive ungrounded deductions (e.g., `["ungrounded_cost_1", "ungrounded_cost_2"]`), the second ungrounded deduction is skipped and erroneously retained.
   - **Action Required:** Prune ungrounded deductions using list comprehension or iterate over a shallow copy:
     ```python
     deductions = [
         d for d in deductions
         if normalize_whitespace(str(d)) and normalize_whitespace(str(d)) in norm_clause
     ]
     ```
    - [x] Fixed

2. **Enable true parallel batch execution in `run_evaluation_batches`**
   - **Priority:** Medium
   - **File:** [`backend/mbiu/evaluation/budgets.py#L481-L523`](file:///c:/git/mbiu/backend/mbiu/evaluation/budgets.py#L481-L523)
   - **Reference:** Section *Compare in batches* in `Mbiu_ system architecture and tooling.md#L145` ("Compare in batches of 4 to 8 clauses, in impact order, run in parallel under a concurrency limit") and Ticket MB-18 specification in `Mbiu Build Tickets.md#L744`.
   - **Explanation:** `run_evaluation_batches` loops over `batches` and directly awaits `await asyncio.wait_for(batch_evaluator(batch), ...)` inside a single coroutine loop wrapped in `async with semaphore:`. Because each batch is awaited sequentially before the loop advances to the next batch, batches are processed one at a time. The semaphore has no effect because only one task ever accesses it, meaning batch evaluation does not run in parallel under `settings.LLM_CONCURRENCY`.
   - **Action Required:** Dispatch batches concurrently up to `concurrency` (e.g. using worker tasks pulling from an `asyncio.Queue` or `asyncio.gather` with dynamic budget checks) so batches run concurrently up to `LLM_CONCURRENCY` while preserving budget termination and impact order.
   - [x] Fixed

3. **Remove dead code statement expression in `run_evaluation_batches`**
   - **Priority:** Low
   - **File:** [`backend/mbiu/evaluation/budgets.py#L489`](file:///c:/git/mbiu/backend/mbiu/evaluation/budgets.py#L489)
   - **Reference:** Repository hygiene and clean code standards.
   - **Explanation:** Line 489 contains the orphaned expression `total_clauses - processed_count` with no assignment, side effect, or usage.
   - **Action Required:** Remove line 489.
   - [x] Fixed

## Code Quality Scores
| Metric | Score | Notes |
|---|---|---|
| Readability & Structure | ⭐⭐⭐⭐⭐ | Clean modular design across budgets, comparison, and summary; clean dataclasses |
| Test Coverage & Quality | ⭐⭐⭐⭐⭐ | 22 comprehensive tests covering ordering, batching, timeouts, budgets, reverse checks, and summary |
| Privacy & Invariants Compliance | ⭐⭐⭐⭐⭐ | Zero contract storage strictly verified, no green labels, 4 labels enforced, synthetic data |
| Architectural Alignment | ⭐⭐⭐⭐⭐ | High architectural compliance; concurrent queue execution in batch runner preserves order and budgets |
| Error Handling & Resilience | ⭐⭐⭐⭐⭐ | Artist-friendly budget exhaustion messages, missing standard fallback, and safe empty state handling |

## Acceptance Criteria Verification
| Acceptance Criterion | Implemented? | Notes |
|---|---|---|
| Batches of 4–8 clauses in impact order | Yes | `order_clauses_by_impact` and `create_clause_batches` dynamically balance batches within [4, 8] |
| Concurrency limit (`LLM_CONCURRENCY`) | Yes | Concurrent worker tasks pull from async queue with in-flight token reservations |
| Per-batch time budget & contract token budget | Yes | `EvaluationBudgetTracker` enforces batch timeouts and total token limits |
| Budget exhaustion message | Yes | Invariant message *"Mbiu checked the most important clauses first. N clauses aren't checked yet."* |
| Impact inputs for code-calculated shillings | Yes | `validate_impact_inputs` parses rate, basis, deductions, and quotes without arithmetic |
| Fairer wording is exact template clause unchanged | Yes | `extract_fairer_wording` validates candidate against reference chunks |
| Reverse check for missing protections | Yes | `check_missing_protections` scans for 5 standard protective clauses |
| Template disagreement formatting | Yes | `format_template_disagreement` formats *"Standard templates differ here..."* |
| Missing template standard handling | Yes | Emits `cannot_compare` with *"Mbiu doesn't have a reviewed standard..."* |
| Summary generation with top 3 asks | Yes | Aggregates all summary fields, versions, and ranks top 3 asks by money/ownership impact |
| Verification gates pass (`just test`, `just lint`, `just typecheck`) | Yes | 172 passed in 37.84s; ruff check & format clean; mypy strict & tsc clean |

## Verdict
**✅ Approved.** All requested fixes (list comprehension for deduction filtering, concurrent worker queue with token reservation, and dead code cleanup) have been implemented and verified. All quality gates pass 100%. Ready for local commit.
