"""Hermetic tests for the MB-12 corpus fetch, store, parse and split pipeline.

External systems (Firecrawl, Supabase S3, Docling) are replaced with
``httpx.MockTransport`` handlers or in-memory fakes, so nothing here touches the
network, cloud storage or the real Docling installation.
"""

import hashlib
import io
import json
import logging
import textwrap
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from urllib.parse import unquote

import httpx
import pytest

from mbiu.pipeline.cli import PipelineSettings, main
from mbiu.pipeline.errors import (
    ConfigurationError,
    DocumentParseError,
    DocumentQualityError,
    FetchError,
    FetchTimeoutError,
    SourceConfigError,
    StorageError,
    UnsupportedDocumentError,
)
from mbiu.pipeline.fetch import FirecrawlFetcher, RobotsPolicy
from mbiu.pipeline.logging_setup import configure_pipeline_logging
from mbiu.pipeline.models import (
    DocumentParser,
    FetchedDocument,
    ObjectStore,
    ParsedDocument,
    PipelineReport,
    Source,
    SourceFetcher,
    StorageMetadata,
    StoredObject,
)
from mbiu.pipeline.parse import DoclingParser, ParseQualityPolicy
from mbiu.pipeline.pipeline import CorpusPipeline
from mbiu.pipeline.sources import load_sources
from mbiu.pipeline.store import SupabaseS3Store, object_key

FIXED_NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
PDF_BYTES = b"%PDF-1.7\nsynthetic public template\n%%EOF\n"
PDF_DIGEST = hashlib.sha256(PDF_BYTES).hexdigest()
DOCUMENT_URL = "https://example.org/templates/template.pdf"

SOURCE = Source(
    url="https://example.org/templates/",
    licence="CC BY 4.0",
    reviewing_body="Mbiu Legal Review",
    contract_type="recording",
    jurisdiction="KE",
)

CONTRACT_TEXT = (
    "1. GRANT OF RIGHTS\n"
    "The Company grants the Artist a non-exclusive licence to perform the Work.\n\n"
    "2. ROYALTIES\n"
    "The Company shall pay the Artist a royalty of twenty percent of Net Receipts.\n"
)

CLEAN_TEXT = "The licensor grants the licensee a worldwide licence to use the recording. " * 5


@pytest.fixture(autouse=True)
def _restore_pipeline_logger() -> Iterator[None]:
    """Keep module tests from leaking handlers or levels into other test files."""
    target = logging.getLogger("mbiu.pipeline")
    handlers = list(target.handlers)
    level = target.level
    propagate = target.propagate
    try:
        yield
    finally:
        for handler in list(target.handlers):
            target.removeHandler(handler)
        for handler in handlers:
            target.addHandler(handler)
        target.setLevel(level)
        target.propagate = propagate


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _metadata(filename: str = "template.pdf") -> StorageMetadata:
    return StorageMetadata(
        source_url=SOURCE.url,
        document_url=DOCUMENT_URL,
        fetched_at=FIXED_NOW,
        licence=SOURCE.licence,
        reviewing_body=SOURCE.reviewing_body,
        template_version="2",
        contract_type=SOURCE.contract_type,
        jurisdiction=SOURCE.jurisdiction,
        content_type="application/pdf",
        filename=filename,
    )


def _fetched_document(
    *,
    url: str = DOCUMENT_URL,
    filename: str = "template.pdf",
    content: bytes = PDF_BYTES,
) -> FetchedDocument:
    return FetchedDocument(
        url=url,
        content=content,
        content_type="application/pdf",
        filename=filename,
        fetched_at=FIXED_NOW,
    )


def _extractor(parsed: ParsedDocument) -> Callable[[FetchedDocument], ParsedDocument]:
    def extract(document: FetchedDocument) -> ParsedDocument:
        return parsed

    return extract


def _failing_extractor(error: Exception) -> Callable[[FetchedDocument], ParsedDocument]:
    def extract(document: FetchedDocument) -> ParsedDocument:
        raise error

    return extract


