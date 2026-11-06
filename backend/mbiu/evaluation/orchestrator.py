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
from typing import Final, Literal

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
from mbiu.corpus.synthetic import retrieve_simple_evidence
from mbiu.documents.extract import extract_text_from_pdf
from mbiu.documents.segment import Clause as SegmentedClause
from mbiu.documents.segment import segment_document
from mbiu.documents.upload import validate_upload
from mbiu.llm import LLMError, as_data
from mbiu.llm.gemini import Gemini, gemini

tracer: Final = trace.get_tracer("mbiu.orchestrator")
PROMPT_PATH: Final = Path(__file__).resolve().parents[1] / "llm" / "prompts" / "compare_v1.md"


def load_compare_prompt() -> str:
    """Load the versioned comparison prompt from disk."""
    if PROMPT_PATH.exists():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return (
        "You are Mbiu, comparing an English music contract clause against a reviewed template. "
        "Provide honest plain-language analysis, verbatim quotes, and a specific ask."
    )


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
    ask_them: str | None = Field(
        default=None, description="A specific question to ask the other party"
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
) -> bool:
    """Verify that quotes in the proposal are exact verbatim substrings of what was sent.

    Deterministic code verification ensuring the model never invents quotes.
    """
    if not clause_quote or not clause_quote.strip():
        return False
    if clause_quote not in clause_text:
        return False
    if evidence_quote is not None and evidence_quote.strip():
        if evidence_text is None or evidence_quote not in evidence_text:
            return False
    return True


async def _run_evaluation_pipeline(
    pdf_bytes: bytes,
    llm: Gemini | None,
    queue: asyncio.Queue[StreamEvent | None],
) -> None:
    """Core evaluation execution pipeline running concurrently with heartbeats."""
    try:
        # The view has already checked the Turnstile token. Tokens are single use.
        # Blocking stages run in threads so heartbeats and other streams keep going.
        with tracer.start_as_current_span("mbiu.upload") as span:
            span.set_attribute("mbiu.stage", "upload_check")
            # ponytail: the view validated this too; pass page_count in if it shows in profiles
            upload_meta = await asyncio.to_thread(validate_upload, pdf_bytes)
            span.set_attribute("mbiu.page_count", upload_meta.page_count)
            span.set_attribute("mbiu.byte_size", upload_meta.total_bytes)

        with tracer.start_as_current_span("mbiu.extract") as span:
            span.set_attribute("mbiu.stage", "extract")
            extracted = await asyncio.to_thread(
                extract_text_from_pdf, pdf_bytes, page_count=upload_meta.page_count
            )
            span.set_attribute("mbiu.extracted_pages", extracted.total_pages)
            span.set_attribute("mbiu.skipped_pages_count", len(extracted.skipped_pages))

        with tracer.start_as_current_span("mbiu.segment") as span:
            span.set_attribute("mbiu.stage", "segment")
            segmented = await asyncio.to_thread(segment_document, extracted)
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
            payload=DocumentPayload(
                page_count=extracted.total_pages,
                sections=sections,
                clauses=api_clauses,
                skipped_pages=skipped_pages,
            ),
        )
        await queue.put(document_event)

        # Stage 4: Batched clause evaluations
        total_clauses = len(segmented.clauses)
        await queue.put(
            ProgressEvent(
                type="progress",
                payload=Progress(stage=Stage.COMPARE, done=0, total=total_clauses),
            )
        )

        overall_deadline = time.monotonic() + min(
            settings.DEADLINE_CAP_S,
            10.0 + (total_clauses * settings.DEADLINE_PER_CLAUSE_S),
        )

        effective_llm = llm if llm is not None else gemini()
        instructions = load_compare_prompt()

        results_list: list[ClauseResult] = []
        done_count = 0
        batch_size = max(1, settings.BATCH_SIZE)

        for i in range(0, total_clauses, batch_size):
            batch = segmented.clauses[i : i + batch_size]

            # Check overall deadline
            if time.monotonic() >= overall_deadline:
                for c in segmented.clauses[i:]:
                    await queue.put(
                        ClauseResultEvent(
                            type="clause_result",
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
                                linked_clauses=[],
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

            for clause in batch:
                clause_res = await _evaluate_single_clause(
                    clause=clause,
                    llm=effective_llm,
                    instructions=instructions,
                    deadline=overall_deadline,
                )
                results_list.append(clause_res)
                done_count += 1

                await queue.put(
                    ClauseResultEvent(
                        type="clause_result",
                        payload=clause_res,
                    )
                )
                await queue.put(
                    ProgressEvent(
                        type="progress",
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
                    prompt="compare_v1",
                    model=settings.GEMINI_MODEL_MAIN,
                    corpus="synthetic-v0",
                ),
            )

            await queue.put(
                DoneEvent(
                    type="done",
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
    llm: Gemini,
    instructions: str,
    deadline: float,
) -> ClauseResult:
    """Evaluate one clause against retrieved synthetic template evidence."""
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

    try:
        with tracer.start_as_current_span("mbiu.compare") as span:
            span.set_attribute("mbiu.stage", "compare")
            llm_result = await llm.generate(
                model=settings.GEMINI_MODEL_MAIN,
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
                linked_clauses=[],
                fairer_wording=None,
                ask_them=proposal.ask_them,
                standard_template_id=primary_ev.template_id if primary_ev else None,
                standard_excerpt=primary_ev.excerpt if primary_ev else None,
                evidence=evidence,
                evidence_ids=[e.evidence_id for e in evidence],
                evidence_quote=None,
                provider=Provider.GEMINI,
                model_version=llm_result.model_version,
            )

        fairer = (
            primary_ev.excerpt
            if proposal.comparison == Outcome.WORSE_FOR_YOU and primary_ev
            else None
        )
        return ClauseResult(
            clause_id=clause.clause_id,
            pages=clause.pages,
            original_text=clause.text,
            status=ClauseStatus.EVALUATED,
            comparison=proposal.comparison,
            headline=proposal.headline,
            what_it_says=proposal.what_it_says,
            what_it_means=proposal.what_it_means,
            comparison_note=None,
            impact_inputs=None,
            linked_clauses=[],
            fairer_wording=fairer,
            ask_them=proposal.ask_them,
            standard_template_id=primary_ev.template_id if primary_ev else None,
            standard_excerpt=primary_ev.excerpt if primary_ev else None,
            evidence=evidence,
            evidence_ids=[e.evidence_id for e in evidence],
            evidence_quote=proposal.evidence_quote,
            provider=Provider.GEMINI,
            model_version=llm_result.model_version,
        )

    except LLMError as err:
        return ClauseResult(
            clause_id=clause.clause_id,
            pages=clause.pages,
            original_text=clause.text,
            status=ClauseStatus.CANNOT_COMPARE,
            comparison=Outcome.CANNOT_COMPARE,
            headline="Unable to complete AI comparison",
            what_it_says=(
                "Mbiu was unable to verify this clause against the standard at this moment."
            ),
            what_it_means=f"The AI evaluation encountered an error: {err.category.value}",
            comparison_note=None,
            impact_inputs=None,
            linked_clauses=[],
            fairer_wording=None,
            ask_them=None,
            standard_template_id=primary_ev.template_id if primary_ev else None,
            standard_excerpt=primary_ev.excerpt if primary_ev else None,
            evidence=evidence,
            evidence_ids=[e.evidence_id for e in evidence],
            evidence_quote=None,
            provider=Provider.GEMINI,
            model_version=settings.GEMINI_MODEL_MAIN,
        )


async def evaluate_contract(
    pdf_bytes: bytes,
    *,
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
