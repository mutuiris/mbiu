"""Fetch source documents, with strict robots.txt handling.

Direct links to a PDF or DOCX are downloaded as-is; web pages go through Firecrawl.
"""

import logging
import re
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from mbiu.pipeline.errors import FetchError, FetchTimeoutError
from mbiu.pipeline.models import FetchedDocument, Source

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.firecrawl.dev"
USER_AGENT = "mbiu-corpus-pipeline/0.1 (+https://mbiu.app)"
_API_VERSION = "v2"
# Links straight to a file are downloaded as-is; Firecrawl is for web pages
DOCUMENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
# Templates are a few MB at most; anything bigger is not what we expect
MAX_DOCUMENT_BYTES = 25 * 1024 * 1024


class RobotsGate(Protocol):
    """Decides whether a URL may be crawled."""

    def allowed(self, url: str, *, timeout_s: float) -> bool:
        """Return True only when robots.txt permits fetching ``url``."""


class RobotsPolicy:
    """Strict robots.txt gate: unreachable or disallowed means skip the fetch."""

    def __init__(
        self,
        *,
        client: httpx.Client,
        user_agent: str = USER_AGENT,
        timeout_s: float = 10.0,
    ) -> None:
        """Create a policy that reads robots.txt through ``client``."""
        self._client = client
        self._user_agent = user_agent
        self._timeout_s = timeout_s

    def allowed(self, url: str, *, timeout_s: float | None = None) -> bool:
        """Return True only when robots.txt is reachable and allows ``url``."""
        parts = urlsplit(url)
        robots_url = urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
        effective_timeout = self._timeout_s if timeout_s is None else timeout_s

        try:
            response = self._client.get(
                robots_url,
                headers={"User-Agent": self._user_agent},
                timeout=effective_timeout,
            )
        except httpx.HTTPError as exc:
            logger.warning("Skipping %s: robots.txt unreachable (%s)", url, type(exc).__name__)
            return False

        if response.status_code in (404, 410):
            return True
        if response.status_code != 200:
            logger.warning("Skipping %s: robots.txt returned %s", url, response.status_code)
            return False

        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        permitted = parser.can_fetch(self._user_agent, url)
        if not permitted:
            logger.info("Skipping %s: robots.txt disallows this crawler", url)
        return permitted


