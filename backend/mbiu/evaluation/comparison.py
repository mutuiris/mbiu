"""Comparison engine, reverse checks, and impact inputs for contract evaluation.

Evaluates user contract clauses against reviewed standard template chunks:
- Evidence Comparison: Compares clauses against retrieved reference template chunks.
- Contract Type Standard Guard: When no reviewed standard exists for the contract type,
  emits 'cannot_compare' (⚪ Couldn't compare) with the kind message:
  "Mbiu doesn't have a reviewed standard for this kind of contract yet, so it can
  explain these clauses but not compare them."
- Template Disagreements: Detects and formats evidence differences across standard templates:
  "Standard templates differ here: one gives X, another Y. Your contract gives Z."
- Impact Inputs: Extracts rate, money_basis, and deductions with exact quotes for frontend
  shillings calculations. The model NEVER does arithmetic in shillings.
- Fairer Wording: Extracts the verbatim standard template clause, unchanged.
- Reverse Check: Identifies protective clauses in reference templates that the contract
  completely lacks (audit rights, accounting statement frequency, termination on non-payment,
  written approvals), emitting 'missing_from_contract' outcomes.
- Verification Guard: All model proposals are validated by MB-17 repair_and_verify.

Zero Contract Storage Invariant:
Operates purely in memory. No contract text or evaluated cards are ever written to disk,
database, temp files, or logs.
"""

from __future__ import annotations

import dataclasses as dc
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from mbiu.corpus.loader import CorpusSnapshot
from mbiu.evaluation.budgets import (
    AFFECTS_MONEY,
    AFFECTS_OWNERSHIP,
    AFFECTS_TIME,
    classify_clause_impact,
)
from mbiu.evaluation.verify import (
    LABEL_CANNOT_COMPARE,
    LABEL_TYPICAL,
    LABEL_UNUSUAL,
    LABEL_WORTH_ASKING_ABOUT,
    ClauseProposal,
    EvaluationContext,
    EvidenceCitation,
    MoneyExampleInputs,
    normalize_whitespace,
    repair_and_verify,
)

# ==============================================================================
# COMPARISON OUTCOME CONSTANTS
# ==============================================================================

OUTCOME_MATCHES_STANDARD = "matches_standard"
OUTCOME_BETTER_FOR_YOU = "better_for_you"
OUTCOME_WORSE_FOR_YOU = "worse_for_you"
OUTCOME_NOT_IN_STANDARD = "not_in_standard"
OUTCOME_MISSING_FROM_CONTRACT = "missing_from_contract"
OUTCOME_CANNOT_COMPARE = "cannot_compare"

VALID_OUTCOMES = frozenset(
    {
        OUTCOME_MATCHES_STANDARD,
        OUTCOME_BETTER_FOR_YOU,
        OUTCOME_WORSE_FOR_YOU,
        OUTCOME_NOT_IN_STANDARD,
        OUTCOME_MISSING_FROM_CONTRACT,
        OUTCOME_CANNOT_COMPARE,
    }
)

# Status Constants
STATUS_EVALUATED = "evaluated"
STATUS_CANNOT_COMPARE = "cannot_compare"
STATUS_EVALUATION_FAILED = "evaluation_failed"
STATUS_NOT_CHECKED = "not_checked"

# Standard message when contract type has no reviewed standard
NO_STANDARD_FOR_TYPE_MESSAGE = (
    "Mbiu doesn't have a reviewed standard for this kind of contract yet, "
    "so it can explain these clauses but not compare them."
)


# ==============================================================================
# CLAUSE EVALUATION RESULT CARD
# ==============================================================================


