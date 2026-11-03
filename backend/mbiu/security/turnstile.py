"""Cloudflare Turnstile token verification.

Verifies Cloudflare Turnstile bot-detection tokens server-side before initiating
any expensive evaluation or AI provider calls. Supports standard Cloudflare test
keys for local development without external network requirements.
"""

from typing import Any

import httpx
from django.conf import settings

CLOUDFLARE_TEST_SECRET_ALWAYS_PASS = "1x0000000000000000000000000000000AA"
CLOUDFLARE_TEST_SECRET_ALWAYS_FAIL = "2x0000000000000000000000000000000AA"
DEFAULT_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class TurnstileError(Exception):
    """Raised when Turnstile bot verification fails or token is missing/invalid.

    Attributes:
        user_message: Plain-language explanation for artists.
        code: Machine-readable error code.
    """

    def __init__(
        self,
        user_message: str = (
            "Security verification was not successful. Please complete the check and try again."
        ),
        code: str = "turnstile_verification_failed",
    ) -> None:
        """Initialize TurnstileError with user message and code."""
        super().__init__(user_message)
        self.user_message = user_message
        self.code = code


def verify_turnstile_token(
    token: str,
    remote_ip: str | None = None,
    *,
    secret_key: str | None = None,
    verify_url: str | None = None,
    timeout_s: float = 5.0,
    client: httpx.Client | None = None,
) -> bool:
    """Verify a Turnstile token synchronously.

    Args:
        token: Response token submitted by the client widget.
        remote_ip: Optional client IP address for Cloudflare verification.
        secret_key: Optional secret key override.
            Defaults to settings.TURNSTILE_SECRET_KEY.
        verify_url: Optional verification endpoint override.
            Defaults to settings.TURNSTILE_VERIFY_URL.
        timeout_s: HTTP request timeout in seconds.
        client: Optional injected httpx.Client for testing.

    Returns:
        True if the token is valid, False otherwise.
    """
    if not token or not token.strip():
        return False

    effective_secret = (
        secret_key
        if secret_key is not None
        else getattr(settings, "TURNSTILE_SECRET_KEY", CLOUDFLARE_TEST_SECRET_ALWAYS_PASS)
    )
    effective_url = (
        verify_url
        if verify_url is not None
        else getattr(settings, "TURNSTILE_VERIFY_URL", DEFAULT_VERIFY_URL)
    )

    # Fast-path for Cloudflare test keys in local dev when no custom client is injected
    if effective_secret == CLOUDFLARE_TEST_SECRET_ALWAYS_FAIL:
        return False
    if effective_secret == CLOUDFLARE_TEST_SECRET_ALWAYS_PASS and client is None:
        # Local development test key always succeeds without requiring live internet
        return True

    payload: dict[str, Any] = {
        "secret": effective_secret,
        "response": token.strip(),
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        if client is not None:
            response = client.post(effective_url, data=payload, timeout=timeout_s)
        else:
            with httpx.Client(timeout=timeout_s) as local_client:
                response = local_client.post(effective_url, data=payload)

        if response.status_code != 200:
            return False

        data = response.json()
        return bool(data.get("success", False))
    except httpx.HTTPError, ValueError:
        return False


async def async_verify_turnstile_token(
    token: str,
    remote_ip: str | None = None,
    *,
    secret_key: str | None = None,
    verify_url: str | None = None,
    timeout_s: float = 5.0,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Verify a Turnstile token asynchronously.

    Args:
        token: Response token submitted by the client widget.
        remote_ip: Optional client IP address for Cloudflare verification.
        secret_key: Optional secret key override.
            Defaults to settings.TURNSTILE_SECRET_KEY.
        verify_url: Optional verification endpoint override.
            Defaults to settings.TURNSTILE_VERIFY_URL.
        timeout_s: HTTP request timeout in seconds.
        client: Optional injected httpx.AsyncClient for testing.

    Returns:
        True if the token is valid, False otherwise.
    """
    if not token or not token.strip():
        return False

    effective_secret = (
        secret_key
        if secret_key is not None
        else getattr(settings, "TURNSTILE_SECRET_KEY", CLOUDFLARE_TEST_SECRET_ALWAYS_PASS)
    )
    effective_url = (
        verify_url
        if verify_url is not None
        else getattr(settings, "TURNSTILE_VERIFY_URL", DEFAULT_VERIFY_URL)
    )

    # Fast-path for Cloudflare test keys in local dev when no custom client is injected
    if effective_secret == CLOUDFLARE_TEST_SECRET_ALWAYS_FAIL:
        return False
    if effective_secret == CLOUDFLARE_TEST_SECRET_ALWAYS_PASS and client is None:
        # Local development test key always succeeds without requiring live internet
        return True

    payload: dict[str, Any] = {
        "secret": effective_secret,
        "response": token.strip(),
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        if client is not None:
            response = await client.post(effective_url, data=payload, timeout=timeout_s)
        else:
            async with httpx.AsyncClient(timeout=timeout_s) as local_client:
                response = await local_client.post(effective_url, data=payload)

        if response.status_code != 200:
            return False

        data = response.json()
        return bool(data.get("success", False))
    except httpx.HTTPError, ValueError:
        return False


def validate_turnstile_token(
    token: str,
    remote_ip: str | None = None,
    *,
    secret_key: str | None = None,
    verify_url: str | None = None,
    timeout_s: float = 5.0,
    client: httpx.Client | None = None,
) -> None:
    """Validate a Turnstile token and raise TurnstileError on verification failure.

    Args:
        token: Response token submitted by client widget.
        remote_ip: Optional client IP address.
        secret_key: Optional secret key override.
        verify_url: Optional verification endpoint override.
        timeout_s: Request timeout in seconds.
        client: Optional injected httpx.Client for testing.

    Raises:
        TurnstileError: If verification is unsuccessful.
    """
    is_valid = verify_turnstile_token(
        token,
        remote_ip,
        secret_key=secret_key,
        verify_url=verify_url,
        timeout_s=timeout_s,
        client=client,
    )
    if not is_valid:
        raise TurnstileError()
