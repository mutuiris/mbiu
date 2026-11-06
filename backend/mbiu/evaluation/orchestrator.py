"""Evaluation stream orchestrator.

The spine of Mbiu: handles the lifecycle of one contract evaluation from upload
validation, text extraction, clause segmentation, template retrieval, batched LLM
comparison, verification of every model proposal, to the final summary event.
Emits a validated stream of StreamEvent models.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator, Callable, Coroutine
from pathlib import Path
from typing import Any, Final, Literal

from django.conf import settings
from opentelemetry import trace

from mbiu.api.schemas import (
    SCHEMA_VERSION,
    Ask,
    Clause,
    ClauseFailedEvent,
    ClauseFailure,
    ClauseNote,
    ClauseResult,
    ClauseResultEvent,
    ClauseStatus,
    ContractMapEvent,
    DocumentEvent,
    DocumentPayload,
    DoneEvent,
    Evidence,
    FailureReason,
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
from mbiu.evaluation.verify import ClauseComparisonProposal, Sent, verify
from mbiu.llm import ErrorCategory, LLMError, as_data
from mbiu.llm.gemini import Gemini, gemini
from mbiu.llm.openai import openai
from mbiu.retrieval.evidence import corpus_version, plan_clauses
from mbiu.retrieval.topics import impact_rank

tracer: Final = trace.get_tracer("mbiu.orchestrator")
# Outcomes worth asking about, as the cards label them
TOP_ASK_OUTCOMES: Final = frozenset(
    {Outcome.WORSE_FOR_YOU, Outcome.MISSING_FROM_CONTRACT, Outcome.NOT_IN_STANDARD}
)
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


def _deadline(clause_count: int) -> float:
    return time.monotonic() + min(
        settings.DEADLINE_CAP_S,
        10.0 + (clause_count * settings.DEADLINE_PER_CLAUSE_S),
    )


async def _provider(
    llm: Gemini | None,
    clauses: list[SegmentedClause],
    queue: asyncio.Queue[StreamEvent | None],
) -> Gemini | None:
    """Return the model provider, or fail each clause and return None when none is usable."""
    if llm is not None:
        return llm
    try:
        return gemini()
    except LLMError as err:
        # No usable provider (for example a missing or revoked key). Say so per clause
        # instead of breaking the stream, so the artist gets an honest retry.
        for c in clauses:
            await queue.put(
                ClauseFailedEvent(
                    payload=ClauseFailure(
                        clause_id=c.clause_id,
                        reason=FailureReason(err.category.value),
                        retryable=True,
                    )
                )
            )
        return None


class _TokenBudget:
    """Tokens one contract may use. Checked between batches, so a batch in flight finishes."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.used = 0

    def add(self, result: Any) -> None:
        self.used += (result.input_tokens or 0) + (result.output_tokens or 0)

    @property
    def spent(self) -> bool:
        return self.used >= self.limit


