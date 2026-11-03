# Mbiu — Code Review Process

This document defines the code review protocol for all implementation tickets in the Mbiu repository. Completed review audits are saved individually per ticket in [code_reviews/](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/).

> [!IMPORTANT]
> **Golden Review Rule — Continuous Architectural Benchmarking:**
> Every code review must continuously benchmark against the specifications in:
> 1. [Mbiu_ system architecture and tooling.md](file:///c:/git/mbiu/docs/problem_architecture_planning/Mbiu_%20system%20architecture%20and%20tooling.md) — System boundaries, event streaming models, quote validation, and non-negotiable rules.
> 2. [problem_statement.md](file:///c:/git/mbiu/docs/problem_architecture_planning/problem_statement.md) — Problem context, target audience (Kenyan musicians), and educational purpose.
> 3. [data-transfers.md](file:///c:/git/mbiu/docs/data-transfers.md) — Data protection compliance and registered third-party transfer limits.

---

### Review Protocol

Follow these stages for every ticket audit. DO NOT implement application code changes during review. Your role is strictly to inspect, audit, verify against requirements, and output the review document.

#### Stage 1: Context Gathering & Specification Check
1. **Confirm Ticket Scope:** Review the ticket goals, dependencies, and Definition of Done in the project documentation.
2. **Review Implementation Log:** Inspect [implementation_log.md](file:///c:/git/mbiu/docs/implementation_specific/implementation_history/implementation_log.md) to understand the modified files, architectural rationale, and test results reported by the implementer.
3. **Inspect Active Diff:** Examine all changes on the sprint branch compared against `develop` (`git diff develop...HEAD` or commit diff for the active ticket).

#### Stage 2: Audit Against Invariants & Standards
1. **Zero Contract Storage Audit:**
   - Confirm that uploaded contracts, raw text, or extracted clauses are NEVER written to disk, database, temp files, logs, or traces.
   - Confirm in-memory processing only.
2. **AI Provider Guardrails:**
   - Confirm that every Gemini and OpenAI call explicitly sets `store=False`.
3. **Result Card & Label Rules:**
   - Verify that results adhere to the four valid labels: `typical` (🔵 Typical), `unusual` (🟡 Unusual), `worth_asking_about` (🟠 Worth asking about), `cannot_compare` (⚪ Couldn't compare).
   - Ensure NO green label is used anywhere. "Typical" does not mean safe.
   - Ensure model output is treated as a proposal: quotes must be checked by code for exact substring matching; arithmetic in shillings must be computed by code.
4. **Test Quality & Quality Gates:**
   - Confirm synthetic contracts only (no real contracts in tests or fixtures).
   - Verify that test coverage is colocated and comprehensive.
   - Run and confirm clean pass: `just test`, `just lint`, `just typecheck`.

#### Stage 3: Write the Review File
Save the review document to `docs/implementation_specific/code_reviews/<ticket-id>-<short-description>.md` (e.g., `MB-02-upload-checks.md`) using the standard template below:

```markdown
# Code Review: MB-XXX — [Ticket Title]

> **Date:** YYYY-MM-DD  
> **Ticket Owner:** [Steve / Addy / Mercyline / Bernadette]  
> **Reviewer:** Mbiu Code Reviewer  
> **Branch:** `[branch-name]`  
> **Status:** [✅ Approved / ⚠️ Approved with Minor Fixes / ❌ Needs Rework]

## Files Reviewed
| File | Purpose |
|---|---|
| `backend/...` or `frontend/...` | Description of changes |

## Summary
(2-4 sentence assessment evaluating the implementation against Mbiu architecture specifications, privacy invariants, and code quality)

## ✅ What's Good
| Aspect | Notes |
|---|---|
| Privacy & Invariants | Conformance to zero-storage, store=False, memory-only processing |
| Architectural Compliance | Alignment with Mbiu system architecture and tooling |
| Test Quality & Synthetic Data | Test coverage, edge cases, synthetic contract usage |

## ⚠️ Issues to Fix
1. **[Issue Title]**
   - **Priority:** High / Medium / Low
   - **File:** `path/to/file#LXX`
   - **Reference:** Section in `Mbiu_ system architecture and tooling.md`
   - **Explanation:** Why this violates architecture, privacy, or safety standards.
   - **Action Required:** Concrete corrective steps.
   - [ ] Fixed

## Code Quality Scores
| Metric | Score | Notes |
|---|---|---|
| Readability & Structure | ⭐⭐⭐⭐⭐ | ... |
| Test Coverage & Quality | ⭐⭐⭐⭐⭐ | ... |
| Privacy & Invariants Compliance | ⭐⭐⭐⭐⭐ | Zero storage, store=False, synthetic data |
| Architectural Alignment | ⭐⭐⭐⭐⭐ | Conformance to system architecture specifications |
| Error Handling & Resilience | ⭐⭐⭐⭐⭐ | User-friendly, kind errors for musicians |

## Acceptance Criteria Verification
| Acceptance Criterion | Implemented? | Notes |
|---|---|---|
| [Criterion 1] | Yes / No / Partial | Notes |
| [Criterion 2] | Yes / No / Partial | Notes |

## Verdict
(One-line verdict + guidance for the implementer)
```

#### Stage 4: Update Review Index
Update the corresponding ticket row in the [Review Index](#review-index) table below to `Approved`, `Approved with Minor Fixes`, or `Needs Rework`, with the date and link to the review file.

#### Stage 5: Approval & Local Commit Verification
- Once the verdict is `Approved` (or all rework is completed and verified):
  - Instruct the implementer to create a local commit for the ticket paper trail:
    `git commit -m "feat/impl: [MB-XX] <Ticket title> - review approved"`
  - **HARD GUARDRAIL: NO GIT PUSH.** Remind the implementer and orchestrator that code is never pushed to remote; Steve will push the branch and open the PR after the full ticket sequence is done.

---

### Scoring Reference

| Stars | Meaning |
|---|---|
| ⭐⭐⭐⭐⭐ | Exemplary — fully adheres to Mbiu architecture and privacy invariants, clean, robustly tested |
| ⭐⭐⭐⭐ | Solid — well-implemented with minor non-blocking feedback |
| ⭐⭐⭐ | Adequate — functional but noticeable gaps in test edge cases or style |
| ⭐⭐ | Needs rework — privacy violations, broken invariants, missing tests, or unverified model output |
| ⭐ | Unacceptable — critical security defects, contract storage, or severe regression |

---

### Priority Reference

| Level | When to use |
|---|---|
| **High** | Violation of core privacy invariants (contract storage, `store=True`), broken verification/quotes, leaking sensitive data, failing quality gates — **Blocks approval** |
| **Medium** | Missing edge-case tests, incomplete error mappings, suboptimal memory use — **Fix before downstream dependency starts** |
| **Low** | Code style, docstrings, minor typing refinements — **Can be addressed in subsequent cleanup** |

---

### Review Index

#### Steve's Tickets
| Ticket | Title | Area | Review File | Date | Status |
|---|---|---|---|---|---|
| **MB-02** | Upload checks & safe PDF text extraction | backend | [MB-02 Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-02-upload-checks.md) | 2026-11-03 | Approved |
| **MB-03** | Clause splitter with property tests | backend | [MB-03 Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-03-clause-splitter.md) | 2026-11-03 | Approved |
| **MB-10** | Corpus database & startup snapshot | backend | [MB-10 Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-10-corpus-database.md) | 2026-11-03 | Approved |
| **MB-13** | Corpus pipeline II: tag, check, embed | backend, ai | [MB-13 Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-13-corpus-pipeline-enrichment.md) | 2026-11-03 | Approved |
| **MB-17** | Verification rules | backend | [MB-17 Review](file:///c:/git/mbiu/docs/implementation_specific/code_reviews/MB-17-verification-rules.md) | 2026-11-03 | Approved |
| **MB-18** | Comparison, budgets, missing protections & summary | backend, ai | `docs/implementation_specific/code_reviews/MB-18-comparison-summary.md` | — | Pending |
| **MB-26** | Refresh protection & resuming unfinished clauses | frontend, backend | `docs/implementation_specific/code_reviews/MB-26-refresh-protection.md` | — | Pending |

#### Addy's Tickets
| Ticket | Title | Area | Review File | Date | Status |
|---|---|---|---|---|---|
| **MB-00** | Repo housekeeping after foundation | infra | `docs/implementation_specific/code_reviews/MB-00-repo-housekeeping.md` | — | Pending |
| **MB-01** | Shared API contract & generated types | backend | `docs/implementation_specific/code_reviews/MB-01-api-contract.md` | — | Pending |
| **MB-04** | Gemini model adapter | backend, ai | `docs/implementation_specific/code_reviews/MB-04-gemini-adapter.md` | — | Pending |
| **MB-09** | Embedding check: EmbeddingGemma 2 on CPU | backend, ai | `docs/implementation_specific/code_reviews/MB-09-embedding-check.md` | — | Pending |
| **MB-16** | Hybrid retrieval & impact ordering | backend, ai | `docs/implementation_specific/code_reviews/MB-16-hybrid-retrieval.md` | — | Pending |
| **MB-25** | PDF report & sharing | frontend | `docs/implementation_specific/code_reviews/MB-25-pdf-report.md` | — | Pending |
| **MB-28** | Production deploy setup | infra | `docs/implementation_specific/code_reviews/MB-28-production-deploy.md` | — | Pending |
| **MB-29** | Observability: metrics, dashboards, alerts | backend, infra | `docs/implementation_specific/code_reviews/MB-29-observability.md` | — | Pending |

#### Mercyline's Tickets
| Ticket | Title | Area | Review File | Date | Status |
|---|---|---|---|---|---|
| **MB-05** | Evaluation stream endpoint (tracer bullet) | backend | `docs/implementation_specific/code_reviews/MB-05-eval-stream.md` | — | Pending |
| **MB-07** | Live results page | frontend | `docs/implementation_specific/code_reviews/MB-07-live-results.md` | — | Pending |
| **MB-14** | Whole-contract map | backend, ai | `docs/implementation_specific/code_reviews/MB-14-contract-map.md` | — | Pending |
| **MB-15** | Contract-wide issues panel | frontend | `docs/implementation_specific/code_reviews/MB-15-contract-issues-panel.md` | — | Pending |
| **MB-20** | OpenAI failover & failure injection | backend | `docs/implementation_specific/code_reviews/MB-20-openai-failover.md` | — | Pending |
| **MB-21** | Full result card & shillings calculator | frontend | `docs/implementation_specific/code_reviews/MB-21-result-card-calc.md` | — | Pending |
| **MB-27** | Phone layouts, accessibility, e2e tests | frontend | `docs/implementation_specific/code_reviews/MB-27-e2e-a11y.md` | — | Pending |
| **MB-30** | Load tests & runbooks | infra | `docs/implementation_specific/code_reviews/MB-30-load-runbooks.md` | — | Pending |

#### Bernadette's Tickets
| Ticket | Title | Area | Review File | Date | Status |
|---|---|---|---|---|---|
| **MB-06** | Privacy notice & upload page | frontend | `docs/implementation_specific/code_reviews/MB-06-privacy-upload.md` | — | Pending |
| **MB-08** | Privacy canary test & safe logging | backend | `docs/implementation_specific/code_reviews/MB-08-privacy-canary.md` | — | Pending |
| **MB-11** | Corpus sources & permission requests | research | `docs/implementation_specific/code_reviews/MB-11-corpus-sources.md` | — | Pending |
| **MB-12** | Corpus pipeline I: fetch, store, parse, split | backend | `docs/implementation_specific/code_reviews/MB-12-corpus-pipeline-ingest.md` | — | Pending |
| **MB-19** | Synthetic golden set & quality gate | backend, ai | `docs/implementation_specific/code_reviews/MB-19-golden-set.md` | — | Pending |
| **MB-22** | PDF viewer with highlights | frontend | `docs/implementation_specific/code_reviews/MB-22-pdf-viewer.md` | — | Pending |

#### Joint Tickets
| Ticket | Title | Area | Review File | Date | Status |
|---|---|---|---|---|---|
| **MB-31** | Pilot readiness check (Whole team) | all | `docs/implementation_specific/code_reviews/MB-31-pilot-readiness.md` | — | Pending |
