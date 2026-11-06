"""Typed failures raised by the corpus pipeline."""


class PipelineError(Exception):
    """Base class for every corpus pipeline failure."""


class ConfigurationError(PipelineError):
    """Raised when required pipeline configuration is missing or invalid."""


class SourceConfigError(PipelineError):
    """Raised when ``corpus/sources.yaml`` is malformed or incomplete."""


class FetchError(PipelineError):
    """Raised when Firecrawl cannot complete a crawl request."""


class FetchTimeoutError(FetchError):
    """Raised when a crawl job exceeds its configured deadline."""


class StorageError(PipelineError):
    """Raised when Supabase Storage rejects a request."""


class DocumentParseError(PipelineError):
    """Raised when a document cannot be converted by Docling."""


class UnsupportedDocumentError(DocumentParseError):
    """Raised for file types this pipeline does not parse."""


class DocumentQualityError(DocumentParseError):
    """Raised when parsed text is too garbled or low quality to publish.

    Attributes:
        reason: Short machine-readable rejection reason.
    """

    def __init__(self, reason: str) -> None:
        """Store the rejection reason and expose it as the exception message."""
        super().__init__(reason)
        self.reason = reason
