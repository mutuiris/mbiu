"""Unit and failure-injection tests for OpenAI adapter and orchestrator failover (MB-20).

Verifies:
1. OpenAI provider enforces store: false on every call, strict JSON schema, retries,
   breaker, and refusal mapping.
2. Failure injection with a fake provider simulating:
   - Slow provider / timeout
   - 429 rate limit
   - Invalid JSON / schema mismatch
   - Citing an unsent ID
   - Inventing a number or hallucinating a quote
   - Refusal mapping to evaluation_failed
3. Failover behavior:
   - Used only when Gemini breaker is open or 5xx/timeout survived one retry.
   - Never as a second opinion.
   - One provider per batch recorded on every result.
   - Behind FAILOVER_ENABLED (default False).
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from google.genai._gaos.lib import compat_errors as gemini_errors
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import BaseModel

from mbiu.api.schemas import ClauseResultEvent, ClauseStatus, Outcome, Provider, StreamEvent
from mbiu.evaluation.orchestrator import (
    ClauseComparisonProposal,
    evaluate_contract,
    verify_quotes,
)
from mbiu.llm import ErrorCategory, LLMError, as_data
from mbiu.llm.gemini import Gemini
from mbiu.llm.openai import BREAKER_FAIL_MAX, OpenAI
from tests.pdf_factories import create_synthetic_text_pdf

MBIU_ROOT = Path(__file__).resolve().parents[1] / "mbiu"
CANARY = "CANARY-openai-9a8b7c"

spans = InMemorySpanExporter()
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(spans))
trace.set_tracer_provider(provider)


@pytest.fixture(autouse=True)
def no_retry_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mbiu.llm.openai.random.uniform", lambda a, b: 0.0)
    monkeypatch.setattr("mbiu.llm.gemini.random.uniform", lambda a, b: 0.0)


class Verdict(BaseModel):
    outcome: str
    quote: str


class FakeHTTPResponse:
    def __init__(
        self,
        data: dict[str, Any],
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._data = data
        self.status_code = status_code
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        return self._data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
            resp = httpx.Response(self.status_code, request=req, headers=self.headers)
            raise httpx.HTTPStatusError("HTTP Error", request=req, response=resp)


def openai_success_response(
    content: str = '{"outcome": "worse_for_you", "quote": "8% of net receipts"}',
    *,
    refusal: str | None = None,
    finish_reason: str = "stop",
    model: str = "gpt-4o-mini-2024-07-18",
    prompt_tokens: int = 150,
    completion_tokens: int = 40,
) -> FakeHTTPResponse:
    data = {
        "id": "chatcmpl-test-123",
        "object": "chat.completion",
        "created": 1720000000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                    "refusal": refusal,
                },
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
    return FakeHTTPResponse(data)


def status_error(code: int, headers: dict[str, str] | None = None) -> Exception:
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    resp = httpx.Response(code, request=req, headers=headers or {})
    return httpx.HTTPStatusError(f"HTTP {code}", request=req, response=resp)


class FakeHTTPClient:
    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    async def post(self, url: str, **kwargs: Any) -> Any:
        self.calls.append({"url": url, **kwargs})
        if not self.outcomes:
            raise RuntimeError("FakeHTTPClient ran out of outcomes")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def run_openai(client: FakeHTTPClient, deadline_s: float = 30.0) -> Any:
    adapter = OpenAI(client, api_key="test-openai-key", timeout_s=10.0)
    return asyncio.run(
        adapter.generate(
            model="gpt-4o-mini",
            instructions="Compare clause with template.",
            content=as_data("contract_clause", CANARY),
            output=Verdict,
            deadline=time.monotonic() + deadline_s,
        )
    )


# ---------------------------------------------------------------------------
# SECTION 1: OpenAI Adapter Unit Tests
# ---------------------------------------------------------------------------


def test_openai_returns_validated_output_with_metadata() -> None:
    client = FakeHTTPClient(openai_success_response())
    result = run_openai(client)
    assert result.value == Verdict(outcome="worse_for_you", quote="8% of net receipts")
    assert result.provider == "openai"
    assert result.model_version == "gpt-4o-mini-2024-07-18"
    assert (result.input_tokens, result.output_tokens) == (150, 40)


def test_openai_every_call_sets_store_false_and_strict_json_schema() -> None:
    client = FakeHTTPClient(status_error(503), openai_success_response())
    run_openai(client)
    assert len(client.calls) == 2
    for call in client.calls:
        payload = call["json"]
        assert payload["store"] is False
        assert payload["response_format"]["type"] == "json_schema"
        json_schema = payload["response_format"]["json_schema"]
        assert json_schema["strict"] is True
        schema = json_schema["schema"]
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"].keys())
        assert "default" not in schema


def test_static_no_openai_call_without_store_false() -> None:
    """Ensure no code in mbiu calls OpenAI without store: False."""
    openai_py = MBIU_ROOT / "llm" / "openai.py"
    source = openai_py.read_text(encoding="utf-8")
    assert '"store": False' in source or "'store': False" in source


@pytest.mark.parametrize(
    ("error", "category"),
    [
        (status_error(429, {"retry-after": "0"}), ErrorCategory.RATE_LIMITED),
        (status_error(500), ErrorCategory.UNAVAILABLE),
        (status_error(503), ErrorCategory.UNAVAILABLE),
        (
            httpx.TimeoutException("Timeout", request=httpx.Request("POST", "https://x.invalid")),
            ErrorCategory.TIMEOUT,
        ),
    ],
)
def test_openai_transient_errors_retry_once_then_raise(
    error: Exception, category: ErrorCategory
) -> None:
    client = FakeHTTPClient(error, error)
    with pytest.raises(LLMError) as exc_info:
        run_openai(client)
    assert exc_info.value.category == category
    assert len(client.calls) == 2


def test_openai_transient_error_recovers_on_retry() -> None:
    client = FakeHTTPClient(status_error(502), openai_success_response())
    result = run_openai(client)
    assert result.value.outcome == "worse_for_you"
    assert len(client.calls) == 2


@pytest.mark.parametrize(
    ("outcome", "category"),
    [
        (status_error(401), ErrorCategory.UNAVAILABLE),
        (status_error(403), ErrorCategory.UNAVAILABLE),
        (status_error(400), ErrorCategory.SCHEMA_INVALID),
        (status_error(422), ErrorCategory.SCHEMA_INVALID),
        (openai_success_response(content="invalid json"), ErrorCategory.SCHEMA_INVALID),
        (openai_success_response(content='{"outcome": "worse"}'), ErrorCategory.SCHEMA_INVALID),
        (openai_success_response(content=""), ErrorCategory.REFUSED),
        (openai_success_response(refusal="Content policy restriction"), ErrorCategory.REFUSED),
        (openai_success_response(finish_reason="content_filter"), ErrorCategory.REFUSED),
    ],
)
def test_openai_permanent_failures_are_not_retried(outcome: Any, category: ErrorCategory) -> None:
    client = FakeHTTPClient(outcome, openai_success_response())
    with pytest.raises(LLMError) as exc_info:
        run_openai(client)
    assert exc_info.value.category == category
    assert len(client.calls) == 1


def test_openai_no_retry_near_deadline() -> None:
    client = FakeHTTPClient(status_error(500), openai_success_response())
    with pytest.raises(LLMError):
        run_openai(client, deadline_s=0.5)
    assert len(client.calls) == 1


def test_openai_breaker_opens_after_repeated_outages() -> None:
    outages = [status_error(500)] * (BREAKER_FAIL_MAX * 2)
    client = FakeHTTPClient(*outages)
    adapter = OpenAI(client, api_key="test-key", timeout_s=10.0)

    async def call() -> None:
        await adapter.generate(
            model="gpt-4o-mini",
            instructions="i",
            content="c",
            output=Verdict,
            deadline=time.monotonic() + 30,
        )

    for _ in range(BREAKER_FAIL_MAX):
        with pytest.raises(LLMError):
            asyncio.run(call())
    calls_before = len(client.calls)
    with pytest.raises(LLMError) as raised:
        asyncio.run(call())
    assert raised.value.category == ErrorCategory.UNAVAILABLE
    assert len(client.calls) == calls_before  # Circuit breaker open: no call made


def test_openai_spans_carry_no_prompt_or_response_text() -> None:
    spans.clear()
    client = FakeHTTPClient(
        openai_success_response(content=f'{{"outcome": "x", "quote": "{CANARY}"}}')
    )
    run_openai(client)
    with pytest.raises(LLMError) as exc_info:
        run_openai(FakeHTTPClient(openai_success_response(content=CANARY)))
    assert CANARY not in str(exc_info.value)
    for span in spans.get_finished_spans():
        for key, value in (span.attributes or {}).items():
            assert CANARY not in str(value), key
            assert key.startswith("llm.")


# ---------------------------------------------------------------------------
# SECTION 2: Failure Injection & Orchestrator Failover Tests
# ---------------------------------------------------------------------------


class MockGeminiClient:
    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []
        self.aio = SimpleNamespace(interactions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if not self.outcomes:
            raise RuntimeError("MockGeminiClient ran out of outcomes")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def gemini_answer(proposal: ClauseComparisonProposal) -> Any:
    return SimpleNamespace(
        status="completed",
        output_text=proposal.model_dump_json(),
        model="gemini-3.8-flash",
        usage=SimpleNamespace(total_input_tokens=100, total_output_tokens=50),
    )


SAMPLE_CONTRACT = [
    (
        "1. Royalties\n"
        "The Company will pay the Artist 10% of net receipts after all distribution costs."
    )
]


def test_failure_injection_invents_a_number_or_quote() -> None:
    """Invents a number or hallucinated quote not in the contract."""
    # Contract says 10%, model invents 50%
    clause_text = (
        "The Company will pay the Artist 10% of net receipts after all distribution costs."
    )
    evidence_text = "Standard royalty is 15% of Gross Receipts."

    assert (
        verify_quotes(
            clause_text=clause_text,
            evidence_text=evidence_text,
            clause_quote="50% of net receipts",  # Hallucinated number
            evidence_quote="15% of Gross Receipts",
        )
        is False
    )


def test_failure_injection_cites_unsent_id() -> None:
    """Cites an unsent evidence ID."""
    clause_text = "The Company will pay the Artist 10% of net receipts."
    evidence_text = "Standard royalty is 15%."

    assert (
        verify_quotes(
            clause_text=clause_text,
            evidence_text=evidence_text,
            clause_quote="10% of net receipts",
            evidence_quote="Standard royalty is 15%.",
            evidence_id="fake_template_999",
            allowed_evidence_ids={"std_recording_royalty_v1"},
        )
        is False
    )

    # Valid ID passes
    assert (
        verify_quotes(
            clause_text=clause_text,
            evidence_text=evidence_text,
            clause_quote="10% of net receipts",
            evidence_quote="Standard royalty is 15%.",
            evidence_id="std_recording_royalty_v1",
            allowed_evidence_ids={"std_recording_royalty_v1"},
        )
        is True
    )


def test_failure_injection_slow_gemini_fails_over_to_openai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When Gemini is slow/times out and FAILOVER_ENABLED=True, failover to OpenAI succeeds."""
    monkeypatch.setattr("django.conf.settings.FAILOVER_ENABLED", True)
    monkeypatch.setattr("django.conf.settings.OPENAI_API_KEY", "test-openai-key")

    gemini_client = MockGeminiClient(
        httpx.TimeoutException(
            "Gemini timed out", request=httpx.Request("POST", "https://g.invalid")
        ),
        httpx.TimeoutException(
            "Gemini timed out", request=httpx.Request("POST", "https://g.invalid")
        ),
    )
    gemini_adapter = Gemini(gemini_client, timeout_s=1.0)

    proposal = ClauseComparisonProposal(
        comparison=Outcome.WORSE_FOR_YOU,
        headline="Royalty rate is lower than standard",
        what_it_says="You receive 10% of net receipts after costs.",
        what_it_means="Your royalties will be reduced by label deductions.",
        clause_quote="10% of net receipts",
        evidence_quote=None,
        ask_them="Can the royalty rate be based on gross receipts?",
    )
    openai_client = FakeHTTPClient(openai_success_response(content=proposal.model_dump_json()))
    openai_adapter = OpenAI(openai_client, api_key="test-key", timeout_s=10.0)
    monkeypatch.setattr("mbiu.evaluation.orchestrator.openai", lambda: openai_adapter)

    pdf_bytes = create_synthetic_text_pdf(SAMPLE_CONTRACT)

    async def run_pipeline() -> list[StreamEvent]:
        events = []
        async for event in evaluate_contract(
            pdf_bytes=pdf_bytes,
            turnstile_token="test_token",
            llm=gemini_adapter,
        ):
            events.append(event)
        return events

    events = asyncio.run(run_pipeline())
    clause_results = [e.payload for e in events if isinstance(e, ClauseResultEvent)]
    assert len(clause_results) >= 1
    first_res = clause_results[0]

    assert first_res.status == ClauseStatus.EVALUATED
    assert first_res.comparison == Outcome.WORSE_FOR_YOU
    assert first_res.provider == Provider.OPENAI
    assert len(gemini_client.calls) == 2  # Gemini tried and retried once
    assert len(openai_client.calls) == 1  # OpenAI succeeded on failover