@dataclass
class ClauseEvaluationResult:
    """Evaluated result card for a single contract clause.

    Attributes:
        clause_id: Unique hierarchical clause ID.
        pages: List of 1-indexed page numbers spanned by the clause.
        original_text: Exact verbatim text of the user clause.
        status: Evaluation status ('evaluated', 'cannot_compare', 'evaluation_failed',
            'not_checked').
        comparison: Comparison outcome ('matches_standard', 'better_for_you', 'worse_for_you',
            'not_in_standard', 'missing_from_contract', 'cannot_compare').
        headline: Concise plain-language headline (<= 45 chars).
        what_it_says: Plain language summary of terms (<= 200 chars).
        what_it_means: Practical consequences phrased with 'may' or 'could' (<= 280 chars).
        comparison_note: Contextual note comparing against standard templates (<= 280 chars).
        impact_inputs: Inputs for frontend shillings calculation (never model arithmetic).
        money_basis: Operative base ('gross' or 'net') if financial clause.
        linked_clauses: List of cross-referenced or overriding clause IDs.
        fairer_wording: Verbatim standard template clause, unchanged.
        ask_them: List of suggested neutral, actionable questions ending in '?'.
        standard_template_id: ID of primary reference template chunk compared against.
        standard_excerpt: Exact quote from primary reference template chunk.
        evidence_ids: List of referenced chunk IDs.
        evidence_quote: Exact primary quote supporting the comparison note.
        evidence: Full citations for all referenced template chunks.
        provider: AI provider used ('gemini' or 'openai').
        model_version: Active model revision tag.
        label: Label ('typical', 'unusual', 'worth_asking_about', 'cannot_compare').
        clause_number: Numbering as printed in contract ('7.2') or None.
        affects: Affected area ('money', 'ownership', 'time', 'freedom_to_work', 'other').
        not_checked_reason: Explanation if status is 'not_checked'.
    """

    clause_id: str
    pages: list[int]
    original_text: str
    status: str
    comparison: str
    headline: str
    what_it_says: str
    what_it_means: str
    comparison_note: str
    impact_inputs: MoneyExampleInputs | None = None
    money_basis: str | None = None
    linked_clauses: list[str] = dc.field(default_factory=list)
    fairer_wording: str | None = None
    ask_them: list[str] = dc.field(default_factory=list)
    standard_template_id: str | None = None
    standard_excerpt: str | None = None
    evidence_ids: list[str] = dc.field(default_factory=list)
    evidence_quote: str | None = None
    evidence: list[EvidenceCitation] = dc.field(default_factory=list)
    provider: str = "gemini"
    model_version: str = "gemini-3.8-flash"
    label: str = LABEL_CANNOT_COMPARE
    clause_number: str | None = None
    affects: str | None = None
    not_checked_reason: str | None = None


# ==============================================================================
# TEMPLATE DISAGREEMENT FORMATTER
# ==============================================================================


def format_template_disagreement(
    first_standard: str,
    second_standard: str,
    contract_term: str,
) -> str:
    """Format clear evidence differences when retrieved standard templates differ.

    Required standard format:
    "Standard templates differ here: one gives X, another Y. Your contract gives Z."

    Args:
        first_standard: Value or excerpt from first template standard (e.g. '30 days').
        second_standard: Value or excerpt from second template standard (e.g. '60 days').
        contract_term: Value or excerpt in the artist's contract (e.g. '90 days').

    Returns:
        Formatted plain-language comparison note.
    """
    return (
        f"Standard templates differ here: one gives {first_standard.strip()}, "
        f"another {second_standard.strip()}. Your contract gives {contract_term.strip()}."
    )


# ==============================================================================
# IMPACT INPUTS VALIDATION (Shillings calculation inputs)
# ==============================================================================


def validate_impact_inputs(
    inputs: MoneyExampleInputs | dict[str, Any] | None,
    clause_text: str,
) -> MoneyExampleInputs | None:
    """Validate impact inputs for code-executed shillings calculation.

    Rules:
    - Model NEVER does arithmetic in shillings.
    - Rate and basis must be present.
    - If a quote is provided, it must be an exact substring of the clause text.
    - Every listed deduction must appear in the clause text.

    Args:
        inputs: Candidate MoneyExampleInputs or raw dict.
        clause_text: Verbatim clause text.

    Returns:
        Validated MoneyExampleInputs object, or None if invalid.
    """
    if inputs is None:
        return None

    if isinstance(inputs, dict):
        rate = inputs.get("rate")
        basis = inputs.get("basis") or inputs.get("money_basis")
        deductions = list(inputs.get("deductions") or [])
        quote = inputs.get("quote")
    else:
        rate = inputs.rate
        basis = inputs.basis
        deductions = list(inputs.deductions)
        quote = inputs.quote

    norm_clause = normalize_whitespace(clause_text)

    # Validate quote if provided
    if quote:
        norm_quote = normalize_whitespace(quote)
        if norm_quote not in norm_clause:
            return None

    # Validate deductions are grounded in the clause text
    deductions = [
        d
        for d in deductions
        if normalize_whitespace(str(d)) and normalize_whitespace(str(d)) in norm_clause
    ]

    # Normalize basis
    norm_basis = str(basis).lower().strip() if basis else None
    if norm_basis not in ("gross", "net"):
        norm_basis = None

    return MoneyExampleInputs(
        rate=rate,
        basis=norm_basis,
        deductions=deductions,
        quote=quote,
    )


