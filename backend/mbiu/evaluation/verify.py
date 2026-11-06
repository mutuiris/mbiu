"""Checks every model proposal must pass before an artist sees it.

Each rule takes the proposal and what the model was sent, and returns why it failed,
or None when it passed. Reasons go back to the model for its one repair attempt and
are never logged, because they can quote contract text.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from django.conf import settings
from opentelemetry import metrics
from pydantic import BaseModel, Field

from mbiu.api.schemas import Evidence, Outcome

failures_counter: Final = metrics.get_meter("mbiu.verify").create_counter(
    "mbiu.verify.failures", description="Model proposals that failed a verification rule"
)

MAX_LENGTH: Final = {"headline": 80, "what_it_says": 280, "what_it_means": 280, "ask_them": 160}

NUMBER_WORDS: Final = {
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
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "eighteen": 18,
    "twenty": 20,
    "twenty-four": 24,
    "thirty": 30,
    "thirty-six": 36,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "ninety": 90,
    "hundred": 100,
}
_word_alternatives = "|".join(sorted(NUMBER_WORDS, key=len, reverse=True))
DIGITS: Final = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")
WORDS: Final = re.compile(rf"\b(?:{_word_alternatives})\b", re.IGNORECASE)
# A number word only counts as a figure in the model's text when a unit follows it,
# so "one of the clauses" isn't treated as an invented number
WORD_FIGURES: Final = re.compile(
    rf"\b(?:{_word_alternatives})(?=\s+(?:days?|weeks?|months?|years?|per\s?cent)\b)",
    re.IGNORECASE,
)

LEGAL_CONCLUSIONS: Final = re.compile(
    r"\b(?:illegal|unlawful|unenforceable|enforceable|legally binding|void|against the law"
    r"|safe|unsafe|guaranteed?|risk-free)\b"
    r"|\b(?:you should|you shouldn't|you must|don't|do not|never)\s+(?:not\s+)?"
    r"(?:sign|accept|reject)\b",
    re.IGNORECASE,
)

JARGON: Final = (
    r"net receipts",
    r"recoup\w*",
    r"in perpetuity",
    r"cross-collaterali[sz]\w*",
    r"indemn\w*",
    r"moral rights",
    r"mechanical royalt\w*",
    r"neighbou?ring rights",
    r"synchroni[sz]ation",
    r"force majeure",
    r"right of first refusal",
)
# What may follow a jargon term to show it is explained right there
EXPLAINED: Final = (
    r"[\"'”’]?(?:\s*\(|\s*:|\s+[-–—]\s|,?\s+(?:which |that )?means?\b|,?\s+meaning\b|,\s*i\.e\.)"
)

VAGUE_QUESTION: Final = re.compile(
    r"^(?:(?:can|could) you explain|what does (?:this|that|it) mean|what is (?:this|that)\b"
    r"|is (?:this|that|it) (?:good|bad|normal|fair|legal|safe|standard|ok(?:ay)?)\b"
    r"|why is (?:this|that) here|do you agree|can we (?:talk|discuss))",
    re.IGNORECASE,
)

PERCENT: Final = re.compile(r"%|\bper\s?cent\b", re.IGNORECASE)
MONEY: Final = re.compile(
    r"\b(?:royalt|receipts|income|revenue|earnings|proceeds|profits?\b|sales\b)", re.IGNORECASE
)
BASIS: Final = re.compile(r"\b(?:gross|net)\b", re.IGNORECASE)


class ClauseComparisonProposal(BaseModel):
    """The model's answer for one clause, which is only a proposal until verified."""

    comparison: Outcome
    headline: str
    what_it_says: str
    what_it_means: str
    clause_quote: str = Field(description="Exact substring quoted from the contract clause")
    evidence_quote: str | None = Field(
        default=None, description="Exact substring quoted from the template excerpt"
    )
    evidence_id: str | None = Field(
        default=None, description="The evidence_id of the template excerpt cited, if any"
    )
    clause_id: str | None = Field(
        default=None, description="The clause_id of the contract clause being compared"
    )
    ask_them: str | None = Field(
        default=None, description="A specific question to ask the other party"
    )


@dataclass(frozen=True)
class Sent:
    """What the model was shown for one clause."""

    clause_id: str
    clause_text: str
    evidence: list[Evidence]


def _card(proposal: ClauseComparisonProposal) -> str:
    return "\n".join(
        [proposal.headline, proposal.what_it_says, proposal.what_it_means, proposal.ask_them or ""]
    )


def _numbers(text: str, words: re.Pattern[str]) -> set[float]:
    found = {float(m.replace(",", "")) for m in DIGITS.findall(text)}
    return found | {float(NUMBER_WORDS[w.lower()]) for w in words.findall(text)}


def _syllables(word: str) -> int:
    word = word.lower()
    if len(word) > 3 and word.endswith("e") and not word.endswith("le"):
        word = word[:-1]
    return max(1, len(re.findall(r"[aeiouy]+", word)))


def reading_grade(text: str) -> float:
    """Flesch-Kincaid grade level: roughly the years of school needed to follow the text."""
    words = re.findall(r"[A-Za-z]+(?:'[a-z]+)?", text)
    if not words:
        return 0.0
    sentences = max(1, len(re.findall(r"[.!?]+(?:\s|$)", text)))
    syllables = sum(_syllables(w) for w in words)
    return 0.39 * len(words) / sentences + 11.8 * syllables / len(words) - 15.59