async def _compare_clauses(
    clauses: list[SegmentedClause],
    effective_llm: Gemini,
    queue: asyncio.Queue[StreamEvent | None],
    *,
    deadline: float,
    clause_links_map: dict[str, set[str]],
    conflicts_by_clause: dict[str, list[str]],
    contract_type: str | None = None,
) -> list[ClauseResult]:
    """Check clauses in batches, most important first, streaming each result as it lands."""
    plans = dict(
        zip(
            (c.clause_id for c in clauses),
            await plan_clauses([c.text for c in clauses], contract_type),
            strict=True,
        )
    )
    # Money, ownership, term, exclusivity and termination first; boilerplate last
    clauses = sorted(clauses, key=lambda c: impact_rank(plans[c.clause_id].topic))
    total_clauses = len(clauses)
    budget = _TokenBudget(settings.TOKEN_BUDGET_PER_CONTRACT)
    await queue.put(
        ProgressEvent(
            type="progress",
            payload=Progress(stage=Stage.COMPARE, done=0, total=total_clauses),
        )
    )

    instructions = load_compare_prompt()
    instructions_openai = load_compare_openai_prompt()

    results_list: list[ClauseResult] = []
    done_count = 0
    batch_size = max(1, settings.BATCH_SIZE)

    # Clauses in a batch are checked in parallel, at most LLM_CONCURRENCY at a time
    semaphore = asyncio.Semaphore(settings.LLM_CONCURRENCY)

    def links_for(clause: SegmentedClause) -> list[str]:
        return sorted(clause_links_map.get(clause.clause_id, set()))

    def as_result(
        clause: SegmentedClause,
        outcome: ClauseResult | LLMError,
        provider: Provider,
        model: str,
    ) -> ClauseResult:
        if isinstance(outcome, ClauseResult):
            return outcome
        return _error_clause_result(
            clause=clause, err=outcome, links=links_for(clause), provider=provider, model=model
        )

    async def run_batch(
        batch: list[SegmentedClause],
        batch_llm: Any,
        batch_instructions: str,
        provider: Provider,
        model: str,
        *,
        raise_on_error: bool = False,
    ) -> list[ClauseResult | LLMError]:
        async def one(clause: SegmentedClause) -> ClauseResult | LLMError:
            async with semaphore:
                try:
                    return await _evaluate_single_clause(
                        clause=clause,
                        llm=batch_llm,
                        instructions=batch_instructions,
                        deadline=deadline,
                        linked_clauses=links_for(clause),
                        conflict_with=conflicts_by_clause.get(clause.clause_id, []),
                        evidence=plans[clause.clause_id].evidence,
                        note=plans[clause.clause_id].note,
                        budget=budget,
                        provider=provider,
                        model=model,
                        raise_on_error=raise_on_error,
                    )
                except LLMError as err:
                    return err

        return list(await asyncio.gather(*(one(c) for c in batch)))

    async def run_openai(batch: list[SegmentedClause]) -> list[ClauseResult]:
        try:
            openai_llm = openai()
        except LLMError as err:
            outcomes: list[ClauseResult | LLMError] = [err] * len(batch)
        else:
            outcomes = await run_batch(
                batch, openai_llm, instructions_openai, Provider.OPENAI, settings.OPENAI_MODEL
            )
        return [
            as_result(c, o, Provider.OPENAI, settings.OPENAI_MODEL)
            for c, o in zip(batch, outcomes, strict=True)
        ]

    for i in range(0, total_clauses, batch_size):
        batch = clauses[i : i + batch_size]

        # Out of time or tokens: the rest were lower impact, so they go out as not checked
        if time.monotonic() >= deadline or budget.spent:
            for c in clauses[i:]:
                await queue.put(
                    ClauseFailedEvent(
                        payload=ClauseFailure(
                            clause_id=c.clause_id, reason=FailureReason.NOT_CHECKED, retryable=True
                        )
                    )
                )
            break

        use_openai_for_batch = False
        if settings.FAILOVER_ENABLED:
            breaker = getattr(effective_llm, "_breaker", None)
            if breaker is not None and getattr(breaker, "current_state", None) == "open":
                use_openai_for_batch = True

        batch_results: list[ClauseResult]
        if use_openai_for_batch:
            batch_results = await run_openai(batch)
        else:
            outcomes = await run_batch(
                batch,
                effective_llm,
                instructions,
                Provider.GEMINI,
                settings.GEMINI_MODEL_MAIN,
                raise_on_error=settings.FAILOVER_ENABLED,
            )
            outage = settings.FAILOVER_ENABLED and any(
                isinstance(o, LLMError)
                and o.category in (ErrorCategory.UNAVAILABLE, ErrorCategory.TIMEOUT)
                for o in outcomes
            )
            # One provider per batch: on an outage the whole batch moves to OpenAI
            batch_results = (
                await run_openai(batch)
                if outage
                else [
                    as_result(c, o, Provider.GEMINI, settings.GEMINI_MODEL_MAIN)
                    for c, o in zip(batch, outcomes, strict=True)
                ]
            )

        for clause_res in batch_results:
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
    return results_list


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

        effective_llm = await _provider(llm, segmented.clauses, queue)
        if effective_llm is None:
            return
        overall_deadline = _deadline(len(segmented.clauses))

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

        results_list = await _compare_clauses(
            segmented.clauses,
            effective_llm,
            queue,
            deadline=overall_deadline,
            clause_links_map=clause_links_map,
            conflicts_by_clause=conflicts_by_clause,
            contract_type=contract_map_payload.contract_type,
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
                            text="Typical: it matches the reviewed standard.",
                        )
                    )
                elif res.comparison == Outcome.BETTER_FOR_YOU:
                    good_news.append(
                        ClauseNote(
                            clause_id=res.clause_id,
                            text="Typical, and better for you than the reviewed standard.",
                        )
                    )

                if res.ask_them:
                    ask_item = Ask(clause_id=res.clause_id, question=res.ask_them)
                    ask_list.append(ask_item)
                    # Results arrive in impact order, so the first three are the top three
                    if res.comparison in TOP_ASK_OUTCOMES and len(top_asks) < 3:
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
                contract_issues=contract_map_payload.issues,
                missing_protections=[],
                good_news=good_news[:10],
                matches_count=matches_count,
                skipped_pages=skipped_pages,
                ask_list=ask_list,
                versions=Versions(
                    schema_version=SCHEMA_VERSION,
                    prompt=summary_prompt,
                    model=summary_model,
                    corpus=await corpus_version(),
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
    llm: Any,
    instructions: str,
    deadline: float,
    linked_clauses: list[str] | None = None,
    conflict_with: list[str] | None = None,
    *,
    evidence: list[Evidence] | None = None,
    note: str | None = None,
    budget: _TokenBudget | None = None,
    provider: Provider = Provider.GEMINI,
    model: str = settings.GEMINI_MODEL_MAIN,
    raise_on_error: bool = False,
) -> ClauseResult:
    """Evaluate one clause against the template evidence retrieved for it."""
    links = linked_clauses or []
    conflicts = conflict_with or []

    if evidence is None:
        evidence = retrieve_simple_evidence(clause.text)

    primary_ev = evidence[0] if evidence else None
    content_parts = [
        as_data("contract_clause", clause.text, clause_id=clause.clause_id),
    ]
    if primary_ev:
        content_parts.append(
            as_data(
                "standard_template",
                primary_ev.excerpt,
                evidence_id=primary_ev.evidence_id,
                template_id=primary_ev.template_id,
                source=primary_ev.source_title,
            )
        )
    content = "\n\n".join(content_parts)
    sent = Sent(clause_id=clause.clause_id, clause_text=clause.text, evidence=evidence)

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
            if budget is not None:
                budget.add(llm_result)

        with tracer.start_as_current_span("mbiu.verify") as span:
            span.set_attribute("mbiu.stage", "verify")
            failed = verify(llm_result.value, sent)
            span.set_attribute("mbiu.verify.failed_rules", sorted(failed))
            if failed:
                # One repair attempt, naming each failed rule; a second failure is final
                checks = "\n".join(f"- {name}: {reason}" for name, reason in failed.items())
                llm_result = await llm.generate(
                    model=model,
                    instructions=instructions,
                    content=(
                        f"{content}\n\n"
                        f"{as_data('previous_answer', llm_result.value.model_dump_json())}\n\n"
                        "Your previous answer failed these checks. Answer again with them "
                        f"fixed:\n{checks}"
                    ),
                    output=ClauseComparisonProposal,
                    deadline=deadline,
                )
                if budget is not None:
                    budget.add(llm_result)
                failed = verify(llm_result.value, sent)
                span.set_attribute("mbiu.verify.failed_rules_after_repair", sorted(failed))
        proposal = llm_result.value

        if failed:
            # Never send an unverified proposal: none of its wording reaches the artist
            return ClauseResult(
                clause_id=clause.clause_id,
                pages=clause.pages,
                original_text=clause.text,
                status=ClauseStatus.CANNOT_COMPARE,
                comparison=Outcome.CANNOT_COMPARE,
                headline="Mbiu couldn't verify this comparison",
                what_it_says=(
                    "Mbiu's answer for this clause didn't pass its accuracy checks, "
                    "so it isn't shown."
                ),
                what_it_means=(
                    "This clause hasn't been compared with the standard. Read it closely, "
                    "or ask someone you trust about it."
                ),
                comparison_note=note,
                impact_inputs=None,
                linked_clauses=links,
                fairer_wording=None,
                ask_them=None,
                standard_template_id=primary_ev.template_id if primary_ev else None,
                standard_excerpt=primary_ev.excerpt if primary_ev else None,
                evidence=evidence,
                evidence_ids=[e.evidence_id for e in evidence],
                evidence_quote=None,
                provider=provider,
                model_version=llm_result.model_version,
            )

        # A conflict is a contract issue, not a template comparison, so the verdict stays
        outcome = proposal.comparison
        notes = []
        if note is not None:
            # Nothing to compare with: keep the explanation, never a verdict
            outcome = Outcome.CANNOT_COMPARE
            notes.append(note)
        if conflicts:
            notes.append(
                f"This clause conflicts with clause(s) {', '.join(conflicts)} "
                "elsewhere in the contract."
            )
        comp_note = " ".join(notes) or None

        fairer = primary_ev.excerpt if outcome == Outcome.WORSE_FOR_YOU and primary_ev else None
        return ClauseResult(
            clause_id=clause.clause_id,
            pages=clause.pages,
            original_text=clause.text,
            status=ClauseStatus.EVALUATED if note is None else ClauseStatus.CANNOT_COMPARE,
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


async def _run_clause_pipeline(
    clauses: list[SegmentedClause],
    llm: Gemini | None,
    queue: asyncio.Queue[StreamEvent | None],
) -> None:
    """Check clauses the browser sent back, without re-reading or re-mapping the contract."""
    try:
        effective_llm = await _provider(llm, clauses, queue)
        if effective_llm is not None:
            await _compare_clauses(
                clauses,
                effective_llm,
                queue,
                deadline=_deadline(len(clauses)),
                clause_links_map={},
                conflicts_by_clause={},
            )
    finally:
        await queue.put(None)


def evaluate_contract(
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
    return _stream(
        lambda queue: _run_evaluation_pipeline(pdf_bytes=pdf_bytes, llm=llm, queue=queue),
        heartbeat_interval_s,
    )


def evaluate_clauses(
    clauses: list[Clause],
    *,
    llm: Gemini | None = None,
    heartbeat_interval_s: float = 10.0,
) -> AsyncGenerator[StreamEvent]:
    """Stream results for clauses the browser already holds: retries and unfinished clauses.

    Sends progress, clause_result and clause_failed events only. The browser keeps the
    document, contract map and summary it already has.
    """
    segmented = [
        SegmentedClause(
            clause_id=c.clause_id,
            section=c.section_id,
            title=c.heading,
            text=c.text,
            pages=list(c.pages),
            start_offset=c.start,
            end_offset=c.end,
        )
        for c in clauses
    ]
    return _stream(lambda queue: _run_clause_pipeline(segmented, llm, queue), heartbeat_interval_s)


async def _stream(
    run: Callable[[asyncio.Queue[StreamEvent | None]], Coroutine[Any, Any, None]],
    heartbeat_interval_s: float,
) -> AsyncGenerator[StreamEvent]:
    """Yield the worker's events, with a heartbeat whenever it is quiet for a while."""
    queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
    worker_task = asyncio.create_task(run(queue))

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