# ==============================================================================
# FAIRER WORDING EXTRACTION
# ==============================================================================


def extract_fairer_wording(
    candidate_wording: str | None,
    reference_chunks: dict[str, str],
) -> str | None:
    """Verify that fairer_wording provides the exact template clause, unchanged.

    The model must never paraphrase, rewrite, or summarize standard wording.
    If provided, fairer_wording MUST be an exact verbatim substring of one
    of the retrieved reference standard template chunks.

    Args:
        candidate_wording: Candidate fairer wording string proposed by model.
        reference_chunks: Dict mapping chunk_id to reference template text.

    Returns:
        Verbatim fairer wording string if verified against reference chunks, else None.
    """
    if not candidate_wording:
        return None

    norm_candidate = normalize_whitespace(candidate_wording)
    if not norm_candidate:
        return None

    for _chunk_id, chunk_text in reference_chunks.items():
        if norm_candidate in normalize_whitespace(chunk_text):
            return candidate_wording.strip()

    return None


# ==============================================================================
# SAFE RESULT CONSTRUCTORS
# ==============================================================================


def create_not_checked_result(
    clause_id: str,
    original_text: str,
    pages: list[int],
    reason: str,
    clause_number: str | None = None,
    section: str | None = None,
    title: str | None = None,
) -> ClauseEvaluationResult:
    """Create a ClauseEvaluationResult for a clause omitted due to budget exhaustion.

    Args:
        clause_id: Target clause ID.
        original_text: Clause text.
        pages: Page numbers spanned.
        reason: Plain artist-friendly explanation from EvaluationBudgetTracker.
        clause_number: Printed clause number if available.
        section: Section name.
        title: Clause title if available.

    Returns:
        ClauseEvaluationResult with status 'not_checked' and label 'cannot_compare'.
    """
    classification = classify_clause_impact(original_text, title=title, section=section)
    headline = (title or f"Clause {clause_id}").strip()
    if len(headline) > 45:
        headline = headline[:42] + "..."

    return ClauseEvaluationResult(
        clause_id=clause_id,
        pages=pages,
        original_text=original_text,
        status=STATUS_NOT_CHECKED,
        comparison=OUTCOME_CANNOT_COMPARE,
        headline=headline,
        what_it_says="This clause was not checked yet.",
        what_it_means="Mbiu checked higher-impact clauses first within the resource budget.",
        comparison_note=reason,
        label=LABEL_CANNOT_COMPARE,
        clause_number=clause_number,
        affects=classification.affects,
        not_checked_reason=reason,
    )


