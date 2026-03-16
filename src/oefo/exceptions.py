"""
Structured exception hierarchy for OEFO pipeline.

Provides classified exceptions that enable:
- Distinguishing transient vs permanent failures
- Carrying diagnostic context for root cause analysis
- Informing retry/fallback decisions in the pipeline
"""

from __future__ import annotations

from typing import Any, Optional


class OEFOError(Exception):
    """Base exception for all OEFO errors."""

    def __init__(
        self,
        message: str,
        *,
        diagnostic: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.diagnostic = diagnostic or {}


# ---------------------------------------------------------------------------
# Scraper exceptions
# ---------------------------------------------------------------------------

class ScraperError(OEFOError):
    """Base exception for scraper failures."""

    def __init__(
        self,
        message: str,
        *,
        source: Optional[str] = None,
        url: Optional[str] = None,
        diagnostic: Optional[dict[str, Any]] = None,
    ) -> None:
        diag = diagnostic or {}
        if source:
            diag["source"] = source
        if url:
            diag["url"] = url
        super().__init__(message, diagnostic=diag)
        self.source = source
        self.url = url


class TransientError(ScraperError):
    """Retryable failure: HTTP 429/5xx, timeouts, DNS resolution."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        diag = kwargs.pop("diagnostic", None) or {}
        if status_code:
            diag["status_code"] = status_code
        super().__init__(message, diagnostic=diag, **kwargs)
        self.status_code = status_code


class PermanentError(ScraperError):
    """Non-retryable failure: HTTP 404, 403, authentication required."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        diag = kwargs.pop("diagnostic", None) or {}
        if status_code:
            diag["status_code"] = status_code
        super().__init__(message, diagnostic=diag, **kwargs)
        self.status_code = status_code


class ContentChangedError(ScraperError):
    """Site structure changed: DOM selectors broken, sitemap missing, new URL scheme."""
    pass


# ---------------------------------------------------------------------------
# Extraction exceptions
# ---------------------------------------------------------------------------

class ExtractionError(OEFOError):
    """Base exception for extraction failures."""
    pass


class NoTextError(ExtractionError):
    """PDF has no extractable text content."""
    pass


class OCRFailedError(ExtractionError):
    """OCR processing (Tesseract/poppler) failed."""
    pass


class LLMExtractionError(ExtractionError):
    """LLM returned invalid or no structured data."""
    pass


# ---------------------------------------------------------------------------
# QC exceptions
# ---------------------------------------------------------------------------

class QCError(OEFOError):
    """Base exception for quality control failures."""
    pass


class ValidationError(QCError):
    """Schema or data validation failure."""
    pass


class BenchmarkError(QCError):
    """Benchmark data unavailable for comparison."""
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Maps HTTP status codes to exception classes
_STATUS_MAP: dict[int, type[ScraperError]] = {
    400: PermanentError,
    401: PermanentError,
    403: PermanentError,
    404: PermanentError,
    410: PermanentError,
    429: TransientError,
    500: TransientError,
    502: TransientError,
    503: TransientError,
    504: TransientError,
}


def classify_http_error(
    status_code: int,
    url: str,
    source: Optional[str] = None,
    response_snippet: Optional[str] = None,
) -> ScraperError:
    """Create the appropriate ScraperError subclass for an HTTP status code.

    Args:
        status_code: HTTP response status code
        url: Request URL
        source: Scraper source name
        response_snippet: First ~200 chars of response body for diagnostics

    Returns:
        Appropriate ScraperError subclass instance
    """
    exc_cls = _STATUS_MAP.get(status_code, TransientError if status_code >= 500 else PermanentError)
    diag: dict[str, Any] = {"status_code": status_code}
    if response_snippet:
        diag["response_snippet"] = response_snippet[:200]
    return exc_cls(
        f"HTTP {status_code} for {url}",
        status_code=status_code,
        source=source,
        url=url,
        diagnostic=diag,
    )
