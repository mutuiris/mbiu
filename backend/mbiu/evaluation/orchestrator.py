"""Evaluation stream orchestrator.

The spine of Mbiu: handles the lifecycle of one contract evaluation from upload
validation, text extraction, clause segmentation, template retrieval, batched LLM
comparison, deterministic quote verification, to the final summary event.
Emits a validated stream of StreamEvent models.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Final, Literal

from django.conf import settings
from opentelemetry import trace
from pydantic import BaseModel, Field

from mbiu.api.schemas import (
    SCHEMA_VERSION,
    Ask,
    Clause,
    ClauseNote,
    ClauseResult,
    ClauseResultEvent,
    ClauseStatus,
    ContractMapEvent,
    DocumentEvent,
    DocumentPayload,
    DoneEvent,
    Heartbeat,
    HeartbeatEvent,
    Outcome,
    Progress,
    ProgressEvent,
    Provider,
    Section,
    SkippedPage,
    Stage,
    StreamEvent,
    Summary,
    Versions,
)
from mbiu.contract_map import map_contract
from mbiu.corpus.synthetic import retrieve_simple_evidence
from mbiu.documents.extract import extract_text_from_pdf
from mbiu.documents.segment import Clause as SegmentedClause
from mbiu.documents.segment import segment_document
from mbiu.documents.upload import validate_upload
from mbiu.llm import ErrorCategory, LLMError, as_data
from mbiu.llm.gemini import Gemini, gemini
from mbiu.llm.openai import openai
from mbiu.security.turnstile import validate_turnstile_token

tracer: Final = trace.get_tracer("mbiu.orchestrator")
PROMPT_PATH: Final = Path(__file__).resolve().parents[1] / "llm" / "prompts" / "compare_v1.md"
OPENAI_PROMPT_PATH: Final = (
    Path(__file__).resolve().parents[1] / "llm" / "prompts" / "compare_openai_v1.md"
)


def load_compare_prompt() -> str:
    """Load the versioned Gemini comparison prompt from disk."""
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return (
        "You are Mbiu, comparing an English music contract clause against a reviewed template. "
        "Provide honest plain-language analysis, verbatim quotes, and a specific ask."
    )


def load_compare_openai_prompt() -> str:
    """Load the versioned OpenAI comparison prompt from disk."""
    if OPENAI_PROMPT_PATH.exists():
        return OPENAI_PROMPT_PATH.read_text(encoding="utf-8")
    return load_compare_prompt()


class ClauseComparisonProposal(BaseModel):
    """Structured proposal returned by the LLM before verification."""

    comparison: Outcome
    headline: str
    what_it_says: str
    what_it_means: str
    clause_quote: str = Field(description="Exact substring quoted from the contract clause")
    evidence_quote: str | None = Field(
        default=None, description="Exact substring quoted from the template excerpt"
    )
    evidence_id: str | None = Field(
        default=None, description="The ID of the template excerpt cited, if any"
    )
    ask_them: str | None = Field(
        default=None, description="A specific question to ask the other party"
    )


def _error_clause_result(
    clause: SegmentedClause,
    err: LLMError,
    links: list[str],
    provider: Provider,
    model: str,
    evidence: list[Any] | None = None,
    standard_template_id: str | None = None,
    standard_excerpt: str | None = None,
) -> ClauseResult:
    """Build a deterministic ClauseResult when an LLM call fails."""
    if err.category == ErrorCategory.REFUSED:
        status = ClauseStatus.EVALUATION_FAILED
        headline = "AI evaluation refused by provider"
        what_it_says = "The AI provider refused to evaluate this clause."
        what_it_means = (
            "The clause could not be evaluated due to provider refusal or content policy."
        )
    else:
        status = ClauseStatus.CANNOT_COMPARE
        headline = "Unable to complete AI comparison"
        what_it_says = "Mbiu was unable to verify this clause against the standard at this moment."
        what_it_means = f"The AI evaluation encountered an error: {err.category.value}"

    ev_list = evidence or []
    return ClauseResult(
        clause_id=clause.clause_id,
        pages=clause.pages,
        original_text=clause.text,
        status=status,
        comparison=Outcome.CANNOT_COMPARE,
        headline=headline,
        what_it_says=what_it_says,
        what_it_means=what_it_means,
        comparison_note=None,
        impact_inputs=None,
        linked_clauses=links,
        fairer_wording=None,
        ask_them=None,
        standard_template_id=standard_template_id,
        standard_excerpt=standard_excerpt,
        evidence=ev_list,
        evidence_ids=[e.evidence_id for e in ev_list],
        evidence_quote=None,
        provider=provider,
        model_version=model,
    )


def _section_kind(name: str) -> Literal["body", "schedule", "annex"]:
    low = name.lower()
    if "schedule" in low:
        return "schedule"
    if "annex" in low or "appendix" in low or "exhibit" in low:
        return "annex"
    return "body"


def verify_quotes(
    clause_text: str,
    evidence_text: str | None,
    clause_quote: str,
    evidence_quote: str | None,
    *,
    evidence_id: str | None = None,
    allowed_evidence_ids: set[str] | None = None,
) -> bool:
    """Verify that quotes and citations in the proposal are exact verbatim substrings and valid IDs.

    Deterministic code verification ensuring the model never invents quotes or cites unsent IDs.
    """
    if not clause_quote or not clause_quote.strip():
        return False
    if clause_quote not in clause_text:
        return False
    if evidence_quote is not None and evidence_quote.strip():
        if evidence_text is None or evidence_quote not in evidence_text:
            return False
    if evidence_id is not None and evidence_id.strip():
        if allowed_evidence_ids is None or evidence_id not in allowed_evidence_ids:
            return False
    return True


async def _run_evaluation_pipeline(
    pdf_bytes: bytes,
    turnstile_token: str,
    client_ip: str | None,
    llm: Gemini | None,
    queue: asyncio.Queue[StreamEvent | None],
) -> None:
    """Core evaluation execution pipeline running concurrently with heartbeats."""
    try:
        # Stage 1: Validation
        with tracer.start_as_current_span("mbiu.upload") as span:
            span.set_attribute("mbiu.stage", "upload_check")
            validate_turnstile_token(turnstile_token, remote_ip=client_ip)
            upload_meta = validate_upload(pdf_bytes)
            span.set_attribute("mbiu.page_count", upload_meta.page_count)
            span.set_attribute("mbiu.byte_size", upload_meta.total_bytes)

        # Stage 2: In-memory text extraction (isolated subprocess)
        with tracer.start_as_current_span("mbiu.extract") as span:
            span.set_attribute("mbiu.stage", "extract")
            extracted = extract_text_from_pdf(pdf_bytes, page_count=upload_meta.page_count)
            span.set_attribute("mbiu.extracted_pages", extracted.total_pages)
            span.set_attribute("mbiu.skipped_pages_count", len(extracted.skipped_pages))

        # Stage 3: Clause segmentation
        with tracer.start_as_current_span("mbiu.segment") as span:
            span.set_attribute("mbiu.stage", "segment")
            segmented = segment_document(extracted)
            span.set_attribute("mbiu.clause_count", segmented.total_clauses)

        # Build DocumentEvent payload
        sections = [
            Section(
                section_id=sec,
                title=None if sec == "main" else sec,
                kind=_section_kind(sec),
            )
            for sec in segmented.sections
        ]
        api_clauses = [
            Clause(
                clause_id=c.clause_id,
                section_id=c.section,
                number=c.clause_id,
                heading=c.title,
                text=c.text,
                pages=c.pages,
                start=c.start_offset,
                end=c.end_offset,
            )
            for c in segmented.clauses
        ]
        skipped_pages = [
            SkippedPage(page=p, reason="no_text_layer") for p in extracted.skipped_pages
        ]

        document_event = DocumentEvent(
            type="document",
            schema_version="1",
            payload=DocumentPayload(
                page_count=extracted.total_pages,
                sections=sections,
                clauses=api_clauses,
                skipped_pages=skipped_pages,
            ),
        )
        await queue.put(document_event)

        effective_llm = llm if llm is not None else gemini()
        total_clauses = len(segmented.clauses)
        overall_deadline = time.monotonic() + min(
            settings.DEADLINE_CAP_S,
            10.0 + (total_clauses * settings.DEADLINE_PER_CLAUSE_S),
        )

        # Stage 3.5: Whole-contract map
        with tracer.start_as_current_span("mbiu.map_contract") as span:
            span.set_attribute("mbiu.stage", "map_contract")
            contract_map_payload = await map_contract(
                segmented,
                llm=effective_llm,
                deadline=overall_deadline,
            )
            span.set_attribute("mbiu.links_count", len(contract_map_payload.links))
            span.set_attribute("mbiu.issues_count", len(contract_map_payload.issues))
            if contract_map_payload.contract_type:
                span.set_attribute("mbiu.contract_type", contract_map_payload.contract_type)

        contract_map_event = ContractMapEvent(
            type="contract_map",
            schema_version="1",
            payload=contract_map_payload,
        )
        await queue.put(contract_map_event)

        # Build fast lookup for linked clauses and conflicts
        clause_links_map: dict[str, set[str]] = {c.clause_id: set() for c in segmented.clauses}
        for link in contract_map_payload.links:
            if link.from_clause_id in clause_links_map and link.to_clause_id != link.from_clause_id:
                clause_links_map[link.from_clause_id].add(link.to_clause_id)
            if link.to_clause_id in clause_links_map and link.to_clause_id != link.from_clause_id:
                clause_links_map[link.to_clause_id].add(link.from_clause_id)

        conflicts_by_clause: dict[str, list[str]] = {}
        for issue in contract_map_payload.issues:
            id1, id2 = issue.clause_ids
            if id1 in clause_links_map:
                clause_links_map[id1].add(id2)
            if id2 in clause_links_map:
                clause_links_map[id2].add(id1)
            conflicts_by_clause.setdefault(id1, []).append(id2)
            conflicts_by_clause.setdefault(id2, []).append(id1)

        # Stage 4: Batched clause evaluations
        await queue.put(
            ProgressEvent(
                type="progress",
                schema_version="1",
                payload=Progress(stage=Stage.COMPARE, done=0, total=total_clauses),
            )
        )

        instructions = load_compare_prompt()
        instructions_openai = load_compare_openai_prompt()

        results_list: list[ClauseResult] = []
        done_count = 0
        batch_size = max(1, settings.BATCH_SIZE)

        for i in range(0, total_clauses, batch_size):
            batch = segmented.clauses[i : i + batch_size]

            # Check overall deadline
            if time.monotonic() >= overall_deadline:
                for c in segmented.clauses[i:]:
                    c_links = sorted(list(clause_links_map.get(c.clause_id, set())))
                    await queue.put(
                        ClauseResultEvent(
                            type="clause_result",
                            schema_version="1",
                            payload=ClauseResult(
                                clause_id=c.clause_id,
                                pages=c.pages,
                                original_text=c.text,
                                status=ClauseStatus.NOT_CHECKED,
                                comparison=Outcome.CANNOT_COMPARE,
                                headline="Not checked within time limit",
                                what_it_says=(
                                    "This clause was not checked before the contract "
                                    "time budget ran out."
                                ),
                                what_it_means="Higher-priority clauses were evaluated first.",
                                comparison_note=None,
                                impact_inputs=None,
                                linked_clauses=c_links,
                                fairer_wording=None,
                                ask_them=None,
                                standard_template_id=None,
                                standard_excerpt=None,
                                evidence=[],
                                evidence_ids=[],
                                evidence_quote=None,
                                provider=None,
                                model_version=None,
                            ),
                        )
                    )
                break

            use_openai_for_batch = False
            if settings.FAILOVER_ENABLED:
                breaker = getattr(effective_llm, "_breaker", None)
                if breaker is not None and getattr(breaker, "current_state", None) == "open":
                    use_openai_for_batch = True

            batch_results: list[ClauseResult] = []

            if use_openai_for_batch:
                try:
                    openai_llm = openai()
                    for clause in batch:
                        c_links = sorted(list(clause_links_map.get(clause.clause_id, set())))
                        c_conflicts = conflicts_by_clause.get(clause.clause_id, [])
                        clause_res = await _evaluate_single_clause(
                            clause=clause,
                            llm=openai_llm,
                            instructions=instructions_openai,
                            deadline=overall_deadline,
                            linked_clauses=c_links,
                            conflict_with=c_conflicts,
                            provider=Provider.OPENAI,
                            model=settings.OPENAI_MODEL,
                        )
                        batch_results.append(clause_res)
                except LLMError as failover_err:
                    for clause in batch:
                        c_links = sorted(list(clause_links_map.get(clause.clause_id, set())))
                        batch_results.append(
                            _error_clause_result(
                                clause=clause,
                                err=failover_err,
                                links=c_links,
                                provider=Provider.OPENAI,
                                model=settings.OPENAI_MODEL,
                            )
                        )
            else:
                failed_outage = False
                temp_results: list[ClauseResult] = []
                for clause in batch:
                    c_links = sorted(list(clause_links_map.get(clause.clause_id, set())))
                    c_conflicts = conflicts_by_clause.get(clause.clause_id, [])
                    try:
                        clause_res = await _evaluate_single_clause(
                            clause=clause,
                            llm=effective_llm,
                            instructions=instructions,
                            deadline=overall_deadline,
                            linked_clauses=c_links,
                            conflict_with=c_conflicts,
                            provider=Provider.GEMINI,
                            model=settings.GEMINI_MODEL_MAIN,
                            raise_on_error=settings.FAILOVER_ENABLED,
                        )
                        temp_results.append(clause_res)
                    except LLMError as err:
                        if settings.FAILOVER_ENABLED and err.category in (
                            ErrorCategory.UNAVAILABLE,
                            ErrorCategory.TIMEOUT,
                        ):
                            failed_outage = True
                            break
                        else:
                            clause_res = _error_clause_result(
                                clause=clause,
                                err=err,
                                links=c_links,
                                provider=Provider.GEMINI,
                                model=settings.GEMINI_MODEL_MAIN,
                            )
                            temp_results.append(clause_res)

                if failed_outage:
                    batch_results = []
                    try:
                        openai_llm = openai()
                        for clause in batch:
                            c_links = sorted(list(clause_links_map.get(clause.clause_id, set())))
                            c_conflicts = conflicts_by_clause.get(clause.clause_id, [])
                            clause_res = await _evaluate_single_clause(
                                clause=clause,
                                llm=openai_llm,
                                instructions=instructions_openai,
                                deadline=overall_deadline,
                                linked_clauses=c_links,
                                conflict_with=c_conflicts,
                                provider=Provider.OPENAI,
                                model=settings.OPENAI_MODEL,
                            )
                            batch_results.append(clause_res)
                    except LLMError as failover_err:
                        for clause in batch:
                            c_links = sorted(list(clause_links_map.get(clause.clause_id, set())))
                            batch_results.append(
                                _error_clause_result(
                                    clause=clause,
                                    err=failover_err,
                                    links=c_links,
                                    provider=Provider.GEMINI,
                                    model=settings.GEMINI_MODEL_MAIN,
                                )
                            )
                else:
                    batch_results = temp_results

            for clause_res in batch_results:
                results_list.append(clause_res)
                done_count += 1
                await queue.put(
                    ClauseResultEvent(
                        type="clause_result",
                        schema_version="1",
                        payload=clause_res,
                    )
                )
                await queue.put(
                    ProgressEvent(
                        type="progress",
                        schema_version="1",
                        payload=Progress(stage=Stage.COMPARE, done=done_count, total=total_clauses),
                    )
                )

        # Stage 5: Compile Summary and Done event
        with tracer.start_as_current_span("mbiu.summarise") as span:
            span.set_attribute("mbiu.stage", "summarise")
            top_asks: list[Ask] = []
            ask_list: list[Ask] = []
            good_news: list[ClauseNote] = []
            matches_count = 0

            for res in results_list:
                if res.comparison == Outcome.MATCHES_STANDARD:
                    matches_count += 1
                    good_news.append(
                        ClauseNote(
                            clause_id=res.clause_id,
                            text="Matches the standard reviewed template.",
                        )
                    )
                elif res.comparison == Outcome.BETTER_FOR_YOU:
                    good_news.append(
                        ClauseNote(
                            clause_id=res.clause_id,
                            text="More favourable to you than the standard template.",
                        )
                    )

                if res.ask_them:
                    ask_item = Ask(clause_id=res.clause_id, question=res.ask_them)
                    ask_list.append(ask_item)
                    if (
                        res.comparison == Outcome.WORSE_FOR_YOU
                        or res.comparison == Outcome.NOT_IN_STANDARD
                    ) and len(top_asks) < 3:
                        top_asks.append(ask_item)

            span.set_attribute("mbiu.matches_count", matches_count)
            span.set_attribute("mbiu.asks_count", len(ask_list))

            providers_used = {r.provider for r in results_list if r.provider is not None}
            if Provider.OPENAI in providers_used and Provider.GEMINI not in providers_used:
                summary_prompt = "compare_openai_v1"
                summary_model = settings.OPENAI_MODEL
            elif Provider.OPENAI in providers_used and Provider.GEMINI in providers_used:
                summary_prompt = "compare_v1,compare_openai_v1"
                summary_model = f"{settings.GEMINI_MODEL_MAIN},{settings.OPENAI_MODEL}"
            else:
                summary_prompt = "compare_v1"
                summary_model = settings.GEMINI_MODEL_MAIN

            summary = Summary(
                top_asks=top_asks,
                contract_issues=[],
                missing_protections=[],
                good_news=good_news[:10],
                matches_count=matches_count,
                skipped_pages=skipped_pages,
                ask_list=ask_list,
                versions=Versions(
                    schema_version=SCHEMA_VERSION,
                    prompt=summary_prompt,
                    model=summary_model,
                    corpus="synthetic-v0",
                ),
            )

            await queue.put(
                DoneEvent(
                    type="done",
                    schema_version="1",
                    payload=summary,
                )
            )

    except Exception:
        # Re-raise to trigger error handling in consumer
        raise
    finally:
        # Signal completion to consumer
        await queue.put(None)


async def _evaluate_single_clause(
    clause: SegmentedClause,
    llm: Any,
    instructions: str,
    deadline: float,
    linked_clauses: list[str] | None = None,
    conflict_with: list[str] | None = None,
    *,
    provider: Provider = Provider.GEMINI,
    model: str = settings.GEMINI_MODEL_MAIN,
    raise_on_error: bool = False,
) -> ClauseResult:
    """Evaluate one clause against retrieved synthetic template evidence."""
    links = linked_clauses or []
    conflicts = conflict_with or []

    # Retrieve template evidence
    with tracer.start_as_current_span("mbiu.retrieve") as span:
        span.set_attribute("mbiu.stage", "retrieve")
        evidence = retrieve_simple_evidence(clause.text)
        span.set_attribute("mbiu.evidence_count", len(evidence))

    primary_ev = evidence[0] if evidence else None
    content_parts = [
        as_data("contract_clause", clause.text, clause_id=clause.clause_id),
    ]
    if primary_ev:
        content_parts.append(
            as_data(
                "standard_template",
                primary_ev.excerpt,
                template_id=primary_ev.template_id,
                source=primary_ev.source_title,
            )
        )
    content = "\n\n".join(content_parts)
    allowed_ev_ids = {e.evidence_id for e in evidence}
    if primary_ev:
        allowed_ev_ids.add(primary_ev.template_id)

    try:
        with tracer.start_as_current_span("mbiu.compare") as span:
            span.set_attribute("mbiu.stage", "compare")
            llm_result = await llm.generate(
                model=model,
                instructions=instructions,
                content=content,
                output=ClauseComparisonProposal,
                deadline=deadline,
            )
            proposal = llm_result.value

        # Verification in code
        with tracer.start_as_current_span("mbiu.verify") as span:
            span.set_attribute("mbiu.stage", "verify")
            quotes_valid = verify_quotes(
                clause_text=clause.text,
                evidence_text=primary_ev.excerpt if primary_ev else None,
                clause_quote=proposal.clause_quote,
                evidence_quote=proposal.evidence_quote,
                evidence_id=proposal.evidence_id,
                allowed_evidence_ids=allowed_ev_ids,
            )
            span.set_attribute("mbiu.quotes_verified", quotes_valid)

        if not quotes_valid:
            return ClauseResult(
                clause_id=clause.clause_id,
                pages=clause.pages,
                original_text=clause.text,
                status=ClauseStatus.CANNOT_COMPARE,
                comparison=Outcome.CANNOT_COMPARE,
                headline="Could not reliably verify comparison quotes",
                what_it_says=proposal.what_it_says,
                what_it_means=proposal.what_it_means,
                comparison_note="The comparison could not be verified against the source text.",
                impact_inputs=None,
                linked_clauses=links,
                fairer_wording=None,
                ask_them=proposal.ask_them,
                standard_template_id=primary_ev.template_id if primary_ev else None,
                standard_excerpt=primary_ev.excerpt if primary_ev else None,
                evidence=evidence,
                evidence_ids=[e.evidence_id for e in evidence],
                evidence_quote=None,
                provider=provider,
                model_version=llm_result.model_version,
            )

        outcome = proposal.comparison
        comp_note = None
        if conflicts and outcome == Outcome.MATCHES_STANDARD:
            outcome = Outcome.WORSE_FOR_YOU
            comp_note = (
                f"This clause conflicts with clause(s) {', '.join(conflicts)} "
                "elsewhere in the contract."
            )

        fairer = primary_ev.excerpt if outcome == Outcome.WORSE_FOR_YOU and primary_ev else None
        return ClauseResult(
            clause_id=clause.clause_id,
            pages=clause.pages,
            original_text=clause.text,
            status=ClauseStatus.EVALUATED,
            comparison=outcome,
            headline=proposal.headline,
            what_it_says=proposal.what_it_says,
            what_it_means=proposal.what_it_means,
            comparison_note=comp_note,
            impact_inputs=None,
            linked_clauses=links,
            fairer_wording=fairer,
            ask_them=proposal.ask_them,
            standard_template_id=primary_ev.template_id if primary_ev else None,
            standard_excerpt=primary_ev.excerpt if primary_ev else None,
            evidence=evidence,
            evidence_ids=[e.evidence_id for e in evidence],
            evidence_quote=proposal.evidence_quote,
            provider=provider,
            model_version=llm_result.model_version,
        )

    except LLMError as err:
        if raise_on_error:
            raise

        return _error_clause_result(
            clause=clause,
            err=err,
            links=links,
            provider=provider,
            model=model,
            evidence=evidence,
            standard_template_id=primary_ev.template_id if primary_ev else None,
            standard_excerpt=primary_ev.excerpt if primary_ev else None,
        )


async def evaluate_contract(
    pdf_bytes: bytes,
    turnstile_token: str,
    *,
    client_ip: str | None = None,
    llm: Gemini | None = None,
    heartbeat_interval_s: float = 10.0,
) -> AsyncGenerator[StreamEvent]:
    """Stream validated evaluation events for an uploaded contract PDF.

    Maintains zero-storage invariants: processes entirely in memory and releases
    all references upon completion, error, or client cancellation.
    Emits periodic HeartbeatEvent every heartbeat_interval_s seconds.
    """
    queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
    worker_task = asyncio.create_task(
        _run_evaluation_pipeline(
            pdf_bytes=pdf_bytes,
            turnstile_token=turnstile_token,
            client_ip=client_ip,
            llm=llm,
            queue=queue,
        )
    )

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval_s)
            except TimeoutError:
                if worker_task.done():
                    # Worker failed or exited unexpectedly
                    exc = worker_task.exception()
                    if exc:
                        raise exc from None
                    break
                # Emit keepalive heartbeat
                yield HeartbeatEvent(
                    type="heartbeat",
                    schema_version="1",
                    payload=Heartbeat(),
                )
                continue

            if event is None:
                # Finished
                break
            yield event

        # Ensure any worker error is raised
        if worker_task.done():
            exc = worker_task.exception()
            if exc:
                raise exc

    except asyncio.CancelledError, GeneratorExit:
        # Client disconnect or cancellation: cancel worker and clean up immediately
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError, Exception:
            pass
        raise
    finally:
        if not worker_task.done():
            worker_task.cancel()