def create_no_reviewed_standard_result(
    clause_id: str,
    original_text: str,
    pages: list[int],
    contract_type: str,
    title: str | None = None,
    plain_language: str | None = None,
    why_it_matters: str | None = None,
    clause_number: str | None = None,
    section: str | None = None,
) -> ClauseEvaluationResult:
    """Create a ClauseEvaluationResult when the contract type has no reviewed standard.

    Explains the clause in plain language but emits cannot_compare for comparison.

    Args:
        clause_id: Target clause ID.
        original_text: Verbatim clause text.
        pages: Page numbers spanned.
        contract_type: Detected contract type (e.g. 'podcast_host').
        title: Optional title.
        plain_language: Optional plain language explanation of what it says.
        why_it_matters: Optional explanation of practical consequences.
        clause_number: Printed clause number.
        section: Section name.

    Returns:
        ClauseEvaluationResult with status 'cannot_compare' and standard notice.
    """
    classification = classify_clause_impact(original_text, title=title, section=section)
    headline = (title or f"Clause {clause_id}").strip()
    if len(headline) > 45:
        headline = headline[:42] + "..."

    what_it_says = plain_language or "This clause outlines terms for this agreement."
    if len(what_it_says) > 200:
        what_it_says = what_it_says[:197] + "..."

    what_it_means = (
        why_it_matters
        or "This clause may affect your responsibilities and rights under this agreement."
    )
    if len(what_it_means) > 280:
        what_it_means = what_it_means[:277] + "..."

    return ClauseEvaluationResult(
        clause_id=clause_id,
        pages=pages,
        original_text=original_text,
        status=STATUS_CANNOT_COMPARE,
        comparison=OUTCOME_CANNOT_COMPARE,
        headline=headline,
        what_it_says=what_it_says,
        what_it_means=what_it_means,
        comparison_note=NO_STANDARD_FOR_TYPE_MESSAGE,
        label=LABEL_CANNOT_COMPARE,
        clause_number=clause_number,
        affects=classification.affects,
        not_checked_reason=None,
    )


# ==============================================================================
# CORE CLAUSE EVALUATION ORCHESTRATOR
# ==============================================================================


