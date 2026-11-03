"""Verification rules and repair orchestration for contract clause evaluation.

This module acts as the non-negotiable guard against false reassurance.
Nothing proposed by an AI model reaches an artist until code has checked it
against all eight verification rules.

Zero Contract Storage Invariant:
Operates entirely in memory on strings, data structures, and tokens.
No contract text, extracted quotes, or proposal data are ever written to disk,
databases, temporary files, logs, or external traces.

Decision Invariant:
Decisions are derived strictly from reviewed reference templates.
If verification fails after a single repair attempt, the outcome falls back
to 'cannot_compare' (⚪ Couldn't compare). It NEVER falls back to 'matches_standard'.
"""

from __future__ import annotations

import dataclasses as dc
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Label Constants (Strictly 4 labels, NO green label)
LABEL_TYPICAL = "typical"
LABEL_UNUSUAL = "unusual"
LABEL_WORTH_ASKING_ABOUT = "worth_asking_about"
LABEL_CANNOT_COMPARE = "cannot_compare"

VALID_LABELS = frozenset(
    {
        LABEL_TYPICAL,
        LABEL_UNUSUAL,
        LABEL_WORTH_ASKING_ABOUT,
        LABEL_CANNOT_COMPARE,
    }
)

# Rule Names
RULE_VERBATIM_QUOTES = "verbatim_quotes"
RULE_GROUNDED_IDS = "grounded_ids"
RULE_GROUNDED_NUMBERS = "grounded_numbers"
RULE_NO_LEGAL_CONCLUSIONS = "no_legal_conclusions"
RULE_PLAIN_LANGUAGE = "plain_language"
RULE_PHONE_FRIENDLY_LENGTH = "phone_friendly_length"
RULE_USABLE_QUESTIONS = "usable_questions"
RULE_COMPARABLE_MONEY = "comparable_money"

ALL_RULES = (
    RULE_VERBATIM_QUOTES,
    RULE_GROUNDED_IDS,
    RULE_GROUNDED_NUMBERS,
    RULE_NO_LEGAL_CONCLUSIONS,
    RULE_PLAIN_LANGUAGE,
    RULE_PHONE_FRIENDLY_LENGTH,
    RULE_USABLE_QUESTIONS,
    RULE_COMPARABLE_MONEY,
)

# Rule 4: Forbidden Legal and Evaluative Phrases
FORBIDDEN_LEGAL_PHRASES: tuple[str, ...] = (
    "illegal",
    "unlawful",
    "unenforceable",
    "enforceable",
    "void",
    "null and void",
    "valid in court",
    "not legal",
    "legally binding",
    "court would strike down",
    "contrary to law",
    "fair",
    "unfair",
    "safe",
    "unsafe",
    "guaranteed",
    "no-risk",
    "risk-free",
    "you should sign",
    "you must sign",
    "don't sign",
    "do not sign",
    "never sign",
    "you shouldn't sign",
    "you should not sign",
    "must sign",
    "you must accept",
    "refuse this",
    "demand that",
    "you must reject",
    "you have to reject",
    "you must",
    "demand",
    "refuse",
    "do not accept",
)

# Rule 5: Industry Legal & Music Jargon Terms that require card explanations
INDUSTRY_JARGON: tuple[str, ...] = (
    "net receipts",
    "recoupable",
    "recoupment",
    "in perpetuity",
    "cross-collateralization",
    "cross-collateralized",
    "indemnity",
    "indemnification",
    "moral rights",
    "master rights",
    "reversion",
    "audit rights",
    "sync license",
    "synchronization license",
    "publishing administration",
    "mechanical royalties",
    "neighboring rights",
    "right of first refusal",
    "key man clause",
    "force majeure",
    "power of attorney",
)

# Rule 2: Direct untyped norm words rejected without code placeholder
UNTYPED_NORM_WORDS: tuple[str, ...] = (
    "industry standard",
    "industry-standard",
    "customary in the music industry",
    "normal deal",
    "customary",
    "normal standard",
)

# Rule 7: Vague Question Patterns
VAGUE_QUESTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^(can|could) you explain this\??$", re.IGNORECASE),
    re.compile(r"^what does this mean\??$", re.IGNORECASE),
    re.compile(r"^is this (good|bad|normal|fair|legal|safe)\??$", re.IGNORECASE),
    re.compile(r"^why is this here\??$", re.IGNORECASE),
    re.compile(r"^do you agree\??$", re.IGNORECASE),
    re.compile(r"^can we talk about this\??$", re.IGNORECASE),
    re.compile(r"^what is this\??$", re.IGNORECASE),
    re.compile(r"^is this standard\??$", re.IGNORECASE),
)


@dataclass(frozen=True)
class PhoneLimits:
    """Character length ceilings for phone display compatibility.

    Attributes:
        max_title_len: Maximum character length for card headline / title.
        max_plain_language_len: Maximum character length for what it says.
        max_why_it_matters_len: Maximum character length for practical implications.
        max_comparison_note_len: Maximum character length for comparison note.
        max_question_len: Maximum character length for each individual question.
    """

    max_title_len: int = 45
    max_plain_language_len: int = 200
    max_why_it_matters_len: int = 280
    max_comparison_note_len: int = 280
    max_question_len: int = 120


@dataclass(frozen=True)
class EvidenceCitation:
    """Citation of a reference standard chunk supporting a comparison.

    Attributes:
        chunk_id: Identifier of reference standard chunk.
        quote: Verbatim substring extracted from reference chunk.
        source_title: Optional human-readable source title.
    """

    chunk_id: str
    quote: str
    source_title: str | None = None


@dataclass(frozen=True)
class MoneyExampleInputs:
    """Inputs for code-calculated shillings illustrations.

    Attributes:
        rate: Operative percentage or flat fee (e.g. 15.0 or '15%').
        basis: Base calculation mode ('gross' or 'net').
        deductions: List of allowable deductions cited from the clause.
        quote: Substring quoting the rate/deductions clause.
    """

    rate: str | float | None = None
    basis: str | None = None
    deductions: list[str] = dc.field(default_factory=list)
    quote: str | None = None


@dataclass(frozen=True)
class MoneyComparison:
    """Monetary comparison between contract clause and reference standard.

    Attributes:
        contract_basis: Base calculation in user contract ('gross' or 'net').
        reference_basis: Base calculation in reference standard ('gross' or 'net').
        contract_rate: Rate in user contract (percentage or amount).
        reference_rate: Rate in reference standard.
    """

    contract_basis: str | None = None
    reference_basis: str | None = None
    contract_rate: str | float | None = None
    reference_rate: str | float | None = None


