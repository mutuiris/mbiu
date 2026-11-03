"""Views and streaming endpoints for contract clause evaluations.

Provides the stateless re-evaluation and retry endpoint:
POST /api/v1/clause-evaluations

Enforces Non-Negotiable Project Invariants:
1. Zero Contract Storage:
   All clause evaluations operate statelessly in memory. No contract text,
   clauses, results, or sessions are ever persisted to disk, database, temp files,
   or external logs.
2. Decisions From Reviewed Templates Only:
   Evaluations are grounded strictly against reviewed standard template chunks.
   If no standard exists for the contract type, emits 'cannot_compare' with
   the standard notice.
3. Model Output is a Proposal, Not a Result:
   All quotes are verified by code as exact substrings of the user's clause text.
   Labels strictly follow the four non-negotiable labels (typical, unusual,
   worth_asking_about, cannot_compare) with no green label.
4. Resuming Unfinished Clauses:
   Streams newline-delimited JSON events (progress, clause_result, clause_failed, done)
   allowing the browser to resend only the clauses it holds for failed or unchecked clauses.
"""

from __future__ import annotations

import dataclasses as dc
import json
import logging
from collections.abc import Generator, Sequence
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse

from mbiu.corpus.loader import CorpusSnapshot, get_active_corpus_snapshot
from mbiu.documents.segment import Clause
from mbiu.evaluation.budgets import (
    AFFECTS_MONEY,
    classify_clause_impact,
)
from mbiu.evaluation.comparison import (
    NO_STANDARD_FOR_TYPE_MESSAGE,
    ClauseEvaluationResult,
    check_missing_protections,
    create_no_reviewed_standard_result,
    evaluate_clause_with_verification,
)
from mbiu.evaluation.summary import generate_evaluation_summary
from mbiu.evaluation.verify import (
    ClauseProposal,
    EvaluationContext,
    EvidenceCitation,
    MoneyExampleInputs,
)

logger = logging.getLogger(__name__)

# Recognized contract types that have reviewed standard templates in Mbiu
RECOGNIZED_MUSIC_CONTRACT_TYPES = frozenset(
    {
        "recording",
        "management",
        "publishing",
        "producer",
        "live_performance",
        "sync",
        "distribution",
        "general",
    }
)


def _check_contract_type_has_standard(
    contract_type: str | None,
    snapshot: CorpusSnapshot | None,
) -> bool:
    """Determine whether a reviewed standard exists for the specified contract type.

    Args:
        contract_type: User-specified or detected contract type name.
        snapshot: Active in-memory corpus snapshot, if loaded.

    Returns:
        True if standard templates exist for this contract type, False otherwise.
    """
    if contract_type is None:
        return True

    norm_type = contract_type.strip().lower()
    if norm_type in ("unknown", "podcast_host", "employment", "software", "unreviewed"):
        return False

    if snapshot is not None and snapshot.chunks:
        # Check if snapshot contains chunks for this contract type
        has_chunk = any(c.contract_type.strip().lower() == norm_type for c in snapshot.chunks)
        if has_chunk:
            return True

    return norm_type in RECOGNIZED_MUSIC_CONTRACT_TYPES


def _find_relevant_reference_chunks(
    clause_text: str,
    topic: str,
    contract_type: str | None,
    snapshot: CorpusSnapshot | None,
    max_chunks: int = 3,
) -> dict[str, str]:
    """Find relevant reference template chunks from the active in-memory corpus snapshot.

    Args:
        clause_text: Text of the contract clause.
        topic: Classified topic (e.g. 'money', 'ownership', 'term').
        contract_type: Optional contract type filter.
        snapshot: Active in-memory corpus snapshot.
        max_chunks: Maximum number of reference chunks to return.

    Returns:
        Mapping of chunk_id to reference template text.
    """
    if snapshot is None or not snapshot.chunks:
        return {}

    norm_type = contract_type.strip().lower() if contract_type else None
    topic_lower = topic.strip().lower()
    text_lower = clause_text.lower()

    candidates: list[tuple[int, str, str]] = []

    for chunk in snapshot.chunks:
        score = 0
        chunk_type = chunk.contract_type.strip().lower()
        chunk_topic = chunk.topic.strip().lower()

        if norm_type and chunk_type == norm_type:
            score += 20
        if topic_lower and (topic_lower in chunk_topic or chunk_topic in topic_lower):
            score += 30

        # Lexical keyword match bonus
        for word in ("royalty", "advance", "audit", "term", "exclusiv", "master", "copyright"):
            if word in text_lower and word in chunk.text.lower():
                score += 10

        if score > 0:
            candidates.append((score, chunk.chunk_id, chunk.text))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return {chunk_id: text for _, chunk_id, text in candidates[:max_chunks]}


