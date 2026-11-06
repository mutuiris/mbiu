"""Deterministic reference evaluation used when no live model is configured.

The production label is assigned by code from the model's evidence, never by the
model itself. This module mirrors that idea for the synthetic golden set: it
reads the clause text with fixed rules, so CI can exercise the gate hermetically
and prove the wiring before a Gemini key is available.
"""

from __future__ import annotations

import re

from evals.generator.models import (
    ClauseExpectation,
    ClausePrediction,
    ContractIssuePrediction,
    ContractPrediction,
    GoldenContract,
)
from evals.generator.risks import RiskKind

_PERPETUAL_RE = re.compile(
    r"\b(?:in perpetuity|perpetual(?:ly)?|throughout the universe|without limit of time)\b",
    re.IGNORECASE,
)

_EXCLUSIVE_RE = re.compile(r"(?<!non-)\bexclusiv(?:e|ely)\b", re.IGNORECASE)
_POST_TERM_RE = re.compile(
    r"\b(?:after|following|beyond)\b[^.]{0,60}\b(?:expiry|expiration|termination|end)\b"
    r"[^.]{0,60}\bTerm\b",
    re.IGNORECASE,
)

_DEDUCTION_RE = re.compile(
    r"\b(?:after deducting|deduct(?:ed|ion|ions)?|less|net of|recoup(?:ment|able)?)\b",
    re.IGNORECASE,
)
_COST_RE = re.compile(
    r"\b(?:costs?|expenses?|advances?|overheads?|marketing|distribution|administration)\b",
    re.IGNORECASE,
)

_DATE_RE = re.compile(
    r"\b(?:within|after|before|by|on or before)\s+(?:\w+\s+){0,2}"
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|fifteen|thirty|sixty|\d+)"
    r"\s*(?:\(\s*\d+\s*\)\s*)?(?:days?|weeks?|months?|years?)\b"
    r"|\beach\s+(?:calendar\s+)?(?:quarter|month|year)\b"
    r"|\b(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\b",
    re.IGNORECASE,
)

_DURATION_RE = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)"
    r"\s*(?:\(\s*(\d+)\s*\)\s*)?years?\b",
    re.IGNORECASE,
)
_TERM_DEFINITION_RE = re.compile(
    r"\b(?:is|shall be|continues for|lasts for|shall continue for)\b",
    re.IGNORECASE,
)

_WORD_NUMBERS: dict[str, int] = {
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


def detect_clause_risks(heading: str, text: str) -> tuple[str, ...]:
    """Detect the four single-clause risks in one clause."""
    risks: list[str] = []
    lowered_heading = heading.lower()

    if _PERPETUAL_RE.search(text):
        risks.append(RiskKind.PERPETUAL_RIGHTS.value)

    exclusivity_topic = (
        "exclusiv" in lowered_heading or "work exclusively" in text.lower()
    )
    if exclusivity_topic and _EXCLUSIVE_RE.search(text) and _POST_TERM_RE.search(text):
        risks.append(RiskKind.EXCLUSIVITY_BEYOND_TERM.value)

    payment_topic = "payment" in lowered_heading or "statement" in lowered_heading
    if payment_topic and _DATE_RE.search(text) is None:
        risks.append(RiskKind.MISSING_PAYMENT_DATES.value)

    royalty_topic = "royalt" in lowered_heading or "royalt" in text.lower()
    if royalty_topic and _DEDUCTION_RE.search(text) and _COST_RE.search(text):
        risks.append(RiskKind.DEDUCTIONS_BEFORE_ROYALTIES.value)

    return tuple(risks)


def _duration_years(match: re.Match[str]) -> int:
    numeral = match.group(2)
    if numeral is not None:
        return int(numeral)
    word = match.group(1).lower()
    return _WORD_NUMBERS.get(word, int(word) if word.isdigit() else 0)


def _term_durations(
    clauses: tuple[ClauseExpectation, ...],
) -> tuple[tuple[str, int], ...]:
    """Find clauses that define a Term length, e.g. 'the Term ... is five (5) years'."""
    durations: list[tuple[str, int]] = []
    for clause in clauses:
        if clause.heading.lower() not in {"term", "renewal"}:
            continue
        for sentence in re.split(r"(?<=[.;])\s+", clause.text):
            if "term" not in sentence.lower():
                continue
            if _TERM_DEFINITION_RE.search(sentence) is None:
                continue
            match = _DURATION_RE.search(sentence)
            if match is not None:
                durations.append((clause.clause_id, _duration_years(match)))
                break
    return tuple(durations)


def evaluate_contract(expectation: GoldenContract) -> ContractPrediction:
    """Evaluate a synthetic contract with fixed rules and return a prediction."""
    outcomes: dict[str, str] = {}
    flags: dict[str, tuple[str, ...]] = {}
    for clause in expectation.clauses:
        detected = detect_clause_risks(clause.heading, clause.text)
        outcomes[clause.clause_id] = "worse_for_you" if detected else "matches_standard"
        flags[clause.clause_id] = detected

    issues: list[ContractIssuePrediction] = []
    durations = _term_durations(expectation.clauses)
    distinct = {years for _, years in durations}
    if len(distinct) > 1:
        clause_ids = tuple(clause_id for clause_id, _ in durations)
        issues.append(
            ContractIssuePrediction(
                issue_id="term-length-conflict-" + "-".join(clause_ids),
                kind="term_length_conflict",
                clause_ids=clause_ids,
                note=(
                    "The contract defines the Term with different lengths: "
                    + ", ".join(
                        f"clause {clause_id} says {years} years"
                        for clause_id, years in durations
                    )
                ),
            )
        )
        for clause_id in clause_ids:
            outcomes[clause_id] = "worse_for_you"
            flags[clause_id] = (*flags[clause_id], RiskKind.CROSS_CLAUSE_CONFLICT.value)

    results = tuple(
        ClausePrediction(
            clause_id=clause.clause_id,
            status="evaluated",
            comparison=outcomes[clause.clause_id],
            risk_flags=flags[clause.clause_id],
        )
        for clause in expectation.clauses
    )
    return ContractPrediction(
        contract_id=expectation.contract_id,
        clause_results=results,
        contract_issues=tuple(issues),
    )


def lenient_prediction(expectation: GoldenContract) -> ContractPrediction:
    """Model the output of a broken prompt that calls everything standard."""
    return ContractPrediction(
        contract_id=expectation.contract_id,
        clause_results=tuple(
            ClausePrediction(
                clause_id=clause.clause_id,
                status="evaluated",
                comparison="matches_standard",
                risk_flags=(),
                note="Similar topic to the standard.",
            )
            for clause in expectation.clauses
        ),
        contract_issues=(),
    )
