"""Data contracts shared by the corpus pipeline stages."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Source:
    """A public template source declared in ``corpus/sources.yaml``."""

    url: str
    licence: str
    reviewing_body: str
    contract_type: str
    jurisdiction: str
    template_version: str = "1"


@dataclass(frozen=True)
class FetchedDocument:
    """A raw document returned by a source fetcher."""

    url: str
    content: bytes
    content_type: str
    filename: str
    fetched_at: datetime


@dataclass(frozen=True)
class StorageMetadata:
    """Metadata attached to a stored raw template."""

    source_url: str
    document_url: str
    fetched_at: datetime
    licence: str
    reviewing_body: str
    template_version: str
    contract_type: str
    jurisdiction: str
    content_type: str
    filename: str


@dataclass(frozen=True)
class StoredObject:
    """Result of an idempotent object write."""

    key: str
    sha256: str
    metadata: StorageMetadata
    created: bool


@dataclass(frozen=True)
class ParsedTable:
    """A table extracted from a template document."""

    rows: list[list[str]]


@dataclass(frozen=True)
class ParsedDocument:
    """Structured content produced by the parser."""

    text: str
    headings: list[str]
    tables: list[ParsedTable]
    page_count: int = 1
    ocr_confidence: float | None = None


@dataclass(frozen=True)
class TemplateClause:
    """A numbered, clean clause from a standard template."""

    clause_id: str
    section: str
    title: str | None
    text: str
    pages: list[int]
    source_url: str
    contract_type: str
    jurisdiction: str
    licence: str
    reviewing_body: str
    template_version: str
    document_sha256: str


@dataclass(frozen=True)
class DocumentOutcome:
    """What happened to one fetched document."""

    source_url: str
    document_url: str
    sha256: str
    storage_key: str
    created: bool
    rejected_reason: str | None
    clauses: list[TemplateClause]


@dataclass(frozen=True)
class PipelineReport:
    """Summary of one pipeline run."""

    outcomes: list[DocumentOutcome] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def created_count(self) -> int:
        """Number of documents stored for the first time."""
        return sum(1 for outcome in self.outcomes if outcome.created)

    @property
    def skipped_count(self) -> int:
        """Number of documents already present in storage."""
        return sum(1 for outcome in self.outcomes if not outcome.created)

    @property
    def rejected_count(self) -> int:
        """Number of stored documents rejected by the parser quality gate."""
        return sum(1 for outcome in self.outcomes if outcome.rejected_reason is not None)

    @property
    def clause_count(self) -> int:
        """Total number of split template clauses."""
        return sum(len(outcome.clauses) for outcome in self.outcomes)


class SourceFetcher(Protocol):
    """Fetches the raw documents for one configured source."""

    def fetch(
        self,
        source: Source,
        *,
        max_pages: int,
        timeout_s: float,
    ) -> list[FetchedDocument]:
        """Return at most ``max_pages`` documents or an empty list when blocked."""


class ObjectStore(Protocol):
    """Idempotent object storage for raw templates."""

    def put_if_absent(
        self,
        content: bytes,
        metadata: StorageMetadata,
    ) -> StoredObject:
        """Store ``content`` once and report whether this call created the object."""


class DocumentParser(Protocol):
    """Converts raw files into structured text, headings and tables."""

    def parse(self, document: FetchedDocument) -> ParsedDocument:
        """Parse ``document`` or raise a typed pipeline error."""