class FirecrawlFetcher:
    """Crawl a source with Firecrawl's crawl API and return capped page content."""

    def __init__(
        self,
        *,
        api_key: str,
        client: httpx.Client,
        robots: RobotsGate | None = None,
        base_url: str = DEFAULT_BASE_URL,
        user_agent: str = USER_AGENT,
        poll_interval_s: float = 1.0,
        now: Callable[[], datetime] | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Wire the Firecrawl API client, robots policy, timing and page limits."""
        self._api_key = api_key
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent
        self._robots = robots or RobotsPolicy(client=client, user_agent=user_agent)
        self._poll_interval_s = poll_interval_s
        self._now = now or (lambda: datetime.now(UTC))
        self._clock = clock
        self._sleep = sleep

    def fetch(
        self,
        source: Source,
        *,
        max_pages: int,
        timeout_s: float,
    ) -> list[FetchedDocument]:
        """Crawl one source, capped at ``max_pages``, within ``timeout_s``.

        Returns an empty list when robots.txt is unreachable or disallows the source.

        Raises:
            FetchError: When Firecrawl rejects or fails the crawl job.
            FetchTimeoutError: When the crawl job exceeds ``timeout_s``.
        """
        if max_pages < 1 or timeout_s <= 0:
            return []
        if not self._robots.allowed(source.url, timeout_s=min(timeout_s, 10.0)):
            return []
        suffix = Path(urlsplit(source.url).path).suffix.lower()
        if suffix in DOCUMENT_TYPES:
            return [self._download(source, DOCUMENT_TYPES[suffix], timeout_s)]

        deadline = self._clock() + timeout_s
        job_id = self._start_crawl(source, max_pages, timeout_s)
        logger.info("Started Firecrawl crawl %s for %s", job_id, source.url)

        while True:
            remaining = deadline - self._clock()
            if remaining <= 0:
                raise FetchTimeoutError(f"Firecrawl crawl {job_id} timed out")
            payload = self._poll_crawl(job_id, min(remaining, timeout_s))
            status = payload.get("status")
            if status == "completed":
                return self._documents(payload.get("data"), source, max_pages)
            if status in ("failed", "cancelled"):
                raise FetchError(f"Firecrawl crawl {job_id} ended with status {status}")
            self._sleep(min(self._poll_interval_s, remaining))

    def _start_crawl(self, source: Source, max_pages: int, timeout_s: float) -> str:
        body: dict[str, object] = {
            "url": source.url,
            "limit": max_pages,
            "ignoreRobotsTxt": False,
            "scrapeOptions": {"formats": ["markdown", "html"]},
        }
        try:
            response = self._client.post(
                self._endpoint("crawl"),
                headers=self._headers(),
                json=body,
                timeout=timeout_s,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FetchError(f"Firecrawl crawl request failed for {source.url}") from exc

        payload = response.json()
        job_id = payload.get("id") if isinstance(payload, Mapping) else None
        if not isinstance(job_id, str) or not job_id:
            raise FetchError("Firecrawl did not return a crawl job id")
        return job_id

    def _poll_crawl(self, job_id: str, timeout_s: float) -> Mapping[Any, Any]:
        try:
            response = self._client.get(
                self._endpoint(f"crawl/{job_id}"),
                headers=self._headers(),
                timeout=timeout_s,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FetchError(f"Firecrawl crawl poll failed for job {job_id}") from exc

        payload = response.json()
        if not isinstance(payload, Mapping):
            raise FetchError(f"Firecrawl returned an invalid crawl payload for job {job_id}")
        return payload

    def _download(self, source: Source, content_type: str, timeout_s: float) -> FetchedDocument:
        """Download a file the source links to directly, keeping its original bytes."""
        try:
            response = self._client.get(
                source.url,
                headers={"User-Agent": self._user_agent, "Accept": f"{content_type},*/*"},
                timeout=timeout_s,
                follow_redirects=True,
            )
        except httpx.HTTPError as exc:
            raise FetchError(f"download failed: {type(exc).__name__}") from exc
        if response.status_code != 200:
            raise FetchError(f"download returned {response.status_code}")
        if len(response.content) > MAX_DOCUMENT_BYTES:
            raise FetchError("download is larger than expected")
        name = Path(urlsplit(source.url).path).name
        return FetchedDocument(
            url=source.url,
            content=response.content,
            content_type=content_type,
            filename=re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "document",
            fetched_at=self._now(),
        )

    def _documents(
        self,
        raw_data: object,
        source: Source,
        max_pages: int,
    ) -> list[FetchedDocument]:
        if raw_data is None:
            return []
        if not isinstance(raw_data, list):
            raise FetchError("Firecrawl crawl payload is missing its data list")

        fetched_at = self._now()
        documents: list[FetchedDocument] = []
        for item in raw_data[:max_pages]:
            if not isinstance(item, Mapping):
                continue
            result = _result_content(item)
            if result is None:
                continue
            content, content_type = result
            url = _text(item.get("url")) or source.url
            documents.append(
                FetchedDocument(
                    url=url,
                    content=content.encode("utf-8"),
                    content_type=content_type,
                    filename=_filename(url, content_type, len(documents)),
                    fetched_at=fetched_at,
                )
            )
        return documents

    def _endpoint(self, path: str) -> str:
        return f"{self._base_url}/{_API_VERSION}/{path.lstrip('/')}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": self._user_agent,
        }


def _result_content(item: Mapping[Any, Any]) -> tuple[str, str] | None:
    markdown = item.get("markdown")
    if isinstance(markdown, str) and markdown.strip():
        return markdown, "text/markdown"
    for key in ("html", "rawHtml"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value, "text/html"
    return None


def _filename(url: str, content_type: str, index: int) -> str:
    """Name fetched content after the URL but always reflect its real media type.

    Firecrawl converts crawled documents to markdown or HTML, even when the source
    URL ends in ``.pdf``. Forcing the extension keeps content-addressed keys and
    downstream parsers aligned with what was actually fetched.
    """
    path = Path(urlsplit(url).path)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", path.name).strip("._")
    if not name:
        name = f"page-{index + 1}"
    suffix = ".md" if content_type == "text/markdown" else ".html"
    stem = Path(name).stem if Path(name).suffix else name
    return f"{stem}{suffix}"


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None