class _StaticFetcher:
    def __init__(self, documents: list[FetchedDocument]) -> None:
        self.documents = documents
        self.calls: list[tuple[Source, int, float]] = []

    def fetch(
        self,
        source: Source,
        *,
        max_pages: int,
        timeout_s: float,
    ) -> list[FetchedDocument]:
        self.calls.append((source, max_pages, timeout_s))
        return self.documents[:max_pages]


class _FailingFetcher:
    def fetch(
        self,
        source: Source,
        *,
        max_pages: int,
        timeout_s: float,
    ) -> list[FetchedDocument]:
        raise FetchError("crawl failed")


class _MemoryStore:
    """In-memory equivalent of the content-addressed Supabase store."""

    def __init__(self) -> None:
        self.objects: dict[str, StoredObject] = {}
        self.writes = 0

    def put_if_absent(self, content: bytes, metadata: StorageMetadata) -> StoredObject:
        digest = hashlib.sha256(content).hexdigest()
        key = object_key(digest, metadata.filename)
        if key in self.objects:
            return StoredObject(key=key, sha256=digest, metadata=metadata, created=False)
        stored = StoredObject(key=key, sha256=digest, metadata=metadata, created=True)
        self.objects[key] = stored
        self.writes += 1
        return stored


class _FailingStore:
    def put_if_absent(self, content: bytes, metadata: StorageMetadata) -> StoredObject:
        raise StorageError("bucket unavailable")


class _RecordingParser:
    def __init__(
        self,
        result: ParsedDocument | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.calls = 0

    def parse(self, document: FetchedDocument) -> ParsedDocument:
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


class _StubPipeline:
    def __init__(self, report: PipelineReport | None = None) -> None:
        self.report = report if report is not None else PipelineReport()
        self.sources: list[Source] = []

    def run(self, sources: Sequence[Source]) -> PipelineReport:
        self.sources = list(sources)
        return self.report


def _write_sources(path: Path, body: str) -> Path:
    path.write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Source configuration
# ---------------------------------------------------------------------------


def test_load_sources_parses_required_fields_and_version(tmp_path: Path) -> None:
    path = _write_sources(
        tmp_path / "sources.yaml",
        """
        sources:
          - url: https://example.org/templates/
            licence: CC BY 4.0
            reviewing_body: Mbiu Legal Review
            contract_type: recording
            jurisdiction: KE
          - url: https://example.org/publishing/
            licence: OGL 3.0
            reviewing_body: Mbiu Publishing Review
            contract_type: publishing
            jurisdiction: UK
            template_version: 3
        """,
    )

    sources = load_sources(path)

    assert [source.url for source in sources] == [
        "https://example.org/templates/",
        "https://example.org/publishing/",
    ]
    assert sources[0].template_version == "1"
    assert sources[1].template_version == "3"


def test_load_sources_returns_empty_for_blank_file(tmp_path: Path) -> None:
    path = _write_sources(tmp_path / "sources.yaml", "sources: []")

    assert load_sources(path) == []


@pytest.mark.parametrize(
    "body",
    [
        "sources: not-a-list",
        "sources:\n  - url: https://example.org/\n    licence: CC BY 4.0",
        "sources:\n  - [not, a, mapping]",
        (
            "sources:\n  - url: ftp://example.org/templates\n"
            "    licence: CC BY 4.0\n"
            "    reviewing_body: Mbiu Legal Review\n"
            "    contract_type: recording\n"
            "    jurisdiction: KE"
        ),
        (
            "sources:\n  - url: https://example.org/templates\n"
            "    licence: CC BY 4.0\n"
            "    reviewing_body: Mbiu Legal Review\n"
            "    contract_type: recording\n"
            "    jurisdiction: KE\n"
            "    template_version: ''"
        ),
    ],
)
def test_load_sources_rejects_invalid_entries(tmp_path: Path, body: str) -> None:
    path = _write_sources(tmp_path / "sources.yaml", body)

    with pytest.raises(SourceConfigError):
        load_sources(path)


def test_load_sources_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(SourceConfigError):
        load_sources(tmp_path / "absent.yaml")


# ---------------------------------------------------------------------------
# Firecrawl fetching and robots.txt gate
# ---------------------------------------------------------------------------


def test_firecrawl_respects_page_cap_and_disables_robots_override() -> None:
    requests: list[httpx.Request] = []
    data = [
        {"url": f"https://example.org/templates/page-{index}.pdf", "markdown": "Clause text"}
        for index in range(5)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if request.method == "POST":
            return httpx.Response(200, json={"id": "job-1"})
        return httpx.Response(200, json={"status": "completed", "data": data})

    with _client(handler) as client:
        fetcher = FirecrawlFetcher(
            api_key="fc-key",
            client=client,
            poll_interval_s=0.0,
            sleep=lambda _: None,
            now=lambda: FIXED_NOW,
        )
        documents = fetcher.fetch(SOURCE, max_pages=2, timeout_s=5.0)

    assert len(documents) == 2
    assert all(document.content_type == "text/markdown" for document in documents)
    assert all(document.filename.endswith(".md") for document in documents)
    assert documents[0].fetched_at == FIXED_NOW
    assert documents[0].content == b"Clause text"

    post = next(request for request in requests if request.method == "POST")
    body = json.loads(post.content)
    assert body == {
        "url": SOURCE.url,
        "limit": 2,
        "ignoreRobotsTxt": False,
        "scrapeOptions": {"formats": ["markdown", "html"]},
    }
    assert post.headers["authorization"] == "Bearer fc-key"
    assert post.url.path == "/v2/crawl"


def test_firecrawl_skips_when_robots_txt_is_unreachable() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise httpx.ConnectError("robots.txt unreachable")

    with _client(handler) as client:
        fetcher = FirecrawlFetcher(api_key="fc-key", client=client)
        documents = fetcher.fetch(SOURCE, max_pages=5, timeout_s=5.0)

    assert documents == []
    assert len(requests) == 1
    assert requests[0].url.path == "/robots.txt"
    assert requests[0].method == "GET"


def test_firecrawl_skips_when_robots_txt_disallows_crawl() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text="User-agent: *\nDisallow: /\n")

    with _client(handler) as client:
        fetcher = FirecrawlFetcher(api_key="fc-key", client=client)
        documents = fetcher.fetch(SOURCE, max_pages=5, timeout_s=5.0)

    assert documents == []
    assert all(request.method == "GET" for request in requests)


def test_firecrawl_proceeds_when_robots_txt_is_missing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "POST":
            return httpx.Response(200, json={"id": "job-2"})
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "data": [{"url": DOCUMENT_URL, "html": "<p>Clause</p>"}],
            },
        )

    with _client(handler) as client:
        fetcher = FirecrawlFetcher(api_key="fc-key", client=client, sleep=lambda _: None)
        documents = fetcher.fetch(SOURCE, max_pages=1, timeout_s=5.0)

    assert len(documents) == 1
    assert documents[0].content_type == "text/html"
    assert documents[0].filename.endswith(".html")


