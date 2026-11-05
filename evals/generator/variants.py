"""The synthetic contracts in the golden set, built from the standard template."""

from __future__ import annotations

from dataclasses import dataclass

from evals.generator.risks import RISK_OVERRIDES, RiskKind
from evals.generator.templates import STANDARD_CLAUSES, TemplateClauseSpec


@dataclass(frozen=True)
class ContractVariant:
    """A named contract assembled from the standard template and planted risks."""

    contract_id: str
    title: str
    risk_ids: tuple[RiskKind, ...]
    overrides: dict[str, str]

    def clauses(self) -> tuple[TemplateClauseSpec, ...]:
        """Return the template clauses with this variant's risks applied."""
        return tuple(
            TemplateClauseSpec(
                clause_id=clause.clause_id,
                heading=clause.heading,
                text=self.overrides.get(clause.clause_id, clause.text),
            )
            for clause in STANDARD_CLAUSES
        )


def _variant(
    contract_id: str, title: str, risk_ids: tuple[RiskKind, ...]
) -> ContractVariant:
    overrides: dict[str, str] = {}
    for risk_id in risk_ids:
        overrides.update(RISK_OVERRIDES[risk_id])
    return ContractVariant(
        contract_id=contract_id,
        title=title,
        risk_ids=risk_ids,
        overrides=overrides,
    )


VARIANTS: tuple[ContractVariant, ...] = (
    _variant(
        "mb19-clean-control",
        "Clean control recording agreement",
        (),
    ),
    _variant(
        "mb19-perpetual-rights",
        "Recording agreement with perpetual rights",
        (RiskKind.PERPETUAL_RIGHTS,),
    ),
    _variant(
        "mb19-exclusivity-beyond-term",
        "Recording agreement with post-term exclusivity",
        (RiskKind.EXCLUSIVITY_BEYOND_TERM,),
    ),
    _variant(
        "mb19-missing-payment-dates",
        "Recording agreement with no payment dates",
        (RiskKind.MISSING_PAYMENT_DATES,),
    ),
    _variant(
        "mb19-deductions-before-royalties",
        "Recording agreement with costs deducted before royalties",
        (RiskKind.DEDUCTIONS_BEFORE_ROYALTIES,),
    ),
    _variant(
        "mb19-cross-clause-conflict",
        "Recording agreement with a conflicting term",
        (RiskKind.CROSS_CLAUSE_CONFLICT,),
    ),
    _variant(
        "mb19-combined-risks",
        "Recording agreement with all five planted risks",
        tuple(RiskKind),
    ),
)