def quotes_are_exact(proposal: ClauseComparisonProposal, sent: Sent) -> str | None:
    """The model read what it cites: quotes are exact substrings of the text sent."""
    if not proposal.clause_quote.strip() or proposal.clause_quote not in sent.clause_text:
        return "clause_quote must be copied exactly, character for character, from the clause."
    if proposal.evidence_quote and proposal.evidence_quote.strip():
        excerpts = [
            e.excerpt
            for e in sent.evidence
            if proposal.evidence_id in (None, e.evidence_id, e.template_id)
        ]
        if not any(proposal.evidence_quote in excerpt for excerpt in excerpts):
            return "evidence_quote must be copied exactly from the standard template it cites."
    return None


def ids_are_real(proposal: ClauseComparisonProposal, sent: Sent) -> str | None:
    """Only real IDs: the clause and evidence IDs were sent for this clause."""
    if proposal.clause_id is not None and proposal.clause_id != sent.clause_id:
        return f"clause_id must be {sent.clause_id}, the clause you were sent."
    sent_ids = {e.evidence_id for e in sent.evidence} | {e.template_id for e in sent.evidence}
    if proposal.evidence_id is not None and proposal.evidence_id not in sent_ids:
        return "evidence_id must be the ID of a standard template you were sent, or null."
    return None


def numbers_are_grounded(proposal: ClauseComparisonProposal, sent: Sent) -> str | None:
    """Every figure, percentage and duration appears in the clause or the template."""
    source = "\n".join([sent.clause_text, sent.clause_id, *(e.excerpt for e in sent.evidence)])
    invented = _numbers(_card(proposal), WORD_FIGURES) - _numbers(source, WORDS)
    if invented:
        figures = ", ".join(f"{n:g}" for n in sorted(invented))
        return f"These figures are not in the clause or the template: {figures}. Remove them."
    return None


def no_legal_conclusions(proposal: ClauseComparisonProposal, sent: Sent) -> str | None:
    """No legal conclusions or advice to sign, unless quoting the contract's own words."""
    source = "\n".join([sent.clause_text, *(e.excerpt for e in sent.evidence)]).lower()
    found = {m.lower() for m in LEGAL_CONCLUSIONS.findall(_card(proposal))}
    blocked = sorted(word for word in found if word not in source)
    if blocked:
        return (
            f"Do not use {', '.join(blocked)}: Mbiu explains clauses and never gives legal "
            "conclusions or says whether to sign."
        )
    return None


def plain_language(proposal: ClauseComparisonProposal, sent: Sent) -> str | None:
    """Readable at the configured grade, with jargon explained on the same card."""
    grade = reading_grade(f"{proposal.what_it_says} {proposal.what_it_means}")
    if grade > settings.MAX_READING_GRADE:
        return (
            f"what_it_says and what_it_means read at school grade {grade:.0f}; use shorter "
            f"sentences and simpler words to get under grade {settings.MAX_READING_GRADE:g}."
        )
    card = _card(proposal)
    for term in JARGON:
        used = re.search(rf"\b{term}", card, re.IGNORECASE)
        if used and not re.search(rf"\b{term}{EXPLAINED}", card, re.IGNORECASE):
            return f'Explain "{used.group(0)}" in plain words right after it is used.'
    return None


def fits_a_phone(proposal: ClauseComparisonProposal, sent: Sent) -> str | None:
    """Each field fits its character limit on a phone screen."""
    too_long = [
        f"{field} (at most {limit} characters)"
        for field, limit in MAX_LENGTH.items()
        if len(getattr(proposal, field) or "") > limit
    ]
    return f"Shorten {', '.join(too_long)}." if too_long else None


def usable_question(proposal: ClauseComparisonProposal, sent: Sent) -> str | None:
    """ask_them is a question that asks for a specific change."""
    question = (proposal.ask_them or "").strip()
    if not question:
        return None
    if not question.endswith("?"):
        return "ask_them must be a question ending with a question mark."
    if len(question.split()) < 5 or VAGUE_QUESTION.search(question):
        return "ask_them must ask the other party for a specific change to this clause."
    return None


def _is_money_share(text: str) -> bool:
    return bool(PERCENT.search(text) and MONEY.search(text))


def money_is_comparable(proposal: ClauseComparisonProposal, sent: Sent) -> str | None:
    """A money comparison needs both sides to say gross or net."""
    if proposal.comparison not in (
        Outcome.MATCHES_STANDARD,
        Outcome.BETTER_FOR_YOU,
        Outcome.WORSE_FOR_YOU,
    ):
        return None
    templates = [e.excerpt for e in sent.evidence if _is_money_share(e.excerpt)]
    if not templates or not _is_money_share(sent.clause_text):
        return None
    if all(BASIS.search(text) for text in [sent.clause_text, *templates]):
        return None
    return (
        "The clause or the template gives a percentage without saying gross or net, so the "
        "two can't be compared. Set comparison to cannot_compare."
    )


RULES: Final[dict[str, Callable[[ClauseComparisonProposal, Sent], str | None]]] = {
    "quotes_are_exact": quotes_are_exact,
    "ids_are_real": ids_are_real,
    "numbers_are_grounded": numbers_are_grounded,
    "no_legal_conclusions": no_legal_conclusions,
    "plain_language": plain_language,
    "fits_a_phone": fits_a_phone,
    "usable_question": usable_question,
    "money_is_comparable": money_is_comparable,
}


def verify(proposal: ClauseComparisonProposal, sent: Sent) -> dict[str, str]:
    """Run every rule and return the failed ones by name, with the reason for each."""
    failed = {
        name: reason for name, rule in RULES.items() if (reason := rule(proposal, sent)) is not None
    }
    for name in failed:
        failures_counter.add(1, {"rule": name})
    return failed