def test_firecrawl_raises_timeout_when_job_exceeds_budget() -> None:
    ticks = iter([0.0, 1.0, 100.0])

    def clock() -> float:
        return next(ticks)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if request.method == "POST":
            return httpx.Response(200, json={"id": "slow-job"})
        return httpx.Response(200, json={"status": "scraping"})

    with _client(handler) as client:
        fetcher = FirecrawlFetcher(
            api_key="fc-key",
            client=client,
            poll_interval_s=0.0,
            clock=clock,
            sleep=lambda _: None,
        )
        with pytest.raises(FetchTimeoutError):
            fetcher.fetch(SOURCE, max_pages=1, timeout_s=5.0)


def test_firecrawl_raises_when_job_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if request.method == "POST":
            return httpx.Response(200, json={"id": "job-3"})
        return httpx.Response(200, json={"status": "failed"})

    with _client(handler) as client:
        fetcher = FirecrawlFetcher(api_key="fc-key", client=client, sleep=lambda _: None)
        with pytest.raises(FetchError):
            fetcher.fetch(SOURCE, max_pages=1, timeout_s=5.0)


def test_firecrawl_rejects_missing_job_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, json={"status": "ok"})

    with _client(handler) as client:
        fetcher = FirecrawlFetcher(api_key="fc-key", client=client)
        with pytest.raises(FetchError):
            fetcher.fetch(SOURCE, max_pages=1, timeout_s=5.0)


