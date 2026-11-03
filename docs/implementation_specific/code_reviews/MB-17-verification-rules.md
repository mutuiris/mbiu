# Code Review: MB-17 — Verification rules

> **Date:** 2026-11-03  
> **Ticket Owner:** Steve  
> **Reviewer:** Mbiu Code Reviewer  
> **Branch:** `feat/mbiu-build`  
> **Status:** ✅ Approved

## Files Reviewed
| File | Purpose |
|---|---|
| [`backend/mbiu/evaluation/__init__.py`](file:///c:/git/mbiu/backend/mbiu/evaluation/__init__.py) | Package initialization exporting evaluation types, verification rules, repair workflow, and observability counters |
| [`backend/mbiu/evaluation/verify.py`](file:///c:/git/mbiu/backend/mbiu/evaluation/verify.py) | Verification rules engine implementing all 8 non-negotiable checks, proposal parsing with aliases, safe fallback card generator, deterministic label assignment, structured repair feedback generator, single-attempt repair orchestration, and thread-safe failure counters |
| [`backend/tests/test_verify.py`](file:///c:/git/mbiu/backend/tests/test_verify.py) | Comprehensive test suite containing 65 tests covering all 8 rules with passing and failing fixtures, hallucinated quotes/IDs/numbers, forbidden advice words, ungrounded jargon, phone length limits, single-repair retry, deterministic fallback to cannot_compare, counters, and Zero Contract Storage invariants |

## Summary
The implementation for ticket **MB-17** delivers the core safety guardrail of the Mbiu platform in [`backend/mbiu/evaluation/verify.py`](file:///c:/git/mbiu/backend/mbiu/evaluation/verify.py). Operating under the fundamental invariant that model output is a proposal rather than a result, it enforces all eight non-negotiable verification rules before any comparison or card can reach an artist. Verbatim quote validation strictly checks that both the clause quote and evidence excerpts are exact substrings of the sent text. Grounding checks prevent hallucinated IDs, ungrounded numbers/percentages/durations, and untyped norm words without frequency placeholders. Evaluative conclusions and advice are strictly forbidden, and modal language ("may", "could") is mandated for practical consequences. Pure-Python deterministic syllable analysis enforces readability ceilings, while industry jargon requires plain-language card explanations. Repair orchestration permits exactly one repair attempt with structured feedback naming failed rules, deterministically falling back to `cannot_compare` (⚪ Couldn't compare) with a safe card upon second failure. All verification gates (`just test`, `just lint`, `just typecheck`) pass cleanly with 150 total tests.

## ✅ What's Good
| Aspect | Notes |
|---|---|
| **Zero Contract Storage Invariant** | Operates strictly in memory on dataclasses and strings. No contract text, extracted quotes, or proposal data are written to disk, databases, temporary files, logs, or external traces. Confirmed by `test_zero_contract_storage_during_verification`. |
| **Model Output as Proposal** | Quotes are verified by code as exact substrings (with whitespace normalization for varying line breaks) before reaching the musician. Arithmetic and Kenyan Shillings illustrations are computed by code and explicitly exempt from number grounding. |
| **The Four Labels & Zero Green Label** | Strictly adheres to the four approved labels: `typical` (🔵 Typical), `unusual` (🟡 Unusual), `worth_asking_about` (🟠 Worth asking about), and `cannot_compare` (⚪ Couldn't compare). No green label is used anywhere. "Typical" never implies safe. |
| **Robust Repair & Fallback Workflow** | `repair_and_verify` allows exactly one repair attempt with structured feedback naming failed rules. If verification fails a second time (or no repair callback is provided), it falls back deterministically to `cannot_compare` with a safe, neutral card (`Requires Advisor Review`). It NEVER falls back to `matches_standard` or `typical`. |
| **Grounded Numbers & ID Auditing** | Verifies every figure, percentage, and duration against sent clause text, linked clauses, and cited reference chunks. Rejects invented evidence IDs, linked clause IDs, and untyped norm phrases ("industry standard", "customary") unless using code frequency placeholders (`{{freq:PXX}}`). |
| **No Legal Conclusions & Modal Tone** | Rejects 30+ forbidden legal validity and advice phrases ("illegal", "unenforceable", "safe", "guaranteed", "you should sign", "don't sign"). Mandates modal phrasing ("may" or "could") in `why_it_matters` and blocks imperative commands ("you must", "demand", "refuse"). |
| **Plain Language & Phone Limits** | Computes Flesch-Kincaid Grade Level deterministically without external C libraries. Enforces phone-friendly character limits (`title` <= 45, `plain_language` <= 200, `why_it_matters` <= 280, `comparison_note` <= 280, each question <= 120). |
| **Observability Counters** | Thread-safe counters (`record_rule_failure`, `get_rule_failure_counts`, `reset_rule_failure_counters`) cleanly track per-rule failures for downstream OpenTelemetry metric reporting. |
| **Test Quality & Synthetic Fixtures** | 65 focused tests covering positive and negative cases for every rule, edge cases, repair success/failure, and project invariants using 100% synthetic contract scenarios. |

## ⚠️ Issues to Fix
1. **Remove ticket metadata from inline comment in source code**
   - **Priority:** Low
   - **File:** [`backend/mbiu/evaluation/verify.py#L334`](file:///c:/git/mbiu/backend/mbiu/evaluation/verify.py#L334)
   - **Reference:** Section *Steve's Active Execution Scope* in `docs/implementation_specific/instructions/sprint.md`: *"NEVER include ticket IDs (e.g., MB-02), branch names, or issue references inside source code. Keep ticket references strictly in documentation and log files."*
   - **Explanation:** Line 334 contains `# Observability: Thread-safe failure counters per rule for MB-29`.
   - **Action Required:** Change comment to `# Observability: Thread-safe failure counters per rule for metrics reporting` in subsequent cleanup or commit.
   - [x] Fixed

## Code Quality Scores
| Metric | Score | Notes |
|---|---|---|
| Readability & Structure | ⭐⭐⭐⭐⭐ | Exemplary modular breakdown of all 8 verification rules, clean dataclasses, and clear orchestration |
| Test Coverage & Quality | ⭐⭐⭐⭐⭐ | 65 tests in `test_verify.py` with both passing and failing fixtures for each rule, repair loops, and fallback logic |
| Privacy & Invariants Compliance | ⭐⭐⭐⭐⭐ | Strictly memory-only, zero disk/temp storage, 4 labels enforced, store=False compliant, synthetic fixtures |
| Architectural Alignment | ⭐⭐⭐⭐⭐ | Exact adherence to architecture specifications, model proposal checks, and fallback invariants |
| Error Handling & Resilience | ⭐⭐⭐⭐⭐ | Detailed `RuleViolation` diagnostics, structured repair feedback prompts, and safe fallback cards |

## Acceptance Criteria Verification
| Acceptance Criterion | Implemented? | Notes |
|---|---|---|
| Rule 1: The model read what it cites (verbatim quotes) | Yes | `verify_verbatim_quotes` verifies `key_quote` in clause and each `evidence.quote` in reference chunk with whitespace normalization |
| Rule 2: Only real IDs (grounded IDs and placeholders) | Yes | `verify_grounded_ids` audits clause ID, linked clause IDs, evidence chunk IDs, pattern IDs; blocks untyped norm words without placeholder |
| Rule 3: Every number is grounded | Yes | `verify_grounded_numbers` audits numbers, percentages, durations against sent texts; exempts code shillings illustrations |
| Rule 4: No legal conclusions & objective tone | Yes | `verify_no_legal_conclusions` blocks advice and legal validity words; requires modal tone ("may", "could") in `why_it_matters` |
| Rule 5: Plain language & jargon explanations | Yes | `verify_plain_language` verifies Flesch-Kincaid Grade Level <= 9.0; ensures music/legal jargon is explained on the card |
| Rule 6: Fits a phone (character limits) | Yes | `verify_phone_friendly_length` enforces limits on title (45), plain_language (200), why_it_matters (280), comparison (280), questions (120) |
| Rule 7: A usable question | Yes | `verify_usable_questions` checks "?" ending, >= 15 chars, max 3 questions, and rejects vague boilerplate |
| Rule 8: Money is comparable | Yes | `verify_comparable_money` requires gross or net on both sides; incompatible bases trigger fallback to `cannot_compare` |
| One repair attempt with failed rule named; second failure becomes cannot_compare | Yes | `repair_and_verify` coordinates feedback, single repair call, and deterministic fallback to `cannot_compare` with safe card |
| Count failures per rule (for observability) | Yes | Thread-safe `record_rule_failure`, `get_rule_failure_counts`, `reset_rule_failure_counters` implemented |
| Passing and failing tests for every rule | Yes | Tested extensively in `test_verify.py` with passing, failing, hallucinated, and edge-case fixtures |
| Verification gates pass (`just test`, `just lint`, `just typecheck`) | Yes | 150 passed in 37.54s; ruff check & format pass; mypy strict & tsc pass cleanly |

## Verdict
**✅ Approved.** The implementation of the verification rules engine, repair loop, and fallback card logic strictly fulfills all architectural and safety specifications. The implementer may proceed with the local ticket commit.