def evaluate_clause_with_verification(
    proposal: ClauseProposal | dict[str, Any],
    context: EvaluationContext,
    pages: list[int],
    clause_number: str | None = None,
    contract_type_has_standard: bool = True,
    repair_fn: Callable[[ClauseProposal, Any], ClauseProposal | dict[str, Any]] | None = None,
    provider: str = "gemini",
    model_version: str = "gemini-3.8-flash",
) -> ClauseEvaluationResult:
    """Evaluate a candidate clause proposal through verification and standard rules.

    Orchestrates:
    1. Contract type standard check (emits cannot_compare if standard missing).
    2. MB-17 repair_and_verify execution.
    3. Fairer wording extraction (exact template clause, unchanged).
    4. Impact inputs validation for code-calculated shillings.
    5. Safe mapping into verified ClauseEvaluationResult.

    Args:
        proposal: Candidate ClauseProposal or dict produced by model.
        context: EvaluationContext with clause text, linked clauses, and reference chunks.
        pages: Page numbers spanned by target clause.
        clause_number: Printed numbering (e.g. '7.2') or None.
        contract_type_has_standard: True if reviewed standard exists for this contract type.
        repair_fn: Optional repair callable for one repair attempt on rule failure.
        provider: AI model provider ('gemini' or 'openai').
        model_version: Revision tag of active model.

    Returns:
        Verified ClauseEvaluationResult.
    """
    clause_id = context.clause_id
    clause_text = context.clause_text

    # Guard 1: Contract type has no reviewed standard
    if not contract_type_has_standard or not context.reference_chunks:
        title = (
            proposal.get("title")
            if isinstance(proposal, dict)
            else getattr(proposal, "title", None)
        )
        plain_lang = (
            proposal.get("plain_language")
            if isinstance(proposal, dict)
            else getattr(proposal, "plain_language", None)
        )
        why_matters = (
            proposal.get("why_it_matters")
            if isinstance(proposal, dict)
            else getattr(proposal, "why_it_matters", None)
        )
        return create_no_reviewed_standard_result(
            clause_id=clause_id,
            original_text=clause_text,
            pages=pages,
            contract_type="unknown",
            title=title,
            plain_language=plain_lang,
            why_it_matters=why_matters,
            clause_number=clause_number,
        )

    # Guard 2: Run MB-17 Verification Rules and Repair Orchestration
    verification_result = repair_and_verify(
        initial_proposal=proposal,
        context=context,
        repair_fn=repair_fn,
    )

    verified_prop = verification_result.verified_proposal
    if verified_prop is None:
        # Fallback card was generated inside verify.py
        verified_prop = ClauseProposal(
            clause_id=clause_id,
            title="Terms Under Review",
            key_quote=clause_text[:40],
            plain_language=(
                "This clause contains terms that could not be verified against reviewed standards."
            ),
            why_it_matters="You may wish to seek guidance on how this clause affects your career.",
            comparison_note=(
                "Verification could not confirm grounding against reviewed reference templates."
            ),
            questions=["Could we clarify the exact operational meaning of this clause?"],
        )

    # Determine comparison outcome
    if not verification_result.passed or verification_result.assigned_label == LABEL_CANNOT_COMPARE:
        outcome = OUTCOME_CANNOT_COMPARE
        status = STATUS_CANNOT_COMPARE
        label = LABEL_CANNOT_COMPARE
    elif verified_prop.matched_pattern_id:
        outcome = OUTCOME_MATCHES_STANDARD
        status = STATUS_EVALUATED
        label = verification_result.assigned_label or LABEL_TYPICAL
    elif verified_prop.implication in ("major", "minor"):
        outcome = OUTCOME_WORSE_FOR_YOU
        status = STATUS_EVALUATED
        label = verification_result.assigned_label or LABEL_WORTH_ASKING_ABOUT
    else:
        outcome = OUTCOME_NOT_IN_STANDARD
        status = STATUS_EVALUATED
        label = verification_result.assigned_label or LABEL_UNUSUAL

    # Fairer wording: exact template chunk substring, unchanged
    fairer_wording: str | None = None
    if verified_prop.evidence:
        primary_evidence = verified_prop.evidence[0]
        ref_text = context.reference_chunks.get(primary_evidence.chunk_id, "")
        if ref_text:
            fairer_wording = ref_text.strip()

    # Impact inputs validation for shillings calculation
    validated_impact_inputs = validate_impact_inputs(
        verified_prop.money_inputs, clause_text=clause_text
    )

    money_basis = (
        validated_impact_inputs.basis
        if validated_impact_inputs
        else (
            verified_prop.money_comparison.contract_basis
            if verified_prop.money_comparison
            else None
        )
    )

    evidence_ids = [e.chunk_id for e in verified_prop.evidence]
    evidence_quote = verified_prop.evidence[0].quote if verified_prop.evidence else None
    std_template_id = verified_prop.evidence[0].chunk_id if verified_prop.evidence else None
    std_excerpt = verified_prop.evidence[0].quote if verified_prop.evidence else None

    # Topic classification fallback for affects dimension
    classification = classify_clause_impact(clause_text, title=verified_prop.title)
    affects = verified_prop.affects or classification.affects

    return ClauseEvaluationResult(
        clause_id=clause_id,
        pages=pages,
        original_text=clause_text,
        status=status,
        comparison=outcome,
        headline=verified_prop.title,
        what_it_says=verified_prop.plain_language,
        what_it_means=verified_prop.why_it_matters,
        comparison_note=verified_prop.comparison_note,
        impact_inputs=validated_impact_inputs,
        money_basis=money_basis,
        linked_clauses=list(verified_prop.linked_clauses),
        fairer_wording=fairer_wording,
        ask_them=list(verified_prop.questions),
        standard_template_id=std_template_id,
        standard_excerpt=std_excerpt,
        evidence_ids=evidence_ids,
        evidence_quote=evidence_quote,
        evidence=list(verified_prop.evidence),
        provider=provider,
        model_version=model_version,
        label=label,
        clause_number=clause_number,
        affects=affects,
        not_checked_reason=None,
    )


# ==============================================================================
# REVERSE CHECK (Missing Protections)
# ==============================================================================


@dataclass(frozen=True)
class ProtectiveStandardPattern:
    """Standard protective pattern expected in reviewed music contract templates."""

    protection_id: str
    topic: str
    headline: str
    detection_keywords: tuple[str, ...]
    missing_what_it_says: str
    missing_what_it_means: str
    standard_comparison_note: str
    suggested_question: str
    template_fairer_wording: str
    affects: str


