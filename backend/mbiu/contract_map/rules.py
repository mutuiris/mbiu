"""Deterministic rule checks for contract-wide issues.

Detects explicit conflicts and overrides between linked or candidate clauses
using deterministic text inspection and exact quote extraction.

Rules enforced:
1. Exact substring rule: quotes must be exact verbatim substrings of the clauses sent.
2. Impartial reporting: Mbiu reports that one clause claims to override or conflict
   with another; it never decides which clause a court would apply.
"""

from __future__ import annotations

import re
from typing import Final

from mbiu.api.schemas import ContractIssue
from mbiu.contract_map.candidates import CandidatePair
from mbiu.contract_map.deterministic import OverrideOccurrence
from mbiu.documents.segment import Clause, SegmentedDocument

_DURATION_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)"
    r"\s*(?:\(\s*(\d+)\s*\)\s*)?years?\b",
    re.IGNORECASE,
)

_WORD_TO_NUMBER: Final[dict[str, int]] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _extract_duration_years(text: str) -> tuple[int, str] | None:
    """Find duration in years and the exact substring mentioning it."""
    for sentence in re.split(r"(?<=[.;\n])\s+", text):
        if "term" not in sentence.lower() and "year" not in sentence.lower():
            continue
        match = _DURATION_RE.search(sentence)
        if match is not None:
            numeral = match.group(2)
            if numeral is not None:
                val = int(numeral)
            else:
                word = match.group(1).lower()
                val = _WORD_TO_NUMBER.get(word, int(word) if word.isdigit() else 0)
            if val > 0:
                # Return the duration value and the sentence as the verbatim quote
                return val, sentence.strip()
    return None


def _find_containing_sentence(text: str, substring: str) -> str:
    """Find the sentence within text that contains the substring."""
    for sentence in re.split(r"(?<=[.;\n])\s+", text):
        if substring in sentence:
            return sentence.strip()
    # Fallback to substring itself if not cleanly sentence-split
    return substring.strip()


def check_deterministic_issues(
    segmented: SegmentedDocument,
    candidate_pairs: list[CandidatePair],
    override_occurrences: list[OverrideOccurrence],
) -> list[ContractIssue]:
    """Detect contract issues deterministically from candidate pairs and overrides.

    Args:
        segmented: The segmented contract document.
        candidate_pairs: Nominated candidate pairs.
        override_occurrences: Override phrases detected in the text.

    Returns:
        List of verified ContractIssue objects.
    """
    issues: list[ContractIssue] = []
    seen_issue_pairs: set[tuple[str, str]] = set()

    clause_map: dict[str, Clause] = {c.clause_id: c for c in segmented.clauses}

    # 1. Check targeted overrides for direct duration/term contradictions
    for occ in override_occurrences:
        if not occ.target_clause_id:
            continue
        c_from = clause_map.get(occ.from_clause_id)
        c_to = clause_map.get(occ.target_clause_id)
        if not c_from or not c_to:
            continue

        pair_key = (
            min(c_from.clause_id, c_to.clause_id),
            max(c_from.clause_id, c_to.clause_id),
        )
        if pair_key in seen_issue_pairs:
            continue

        # Check duration clash
        dur_from = _extract_duration_years(c_from.text)
        dur_to = _extract_duration_years(c_to.text)

        if dur_from and dur_to and dur_from[0] != dur_to[0]:
            # Both specify different term lengths, and one overrides the other
            quote_from = dur_from[1]
            quote_to = dur_to[1]

            # Double check quotes are verbatim substrings
            if quote_from in c_from.text and quote_to in c_to.text:
                pages = sorted(list(set(c_from.pages + c_to.pages)))
                # Order clause IDs: primary/earlier clause first
                c1_id, c2_id = (
                    (c_to.clause_id, c_from.clause_id)
                    if c_to.start_offset < c_from.start_offset
                    else (c_from.clause_id, c_to.clause_id)
                )
                q1, q2 = (
                    (quote_to, quote_from)
                    if c_to.start_offset < c_from.start_offset
                    else (quote_from, quote_to)
                )

                issues.append(
                    ContractIssue(
                        kind="conflict",
                        clause_ids=(c1_id, c2_id),
                        pages=pages,
                        explanation=(
                            f"Clause {c_from.clause_id} sets the Term to {dur_from[0]} years "
                            f"notwithstanding clause {c_to.clause_id} which provides for a "
                            f"{dur_to[0]} year Term, creating a cross-clause conflict on duration."
                        ),
                        quotes=(q1, q2),
                    )
                )
                seen_issue_pairs.add(pair_key)
                continue

        # If it's a targeted override without duration clash, report as an override issue
        override_sentence = _find_containing_sentence(c_from.text, occ.matched_phrase)
        if override_sentence in c_from.text:
            # Quote first sentence of target clause
            first_sentence_target = re.split(r"(?<=[.;\n])\s+", c_to.text)[0].strip()
            if first_sentence_target in c_to.text:
                pages = sorted(list(set(c_from.pages + c_to.pages)))
                c1_id, c2_id = (
                    (c_to.clause_id, c_from.clause_id)
                    if c_to.start_offset < c_from.start_offset
                    else (c_from.clause_id, c_to.clause_id)
                )
                q1, q2 = (
                    (first_sentence_target, override_sentence)
                    if c_to.start_offset < c_from.start_offset
                    else (override_sentence, first_sentence_target)
                )

                issues.append(
                    ContractIssue(
                        kind="override",
                        clause_ids=(c1_id, c2_id),
                        pages=pages,
                        explanation=(
                            f"Clause {c_from.clause_id} claims to override "
                            f"clause {c_to.clause_id}. Mbiu reports that one clause claims to "
                            "override another; it never decides which a court would apply."
                        ),
                        quotes=(q1, q2),
                    )
                )
                seen_issue_pairs.add(pair_key)

    # 2. Check candidate pairs in same topic (e.g. term) even if override was general
    for pair in candidate_pairs:
        c_a = pair.clause_a
        c_b = pair.clause_b
        pair_key = (
            min(c_a.clause_id, c_b.clause_id),
            max(c_a.clause_id, c_b.clause_id),
        )
        if pair_key in seen_issue_pairs:
            continue

        dur_a = _extract_duration_years(c_a.text)
        dur_b = _extract_duration_years(c_b.text)
        if dur_a and dur_b and dur_a[0] != dur_b[0]:
            # Both define contradictory terms on the same topic
            quote_a = dur_a[1]
            quote_b = dur_b[1]
            if quote_a in c_a.text and quote_b in c_b.text:
                pages = sorted(list(set(c_a.pages + c_b.pages)))
                c1_id, c2_id = (
                    (c_a.clause_id, c_b.clause_id)
                    if c_a.start_offset < c_b.start_offset
                    else (c_b.clause_id, c_a.clause_id)
                )
                q1, q2 = (
                    (quote_a, quote_b)
                    if c_a.start_offset < c_b.start_offset
                    else (quote_b, quote_a)
                )

                issues.append(
                    ContractIssue(
                        kind="conflict",
                        clause_ids=(c1_id, c2_id),
                        pages=pages,
                        explanation=(
                            f"Clause {c_a.clause_id} and clause {c_b.clause_id} specify "
                            f"conflicting durations for the Term ({dur_a[0]} years vs "
                            f"{dur_b[0]} years)."
                        ),
                        quotes=(q1, q2),
                    )
                )
                seen_issue_pairs.add(pair_key)

    return issues
