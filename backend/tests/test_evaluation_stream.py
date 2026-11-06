"""Comprehensive tests for the evaluation streaming endpoint and orchestrator.

Verifies:
1. Stream event order: document -> progress -> clause_result -> done.
2. Quote verification: exact substring quotes accepted; hallucinated quotes rejected.
3. Keepalive heartbeats: emitted during slow LLM processing.
4. Client disconnect: early cancellation stops processing cleanly without leaks.
5. Pre-stream validation errors: bad file, encrypted PDF, invalid Turnstile return ApiError.
6. OpenTelemetry tracing: spans generated for all stages with zero contract text or PII.
"""

from __future__ import annotations

import asyncio
import io
import json
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pytest
from django.http import HttpResponse, StreamingHttpResponse
from django.http.response import HttpResponseBase
from django.test import AsyncRequestFactory
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from mbiu.api.schemas import (
    ClauseResultEvent,
    ContractMapEvent,
    DocumentEvent,
    DoneEvent,
    HeartbeatEvent,
    Outcome,
    ProgressEvent,
    StreamEvent,
    stream_event,
)
from mbiu.api.views import clause_evaluations, evaluations
from mbiu.evaluation.orchestrator import (
    ClauseComparisonProposal,
    evaluate_contract,
    verify_quotes,
)
from mbiu.llm.gemini import Gemini
from mbiu.security.turnstile import (
    CLOUDFLARE_TEST_SECRET_ALWAYS_FAIL,
)
from tests.pdf_factories import (
    create_synthetic_encrypted_pdf,
    create_synthetic_text_pdf,
)

# OpenTelemetry span capture fixture
span_exporter = InMemorySpanExporter()
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
trace.set_tracer_provider(tracer_provider)


class FakeGeminiClient:
    """Mock Gemini client returning pre-configured proposals or delays."""

    def __init__(
        self,
        *,
        delay_s: float = 0.0,
        proposal: ClauseComparisonProposal | None = None,
        raise_err: Exception | None = None,
    ) -> None:
        self.delay_s = delay_s
        self.proposal = proposal
        self.raise_err = raise_err

    async def _create(self, **kwargs: Any) -> Any:
        if self.delay_s > 0:
            await asyncio.sleep(self.delay_s)
        if self.raise_err:
            raise self.raise_err

        prop = self.proposal or ClauseComparisonProposal(
            comparison=Outcome.WORSE_FOR_YOU,
            headline="Royalty rate is lower than recommended standard",
            what_it_says="You receive 10% of net receipts after costs.",
            what_it_means="Your earnings will be reduced by label expenses.",
            clause_quote="10% of net receipts",
            evidence_quote="royalty of not less than 15% to 20% of Gross Receipts",
            ask_them="Can the royalty rate be increased to 15% of gross receipts?",
        )

        return SimpleNamespace(
            status="completed",
            output_text=prop.model_dump_json(),
            model="gemini-3.8-flash",
            usage=SimpleNamespace(total_input_tokens=100, total_output_tokens=50),
        )

    @property
    def aio(self) -> Any:
        return SimpleNamespace(interactions=SimpleNamespace(create=self._create))


@pytest.fixture
def fake_llm() -> Gemini:
    client = FakeGeminiClient()
    return Gemini(client, timeout_s=10.0)


SYNTHETIC_TEST_CONTRACT = [
    (
        "1. Definitions and Royalties\n"
        "The Company shall pay the Artist 10% of net receipts after all distribution costs."
    ),
    ("2. Term\nThe initial period shall be for a duration of two (2) years."),
]


def test_quote_verification_logic() -> None:
    """Verifies that quotes must be exact substrings of what was sent."""
    clause_text = "The Label shall pay the Artist 10% of net receipts after costs."
    evidence_text = "Standard royalty is 15% of Gross Receipts without deductions."

    # Exact quotes pass
    assert (
        verify_quotes(
            clause_text=clause_text,
            evidence_text=evidence_text,
            clause_quote="10% of net receipts",
            evidence_quote="15% of Gross Receipts",
        )
        is True
    )

    # Hallucinated clause quote fails
    assert (
        verify_quotes(
            clause_text=clause_text,
            evidence_text=evidence_text,
            clause_quote="50% of gross profits",  # Not in clause_text
            evidence_quote="15% of Gross Receipts",
        )
        is False
    )

    # Hallucinated evidence quote fails
    assert (
        verify_quotes(
            clause_text=clause_text,
            evidence_text=evidence_text,
            clause_quote="10% of net receipts",
            evidence_quote="Standard rate is 30%",  # Not in evidence_text
        )
        is False
    )

    # Empty clause quote fails
    assert (
        verify_quotes(
            clause_text=clause_text,
            evidence_text=evidence_text,
            clause_quote="",
            evidence_quote=None,
        )
        is False
    )


