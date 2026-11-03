from typing import Any
from urllib.parse import unquote

from django.conf import settings
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import extract
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind

tracer = trace.get_tracer("mbiu")

UNTRACED_PATHS = {"/healthz", "/readyz"}


def _parse_headers(raw: str) -> dict[str, str]:
    headers = {}
    for pair in raw.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            headers[unquote(key.strip())] = unquote(value.strip())
    return headers


def setup_tracing() -> None:
    """Export traces over OTLP. Does nothing when OTEL_EXPORTER_OTLP_ENDPOINT is empty."""
    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        return
    provider = TracerProvider(
        resource=Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
    )
    exporter = OTLPSpanExporter(
        endpoint=f"{settings.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip('/')}/v1/traces",
        headers=_parse_headers(settings.OTEL_EXPORTER_OTLP_HEADERS),
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


class TracingMiddleware:
    """ASGI middleware: one server span per HTTP request, with only method, route and status.

    Used instead of OpenTelemetry's ASGI auto-instrumentation, which also records client IPs,
    user agents and query strings that Mbiu must not export. Health checks are not traced.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Pass the request on, wrapped in a span unless it's a health check or not HTTP."""
        if scope["type"] != "http" or scope["path"] in UNTRACED_PATHS:
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope["headers"]}
        status = 0

        async def send_with_status(message: dict[str, Any]) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        with tracer.start_as_current_span(
            f"{scope['method']} {scope['path']}", context=extract(headers), kind=SpanKind.SERVER
        ) as span:
            span.set_attribute("http.request.method", scope["method"])
            await self.app(scope, receive, send_with_status)
            span.set_attribute("http.response.status_code", status)