def test_robots_policy_allows_site_without_robots_file() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    with _client(handler) as client:
        assert RobotsPolicy(client=client).allowed(SOURCE.url) is True


def test_robots_policy_denies_unexpected_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with _client(handler) as client:
        assert RobotsPolicy(client=client).allowed(SOURCE.url) is False


# ---------------------------------------------------------------------------
# Content-addressed Supabase S3 storage
# ---------------------------------------------------------------------------


def test_object_key_is_content_addressed_with_safe_suffix() -> None:
    assert object_key("abc123", "Template.PDF") == "raw/abc123.pdf"
    assert object_key("abc123", "template") == "raw/abc123"
    assert object_key("abc123", "../../escape") == "raw/abc123"


def test_store_writes_sha256_key_and_metadata_headers() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(404 if request.method == "HEAD" else 200)

    with _client(handler) as client:
        store = SupabaseS3Store(
            endpoint="https://storage.example.org",
            access_key="access",
            secret_key="secret",
            bucket="corpus",
            client=client,
            now=lambda: FIXED_NOW,
        )
        stored = store.put_if_absent(PDF_BYTES, _metadata())

    assert [request.method for request in requests] == ["HEAD", "PUT"]
    assert stored.created is True
    assert stored.sha256 == PDF_DIGEST
    assert stored.key == f"raw/{PDF_DIGEST}.pdf"

    head, put = requests
    expected_path = f"/corpus/raw/{PDF_DIGEST}.pdf"
    assert head.url.path == expected_path
    assert put.url.path == expected_path
    assert put.content == PDF_BYTES

    headers = put.headers
    assert headers["content-type"] == "application/pdf"
    assert unquote(headers["x-amz-meta-source-url"]) == SOURCE.url
    assert unquote(headers["x-amz-meta-document-url"]) == DOCUMENT_URL
    assert unquote(headers["x-amz-meta-fetch-date"]) == FIXED_NOW.isoformat()
    assert unquote(headers["x-amz-meta-licence"]) == SOURCE.licence
    assert unquote(headers["x-amz-meta-reviewing-body"]) == SOURCE.reviewing_body
    assert unquote(headers["x-amz-meta-template-version"]) == "2"
    assert unquote(headers["x-amz-meta-contract-type"]) == SOURCE.contract_type
    assert unquote(headers["x-amz-meta-jurisdiction"]) == SOURCE.jurisdiction
    assert unquote(headers["x-amz-meta-filename"]) == "template.pdf"

    authorization = headers["authorization"]
    assert authorization.startswith("AWS4-HMAC-SHA256 Credential=access/20261104/")
    assert "SignedHeaders=" in authorization
    assert "x-amz-meta-template-version" in authorization


def test_store_is_idempotent_when_object_already_exists() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    with _client(handler) as client:
        store = SupabaseS3Store(
            endpoint="https://storage.example.org",
            access_key="access",
            secret_key="secret",
            bucket="corpus",
            client=client,
            now=lambda: FIXED_NOW,
        )
        stored = store.put_if_absent(PDF_BYTES, _metadata())

    assert [request.method for request in requests] == ["HEAD"]
    assert stored.created is False
    assert stored.key == f"raw/{PDF_DIGEST}.pdf"


def test_store_raises_on_rejected_head_or_put() -> None:
    def rejecting_head(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403)

    with _client(rejecting_head) as client:
        store = SupabaseS3Store(
            endpoint="https://storage.example.org",
            access_key="access",
            secret_key="secret",
            bucket="corpus",
            client=client,
        )
        with pytest.raises(StorageError, match="HEAD"):
            store.put_if_absent(PDF_BYTES, _metadata())

    def rejecting_put(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404 if request.method == "HEAD" else 500)

    with _client(rejecting_put) as client:
        store = SupabaseS3Store(
            endpoint="https://storage.example.org",
            access_key="access",
            secret_key="secret",
            bucket="corpus",
            client=client,
        )
        with pytest.raises(StorageError, match="PUT"):
            store.put_if_absent(PDF_BYTES, _metadata())