@dataclass
class ClauseProposal:
    """Draft evaluation proposal produced by the AI model.

    Model proposals are proposals, not results. Nothing in this class reaches
    an artist until verified by code.
    """

    clause_id: str
    title: str
    key_quote: str
    plain_language: str
    why_it_matters: str
    comparison_note: str
    questions: list[str]
    matched_pattern_id: str | None = None
    implication: str | None = None  # 'none', 'minor', 'major', 'unclear'
    affects: str | None = None  # 'money', 'ownership', 'time', 'freedom_to_work', 'other'
    evidence: list[EvidenceCitation] = dc.field(default_factory=list)
    linked_clauses: list[str] = dc.field(default_factory=list)
    money_inputs: MoneyExampleInputs | None = None
    money_comparison: MoneyComparison | None = None
    jargon_definitions: dict[str, str] = dc.field(default_factory=dict)
    illustrative_examples: list[str] = dc.field(default_factory=list)


@dataclass(frozen=True)
class EvaluationContext:
    """Evaluation request context providing verified source texts and valid IDs.

    Attributes:
        clause_id: Extractor-assigned ID for the target clause.
        clause_text: Verbatim original text of the clause under evaluation.
        linked_clauses: Mapping of linked clause ID to verbatim text.
        reference_chunks: Mapping of reference standard chunk ID to verbatim text.
        known_patterns: Set of valid pattern IDs available in the corpus.
    """

    clause_id: str
    clause_text: str
    linked_clauses: dict[str, str] = dc.field(default_factory=dict)
    reference_chunks: dict[str, str] = dc.field(default_factory=dict)
    known_patterns: set[str] = dc.field(default_factory=set)


@dataclass(frozen=True)
class RuleViolation:
    """Details of a single verification rule check failure.

    Attributes:
        rule_name: Name of the rule that failed.
        message: Plain-language diagnostic explanation.
        field: Name of proposal field triggering the violation, if applicable.
        details: Additional contextual data for logging or model repair.
    """

    rule_name: str
    message: str
    field: str | None = None
    details: dict[str, Any] = dc.field(default_factory=dict)


@dataclass(frozen=True)
class RuleResult:
    """Result of running a single verification rule.

    Attributes:
        passed: True if the rule check succeeded, False otherwise.
        rule_name: Name of the verified rule.
        message: Summary message describing the outcome.
        violations: List of specific violations found.
    """

    passed: bool
    rule_name: str
    message: str = "Passed"
    violations: list[RuleViolation] = dc.field(default_factory=list)


@dataclass(frozen=True)
class VerificationResult:
    """Comprehensive result of running all verification rules against a proposal.

    Attributes:
        passed: True if all rules passed, False if any rule failed.
        violations: Aggregated list of all rule violations.
        rule_results: Mapping of rule name to individual RuleResult.
        verified_proposal: The verified proposal if passed, or safe fallback proposal.
        assigned_label: Code-assigned label ('typical', 'unusual', 'worth_asking_about',
            'cannot_compare').
        fallback_reason: Reason string if fallback occurred.
    """

    passed: bool
    violations: list[RuleViolation] = dc.field(default_factory=list)
    rule_results: dict[str, RuleResult] = dc.field(default_factory=dict)
    verified_proposal: ClauseProposal | None = None
    assigned_label: str | None = None
    fallback_reason: str | None = None


@dataclass(frozen=True)
class VerificationFeedback:
    """Structured repair feedback returned to the model upon verification failure.

    Attributes:
        failed_rules: List of rule names that failed.
        violations: Complete list of rule violations.
        repair_instructions: Instruction prompt for the model repair attempt.
    """

    failed_rules: list[str]
    violations: list[RuleViolation]
    repair_instructions: str


# Observability: Thread-safe failure counters per rule for metrics reporting
_COUNTER_LOCK = threading.Lock()
_RULE_FAILURE_COUNTERS: dict[str, int] = {rule: 0 for rule in ALL_RULES}


def record_rule_failure(rule_name: str) -> None:
    """Record an increment to a rule failure counter.

    Args:
        rule_name: Canonical rule identifier.
    """
    with _COUNTER_LOCK:
        _RULE_FAILURE_COUNTERS[rule_name] = _RULE_FAILURE_COUNTERS.get(rule_name, 0) + 1


def get_rule_failure_counts() -> dict[str, int]:
    """Retrieve a copy of current rule failure counters.

    Returns:
        Mapping of rule name to cumulative failure count.
    """
    with _COUNTER_LOCK:
        return dict(_RULE_FAILURE_COUNTERS)


def reset_rule_failure_counters() -> None:
    """Reset all rule failure counters to zero (used in tests and monitoring resets)."""
    with _COUNTER_LOCK:
        for rule in ALL_RULES:
            _RULE_FAILURE_COUNTERS[rule] = 0


# Text normalization & syllable helpers
def normalize_whitespace(text: str) -> str:
    """Normalize consecutive whitespace into single spaces and strip edges.

    Args:
        text: Raw input string.

    Returns:
        Whitespace-normalized string.
    """
    return re.sub(r"\s+", " ", text).strip()


def count_syllables_in_word(word: str) -> int:
    """Count syllables in an English word using deterministic heuristic rules.

    Args:
        word: Single word token.

    Returns:
        Positive integer count of syllables.
    """
    clean = re.sub(r"[^a-zA-Z]", "", word).lower()
    if not clean:
        return 0
    if len(clean) <= 3:
        return 1

    # Strip terminal silent e or unvocalized ed/es
    if clean.endswith("e") and not clean.endswith(("le", "ee")):
        clean = clean[:-1]
    elif clean.endswith("ed") and not clean.endswith(("ted", "ded")):
        clean = clean[:-2]
    elif clean.endswith("es") and not clean.endswith(("ses", "zes", "ches", "shes")):
        clean = clean[:-2]

    # Handle triphthongs / vowel-y-vowel (e.g. 'oya' in royalty -> ro-yal-ty)
    clean = re.sub(r"([aeiou])y([aeiou])", r"\1 \2", clean)
    # Split distinct adjacent vocalized vowels (ia, io, ua)
    clean = re.sub(r"([aeiou])(ia|io|ua)", r"\1 \2", clean)

    vowel_groups = re.findall(r"[aeiouy]+", clean)
    return max(1, len(vowel_groups))


def calculate_flesch_kincaid_grade(text: str) -> float:
    """Compute Flesch-Kincaid Grade Level for a given text snippet.

    Formula: 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59

    Args:
        text: Input text to analyze.

    Returns:
        Estimated US school grade level (float >= 0.0).
    """
    stripped = text.strip()
    if not stripped:
        return 0.0

    raw_sentences = [s.strip() for s in re.split(r"[.!?]+", stripped) if s.strip()]
    if not raw_sentences:
        raw_sentences = [stripped]

    words = [w for w in re.findall(r"[A-Za-z0-9\-']+", stripped) if any(c.isalnum() for c in w)]
    if not words:
        return 0.0

    total_syllables = sum(count_syllables_in_word(w) for w in words)
    words_count = len(words)
    sentences_count = len(raw_sentences)

    grade = 0.39 * (words_count / sentences_count) + 11.8 * (total_syllables / words_count) - 15.59
    return max(0.0, float(grade))


