"""Privacy-safe logging primitives for Mbiu.

``SanitizedLogFilter`` scrubs every record before a formatter renders it. Emails,
phone numbers, quoted prose and long free-text contract chunks are replaced with
placeholders, values stored under sensitive keys are removed entirely, and formatted
exception reports and stack information are sanitized too.

Contract text is only reliably detectable when it is quoted, longer than a single
log line, or stored under a known sensitive key. Contract text must therefore stay
inside the document pipeline and out of log calls.
"""

import logging
import re
import traceback
from collections.abc import Mapping
from types import TracebackType
from typing import Any, Final

REDACTED: Final = "[REDACTED]"
REDACTED_EMAIL: Final = "[REDACTED_EMAIL]"
REDACTED_PHONE: Final = "[REDACTED_PHONE]"
REDACTED_CONTRACT_TEXT: Final = "[REDACTED_CONTRACT_TEXT]"

# Field names (normalised to lower snake_case) whose values are never safe to log.
# A field matches when its trailing one to three tokens equal a known sensitive name,
# so ``primary_artist_name`` and ``contractText`` both match ``artist_name`` and
# ``contract_text``.
_SENSITIVE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "access_token",
        "address",
        "artist_name",
        "authorization",
        "clause_text",
        "contact_name",
        "content",
        "contract_body",
        "contract_text",
        "document_text",
        "email",
        "email_address",
        "evidence_quote",
        "extracted_text",
        "file_bytes",
        "file_content",
        "first_name",
        "full_name",
        "full_text",
        "last_name",
        "name",
        "original_text",
        "page_text",
        "password",
        "payload",
        "pdf_bytes",
        "phone",
        "phone_number",
        "prompt",
        "prompt_payload",
        "quote",
        "raw_payload",
        "raw_text",
        "real_name",
        "request_body",
        "request_payload",
        "secret",
        "system_prompt",
        "text_chunk",
        "token",
        "user_prompt",
    }
)

_EMAIL_RE: Final = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE: Final = re.compile(
    r"(?<![\w.])"
    r"(?:"
    r"\+\d{1,3}(?:[\s.-]?\(?\d{1,4}\)?){2,4}"
    r"|0\d{2,4}(?:[\s.-]?\d{2,4}){2,3}"
    r"|\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}"
    r")"
    r"(?![\w]|\.[\d])"
)
# Quoted prose (at least eight characters, including a space) is treated as contract text.
_QUOTED_SPAN_RE: Final = re.compile(r"""["'“‘][^"'“”‘’\n]{8,}["'”’]""")
# Any single line this long is treated as a raw contract text chunk.
_LONG_TEXT_RE: Final = re.compile(r"[^\n]{120,}")
_CAMEL_BOUNDARY_RE: Final = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_KEY_SEPARATOR_RE: Final = re.compile(r"[^a-z0-9]+")

_RESERVED_ATTRIBUTES: Final[frozenset[str]] = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
)


def sanitize_text(text: str) -> str:
    """Return ``text`` with emails, phone numbers and contract text replaced.

    Emails and phones are redacted first, then quoted prose, then any remaining
    unbroken run of 120 or more characters on one line. The result never contains
    the matched values.
    """
    scrubbed = _EMAIL_RE.sub(REDACTED_EMAIL, text)
    scrubbed = _PHONE_RE.sub(REDACTED_PHONE, scrubbed)
    scrubbed = _QUOTED_SPAN_RE.sub(_redact_quoted_span, scrubbed)
    return _LONG_TEXT_RE.sub(REDACTED_CONTRACT_TEXT, scrubbed)


def _redact_quoted_span(match: re.Match[str]) -> str:
    body = match.group(0)[1:-1]
    return REDACTED_CONTRACT_TEXT if any(char.isspace() for char in body) else match.group(0)


def _normalise_key(key: str) -> str:
    spaced = _CAMEL_BOUNDARY_RE.sub("_", key)
    return _KEY_SEPARATOR_RE.sub("_", spaced.lower()).strip("_")


def _is_sensitive_key(key: str) -> bool:
    parts = _normalise_key(key).split("_")
    for size in (1, 2, 3):
        if size <= len(parts) and "_".join(parts[-size:]) in _SENSITIVE_KEYS:
            return True
    return False


def _sanitize_named_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if _is_sensitive_key(key):
        return REDACTED
    return _sanitize_value(value)


def _sanitize_mapping(value: Mapping[Any, Any], *, redact_keys: bool) -> dict[Any, Any]:
    sanitized: dict[Any, Any] = {}
    for raw_key, raw_value in value.items():
        key = _sanitize_value(raw_key) if redact_keys else raw_key
        if isinstance(raw_key, str):
            sanitized[key] = _sanitize_named_value(raw_key, raw_value)
        else:
            sanitized[key] = _sanitize_value(raw_value)
    return sanitized


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, (bytes, bytearray)):
        return sanitize_text(bytes(value).decode("utf-8", errors="replace"))
    if isinstance(value, BaseException):
        return sanitize_text(f"{type(value).__name__}: {value}")
    if isinstance(value, Mapping):
        return _sanitize_mapping(value, redact_keys=True)
    if isinstance(value, tuple):
        return tuple(_sanitize_value(item) for item in value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return {_sanitize_value(item) for item in value}
    return value


def _sanitize_args(args: Any) -> Any:
    # Keep top-level mapping keys intact so named ``%(field)s`` formatting still works.
    if isinstance(args, Mapping):
        return _sanitize_mapping(args, redact_keys=False)
    if isinstance(args, tuple):
        return tuple(_sanitize_value(item) for item in args)
    return _sanitize_value(args)


def _format_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: TracebackType | None,
) -> str:
    # Stack frames hold source paths and code, never runtime contract text. Only the
    # exception type and message can carry user content, so only those are sanitized.
    frames = "".join(traceback.format_tb(exc_tb))
    reason = "".join(traceback.format_exception_only(exc_type, exc_value))
    header = "Traceback (most recent call last):\n" if frames else ""
    return f"{header}{frames}{sanitize_text(reason)}"


class SanitizedLogFilter(logging.Filter):
    """Scrub sensitive content from every record before it is formatted.

    Attach to a logger or handler. The filter sanitizes messages, ``%`` arguments,
    ``extra`` fields, formatted exception reports and stack information in place.
    If sanitizing unexpectedly fails, the record is reduced to a placeholder so an
    unsanitized value can never reach a handler.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize ``record`` in place and keep the record."""
        try:
            record.args = _sanitize_args(record.args)
            for key, value in list(record.__dict__.items()):
                if key in _RESERVED_ATTRIBUTES:
                    continue
                record.__dict__[key] = _sanitize_named_value(key, value)

            # Render lazily formatted arguments first: ``%r`` adds quotes that only
            # become visible after formatting, and quoted prose is contract text.
            record.msg = _sanitize_value(record.getMessage())
            record.args = ()

            if record.exc_text is not None:
                record.exc_text = sanitize_text(record.exc_text)
            if record.exc_info is not None:
                exc_type, exc_value, exc_tb = record.exc_info
                if exc_type is not None and exc_value is not None:
                    record.exc_text = _format_exception(exc_type, exc_value, exc_tb)
            if record.stack_info is not None:
                record.stack_info = sanitize_text(record.stack_info)
        except Exception:
            # Fail closed: a record we cannot inspect must not be emitted as-is.
            for key in list(record.__dict__):
                if key not in _RESERVED_ATTRIBUTES:
                    del record.__dict__[key]
            record.msg = "[REDACTED_LOG_RECORD]"
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return True
