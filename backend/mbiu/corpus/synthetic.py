"""Synthetic reference corpus for tracer bullet and offline evaluations.

Provides hand-crafted standard templates derived from public guidelines
(WIPO, Kenya Copyright Act Cap. 130, and KECOBO guidance).
Used for simple in-memory retrieval during tracer-bullet evaluation.
"""

from dataclasses import dataclass
from typing import Final

from mbiu.api.schemas import Evidence


@dataclass(frozen=True)
class SyntheticTemplateClause:
    """A single synthetic reference template clause."""

    template_id: str
    source_title: str
    jurisdiction: str
    topic: str
    excerpt: str
    keywords: tuple[str, ...]

    def to_evidence(self, evidence_id: str) -> Evidence:
        """Convert to an API Evidence model."""
        return Evidence(
            evidence_id=evidence_id,
            template_id=self.template_id,
            source_title=self.source_title,
            jurisdiction=self.jurisdiction,
            excerpt=self.excerpt,
        )


SYNTHETIC_CORPUS: Final[tuple[SyntheticTemplateClause, ...]] = (
    SyntheticTemplateClause(
        template_id="tpl-wipo-recording-royalties",
        source_title="WIPO Guide on Music Contracts (Model Agreement)",
        jurisdiction="KE / International",
        topic="royalties",
        excerpt=(
            "The Label shall pay to the Artist a royalty of not less than 15% to 20% "
            "of Gross Receipts derived from the commercial exploitation of the Masters, "
            "calculated without deduction of marketing, distribution overhead, "
            "or administrative costs."
        ),
        keywords=("royalty", "royalties", "receipts", "gross", "net", "sales", "streaming", "%"),
    ),
    SyntheticTemplateClause(
        template_id="tpl-kecobo-recoupment",
        source_title="KECOBO Standard Guidance on Recording Deals",
        jurisdiction="KE",
        topic="recoupment",
        excerpt=(
            "Direct recording and production costs approved in advance in writing shall be "
            "recoupable solely from the Artist's accrued royalties. In no event shall the Artist "
            "be personally liable to repay unrecouped balances, nor shall income from live gigs "
            "or outside work be garnished for recoupment."
        ),
        keywords=("recoup", "recoupable", "recoupment", "advance", "costs", "studio", "expenses"),
    ),
    SyntheticTemplateClause(
        template_id="tpl-wipo-term-duration",
        source_title="WIPO Guide on Music Contracts (Model Agreement)",
        jurisdiction="KE / International",
        topic="term",
        excerpt=(
            "The initial term of this Agreement shall be for a period of one (1) year "
            "from the Effective Date. Any extension or renewal options shall be exercisable "
            "only upon the mutual written agreement of both parties."
        ),
        keywords=("term", "duration", "period", "years", "months", "renewal", "extension"),
    ),
    SyntheticTemplateClause(
        template_id="tpl-cap130-grant-of-rights",
        source_title="Kenya Copyright Act (Cap. 130) Standard Assignment Provisions",
        jurisdiction="KE",
        topic="rights",
        excerpt=(
            "The Artist grants to the Company a non-exclusive license to reproduce and "
            "distribute the Masters for the duration of the agreed Term. All underlying "
            "copyrights, songwriting publishing shares, and moral rights remain strictly "
            "vested in the Artist."
        ),
        keywords=(
            "grant",
            "rights",
            "copyright",
            "masters",
            "ownership",
            "perpetual",
            "exclusive",
        ),
    ),
    SyntheticTemplateClause(
        template_id="tpl-kecobo-exclusivity",
        source_title="KECOBO Guidelines on Artist Exclusivity",
        jurisdiction="KE",
        topic="exclusivity",
        excerpt=(
            "Exclusivity shall apply solely to the release of contracted studio recordings. "
            "The Artist retains full freedom to perform live, collaborate on non-competing "
            "projects, and pursue independent brand or freelance opportunities."
        ),
        keywords=(
            "exclusivity",
            "exclusive",
            "solely",
            "restrict",
            "perform",
            "freedom",
            "collaborate",
        ),
    ),
    SyntheticTemplateClause(
        template_id="tpl-wipo-accounting-audit",
        source_title="WIPO Guide on Music Contracts (Model Agreement)",
        jurisdiction="KE / International",
        topic="accounting",
        excerpt=(
            "The Company shall render detailed accounting statements semi-annually within sixty "
            "(60) days following 30 June and 31 December. The Artist shall have the right upon "
            "reasonable notice to inspect and audit all books, statements, and streaming logs "
            "relating to their works."
        ),
        keywords=(
            "accounting",
            "audit",
            "statements",
            "semi-annually",
            "quarterly",
            "inspect",
            "books",
        ),
    ),
    SyntheticTemplateClause(
        template_id="tpl-live-gig-compensation",
        source_title="Kenyan Live Performance Standard Terms",
        jurisdiction="KE",
        topic="compensation",
        excerpt=(
            "The Promoter shall pay the Artist a guaranteed fee with a minimum 50% "
            "non-refundable deposit payable upon execution, and the remaining balance "
            "immediately prior to or upon conclusion of the performance. Local hospitality "
            "and technical rider items shall be provided."
        ),
        keywords=("live", "gig", "performance", "promoter", "fee", "deposit", "venue", "rider"),
    ),
    SyntheticTemplateClause(
        template_id="tpl-kecobo-termination",
        source_title="KECOBO Model Artist Agreement",
        jurisdiction="KE",
        topic="termination",
        excerpt=(
            "Either party may terminate this Agreement upon thirty (30) days written notice for "
            "material breach, provided the breaching party fails to cure such breach within the "
            "thirty (30) day notice period."
        ),
        keywords=("terminate", "termination", "breach", "notice", "cure", "cancel"),
    ),
)


def retrieve_simple_evidence(clause_text: str, max_items: int = 1) -> list[Evidence]:
    """Retrieve best-matching synthetic template evidence based on keyword heuristics.

    Args:
        clause_text: Extracted text of the clause to match.
        max_items: Maximum number of template excerpts to return.

    Returns:
        List of Evidence objects with assigned stable evidence IDs.
    """
    text_lower = clause_text.lower()
    scored: list[tuple[int, SyntheticTemplateClause]] = []

    for template in SYNTHETIC_CORPUS:
        score = sum(1 for kw in template.keywords if kw in text_lower)
        if score > 0:
            scored.append((score, template))

    # Sort descending by score
    scored.sort(key=lambda item: item[0], reverse=True)

    results: list[Evidence] = []
    for idx, (_, template) in enumerate(scored[:max_items], start=1):
        results.append(template.to_evidence(f"ev-{idx}"))

    # If no keywords matched, provide general royalty or rights standard as default candidate
    if not results and SYNTHETIC_CORPUS:
        results.append(SYNTHETIC_CORPUS[0].to_evidence("ev-1"))

    return results
