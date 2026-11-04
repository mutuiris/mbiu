"""Unit tests for Cloudflare Turnstile token verification.

Verifies test key fast-paths (for local development), mock HTTP client behavior,
failure modes, timeouts, and typed TurnstileError exceptions.
"""

import asyncio

import httpx
import pytest

from mbiu.security.turnstile import (
    CLOUDFLARE_TEST_SECRET_ALWAYS_FAIL,
    CLOUDFLARE_TEST_SECRET_ALWAYS_PASS,
    TurnstileError,
    async_verify_turnstile_token,
    validate_turnstile_token,
    verify_turnstile_token,
)


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


def test_always_pass_test_key_in_local_dev() -> None:
    """The Cloudflare test pass key automatically succeeds in local dev."""
    assert (
        verify_turnstile_token(
            "dummy_token_123",
            secret_key=CLOUDFLARE_TEST_SECRET_ALWAYS_PASS,
        )
        is True
    )

    # Does not raise
    validate_turnstile_token(
        "dummy_token_123",
        secret_key=CLOUDFLARE_TEST_SECRET_ALWAYS_PASS,
    )


def test_async_always_pass_test_key() -> None:
    """Async verification succeeds with always-pass test key."""
    assert (
        asyncio.run(
            async_verify_turnstile_token(
                "dummy_token_123",
                secret_key=CLOUDFLARE_TEST_SECRET_ALWAYS_PASS,
            )
        )
        is True
    )


def test_always_fail_test_key() -> None:
    """The Cloudflare test fail key returns False and raises TurnstileError."""
    assert (
        verify_turnstile_token(
            "dummy_token_123",
            secret_key=CLOUDFLARE_TEST_SECRET_ALWAYS_FAIL,
        )
        is False
    )

    with pytest.raises(TurnstileError) as exc_info:
        validate_turnstile_token(
            "dummy_token_123",
            secret_key=CLOUDFLARE_TEST_SECRET_ALWAYS_FAIL,
        )

    assert exc_info.value.code == "turnstile_verification_failed"
    assert "Security verification was not successful" in exc_info.value.user_message


def test_live_mock_successful_verification() -> None:
    """Mock client returning 200 success=True confirms token validity."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True, "challenge_ts": "2026-11-03T00:00:00Z"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        result = verify_turnstile_token(
            "valid_token",
            secret_key="custom_secret_key",
            client=client,
        )
        assert result is True


def test_live_mock_failed_verification() -> None:
    """Mock client returning success=False returns False."""

    def handler(request: httpx.Request) -> httpx.Response:
        payload = {"success": False, "error-codes": ["invalid-input-response"]}
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        result = verify_turnstile_token(
            "invalid_token",
            secret_key="custom_secret_key",
            client=client,
        )
        assert result is False


def test_live_mock_server_error() -> None:
    """Mock client returning HTTP 500 returns False."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        result = verify_turnstile_token(
            "any_token",
            secret_key="custom_secret_key",
            client=client,
        )
        assert result is False


def test_live_mock_network_exception() -> None:
    """Network connection error during verification safely returns False."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        result = verify_turnstile_token(
            "any_token",
            secret_key="custom_secret_key",
            client=client,
        )
        assert result is False


def test_async_mock_verification() -> None:
    """Async mock client returning success=True confirms token."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True})

    async def _run() -> bool:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await async_verify_turnstile_token(
                "valid_token",
                secret_key="custom_secret_key",
                client=client,
            )

    assert asyncio.run(_run()) is True
