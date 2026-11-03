"""The only code that talks to AI providers.

Every call goes through here, so storage-off, timeouts, retries and the circuit breaker
are enforced in one place.
"""

import re
from dataclasses import dataclass
from enum import StrEnum


class ErrorCategory(StrEnum):
    """Why a model call failed."""

    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    REFUSED = "refused"
    SCHEMA_INVALID = "schema_invalid"
    UNAVAILABLE = "unavailable"


class LLMError(Exception):
    """A failed model call. Never carries prompt or response text."""

    def __init__(
        self,
        category: ErrorCategory,
        *,
        retryable: bool = False,
        outage: bool = False,
        retry_after_s: float | None = None,
    ) -> None:
        super().__init__(category.value)
        self.category = category
        self.retryable = retryable
        self.outage = outage  # counts towards opening the circuit breaker
        self.retry_after_s = retry_after_s


@dataclass(frozen=True)
class LLMResult[T]:
    """A validated model answer plus what to record about the call."""

    value: T
    provider: str
    model_version: str
    input_tokens: int | None
    output_tokens: int | None


def as_data(tag: str, text: str, **attrs: str) -> str:
    """Wrap untrusted text (contract wording, questions) in a delimited block.

    The prompt tells the model that anything inside these tags is data, not instructions.
    A closing tag inside the text is escaped so it cannot end the block early.
    """
    escaped = re.sub(rf"</\s*{re.escape(tag)}", rf"<\\/{tag}", text, flags=re.IGNORECASE)
    attributes = "".join(f' {key}="{value}"' for key, value in attrs.items())
    return f"<{tag}{attributes}>\n{escaped}\n</{tag}>"