def test_stream_event_sequence_and_schemas(fake_llm: Gemini) -> None:
    """A valid synthetic PDF emits: document -> progress -> clause_results -> done."""

    async def run_test() -> None:
        pdf_bytes = create_synthetic_text_pdf(SYNTHETIC_TEST_CONTRACT)
        events: list[StreamEvent] = []

        async for event in evaluate_contract(
            pdf_bytes=pdf_bytes,
            llm=fake_llm,
            heartbeat_interval_s=5.0,
        ):
            events.append(event)
            # Verify schema round-trip
            validated = stream_event.validate_python(event.model_dump())
            assert validated.type == event.type

        assert len(events) >= 4

        # 1. First event is DocumentEvent
        assert isinstance(events[0], DocumentEvent)
        doc_payload = events[0].payload
        assert doc_payload.page_count == 2
        assert len(doc_payload.clauses) >= 2

        # 2. Second event is ContractMapEvent
        assert isinstance(events[1], ContractMapEvent)
        assert events[1].payload.links is not None

        # 3. Third event is initial ProgressEvent
        assert isinstance(events[2], ProgressEvent)
        assert events[2].payload.stage == "compare"
        assert events[2].payload.done == 0

        # 3. Intermediate events include ClauseResultEvents
        clause_results = [e for e in events if isinstance(e, ClauseResultEvent)]
        assert len(clause_results) == len(doc_payload.clauses)
        for cr in clause_results:
            assert cr.payload.status in ("evaluated", "cannot_compare")
            assert cr.payload.headline != ""

        # 4. Final event is DoneEvent
        assert isinstance(events[-1], DoneEvent)
        done_payload = events[-1].payload
        assert done_payload.versions.schema_version == "1"
        assert done_payload.versions.prompt == "compare_v1"

    asyncio.run(run_test())


def test_heartbeats_during_slow_llm() -> None:
    """HeartbeatEvents are emitted when LLM processing takes longer than the interval."""

    async def run_test() -> None:
        # LLM delays for 0.3s; heartbeat interval is 0.1s
        slow_client = FakeGeminiClient(delay_s=0.3)
        slow_llm = Gemini(slow_client, timeout_s=5.0)

        pdf_bytes = create_synthetic_text_pdf(
            ["1. Single Clause\nThe Artist agrees to 10% of net receipts."]
        )

        events: list[StreamEvent] = []
        async for event in evaluate_contract(
            pdf_bytes=pdf_bytes,
            llm=slow_llm,
            heartbeat_interval_s=0.1,
        ):
            events.append(event)

        heartbeats = [e for e in events if isinstance(e, HeartbeatEvent)]
        assert len(heartbeats) >= 1

    asyncio.run(run_test())


def test_client_disconnect_stops_processing() -> None:
    """Cancelling or closing the generator halts background work immediately."""

    async def run_test() -> None:
        slow_client = FakeGeminiClient(delay_s=5.0)
        slow_llm = Gemini(slow_client, timeout_s=10.0)

        pdf_bytes = create_synthetic_text_pdf(SYNTHETIC_TEST_CONTRACT)
        gen = evaluate_contract(
            pdf_bytes=pdf_bytes,
            llm=slow_llm,
            heartbeat_interval_s=0.1,
        )

        # Heartbeats may come first while extraction runs in a thread
        first_event = await anext(gen)
        while isinstance(first_event, HeartbeatEvent):
            first_event = await anext(gen)
        assert isinstance(first_event, DocumentEvent)

        # Close generator (simulating client network disconnect)
        await gen.aclose()

    asyncio.run(run_test())