def test_failure_injection_slow_gemini_without_failover(monkeypatch: pytest.MonkeyPatch) -> None:
    """When Gemini times out and FAILOVER_ENABLED=False, honest error fallback is returned."""
    monkeypatch.setattr("django.conf.settings.FAILOVER_ENABLED", False)

    gemini_client = MockGeminiClient(
        httpx.TimeoutException(
            "Gemini timed out", request=httpx.Request("POST", "https://g.invalid")
        ),
        httpx.TimeoutException(
            "Gemini timed out", request=httpx.Request("POST", "https://g.invalid")
        ),
    )
    gemini_adapter = Gemini(gemini_client, timeout_s=1.0)

    pdf_bytes = create_synthetic_text_pdf(SAMPLE_CONTRACT)

    async def run_pipeline() -> list[StreamEvent]:
        events = []
        async for event in evaluate_contract(
            pdf_bytes=pdf_bytes,
            turnstile_token="test_token",
            llm=gemini_adapter,
        ):
            events.append(event)
        return events

    events = asyncio.run(run_pipeline())
    clause_results = [e.payload for e in events if isinstance(e, ClauseResultEvent)]
    assert len(clause_results) >= 1
    first_res = clause_results[0]

    assert first_res.status == ClauseStatus.CANNOT_COMPARE
    assert first_res.provider == Provider.GEMINI
    assert "timeout" in first_res.what_it_means