# Core standard protective clauses musicians need in music contracts
STANDARD_PROTECTIVE_PATTERNS: tuple[ProtectiveStandardPattern, ...] = (
    ProtectiveStandardPattern(
        protection_id="audit_rights",
        topic="audit",
        headline="No audit rights found",
        detection_keywords=(
            "audit",
            "inspect books",
            "examination of books",
            "accounting inspection",
        ),
        missing_what_it_says=(
            "We didn't find a clause giving you the right to inspect accounting records or "
            "royalty statements."
        ),
        missing_what_it_means=(
            "Without audit rights, you may not be able to independently verify whether royalty "
            "calculations and deductions are accurate."
        ),
        standard_comparison_note=(
            "Standard music agreements grant the artist an annual right to audit books and "
            "records upon reasonable written notice."
        ),
        suggested_question=(
            "Could we include a standard clause granting an annual right to inspect accounting "
            "books and records?"
        ),
        template_fairer_wording=(
            "The Artist shall have the right, once per calendar year upon thirty (30) days "
            "written notice, to inspect and audit the Company's books and records relating "
            "to royalty accounting."
        ),
        affects=AFFECTS_MONEY,
    ),
    ProtectiveStandardPattern(
        protection_id="accounting_frequency",
        topic="accounting_schedule",
        headline="No regular accounting schedule found",
        detection_keywords=(
            "semi-annually",
            "quarterly",
            "accounting period",
            "statement of account",
            "within 60 days",
            "within 90 days",
        ),
        missing_what_it_says=(
            "We didn't find a specific schedule for when royalty accounting statements and "
            "payments must be sent."
        ),
        missing_what_it_means=(
            "Without a fixed accounting schedule, payment dates could be delayed indefinitely "
            "without triggering a contractual breach."
        ),
        standard_comparison_note=(
            "Standard templates specify semi-annual or quarterly accounting statements delivered "
            "within 60 to 90 days following each accounting period."
        ),
        suggested_question=(
            "Can we add a clear schedule requiring accounting statements and "
            "payments semi-annually within 60 days?"
        ),
        template_fairer_wording=(
            "The Company shall render to the Artist semi-annual royalty statements together with "
            "payment of all sums due within sixty (60) days after each June 30 and December 31."
        ),
        affects=AFFECTS_MONEY,
    ),
    ProtectiveStandardPattern(
        protection_id="termination_on_breach",
        topic="termination_rights",
        headline="No artist termination right for non-payment",
        detection_keywords=(
            "artist may terminate",
            "artist shall have the right to terminate",
            "non-payment",
            "cure period",
            "material breach",
        ),
        missing_what_it_says=(
            "We didn't find a clause allowing you to terminate the contract if payments are not "
            "made or terms are breached."
        ),
        missing_what_it_means=(
            "Without an artist termination right, you could remain tied to the contract even if "
            "the other party fails to pay royalties."
        ),
        standard_comparison_note=(
            "Standard agreements permit the artist to terminate after 30 days written notice if "
            "a material breach or non-payment remains uncured."
        ),
        suggested_question=(
            "Can we specify that the artist may terminate upon 30 days written notice if payment "
            "default is not cured?"
        ),
        template_fairer_wording=(
            "The Artist may terminate this Agreement upon thirty (30) days written notice if the "
            "Company fails to make any payment due hereunder, provided such default is not cured "
            "within the notice period."
        ),
        affects=AFFECTS_TIME,
    ),
    ProtectiveStandardPattern(
        protection_id="written_approval_deductions",
        topic="deductions_approval",
        headline="No written approval required for deductions",
        detection_keywords=(
            "prior written approval",
            "written consent",
            "deduction cap",
            "approved in writing",
        ),
        missing_what_it_says=(
            "We didn't find a requirement for prior written approval before major recording or "
            "promotional expenses are deducted."
        ),
        missing_what_it_means=(
            "Without approval controls, extensive recoupable costs could reduce your net royalties "
            "to zero."
        ),
        standard_comparison_note=(
            "Standard templates require artist written consent for marketing or third-party "
            "expenses exceeding agreed caps."
        ),
        suggested_question=(
            "Could we require mutual written approval for any individual marketing or production "
            "deduction exceeding KES 50,000?"
        ),
        template_fairer_wording=(
            "No promotional or third-party expense exceeding agreed thresholds shall be "
            "recoupable without the Artist's prior written consent."
        ),
        affects=AFFECTS_MONEY,
    ),
    ProtectiveStandardPattern(
        protection_id="rights_reversion",
        topic="reversion",
        headline="No rights reversion clause found",
        detection_keywords=(
            "revert to artist",
            "reversion of rights",
            "rights shall revert",
            "re-assignment",
        ),
        missing_what_it_says=(
            "We didn't find a clause providing for the return of your recordings or publishing "
            "rights after recoupment or term expiration."
        ),
        missing_what_it_means=(
            "Without a reversion provision, the company may hold rights to your music indefinitely."
        ),
        standard_comparison_note=(
            "Standard creator-friendly agreements provide that rights revert to the artist within "
            "3 to 7 years after recoupment."
        ),
        suggested_question=(
            "Can we add a reversion clause so that rights revert to the artist 5 years after "
            "recoupment of initial production costs?"
        ),
        template_fairer_wording=(
            "All master recording rights granted herein shall revert to the Artist five (5) "
            "years following the full recoupment of all approved recording costs."
        ),
        affects=AFFECTS_OWNERSHIP,
    ),
)