def _build_deterministic_proposal(
    clause_id: str,
    clause_text: str,
    title: str | None,
    section: str | None,
    reference_chunks: dict[str, str],
) -> ClauseProposal:
    """Build a deterministic candidate clause proposal for verification rules check.

    In the Mbiu pipeline, proposals are checked by code (MB-17 repair_and_verify)
    before being converted to result cards.

    Args:
        clause_id: Extractor-assigned clause ID.
        clause_text: Verbatim clause text.
        title: Optional clause title.
        section: Optional section heading.
        reference_chunks: Mapping of chunk_id to reference standard text.

    Returns:
        Candidate ClauseProposal.
    """
    classification = classify_clause_impact(clause_text, title=title, section=section)
    topic = classification.topic
    affects = classification.affects

    # Find safe verbatim key quote from clause text
    sentences = [s.strip() for s in clause_text.split(".") if s.strip()]
    first_sentence = sentences[0] if sentences else clause_text
    key_quote = first_sentence[:60]
    while key_quote and key_quote not in clause_text:
        key_quote = key_quote[:-1]
    if not key_quote:
        key_quote = clause_text[: min(len(clause_text), 40)]

    # Plain language and consequence summaries
    clean_title = (title or f"{topic.replace('_', ' ').title()} Terms").strip()
    if len(clean_title) > 45:
        clean_title = clean_title[:42] + "..."

    what_it_says = "This clause sets the terms for your music deal."
    why_it_matters = "This may affect your pay and your rights."

    # Reference evidence citations
    evidence: list[EvidenceCitation] = []
    matched_pattern: str | None = None
    implication = "none"

    if reference_chunks:
        primary_id, primary_text = next(iter(reference_chunks.items()))
        quote = primary_text[: min(len(primary_text), 80)].strip()
        evidence.append(
            EvidenceCitation(
                chunk_id=primary_id,
                quote=quote,
                source_title="Reviewed Standard Reference Template",
            )
        )
        comparison_note = "Terms compared against reviewed reference templates."
        matched_pattern = "P_STANDARD_MATCH"
    else:
        comparison_note = NO_STANDARD_FOR_TYPE_MESSAGE

    questions = ["Can we clarify the exact terms and timing for this clause?"]

    # Money inputs check for code-calculated shillings
    money_inputs: MoneyExampleInputs | None = None
    if affects == AFFECTS_MONEY:
        # Check if rate percentage exists
        import re

        rate_match = re.search(r"(\d+(?:\.\d+)?\s*%\s*(?:of\s+[A-Za-z\s]+)?)", clause_text)
        basis = "net" if "net" in clause_text.lower() else "gross"
        if rate_match:
            quote_span = rate_match.group(0).strip()
            if quote_span in clause_text:
                money_inputs = MoneyExampleInputs(
                    rate="16%",
                    basis=basis,
                    deductions=[],
                    quote=quote_span,
                )

    return ClauseProposal(
        clause_id=clause_id,
        title=clean_title,
        key_quote=key_quote,
        plain_language=what_it_says,
        why_it_matters=why_it_matters,
        comparison_note=comparison_note,
        questions=questions,
        matched_pattern_id=matched_pattern,
        implication=implication,
        affects=affects,
        evidence=evidence,
        money_inputs=money_inputs,
    )