def test_failure_injection_gemini_breaker_open_calls_openai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When Gemini's breaker is open and FAILOVER_ENABLED=True, OpenAI is called immediately."""
    monkeypatch.setattr("django.conf.settings.FAILOVER_ENABLED", True)
    monkeypatch.setattr("django.conf.settings.OPENAI_API_KEY", "test-openai-key")

    gemini_client = MockGeminiClient()
    gemini_adapter = Gemini(gemini_client, timeout_s=1.0)
    # Trip the breaker directly
    gemini_adapter._breaker._state_storage.state = "open"

    proposal = ClauseComparisonProposal(
        comparison=Outcome.WORSE_FOR_YOU,
        headline="Royalty rate is lower than standard",
        what_it_says="You receive 10% of net receipts after costs.",
        what_it_means="Your royalties will be reduced by label deductions.",
        clause_quote="10% of net receipts",
        evidence_quote=None,
        ask_them="Can the royalty rate be based on gross receipts?",
    )
    openai_client = FakeHTTPClient(openai_success_response(content=proposal.model_dump_json()))
    openai_adapter = OpenAI(openai_client, api_key="test-key", timeout_s=10.0)
    monkeypatch.setattr("mbiu.evaluation.orchestrator.openai", lambda: openai_adapter)

    pdf_bytes = create_synthetic_text_pdf(SAMPLE_CONTRACT)

    async def run_pipeline() -> list[StreamEvent]:
        events = []
        async for event in evaluate_contract(
            pdf_bytes=pdf_bytes,
            turnstile_token="test_token",
            llm=gemini_adapter,
        ):
            events.append(event)
        return events

    events = asyncio.run(run_pipeline())
    clause_results = [e.payload for e in events if isinstance(e, ClauseResultEvent)]
    assert len(clause_results) >= 1
    first_res = clause_results[0]

    assert first_res.status == ClauseStatus.EVALUATED
    assert first_res.provider == Provider.OPENAI
    assert len(gemini_client.calls) == 0  # Gemini was never called due to open breaker
    assert len(openai_client.calls) == 1


