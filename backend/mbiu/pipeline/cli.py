"""Command line entry point for the corpus pipeline."""

import argparse
import logging
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import httpx

from mbiu.pipeline.errors import ConfigurationError, SourceConfigError
from mbiu.pipeline.fetch import DEFAULT_BASE_URL, USER_AGENT, FirecrawlFetcher, RobotsPolicy
from mbiu.pipeline.logging_setup import configure_pipeline_logging
from mbiu.pipeline.parse import DoclingParser
from mbiu.pipeline.pipeline import CorpusPipeline, write_clauses
from mbiu.pipeline.sources import load_sources
from mbiu.pipeline.store import SupabaseS3Store


@dataclass(frozen=True)
class PipelineSettings:
    """Environment-driven configuration for the real pipeline clients."""

    firecrawl_api_key: str
    firecrawl_base_url: str
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_region: str
    max_pages_per_source: int
    job_timeout_s: float
    log_level: int

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> PipelineSettings:
        """Read settings from environment variables with safe defaults."""
        values = os.environ if env is None else env
        return cls(
            firecrawl_api_key=_clean(values.get("FIRECRAWL_API_KEY")),
            firecrawl_base_url=(_clean(values.get("FIRECRAWL_BASE_URL")) or DEFAULT_BASE_URL),
            s3_endpoint=_clean(values.get("STORAGE_S3_ENDPOINT")),
            s3_access_key=_clean(values.get("STORAGE_S3_KEY")),
            s3_secret_key=_clean(values.get("STORAGE_S3_SECRET")),
            s3_bucket=_clean(values.get("STORAGE_BUCKET")),
            s3_region=_clean(values.get("STORAGE_S3_REGION")) or "us-east-1",
            max_pages_per_source=_positive_int(
                values.get("CORPUS_MAX_PAGES_PER_SOURCE"),
                25,
                "CORPUS_MAX_PAGES_PER_SOURCE",
            ),
            job_timeout_s=_positive_float(
                values.get("CORPUS_JOB_TIMEOUT_S"),
                60.0,
                "CORPUS_JOB_TIMEOUT_S",
            ),
            log_level=_log_level(values.get("CORPUS_LOG_LEVEL")),
        )

    def validate(self) -> None:
        """Raise when a required credential or storage setting is missing."""
        required = {
            "FIRECRAWL_API_KEY": self.firecrawl_api_key,
            "STORAGE_S3_ENDPOINT": self.s3_endpoint,
            "STORAGE_S3_KEY": self.s3_access_key,
            "STORAGE_S3_SECRET": self.s3_secret_key,
            "STORAGE_BUCKET": self.s3_bucket,
        }
        missing = sorted(name for name, value in required.items() if not value)
        if missing:
            raise ConfigurationError("missing required settings: " + ", ".join(missing))


def build_pipeline(
    settings: PipelineSettings,
    *,
    max_pages: int | None = None,
    timeout_s: float | None = None,
) -> CorpusPipeline:
    """Construct the production Firecrawl, Supabase S3 and Docling pipeline."""
    settings.validate()
    effective_pages = settings.max_pages_per_source if max_pages is None else max_pages
    effective_timeout = settings.job_timeout_s if timeout_s is None else timeout_s
    if effective_pages < 1:
        raise ConfigurationError("max pages must be at least 1")
    if effective_timeout <= 0:
        raise ConfigurationError("job timeout must be positive")

    client = httpx.Client(timeout=effective_timeout)
    robots = RobotsPolicy(client=client, user_agent=USER_AGENT)
    fetcher = FirecrawlFetcher(
        api_key=settings.firecrawl_api_key,
        client=client,
        robots=robots,
        base_url=settings.firecrawl_base_url,
        user_agent=USER_AGENT,
    )
    store = SupabaseS3Store(
        endpoint=settings.s3_endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket=settings.s3_bucket,
        region=settings.s3_region,
        client=client,
        timeout_s=effective_timeout,
    )
    return CorpusPipeline(
        fetcher=fetcher,
        store=store,
        parser=DoclingParser(),
        max_pages_per_source=effective_pages,
        timeout_s=effective_timeout,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    pipeline: CorpusPipeline | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    """Run the requested pipeline command and return a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    configure_pipeline_logging()
    logger = logging.getLogger(__name__)

    try:
        settings = PipelineSettings.from_env(env)
    except ConfigurationError as exc:
        logger.error("Invalid pipeline configuration: %s", exc)
        return 2
    configure_pipeline_logging(level=settings.log_level)

    sources_path: Path = args.sources
    try:
        sources = load_sources(sources_path)
    except SourceConfigError as exc:
        logger.error("Cannot load sources: %s", exc)
        return 2

    if not sources:
        logger.info("No sources configured in %s", sources_path)
        return 0

    active_pipeline = pipeline
    if active_pipeline is None:
        try:
            active_pipeline = build_pipeline(
                settings,
                max_pages=args.max_pages,
                timeout_s=args.timeout,
            )
        except ConfigurationError as exc:
            logger.error("Pipeline configuration error: %s", exc)
            return 2

    report = active_pipeline.run(sources)
    out_dir: Path = args.out
    for outcome in report.outcomes:
        if outcome.clauses:
            write_clauses(out_dir, outcome)
    logger.info(
        "Corpus fetch complete: %d created, %d skipped, %d rejected, %d clauses",
        report.created_count,
        report.skipped_count,
        report.rejected_count,
        report.clause_count,
    )
    return 1 if report.errors else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m mbiu.pipeline",
        description="Fetch and version public music contract templates.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    fetch = subcommands.add_parser(
        "fetch",
        help="Fetch sources, store raw files, parse them and split numbered clauses.",
    )
    fetch.add_argument(
        "--sources",
        type=Path,
        default=_default_sources_path(),
        help="Path to corpus/sources.yaml.",
    )
    fetch.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Override the per-source page cap.",
    )
    fetch.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Override the per-source job timeout in seconds.",
    )
    fetch.add_argument(
        "--out",
        type=Path,
        default=_default_sources_path().parent / "clauses",
        help="Directory for split clauses, one <sha256>.jsonl per document.",
    )
    return parser


def _default_sources_path() -> Path:
    return Path(__file__).resolve().parents[3] / "corpus" / "sources.yaml"


def _clean(raw: str | None) -> str:
    return raw.strip() if raw else ""


def _positive_int(raw: str | None, default: int, name: str) -> int:
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value < 1:
        raise ConfigurationError(f"{name} must be at least 1")
    return value


def _positive_float(raw: str | None, default: float, name: str) -> float:
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be positive")
    return value


def _log_level(raw: str | None) -> int:
    if not raw or not raw.strip():
        return logging.INFO
    return logging.getLevelNamesMapping().get(raw.strip().upper(), logging.INFO)
