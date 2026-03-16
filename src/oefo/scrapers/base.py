"""
Base scraper class with common functionality for all data source scrapers.

Provides:
- HTTP request handling with retries and rate limiting
- PDF/file download with integrity checking
- BeautifulSoup HTML parsing
- Content deduplication via SHA-256 hashing
- Document metadata registration
- Comprehensive logging
"""

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..exceptions import TransientError, PermanentError, classify_http_error
from ..models import DocumentStatus, RawDocument, SourceType
from ..config.settings import USER_AGENT


# Configure module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.

    Provides common functionality for HTTP requests, file downloads, content
    deduplication, and document registration. Subclasses implement source-specific
    scraping logic.

    Attributes:
        name: Human-readable name of the scraper (e.g., "IFC", "EBRD")
        base_url: Base URL of the source website
        output_dir: Local directory for storing downloaded files
        rate_limit: Seconds to wait between HTTP requests (default: 1.0)
        session: Configured requests.Session with retries
        document_store: Set of content hashes for deduplication
        last_request_time: Timestamp of last HTTP request for rate limiting
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        output_dir: str,
        rate_limit: float = 1.0,
    ) -> None:
        """
        Initialize the scraper.

        Args:
            name: Human-readable scraper name
            base_url: Base URL of the target website
            output_dir: Directory for downloaded files
            rate_limit: Seconds between requests (default: 1.0)
        """
        self.name = name
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.rate_limit = rate_limit
        self.last_request_time = 0.0

        # Create output directory if needed
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Persistent document store — survives across runs
        self._hash_store_path = self.output_dir / ".document_hashes.json"
        self.document_store: set[str] = self._load_document_store()

        # Configure session with retries
        self.session = self._create_session()

        logger.info(f"Initialized {self.name} scraper: {self.base_url}")

    def _create_session(self) -> requests.Session:
        """
        Create a requests.Session with retry strategy.

        Implements exponential backoff for transient failures.

        Returns:
            Configured requests.Session
        """
        session = requests.Session()

        # Retry strategy: 3 attempts with exponential backoff
        retry_strategy = Retry(
            total=3,
            backoff_factor=1.0,  # 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set user agent from centralized config
        session.headers.update({"User-Agent": USER_AGENT})

        return session

    def _load_document_store(self) -> set[str]:
        """Load persisted content hashes from disk."""
        if self._hash_store_path.exists():
            try:
                data = json.loads(self._hash_store_path.read_text())
                hashes = set(data) if isinstance(data, list) else set()
                logger.debug(f"Loaded {len(hashes)} hashes from {self._hash_store_path}")
                return hashes
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not load hash store: {e}")
        return set()

    def _save_document_store(self) -> None:
        """Persist content hashes to disk."""
        try:
            self._hash_store_path.write_text(
                json.dumps(sorted(self.document_store), indent=0)
            )
        except OSError as e:
            logger.warning(f"Could not save hash store: {e}")

    def get_page(self, url: str) -> requests.Response:
        """
        Fetch a web page with rate limiting and retries.

        Applies rate limiting to respect server resources.
        Retries on transient errors (429, 5xx).

        Args:
            url: URL to fetch

        Returns:
            requests.Response object

        Raises:
            requests.RequestException: On persistent network errors
        """
        # Apply rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)

        logger.debug(f"GET {url}")
        self.last_request_time = time.time()

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else 0
            snippet = (e.response.text[:200] if e.response is not None else "")
            raise classify_http_error(
                status_code=status_code,
                url=url,
                source=self.name,
                response_snippet=snippet,
            ) from e
        except requests.exceptions.Timeout as e:
            raise TransientError(
                f"Timeout fetching {url}",
                source=self.name,
                url=url,
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise TransientError(
                f"Connection error for {url}: {e}",
                source=self.name,
                url=url,
            ) from e

        return response

    def get_soup(self, url: str) -> BeautifulSoup:
        """
        Fetch and parse an HTML page.

        Args:
            url: URL to fetch

        Returns:
            BeautifulSoup parsed HTML object

        Raises:
            requests.RequestException: On network errors
        """
        response = self.get_page(url)
        soup = BeautifulSoup(response.content, "html.parser")
        logger.debug(f"Parsed HTML from {url}")
        return soup

    def download_file(self, url: str, filename: str) -> Path:
        """
        Download a file from a URL.

        Validates Content-Type and file size. Computes SHA-256 hash for
        deduplication.

        Args:
            url: URL to download from
            filename: Local filename to save as

        Returns:
            Path to downloaded file

        Raises:
            requests.RequestException: On download error
            IOError: On file system error
        """
        filepath = self.output_dir / filename

        logger.info(f"Downloading {filename} from {url}")

        response = self.get_page(url)

        # Check content type and size
        content_type = response.headers.get("content-type", "")
        content_length = int(response.headers.get("content-length", 0))

        logger.debug(
            f"  Content-Type: {content_type}, Size: {content_length} bytes"
        )

        # Write file
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        logger.info(f"  Saved to {filepath}")
        return filepath

    def download_pdf(self, url: str, filename: str) -> Path:
        """
        Download a PDF file.

        Validates that file is actually a PDF and stores metadata.

        Args:
            url: URL to download from
            filename: Local filename (should end in .pdf)

        Returns:
            Path to downloaded PDF

        Raises:
            ValueError: If file is not a valid PDF
        """
        if not filename.endswith(".pdf"):
            filename = filename + ".pdf"

        filepath = self.download_file(url, filename)

        # Validate PDF magic bytes
        with open(filepath, "rb") as f:
            magic = f.read(4)
            if magic != b"%PDF":
                logger.warning(f"File {filepath} does not appear to be a valid PDF")
                raise ValueError(f"Invalid PDF file: {filepath}")

        logger.debug(f"Validated PDF: {filepath}")
        return filepath

    def _compute_content_hash(self, filepath: Path) -> str:
        """
        Compute SHA-256 hash of file contents.

        Args:
            filepath: Path to file

        Returns:
            Hex string of SHA-256 hash
        """
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def is_duplicate(self, url: str, filepath: Optional[Path] = None) -> bool:
        """
        Check if document is a duplicate based on content hash.

        Args:
            url: Source URL
            filepath: Optional path to already-downloaded file

        Returns:
            True if duplicate detected, False otherwise
        """
        if filepath and filepath.exists():
            content_hash = self._compute_content_hash(filepath)
            if content_hash in self.document_store:
                logger.warning(f"Duplicate detected: {url} (hash: {content_hash})")
                return True
            return False

        # Can't determine without file content
        return False

    def register_document(
        self,
        url: str,
        filepath: Path,
        source_type: SourceType,
        source_institution: Optional[str] = None,
        document_title: Optional[str] = None,
        document_date: Optional[str] = None,
    ) -> RawDocument:
        """
        Register a downloaded document in the store.

        Creates RawDocument metadata, computes content hash, and stores
        for deduplication.

        Args:
            url: Source URL
            filepath: Local file path
            source_type: Type of source (from SourceType enum)
            source_institution: Optional institution name
            document_title: Optional document title
            document_date: Optional publication date (YYYY-MM-DD)

        Returns:
            RawDocument metadata object
        """
        filepath = Path(filepath) if isinstance(filepath, str) else filepath
        content_hash = self._compute_content_hash(filepath)
        is_new = content_hash not in self.document_store
        self.document_store.add(content_hash)
        if is_new:
            self._save_document_store()

        file_size = filepath.stat().st_size
        mime_type = "application/pdf" if filepath.suffix == ".pdf" else "text/html"

        doc = RawDocument(
            document_id=f"{self.name}_{int(time.time())}_{filepath.stem}",
            source_url=url,
            local_file_path=str(filepath),
            content_hash=content_hash,
            source_type=source_type,
            source_institution=source_institution or self.name,
            download_date=datetime.now(),
            download_status=DocumentStatus.DOWNLOADED,
            file_size_bytes=file_size,
            mime_type=mime_type,
            document_title=document_title,
        )

        logger.info(
            f"Registered document: {doc.document_id} "
            f"(hash: {content_hash[:8]}..., size: {file_size} bytes)"
        )

        return doc

    @abstractmethod
    def scrape(self) -> list[RawDocument]:
        """
        Scrape data from the source.

        This method must be implemented by subclasses to define
        source-specific scraping logic.

        Returns:
            List of RawDocument objects representing downloaded files
        """
        pass