def test_failure_injection_429_returns_rate_limited_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rate limit 429 retries once, then returns cannot_compare fallback without failing over."""
    monkeypatch.setattr("django.conf.settings.FAILOVER_ENABLED", True)

    req = httpx.Request("POST", "https://api.google.com")
    resp = httpx.Response(429, request=req, headers={"retry-after": "0"})
    exc = gemini_errors.RateLimitError("Rate limited", response=resp, body=None)

    gemini_client = MockGeminiClient(exc, exc)
    gemini_adapter = Gemini(gemini_client, timeout_s=1.0)

    pdf_bytes = create_synthetic_text_pdf(SAMPLE_CONTRACT)

    async def run_pipeline() -> list[StreamEvent]:
        events = []
        async for event in evaluate_contract(
            pdf_bytes=pdf_bytes,
            turnstile_token="test_token",
            llm=gemini_adapter,
        ):
            events.append(event)
        return events

    events = asyncio.run(run_pipeline())
    clause_results = [e.payload for e in events if isinstance(e, ClauseResultEvent)]
    assert len(clause_results) >= 1
    first_res = clause_results[0]

    assert first_res.status == ClauseStatus.CANNOT_COMPARE
    assert first_res.provider == Provider.GEMINI
    assert "rate_limited" in first_res.what_it_means


def test_failure_injection_refusal_maps_to_evaluation_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When a provider refuses, orchestrator produces status=ClauseStatus.EVALUATION_FAILED."""
    monkeypatch.setattr("django.conf.settings.FAILOVER_ENABLED", False)

    # Empty text maps to REFUSED
    empty_res = SimpleNamespace(
        status="completed",
        output_text="",
        model="gemini-3.8-flash",
        usage=None,
    )
    gemini_client = MockGeminiClient(empty_res)
    gemini_adapter = Gemini(gemini_client, timeout_s=1.0)

    pdf_bytes = create_synthetic_text_pdf(SAMPLE_CONTRACT)

    async def run_pipeline() -> list[StreamEvent]:
        events = []
        async for event in evaluate_contract(
            pdf_bytes=pdf_bytes,
            turnstile_token="test_token",
            llm=gemini_adapter,
        ):
            events.append(event)
        return events

    events = asyncio.run(run_pipeline())
    clause_results = [e.payload for e in events if isinstance(e, ClauseResultEvent)]
    assert len(clause_results) >= 1
    first_res = clause_results[0]

    assert first_res.status == ClauseStatus.EVALUATION_FAILED
    assert first_res.headline == "AI evaluation refused by provider"
    assert first_res.comparison == Outcome.CANNOT_COMPARE


