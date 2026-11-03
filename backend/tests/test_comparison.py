"""Tests for comparison engine, batching, budgets, and reverse checks (MB-18).

Invariants enforced:
- Zero Contract Storage: All comparison, batching, and reverse checks operate in memory.
- Storage Off at AI Providers: Evaluations adhere to store=False requirements.
- Synthetic Contracts Only: All test fixtures use synthetic contract scenarios.
- Model Output is a Proposal: Quotes and impact inputs are validated by code; model never
  does arithmetic in shillings.
- Decisions From Reviewed Templates Only: If no template standard exists,
  cannot_compare is returned.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from mbiu.documents.segment import Clause
from mbiu.evaluation.budgets import (
    AFFECTS_FREEDOM_TO_WORK,
    AFFECTS_MONEY,
    AFFECTS_OTHER,
    AFFECTS_OWNERSHIP,
    AFFECTS_TIME,
    EvaluationBudgetTracker,
    classify_clause_impact,
    create_clause_batches,
    order_clauses_by_impact,
    run_evaluation_batches,
)
from mbiu.evaluation.comparison import (
    NO_STANDARD_FOR_TYPE_MESSAGE,
    OUTCOME_CANNOT_COMPARE,
    OUTCOME_MATCHES_STANDARD,
    OUTCOME_MISSING_FROM_CONTRACT,
    STATUS_CANNOT_COMPARE,
    STATUS_EVALUATED,
    check_missing_protections,
    create_no_reviewed_standard_result,
    evaluate_clause_with_verification,
    extract_fairer_wording,
    format_template_disagreement,
    validate_impact_inputs,
)
from mbiu.evaluation.verify import (
    LABEL_CANNOT_COMPARE,
    LABEL_TYPICAL,
    LABEL_WORTH_ASKING_ABOUT,
    ClauseProposal,
    EvaluationContext,
    EvidenceCitation,
    MoneyExampleInputs,
)

# ==============================================================================
# IMPACT ORDERING TESTS
# ==============================================================================


def test_classify_clause_impact_categories() -> None:
    """Verify topic classification and impact dimension mapping."""
    # Money
    res_money = classify_clause_impact("The Producer shall pay 15% of Net Receipts.")
    assert res_money.topic == "money"
    assert res_money.affects == AFFECTS_MONEY
    assert res_money.priority_score == 100

    # Ownership
    res_owner = classify_clause_impact("Company shall own all master sound recordings.")
    assert res_owner.topic == "ownership"
    assert res_owner.affects == AFFECTS_OWNERSHIP
    assert res_owner.priority_score == 90

    # Term
    res_term = classify_clause_impact("The contract period shall be 3 years from effective date.")
    assert res_term.topic == "term"
    assert res_term.affects == AFFECTS_TIME
    assert res_term.priority_score == 80

    # Exclusivity
    res_excl = classify_clause_impact("Artist grants exclusive recording services and non-compete.")
    assert res_excl.topic == "exclusivity"
    assert res_excl.affects == AFFECTS_FREEDOM_TO_WORK
    assert res_excl.priority_score == 70

    # Termination
    res_term_right = classify_clause_impact(
        "Either party may terminate upon uncured material breach."
    )
    assert res_term_right.topic == "termination"
    assert res_term_right.affects == AFFECTS_TIME
    assert res_term_right.priority_score == 60

    # Boilerplate
    res_boiler = classify_clause_impact(
        "Any notice under this agreement shall be in writing to the addresses specified."
    )
    assert res_boiler.topic == "boilerplate"
    assert res_boiler.affects == AFFECTS_OTHER
    assert res_boiler.priority_score == 10


def test_order_clauses_by_impact_prioritization() -> None:
    """Verify money and ownership clauses are ordered before boilerplate."""
    c_notice = Clause(
        clause_id="12.1",
        section="main",
        title="Notices",
        text="All notices shall be given in writing via registered post.",
        pages=[5],
        start_offset=1000,
        end_offset=1055,
    )
    c_gov = Clause(
        clause_id="12.2",
        section="main",
        title="Governing Law",
        text="This agreement is governed by the laws of Kenya.",
        pages=[5],
        start_offset=1056,
        end_offset=1100,
    )
    c_royalty = Clause(
        clause_id="4.1",
        section="main",
        title="Royalties",
        text="Artist shall receive 15% of Net Receipts semi-annually.",
        pages=[2],
        start_offset=200,
        end_offset=255,
    )
    c_masters = Clause(
        clause_id="5.1",
        section="main",
        title="Masters Ownership",
        text="All sound recordings and master rights belong to Company.",
        pages=[2],
        start_offset=256,
        end_offset=310,
    )
    c_term = Clause(
        clause_id="3.1",
        section="main",
        title="Term",
        text="The duration of this agreement shall be 2 years.",
        pages=[1],
        start_offset=100,
        end_offset=145,
    )

    unordered = [c_notice, c_gov, c_royalty, c_masters, c_term]
    ordered = order_clauses_by_impact(unordered)

    # Royalty (Money, 100) and Masters (Ownership, 90) must precede Term (80)
    # Notices and Governing Law (Boilerplate, 10) must be last
    ordered_ids = [c.clause_id for c in ordered]
    assert ordered_ids[0] == "4.1"  # Money
    assert ordered_ids[1] == "5.1"  # Ownership
    assert ordered_ids[2] == "3.1"  # Term
    assert ordered_ids[3] == "12.1"  # Boilerplate
    assert ordered_ids[4] == "12.2"  # Boilerplate


def test_order_clauses_stability() -> None:
    """Verify clauses within the same priority score maintain original document order."""
    c1 = {"id": "1", "text": "Royalty is 10% of Net Receipts."}
    c2 = {"id": "2", "text": "Accounting shall be rendered semi-annually with payments."}
    c3 = {"id": "3", "text": "Deductions from gross monies shall be capped at 10%."}

    ordered = order_clauses_by_impact([c1, c2, c3])
    assert [c["id"] for c in ordered] == ["1", "2", "3"]


# ==============================================================================
# BATCHING TESTS (4 to 8 clauses)
# ==============================================================================


def test_create_clause_batches_sizing() -> None:
    """Verify batch sizes stay between 4 and 8 clauses."""
    # 0 clauses -> []
    assert create_clause_batches([]) == []

    # 3 clauses (< 4) -> single batch of 3
    assert len(create_clause_batches([1, 2, 3])) == 1

    # 6 clauses -> single batch of 6
    batches_6 = create_clause_batches(list(range(6)))
    assert len(batches_6) == 1
    assert len(batches_6[0]) == 6

    # 8 clauses -> single batch of 8
    batches_8 = create_clause_batches(list(range(8)))
    assert len(batches_8) == 1
    assert len(batches_8[0]) == 8

    # 10 clauses -> 2 batches (e.g. 5, 5)
    batches_10 = create_clause_batches(list(range(10)))
    assert len(batches_10) == 2
    for b in batches_10:
        assert 4 <= len(b) <= 8

    # 13 clauses -> batches of [5, 4, 4] or [7, 6]
    batches_13 = create_clause_batches(list(range(13)))
    for b in batches_13:
        assert 4 <= len(b) <= 8
    assert sum(len(b) for b in batches_13) == 13

    # 25 clauses -> 4 or 5 batches, none under 4 or over 8
    batches_25 = create_clause_batches(list(range(25)))
    for b in batches_25:
        assert 4 <= len(b) <= 8
    assert sum(len(b) for b in batches_25) == 25


# ==============================================================================
# BUDGET TRACKER TESTS
# ==============================================================================


def test_budget_tracker_token_exhaustion() -> None:
    """Verify token exhaustion correctly marks remaining clauses as not_checked."""
    tracker = EvaluationBudgetTracker(clause_count=10, token_budget=10000)
    assert not tracker.is_token_exhausted
    assert tracker.can_process_batch(estimated_tokens=3000)

    # Consume 9000 tokens
    tracker.record_tokens(9000)
    assert not tracker.is_token_exhausted
    # Cannot process a 2000 token batch (9000 + 2000 > 10000)
    assert not tracker.can_process_batch(estimated_tokens=2000)

    # Consume remaining tokens
    tracker.record_tokens(1000)
    assert tracker.is_token_exhausted
    assert not tracker.can_process_batch()

    # Kind message
    reason_plural = tracker.get_not_checked_reason(remaining_clauses_count=4)
    assert (
        reason_plural
        == "Mbiu checked the most important clauses first. 4 clauses aren't checked yet."
    )

    reason_singular = tracker.get_not_checked_reason(remaining_clauses_count=1)
    assert (
        reason_singular
        == "Mbiu checked the most important clauses first. 1 clause isn't checked yet."
    )


def test_budget_tracker_time_exhaustion() -> None:
    """Verify time exhaustion when simulated clock exceeds overall deadline."""
    fake_time = 100.0

    def clock() -> float:
        return fake_time

    # 5 clauses * 3s = 15s computed, clamped to batch_timeout_s=30s
    tracker = EvaluationBudgetTracker(
        clause_count=5,
        batch_timeout_s=30.0,
        deadline_per_clause_s=3.0,
        deadline_cap_s=300.0,
        clock=clock,
    )
    assert tracker.overall_deadline_s == 30.0
    assert not tracker.is_time_exhausted
    assert tracker.can_process_batch()

    # Advance clock past 30s deadline
    fake_time = 135.0
    assert tracker.is_time_exhausted
    assert not tracker.can_process_batch()


@pytest.mark.anyio
async def test_run_evaluation_batches_token_budget_exhaustion() -> None:
    """Verify async batch runner halts on budget exhaustion and returns not_checked cards."""
    tracker = EvaluationBudgetTracker(clause_count=12, token_budget=5000)

    batches = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]

    async def mock_evaluator(batch: list[int]) -> tuple[list[str], int]:
        # Each batch uses 3000 tokens
        return ([f"result_{x}" for x in batch], 3000)

    def on_not_checked(items: list[int], reason: str) -> list[str]:
        return [f"not_checked_{x}_{reason[:10]}" for x in items]

    results = await run_evaluation_batches(
        batches=batches,
        batch_evaluator=mock_evaluator,
        tracker=tracker,
        concurrency_limit=2,
        on_not_checked=on_not_checked,
    )

    # Batch 1 processed (4 items, 3000 tokens).
    # Batch 2 and 3 skipped because 3000 + 4000 > 5000 budget!
    assert "result_1" in results
    assert "result_4" in results
    # Remaining 8 items are marked not_checked
    assert any("not_checked_5" in r for r in results)
    assert any("not_checked_12" in r for r in results)
    assert len(results) == 12


@pytest.mark.anyio
async def test_run_evaluation_batches_handles_timeout() -> None:
    """Verify batch runner handles batch timeout gracefully without crashing."""
    tracker = EvaluationBudgetTracker(clause_count=6, batch_timeout_s=0.1)

    batch = [1, 2, 3, 4]

    async def slow_evaluator(items: list[int]) -> tuple[list[str], int]:
        await asyncio.sleep(0.5)  # Exceeds 0.1s timeout
        return ([f"result_{x}" for x in items], 100)

    def on_not_checked(items: list[int], reason: str) -> list[str]:
        return [f"timeout_{x}" for x in items]

    results = await run_evaluation_batches(
        batches=[batch],
        batch_evaluator=slow_evaluator,
        tracker=tracker,
        on_not_checked=on_not_checked,
    )

    assert len(results) == 4
    assert all("timeout_" in r for r in results)


# ==============================================================================
# IMPACT INPUTS & CODE ARITHMETIC TESTS
# ==============================================================================


def test_validate_impact_inputs_exact_quotes() -> None:
    """Verify impact inputs are validated against exact clause substrings without arithmetic."""
    clause_text = (
        "The Company shall remit 18% of Net Receipts, after deducting manufacturing "
        "and shipping costs."
    )

    # Valid inputs
    valid_inputs = MoneyExampleInputs(
        rate="18%",
        basis="net",
        deductions=["manufacturing and shipping costs"],
        quote="18% of Net Receipts",
    )
    validated = validate_impact_inputs(valid_inputs, clause_text)
    assert validated is not None
    assert validated.rate == "18%"
    assert validated.basis == "net"
    assert validated.quote == "18% of Net Receipts"

    # Hallucinated quote
    invalid_quote_inputs = MoneyExampleInputs(
        rate="18%",
        basis="net",
        deductions=[],
        quote="25% of Gross Monies",  # NOT in clause
    )
    assert validate_impact_inputs(invalid_quote_inputs, clause_text) is None


def test_validate_impact_inputs_filters_ungrounded_deductions() -> None:
    """Verify deductions not present in the clause text are pruned."""
    clause_text = "The Company shall pay 12% of Net Receipts less legal costs."
    inputs = MoneyExampleInputs(
        rate=12.0,
        basis="net",
        deductions=["legal costs", "unapproved studio expenses"],  # Second is hallucinated
        quote="12% of Net Receipts",
    )
    validated = validate_impact_inputs(inputs, clause_text)
    assert validated is not None
    assert validated.deductions == ["legal costs"]


# ==============================================================================
# FAIRER WORDING TESTS
# ==============================================================================


def test_extract_fairer_wording_exact_template_unchanged() -> None:
    """Verify fairer_wording extracts verbatim reference text unchanged."""
    reference_chunks = {
        "ref-01": (
            "Standard Clause 6: Artist shall receive 20% of Gross Receipts with no "
            "recoupment deductions."
        ),
        "ref-02": (
            "Standard Audit Term: Artist may inspect books once annually upon "
            "thirty (30) days notice."
        ),
    }

    # Exact verbatim substring
    candidate = "Artist shall receive 20% of Gross Receipts with no recoupment deductions."
    result = extract_fairer_wording(candidate, reference_chunks)
    assert result == candidate

    # Altered / paraphrased candidate rejected
    paraphrased = "You should get 20% of Gross Receipts without deductions."
    assert extract_fairer_wording(paraphrased, reference_chunks) is None


# ==============================================================================
# NO REVIEWED STANDARD & TEMPLATE DISAGREEMENT TESTS
# ==============================================================================


def test_create_no_reviewed_standard_result() -> None:
    """Verify handling when contract type has no reviewed standard."""
    result = create_no_reviewed_standard_result(
        clause_id="2.1",
        original_text="The Host shall produce 12 podcast episodes per year.",
        pages=[1],
        contract_type="podcast_agreement",
        title="Podcast Production",
        plain_language="You agree to produce twelve podcast episodes each year.",
        why_it_matters="This may establish a strict delivery schedule.",
    )

    assert result.status == STATUS_CANNOT_COMPARE
    assert result.comparison == OUTCOME_CANNOT_COMPARE
    assert result.label == LABEL_CANNOT_COMPARE
    assert result.comparison_note == NO_STANDARD_FOR_TYPE_MESSAGE
    assert "produce twelve podcast episodes" in result.what_it_says
    assert "may establish a strict delivery" in result.what_it_means


def test_format_template_disagreement() -> None:
    """Verify clear evidence formatting when retrieved templates differ."""
    formatted = format_template_disagreement(
        first_standard="30 days",
        second_standard="60 days",
        contract_term="90 days",
    )
    expected = (
        "Standard templates differ here: one gives 30 days, another 60 days. "
        "Your contract gives 90 days."
    )
    assert formatted == expected


# ==============================================================================
# VERIFIED CLAUSE EVALUATION ORCHESTRATION
# ==============================================================================


def test_evaluate_clause_with_verification_success() -> None:
    """Verify full evaluation pipeline with MB-17 verification integration."""
    context = EvaluationContext(
        clause_id="7.1",
        clause_text=(
            "7.1 The Label pays 15% of Net Receipts payable within 90 days of each half-year."
        ),
        reference_chunks={
            "ref-rec-01": (
                "Standard terms: Producer shall pay a royalty rate of 16% of Net Receipts."
            )
        },
        known_patterns={"P01_ROYALTY_NET"},
    )

    proposal = ClauseProposal(
        clause_id="7.1",
        title="Streaming Royalties",
        key_quote="The Label pays 15% of Net Receipts",
        plain_language=(
            "You receive 15% of net receipts (meaning money left after deductions) "
            "from music sales."
        ),
        why_it_matters="This rate may affect your long-term earnings and could be improved.",
        comparison_note=(
            "Matches reference standard {{freq:P01_ROYALTY_NET}} for net receipt accounting."
        ),
        questions=[
            "Could we clarify which specific costs are deducted before calculating net receipts?"
        ],
        matched_pattern_id="P01_ROYALTY_NET",
        implication="none",
        affects="money",
        evidence=[
            EvidenceCitation(
                chunk_id="ref-rec-01",
                quote="Producer shall pay a royalty rate of 16% of Net Receipts",
            )
        ],
        money_inputs=MoneyExampleInputs(
            rate="15%",
            basis="net",
            deductions=[],
            quote="15% of Net Receipts",
        ),
    )

    eval_result = evaluate_clause_with_verification(
        proposal=proposal,
        context=context,
        pages=[2],
        clause_number="7.1",
        contract_type_has_standard=True,
    )

    assert eval_result.status == STATUS_EVALUATED
    assert eval_result.comparison == OUTCOME_MATCHES_STANDARD
    assert eval_result.label == LABEL_TYPICAL
    assert eval_result.headline == "Streaming Royalties"
    assert eval_result.impact_inputs is not None
    assert eval_result.impact_inputs.rate == "15%"
    assert eval_result.fairer_wording is not None


# ==============================================================================
# REVERSE CHECK (Missing Protections) TESTS
# ==============================================================================


def test_reverse_check_detects_all_missing_protections() -> None:
    """Verify reverse check detects missing protective clauses when absent."""
    # Synthetic one-sided contract with NO audit rights, NO accounting schedule,
    # and NO termination right
    clauses = [
        Clause(
            clause_id="1",
            section="main",
            title="Grant of Rights",
            text="Artist grants all rights to Label in perpetuity throughout the universe.",
            pages=[1],
            start_offset=0,
            end_offset=74,
        ),
        Clause(
            clause_id="2",
            section="main",
            title="Exclusivity",
            text="Artist agrees to perform exclusively for Label.",
            pages=[1],
            start_offset=75,
            end_offset=123,
        ),
    ]

    missing = check_missing_protections(clauses, contract_type_has_standard=True)

    # Must flag audit rights, accounting schedule, termination on breach,
    # written approvals, and rights reversion
    missing_ids = [m.clause_id for m in missing]
    assert "missing_audit_rights" in missing_ids
    assert "missing_accounting_frequency" in missing_ids
    assert "missing_termination_on_breach" in missing_ids
    assert "missing_written_approval_deductions" in missing_ids
    assert "missing_rights_reversion" in missing_ids

    # Check cautious tone: "We didn't find", label is worth_asking_about
    for m in missing:
        assert m.comparison == OUTCOME_MISSING_FROM_CONTRACT
        assert m.label == LABEL_WORTH_ASKING_ABOUT
        assert m.what_it_says.startswith("We didn't find")
        assert len(m.ask_them) >= 1
        assert m.ask_them[0].endswith("?")
        assert m.fairer_wording is not None


def test_reverse_check_ignores_present_protections() -> None:
    """Verify reverse check does NOT flag protections that are present in the contract."""
    clauses = [
        Clause(
            clause_id="12",
            section="main",
            title="Audit Rights",
            text="The Artist may audit and inspect books of account once every calendar year.",
            pages=[4],
            start_offset=500,
            end_offset=580,
        ),
        Clause(
            clause_id="13",
            section="main",
            title="Accounting Schedule",
            text="Royalty statements shall be rendered semi-annually within 60 days.",
            pages=[4],
            start_offset=581,
            end_offset=650,
        ),
    ]

    missing = check_missing_protections(clauses, contract_type_has_standard=True)
    missing_ids = [m.clause_id for m in missing]

    assert "missing_audit_rights" not in missing_ids
    assert "missing_accounting_frequency" not in missing_ids


# ==============================================================================
# ZERO CONTRACT STORAGE INVARIANT TEST
# ==============================================================================


def test_zero_contract_storage_during_comparison() -> None:
    """Verify zero contract storage: no files written during comparison or reverse check."""
    temp_dir = Path(tempfile.gettempdir())
    files_before = set(temp_dir.iterdir())

    # Execute batching, ordering, evaluation, and reverse check
    clauses = [
        Clause(
            clause_id="1",
            section="main",
            title="Royalty Terms",
            text="Artist gets 15% of Net Receipts.",
            pages=[1],
            start_offset=0,
            end_offset=32,
        ),
        Clause(
            clause_id="2",
            section="main",
            title="Notices",
            text="Notices to registered address.",
            pages=[1],
            start_offset=33,
            end_offset=63,
        ),
    ]

    ordered = order_clauses_by_impact(clauses)
    create_clause_batches(ordered)
    check_missing_protections(ordered)

    files_after = set(temp_dir.iterdir())
    new_files = [f for f in (files_after - files_before) if "mbiu" in f.name.lower()]
    assert len(new_files) == 0, f"Leaked temporary files detected: {new_files}"
