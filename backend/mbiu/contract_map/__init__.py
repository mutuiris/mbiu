"""Whole-contract map package (MB-14).

Discovers cross-clause relationships across the entire contract:
- Deterministic links from cross-references ("clause 12", "Schedule B"),
  override wording ("notwithstanding", "subject to", "save as provided",
  "in the event of conflict"), and defined terms.
- Candidate pairs combining linked clauses and same-topic clustering.
- Contract-wide conflict and override detection with exact quote verification.
- Contract type classification matching reviewed standard templates.

Adheres strictly to Mbiu invariants:
- Zero storage: Operates purely in-memory.
- Impartiality: Reports what each clause claims or says; never decides which a court would apply.
- Grounding: Quotes must be exact verbatim substrings of the clauses.
"""

from __future__ import annotations

from mbiu.api.schemas import ContractMapPayload
from mbiu.contract_map.analyzer import analyze_contract_issues
from mbiu.contract_map.candidates import build_candidate_pairs
from mbiu.contract_map.classifier import detect_contract_type
from mbiu.contract_map.deterministic import build_deterministic_links
from mbiu.documents.segment import SegmentedDocument
from mbiu.llm.gemini import Gemini


async def map_contract(
    segmented: SegmentedDocument,
    *,
    llm: Gemini | None = None,
    deadline: float | None = None,
) -> ContractMapPayload:
    """Analyze a segmented contract and produce its complete contract map.

    Args:
        segmented: The segmented contract document.
        llm: Optional Gemini client (must have store=False).
        deadline: Optional deadline timestamp for LLM checks.

    Returns:
        ContractMapPayload containing contract_type, links, and issues.
    """
    # 1. Classify contract type
    contract_type = detect_contract_type(segmented)

    # 2. Extract deterministic links and override phrases
    deterministic_links, overrides = build_deterministic_links(segmented)

    # 3. Generate candidate pairs (linked + same-topic clauses)
    candidate_pairs, all_links = build_candidate_pairs(segmented, deterministic_links)

    # 4. Analyze candidate pairs for conflicts and overrides with quote verification
    issues = await analyze_contract_issues(
        segmented,
        candidate_pairs,
        overrides,
        llm=llm,
        deadline=deadline,
    )

    return ContractMapPayload(
        contract_type=contract_type,
        links=all_links,
        issues=issues,
    )


__all__ = [
    "analyze_contract_issues",
    "build_candidate_pairs",
    "build_deterministic_links",
    "detect_contract_type",
    "map_contract",
]
