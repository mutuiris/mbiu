"""Orchestrate fetch, store, parse and split for every configured source."""

import json
import logging
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

from mbiu.pipeline.errors import (
    DocumentParseError,
    DocumentQualityError,
    FetchError,
    PipelineError,
    StorageError,
)
from mbiu.pipeline.models import (
    DocumentOutcome,
    DocumentParser,
    FetchedDocument,
    ObjectStore,
    PipelineReport,
    Source,
    SourceFetcher,
    StorageMetadata,
    TemplateClause,
)
from mbiu.pipeline.split import split_document


class CorpusPipeline:
    """Idempotent corpus ingestion across all stages."""

    def __init__(
        self,
        *,
        fetcher: SourceFetcher,
        store: ObjectStore,
        parser: DocumentParser,
        max_pages_per_source: int = 25,
        timeout_s: float = 60.0,
        logger: logging.Logger | None = None,
    ) -> None:
        """Wire the stage implementations and per-source limits."""
        self._fetcher = fetcher
        self._store = store
        self._parser = parser
        self._max_pages_per_source = max_pages_per_source
        self._timeout_s = timeout_s
        self._logger = logger or logging.getLogger(__name__)

    def run(self, sources: Sequence[Source]) -> PipelineReport:
        """Run every source once without duplicating stored objects.

        A document already present in storage is reported as skipped and is not
        parsed or written again.
        """
        outcomes: list[DocumentOutcome] = []
        errors: list[str] = []

        for source in sources:
            self._logger.info("Fetching %s", short_url(source.url))
            try:
                documents = self._fetcher.fetch(
                    source,
                    max_pages=self._max_pages_per_source,
                    timeout_s=self._timeout_s,
                )
            except FetchError as exc:
                message = f"fetch failed for {short_url(source.url)}: {exc}"
                self._logger.warning("%s", message)
                errors.append(message)
                continue

            self._logger.info(
                "Fetched %d document(s) from %s", len(documents), short_url(source.url)
            )
            for document in documents:
                outcome, error = self._process_document(source, document)
                if outcome is not None:
                    outcomes.append(outcome)
                if error is not None:
                    errors.append(error)

        return PipelineReport(outcomes=outcomes, errors=errors)

    def _process_document(
        self,
        source: Source,
        document: FetchedDocument,
    ) -> tuple[DocumentOutcome | None, str | None]:
        metadata = _metadata_for(source, document)
        try:
            stored = self._store.put_if_absent(document.content, metadata)
        except StorageError as exc:
            message = f"storage failed for {short_url(document.url)}: {exc}"
            self._logger.warning("%s", message)
            return None, message

        if not stored.created:
            self._logger.info("Skipping already stored %s", stored.key)
            return (
                DocumentOutcome(
                    source_url=source.url,
                    document_url=document.url,
                    sha256=stored.sha256,
                    storage_key=stored.key,
                    created=False,
                    rejected_reason=None,
                    clauses=[],
                ),
                None,
            )

        try:
            parsed = self._parser.parse(document)
        except DocumentQualityError as exc:
            self._logger.warning("Rejected %s: %s", short_url(document.url), exc.reason)
            return (
                DocumentOutcome(
                    source_url=source.url,
                    document_url=document.url,
                    sha256=stored.sha256,
                    storage_key=stored.key,
                    created=True,
                    rejected_reason=exc.reason,
                    clauses=[],
                ),
                None,
            )
        except DocumentParseError as exc:
            message = f"parse failed for {short_url(document.url)}: {exc}"
            self._logger.warning("%s", message)
            return (
                DocumentOutcome(
                    source_url=source.url,
                    document_url=document.url,
                    sha256=stored.sha256,
                    storage_key=stored.key,
                    created=True,
                    rejected_reason="parse_error",
                    clauses=[],
                ),
                message,
            )

        clauses = split_document(parsed, metadata, document_sha256=stored.sha256)
        self._logger.info("Split %s into %d clause(s)", stored.key, len(clauses))
        return (
            DocumentOutcome(
                source_url=source.url,
                document_url=document.url,
                sha256=stored.sha256,
                storage_key=stored.key,
                created=True,
                rejected_reason=None,
                clauses=clauses,
            ),
            None,
        )


def write_clauses(out_dir: Path, outcome: DocumentOutcome) -> Path:
    """Write one document's clauses as JSONL, keyed by its SHA-256, for the next stage.

    Rewriting the same document gives the same file, so reruns are safe.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{outcome.sha256}.jsonl"
    lines = (json.dumps(asdict(clause), sort_keys=True) + "\n" for clause in outcome.clauses)
    path.write_text("".join(lines), encoding="utf-8")
    return path


def read_clauses(clauses_dir: Path) -> list[TemplateClause]:
    """Read every ``<sha256>.jsonl`` file that ``write_clauses`` produced, in a stable order.

    Raises:
        PipelineError: If there are no clause files or a line is not a valid clause.
    """
    paths = sorted(clauses_dir.glob("*.jsonl"))
    if not paths:
        raise PipelineError(f"no clause files in {clauses_dir}; run the fetch command first")
    clauses: list[TemplateClause] = []
    for path in paths:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            try:
                clauses.append(TemplateClause(**json.loads(line)))
            except (TypeError, ValueError) as exc:
                raise PipelineError(f"{path.name} line {number} is not a valid clause") from exc
    return clauses


def short_url(url: str) -> str:
    """Host and file name only. The log filter treats lines of 120+ characters as contract
    text and hides them, so long URLs would hide the reason a source failed.
    """
    parts = urlsplit(url)
    name = unquote(Path(parts.path).name) or parts.path
    return f"{parts.netloc}/{name[:60]}"


def _metadata_for(source: Source, document: FetchedDocument) -> StorageMetadata:
    return StorageMetadata(
        source_url=source.url,
        document_url=document.url,
        fetched_at=document.fetched_at,
        licence=source.licence,
        reviewing_body=source.reviewing_body,
        template_version=source.template_version,
        contract_type=source.contract_type,
        jurisdiction=source.jurisdiction,
        content_type=document.content_type,
        filename=document.filename,
    )