def _extract_all_numbers(text: str) -> set[str]:
    """Extract all numeric tokens, percentages, and written numerals from text.

    Args:
        text: String to scan.

    Returns:
        Set of standardized lowercase number strings.
    """
    found: set[str] = set()

    # Percentages: 15%, 15.5%
    for match in re.finditer(r"\b\d+(?:\.\d+)?%", text):
        found.add(match.group(0).lower())

    # Raw numbers: 15, 100,000, 2.5
    for match in re.finditer(r"\b\d+(?:,\d{3})*(?:\.\d+)?\b", text):
        clean_num = match.group(0).replace(",", "")
        found.add(clean_num)
        found.add(match.group(0))

    # Common written number words
    num_words = (
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "fifteen",
        "twenty",
        "twenty-four",
        "thirty",
        "thirty-six",
        "fifty",
        "sixty",
        "ninety",
        "hundred",
        "thousand",
    )
    for word in num_words:
        if re.search(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE):
            found.add(word.lower())

    return found


def _extract_durations(text: str) -> set[str]:
    """Extract duration expressions from text.

    Args:
        text: String to scan.

    Returns:
        Set of duration strings.
    """
    pattern = (
        r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve|eighteen|twenty|"
        r"twenty-four|thirty|thirty-six|sixty|ninety)\s+"
        r"(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?|semi-annually|quarterly|annually)\b"
    )
    return {m.group(0).lower() for m in re.finditer(pattern, text, re.IGNORECASE)}


# ==============================================================================
# RULE 1: Verbatim Quotes
# ==============================================================================
def verify_verbatim_quotes(proposal: ClauseProposal, context: EvaluationContext) -> RuleResult:
    """Verify that key quote and evidence quotes are exact substrings of sent texts.

    Whitespace-normalized comparisons are performed so that varying line breaks
    or multi-spaces do not cause false negatives, while preserving exact character
    fidelity.

    Args:
        proposal: Model proposal under evaluation.
        context: Request evaluation context containing verified source texts.

    Returns:
        RuleResult with status and any quote mismatch violations.
    """
    violations: list[RuleViolation] = []

    # 1. Verify key_quote against clause_text
    if not proposal.key_quote or not proposal.key_quote.strip():
        violations.append(
            RuleViolation(
                rule_name=RULE_VERBATIM_QUOTES,
                message="key_quote is missing or empty.",
                field="key_quote",
            )
        )
    else:
        norm_key_quote = normalize_whitespace(proposal.key_quote)
        norm_clause_text = normalize_whitespace(context.clause_text)

        if norm_key_quote not in norm_clause_text:
            violations.append(
                RuleViolation(
                    rule_name=RULE_VERBATIM_QUOTES,
                    message=(
                        f"key_quote '{proposal.key_quote}' is not an exact substring "
                        "of the sent clause text."
                    ),
                    field="key_quote",
                    details={"key_quote": proposal.key_quote},
                )
            )

    # 2. Verify each evidence quote against reference standard chunks
    for idx, ev in enumerate(proposal.evidence):
        if not ev.quote or not ev.quote.strip():
            violations.append(
                RuleViolation(
                    rule_name=RULE_VERBATIM_QUOTES,
                    message=f"Evidence citation for chunk '{ev.chunk_id}' has an empty quote.",
                    field=f"evidence[{idx}].quote",
                    details={"chunk_id": ev.chunk_id},
                )
            )
            continue

        ref_text = context.reference_chunks.get(ev.chunk_id)
        if ref_text is None:
            # Chunk ID missing is also caught by Rule 2, but quote cannot be verified
            violations.append(
                RuleViolation(
                    rule_name=RULE_VERBATIM_QUOTES,
                    message=(
                        f"Cannot verify quote for chunk '{ev.chunk_id}' "
                        "because chunk ID was not provided in request."
                    ),
                    field=f"evidence[{idx}].chunk_id",
                    details={"chunk_id": ev.chunk_id},
                )
            )
            continue

        norm_ev_quote = normalize_whitespace(ev.quote)
        norm_ref_text = normalize_whitespace(ref_text)
        if norm_ev_quote not in norm_ref_text:
            violations.append(
                RuleViolation(
                    rule_name=RULE_VERBATIM_QUOTES,
                    message=(
                        f"Evidence quote '{ev.quote}' is not an exact substring "
                        f"of reference chunk '{ev.chunk_id}'."
                    ),
                    field=f"evidence[{idx}].quote",
                    details={"chunk_id": ev.chunk_id, "quote": ev.quote},
                )
            )

    passed = len(violations) == 0
    if not passed:
        record_rule_failure(RULE_VERBATIM_QUOTES)
    return RuleResult(
        passed=passed,
        rule_name=RULE_VERBATIM_QUOTES,
        message="Verbatim quotes verified." if passed else "Quote mismatch detected.",
        violations=violations,
    )


# ==============================================================================
# RULE 2: Grounded IDs
# ==============================================================================
def verify_grounded_ids(proposal: ClauseProposal, context: EvaluationContext) -> RuleResult:
    """Verify that all clause IDs, evidence IDs, and pattern IDs belong to request.

    Rejects hallucinated IDs or references to external materials not in context.
    Also rejects untyped norm words ('industry standard', 'customary') without
    code placeholders.

    Args:
        proposal: Model proposal under evaluation.
        context: Request evaluation context containing valid IDs.

    Returns:
        RuleResult with status and any ID grounding violations.
    """
    violations: list[RuleViolation] = []

    # 1. Target clause ID must match request
    if proposal.clause_id != context.clause_id:
        violations.append(
            RuleViolation(
                rule_name=RULE_GROUNDED_IDS,
                message=(
                    f"Proposal clause_id '{proposal.clause_id}' does not match "
                    f"request clause_id '{context.clause_id}'."
                ),
                field="clause_id",
                details={"proposal_id": proposal.clause_id, "request_id": context.clause_id},
            )
        )

    # 2. Every cited evidence chunk ID must strictly exist in context.reference_chunks
    for idx, ev in enumerate(proposal.evidence):
        if ev.chunk_id not in context.reference_chunks:
            violations.append(
                RuleViolation(
                    rule_name=RULE_GROUNDED_IDS,
                    message=(
                        f"Cited evidence ID '{ev.chunk_id}' does not exist "
                        "in request reference chunks."
                    ),
                    field=f"evidence[{idx}].chunk_id",
                    details={"chunk_id": ev.chunk_id},
                )
            )

    # 3. Every linked clause ID must exist in context.linked_clauses
    for idx, linked_id in enumerate(proposal.linked_clauses):
        if linked_id not in context.linked_clauses:
            violations.append(
                RuleViolation(
                    rule_name=RULE_GROUNDED_IDS,
                    message=(
                        f"Cited linked clause ID '{linked_id}' does not exist "
                        "in request linked clauses."
                    ),
                    field=f"linked_clauses[{idx}]",
                    details={"linked_id": linked_id},
                )
            )

    # 4. Pattern ID must exist in known patterns if provided
    if proposal.matched_pattern_id and context.known_patterns:
        if proposal.matched_pattern_id not in context.known_patterns:
            violations.append(
                RuleViolation(
                    rule_name=RULE_GROUNDED_IDS,
                    message=(
                        f"Matched pattern ID '{proposal.matched_pattern_id}' "
                        "is not in known patterns."
                    ),
                    field="matched_pattern_id",
                    details={"pattern_id": proposal.matched_pattern_id},
                )
            )

    # 5. Direct use of untyped norm words without code placeholders is rejected
    if proposal.comparison_note:
        note_lower = proposal.comparison_note.lower()
        for norm_word in UNTYPED_NORM_WORDS:
            if re.search(r"\b" + re.escape(norm_word) + r"\b", note_lower):
                # Placeholder pattern: {{freq:...}}
                if "{{freq:" not in proposal.comparison_note:
                    violations.append(
                        RuleViolation(
                            rule_name=RULE_GROUNDED_IDS,
                            message=(
                                f"Direct use of untyped norm word '{norm_word}' is forbidden; "
                                "only frequency code placeholders (e.g. '{{freq:PXX}}') "
                                "are permitted."
                            ),
                            field="comparison_note",
                            details={"norm_word": norm_word},
                        )
                    )

    passed = len(violations) == 0
    if not passed:
        record_rule_failure(RULE_GROUNDED_IDS)
    return RuleResult(
        passed=passed,
        rule_name=RULE_GROUNDED_IDS,
        message="All IDs verified and grounded." if passed else "Ungrounded IDs detected.",
        violations=violations,
    )


