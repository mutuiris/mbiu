"""Evaluation summary generator for contract evaluations.

Produces the consolidated final summary object for the 'done' event:
- top_asks: Top 3 questions ranked by impact on money and ownership.
- contract_issues: Contract-wide overrides and conflicts identified in the contract map.
- missing_protections: List of essential protections missing from the contract.
- good_news: Clauses that match or improve upon reviewed standards.
- matches_count: Total count of clauses matching reference standards.
- skipped_pages: Pages without text layers that were skipped during extraction.
- ask_list: Consolidated checklist of suggested negotiation questions.
- clauses_not_checked: Count of clauses omitted when budget was exhausted.
- label_counts: Grand totals for the four non-negotiable labels.
- versions: Schema, prompt, model, and corpus version identifiers.

Zero Contract Storage Invariant:
Summary aggregation operates purely in memory on verified result objects.
No contract text or summaries are persisted to disk or databases.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from mbiu.evaluation.budgets import AFFECTS_MONEY, AFFECTS_OWNERSHIP
from mbiu.evaluation.comparison import (
    OUTCOME_BETTER_FOR_YOU,
    OUTCOME_MATCHES_STANDARD,
    OUTCOME_MISSING_FROM_CONTRACT,
    OUTCOME_WORSE_FOR_YOU,
    STATUS_NOT_CHECKED,
    ClauseEvaluationResult,
)
from mbiu.evaluation.verify import (
    LABEL_CANNOT_COMPARE,
    LABEL_TYPICAL,
    LABEL_UNUSUAL,
    LABEL_WORTH_ASKING_ABOUT,
)

DEFAULT_SCHEMA_VERSION = "1.0.0"
DEFAULT_PROMPT_VERSION = "2026.1"
DEFAULT_MODEL_VERSION = "gemini-3.8-flash"
DEFAULT_CORPUS_VERSION = "v2026.10"


@dataclass(frozen=True)
class EvaluationVersions:
    """Version metadata documenting system provenance.

    Attributes:
        schema_version: API and data structure schema revision.
        prompt_version: Evaluation prompt template revision.
        model_version: Active AI model provider revision.
        corpus_version: Active reference template corpus snapshot version.
    """

    schema_version: str = DEFAULT_SCHEMA_VERSION
    prompt_version: str = DEFAULT_PROMPT_VERSION
    model_version: str = DEFAULT_MODEL_VERSION
    corpus_version: str = DEFAULT_CORPUS_VERSION


@dataclass(frozen=True)
class GoodNewsItem:
    """Clause identified as matching or exceeding reviewed standard templates.

    Attributes:
        clause_id: Target clause identifier.
        headline: Plain language topic headline.
        pages: Pages spanned by the clause.
        note: Short reassuring explanation.
        outcome: Either 'matches_standard' or 'better_for_you'.
    """

    clause_id: str
    headline: str
    pages: list[int]
    note: str
    outcome: str


@dataclass
class EvaluationSummary:
    """Consolidated summary of contract evaluation findings.

    Attributes:
        top_asks: Top 3 questions ranked by impact on money and ownership.
        contract_issues: List of contract-wide overrides and conflicts.
        missing_protections: Protections identified by reverse check as absent.
        good_news: List of clauses matching or better than the standard.
        matches_count: Count of clauses matching standard templates.
        skipped_pages: Page numbers skipped during PDF extraction.
        ask_list: Full checklist of all suggested negotiation questions.
        clauses_not_checked: Number of clauses left unchecked due to budget limits.
        label_counts: Grand totals for the four non-negotiable labels.
        versions: Provenance version tags.
    """

    top_asks: list[str]
    contract_issues: list[dict[str, Any]] = field(default_factory=list)
    missing_protections: list[dict[str, Any]] = field(default_factory=list)
    good_news: list[dict[str, Any]] = field(default_factory=list)
    matches_count: int = 0
    skipped_pages: list[int] = field(default_factory=list)
    ask_list: list[str] = field(default_factory=list)
    clauses_not_checked: int = 0
    label_counts: dict[str, int] = field(default_factory=dict)
    versions: EvaluationVersions = field(default_factory=EvaluationVersions)

    # Architectural compatibility aliases
    @property
    def top_questions(self) -> list[str]:
        """Alias for top_asks."""
        return self.top_asks

    @property
    def contract_wide_issues(self) -> list[dict[str, Any]]:
        """Alias for contract_issues."""
        return self.contract_issues

    @property
    def not_found_items(self) -> list[dict[str, Any]]:
        """Alias for missing_protections."""
        return self.missing_protections

    @property
    def all_questions(self) -> list[str]:
        """Alias for ask_list."""
        return self.ask_list


def rank_top_asks(
    results: Sequence[ClauseEvaluationResult],
    max_asks: int = 3,
) -> list[str]:
    """Select and rank the top 3 questions by practical impact on money and ownership.

    Ranking priorities:
    1. Clauses affecting money or ownership with outcome 'worse_for_you'
       or label 'worth_asking_about' (score 100).
    2. Missing protections identified by reverse check (score 95).
    3. Other clauses affecting money or ownership (score 80).
    4. Clauses affecting term or exclusivity (score 70).
    5. Clauses affecting termination (score 60).
    6. All other suggested questions (score 40).

    Args:
        results: Evaluated clause results and missing protection cards.
        max_asks: Maximum number of questions to return (default 3).

    Returns:
        List of at most max_asks prioritized, deduplicated questions.
    """
    scored_questions: list[tuple[int, int, str]] = []
    seen_normalized: set[str] = set()

    question_idx = 0
    for card in results:
        if not card.ask_them:
            continue

        # Compute priority score
        affects = card.affects or ""
        is_money_or_ownership = affects in (AFFECTS_MONEY, AFFECTS_OWNERSHIP)

        if card.comparison == OUTCOME_MISSING_FROM_CONTRACT:
            score = 95
        elif is_money_or_ownership and (
            card.comparison == OUTCOME_WORSE_FOR_YOU or card.label == LABEL_WORTH_ASKING_ABOUT
        ):
            score = 100
        elif is_money_or_ownership:
            score = 80
        elif affects in ("term", "exclusivity", "freedom_to_work"):
            score = 70
        elif affects == "termination":
            score = 60
        else:
            score = 40

        for q in card.ask_them:
            q_clean = q.strip()
            norm = q_clean.lower()
            if norm and norm not in seen_normalized:
                seen_normalized.add(norm)
                # Sort by -score, then by question index to maintain original order within tier
                scored_questions.append((-score, question_idx, q_clean))
                question_idx += 1

    scored_questions.sort(key=lambda x: (x[0], x[1]))
    return [item[2] for item in scored_questions[:max_asks]]


def generate_evaluation_summary(
    clause_results: Sequence[ClauseEvaluationResult],
    contract_issues: Sequence[dict[str, Any]] | None = None,
    skipped_pages: Sequence[int] | None = None,
    versions: EvaluationVersions | None = None,
) -> EvaluationSummary:
    """Generate the consolidated evaluation summary object from clause results.

    Aggregates:
    - top_asks: top 3 questions ranked by impact on money and ownership.
    - contract_issues: contract-wide overrides/conflicts.
    - missing_protections: list of protections missing from the contract.
    - good_news: clauses that match or are better than the standard.
    - matches_count: count of clauses matching standard.
    - skipped_pages: list of skipped pages.
    - ask_list: consolidated checklist of suggested negotiation questions.
    - clauses_not_checked: count of clauses left unchecked.
    - label_counts: counts for typical, unusual, worth_asking_about, cannot_compare.
    - versions: schema_version, prompt_version, model_version, corpus_version.

    Args:
        clause_results: All clause results (including missing protections and not_checked).
        contract_issues: Optional contract-wide conflicts/overrides from contract map.
        skipped_pages: Optional page numbers skipped during PDF extraction.
        versions: Optional custom version identifiers.

    Returns:
        EvaluationSummary instance.
    """
    label_counts: dict[str, int] = {
        LABEL_TYPICAL: 0,
        LABEL_UNUSUAL: 0,
        LABEL_WORTH_ASKING_ABOUT: 0,
        LABEL_CANNOT_COMPARE: 0,
    }

    matches_count = 0
    clauses_not_checked = 0
    good_news: list[dict[str, Any]] = []
    missing_protections: list[dict[str, Any]] = []
    seen_questions: set[str] = set()
    ask_list: list[str] = []

    for card in clause_results:
        # Increment label counts
        if card.label in label_counts:
            label_counts[card.label] += 1
        else:
            label_counts[LABEL_CANNOT_COMPARE] += 1

        # Check unchecked
        if card.status == STATUS_NOT_CHECKED:
            clauses_not_checked += 1

        # Check matches and good news
        if card.comparison == OUTCOME_MATCHES_STANDARD:
            matches_count += 1
            good_news.append(
                {
                    "clause_id": card.clause_id,
                    "headline": card.headline,
                    "pages": list(card.pages),
                    "note": card.comparison_note or "Matches reviewed standard template terms.",
                    "outcome": OUTCOME_MATCHES_STANDARD,
                }
            )
        elif card.comparison == OUTCOME_BETTER_FOR_YOU:
            good_news.append(
                {
                    "clause_id": card.clause_id,
                    "headline": card.headline,
                    "pages": list(card.pages),
                    "note": card.comparison_note
                    or "More favourable to you than standard template terms.",
                    "outcome": OUTCOME_BETTER_FOR_YOU,
                }
            )

        # Check missing protections
        if card.comparison == OUTCOME_MISSING_FROM_CONTRACT:
            missing_protections.append(
                {
                    "clause_id": card.clause_id,
                    "headline": card.headline,
                    "what_it_says": card.what_it_says,
                    "what_it_means": card.what_it_means,
                    "comparison_note": card.comparison_note,
                    "questions": list(card.ask_them),
                    "fairer_wording": card.fairer_wording,
                }
            )

        # Collect questions for ask_list
        for q in card.ask_them:
            q_clean = q.strip()
            norm = q_clean.lower()
            if norm and norm not in seen_questions:
                seen_questions.add(norm)
                ask_list.append(q_clean)

    top_asks = rank_top_asks(clause_results, max_asks=3)

    return EvaluationSummary(
        top_asks=top_asks,
        contract_issues=list(contract_issues or []),
        missing_protections=missing_protections,
        good_news=good_news,
        matches_count=matches_count,
        skipped_pages=list(skipped_pages or []),
        ask_list=ask_list,
        clauses_not_checked=clauses_not_checked,
        label_counts=label_counts,
        versions=versions or EvaluationVersions(),
    )
