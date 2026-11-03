"""Tests for evaluation summary generator and top asks ranking (MB-18).

Invariants enforced:
- Zero Contract Storage: All summary aggregation operates in memory.
- Four Labels Only: Summary counts map strictly to typical, unusual,
  worth_asking_about, cannot_compare.
- Top Asks Ranking: Highest priority given to practical impact on money and ownership.
- Synthetic Contracts Only: All test fixtures use synthetic contract scenarios.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from mbiu.evaluation.budgets import AFFECTS_MONEY, AFFECTS_OTHER, AFFECTS_OWNERSHIP
from mbiu.evaluation.comparison import (
    OUTCOME_BETTER_FOR_YOU,
    OUTCOME_CANNOT_COMPARE,
    OUTCOME_MATCHES_STANDARD,
    OUTCOME_MISSING_FROM_CONTRACT,
    OUTCOME_NOT_IN_STANDARD,
    OUTCOME_WORSE_FOR_YOU,
    STATUS_EVALUATED,
    STATUS_NOT_CHECKED,
    ClauseEvaluationResult,
)
from mbiu.evaluation.summary import (
    DEFAULT_MODEL_VERSION,
    DEFAULT_SCHEMA_VERSION,
    EvaluationSummary,
    EvaluationVersions,
    generate_evaluation_summary,
    rank_top_asks,
)
from mbiu.evaluation.verify import (
    LABEL_CANNOT_COMPARE,
    LABEL_TYPICAL,
    LABEL_UNUSUAL,
    LABEL_WORTH_ASKING_ABOUT,
)


def _make_dummy_card(
    clause_id: str,
    outcome: str,
    label: str,
    affects: str = AFFECTS_MONEY,
    headline: str = "Test Headline",
    questions: list[str] | None = None,
    status: str = STATUS_EVALUATED,
    pages: list[int] | None = None,
) -> ClauseEvaluationResult:
    """Helper to construct synthetic ClauseEvaluationResult."""
    return ClauseEvaluationResult(
        clause_id=clause_id,
        pages=pages or [1],
        original_text=f"Synthetic text for {clause_id}",
        status=status,
        comparison=outcome,
        headline=headline,
        what_it_says=f"What it says for {clause_id}",
        what_it_means=f"What it means for {clause_id}",
        comparison_note=f"Comparison note for {clause_id}",
        label=label,
        affects=affects,
        ask_them=questions or [],
    )


def test_generate_evaluation_summary_comprehensive() -> None:
    """Verify complete summary generation with top asks, good news, and label counts."""
    # 1. Matches standard (good news, typical)
    c1 = _make_dummy_card(
        clause_id="4.1",
        outcome=OUTCOME_MATCHES_STANDARD,
        label=LABEL_TYPICAL,
        affects=AFFECTS_MONEY,
        headline="Royalty Accounting",
        questions=["Could we clarify deductions?"],
    )
    # 2. Better for you (good news, typical)
    c2 = _make_dummy_card(
        clause_id="4.2",
        outcome=OUTCOME_BETTER_FOR_YOU,
        label=LABEL_TYPICAL,
        affects=AFFECTS_MONEY,
        headline="High Gross Rate",
        questions=["Can we confirm mechanical rates?"],
    )
    # 3. Worse for you on money (top ask candidate, worth_asking_about)
    c3 = _make_dummy_card(
        clause_id="7.1",
        outcome=OUTCOME_WORSE_FOR_YOU,
        label=LABEL_WORTH_ASKING_ABOUT,
        affects=AFFECTS_MONEY,
        headline="Low Net Royalty",
        questions=["Could we increase the royalty rate to 16% of Gross?"],
    )
    # 4. Worse for you on ownership (top ask candidate, worth_asking_about)
    c4 = _make_dummy_card(
        clause_id="8.1",
        outcome=OUTCOME_WORSE_FOR_YOU,
        label=LABEL_WORTH_ASKING_ABOUT,
        affects=AFFECTS_OWNERSHIP,
        headline="Perpetual Masters Assignment",
        questions=["Can master ownership revert after 5 years?"],
    )
    # 5. Missing from contract (reverse check, top ask candidate, worth_asking_about)
    c5 = _make_dummy_card(
        clause_id="missing_audit_rights",
        outcome=OUTCOME_MISSING_FROM_CONTRACT,
        label=LABEL_WORTH_ASKING_ABOUT,
        affects=AFFECTS_MONEY,
        headline="No audit rights found",
        questions=["Could we add an annual audit right to inspect books?"],
    )
    # 6. Boilerplate question (lower priority, not in standard)
    c6 = _make_dummy_card(
        clause_id="15.1",
        outcome=OUTCOME_NOT_IN_STANDARD,
        label=LABEL_UNUSUAL,
        affects=AFFECTS_OTHER,
        headline="Notices",
        questions=["Can notices be sent via email?"],
    )
    # 7. Unchecked clause due to budget exhaustion
    c7 = _make_dummy_card(
        clause_id="16.1",
        outcome=OUTCOME_CANNOT_COMPARE,
        label=LABEL_CANNOT_COMPARE,
        status=STATUS_NOT_CHECKED,
        headline="Unchecked Clause",
    )

    results = [c1, c2, c3, c4, c5, c6, c7]
    contract_issues = [
        {
            "issue": "Clause 4.1 conflicts with Clause 8.1",
            "pages": [2, 5],
        }
    ]

    summary = generate_evaluation_summary(
        clause_results=results,
        contract_issues=contract_issues,
        skipped_pages=[3],
    )

    # 1. Top asks: max 3, prioritized by money & ownership impact
    assert len(summary.top_asks) == 3
    # Low Net Royalty (money worse), Perpetual Masters (ownership worse),
    # and Missing Audit (missing protection)
    assert "Could we increase the royalty rate to 16% of Gross?" in summary.top_asks
    assert "Can master ownership revert after 5 years?" in summary.top_asks
    assert "Could we add an annual audit right to inspect books?" in summary.top_asks
    # Boilerplate notice question should NOT be in top 3
    assert "Can notices be sent via email?" not in summary.top_asks

    # 2. Good news: c1 (matches standard) and c2 (better for you)
    assert len(summary.good_news) == 2
    assert summary.matches_count == 1
    assert any(g["clause_id"] == "4.1" for g in summary.good_news)
    assert any(g["clause_id"] == "4.2" for g in summary.good_news)

    # 3. Missing protections
    assert len(summary.missing_protections) == 1
    assert summary.missing_protections[0]["clause_id"] == "missing_audit_rights"

    # 4. Clauses not checked
    assert summary.clauses_not_checked == 1

    # 5. Skipped pages
    assert summary.skipped_pages == [3]

    # 6. Contract issues
    assert len(summary.contract_issues) == 1

    # 7. Label counts (strictly the 4 non-negotiable labels)
    assert summary.label_counts[LABEL_TYPICAL] == 2  # c1, c2
    assert summary.label_counts[LABEL_WORTH_ASKING_ABOUT] == 3  # c3, c4, c5
    assert summary.label_counts[LABEL_CANNOT_COMPARE] == 1  # c7
    assert summary.label_counts[LABEL_UNUSUAL] == 1  # c6

    # 8. Provenance versions
    assert summary.versions.schema_version == DEFAULT_SCHEMA_VERSION
    assert summary.versions.model_version == DEFAULT_MODEL_VERSION


def test_rank_top_asks_deduplication_and_limit() -> None:
    """Verify rank_top_asks deduplicates questions and respects max_asks ceiling."""
    c1 = _make_dummy_card(
        clause_id="1",
        outcome=OUTCOME_WORSE_FOR_YOU,
        label=LABEL_WORTH_ASKING_ABOUT,
        affects=AFFECTS_MONEY,
        questions=[
            "Can we change the royalty rate to 18%?",
            "Can we change the royalty rate to 18%?",
        ],
    )
    c2 = _make_dummy_card(
        clause_id="2",
        outcome=OUTCOME_WORSE_FOR_YOU,
        label=LABEL_WORTH_ASKING_ABOUT,
        affects=AFFECTS_OWNERSHIP,
        questions=[
            "can we change the royalty rate to 18%?",
            "Can the rights revert in 3 years?",
        ],
    )

    top_asks = rank_top_asks([c1, c2], max_asks=3)
    assert len(top_asks) == 2
    assert "Can we change the royalty rate to 18%?" in top_asks
    assert "Can the rights revert in 3 years?" in top_asks


def test_summary_with_empty_results() -> None:
    """Verify summary handles empty contract evaluations gracefully."""
    summary = generate_evaluation_summary([])
    assert summary.top_asks == []
    assert summary.matches_count == 0
    assert summary.clauses_not_checked == 0
    assert summary.good_news == []
    assert summary.missing_protections == []
    assert summary.ask_list == []
    assert summary.label_counts[LABEL_TYPICAL] == 0


def test_summary_architectural_aliases() -> None:
    """Verify backwards-compatible property aliases match architecture specs."""
    summary = EvaluationSummary(
        top_asks=["Question 1?"],
        contract_issues=[{"issue": "conflict"}],
        missing_protections=[{"missing": "audit"}],
        good_news=[],
        matches_count=0,
        skipped_pages=[],
        ask_list=["Question 1?", "Question 2?"],
        clauses_not_checked=0,
        label_counts={},
        versions=EvaluationVersions(),
    )

    assert summary.top_questions == summary.top_asks
    assert summary.contract_wide_issues == summary.contract_issues
    assert summary.not_found_items == summary.missing_protections
    assert summary.all_questions == summary.ask_list


def test_zero_contract_storage_summary() -> None:
    """Verify zero contract storage during summary generation."""
    temp_dir = Path(tempfile.gettempdir())
    files_before = set(temp_dir.iterdir())

    c = _make_dummy_card("1", OUTCOME_MATCHES_STANDARD, LABEL_TYPICAL)
    generate_evaluation_summary([c])

    files_after = set(temp_dir.iterdir())
    new_files = [f for f in (files_after - files_before) if "mbiu" in f.name.lower()]
    assert len(new_files) == 0, "Leaked files during summary generation"
