"""The reviewed recording-agreement template the synthetic contracts start from.

Every contract in the golden set is this template with zero or more known risks
planted into it. Keeping the baseline text here means the expected outcome of a
clean contract is known without a model or a human label.
"""

from __future__ import annotations

from dataclasses import dataclass

STANDARD_TEMPLATE_ID = "mb19-recording-standard-v1"
CONTRACT_TYPE = "recording"
JURISDICTION = "Kenya"


@dataclass(frozen=True)
class TemplateClauseSpec:
    """One clause in the reviewed standard template."""

    clause_id: str
    heading: str
    text: str


STANDARD_CLAUSES: tuple[TemplateClauseSpec, ...] = (
    TemplateClauseSpec(
        clause_id="1.1",
        heading="Parties",
        text=(
            "This Recording Agreement is made between the Artist and the Company on the "
            "Effective Date stated at the end of this Agreement."
        ),
    ),
    TemplateClauseSpec(
        clause_id="2.1",
        heading="Term",
        text=(
            "The Term of this Agreement begins on the Effective Date and continues for "
            "two (2) years, unless it is terminated earlier in accordance with this Agreement."
        ),
    ),
    TemplateClauseSpec(
        clause_id="3.1",
        heading="Grant of Rights",
        text=(
            "The Artist grants to the Company a non-exclusive licence to record, reproduce, "
            "distribute and exploit the Recordings during the Term in Kenya. All rights not "
            "expressly granted are reserved by the Artist."
        ),
    ),
    TemplateClauseSpec(
        clause_id="3.2",
        heading="Ownership",
        text=(
            "The Company owns the master recordings created under this Agreement. The Artist "
            "retains ownership of the musical compositions and the right to receive royalties."
        ),
    ),
    TemplateClauseSpec(
        clause_id="4.1",
        heading="Royalties",
        text=(
            "The Company shall pay the Artist a royalty of twenty per cent (20%) of Gross "
            "Receipts from the exploitation of the Recordings."
        ),
    ),
    TemplateClauseSpec(
        clause_id="4.2",
        heading="Payment Dates",
        text=(
            "Within thirty (30) days after the end of each calendar quarter, the Company shall "
            "send the Artist a statement. The Company shall pay the royalties shown in that "
            "statement within fifteen (15) days after the statement date."
        ),
    ),
    TemplateClauseSpec(
        clause_id="4.3",
        heading="Accounting",
        text=(
            "The Company shall keep complete books and records of Gross Receipts and shall "
            "allow the Artist to inspect them once each year on reasonable notice."
        ),
    ),
    TemplateClauseSpec(
        clause_id="5.1",
        heading="Exclusivity",
        text=(
            "During the Term, the Artist shall work exclusively with the Company for the "
            "recording and release of the Recordings and shall not grant the same rights to "
            "any other label."
        ),
    ),
    TemplateClauseSpec(
        clause_id="6.1",
        heading="Termination",
        text=(
            "Either party may terminate this Agreement on thirty (30) days written notice if "
            "the other party commits a material breach and does not cure it within that period."
        ),
    ),
    TemplateClauseSpec(
        clause_id="7.1",
        heading="Renewal",
        text=(
            "The parties may renew this Agreement for a further period only by a written "
            "agreement signed by both parties."
        ),
    ),
    TemplateClauseSpec(
        clause_id="8.1",
        heading="Governing Law",
        text=(
            "This Agreement is governed by the laws of Kenya and the courts of Kenya have "
            "exclusive jurisdiction over any dispute about it."
        ),
    ),
    TemplateClauseSpec(
        clause_id="9.1",
        heading="Notices",
        text=(
            "Notices under this Agreement must be in writing and delivered to the addresses "
            "given by the parties in clause 1.1."
        ),
    ),
    TemplateClauseSpec(
        clause_id="10.1",
        heading="Entire Agreement",
        text=(
            "This Agreement is the entire agreement between the parties about the Recordings "
            "and replaces all earlier understandings on that subject."
        ),
    ),
)

STANDARD_CLAUSES_BY_ID: dict[str, TemplateClauseSpec] = {
    clause.clause_id: clause for clause in STANDARD_CLAUSES
}


def clause_block(
    clauses: tuple[TemplateClauseSpec, ...] | list[TemplateClauseSpec],
) -> str:
    """Render clauses as plain text for an evaluation prompt."""
    return "\n\n".join(
        f"{clause.clause_id} {clause.heading}\n{clause.text}" for clause in clauses
    )
