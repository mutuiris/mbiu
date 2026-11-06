"""AI-assisted whole-contract map analyzer and quote verification.

Runs overview or batched checks using Gemini with store=False.
Enforces the core safety rule:
Model output is a proposal; code strictly verifies that every quote is an exact
verbatim substring of what was sent to the model before accepting it.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Final, Literal

from django.conf import settings
from pydantic import BaseModel, Field

from mbiu.api.schemas import ContractIssue
from mbiu.contract_map.candidates import CandidatePair
from mbiu.contract_map.deterministic import OverrideOccurrence
from mbiu.contract_map.rules import check_deterministic_issues
from mbiu.documents.segment import Clause, SegmentedDocument
from mbiu.llm import as_data
from mbiu.llm.gemini import Gemini

logger = logging.getLogger(__name__)

PROMPT_FILE: Final[Path] = (
    Path(__file__).resolve().parent.parent / "llm" / "prompts" / "contract_map_v1.md"
)


class IssueProposal(BaseModel):
    """Proposal for a contract-wide issue returned by the LLM."""

    kind: Literal["conflict", "override"]
    clause_ids: list[str] = Field(min_length=2, max_length=2)
    quotes: list[str] = Field(min_length=2, max_length=2)
    explanation: str


class ContractMapAnalysisProposal(BaseModel):
    """Top-level LLM output for contract-wide issue analysis."""

    issues: list[IssueProposal] = Field(default_factory=list)


def load_contract_map_prompt() -> str:
    """Load the versioned contract map prompt from markdown."""
    if PROMPT_FILE.is_file():
        return PROMPT_FILE.read_text(encoding="utf-8")
    return (
        "You are Mbiu, analyzing a music contract for contradictions and override wording. "
        "Every quote must be an exact verbatim substring from the clause text."
    )


def verify_issue_quotes(
    proposal: IssueProposal,
    clause_map: dict[str, Clause],
) -> bool:
    """Verify that quotes in the proposal are exact verbatim substrings of the clauses.

    Code verification ensures hallucinated quotes are never admitted.
    """
    id_1, id_2 = proposal.clause_ids[0], proposal.clause_ids[1]
    if id_1 == id_2:
        return False

    c1 = clause_map.get(id_1)
    c2 = clause_map.get(id_2)
    if not c1 or not c2:
        return False

    q1, q2 = proposal.quotes[0].strip(), proposal.quotes[1].strip()
    if not q1 or not q2:
        return False

    # Check exact substring containment
    if q1 not in c1.text or q2 not in c2.text:
        # Check if the quotes were swapped by the model
        if q1 in c2.text and q2 in c1.text:
            # Swap quotes to match clause order
            proposal.clause_ids[0], proposal.clause_ids[1] = id_2, id_1
            return True
        return False

    return True


async def analyze_contract_issues(
    segmented: SegmentedDocument,
    candidate_pairs: list[CandidatePair],
    override_occurrences: list[OverrideOccurrence],
    *,
    llm: Gemini | None = None,
    deadline: float | None = None,
) -> list[ContractIssue]:
    """Analyze the contract for cross-clause conflicts and overrides.

    Uses deterministic checks as a guaranteed baseline, and enhances with
    verified LLM checks when an LLM is provided.

    Args:
        segmented: The segmented contract document.
        candidate_pairs: Nominated candidate pairs.
        override_occurrences: Override phrases detected in the text.
        llm: Optional Gemini model client (with store=False).
        deadline: Monotonic deadline timestamp for the model check.

    Returns:
        List of verified ContractIssue objects.
    """
    clause_map: dict[str, Clause] = {c.clause_id: c for c in segmented.clauses}

    # 1. Guaranteed deterministic baseline
    deterministic_issues = check_deterministic_issues(
        segmented, candidate_pairs, override_occurrences
    )

    if llm is None or not candidate_pairs:
        return deterministic_issues

    # 2. Model overview pass
    system_prompt = load_contract_map_prompt()
    effective_deadline = deadline if deadline is not None else time.monotonic() + 30.0

    # Build context for the candidate pairs
    prompt_lines: list[str] = [
        "Analyze the following candidate clause pairs from the contract "
        "for conflicts or overrides:\n"
    ]
    for idx, pair in enumerate(candidate_pairs[:20], start=1):
        prompt_lines.append(f"Candidate pair {idx} (reasons: {', '.join(pair.reasons)}):")
        # Contract text is untrusted, so it goes in data blocks the prompt treats as data
        for clause in (pair.clause_a, pair.clause_b):
            prompt_lines.append(
                as_data(
                    "contract_clause",
                    clause.text,
                    clause_id=clause.clause_id,
                    title=clause.title or "Untitled",
                    pages=",".join(str(p) for p in clause.pages),
                )
            )

    user_prompt = "\n".join(prompt_lines)

    verified_model_issues: list[ContractIssue] = []
    try:
        llm_result = await llm.generate(
            model=settings.GEMINI_MODEL_MAIN,
            instructions=system_prompt,
            content=user_prompt,
            output=ContractMapAnalysisProposal,
            deadline=effective_deadline,
        )
        proposal = llm_result.value

        for item in proposal.issues:
            if verify_issue_quotes(item, clause_map):
                c1 = clause_map[item.clause_ids[0]]
                c2 = clause_map[item.clause_ids[1]]
                pages = sorted(list(set(c1.pages + c2.pages)))
                verified_model_issues.append(
                    ContractIssue(
                        kind=item.kind,
                        clause_ids=(c1.clause_id, c2.clause_id),
                        pages=pages,
                        explanation=item.explanation,
                        quotes=(item.quotes[0].strip(), item.quotes[1].strip()),
                    )
                )
            else:
                logger.warning(
                    "Model proposal failed quote verification for clauses %s",
                    item.clause_ids,
                )
    except Exception as exc:
        logger.warning("LLM contract map check failed or timed out: %s", exc)

    # 3. Merge deterministic issues and verified model issues (deterministic takes priority)
    seen_pairs: set[tuple[str, str]] = set()
    combined_issues: list[ContractIssue] = []

    for issue in deterministic_issues:
        pair_key = (
            min(issue.clause_ids[0], issue.clause_ids[1]),
            max(issue.clause_ids[0], issue.clause_ids[1]),
        )
        seen_pairs.add(pair_key)
        combined_issues.append(issue)

    for issue in verified_model_issues:
        pair_key = (
            min(issue.clause_ids[0], issue.clause_ids[1]),
            max(issue.clause_ids[0], issue.clause_ids[1]),
        )
        if pair_key not in seen_pairs:
            seen_pairs.add(pair_key)
            combined_issues.append(issue)

    return combined_issues
