"""Comprehensive test suite for evaluation verification rules and repair workflow.

Adheres strictly to project invariants:
- Zero Contract Storage: All verification operates in memory. No contracts or
  quotes are written to disk, temp files, or databases.
- Synthetic Contracts Only: All test fixtures use synthetic contract scenarios.
- Deterministic Fallback: Unverified proposals fall back to 'cannot_compare'
  (⚪ Couldn't compare), NEVER 'matches_standard'.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from mbiu.evaluation.verify import (
    LABEL_CANNOT_COMPARE,
    LABEL_TYPICAL,
    LABEL_UNUSUAL,
    LABEL_WORTH_ASKING_ABOUT,
    RULE_GROUNDED_IDS,
    RULE_NO_LEGAL_CONCLUSIONS,
    RULE_VERBATIM_QUOTES,
    VALID_LABELS,
    ClauseProposal,
    EvaluationContext,
    EvidenceCitation,
    MoneyComparison,
    VerificationFeedback,
    calculate_flesch_kincaid_grade,
    count_syllables_in_word,
    get_rule_failure_counts,
    normalize_whitespace,
    parse_proposal,
    repair_and_verify,
    reset_rule_failure_counters,
    verify_comparable_money,
    verify_grounded_ids,
    verify_grounded_numbers,
    verify_no_legal_conclusions,
    verify_phone_friendly_length,
    verify_plain_language,
    verify_proposal,
    verify_usable_questions,
    verify_verbatim_quotes,
)


@pytest.fixture(autouse=True)
def clean_counters() -> None:
    """Reset rule failure counters before each test."""
    reset_rule_failure_counters()


@pytest.fixture
def sample_context() -> EvaluationContext:
    """Create a realistic synthetic evaluation context."""
    return EvaluationContext(
        clause_id="7.1",
        clause_text=(
            "7.1 Royalties. The Company shall pay the Artist a royalty of 15% of Net Receipts "
            "derived from commercial exploitation of the Masters, payable semi-annually within "
            "90 days following each calendar half-year."
        ),
        linked_clauses={
            "7.2": (
                "7.2 Deductions. Net Receipts shall mean Gross Receipts less direct manufacturing "
                "costs."
            ),
            "12.1": "12.1 Audit Rights. The Artist may audit accounts once every 12 months.",
        },
        reference_chunks={
            "ref-rec-01": (
                "Standard Recording Agreement Clause 4: The Producer shall remit to the Artist "
                "a royalty rate of 16% of Net Receipts semi-annually."
            ),
            "ref-rec-02": (
                "Standard Template Royalty Terms: Royalties shall be accounted within 60 days "
                "of each calendar half-year on a net receipts basis."
            ),
        },
        known_patterns={"P01_ROYALTY_NET", "P02_AUDIT_ANNUAL"},
    )


@pytest.fixture
def valid_proposal() -> ClauseProposal:
    """Create a fully compliant candidate proposal."""
    return ClauseProposal(
        clause_id="7.1",
        title="Streaming & Sales Royalties",
        key_quote="The Company shall pay the Artist a royalty of 15% of Net Receipts",
        plain_language=(
            "You receive 15% of net receipts (meaning money left after deductions) "
            "from your music sales."
        ),
        why_it_matters=(
            "This rate may affect your long-term earnings and could be improved "
            "relative to standard rates."
        ),
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
                quote=(
                    "The Producer shall remit to the Artist a royalty rate of 16% of Net Receipts"
                ),
            )
        ],
        linked_clauses=["7.2"],
        money_comparison=MoneyComparison(
            contract_basis="net",
            reference_basis="net",
            contract_rate="15%",
            reference_rate="16%",
        ),
        jargon_definitions={"net receipts": "Revenue remaining after permitted label deductions."},
    )


# ==============================================================================
# RULE 1: Verbatim Quotes Tests
# ==============================================================================
class TestRule1VerbatimQuotes:
    """Tests for Rule 1 (Verbatim quotes)."""

    def test_verbatim_quotes_valid(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Exact substring quotes pass verification."""
        res = verify_verbatim_quotes(valid_proposal, sample_context)
        assert res.passed
        assert len(res.violations) == 0

    def test_verbatim_quotes_whitespace_normalization(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Whitespace normalization tolerates differences in line breaks and spaces."""
        valid_proposal.key_quote = "The Company  shall pay the Artist\n a royalty of 15%"
        res = verify_verbatim_quotes(valid_proposal, sample_context)
        assert res.passed

    def test_verbatim_quotes_hallucinated_clause_quote(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Modified or hallucinated clause quote fails."""
        valid_proposal.key_quote = "The Company will pay the Singer an advance of 50%"
        res = verify_verbatim_quotes(valid_proposal, sample_context)
        assert not res.passed
        assert any(v.field == "key_quote" for v in res.violations)
        assert get_rule_failure_counts()[RULE_VERBATIM_QUOTES] >= 1

    def test_verbatim_quotes_hallucinated_evidence_quote(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Modified evidence quote fails."""
        valid_proposal.evidence = [
            EvidenceCitation(
                chunk_id="ref-rec-01",
                quote="The Producer will give 80% of all gross money to the Singer",
            )
        ]
        res = verify_verbatim_quotes(valid_proposal, sample_context)
        assert not res.passed
        assert any("evidence[0].quote" in (v.field or "") for v in res.violations)

    def test_verbatim_quotes_missing_key_quote(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Missing or empty key_quote fails."""
        valid_proposal.key_quote = ""
        res = verify_verbatim_quotes(valid_proposal, sample_context)
        assert not res.passed

    def test_verbatim_quotes_empty_evidence_quote(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Empty quote in evidence citation fails."""
        valid_proposal.evidence = [EvidenceCitation(chunk_id="ref-rec-01", quote="   ")]
        res = verify_verbatim_quotes(valid_proposal, sample_context)
        assert not res.passed


# ==============================================================================
# RULE 2: Grounded IDs Tests
# ==============================================================================
class TestRule2GroundedIDs:
    """Tests for Rule 2 (Grounded IDs)."""

    def test_grounded_ids_valid(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Valid IDs belonging to request pass."""
        res = verify_grounded_ids(valid_proposal, sample_context)
        assert res.passed

    def test_grounded_ids_mismatched_clause_id(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Proposal citing a different clause ID fails."""
        valid_proposal.clause_id = "9.9"
        res = verify_grounded_ids(valid_proposal, sample_context)
        assert not res.passed
        assert any(v.field == "clause_id" for v in res.violations)

    def test_grounded_ids_invented_evidence_id(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Proposal citing an unprovided evidence chunk ID fails."""
        valid_proposal.evidence = [
            EvidenceCitation(chunk_id="ref-fake-999", quote="Some template quote")
        ]
        res = verify_grounded_ids(valid_proposal, sample_context)
        assert not res.passed
        assert any("ref-fake-999" in v.message for v in res.violations)

    def test_grounded_ids_invented_linked_clause_id(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Proposal citing an unprovided linked clause ID fails."""
        valid_proposal.linked_clauses = ["99.1"]
        res = verify_grounded_ids(valid_proposal, sample_context)
        assert not res.passed
        assert any("99.1" in v.message for v in res.violations)

    def test_grounded_ids_untyped_norm_words_rejected(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Direct untyped norm words ('industry standard') rejected without placeholder."""
        valid_proposal.comparison_note = "This royalty rate is customary industry standard."
        res = verify_grounded_ids(valid_proposal, sample_context)
        assert not res.passed
        assert any("untyped norm word" in v.message for v in res.violations)

    def test_grounded_ids_placeholder_allowed(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Norm word with frequency placeholder passes."""
        valid_proposal.comparison_note = "Matches standard template {{freq:P01_ROYALTY_NET}}."
        res = verify_grounded_ids(valid_proposal, sample_context)
        assert res.passed


# ==============================================================================
# RULE 3: Grounded Numbers Tests
# ==============================================================================
class TestRule3GroundedNumbers:
    """Tests for Rule 3 (Grounded numbers & figures)."""

    def test_grounded_numbers_valid(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Numbers (15%, 16%, 90 days) present in text pass."""
        res = verify_grounded_numbers(valid_proposal, sample_context)
        assert res.passed

    def test_grounded_numbers_invented_percentage(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Hallucinated percentage (e.g. 50%) fails."""
        valid_proposal.plain_language = "The label pays 50% royalties."
        res = verify_grounded_numbers(valid_proposal, sample_context)
        assert not res.passed
        assert any("50%" in v.message for v in res.violations)

    def test_grounded_numbers_invented_duration(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Hallucinated duration (e.g. 5 years) fails."""
        valid_proposal.why_it_matters = "This lock-in may last for 5 years."
        res = verify_grounded_numbers(valid_proposal, sample_context)
        assert not res.passed
        assert any("5 years" in v.message for v in res.violations)

    def test_grounded_numbers_invented_currency_figure(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Hallucinated raw figure (e.g. 500000) fails."""
        valid_proposal.plain_language = "You receive an advance of 500,000 on signing."
        res = verify_grounded_numbers(valid_proposal, sample_context)
        assert not res.passed
        assert any("500,000" in v.message or "500000" in v.message for v in res.violations)

    def test_grounded_numbers_illustrative_examples_exempt(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Code-generated shillings illustrative examples are explicitly exempt."""
        valid_proposal.illustrative_examples = [
            "For example, KES 100,000 gross revenue with 15% rate yields KES 15,000."
        ]
        res = verify_grounded_numbers(valid_proposal, sample_context)
        assert res.passed


# ==============================================================================
# RULE 4: No Legal Conclusions Tests
# ==============================================================================
class TestRule4NoLegalConclusions:
    """Tests for Rule 4 (No legal conclusions & Objective tone)."""

    def test_no_legal_conclusions_valid(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Neutral tone with 'may' and 'could' passes."""
        res = verify_no_legal_conclusions(valid_proposal, sample_context)
        assert res.passed

    @pytest.mark.parametrize(
        "forbidden_word",
        [
            "illegal",
            "unenforceable",
            "safe",
            "guaranteed",
            "you should sign",
            "don't sign",
            "unfair",
            "void",
            "valid in court",
            "demand that",
            "refuse this",
        ],
    )
    def test_no_legal_conclusions_forbidden_words(
        self,
        forbidden_word: str,
        valid_proposal: ClauseProposal,
        sample_context: EvaluationContext,
    ) -> None:
        """Forbidden advice or legal conclusion words trigger violation."""
        valid_proposal.why_it_matters = (
            f"This term may be {forbidden_word} and could hurt your career."
        )
        res = verify_no_legal_conclusions(valid_proposal, sample_context)
        assert not res.passed
        assert any(forbidden_word in v.message.lower() for v in res.violations)

    def test_no_legal_conclusions_missing_modal_tone(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """why_it_matters lacking modal language ('may' or 'could') fails."""
        valid_proposal.why_it_matters = (
            "This will definitely reduce your royalties and creates a lock-in."
        )
        res = verify_no_legal_conclusions(valid_proposal, sample_context)
        assert not res.passed
        assert any("modal language" in v.message for v in res.violations)


# ==============================================================================
# RULE 5: Plain Language & Jargon Tests
# ==============================================================================
class TestRule5PlainLanguageAndJargon:
    """Tests for Rule 5 (Plain language readability & Jargon definition)."""

    def test_plain_language_readable_text_passes(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Simple plain language passes readability threshold."""
        res = verify_plain_language(valid_proposal, sample_context, max_grade_level=9.0)
        assert res.passed

    def test_plain_language_high_grade_fails(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Excessively complex multisyllabic legalese fails readability grade check."""
        valid_proposal.plain_language = (
            "Notwithstanding aforementioned indemnification stipulations, the counterparty "
            "unilaterally appropriates cross-collateralized sub-licensing considerations."
        )
        valid_proposal.why_it_matters = (
            "Jurisprudential extraterritoriality may disincentivize remuneration reciprocity."
        )
        res = verify_plain_language(valid_proposal, sample_context, max_grade_level=8.0)
        assert not res.passed
        assert any("grade level" in v.message for v in res.violations)

    def test_jargon_explained_in_definitions_passes(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Jargon explained via jargon_definitions passes."""
        valid_proposal.plain_language = "Royalties are recoupable against future earnings."
        valid_proposal.jargon_definitions = {
            "recoupable": "The label deducts past advances from royalties before paying you."
        }
        res = verify_plain_language(valid_proposal, sample_context)
        assert res.passed

    def test_jargon_explained_inline_passes(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Jargon explained inline in text passes."""
        valid_proposal.plain_language = (
            "Rights are assigned in perpetuity (meaning forever) to the label."
        )
        valid_proposal.jargon_definitions = {}
        res = verify_plain_language(valid_proposal, sample_context)
        assert res.passed

    def test_unexplained_jargon_fails(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Unexplained industry jargon term fails."""
        valid_proposal.plain_language = "All recording advances are recoupable."
        valid_proposal.jargon_definitions = {}
        res = verify_plain_language(valid_proposal, sample_context)
        assert not res.passed
        assert any("recoupable" in v.message for v in res.violations)


# ==============================================================================
# RULE 6: Phone-Friendly Length Tests
# ==============================================================================
class TestRule6PhoneFriendlyLength:
    """Tests for Rule 6 (Phone-friendly character lengths)."""

    def test_phone_friendly_length_valid(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """All fields within limits pass."""
        res = verify_phone_friendly_length(valid_proposal, sample_context)
        assert res.passed

    def test_phone_friendly_title_too_long(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Headline exceeding 45 characters fails."""
        valid_proposal.title = "A" * 46
        res = verify_phone_friendly_length(valid_proposal, sample_context)
        assert not res.passed
        assert any(v.field == "title" for v in res.violations)

    def test_phone_friendly_plain_language_too_long(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Plain language exceeding 200 characters fails."""
        valid_proposal.plain_language = "B" * 201
        res = verify_phone_friendly_length(valid_proposal, sample_context)
        assert not res.passed
        assert any(v.field == "plain_language" for v in res.violations)

    def test_phone_friendly_why_it_matters_too_long(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Why it matters exceeding 280 characters fails."""
        valid_proposal.why_it_matters = "C" * 281
        res = verify_phone_friendly_length(valid_proposal, sample_context)
        assert not res.passed
        assert any(v.field == "why_it_matters" for v in res.violations)

    def test_phone_friendly_comparison_note_too_long(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Comparison note exceeding 280 characters fails."""
        valid_proposal.comparison_note = "D" * 281
        res = verify_phone_friendly_length(valid_proposal, sample_context)
        assert not res.passed
        assert any(v.field == "comparison_note" for v in res.violations)

    def test_phone_friendly_question_too_long(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Question exceeding 120 characters fails."""
        valid_proposal.questions = ["Could we change this clause? " + "E" * 100]
        res = verify_phone_friendly_length(valid_proposal, sample_context)
        assert not res.passed
        assert any("questions" in (v.field or "") for v in res.violations)


# ==============================================================================
# RULE 7: Usable Questions Tests
# ==============================================================================
class TestRule7UsableQuestions:
    """Tests for Rule 7 (Usable questions)."""

    def test_usable_questions_valid(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Actionable question ending in '?' passes."""
        res = verify_usable_questions(valid_proposal, sample_context)
        assert res.passed

    def test_usable_questions_missing_question_mark(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Question missing '?' fails."""
        valid_proposal.questions = ["Could we clarify the deduction schedule"]
        res = verify_usable_questions(valid_proposal, sample_context)
        assert not res.passed
        assert any("does not end with '?'" in v.message for v in res.violations)

    @pytest.mark.parametrize(
        "vague_q",
        [
            "What does this mean?",
            "Can you explain this?",
            "Is this good?",
            "Why is this here?",
            "Do you agree?",
            "Can we talk about this?",
            "Is this normal?",
        ],
    )
    def test_usable_questions_vague_questions_rejected(
        self,
        vague_q: str,
        valid_proposal: ClauseProposal,
        sample_context: EvaluationContext,
    ) -> None:
        """Vague, non-actionable boilerplate questions are rejected."""
        valid_proposal.questions = [vague_q]
        res = verify_usable_questions(valid_proposal, sample_context)
        assert not res.passed
        assert any("too vague" in v.message for v in res.violations)

    def test_usable_questions_too_brief_rejected(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Question shorter than 15 characters rejected."""
        valid_proposal.questions = ["Can we cap it?"]  # 14 chars
        res = verify_usable_questions(valid_proposal, sample_context)
        assert not res.passed
        assert any("too brief" in v.message for v in res.violations)

    def test_usable_questions_too_many(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """More than 3 questions fails."""
        valid_proposal.questions = [
            "Could we clarify deduction limits?",
            "Could we increase accounting frequency?",
            "Could we reduce the reversion term?",
            "Could we specify audit windows?",
        ]
        res = verify_usable_questions(valid_proposal, sample_context)
        assert not res.passed
        assert any("Too many questions" in v.message for v in res.violations)


# ==============================================================================
# RULE 8: Comparable Money Tests
# ==============================================================================
class TestRule8ComparableMoney:
    """Tests for Rule 8 (Comparable money)."""

    def test_comparable_money_matching_bases_passes(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Matching bases ('net' vs 'net' or 'gross' vs 'gross') pass."""
        valid_proposal.money_comparison = MoneyComparison(
            contract_basis="gross",
            reference_basis="gross",
            contract_rate="20%",
            reference_rate="20%",
        )
        res = verify_comparable_money(valid_proposal, sample_context)
        assert res.passed

    def test_comparable_money_missing_basis_fails(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Missing basis on either side fails."""
        valid_proposal.money_comparison = MoneyComparison(
            contract_basis="net",
            reference_basis=None,
        )
        res = verify_comparable_money(valid_proposal, sample_context)
        assert not res.passed
        assert any("Reference monetary basis" in v.message for v in res.violations)

    def test_comparable_money_incompatible_bases_fails(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Comparing net to gross directly fails."""
        valid_proposal.money_comparison = MoneyComparison(
            contract_basis="net",
            reference_basis="gross",
        )
        res = verify_comparable_money(valid_proposal, sample_context)
        assert not res.passed
        assert any("Incompatible monetary bases" in v.message for v in res.violations)

    def test_comparable_money_not_applicable_passes(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Non-monetary proposal passes Rule 8 trivially."""
        valid_proposal.money_comparison = None
        valid_proposal.money_inputs = None
        res = verify_comparable_money(valid_proposal, sample_context)
        assert res.passed


# ==============================================================================
# REPAIR & FALLBACK WORKFLOW TESTS
# ==============================================================================
class TestRepairAndFallbackWorkflow:
    """Tests for orchestration, feedback generation, and fallback behavior."""

    def test_verify_proposal_end_to_end_pass(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """End-to-end verification succeeds and assigns deterministic label."""
        res = verify_proposal(valid_proposal, sample_context)
        assert res.passed
        assert res.assigned_label == LABEL_TYPICAL
        assert res.verified_proposal is not None

    def test_repair_attempt_succeeds(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Single repair attempt fixes error and succeeds."""
        # Initial proposal has hallucinated quote and forbidden word
        valid_proposal.key_quote = "Hallucinated quote not in clause text"
        valid_proposal.why_it_matters = "This is illegal and you should sign nothing."

        def mock_repair_agent(
            proposal: ClauseProposal, feedback: VerificationFeedback
        ) -> ClauseProposal:
            assert RULE_VERBATIM_QUOTES in feedback.failed_rules
            assert RULE_NO_LEGAL_CONCLUSIONS in feedback.failed_rules
            # Fix both issues
            proposal.key_quote = "The Company shall pay the Artist a royalty of 15% of Net Receipts"
            proposal.why_it_matters = (
                "This rate may affect your long-term earnings and could be negotiated."
            )
            return proposal

        res = repair_and_verify(valid_proposal, sample_context, repair_fn=mock_repair_agent)
        assert res.passed
        assert res.verified_proposal is not None
        assert (
            res.verified_proposal.key_quote
            == "The Company shall pay the Artist a royalty of 15% of Net Receipts"
        )

    def test_repair_attempt_failure_falls_back_to_cannot_compare(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """If verification fails after repair attempt, fall back to 'cannot_compare'."""
        valid_proposal.key_quote = "Wrong quote"

        def broken_repair_agent(
            proposal: ClauseProposal, feedback: VerificationFeedback
        ) -> ClauseProposal:
            # Model still produces invalid quote
            proposal.key_quote = "Still completely wrong quote"
            return proposal

        res = repair_and_verify(valid_proposal, sample_context, repair_fn=broken_repair_agent)
        assert not res.passed
        assert res.assigned_label == LABEL_CANNOT_COMPARE
        assert res.verified_proposal is not None
        assert res.verified_proposal.title == "Requires Advisor Review"
        assert res.verified_proposal.implication == "unclear"

    def test_no_repair_fn_immediate_fallback_to_cannot_compare(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Without a repair function, immediate fallback to cannot_compare."""
        valid_proposal.key_quote = "Wrong quote"
        res = repair_and_verify(valid_proposal, sample_context, repair_fn=None)
        assert not res.passed
        assert res.assigned_label == LABEL_CANNOT_COMPARE
        assert res.verified_proposal is not None

    def test_rule_failure_counters_and_reset(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Failure counters accurately track rule failures across invocations."""
        reset_rule_failure_counters()
        counts_init = get_rule_failure_counts()
        assert all(c == 0 for c in counts_init.values())

        # Cause verbatim quote failure and ungrounded id failure
        valid_proposal.key_quote = "Invalid"
        valid_proposal.clause_id = "Wrong"
        verify_proposal(valid_proposal, sample_context)

        counts = get_rule_failure_counts()
        assert counts[RULE_VERBATIM_QUOTES] >= 1
        assert counts[RULE_GROUNDED_IDS] >= 1

        reset_rule_failure_counters()
        assert get_rule_failure_counts()[RULE_VERBATIM_QUOTES] == 0


# ==============================================================================
# PROJECT INVARIANTS & SECURITY TESTS
# ==============================================================================
class TestProjectInvariantsAndSecurity:
    """Tests verifying non-negotiable architectural and privacy invariants."""

    def test_zero_contract_storage_during_verification(
        self, valid_proposal: ClauseProposal, sample_context: EvaluationContext
    ) -> None:
        """Zero contract storage: no files are written to temp directory during verification."""
        temp_dir = Path(tempfile.gettempdir())
        files_before = set(temp_dir.iterdir())

        # Run verification and repair cycle
        verify_proposal(valid_proposal, sample_context)

        files_after = set(temp_dir.iterdir())
        new_files = files_after - files_before
        # Invariant: Ensure no temporary file contains contract or proposal text
        contract_markers = ("Royalties", "15% of Net Receipts", "Streaming & Sales")
        leaked_files = [
            f
            for f in new_files
            if f.is_file()
            and any(marker in f.read_text(errors="ignore") for marker in contract_markers)
        ]
        assert len(leaked_files) == 0, (
            f"Leaked temporary contract files during verification: {leaked_files}"
        )

    def test_valid_labels_enforced(self) -> None:
        """Strictly 4 labels allowed; NO green label is ever accepted or assigned."""
        assert VALID_LABELS == {
            LABEL_TYPICAL,
            LABEL_UNUSUAL,
            LABEL_WORTH_ASKING_ABOUT,
            LABEL_CANNOT_COMPARE,
        }
        assert "safe" not in VALID_LABELS
        assert "green" not in VALID_LABELS
        assert "matches_standard" not in VALID_LABELS

    def test_parse_proposal_aliases(self) -> None:
        """parse_proposal accepts field aliases ('headline', 'what_it_says', 'ask_them')."""
        raw_dict: dict[str, Any] = {
            "clause_id": "1.1",
            "headline": "Advance Payment",
            "key_quote": "Advance shall be payable upon execution",
            "what_it_says": "The label pays an advance on signing.",
            "what_it_means": "This may provide immediate funds.",
            "comparison_note": "Standard template comparison.",
            "ask_them": "Could we clarify the payment deadline?",
        }
        parsed = parse_proposal(raw_dict)
        assert parsed.clause_id == "1.1"
        assert parsed.title == "Advance Payment"
        assert parsed.plain_language == "The label pays an advance on signing."
        assert parsed.why_it_matters == "This may provide immediate funds."
        assert parsed.questions == ["Could we clarify the payment deadline?"]

    def test_syllable_and_flesch_kincaid_helpers(self) -> None:
        """Text syllable and readability metrics behave deterministically."""
        assert count_syllables_in_word("contract") == 2
        assert count_syllables_in_word("royalty") == 3
        assert count_syllables_in_word("a") == 1
        assert count_syllables_in_word("") == 0

        grade = calculate_flesch_kincaid_grade("The label pays royalties twice a year.")
        assert 0.0 <= grade <= 8.0

        assert normalize_whitespace("  hello   world \n \t test  ") == "hello world test"