# ==============================================================================
# RULE 3: Grounded Numbers
# ==============================================================================
def verify_grounded_numbers(proposal: ClauseProposal, context: EvaluationContext) -> RuleResult:
    """Verify that every number, percentage, and duration appears in the sent texts.

    Sources allowed: target clause text, linked clause texts, and cited reference
    chunk texts. Illustrative examples (e.g., code-calculated shillings examples)
    are exempt when explicitly marked. Hallucinated numbers trigger rule failure.

    Args:
        proposal: Model proposal under evaluation.
        context: Request evaluation context.

    Returns:
        RuleResult with status and any ungrounded figure violations.
    """
    violations: list[RuleViolation] = []

    # Assemble all allowed ground source texts
    allowed_sources: list[str] = [context.clause_text]
    allowed_sources.extend(context.linked_clauses.values())
    for ev in proposal.evidence:
        if ev.chunk_id in context.reference_chunks:
            allowed_sources.append(context.reference_chunks[ev.chunk_id])

    combined_allowed_text = " ".join(allowed_sources)
    allowed_numbers = _extract_all_numbers(combined_allowed_text)
    allowed_durations = _extract_durations(combined_allowed_text)

    # Include clause IDs as allowed numbers (e.g. clause "7.2" -> "7.2")
    allowed_numbers.add(context.clause_id.lower())
    for lid in context.linked_clauses:
        allowed_numbers.add(lid.lower())

    # Text fields in proposal to audit for model numbers
    fields_to_check: list[tuple[str, str]] = [
        ("title", proposal.title),
        ("plain_language", proposal.plain_language),
        ("why_it_matters", proposal.why_it_matters),
        ("comparison_note", proposal.comparison_note),
    ]
    for idx, q in enumerate(proposal.questions):
        fields_to_check.append((f"questions[{idx}]", q))

    # Exempt illustrative examples texts from grounding checks
    exempt_texts = " ".join(proposal.illustrative_examples)

    for field_name, text in fields_to_check:
        if not text:
            continue

        # 1. Check percentages: e.g. '15%'
        pct_matches = re.finditer(r"\b\d+(?:\.\d+)?%", text)
        for pm in pct_matches:
            pct = pm.group(0).lower()
            if pct in exempt_texts.lower():
                continue
            if pct not in allowed_numbers and pct not in combined_allowed_text.lower():
                violations.append(
                    RuleViolation(
                        rule_name=RULE_GROUNDED_NUMBERS,
                        message=(
                            f"Ungrounded percentage '{pct}' in {field_name} "
                            "not found in clause, linked clauses, or cited evidence."
                        ),
                        field=field_name,
                        details={"percentage": pct},
                    )
                )

        # 2. Check durations: e.g. '3 years', '90 days'
        dur_matches = _extract_durations(text)
        for dur in dur_matches:
            if dur in exempt_texts.lower():
                continue
            # Duration must appear in allowed durations or combined text
            if dur not in allowed_durations and dur not in combined_allowed_text.lower():
                violations.append(
                    RuleViolation(
                        rule_name=RULE_GROUNDED_NUMBERS,
                        message=(
                            f"Ungrounded duration '{dur}' in {field_name} "
                            "not found in clause, linked clauses, or cited evidence."
                        ),
                        field=field_name,
                        details={"duration": dur},
                    )
                )

        # 3. Check standalone numbers (excluding single digit structural indices 0-9)
        num_matches = re.finditer(r"\b\d+(?:,\d{3})*(?:\.\d+)?\b", text)
        for nm in num_matches:
            raw_num = nm.group(0)
            clean_num = raw_num.replace(",", "")
            # Skip single digit numbers 0-9 when used in sentences (e.g. 1 question, 2 options)
            if len(clean_num) == 1 and clean_num.isdigit():
                continue
            if raw_num in exempt_texts or clean_num in exempt_texts:
                continue

            if (
                clean_num not in allowed_numbers
                and raw_num not in allowed_numbers
                and clean_num not in combined_allowed_text
            ):
                violations.append(
                    RuleViolation(
                        rule_name=RULE_GROUNDED_NUMBERS,
                        message=(
                            f"Ungrounded number '{raw_num}' in {field_name} "
                            "not found in clause, linked clauses, or cited evidence."
                        ),
                        field=field_name,
                        details={"number": raw_num},
                    )
                )

    passed = len(violations) == 0
    if not passed:
        record_rule_failure(RULE_GROUNDED_NUMBERS)
    return RuleResult(
        passed=passed,
        rule_name=RULE_GROUNDED_NUMBERS,
        message="All numbers and figures grounded." if passed else "Ungrounded figures detected.",
        violations=violations,
    )