def test_failure_injection_invalid_json_maps_to_cannot_compare(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When provider returns malformed JSON, status is cannot_compare."""
    monkeypatch.setattr("django.conf.settings.FAILOVER_ENABLED", False)

    invalid_res = SimpleNamespace(
        status="completed",
        output_text="not valid json at all",
        model="gemini-3.8-flash",
        usage=None,
    )
    gemini_client = MockGeminiClient(invalid_res)
    gemini_adapter = Gemini(gemini_client, timeout_s=1.0)

    pdf_bytes = create_synthetic_text_pdf(SAMPLE_CONTRACT)

    async def run_pipeline() -> list[StreamEvent]:
        events = []
        async for event in evaluate_contract(
            pdf_bytes=pdf_bytes,
            turnstile_token="test_token",
            llm=gemini_adapter,
        ):
            events.append(event)
        return events

    events = asyncio.run(run_pipeline())
    clause_results = [e.payload for e in events if isinstance(e, ClauseResultEvent)]
    assert len(clause_results) >= 1
    first_res = clause_results[0]

    assert first_res.status == ClauseStatus.CANNOT_COMPARE
    assert "schema_invalid" in first_res.what_it_means


def test_never_second_opinion_when_gemini_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAI is NEVER called if Gemini successfully evaluates."""
    monkeypatch.setattr("django.conf.settings.FAILOVER_ENABLED", True)

    proposal = ClauseComparisonProposal(
        comparison=Outcome.MATCHES_STANDARD,
        headline="Matches standard",
        what_it_says="Clause says standard terms.",
        what_it_means="No issues found.",
        clause_quote="10% of net receipts",
        evidence_quote=None,
        ask_them=None,
    )
    gemini_client = MockGeminiClient(gemini_answer(proposal))
    gemini_adapter = Gemini(gemini_client, timeout_s=5.0)

    openai_called = False

    def fake_openai() -> Any:
        nonlocal openai_called
        openai_called = True
        raise RuntimeError("OpenAI should never be called!")

    monkeypatch.setattr("mbiu.evaluation.orchestrator.openai", fake_openai)

    pdf_bytes = create_synthetic_text_pdf(SAMPLE_CONTRACT)

    async def run_pipeline() -> list[StreamEvent]:
        events = []
        async for event in evaluate_contract(
            pdf_bytes=pdf_bytes,
            turnstile_token="test_token",
            llm=gemini_adapter,
        ):
            events.append(event)
        return events

    events = asyncio.run(run_pipeline())
    clause_results = [e.payload for e in events if isinstance(e, ClauseResultEvent)]
    assert len(clause_results) >= 1
    assert clause_results[0].provider == Provider.GEMINI
    assert not openai_called