def check_missing_protections(
    contract_clauses: Sequence[Any],
    contract_type_has_standard: bool = True,
    corpus_snapshot: CorpusSnapshot | None = None,
) -> list[ClauseEvaluationResult]:
    """Execute the Reverse Check to identify standard protections absent from the contract.

    Identifies standard protective clauses in matching reference templates that
    the contract completely lacks (audit rights, accounting frequency, termination
    on non-payment, written approvals, rights reversion).

    Emits outcomes with comparison='missing_from_contract' and label='worth_asking_about'
    (🟠 Worth asking about). Phrasing is always objective and cautious:
    "We didn't find" rather than "your contract lacks".

    Args:
        contract_clauses: List of clauses in the artist's contract.
        contract_type_has_standard: Whether a reviewed standard exists for this contract type.
        corpus_snapshot: Optional active corpus snapshot for reference chunk citations.

    Returns:
        List of ClauseEvaluationResult objects for each missing protection.
    """
    if not contract_type_has_standard or not contract_clauses:
        return []

    # Concatenate all clause texts to search for protective concepts
    full_text_lower = " ".join(getattr(c, "text", str(c)).lower() for c in contract_clauses)

    missing_results: list[ClauseEvaluationResult] = []

    for pattern in STANDARD_PROTECTIVE_PATTERNS:
        # Check if any detection keyword is present in the contract
        found = any(kw in full_text_lower for kw in pattern.detection_keywords)
        if not found:
            # Emits missing_from_contract outcome
            clause_id = f"missing_{pattern.protection_id}"

            # Look up corpus chunk if available
            evidence: list[EvidenceCitation] = []
            std_template_id: str | None = None
            if corpus_snapshot is not None:
                for chunk in corpus_snapshot.chunks:
                    if pattern.topic in chunk.topic.lower() or pattern.topic in chunk.text.lower():
                        std_template_id = chunk.chunk_id
                        evidence.append(
                            EvidenceCitation(
                                chunk_id=chunk.chunk_id,
                                quote=chunk.text[:80],
                                source_title=chunk.source_title,
                            )
                        )
                        break

            missing_card = ClauseEvaluationResult(
                clause_id=clause_id,
                pages=[],
                original_text="",
                status=STATUS_EVALUATED,
                comparison=OUTCOME_MISSING_FROM_CONTRACT,
                headline=pattern.headline,
                what_it_says=pattern.missing_what_it_says,
                what_it_means=pattern.missing_what_it_means,
                comparison_note=pattern.standard_comparison_note,
                fairer_wording=pattern.template_fairer_wording,
                ask_them=[pattern.suggested_question],
                standard_template_id=std_template_id,
                standard_excerpt=pattern.template_fairer_wording[:120],
                evidence=evidence,
                evidence_ids=[e.chunk_id for e in evidence],
                label=LABEL_WORTH_ASKING_ABOUT,
                affects=pattern.affects,
            )
            missing_results.append(missing_card)

    return missing_results