def test_store_wraps_network_failures() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("storage offline")

    with _client(handler) as client:
        store = SupabaseS3Store(
            endpoint="https://storage.example.org",
            access_key="access",
            secret_key="secret",
            bucket="corpus",
            client=client,
        )
        with pytest.raises(StorageError):
            store.put_if_absent(PDF_BYTES, _metadata())


# ---------------------------------------------------------------------------
# Docling parsing and fail-closed quality gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("parsed", "reason"),
    [
        (ParsedDocument(text="", headings=[], tables=[]), "empty_text"),
        (ParsedDocument(text="short clause", headings=[], tables=[]), "too_short"),
        (
            ParsedDocument(text=CLEAN_TEXT, headings=[], tables=[], ocr_confidence=0.2),
            "low_ocr_confidence",
        ),
        (
            ParsedDocument(text=CLEAN_TEXT + "\ufffd" * 20, headings=[], tables=[]),
            "garbled_encoding",
        ),
        (
            ParsedDocument(text="A" * 180 + "\x00" * 20, headings=[], tables=[]),
            "garbled_control_characters",
        ),
        (ParsedDocument(text="9" * 240, headings=[], tables=[]), "garbled_text"),
    ],
)
def test_parser_rejects_low_quality_output(parsed: ParsedDocument, reason: str) -> None:
    parser = DoclingParser(extractor=_extractor(parsed))

    with pytest.raises(DocumentQualityError) as excinfo:
        parser.parse(_fetched_document())

    assert excinfo.value.reason == reason


def test_parser_accepts_clean_output() -> None:
    parsed = ParsedDocument(text=CLEAN_TEXT, headings=["Grant"], tables=[], page_count=2)
    parser = DoclingParser(extractor=_extractor(parsed))

    assert parser.parse(_fetched_document()) is parsed


def test_parser_honours_custom_quality_policy() -> None:
    parsed = ParsedDocument(text="A short clean clause.", headings=[], tables=[])
    parser = DoclingParser(
        extractor=_extractor(parsed),
        policy=ParseQualityPolicy(min_characters=5),
    )

    assert parser.parse(_fetched_document()) is parsed


def test_parser_rejects_unsupported_suffix() -> None:
    parsed = ParsedDocument(text=CLEAN_TEXT, headings=[], tables=[])
    parser = DoclingParser(extractor=_extractor(parsed))

    with pytest.raises(UnsupportedDocumentError):
        parser.parse(_fetched_document(filename="notes.txt"))


def test_parser_wraps_extractor_failures() -> None:
    parser = DoclingParser(extractor=_failing_extractor(RuntimeError("docling crashed")))

    with pytest.raises(DocumentParseError, match="could not parse"):
        parser.parse(_fetched_document())


def test_parser_propagates_typed_parse_errors() -> None:
    parser = DoclingParser(extractor=_failing_extractor(DocumentParseError("unsupported layout")))

    with pytest.raises(DocumentParseError, match="unsupported layout"):
        parser.parse(_fetched_document())


# ---------------------------------------------------------------------------
# End-to-end orchestration and idempotency
# ---------------------------------------------------------------------------


def _pipeline(
    *,
    fetcher: SourceFetcher,
    store: ObjectStore,
    parser: DocumentParser,
) -> CorpusPipeline:
    return CorpusPipeline(
        fetcher=fetcher,
        store=store,
        parser=parser,
        max_pages_per_source=10,
        timeout_s=30.0,
    )


def test_pipeline_stores_metadata_and_splits_numbered_clauses() -> None:
    store = _MemoryStore()
    parser = _RecordingParser(ParsedDocument(text=CONTRACT_TEXT, headings=[], tables=[]))
    fetcher = _StaticFetcher([_fetched_document()])
    pipeline = _pipeline(fetcher=fetcher, store=store, parser=parser)

    report = pipeline.run([SOURCE])

    assert report.errors == []
    assert report.created_count == 1
    assert report.skipped_count == 0
    assert report.rejected_count == 0
    assert report.clause_count == 2
    assert fetcher.calls == [(SOURCE, 10, 30.0)]

    outcome = report.outcomes[0]
    assert outcome.created is True
    assert outcome.rejected_reason is None
    assert outcome.sha256 == PDF_DIGEST
    assert outcome.storage_key == f"raw/{PDF_DIGEST}.pdf"
    assert outcome.source_url == SOURCE.url
    assert outcome.document_url == DOCUMENT_URL

    assert [clause.clause_id for clause in outcome.clauses] == ["1", "2"]
    first = outcome.clauses[0]
    assert first.title == "GRANT OF RIGHTS"
    assert first.section == "main"
    assert first.source_url == SOURCE.url
    assert first.licence == SOURCE.licence
    assert first.reviewing_body == SOURCE.reviewing_body
    assert first.contract_type == SOURCE.contract_type
    assert first.jurisdiction == SOURCE.jurisdiction
    assert first.template_version == SOURCE.template_version
    assert first.document_sha256 == PDF_DIGEST
    assert first.pages == [1]