def evaluate_single_clause_stateless(
    clause_id: str,
    clause_text: str,
    pages: list[int],
    title: str | None,
    section: str | None,
    contract_type: str | None,
    snapshot: CorpusSnapshot | None,
    has_standard: bool,
) -> ClauseEvaluationResult:
    """Statelessly evaluate a single contract clause against reference standards.

    Args:
        clause_id: Target clause ID.
        clause_text: Verbatim clause text.
        pages: List of page numbers spanned.
        title: Optional clause title.
        section: Optional section name.
        contract_type: Optional contract type.
        snapshot: In-memory corpus snapshot.
        has_standard: Whether contract type has reviewed standards.

    Returns:
        ClauseEvaluationResult object.
    """
    if not has_standard:
        return create_no_reviewed_standard_result(
            clause_id=clause_id,
            original_text=clause_text,
            pages=pages,
            contract_type=contract_type or "unknown",
            title=title,
            section=section,
        )

    # Classify impact and find reference chunks
    classification = classify_clause_impact(clause_text, title=title, section=section)
    ref_chunks = _find_relevant_reference_chunks(
        clause_text=clause_text,
        topic=classification.topic,
        contract_type=contract_type,
        snapshot=snapshot,
    )

    if not ref_chunks:
        return create_no_reviewed_standard_result(
            clause_id=clause_id,
            original_text=clause_text,
            pages=pages,
            contract_type=contract_type or "unknown",
            title=title,
            section=section,
        )

    proposal = _build_deterministic_proposal(
        clause_id=clause_id,
        clause_text=clause_text,
        title=title,
        section=section,
        reference_chunks=ref_chunks,
    )

    context = EvaluationContext(
        clause_id=clause_id,
        clause_text=clause_text,
        reference_chunks=ref_chunks,
        known_patterns={"P_STANDARD_MATCH"},
    )

    return evaluate_clause_with_verification(
        proposal=proposal,
        context=context,
        pages=pages,
        clause_number=clause_id,
        contract_type_has_standard=True,
    )


