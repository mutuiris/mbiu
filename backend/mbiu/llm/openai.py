"""OpenAI Structured Outputs adapter with strict mode and zero-storage enforcement."""

import copy
import json
import random
import time
from functools import cache
from typing import Any

import httpx
import pybreaker
from django.conf import settings
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


def to_strict_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Transform a Pydantic JSON schema to meet OpenAI Structured Outputs strict mode rules.

    - Every object schema must have 'additionalProperties: false'.
    - 'required' must explicitly list every key present in 'properties'.
    - Strip 'default' keys because OpenAI strict mode rejects default values.
    """
    strict = copy.deepcopy(schema)

    def _clean_node(node: Any) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object" or "properties" in node:
                node["additionalProperties"] = False
                if "properties" in node:
                    node["required"] = list(node["properties"].keys())
            for value in node.values():
                _clean_node(value)
        elif isinstance(node, list):
            for item in node:
                _clean_node(item)

    _clean_node(strict)
    return strict


def _classify_openai(exc: BaseException) -> LLMError:
    """Classify OpenAI client exceptions into standardized LLMError categories."""
    if isinstance(exc, LLMError):
        return exc
    if isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        return LLMError(ErrorCategory.TIMEOUT, retryable=True, outage=True)
    if isinstance(exc, (httpx.ConnectError, httpx.NetworkError)):
        return LLMError(ErrorCategory.UNAVAILABLE, retryable=True, outage=True)
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 429:
            retry_after = exc.response.headers.get("retry-after")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else None
            return LLMError(
                ErrorCategory.RATE_LIMITED, retryable=True, outage=True, retry_after_s=delay
            )
        if status >= 500:
            return LLMError(ErrorCategory.UNAVAILABLE, retryable=True, outage=True)
        if status in (401, 403):
            return LLMError(ErrorCategory.UNAVAILABLE, outage=True)
        if status in (400, 422):
            return LLMError(ErrorCategory.SCHEMA_INVALID)
        return LLMError(ErrorCategory.UNAVAILABLE, outage=True)
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


class OpenAI:
    """OpenAI Structured Outputs adapter with zero storage enforced on every call."""

    provider = "openai"

    def __init__(
        self,
        client: Any,
        *,
        api_key: str | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        """Initialize the OpenAI adapter with a client, API key, and timeout."""
        self._client = client
        self._api_key = api_key or getattr(settings, "OPENAI_API_KEY", "")
        self._timeout_s = timeout_s
        self._breaker = pybreaker.CircuitBreaker(
            fail_max=BREAKER_FAIL_MAX,
            reset_timeout=BREAKER_RESET_S,
            exclude=[lambda exc: isinstance(exc, LLMError) and not exc.outage],
            name="openai",
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
        """Ask for JSON matching `output` in strict mode and return it validated.

        `deadline` is a `time.monotonic()` value; no attempt or retry runs past it.
        `store: false` is strictly enforced on every call.
        """
        schema = to_strict_json_schema(output.model_json_schema())
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

        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": content},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": output.__name__,
                    "strict": True,
                    "schema": schema,
                },
            },
            "temperature": temperature,
            "store": False,  # never let the provider keep contract text
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            with self._breaker.calling():
                try:
                    resp = await self._client.post(
                        "https://api.openai.com/v1/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=min(self._timeout_s, remaining),
                    )
                    if hasattr(resp, "raise_for_status"):
                        resp.raise_for_status()
                    data = resp.json() if hasattr(resp, "json") and callable(resp.json) else resp
                except Exception as exc:
                    raise _classify_openai(exc) from None
        except pybreaker.CircuitBreakerError:
            raise LLMError(ErrorCategory.UNAVAILABLE) from None

        choices = data.get("choices")
        if not choices or not isinstance(choices, list):
            raise LLMError(ErrorCategory.REFUSED)

        first_choice = choices[0]
        finish_reason = first_choice.get("finish_reason")
        message = first_choice.get("message") or {}

        if finish_reason == "content_filter" or message.get("refusal"):
            raise LLMError(ErrorCategory.REFUSED)

        text = message.get("content")
        if not text:
            raise LLMError(ErrorCategory.REFUSED)

        try:
            value = output.model_validate_json(text)
        except ValidationError, json.JSONDecodeError:
            raise LLMError(ErrorCategory.SCHEMA_INVALID) from None

        usage = data.get("usage") or {}
        return LLMResult(
            value=value,
            provider=self.provider,
            model_version=data.get("model") or model,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )


@cache
def openai() -> OpenAI:
    """The process-wide OpenAI adapter (one circuit breaker per provider)."""
    if not settings.OPENAI_API_KEY:
        raise LLMError(ErrorCategory.UNAVAILABLE)
    client = httpx.AsyncClient(timeout=settings.BATCH_TIMEOUT_S)
    return OpenAI(client, api_key=settings.OPENAI_API_KEY, timeout_s=settings.BATCH_TIMEOUT_S)
