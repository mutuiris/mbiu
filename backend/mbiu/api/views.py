"""API view handlers for contract and clause evaluation streaming."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from django.conf import settings
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
    StreamingHttpResponse,
)
from django.http.response import HttpResponseBase
from pydantic import ValidationError

from mbiu.api.schemas import ApiError, ClauseEvaluationRequest, ErrorCode, StreamEvent
from mbiu.documents.errors import (
    DocumentError,
    EmptyPDFError,
    EncryptedPDFError,
    ExtractionFailedError,
    ExtractionMemoryError,
    ExtractionTimeoutError,
    FileTooLargeError,
    InvalidPDFError,
    PageLimitExceededError,
    ScannedPDFError,
)
from mbiu.documents.upload import validate_upload
from mbiu.evaluation.orchestrator import evaluate_clauses, evaluate_contract
from mbiu.security.turnstile import TurnstileError, validate_turnstile_token


def _map_error_to_api_error(exc: Exception) -> tuple[int, ApiError]:
    """Map internal document and security errors to artist-facing ApiError models."""
    if isinstance(exc, TurnstileError):
        return 400, ApiError(
            code=ErrorCode.BOT_CHECK_FAILED,
            message=exc.user_message,
        )
    if isinstance(exc, (EmptyPDFError, InvalidPDFError)):
        return 400, ApiError(
            code=ErrorCode.INVALID_FILE_TYPE,
            message=exc.user_message,
        )
    if isinstance(exc, FileTooLargeError):
        return 400, ApiError(
            code=ErrorCode.FILE_TOO_LARGE,
            message=exc.user_message,
        )
    if isinstance(exc, PageLimitExceededError):
        return 400, ApiError(
            code=ErrorCode.TOO_MANY_PAGES,
            message=exc.user_message,
        )
    if isinstance(exc, EncryptedPDFError):
        return 400, ApiError(
            code=ErrorCode.ENCRYPTED_PDF,
            message=exc.user_message,
        )
    if isinstance(exc, ScannedPDFError):
        return 400, ApiError(
            code=ErrorCode.SCANNED_PDF,
            message=exc.user_message,
        )
    if isinstance(exc, (ExtractionTimeoutError, ExtractionMemoryError, ExtractionFailedError)):
        return 503, ApiError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=exc.user_message,
        )
    if isinstance(exc, DocumentError):
        return 400, ApiError(
            code=ErrorCode.INVALID_FILE_TYPE,
            message=exc.user_message,
        )
    return 500, ApiError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message="Mbiu was unable to process this document. Please check the file and try again.",
    )


def _apply_cors[T: HttpResponseBase](response: T, origin: str | None) -> T:
    """Set restrictive CORS headers according to project security rules."""
    allowed_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", ["http://localhost:3000"])
    normalized_allowed = {o.rstrip("/") for o in allowed_origins}
    normalized_allowed.update({"http://localhost:3000", "http://127.0.0.1:3000"})
    if origin and (origin.rstrip("/") in normalized_allowed or "*" in normalized_allowed):
        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = (
            "Content-Type, traceparent, X-Requested-With, X-Turnstile-Token"
        )
        response["Access-Control-Max-Age"] = "86400"
    return response


def _client_ip(request: HttpRequest) -> str | None:
    return (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR")
    )


def _error_response(exc: Exception, origin: str | None) -> HttpResponseBase:
    status, api_err = _map_error_to_api_error(exc)
    return _apply_cors(JsonResponse(api_err.model_dump(), status=status), origin)


def _ndjson_response(events: AsyncIterator[StreamEvent], origin: str | None) -> HttpResponseBase:
    async def ndjson_stream() -> AsyncIterator[bytes]:
        async for event in events:
            yield (event.model_dump_json() + "\n").encode("utf-8")

    stream_response = StreamingHttpResponse(
        ndjson_stream(),
        content_type="application/x-ndjson",
    )
    stream_response["Cache-Control"] = "no-store"
    stream_response["X-Content-Type-Options"] = "nosniff"
    stream_response["X-Accel-Buffering"] = "no"
    return _apply_cors(stream_response, origin)


async def evaluations(request: HttpRequest) -> HttpResponseBase:
    """Handle contract upload and stream back NDJSON evaluation events.

    Endpoint: POST /api/v1/evaluations
    Requires:
      - Multipart file under 'pdf' (or 'file')
      - Turnstile token under 'turnstile_token' (or 'cf-turnstile-response')
    Returns:
      - 200 OK: application/x-ndjson event stream
      - 400/503: application/json ApiError if validation fails before stream starts
    """
    origin = request.headers.get("Origin") or request.META.get("HTTP_ORIGIN")

    if request.method == "OPTIONS":
        res = HttpResponse(status=204)
        return _apply_cors(res, origin)

    if request.method != "POST":
        res = HttpResponse(status=405)
        return _apply_cors(res, origin)

    # 1. Parse uploaded document
    uploaded_file = request.FILES.get("pdf") or request.FILES.get("file")
    if not uploaded_file:
        status, api_err = (
            400,
            ApiError(
                code=ErrorCode.INVALID_FILE_TYPE,
                message="No contract file was provided. Please choose a valid PDF file to upload.",
            ),
        )
        res = JsonResponse(api_err.model_dump(), status=status)
        return _apply_cors(res, origin)

    pdf_bytes = uploaded_file.read()

    # 2. Extract Turnstile token
    turnstile_token = (
        request.POST.get("turnstile_token")
        or request.POST.get("cf-turnstile-response")
        or request.headers.get("X-Turnstile-Token")
        or ""
    ).strip()

    # 3. Pre-flight checks before opening the stream. Turnstile is checked only here.
    try:
        await asyncio.to_thread(
            validate_turnstile_token, turnstile_token, remote_ip=_client_ip(request)
        )
        await asyncio.to_thread(validate_upload, pdf_bytes)
    except Exception as exc:
        return _error_response(exc, origin)

    # 4. Stream evaluation events as newline-delimited JSON (NDJSON)
    return _ndjson_response(evaluate_contract(pdf_bytes=pdf_bytes), origin)


async def clause_evaluations(request: HttpRequest) -> HttpResponseBase:
    """Check clauses the browser sends back, and stream their results as NDJSON.

    Endpoint: POST /api/v1/clause-evaluations
    Body: a ClauseEvaluationRequest as JSON.
    Returns:
      - 200 OK: application/x-ndjson stream of progress, clause_result and clause_failed
      - 400/503: application/json ApiError if the request is refused before the stream
    """
    origin = request.headers.get("Origin") or request.META.get("HTTP_ORIGIN")

    if request.method == "OPTIONS":
        return _apply_cors(HttpResponse(status=204), origin)

    if request.method != "POST":
        return _apply_cors(HttpResponse(status=405), origin)

    try:
        body = ClauseEvaluationRequest.model_validate_json(request.body)
    except ValidationError:
        api_err = ApiError(
            code=ErrorCode.INVALID_REQUEST,
            message="Mbiu couldn't read the clauses to check. Upload the contract again.",
        )
        return _apply_cors(JsonResponse(api_err.model_dump(), status=400), origin)

    try:
        await asyncio.to_thread(
            validate_turnstile_token, body.turnstile_token, remote_ip=_client_ip(request)
        )
    except Exception as exc:
        return _error_response(exc, origin)

    return _ndjson_response(evaluate_clauses(body.clauses), origin)