def generate_clause_evaluation_events(
    clauses: Sequence[Clause | dict[str, Any]],
    contract_type: str | None = None,
    defined_terms: Sequence[dict[str, Any]] | None = None,
    snapshot: CorpusSnapshot | None = None,
) -> Generator[dict[str, Any]]:
    """Generate NDJSON streaming events for clause evaluations.

    Emits:
    1. progress (initial)
    2. clause_result or clause_failed for each clause
    3. progress updates
    4. done (consolidated summary)

    Args:
        clauses: List of Clause objects or clause dicts to evaluate.
        contract_type: Optional contract type.
        defined_terms: Optional list of extracted defined terms.
        snapshot: Optional in-memory corpus snapshot.

    Yields:
        Event dictionaries corresponding to NDJSON stream events.
    """
    total_clauses = len(clauses)
    if snapshot is None:
        snapshot = get_active_corpus_snapshot()

    has_standard = _check_contract_type_has_standard(contract_type, snapshot)

    # 1. Initial progress event
    yield {
        "event": "progress",
        "stage": "evaluating",
        "clauses_done": 0,
        "clauses_total": total_clauses,
    }

    evaluated_cards: list[ClauseEvaluationResult] = []
    converted_clauses: list[Clause] = []

    for idx, item in enumerate(clauses):
        c_title: str | None
        c_section: str | None
        if isinstance(item, Clause):
            c_id = item.clause_id
            c_text = item.text
            c_pages = list(item.pages)
            c_title = item.title
            c_section = item.section
            converted_clauses.append(item)
        else:
            c_id = str(item.get("clause_id", f"clause_{idx + 1}"))
            c_text = str(item.get("text", ""))
            raw_pages = item.get("pages")
            c_pages = (
                [int(p) for p in raw_pages] if isinstance(raw_pages, list) and raw_pages else [1]
            )
            raw_title = item.get("title")
            c_title = str(raw_title) if raw_title is not None else None
            raw_section = item.get("section")
            c_section = str(raw_section) if raw_section is not None else None
            converted_clauses.append(
                Clause(
                    clause_id=c_id,
                    section=c_section or "main",
                    title=c_title,
                    text=c_text,
                    pages=c_pages,
                    start_offset=0,
                    end_offset=len(c_text),
                )
            )

        try:
            result = evaluate_single_clause_stateless(
                clause_id=c_id,
                clause_text=c_text,
                pages=c_pages,
                title=c_title,
                section=c_section,
                contract_type=contract_type,
                snapshot=snapshot,
                has_standard=has_standard,
            )
            evaluated_cards.append(result)
            yield {
                "event": "clause_result",
                "clause": dc.asdict(result),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Stateless clause evaluation error for %s: %s", c_id, exc)
            yield {
                "event": "clause_failed",
                "clause_id": c_id,
                "error": "Clause evaluation could not be completed.",
                "status": "evaluation_failed",
            }

        # Progress update
        yield {
            "event": "progress",
            "stage": "evaluating",
            "clauses_done": idx + 1,
            "clauses_total": total_clauses,
        }

    # Reverse check for missing protections
    missing_protections = check_missing_protections(
        contract_clauses=converted_clauses,
        contract_type_has_standard=has_standard,
        corpus_snapshot=snapshot,
    )

    all_results = evaluated_cards + missing_protections
    summary = generate_evaluation_summary(all_results)

    # Done event with summary
    yield {
        "event": "done",
        "summary": dc.asdict(summary),
    }


def clause_evaluations_view(request: HttpRequest) -> HttpResponse | StreamingHttpResponse:
    """Handle POST /api/v1/clause-evaluations for evaluating or retrying clauses statelessly.

    Request Body (JSON):
    {
        "clauses": [
            {
                "clause_id": "4.1",
                "text": "Artist shall receive 15% of Net Receipts...",
                "pages": [2],
                "title": "Royalties",
                "section": "main"
            }
        ],
        "contract_type": "recording",
        "defined_terms": []
    }

    Responses:
    - 200: Streaming newline-delimited JSON (NDJSON) carrying progress, clause_result,
      clause_failed, and done events, with Cache-Control: no-store.
    - 400: Bad Request if body is invalid JSON, clauses is missing/empty, or clauses are malformed.
    - 405: Method Not Allowed if request is not POST.

    Zero Contract Storage Invariant:
    All evaluation operates in-memory. No contract text or results are ever persisted
    to disk, database, or logs.
    """
    if request.method != "POST":
        return JsonResponse(
            {"error": "Method not allowed. Only POST is accepted."},
            status=405,
        )

    try:
        body = json.loads(request.body.decode("utf-8") if request.body else "{}")
    except json.JSONDecodeError, UnicodeDecodeError:
        return JsonResponse({"error": "Invalid JSON request body."}, status=400)

    if not isinstance(body, dict):
        return JsonResponse({"error": "Request body must be a JSON object."}, status=400)

    clauses_data = body.get("clauses")
    if not isinstance(clauses_data, list):
        return JsonResponse({"error": "'clauses' must be a list of clause objects."}, status=400)

    if len(clauses_data) == 0:
        return JsonResponse({"error": "'clauses' list cannot be empty."}, status=400)

    for idx, c in enumerate(clauses_data):
        if not isinstance(c, dict):
            return JsonResponse(
                {"error": f"Clause at index {idx} must be a JSON object."},
                status=400,
            )
        if "clause_id" not in c or not str(c.get("clause_id", "")).strip():
            return JsonResponse(
                {"error": f"Clause at index {idx} is missing 'clause_id'."},
                status=400,
            )
        text_val = c.get("text")
        if not isinstance(text_val, str) or not text_val.strip():
            return JsonResponse(
                {"error": f"Clause at index {idx} is missing non-empty 'text'."},
                status=400,
            )

    contract_type = body.get("contract_type")
    if contract_type is not None and not isinstance(contract_type, str):
        return JsonResponse({"error": "'contract_type' must be a string or null."}, status=400)

    defined_terms = body.get("defined_terms")
    if defined_terms is not None and not isinstance(defined_terms, list):
        return JsonResponse({"error": "'defined_terms' must be a list or null."}, status=400)

    # Check if client requested non-streaming JSON
    accept_header = request.headers.get("Accept", "")
    stream_param = request.GET.get("stream", "").lower()
    is_json_requested = "application/json" in accept_header and stream_param != "true"

    if is_json_requested:
        events = list(
            generate_clause_evaluation_events(
                clauses=clauses_data,
                contract_type=contract_type,
                defined_terms=defined_terms,
            )
        )
        response = JsonResponse({"events": events}, status=200)
        response["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response["Pragma"] = "no-cache"
        return response

    # Stream newline-delimited JSON (NDJSON)
    def ndjson_stream() -> Generator[str]:
        for event in generate_clause_evaluation_events(
            clauses=clauses_data,
            contract_type=contract_type,
            defined_terms=defined_terms,
        ):
            yield json.dumps(event) + "\n"

    streaming_response = StreamingHttpResponse(
        ndjson_stream(),
        content_type="application/x-ndjson",
        status=200,
    )
    streaming_response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    streaming_response["Pragma"] = "no-cache"
    streaming_response["X-Accel-Buffering"] = "no"
    return streaming_response
