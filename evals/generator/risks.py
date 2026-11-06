"""Definitions of the five risks planted into synthetic contracts.

Each risk says exactly which clause it touches, what the evaluator should say,
and the marker phrase that proves the risk is present in the generated PDF.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RiskKind(StrEnum):
    """The five risk families the golden set must catch."""

    PERPETUAL_RIGHTS = "perpetual_rights"
    EXCLUSIVITY_BEYOND_TERM = "exclusivity_beyond_term"
    MISSING_PAYMENT_DATES = "missing_payment_dates"
    DEDUCTIONS_BEFORE_ROYALTIES = "deductions_before_royalties"
    CROSS_CLAUSE_CONFLICT = "cross_clause_conflict"


@dataclass(frozen=True)
class RiskDefinition:
    """One planted risk and the ground truth for it."""

    risk_id: RiskKind
    kind: str
    description: str
    clause_ids: tuple[str, ...]
    expected_outcome: str | None
    expected_issue_kind: str | None
    marker: str


RISK_DEFINITIONS: tuple[RiskDefinition, ...] = (
    RiskDefinition(
        risk_id=RiskKind.PERPETUAL_RIGHTS,
        kind="clause",
        description=(
            "The grant assigns all rights to the company in perpetuity instead of a "
            "non-exclusive licence limited to the Term."
        ),
        clause_ids=("3.1",),
        expected_outcome="worse_for_you",
        expected_issue_kind=None,
        marker="in perpetuity throughout the universe",
    ),
    RiskDefinition(
        risk_id=RiskKind.EXCLUSIVITY_BEYOND_TERM,
        kind="clause",
        description=(
            "Exclusivity continues for five years after the Term ends, restricting the "
            "artist beyond the agreed term."
        ),
        clause_ids=("5.1",),
        expected_outcome="worse_for_you",
        expected_issue_kind=None,
        marker="five (5) years after the expiry or termination of the Term",
    ),
    RiskDefinition(
        risk_id=RiskKind.MISSING_PAYMENT_DATES,
        kind="clause",
        description=(
            "The payment clause sets no statement date and no payment date, so the artist "
            "cannot know when royalties are due."
        ),
        clause_ids=("4.2",),
        expected_outcome="worse_for_you",
        expected_issue_kind=None,
        marker="in the manner the Company considers appropriate",
    ),
    RiskDefinition(
        risk_id=RiskKind.DEDUCTIONS_BEFORE_ROYALTIES,
        kind="clause",
        description=(
            "Recording, marketing and other costs are deducted before the royalty is "
            "calculated, reducing the artist's share."
        ),
        clause_ids=("4.1",),
        expected_outcome="worse_for_you",
        expected_issue_kind=None,
        marker="after deducting all recording, marketing, distribution",
    ),
    RiskDefinition(
        risk_id=RiskKind.CROSS_CLAUSE_CONFLICT,
        kind="cross_clause",
        description=(
            "The renewal clause says the Term is five years notwithstanding the two-year "
            "Term in clause 2.1, so the contract contradicts itself."
        ),
        clause_ids=("2.1", "7.1"),
        expected_outcome=None,
        expected_issue_kind="term_length_conflict",
        marker="Notwithstanding clause 2.1, the Term of this Agreement is five (5) years",
    ),
)

RISK_DEFINITIONS_BY_ID: dict[RiskKind, RiskDefinition] = {
    risk.risk_id: risk for risk in RISK_DEFINITIONS
}


RISK_OVERRIDES: dict[RiskKind, dict[str, str]] = {
    RiskKind.PERPETUAL_RIGHTS: {
        "3.1": (
            "The Artist irrevocably assigns to the Company all right, title and interest in "
            "the Recordings, the Masters and all related rights in perpetuity throughout the "
            "universe, including all renewals and extensions. The Artist retains no ownership "
            "in the Recordings or the Masters."
        )
    },
    RiskKind.EXCLUSIVITY_BEYOND_TERM: {
        "5.1": (
            "The Artist shall work exclusively with the Company during the Term and for "
            "five (5) years after the expiry or termination of the Term, and shall not record "
            "for, perform for or grant any rights to any other label during that period."
        )
    },
    RiskKind.MISSING_PAYMENT_DATES: {
        "4.2": (
            "The Company shall account to the Artist for royalties from time to time in the "
            "manner the Company considers appropriate. Payment shall be made when the Company "
            "is able to do so, and no statement or payment date is fixed by this Agreement."
        )
    },
    RiskKind.DEDUCTIONS_BEFORE_ROYALTIES: {
        "4.1": (
            "The Company shall pay the Artist a royalty of twenty per cent (20%) of Gross "
            "Receipts after deducting all recording, marketing, distribution, administration "
            "and overhead costs, and after recoupment of any advances paid to the Artist."
        )
    },
    RiskKind.CROSS_CLAUSE_CONFLICT: {
        "7.1": (
            "Notwithstanding clause 2.1, the Term of this Agreement is five (5) years from "
            "the Effective Date and renews automatically for further five (5) year periods "
            "unless notice is given."
        )
    },
}
