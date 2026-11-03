"""Typed exceptions for document upload validation and text extraction.

Maps system extraction issues to plain, kind artist-facing explanations
without technical jargon or contract exposure.
"""


class DocumentError(Exception):
    """Base exception for all document upload and extraction failures.

    Attributes:
        user_message: Plain-language, artist-facing explanation.
        code: Machine-readable error code.
    """

    def __init__(self, user_message: str, code: str) -> None:
        """Initialize DocumentError with an artist-facing message and machine code.

        Args:
            user_message: Plain-language explanation intended for musicians.
            code: Short machine-readable identifier.
        """
        super().__init__(user_message)
        self.user_message = user_message
        self.code = code


class InvalidPDFError(DocumentError):
    """Raised when an uploaded file is not a valid PDF or has bad magic bytes."""

    def __init__(
        self,
        user_message: str = (
            "This file does not appear to be a valid PDF document. "
            "Please check the file and upload it again."
        ),
    ) -> None:
        """Initialize InvalidPDFError with default or custom artist message."""
        super().__init__(user_message=user_message, code="invalid_pdf")


class FileTooLargeError(DocumentError):
    """Raised when an uploaded PDF exceeds the maximum file size limit."""

    def __init__(
        self,
        limit_mb: int,
        user_message: str | None = None,
    ) -> None:
        """Initialize FileTooLargeError with configured size limit.

        Args:
            limit_mb: Configured maximum file size in megabytes.
            user_message: Optional custom message. If omitted, formatted message is used.
        """
        self.limit_mb = limit_mb
        message = (
            user_message
            if user_message is not None
            else (
                f"This file is larger than Mbiu can check right now "
                f"(limit: {limit_mb} MB). Try a smaller file."
            )
        )
        super().__init__(user_message=message, code="file_too_large")


class PageLimitExceededError(DocumentError):
    """Raised when an uploaded PDF exceeds the maximum allowed page count."""

    def __init__(
        self,
        limit_pages: int,
        user_message: str | None = None,
    ) -> None:
        """Initialize PageLimitExceededError with configured page count limit.

        Args:
            limit_pages: Configured maximum allowed page count.
            user_message: Optional custom message. If omitted, standard artist message is used.
        """
        self.limit_pages = limit_pages
        message = (
            user_message
            if user_message is not None
            else (
                f"This file is larger than Mbiu can check right now "
                f"(limit: {limit_pages} pages). Try a smaller file."
            )
        )
        super().__init__(user_message=message, code="page_limit_exceeded")


class EncryptedPDFError(DocumentError):
    """Raised when an uploaded PDF is password-protected or encrypted."""

    def __init__(
        self,
        user_message: str = (
            "This PDF is password-protected. Remove the password and upload it again."
        ),
    ) -> None:
        """Initialize EncryptedPDFError with standard artist message."""
        super().__init__(user_message=user_message, code="encrypted_pdf")


class ScannedPDFError(DocumentError):
    """Raised when a PDF contains only scanned images or has no extractable text layer."""

    def __init__(
        self,
        user_message: str = (
            "This PDF is a photo or scan, so Mbiu can't read the text. "
            "If you have the original document file, upload that instead."
        ),
    ) -> None:
        """Initialize ScannedPDFError with standard artist message."""
        super().__init__(user_message=user_message, code="scanned_pdf")


class EmptyPDFError(DocumentError):
    """Raised when an uploaded PDF document has zero pages or zero content."""

    def __init__(
        self,
        user_message: str = (
            "This PDF document does not contain any pages. Please upload a valid contract."
        ),
    ) -> None:
        """Initialize EmptyPDFError with standard artist message."""
        super().__init__(user_message=user_message, code="empty_pdf")


class ExtractionTimeoutError(DocumentError):
    """Raised when text extraction in the subprocess exceeds its page-scaled time limit."""

    def __init__(
        self,
        user_message: str = (
            "PDF extraction took longer than expected. "
            "Please try uploading a smaller or simpler file."
        ),
    ) -> None:
        """Initialize ExtractionTimeoutError with standard artist message."""
        super().__init__(user_message=user_message, code="extraction_timeout")


class ExtractionMemoryError(DocumentError):
    """Raised when text extraction in the subprocess exceeds its memory limit."""

    def __init__(
        self,
        user_message: str = (
            "PDF extraction exceeded available memory limits. Please try a smaller file."
        ),
    ) -> None:
        """Initialize ExtractionMemoryError with standard artist message."""
        super().__init__(user_message=user_message, code="extraction_memory_limit")


class ExtractionFailedError(DocumentError):
    """Raised when text extraction encounters an unrecoverable worker failure.

    Attributes:
        details: Optional technical diagnostic string for server-side logging.
    """

    def __init__(
        self,
        user_message: str = (
            "Mbiu was unable to extract text from this PDF. "
            "Please check the document format and try again."
        ),
        details: str | None = None,
    ) -> None:
        """Initialize ExtractionFailedError with standard artist message and optional details."""
        super().__init__(user_message=user_message, code="extraction_failed")
        self.details = details