# ==============================================================================
# RULE 4: No Legal Conclusions & Objective Tone
# ==============================================================================
def verify_no_legal_conclusions(proposal: ClauseProposal, context: EvaluationContext) -> RuleResult:
    """Verify that proposal contains no legal conclusions, advice, or impermissible tone.

    Blocks advice or legal validity words ('illegal', 'unenforceable', 'safe',
    'guaranteed', 'you should sign', 'don't sign').
    Enforces objective tone in why_it_matters by requiring modal language ('may' or 'could')
    and rejecting imperative commands ('you must', 'demand', 'refuse').

    Args:
        proposal: Model proposal under evaluation.
        context: Request evaluation context.

    Returns:
        RuleResult with status and any legal conclusion violations.
    """
    violations: list[RuleViolation] = []

    fields_to_check: list[tuple[str, str]] = [
        ("title", proposal.title),
        ("plain_language", proposal.plain_language),
        ("why_it_matters", proposal.why_it_matters),
        ("comparison_note", proposal.comparison_note),
    ]
    for idx, q in enumerate(proposal.questions):
        fields_to_check.append((f"questions[{idx}]", q))

    # 1. Check forbidden legal advice / validity phrases
    for field_name, content in fields_to_check:
        if not content:
            continue
        for phrase in FORBIDDEN_LEGAL_PHRASES:
            pattern = r"\b" + re.escape(phrase) + r"\b"
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(
                    RuleViolation(
                        rule_name=RULE_NO_LEGAL_CONCLUSIONS,
                        message=(
                            f"Forbidden legal conclusion or advice phrase '{phrase}' "
                            f"found in {field_name}."
                        ),
                        field=field_name,
                        details={"forbidden_phrase": phrase},
                    )
                )

    # 2. Check objective tone in why_it_matters: must use 'may' or 'could'
    if proposal.why_it_matters:
        has_modal = bool(re.search(r"\b(may|could)\b", proposal.why_it_matters, re.IGNORECASE))
        if not has_modal:
            violations.append(
                RuleViolation(
                    rule_name=RULE_NO_LEGAL_CONCLUSIONS,
                    message=(
                        "why_it_matters must use objective modal language "
                        "('may' or 'could') to describe practical consequences."
                    ),
                    field="why_it_matters",
                )
            )

    passed = len(violations) == 0
    if not passed:
        record_rule_failure(RULE_NO_LEGAL_CONCLUSIONS)
    return RuleResult(
        passed=passed,
        rule_name=RULE_NO_LEGAL_CONCLUSIONS,
        message=(
            "No legal conclusions detected; objective tone verified."
            if passed
            else "Legal conclusions or tone violations detected."
        ),
        violations=violations,
    )


# ==============================================================================
# RULE 5: Plain Language & Jargon
# ==============================================================================
def verify_plain_language(
    proposal: ClauseProposal,
    context: EvaluationContext,
    max_grade_level: float = 9.0,
) -> RuleResult:
    """Verify readability score and ensure legal/industry jargon is explained on card.

    Readability is calculated via Flesch-Kincaid Grade Level on the musician-facing
    text (plain_language and why_it_matters).
    Jargon terms ('net receipts', 'recoupable', 'in perpetuity', etc.) must be defined
    or explained in the card content.

    Args:
        proposal: Model proposal under evaluation.
        context: Request evaluation context.
        max_grade_level: Upper grade ceiling for readability (default: 9.0).

    Returns:
        RuleResult with status and readability/jargon violations.
    """
    violations: list[RuleViolation] = []

    # 1. Readability Check
    combined_card_text = f"{proposal.plain_language} {proposal.why_it_matters}".strip()
    grade = calculate_flesch_kincaid_grade(combined_card_text)
    if grade > max_grade_level:
        violations.append(
            RuleViolation(
                rule_name=RULE_PLAIN_LANGUAGE,
                message=(
                    f"Readability grade level {grade:.1f} exceeds maximum "
                    f"threshold of {max_grade_level:.1f}."
                ),
                field="plain_language",
                details={"calculated_grade": grade, "max_grade_level": max_grade_level},
            )
        )

    # 2. Industry Jargon Explanation Check
    all_card_text = (
        f"{proposal.title} {proposal.plain_language} "
        f"{proposal.why_it_matters} {proposal.comparison_note}"
    ).lower()

    for term in INDUSTRY_JARGON:
        term_pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(term_pattern, all_card_text):
            # Check if defined in proposal.jargon_definitions
            is_defined = False
            for def_key, def_val in proposal.jargon_definitions.items():
                if term in def_key.lower() and len(def_val.strip()) > 5:
                    is_defined = True
                    break

            # Or check inline explanation patterns: e.g. 'term (meaning ...)'
            if not is_defined:
                explanation_cues = (
                    r"\b" + re.escape(term) + r"\s*\((?:which\s+)?means?[^)]+\)",
                    r"\b" + re.escape(term) + r"\s*\((?:defined\s+as|meaning)[^)]+\)",
                    r"\b" + re.escape(term) + r",?\s*(?:which\s+)?means?\b",
                    r"\b" + re.escape(term) + r",?\s*meaning\b",
                    r"\b" + re.escape(term) + r"\s*[:—\-]\s*[^.?!]+",
                )
                for cue in explanation_cues:
                    if re.search(cue, all_card_text):
                        is_defined = True
                        break

            if not is_defined:
                violations.append(
                    RuleViolation(
                        rule_name=RULE_PLAIN_LANGUAGE,
                        message=(
                            f"Industry jargon term '{term}' is used without "
                            "an accompanying plain-language explanation on the card."
                        ),
                        field="plain_language",
                        details={"jargon_term": term},
                    )
                )

    passed = len(violations) == 0
    if not passed:
        record_rule_failure(RULE_PLAIN_LANGUAGE)
    return RuleResult(
        passed=passed,
        rule_name=RULE_PLAIN_LANGUAGE,
        message=(
            "Plain language and jargon requirements verified."
            if passed
            else "Readability or unexplained jargon violations detected."
        ),
        violations=violations,
    )