def test_pipeline_second_run_is_idempotent() -> None:
    store = _MemoryStore()
    parser = _RecordingParser(ParsedDocument(text=CONTRACT_TEXT, headings=[], tables=[]))
    pipeline = _pipeline(
        fetcher=_StaticFetcher([_fetched_document()]),
        store=store,
        parser=parser,
    )

    first = pipeline.run([SOURCE])
    second = pipeline.run([SOURCE])

    assert first.created_count == 1
    assert first.clause_count == 2

    assert second.created_count == 0
    assert second.skipped_count == 1
    assert second.rejected_count == 0
    assert second.clause_count == 0
    assert second.outcomes[0].storage_key == f"raw/{PDF_DIGEST}.pdf"
    assert second.outcomes[0].clauses == []

    assert store.writes == 1
    assert parser.calls == 1


def test_pipeline_records_quality_rejection_without_duplicate_write() -> None:
    store = _MemoryStore()
    parser = _RecordingParser(error=DocumentQualityError("low_ocr_confidence"))
    pipeline = _pipeline(
        fetcher=_StaticFetcher([_fetched_document()]),
        store=store,
        parser=parser,
    )

    report = pipeline.run([SOURCE])

    assert report.errors == []
    assert report.created_count == 1
    assert report.rejected_count == 1
    assert report.outcomes[0].rejected_reason == "low_ocr_confidence"
    assert report.outcomes[0].clauses == []
    assert store.writes == 1


def test_pipeline_reports_parse_errors() -> None:
    parser = _RecordingParser(error=DocumentParseError("broken PDF"))
    pipeline = _pipeline(
        fetcher=_StaticFetcher([_fetched_document()]),
        store=_MemoryStore(),
        parser=parser,
    )

    report = pipeline.run([SOURCE])

    assert report.rejected_count == 1
    assert report.outcomes[0].rejected_reason == "parse_error"
    assert len(report.errors) == 1
    assert "parse failed" in report.errors[0]


def test_pipeline_reports_storage_and_fetch_failures() -> None:
    storage_report = _pipeline(
        fetcher=_StaticFetcher([_fetched_document()]),
        store=_FailingStore(),
        parser=_RecordingParser(),
    ).run([SOURCE])

    assert storage_report.outcomes == []
    assert len(storage_report.errors) == 1
    assert "storage failed" in storage_report.errors[0]

    fetch_report = _pipeline(
        fetcher=_FailingFetcher(),
        store=_MemoryStore(),
        parser=_RecordingParser(),
    ).run([SOURCE])

    assert fetch_report.outcomes == []
    assert len(fetch_report.errors) == 1
    assert "fetch failed" in fetch_report.errors[0]


# ---------------------------------------------------------------------------
# Logging and CLI
# ---------------------------------------------------------------------------


def test_pipeline_logs_pass_through_the_sanitizing_filter() -> None:
    stream = io.StringIO()
    target = logging.getLogger("mbiu.pipeline")
    configure_pipeline_logging(logger=target, stream=stream)

    logging.getLogger("mbiu.pipeline.fetch").warning(
        'Contact artist@example.com about "Net Receipts of the recording agreement"'
    )

    output = stream.getvalue()
    assert "[REDACTED_EMAIL]" in output
    assert "artist@example.com" not in output
    assert "[REDACTED_CONTRACT_TEXT]" in output


