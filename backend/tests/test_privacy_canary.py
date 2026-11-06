"""Privacy canary tests for the sanitizing log filter.

Every synthetic contract marker and PII value below is fake. The tests assert that
after passing a record through ``SanitizedLogFilter``, neither formatted output nor
any record field contains the original value.
"""

import io
import logging
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from mbiu.security.logging import (
    REDACTED,
    REDACTED_CONTRACT_TEXT,
    REDACTED_EMAIL,
    REDACTED_PHONE,
    SanitizedLogFilter,
    sanitize_text,
)

LOGGER_NAME = "mbiu.tests.privacy_canary"
CANARY = "MBIU-CANARY-7F3C2A"
EMAIL = "canary.artist@example.test"
PHONE = "+254 712 345 678"
ARTIST_NAME = f"Artist {CANARY}"
FILE_CONTENT = f"%PDF-1.7 file bytes {CANARY}"
RAW_PAYLOAD = f'{{"prompt": "{CANARY} hidden prompt"}}'
SHORT_CONTRACT = (
    f"The Artist assigns all rights in the recordings to the Label in perpetuity. {CANARY}"
)
LONG_CONTRACT = (
    "Clause 7.2. "
    + ("The Artist shall receive no royalties for any exploitation of the recordings. " * 4)
    + CANARY
)


@contextmanager
def _capturing_logger(
    fmt: str = "%(levelname)s %(name)s %(message)s",
) -> Iterator[tuple[logging.Logger, io.StringIO]]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(fmt))
    handler.addFilter(SanitizedLogFilter())

    logger = logging.getLogger(LOGGER_NAME)
    previous_handlers = list(logger.handlers)
    previous_propagate = logger.propagate
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    try:
        yield logger, stream
    finally:
        logger.handlers = previous_handlers
        logger.propagate = previous_propagate
        logger.setLevel(logging.NOTSET)
        handler.close()


def _assert_no_raw_secrets(output: str) -> None:
    for secret in (CANARY, EMAIL, PHONE, ARTIST_NAME, FILE_CONTENT, RAW_PAYLOAD):
        assert secret not in output


def test_email_in_message_is_redacted() -> None:
    with _capturing_logger() as (logger, stream):
        logger.info("Contact the artist at %s for approval.", EMAIL)

    output = stream.getvalue()
    assert REDACTED_EMAIL in output
    _assert_no_raw_secrets(output)


def test_phone_in_message_is_redacted() -> None:
    with _capturing_logger() as (logger, stream):
        logger.info("Call %s to confirm the session.", PHONE)

    output = stream.getvalue()
    assert REDACTED_PHONE in output
    _assert_no_raw_secrets(output)


def test_percent_repr_contract_text_is_redacted() -> None:
    with _capturing_logger() as (logger, stream):
        logger.info("Extracted clause: %r", SHORT_CONTRACT)

    output = stream.getvalue()
    assert REDACTED_CONTRACT_TEXT in output
    _assert_no_raw_secrets(output)


def test_curly_quoted_contract_text_is_redacted() -> None:
    with _capturing_logger() as (logger, stream):
        logger.info("Clause reads “%s” in the agreement.", SHORT_CONTRACT)

    output = stream.getvalue()
    assert REDACTED_CONTRACT_TEXT in output
    _assert_no_raw_secrets(output)


def test_long_unquoted_contract_text_is_redacted() -> None:
    with _capturing_logger() as (logger, stream):
        logger.info("Extracted: %s", LONG_CONTRACT)

    output = stream.getvalue()
    assert REDACTED_CONTRACT_TEXT in output
    _assert_no_raw_secrets(output)


def test_sensitive_extra_fields_are_redacted() -> None:
    fmt = (
        "%(message)s contract=%(contract_text)s payload=%(raw_payload)s "
        "name=%(artist_name)s file=%(file_content)s"
    )
    with _capturing_logger(fmt) as (logger, stream):
        logger.warning(
            "Upload received",
            extra={
                "contract_text": SHORT_CONTRACT,
                "raw_payload": RAW_PAYLOAD,
                "artist_name": ARTIST_NAME,
                "file_content": FILE_CONTENT,
            },
        )

    output = stream.getvalue()
    assert output.count(REDACTED) == 4
    assert REDACTED_CONTRACT_TEXT not in output
    _assert_no_raw_secrets(output)


@pytest.mark.parametrize(
    "key",
    ["contract_text", "contractText", "raw_payload", "artist_name", "file_content"],
)
def test_sensitive_key_variants_are_redacted(key: str, caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    log_filter = SanitizedLogFilter()
    logger.addFilter(log_filter)
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    try:
        logger.info("Field check", extra={key: f"{CANARY} {key}"})
    finally:
        logger.removeFilter(log_filter)

    record = caplog.records[-1]
    assert getattr(record, key) == REDACTED
    assert CANARY not in repr(record.__dict__)


def test_mapping_arguments_are_redacted(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    log_filter = SanitizedLogFilter()
    logger.addFilter(log_filter)
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    try:
        logger.info("Contact: %(contact)s", {"contact": EMAIL})
    finally:
        logger.removeFilter(log_filter)

    record = caplog.records[-1]
    assert record.getMessage() == f"Contact: {REDACTED_EMAIL}"
    assert EMAIL not in repr(record.__dict__)


def test_nested_extra_fields_are_redacted(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    log_filter = SanitizedLogFilter()
    logger.addFilter(log_filter)
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    try:
        logger.info(
            "Nested metadata",
            extra={
                "metadata": {
                    "artist_name": ARTIST_NAME,
                    "notes": [EMAIL, {"contract_text": SHORT_CONTRACT}],
                }
            },
        )
    finally:
        logger.removeFilter(log_filter)

    metadata = vars(caplog.records[-1])["metadata"]
    assert metadata["artist_name"] == REDACTED
    assert metadata["notes"][0] == REDACTED_EMAIL
    assert metadata["notes"][1]["contract_text"] == REDACTED
    assert CANARY not in repr(metadata)


def test_exception_report_is_redacted() -> None:
    with _capturing_logger() as (logger, stream):
        try:
            raise ValueError(f"Clause text: {LONG_CONTRACT}")
        except ValueError:
            logger.exception("Parser rejected %r from %s", SHORT_CONTRACT, EMAIL)

    output = stream.getvalue()
    assert REDACTED_CONTRACT_TEXT in output
    assert REDACTED_EMAIL in output
    assert "Traceback (most recent call last)" in output
    _assert_no_raw_secrets(output)


def test_ordinary_message_is_unchanged() -> None:
    message = "Processed 3 pages in 1.52 seconds"
    with _capturing_logger() as (logger, stream):
        logger.info(message)

    assert stream.getvalue().strip().endswith(message)
    assert REDACTED not in stream.getvalue()


def test_sanitize_text_replaces_all_patterns() -> None:
    text = f"Email {EMAIL}, phone {PHONE}, clause “{SHORT_CONTRACT}”."
    scrubbed = sanitize_text(text)

    assert REDACTED_EMAIL in scrubbed
    assert REDACTED_PHONE in scrubbed
    assert REDACTED_CONTRACT_TEXT in scrubbed
    _assert_no_raw_secrets(scrubbed)


def test_filter_fails_closed_when_record_cannot_be_rendered() -> None:
    class Exploding:
        def __str__(self) -> str:
            raise RuntimeError(f"cannot render {CANARY}")

    with _capturing_logger() as (logger, stream):
        logger.info(Exploding())

    output = stream.getvalue()
    assert "[REDACTED_LOG_RECORD]" in output
    assert CANARY not in output