# ==============================================================================
# RULE 6: Phone-Friendly Length
# ==============================================================================
def verify_phone_friendly_length(
    proposal: ClauseProposal,
    context: EvaluationContext,
    limits: PhoneLimits | None = None,
) -> RuleResult:
    """Verify that card sections respect character length ceilings for phone screens.

    Args:
        proposal: Model proposal under evaluation.
        context: Request evaluation context.
        limits: Optional phone length ceilings (defaults to standard PhoneLimits).

    Returns:
        RuleResult with status and length ceiling violations.
    """
    if limits is None:
        limits = PhoneLimits()

    violations: list[RuleViolation] = []

    # Title / Headline: max 45 chars
    if len(proposal.title) > limits.max_title_len:
        violations.append(
            RuleViolation(
                rule_name=RULE_PHONE_FRIENDLY_LENGTH,
                message=(
                    f"Title length ({len(proposal.title)} chars) exceeds "
                    f"limit of {limits.max_title_len} chars."
                ),
                field="title",
                details={"length": len(proposal.title), "max_length": limits.max_title_len},
            )
        )

    # Plain language: max 200 chars
    if len(proposal.plain_language) > limits.max_plain_language_len:
        violations.append(
            RuleViolation(
                rule_name=RULE_PHONE_FRIENDLY_LENGTH,
                message=(
                    f"plain_language length ({len(proposal.plain_language)} chars) "
                    f"exceeds limit of {limits.max_plain_language_len} chars."
                ),
                field="plain_language",
                details={
                    "length": len(proposal.plain_language),
                    "max_length": limits.max_plain_language_len,
                },
            )
        )

    # Why it matters: max 280 chars
    if len(proposal.why_it_matters) > limits.max_why_it_matters_len:
        violations.append(
            RuleViolation(
                rule_name=RULE_PHONE_FRIENDLY_LENGTH,
                message=(
                    f"why_it_matters length ({len(proposal.why_it_matters)} chars) "
                    f"exceeds limit of {limits.max_why_it_matters_len} chars."
                ),
                field="why_it_matters",
                details={
                    "length": len(proposal.why_it_matters),
                    "max_length": limits.max_why_it_matters_len,
                },
            )
        )

    # Comparison note: max 280 chars
    if len(proposal.comparison_note) > limits.max_comparison_note_len:
        violations.append(
            RuleViolation(
                rule_name=RULE_PHONE_FRIENDLY_LENGTH,
                message=(
                    f"comparison_note length ({len(proposal.comparison_note)} chars) "
                    f"exceeds limit of {limits.max_comparison_note_len} chars."
                ),
                field="comparison_note",
                details={
                    "length": len(proposal.comparison_note),
                    "max_length": limits.max_comparison_note_len,
                },
            )
        )

    # Each question: max 120 chars
    for idx, q in enumerate(proposal.questions):
        if len(q) > limits.max_question_len:
            violations.append(
                RuleViolation(
                    rule_name=RULE_PHONE_FRIENDLY_LENGTH,
                    message=(
                        f"Question {idx + 1} length ({len(q)} chars) "
                        f"exceeds limit of {limits.max_question_len} chars."
                    ),
                    field=f"questions[{idx}]",
                    details={"length": len(q), "max_length": limits.max_question_len},
                )
            )

    passed = len(violations) == 0
    if not passed:
        record_rule_failure(RULE_PHONE_FRIENDLY_LENGTH)
    return RuleResult(
        passed=passed,
        rule_name=RULE_PHONE_FRIENDLY_LENGTH,
        message=(
            "All fields fit within phone display limits."
            if passed
            else "Field length exceeds phone limits."
        ),
        violations=violations,
    )


# ==============================================================================
# RULE 7: Usable Questions
# ==============================================================================
def verify_usable_questions(proposal: ClauseProposal, context: EvaluationContext) -> RuleResult:
    """Verify that suggested questions are specific, neutral, actionable, and end with '?'.

    Rejects vague boilerplate questions ('What does this mean?', 'Is this good?').
    Questions must address the clause directly and propose or ask about a specific
    term, cap, definition, or timeframe.

    Args:
        proposal: Model proposal under evaluation.
        context: Request evaluation context.

    Returns:
        RuleResult with status and question usability violations.
    """
    violations: list[RuleViolation] = []

    # Maximum 3 questions allowed per card
    if len(proposal.questions) > 3:
        violations.append(
            RuleViolation(
                rule_name=RULE_USABLE_QUESTIONS,
                message=f"Too many questions ({len(proposal.questions)}); maximum is 3 per card.",
                field="questions",
                details={"question_count": len(proposal.questions)},
            )
        )

    for idx, q in enumerate(proposal.questions):
        trimmed = q.strip()

        # 1. Must end with '?'
        if not trimmed.endswith("?"):
            violations.append(
                RuleViolation(
                    rule_name=RULE_USABLE_QUESTIONS,
                    message=f"Question {idx + 1} does not end with '?': '{q}'",
                    field=f"questions[{idx}]",
                    details={"question": q},
                )
            )

        # 2. Minimum length to ensure specificity
        if len(trimmed) < 15:
            violations.append(
                RuleViolation(
                    rule_name=RULE_USABLE_QUESTIONS,
                    message=f"Question {idx + 1} is too brief to be actionable: '{q}'",
                    field=f"questions[{idx}]",
                    details={"question": q},
                )
            )

        # 3. Check for vague boilerplate questions
        for pattern in VAGUE_QUESTION_PATTERNS:
            if pattern.search(trimmed):
                violations.append(
                    RuleViolation(
                        rule_name=RULE_USABLE_QUESTIONS,
                        message=(
                            f"Question {idx + 1} is too vague ('{q}'). "
                            "Questions must ask for a specific change or concrete "
                            "term clarification."
                        ),
                        field=f"questions[{idx}]",
                        details={"question": q},
                    )
                )
                break

    passed = len(violations) == 0
    if not passed:
        record_rule_failure(RULE_USABLE_QUESTIONS)
    return RuleResult(
        passed=passed,
        rule_name=RULE_USABLE_QUESTIONS,
        message="Questions verified as actionable." if passed else "Question usability violations.",
        violations=violations,
    )


# ==============================================================================
# RULE 8: Comparable Money
# ==============================================================================
def verify_comparable_money(proposal: ClauseProposal, context: EvaluationContext) -> RuleResult:
    """Verify that both sides of a monetary comparison explicitly specify gross or net.

    If either side lacks a basis, or if bases are incompatible (e.g. comparing net to gross
    without reconciliation), returns failure triggering a fallback to 'cannot_compare'.

    Args:
        proposal: Model proposal under evaluation.
        context: Request evaluation context.

    Returns:
        RuleResult with status and money comparability violations.
    """
    violations: list[RuleViolation] = []

    # Check if a money comparison is attempted
    comparison = proposal.money_comparison
    inputs = proposal.money_inputs

    if comparison is not None:
        c_basis = comparison.contract_basis.lower().strip() if comparison.contract_basis else None
        r_basis = comparison.reference_basis.lower().strip() if comparison.reference_basis else None

        valid_bases = {"gross", "net"}

        if c_basis not in valid_bases:
            violations.append(
                RuleViolation(
                    rule_name=RULE_COMPARABLE_MONEY,
                    message=(
                        f"Contract monetary basis '{c_basis}' must be explicitly 'gross' or 'net'."
                    ),
                    field="money_comparison.contract_basis",
                    details={"contract_basis": c_basis},
                )
            )

        if r_basis not in valid_bases:
            violations.append(
                RuleViolation(
                    rule_name=RULE_COMPARABLE_MONEY,
                    message=(
                        f"Reference monetary basis '{r_basis}' must be explicitly 'gross' or 'net'."
                    ),
                    field="money_comparison.reference_basis",
                    details={"reference_basis": r_basis},
                )
            )

        if c_basis in valid_bases and r_basis in valid_bases and c_basis != r_basis:
            violations.append(
                RuleViolation(
                    rule_name=RULE_COMPARABLE_MONEY,
                    message=(
                        f"Incompatible monetary bases: contract is '{c_basis}' "
                        f"while reference standard is '{r_basis}'. Cannot compare directly."
                    ),
                    field="money_comparison",
                    details={"contract_basis": c_basis, "reference_basis": r_basis},
                )
            )

    elif inputs is not None and inputs.rate is not None:
        # If rate is provided in inputs, basis must be explicitly gross or net
        basis = inputs.basis.lower().strip() if inputs.basis else None
        if basis not in {"gross", "net"}:
            violations.append(
                RuleViolation(
                    rule_name=RULE_COMPARABLE_MONEY,
                    message=(f"Money inputs basis '{basis}' must be explicitly 'gross' or 'net'."),
                    field="money_inputs.basis",
                    details={"basis": basis},
                )
            )

    passed = len(violations) == 0
    if not passed:
        record_rule_failure(RULE_COMPARABLE_MONEY)
    return RuleResult(
        passed=passed,
        rule_name=RULE_COMPARABLE_MONEY,
        message=(
            "Money bases verified as comparable."
            if passed
            else "Money bases incompatible or unspecified."
        ),
        violations=violations,
    )