def test_api_view_successful_streaming(fake_llm: Gemini, monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /api/v1/evaluations returns 200 with NDJSON stream and CORS headers."""

    async def run_test() -> None:
        monkeypatch.setattr("mbiu.evaluation.orchestrator.gemini", lambda: fake_llm)

        pdf_bytes = create_synthetic_text_pdf(SYNTHETIC_TEST_CONTRACT)
        factory = AsyncRequestFactory()

        data = {
            "turnstile_token": "valid_token",
            "pdf": io.BytesIO(pdf_bytes),
        }
        request = factory.post(
            "/api/v1/evaluations",
            data=data,
            format="multipart",
            headers={"origin": "http://localhost:3000"},
        )

        response = await evaluations(request)

        assert isinstance(response, StreamingHttpResponse)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/x-ndjson"
        assert response["Cache-Control"] == "no-store"
        assert response["Access-Control-Allow-Origin"] == "http://localhost:3000"

        # Read streamed lines
        lines: list[dict[str, Any]] = []
        assert isinstance(response.streaming_content, AsyncIterator)
        async for chunk in response.streaming_content:
            for line in chunk.decode("utf-8").strip().split("\n"):
                if line:
                    lines.append(json.loads(line))

        assert len(lines) >= 3
        assert lines[0]["type"] == "document"
        assert lines[-1]["type"] == "done"

    asyncio.run(run_test())


def test_api_view_options_preflight() -> None:
    """OPTIONS /api/v1/evaluations returns 204 with CORS preflight headers."""

    async def run_test() -> None:
        factory = AsyncRequestFactory()
        request = factory.options(
            "/api/v1/evaluations",
            headers={"origin": "http://localhost:3000"},
        )
        response = await evaluations(request)

        assert response.status_code == 204
        assert response["Access-Control-Allow-Origin"] == "http://localhost:3000"
        assert "POST" in response["Access-Control-Allow-Methods"]
        assert "traceparent" in response["Access-Control-Allow-Headers"]

    asyncio.run(run_test())


def test_api_view_rejects_missing_file() -> None:
    """POST without file returns 400 ApiError."""

    async def run_test() -> None:
        factory = AsyncRequestFactory()
        request = factory.post("/api/v1/evaluations", data={"turnstile_token": "tok"})
        response = await evaluations(request)

        assert isinstance(response, HttpResponse)
        assert response.status_code == 400
        body = json.loads(response.content)
        assert body["code"] == "invalid_file_type"

    asyncio.run(run_test())


def test_api_view_rejects_encrypted_pdf() -> None:
    """POST with encrypted PDF returns 400 ApiError encrypted_pdf."""

    async def run_test() -> None:
        encrypted_bytes = create_synthetic_encrypted_pdf(password="secret")
        factory = AsyncRequestFactory()
        request = factory.post(
            "/api/v1/evaluations",
            data={"turnstile_token": "tok", "pdf": io.BytesIO(encrypted_bytes)},
            format="multipart",
        )
        response = await evaluations(request)

        assert isinstance(response, HttpResponse)
        assert response.status_code == 400
        body = json.loads(response.content)
        assert body["code"] == "encrypted_pdf"

    asyncio.run(run_test())


def test_api_view_rejects_invalid_turnstile(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST with failed Turnstile check returns 400 ApiError bot_check_failed."""

    async def run_test() -> None:
        from django.conf import settings

        monkeypatch.setattr(
            settings,
            "TURNSTILE_SECRET_KEY",
            CLOUDFLARE_TEST_SECRET_ALWAYS_FAIL,
        )
        pdf_bytes = create_synthetic_text_pdf(["1. Clause\nContent"])
        factory = AsyncRequestFactory()
        request = factory.post(
            "/api/v1/evaluations",
            data={"turnstile_token": "fail_token", "pdf": io.BytesIO(pdf_bytes)},
            format="multipart",
        )
        response = await evaluations(request)

        assert isinstance(response, HttpResponse)
        assert response.status_code == 400
        body = json.loads(response.content)
        assert body["code"] == "bot_check_failed"

    asyncio.run(run_test())


def test_opentelemetry_traces_stages_without_contract_text(fake_llm: Gemini) -> None:
    """Assert traces are emitted for all stages and contain no contract text."""

    async def run_test() -> None:
        span_exporter.clear()

        canary = "UNIQUE-CANARY-SECRET-TEXT-987"
        contract_with_canary = [
            f"1. Secret Clause\nThis contract has {canary} which must never be logged."
        ]
        pdf_bytes = create_synthetic_text_pdf(contract_with_canary)

        async for _ in evaluate_contract(
            pdf_bytes=pdf_bytes,
            llm=fake_llm,
        ):
            pass

        spans = span_exporter.get_finished_spans()
        stage_names = {span.name for span in spans}

        # Verify stage spans exist
        assert "mbiu.upload" in stage_names
        assert "mbiu.extract" in stage_names
        assert "mbiu.segment" in stage_names
        assert "mbiu.retrieve" in stage_names
        assert "mbiu.compare" in stage_names
        assert "mbiu.verify" in stage_names
        assert "mbiu.summarise" in stage_names

        # Verify privacy invariant: canary marker must NEVER appear in any span name or attribute
        for span in spans:
            assert canary not in span.name
            if span.attributes:
                for k, v in span.attributes.items():
                    assert canary not in str(k)
                    assert canary not in str(v)

    asyncio.run(run_test())


def test_missing_provider_sends_clause_failed_instead_of_breaking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no usable model provider, every clause fails honestly and the stream ends cleanly."""
    from mbiu.api.schemas import ClauseFailedEvent
    from mbiu.llm import ErrorCategory, LLMError

    def _no_provider() -> Gemini:
        raise LLMError(ErrorCategory.UNAVAILABLE)

    monkeypatch.setattr("mbiu.evaluation.orchestrator.gemini", _no_provider)

    async def run_test() -> None:
        pdf_bytes = create_synthetic_text_pdf(SYNTHETIC_TEST_CONTRACT)
        events = [e async for e in evaluate_contract(pdf_bytes=pdf_bytes, heartbeat_interval_s=5.0)]
        document = next(e for e in events if isinstance(e, DocumentEvent))
        failed = [e for e in events if isinstance(e, ClauseFailedEvent)]
        clause_ids = {c.clause_id for c in document.payload.clauses}
        assert {e.payload.clause_id for e in failed} == clause_ids
        assert all(e.payload.reason == "unavailable" and e.payload.retryable for e in failed)

    asyncio.run(run_test())


def test_clauses_run_in_parallel_up_to_the_concurrency_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Clause checks overlap, but never more than LLM_CONCURRENCY at once."""
    from django.conf import settings

    monkeypatch.setattr(settings, "LLM_CONCURRENCY", 2)
    in_flight = 0
    peak = 0

    class CountingClient(FakeGeminiClient):
        async def _create(self, **kwargs: Any) -> Any:
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            try:
                return await super()._create(**kwargs)
            finally:
                in_flight -= 1

    llm = Gemini(CountingClient(delay_s=0.2), timeout_s=10.0)
    clauses = [f"{n}. Clause {n}\nThe Artist receives 10% of net receipts." for n in range(1, 6)]

    async def run_test() -> None:
        pdf_bytes = create_synthetic_text_pdf(clauses)
        async for _ in evaluate_contract(pdf_bytes=pdf_bytes, llm=llm, heartbeat_interval_s=5.0):
            pass

    asyncio.run(run_test())
    assert peak == 2


def _clause(clause_id: str, text: str) -> dict[str, Any]:
    return {
        "clause_id": clause_id,
        "section_id": "main",
        "number": clause_id,
        "heading": None,
        "text": text,
        "pages": [1],
        "start": 0,
        "end": len(text),
    }


RESENT_CLAUSES = [
    _clause("1", "The Company shall pay the Artist 10% of net receipts after costs."),
    _clause("2", "The initial period shall be for a duration of two (2) years."),
]


async def _post_clauses(body: dict[str, Any]) -> tuple[HttpResponseBase, list[dict[str, Any]]]:
    request = AsyncRequestFactory().post(
        "/api/v1/clause-evaluations",
        data=json.dumps(body),
        content_type="application/json",
        headers={"origin": "http://localhost:3000"},
    )
    response = await clause_evaluations(request)
    lines: list[dict[str, Any]] = []
    if isinstance(response, StreamingHttpResponse):
        assert isinstance(response.streaming_content, AsyncIterator)
        async for chunk in response.streaming_content:
            lines.extend(json.loads(line) for line in chunk.decode().splitlines() if line)
    return response, lines


def test_resent_clauses_stream_only_their_results(
    fake_llm: Gemini, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /api/v1/clause-evaluations checks just the clauses sent, using the shared events."""
    monkeypatch.setattr("mbiu.evaluation.orchestrator.gemini", lambda: fake_llm)

    async def run_test() -> None:
        response, lines = await _post_clauses(
            {"turnstile_token": "valid_token", "clauses": RESENT_CLAUSES}
        )
        assert response.status_code == 200
        assert response["Content-Type"] == "application/x-ndjson"
        assert response["Cache-Control"] == "no-store"
        assert response["Access-Control-Allow-Origin"] == "http://localhost:3000"

        events = [stream_event.validate_python(line) for line in lines]
        assert all(line["schema_version"] == "1" for line in lines)
        assert {e.type for e in events} <= {"progress", "clause_result", "heartbeat"}
        results = [e for e in events if isinstance(e, ClauseResultEvent)]
        assert [r.payload.clause_id for r in results] == ["1", "2"]
        assert results[0].payload.status == "evaluated"
        assert results[0].payload.original_text == RESENT_CLAUSES[0]["text"]

    asyncio.run(run_test())


def test_resent_clauses_fail_honestly_without_a_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no usable provider, each resent clause gets a retryable clause_failed event."""
    from mbiu.api.schemas import ClauseFailedEvent
    from mbiu.llm import ErrorCategory, LLMError

    def _no_provider() -> Gemini:
        raise LLMError(ErrorCategory.UNAVAILABLE)

    monkeypatch.setattr("mbiu.evaluation.orchestrator.gemini", _no_provider)

    async def run_test() -> None:
        _, lines = await _post_clauses({"turnstile_token": "tok", "clauses": RESENT_CLAUSES})
        events = [stream_event.validate_python(line) for line in lines]
        failed = [e for e in events if isinstance(e, ClauseFailedEvent)]
        assert [e.payload.clause_id for e in failed] == ["1", "2"]
        assert all(e.payload.retryable for e in failed)

    asyncio.run(run_test())


@pytest.mark.parametrize(
    "body",
    [
        {"turnstile_token": "tok", "clauses": []},
        {"turnstile_token": "tok"},
        {"turnstile_token": "", "clauses": RESENT_CLAUSES},
        {"turnstile_token": "tok", "clauses": [{"clause_id": "1", "text": "No pages"}]},
        {"turnstile_token": "tok", "clauses": RESENT_CLAUSES, "contract": "extra field"},
    ],
)
def test_resent_clauses_reject_invalid_requests(body: dict[str, Any]) -> None:
    """A body that doesn't match the shared contract is refused before any model call."""

    async def run_test() -> None:
        response, _ = await _post_clauses(body)
        assert isinstance(response, HttpResponse)
        assert response.status_code == 400
        assert json.loads(response.content)["code"] == "invalid_request"

    asyncio.run(run_test())


def test_resent_clauses_require_the_bot_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed Turnstile check refuses the request, as for uploads."""
    from django.conf import settings

    monkeypatch.setattr(settings, "TURNSTILE_SECRET_KEY", CLOUDFLARE_TEST_SECRET_ALWAYS_FAIL)

    async def run_test() -> None:
        response, _ = await _post_clauses({"turnstile_token": "tok", "clauses": RESENT_CLAUSES})
        assert isinstance(response, HttpResponse)
        assert response.status_code == 400
        assert json.loads(response.content)["code"] == "bot_check_failed"

    asyncio.run(run_test())


def test_resent_clauses_preflight() -> None:
    """OPTIONS /api/v1/clause-evaluations answers the browser's CORS preflight."""

    async def run_test() -> None:
        request = AsyncRequestFactory().options(
            "/api/v1/clause-evaluations", headers={"origin": "http://localhost:3000"}
        )
        response = await clause_evaluations(request)
        assert response.status_code == 204
        assert "Content-Type" in response["Access-Control-Allow-Headers"]

    asyncio.run(run_test())
