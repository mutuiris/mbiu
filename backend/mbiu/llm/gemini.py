import json
import random
import time
from functools import cache
from typing import Any

import httpx
import pybreaker
from django.conf import settings
from google import genai
from google.genai import errors as genai_sdk_errors
from google.genai import types
from google.genai._gaos.lib import compat_errors as gemini_errors
from opentelemetry import trace
from pydantic import BaseModel, ValidationError
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, stop_any
from tenacity.stop import stop_base
from tenacity.wait import wait_base

from mbiu.llm import ErrorCategory, LLMError, LLMResult

tracer = trace.get_tracer("mbiu.llm")

MAX_ATTEMPTS = 2  # one retry and only for rate limits, timeouts and server errors
BREAKER_FAIL_MAX = 5
BREAKER_RESET_S = 60


def _classify(exc: BaseException) -> LLMError:
    if isinstance(exc, LLMError):
        return exc
    if isinstance(exc, (TimeoutError, gemini_errors.APITimeoutError, httpx.TimeoutException)):
        return LLMError(ErrorCategory.TIMEOUT, retryable=True, outage=True)
    if isinstance(exc, gemini_errors.APIConnectionError):
        return LLMError(ErrorCategory.UNAVAILABLE, retryable=True, outage=True)
    if isinstance(exc, (gemini_errors.APIStatusError, genai_sdk_errors.APIError)):
        raw_status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        status = int(raw_status) if isinstance(raw_status, int) else 0
        if status == 429:
            resp = getattr(exc, "response", None)
            headers = getattr(resp, "headers", None)
            retry_after = headers.get("retry-after") if headers is not None else None
            delay = float(retry_after) if retry_after and retry_after.isdigit() else None
            return LLMError(
                ErrorCategory.RATE_LIMITED, retryable=True, outage=True, retry_after_s=delay
            )
        if status >= 500:
            return LLMError(ErrorCategory.UNAVAILABLE, retryable=True, outage=True)
        if status in (401, 402, 403):  # bad key, no credits, no access: every call will fail
            return LLMError(ErrorCategory.UNAVAILABLE, outage=True)
        return LLMError(ErrorCategory.SCHEMA_INVALID)  # 400/422: the request itself was wrong
    return LLMError(ErrorCategory.UNAVAILABLE, outage=True)


class _StopNearDeadline(stop_base):
    """Stop retrying when less than a second is left before the deadline."""

    def __init__(self, deadline: float) -> None:
        self._deadline = deadline

    def __call__(self, retry_state: Any) -> bool:
        return self._deadline - time.monotonic() < 1.0


class _WaitWithinDeadline(wait_base):
    """Honour Retry-After when given, otherwise a short jittered pause; never past the deadline."""

    def __init__(self, deadline: float) -> None:
        self._deadline = deadline

    def __call__(self, retry_state: Any) -> float:
        outcome = retry_state.outcome
        error = outcome.exception() if outcome else None
        if isinstance(error, LLMError) and error.retry_after_s is not None:
            pause = error.retry_after_s
        else:
            pause = random.uniform(0.5, 2.0)
        return max(0.0, min(pause, self._deadline - time.monotonic() - 1.0))


class Gemini:
    """Gemini through the Interactions API, with storage off on every call."""

    provider = "gemini"

    def __init__(self, client: Any, *, timeout_s: float) -> None:
        self._client = client
        self._timeout_s = timeout_s
        self._breaker = pybreaker.CircuitBreaker(
            fail_max=BREAKER_FAIL_MAX,
            reset_timeout=BREAKER_RESET_S,
            exclude=[lambda exc: isinstance(exc, LLMError) and not exc.outage],
            name="gemini",
        )

    async def generate[T: BaseModel](
        self,
        *,
        model: str,
        instructions: str,
        content: str,
        output: type[T],
        deadline: float,
        temperature: float = 0.1,
    ) -> LLMResult[T]:
        """Ask for JSON matching `output` and return it validated.

        `deadline` is a `time.monotonic()` value; no attempt or retry runs past it.
        Fixed instructions go first and per-request content last, so the shared prefix
        can be cached.
        """
        schema = output.model_json_schema()
        retrying = AsyncRetrying(
            stop=stop_any(stop_after_attempt(MAX_ATTEMPTS), _StopNearDeadline(deadline)),
            retry=retry_if_exception(lambda e: isinstance(e, LLMError) and e.retryable),
            wait=_WaitWithinDeadline(deadline),
            reraise=True,
        )

        with tracer.start_as_current_span("llm.call") as span:
            span.set_attribute("llm.provider", self.provider)
            span.set_attribute("llm.model", model)
            try:
                result: LLMResult[T] = await retrying(
                    self._attempt,
                    model,
                    instructions,
                    content,
                    schema,
                    output,
                    deadline,
                    temperature,
                )
            except LLMError as error:
                span.set_attribute("llm.error_category", error.category.value)
                raise
            finally:
                span.set_attribute("llm.attempts", retrying.statistics.get("attempt_number", 0))
            span.set_attribute("llm.model_version", result.model_version)
            if result.input_tokens is not None:
                span.set_attribute("llm.input_tokens", result.input_tokens)
            if result.output_tokens is not None:
                span.set_attribute("llm.output_tokens", result.output_tokens)
            return result

    async def _attempt[T: BaseModel](
        self,
        model: str,
        instructions: str,
        content: str,
        schema: dict[str, Any],
        output: type[T],
        deadline: float,
        temperature: float,
    ) -> LLMResult[T]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise LLMError(ErrorCategory.TIMEOUT)
        try:
            with self._breaker.calling():
                try:
                    interaction = await self._client.aio.interactions.create(
                        model=model,
                        system_instruction=instructions,
                        input=content,
                        response_format={"mime_type": "application/json", "schema": schema},
                        generation_config={
                            "temperature": temperature,
                            "thinking_level": settings.GEMINI_THINKING_LEVEL,
                        },
                        store=False,  # never let the provider keep contract text
                        timeout=min(self._timeout_s, remaining),
                    )
                except Exception as exc:
                    raise _classify(exc) from None
        except pybreaker.CircuitBreakerError:
            raise LLMError(ErrorCategory.UNAVAILABLE) from None

        text = getattr(interaction, "output_text", None)
        if getattr(interaction, "status", "completed") != "completed" or not text:
            raise LLMError(ErrorCategory.REFUSED)
        try:
            value = output.model_validate_json(text)
        except ValidationError, json.JSONDecodeError:
            raise LLMError(ErrorCategory.SCHEMA_INVALID) from None
        usage = getattr(interaction, "usage", None)
        return LLMResult(
            value=value,
            provider=self.provider,
            model_version=getattr(interaction, "model", None) or model,
            input_tokens=getattr(usage, "total_input_tokens", None),
            output_tokens=getattr(usage, "total_output_tokens", None),
        )


@cache
def gemini() -> Gemini:
    """The process-wide Gemini adapter (one circuit breaker per provider)."""
    if not settings.GEMINI_API_KEY:
        raise LLMError(ErrorCategory.UNAVAILABLE)
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        # The adapter retries within the deadline itself. The SDK's own retries would
        # multiply every timeout and blow through the contract's time budget.
        http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=0)),
    )
    return Gemini(client, timeout_s=settings.BATCH_TIMEOUT_S)