# ==============================================================================
# PROPOSAL PARSER HELPER
# ==============================================================================
def parse_proposal(data: ClauseProposal | dict[str, Any]) -> ClauseProposal:
    """Parse a ClauseProposal dataclass or dictionary into a normalized ClauseProposal.

    Supports aliases:
        'headline' -> 'title'
        'what_it_says' -> 'plain_language'
        'what_it_means' -> 'why_it_matters'
        'ask_them' -> 'questions'

    Args:
        data: Proposal object or dictionary.

    Returns:
        Standardized ClauseProposal instance.
    """
    if isinstance(data, ClauseProposal):
        return data

    clause_id = str(data.get("clause_id", ""))
    title = str(data.get("title") or data.get("headline") or "")
    key_quote = str(data.get("key_quote") or "")
    plain_language = str(data.get("plain_language") or data.get("what_it_says") or "")
    why_it_matters = str(data.get("why_it_matters") or data.get("what_it_means") or "")
    comparison_note = str(data.get("comparison_note") or "")

    raw_questions = data.get("questions") or data.get("ask_them") or []
    if isinstance(raw_questions, str):
        questions = [raw_questions]
    elif isinstance(raw_questions, list):
        questions = [str(q) for q in raw_questions]
    else:
        questions = []

    matched_pattern_id = data.get("matched_pattern_id")
    implication = data.get("implication")
    affects = data.get("affects")

    # Evidence citations
    raw_evidence = data.get("evidence", [])
    evidence_list: list[EvidenceCitation] = []
    for item in raw_evidence:
        if isinstance(item, EvidenceCitation):
            evidence_list.append(item)
        elif isinstance(item, dict):
            evidence_list.append(
                EvidenceCitation(
                    chunk_id=str(item.get("chunk_id", "")),
                    quote=str(item.get("quote", "")),
                    source_title=item.get("source_title"),
                )
            )

    linked_clauses = [str(x) for x in data.get("linked_clauses", [])]

    # Money inputs
    money_inputs: MoneyExampleInputs | None = None
    raw_inputs = data.get("money_inputs") or data.get("money_example_inputs")
    if isinstance(raw_inputs, MoneyExampleInputs):
        money_inputs = raw_inputs
    elif isinstance(raw_inputs, dict):
        money_inputs = MoneyExampleInputs(
            rate=raw_inputs.get("rate"),
            basis=raw_inputs.get("basis"),
            deductions=list(raw_inputs.get("deductions", [])),
            quote=raw_inputs.get("quote"),
        )

    # Money comparison
    money_comparison: MoneyComparison | None = None
    raw_comp = data.get("money_comparison")
    if isinstance(raw_comp, MoneyComparison):
        money_comparison = raw_comp
    elif isinstance(raw_comp, dict):
        money_comparison = MoneyComparison(
            contract_basis=raw_comp.get("contract_basis"),
            reference_basis=raw_comp.get("reference_basis"),
            contract_rate=raw_comp.get("contract_rate"),
            reference_rate=raw_comp.get("reference_rate"),
        )

    jargon_definitions = dict(data.get("jargon_definitions", {}))
    illustrative_examples = [str(x) for x in data.get("illustrative_examples", [])]

    return ClauseProposal(
        clause_id=clause_id,
        title=title,
        key_quote=key_quote,
        plain_language=plain_language,
        why_it_matters=why_it_matters,
        comparison_note=comparison_note,
        questions=questions,
        matched_pattern_id=matched_pattern_id,
        implication=implication,
        affects=affects,
        evidence=evidence_list,
        linked_clauses=linked_clauses,
        money_inputs=money_inputs,
        money_comparison=money_comparison,
        jargon_definitions=jargon_definitions,
        illustrative_examples=illustrative_examples,
    )


# ==============================================================================
# SAFE FALLBACK CARD GENERATOR
# ==============================================================================
def get_safe_fallback_card(
    clause_id: str,
    clause_text: str,
    reason: str,
) -> ClauseProposal:
    """Generate a safe, neutral fallback card when verification cannot be satisfied.

    Always assigned label 'cannot_compare' (⚪ Couldn't compare).
    Never falls back to 'typical' or 'matches standard'.

    Args:
        clause_id: Identifier of the unverified clause.
        clause_text: Original text of the clause.
        reason: Plain-language diagnostic explanation of why verification failed.

    Returns:
        Safe ClauseProposal with 'cannot_compare' semantics.
    """
    key_quote = clause_text.strip()
    if len(key_quote) > 100:
        key_quote = key_quote[:100].strip()

    return ClauseProposal(
        clause_id=clause_id,
        title="Requires Advisor Review",
        key_quote=key_quote,
        plain_language="Mbiu could not verify this comparison against reviewed standards.",
        why_it_matters=(
            "This clause could contain terms that require human review "
            "with a legal advisor or trusted manager."
        ),
        comparison_note="Automated comparison unavailable.",
        questions=["Could you clarify the specific intent and scope of this clause?"],
        implication="unclear",
        affects="other",
    )


# ==============================================================================
# DETERMINISTIC LABEL ASSIGNMENT
# ==============================================================================
def assign_deterministic_label(
    proposal: ClauseProposal,
    evidence_count: int,
) -> str:
    """Assign label deterministically based on verified evidence and implications.

    Invariants:
        Matches standard -> typical (🔵 Typical)
        Not in standard, no implication -> unusual (🟡 Unusual)
        Not in standard, with implication / high impact deviation -> worth_asking_about (🟠)
        Zero evidence or unverified -> cannot_compare (⚪ Couldn't compare)

    Args:
        proposal: Verified model proposal.
        evidence_count: Number of verified reference chunks supporting proposal.

    Returns:
        One of the four non-negotiable labels.
    """
    if evidence_count == 0:
        return LABEL_CANNOT_COMPARE

    implication = (proposal.implication or "none").lower()

    if implication in ("major", "minor"):
        return LABEL_WORTH_ASKING_ABOUT
    elif implication == "unclear":
        return LABEL_UNUSUAL
    elif proposal.matched_pattern_id:
        return LABEL_TYPICAL
    else:
        return LABEL_UNUSUAL