def test_settings_apply_defaults_and_validate_credentials() -> None:
    settings = PipelineSettings.from_env({})

    assert settings.firecrawl_base_url == "https://api.firecrawl.dev"
    assert settings.s3_region == "us-east-1"
    assert settings.max_pages_per_source == 25
    assert settings.job_timeout_s == 60.0
    assert settings.log_level == logging.INFO
    with pytest.raises(ConfigurationError, match="FIRECRAWL_API_KEY"):
        settings.validate()


def test_settings_read_overrides() -> None:
    settings = PipelineSettings.from_env(
        {
            "FIRECRAWL_API_KEY": "fc-key",
            "STORAGE_S3_ENDPOINT": "https://storage.example.org",
            "STORAGE_S3_KEY": "access",
            "STORAGE_S3_SECRET": "secret",
            "STORAGE_BUCKET": "corpus",
            "CORPUS_MAX_PAGES_PER_SOURCE": "5",
            "CORPUS_JOB_TIMEOUT_S": "12.5",
            "CORPUS_LOG_LEVEL": "debug",
        }
    )

    settings.validate()
    assert settings.max_pages_per_source == 5
    assert settings.job_timeout_s == 12.5
    assert settings.log_level == logging.DEBUG


@pytest.mark.parametrize(
    "env",
    [
        {"CORPUS_MAX_PAGES_PER_SOURCE": "zero"},
        {"CORPUS_MAX_PAGES_PER_SOURCE": "0"},
        {"CORPUS_JOB_TIMEOUT_S": "0"},
    ],
)
def test_settings_reject_invalid_limits(env: dict[str, str]) -> None:
    with pytest.raises(ConfigurationError):
        PipelineSettings.from_env(env)


def test_cli_runs_fetch_with_configured_sources(tmp_path: Path) -> None:
    path = _write_sources(
        tmp_path / "sources.yaml",
        """
        sources:
          - url: https://example.org/templates/
            licence: CC BY 4.0
            reviewing_body: Mbiu Legal Review
            contract_type: recording
            jurisdiction: KE
        """,
    )
    stub = _StubPipeline()

    exit_code = main(
        ["fetch", "--sources", str(path)],
        pipeline=cast(CorpusPipeline, stub),
        env={},
    )

    assert exit_code == 0
    assert [source.url for source in stub.sources] == [SOURCE.url]
    assert stub.sources[0].template_version == "1"


def test_cli_returns_zero_for_empty_sources_without_credentials(tmp_path: Path) -> None:
    path = _write_sources(tmp_path / "sources.yaml", "sources: []")
    stub = _StubPipeline()

    exit_code = main(
        ["fetch", "--sources", str(path)],
        pipeline=cast(CorpusPipeline, stub),
        env={},
    )

    assert exit_code == 0
    assert stub.sources == []


def test_cli_returns_two_when_credentials_are_missing(tmp_path: Path) -> None:
    path = _write_sources(
        tmp_path / "sources.yaml",
        """
        sources:
          - url: https://example.org/templates/
            licence: CC BY 4.0
            reviewing_body: Mbiu Legal Review
            contract_type: recording
            jurisdiction: KE
        """,
    )

    assert main(["fetch", "--sources", str(path)], env={}) == 2


def test_cli_returns_two_for_invalid_sources(tmp_path: Path) -> None:
    path = _write_sources(tmp_path / "sources.yaml", "sources: [not-a-mapping]")

    assert (
        main(
            ["fetch", "--sources", str(path)],
            pipeline=cast(CorpusPipeline, _StubPipeline()),
            env={},
        )
        == 2
    )


def test_cli_returns_one_when_the_report_contains_errors(tmp_path: Path) -> None:
    path = _write_sources(
        tmp_path / "sources.yaml",
        """
        sources:
          - url: https://example.org/templates/
            licence: CC BY 4.0
            reviewing_body: Mbiu Legal Review
            contract_type: recording
            jurisdiction: KE
        """,
    )
    stub = _StubPipeline(PipelineReport(errors=["fetch failed"]))

    assert (
        main(
            ["fetch", "--sources", str(path)],
            pipeline=cast(CorpusPipeline, stub),
            env={},
        )
        == 1
    )
