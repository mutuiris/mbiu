"""API view handlers for contract evaluation streaming."""

from __future__ import annotations

from collections.abc import AsyncIterator

from django.conf import settings
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
    StreamingHttpResponse,
)
from django.http.response import HttpResponseBase
from django.views.decorators.csrf import csrf_exempt

from mbiu.api.schemas import ApiError, ErrorCode
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
from mbiu.evaluation.orchestrator import evaluate_contract
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
    if origin and (origin in allowed_origins or "*" in allowed_origins):
        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, traceparent, X-Requested-With"
        response["Access-Control-Max-Age"] = "86400"
    return response


@csrf_exempt
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

    client_ip = (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR")
    )

    # 3. Synchronous pre-flight checks (Turnstile and PDF validation) before opening stream
    try:
        validate_turnstile_token(turnstile_token, remote_ip=client_ip)
        validate_upload(pdf_bytes)
    except Exception as exc:
        status, api_err = _map_error_to_api_error(exc)
        res = JsonResponse(api_err.model_dump(), status=status)
        return _apply_cors(res, origin)

    # 4. Stream evaluation events as newline-delimited JSON (NDJSON)
    async def ndjson_stream() -> AsyncIterator[bytes]:
        async for event in evaluate_contract(
            pdf_bytes=pdf_bytes,
            turnstile_token=turnstile_token,
            client_ip=client_ip,
        ):
            yield (event.model_dump_json() + "\n").encode("utf-8")

    stream_response = StreamingHttpResponse(
        ndjson_stream(),
        content_type="application/x-ndjson",
    )
    stream_response["Cache-Control"] = "no-store"
    stream_response["X-Content-Type-Options"] = "nosniff"
    return _apply_cors(stream_response, origin)