# ==============================================================================
# MAIN VERIFICATION FUNCTION
# ==============================================================================
def verify_proposal(
    proposal: ClauseProposal | dict[str, Any],
    context: EvaluationContext,
    max_grade_level: float = 9.0,
    limits: PhoneLimits | None = None,
) -> VerificationResult:
    """Execute all eight verification rules against a candidate clause proposal.

    Args:
        proposal: Proposal object or raw dictionary from model output.
        context: Request evaluation context.
        max_grade_level: Readability grade ceiling (default 9.0).
        limits: Optional phone length ceilings.

    Returns:
        VerificationResult with overall pass/fail status and granular details.
    """
    norm_proposal = parse_proposal(proposal)

    rule_checks: list[tuple[str, RuleResult]] = [
        (RULE_VERBATIM_QUOTES, verify_verbatim_quotes(norm_proposal, context)),
        (RULE_GROUNDED_IDS, verify_grounded_ids(norm_proposal, context)),
        (RULE_GROUNDED_NUMBERS, verify_grounded_numbers(norm_proposal, context)),
        (RULE_NO_LEGAL_CONCLUSIONS, verify_no_legal_conclusions(norm_proposal, context)),
        (
            RULE_PLAIN_LANGUAGE,
            verify_plain_language(norm_proposal, context, max_grade_level=max_grade_level),
        ),
        (
            RULE_PHONE_FRIENDLY_LENGTH,
            verify_phone_friendly_length(norm_proposal, context, limits=limits),
        ),
        (RULE_USABLE_QUESTIONS, verify_usable_questions(norm_proposal, context)),
        (RULE_COMPARABLE_MONEY, verify_comparable_money(norm_proposal, context)),
    ]

    rule_results: dict[str, RuleResult] = {}
    all_violations: list[RuleViolation] = []
    overall_passed = True

    for name, res in rule_checks:
        rule_results[name] = res
        if not res.passed:
            overall_passed = False
            all_violations.extend(res.violations)

    if overall_passed:
        label = assign_deterministic_label(norm_proposal, len(norm_proposal.evidence))
        return VerificationResult(
            passed=True,
            violations=[],
            rule_results=rule_results,
            verified_proposal=norm_proposal,
            assigned_label=label,
        )

    return VerificationResult(
        passed=False,
        violations=all_violations,
        rule_results=rule_results,
        verified_proposal=None,
        assigned_label=None,
    )


# ==============================================================================
# REPAIR FEEDBACK GENERATOR
# ==============================================================================
def generate_repair_feedback(result: VerificationResult) -> VerificationFeedback:
    """Generate structured feedback instructing the model how to repair violations.

    Names failed rules specifically and provides actionable repair guidance.

    Args:
        result: Failed VerificationResult.

    Returns:
        VerificationFeedback with failed rule names and repair prompt.
    """
    failed_rules = [
        rule_name for rule_name, rule_res in result.rule_results.items() if not rule_res.passed
    ]

    lines: list[str] = [
        "Your proposal failed verification on the following rules: "
        + ", ".join(failed_rules)
        + ".",
        "Please fix the following issues and return the corrected JSON proposal:",
    ]

    for idx, v in enumerate(result.violations, 1):
        field_str = f" in '{v.field}'" if v.field else ""
        lines.append(f"{idx}. [{v.rule_name}]{field_str}: {v.message}")

    lines.append(
        "Ensure all quotes are verbatim substrings, IDs belong to this request, "
        "numbers are grounded, legal advice/conclusion words are removed, "
        "and questions are neutral and actionable ending with '?'."
    )

    prompt = "\n".join(lines)
    return VerificationFeedback(
        failed_rules=failed_rules,
        violations=result.violations,
        repair_instructions=prompt,
    )


# ==============================================================================
# REPAIR & FALLBACK WORKFLOW
# ==============================================================================
def repair_and_verify(
    initial_proposal: ClauseProposal | dict[str, Any],
    context: EvaluationContext,
    repair_fn: (
        Callable[[ClauseProposal, VerificationFeedback], ClauseProposal | dict[str, Any]] | None
    ) = None,
    max_grade_level: float = 9.0,
    limits: PhoneLimits | None = None,
) -> VerificationResult:
    """Orchestrate verification with one repair attempt and deterministic fallback.

    Workflow:
        1. Run verify_proposal on initial proposal.
        2. If passed, return verified proposal.
        3. If failed and repair_fn is supplied:
           - Generate structured feedback naming failed rules.
           - Invoke repair_fn exactly once.
           - Re-verify repaired proposal.
           - If repaired proposal passes, return verified proposal.
        4. If verification fails after repair (or no repair_fn provided):
           - Fall back deterministically to 'cannot_compare' (⚪ Couldn't compare).
           - NEVER fall back to 'matches_standard'.
           - Return safe fallback card.

    Args:
        initial_proposal: First draft proposal from model.
        context: Request evaluation context.
        repair_fn: Optional callable executing one repair attempt with feedback.
        max_grade_level: Readability grade ceiling.
        limits: Optional phone length ceilings.

    Returns:
        Final VerificationResult (either verified proposal or cannot_compare fallback).
    """
    first_result = verify_proposal(
        initial_proposal,
        context,
        max_grade_level=max_grade_level,
        limits=limits,
    )

    if first_result.passed:
        return first_result

    # One repair attempt permitted
    if repair_fn is not None:
        feedback = generate_repair_feedback(first_result)
        repaired_raw = repair_fn(parse_proposal(initial_proposal), feedback)
        second_result = verify_proposal(
            repaired_raw,
            context,
            max_grade_level=max_grade_level,
            limits=limits,
        )
        if second_result.passed:
            return second_result

        failed_summary = ", ".join(feedback.failed_rules)
        fallback_card = get_safe_fallback_card(
            clause_id=context.clause_id,
            clause_text=context.clause_text,
            reason=f"Verification failed after repair attempt: {failed_summary}",
        )
        return VerificationResult(
            passed=False,
            violations=second_result.violations,
            rule_results=second_result.rule_results,
            verified_proposal=fallback_card,
            assigned_label=LABEL_CANNOT_COMPARE,
            fallback_reason=f"Verification failed after repair attempt ({failed_summary}).",
        )

    # No repair function provided; immediate deterministic fallback to cannot_compare
    failed_summary = ", ".join(
        rule for rule, res in first_result.rule_results.items() if not res.passed
    )
    fallback_card = get_safe_fallback_card(
        clause_id=context.clause_id,
        clause_text=context.clause_text,
        reason=f"Verification failed: {failed_summary}",
    )
    return VerificationResult(
        passed=False,
        violations=first_result.violations,
        rule_results=first_result.rule_results,
        verified_proposal=fallback_card,
        assigned_label=LABEL_CANNOT_COMPARE,
        fallback_reason=f"Verification failed without repair ({failed_summary}).",
    )
