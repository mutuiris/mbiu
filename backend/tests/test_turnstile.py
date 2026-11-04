"""Unit tests for Cloudflare Turnstile token verification.

Verifies mock HTTP transport behavior, failure modes, timeouts, payload structure,
missing secrets, and typed TurnstileError exceptions using httpx.MockTransport.
"""

import asyncio
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest

from mbiu.security.turnstile import (
    TurnstileError,
    async_verify_turnstile_token,
    validate_turnstile_token,
    verify_turnstile_token,
)

DUMMY_SECRET_FOR_TESTS = "test_turnstile_secret_key"


def test_empty_or_blank_token_fails() -> None:
    """An empty or blank Turnstile token returns False immediately."""
    assert verify_turnstile_token("") is False
    assert verify_turnstile_token("   ") is False

    with pytest.raises(TurnstileError):
        validate_turnstile_token("")


def test_async_empty_or_blank_token_fails() -> None:
    """Async verification returns False immediately for blank token."""
    assert asyncio.run(async_verify_turnstile_token("")) is False
    assert asyncio.run(async_verify_turnstile_token("   ")) is False


def test_missing_or_empty_secret_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """If no secret key is provided and settings has empty secret, verification fails."""
    monkeypatch.setattr("django.conf.settings.TURNSTILE_SECRET_KEY", "")
    assert verify_turnstile_token("dummy_token_123", secret_key=None) is False
    assert asyncio.run(async_verify_turnstile_token("dummy_token_123", secret_key=None)) is False


def test_successful_verification() -> None:
    """Mock client returning 200 success=True confirms token validity."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True, "challenge_ts": "2026-11-04T00:00:00Z"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        assert (
            verify_turnstile_token(
                "valid_token",
                secret_key=DUMMY_SECRET_FOR_TESTS,
                client=client,
            )
            is True
        )

        # validate_turnstile_token does not raise
        validate_turnstile_token(
            "valid_token",
            secret_key=DUMMY_SECRET_FOR_TESTS,
            client=client,
        )


def test_failed_verification() -> None:
    """Mock client returning success=False returns False and raises TurnstileError."""

    def handler(request: httpx.Request) -> httpx.Response:
        payload = {"success": False, "error-codes": ["invalid-input-response"]}
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        assert (
            verify_turnstile_token(
                "invalid_token",
                secret_key=DUMMY_SECRET_FOR_TESTS,
                client=client,
            )
            is False
        )

        with pytest.raises(TurnstileError) as exc_info:
            validate_turnstile_token(
                "invalid_token",
                secret_key=DUMMY_SECRET_FOR_TESTS,
                client=client,
            )

        assert exc_info.value.code == "turnstile_verification_failed"
        assert "Security verification was not successful" in exc_info.value.user_message


def test_async_successful_verification() -> None:
    """Async mock client returning success=True confirms token."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True})

    async def _run() -> bool:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await async_verify_turnstile_token(
                "valid_token",
                secret_key=DUMMY_SECRET_FOR_TESTS,
                client=client,
            )

    assert asyncio.run(_run()) is True


def test_async_failed_verification() -> None:
    """Async mock client returning success=False returns False."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": False})

    async def _run() -> bool:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await async_verify_turnstile_token(
                "invalid_token",
                secret_key=DUMMY_SECRET_FOR_TESTS,
                client=client,
            )

    assert asyncio.run(_run()) is False


def test_server_error_returns_false() -> None:
    """Mock client returning HTTP 500 returns False."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        result = verify_turnstile_token(
            "any_token",
            secret_key=DUMMY_SECRET_FOR_TESTS,
            client=client,
        )
        assert result is False


def test_async_server_error_returns_false() -> None:
    """Async mock client returning HTTP 500 returns False."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    async def _run() -> bool:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await async_verify_turnstile_token(
                "any_token",
                secret_key=DUMMY_SECRET_FOR_TESTS,
                client=client,
            )

    assert asyncio.run(_run()) is False


def test_network_exception_returns_false() -> None:
    """Network connection error during verification safely returns False."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        result = verify_turnstile_token(
            "any_token",
            secret_key=DUMMY_SECRET_FOR_TESTS,
            client=client,
        )
        assert result is False


def test_async_network_exception_returns_false() -> None:
    """Async network error during verification safely returns False."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    async def _run() -> bool:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await async_verify_turnstile_token(
                "any_token",
                secret_key=DUMMY_SECRET_FOR_TESTS,
                client=client,
            )

    assert asyncio.run(_run()) is False


def test_invalid_json_response_returns_false() -> None:
    """Mock client returning 200 with invalid JSON returns False."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<not-json>")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        result = verify_turnstile_token(
            "any_token",
            secret_key=DUMMY_SECRET_FOR_TESTS,
            client=client,
        )
        assert result is False


def test_payload_contains_secret_token_and_remote_ip() -> None:
    """Verification request sends secret, token, and optional client IP in body."""
    captured_body: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_body
        body_str = request.read().decode("utf-8")
        parsed = parse_qs(body_str)
        captured_body = {k: v[0] for k, v in parsed.items()}
        return httpx.Response(200, json={"success": True})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        ok = verify_turnstile_token(
            "token_abc",
            remote_ip="192.168.1.100",
            secret_key="my_secret_123",
            client=client,
        )
        assert ok is True
        assert captured_body["secret"] == "my_secret_123"
        assert captured_body["response"] == "token_abc"
        assert captured_body["remoteip"] == "192.168.1.100"
