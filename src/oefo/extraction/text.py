"""
Tier 1: Native Text Extraction from PDFs

This module provides direct text extraction from PDF documents using pdfplumber
(primary) and PyMuPDF (fallback). Optimized for documents with embedded text content.

Key Features:
- Table extraction with structural preservation
- Financial keyword detection for relevance filtering
- Page-level text quality assessment
- Graceful fallback between extraction methods
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)

# Financial keywords indicating relevant content for WACC/cost of capital extraction
FINANCIAL_KEYWORDS = {
    "wacc",
    "weighted average cost of capital",
    "cost of debt",
    "cost of equity",
    "rate of return",
    "interest rate",
    "leverage",
    "gearing",
    "spread",
    "basis points",
    "coupon",
    "maturity",
    "tenor",
    "discount rate",
    "capm",
    "capital asset pricing",
    "risk-free rate",
    "market risk premium",
    "beta",
    "cost of capital",
    "hurdle rate",
    "required return",
    "debt/equity",
    "capital structure",
    "financing terms",
    "coupon rate",
}


class TextExtractor:
    """
    Extract native text content from PDFs using pdfplumber and PyMuPDF.

    Provides methods for:
    - Full document text extraction with page preservation
    - Structured table detection and extraction
    - Financial content relevance detection
    - Text quality assessment
    """

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        """
        Initialize TextExtractor.

        Args:
            logger_instance: Optional logger for detailed processing logs.
        """
        self.logger = logger_instance or logger
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Verify that required PDF libraries are available."""
        if pdfplumber is None:
            self.logger.warning(
                "pdfplumber not installed. Install with: pip install pdfplumber"
            )
        if fitz is None:
            self.logger.warning(
                "PyMuPDF (fitz) not installed. Install with: pip install PyMuPDF"
            )

    def extract_text(self, pdf_path: str) -> Dict:
        """
        Extract text from all pages of a PDF document.

        Uses pdfplumber as primary method; falls back to PyMuPDF if pdfplumber
        is unavailable or fails.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Dictionary containing:
                - pages: List of dicts with keys:
                    - page_num: 0-indexed page number
                    - text: Extracted text content
                    - tables_found: Number of tables detected on page
                - metadata: PDF metadata (title, author, etc.)
                - total_pages: Total number of pages in document
                - extraction_method: 'pdfplumber' or 'pymupdf'
                - success: Boolean indicating successful extraction
                - error: Error message if extraction failed

        Raises:
            FileNotFoundError: If PDF file does not exist.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Try pdfplumber first
        if pdfplumber is not None:
            try:
                return self._extract_with_pdfplumber(pdf_path)
            except Exception as e:
                self.logger.warning(
                    f"pdfplumber extraction failed for {pdf_path.name}: {str(e)}. "
                    "Attempting fallback with PyMuPDF."
                )

        # Fall back to PyMuPDF
        if fitz is not None:
            try:
                return self._extract_with_pymupdf(pdf_path)
            except Exception as e:
                self.logger.error(
                    f"PyMuPDF extraction also failed for {pdf_path.name}: {str(e)}"
                )
                return {
                    "pages": [],
                    "metadata": {},
                    "total_pages": 0,
                    "extraction_method": None,
                    "success": False,
                    "error": str(e),
                }

        # No extraction method available
        error_msg = "No PDF extraction library available (install pdfplumber or PyMuPDF)"
        self.logger.error(error_msg)
        return {
            "pages": [],
            "metadata": {},
            "total_pages": 0,
            "extraction_method": None,
            "success": False,
            "error": error_msg,
        }

    def _extract_with_pdfplumber(self, pdf_path: Path) -> Dict:
        """
        Extract text using pdfplumber.

        Args:
            pdf_path: Path object to PDF file.

        Returns:
            Extraction result dictionary.
        """
        pages_data = []

        with pdfplumber.open(pdf_path) as pdf:
            metadata = {
                "title": pdf.metadata.get("Title", ""),
                "author": pdf.metadata.get("Author", ""),
                "subject": pdf.metadata.get("Subject", ""),
                "creator": pdf.metadata.get("Creator", ""),
                "producer": pdf.metadata.get("Producer", ""),
            }

            for page_idx, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                tables = page.find_tables()
                tables_count = len(tables) if tables else 0

                pages_data.append(
                    {
                        "page_num": page_idx,
                        "text": text,
                        "tables_found": tables_count,
                    }
                )

            self.logger.info(
                f"Extracted text from {len(pages_data)} pages using pdfplumber"
            )

        return {
            "pages": pages_data,
            "metadata": metadata,
            "total_pages": len(pages_data),
            "extraction_method": "pdfplumber",
            "success": True,
            "error": None,
        }

    def _extract_with_pymupdf(self, pdf_path: Path) -> Dict:
        """
        Extract text using PyMuPDF (fitz).

        Args:
            pdf_path: Path object to PDF file.

        Returns:
            Extraction result dictionary.
        """
        pages_data = []
        doc = fitz.open(pdf_path)

        metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "creator": doc.metadata.get("creator", ""),
            "producer": doc.metadata.get("producer", ""),
        }

        for page_idx, page in enumerate(doc):
            text = page.get_text()
            tables = page.find_tables()
            tables_count = len(tables) if tables else 0

            pages_data.append(
                {
                    "page_num": page_idx,
                    "text": text,
                    "tables_found": tables_count,
                }
            )

        doc.close()
        self.logger.info(
            f"Extracted text from {len(pages_data)} pages using PyMuPDF"
        )

        return {
            "pages": pages_data,
            "metadata": metadata,
            "total_pages": len(pages_data),
            "extraction_method": "pymupdf",
            "success": True,
            "error": None,
        }

    def extract_tables(self, pdf_path: str) -> List[pd.DataFrame]:
        """
        Extract all tables from a PDF as pandas DataFrames.

        Attempts table extraction using pdfplumber's structured table detection.
        Falls back to PyMuPDF if pdfplumber is unavailable.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of pandas DataFrames, one per detected table.
            Empty list if no tables found or extraction fails.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        tables = []

        if pdfplumber is not None:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page_idx, page in enumerate(pdf.pages):
                        page_tables = page.extract_tables()
                        if page_tables:
                            for table_idx, table in enumerate(page_tables):
                                df = pd.DataFrame(table[1:], columns=table[0])
                                df["_source_page"] = page_idx
                                df["_table_num"] = table_idx
                                tables.append(df)
                                self.logger.debug(
                                    f"Extracted table {len(tables)} from page {page_idx}"
                                )
                return tables
            except Exception as e:
                self.logger.warning(
                    f"pdfplumber table extraction failed: {str(e)}. "
                    "Attempting fallback with PyMuPDF."
                )

        if fitz is not None:
            try:
                doc = fitz.open(pdf_path)
                for page_idx, page in enumerate(doc):
                    page_tables = page.find_tables()
                    if page_tables:
                        for table_idx, table in enumerate(page_tables.tables):
                            # Convert table to list of lists for DataFrame
                            table_data = []
                            for row in table:
                                row_data = []
                                for cell in row:
                                    row_data.append(cell.get_text().strip())
                                table_data.append(row_data)

                            if table_data:
                                df = pd.DataFrame(
                                    table_data[1:], columns=table_data[0]
                                )
                                df["_source_page"] = page_idx
                                df["_table_num"] = table_idx
                                tables.append(df)
                                self.logger.debug(
                                    f"Extracted table {len(tables)} from page {page_idx}"
                                )
                doc.close()
            except Exception as e:
                self.logger.error(f"PyMuPDF table extraction failed: {str(e)}")

        return tables

    def detect_financial_pages(self, pdf_path: str) -> List[int]:
        """
        Detect pages containing financial keywords relevant to cost of capital.

        Searches for terms like WACC, cost of debt, leverage, etc. to identify
        pages likely to contain relevant financial data.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of 0-indexed page numbers containing financial keywords.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        extraction_result = self.extract_text(str(pdf_path))
        if not extraction_result["success"]:
            self.logger.warning(
                f"Could not extract text for financial page detection: "
                f"{extraction_result['error']}"
            )
            return []

        financial_pages = []

        for page_data in extraction_result["pages"]:
            text_lower = page_data["text"].lower()

            # Check for financial keywords
            for keyword in FINANCIAL_KEYWORDS:
                if keyword in text_lower:
                    financial_pages.append(page_data["page_num"])
                    self.logger.debug(
                        f"Financial keyword '{keyword}' found on page {page_data['page_num']}"
                    )
                    break  # Only count each page once

        self.logger.info(
            f"Detected {len(financial_pages)} financial pages: {financial_pages}"
        )
        return financial_pages

    def is_text_quality_sufficient(
        self, text: str, min_chars_per_page: int = 50
    ) -> bool:
        """
        Assess whether extracted text quality is sufficient for processing.

        Simple heuristic: checks if text length exceeds minimum threshold and
        contains non-whitespace characters.

        Args:
            text: Extracted text content from a page or document.
            min_chars_per_page: Minimum character count to consider text quality sufficient.
                Default: 50 characters.

        Returns:
            True if text quality is sufficient, False otherwise.
        """
        if not text:
            return False

        # Count non-whitespace characters
        non_ws_chars = len(text.strip())

        is_sufficient = non_ws_chars >= min_chars_per_page
        self.logger.debug(
            f"Text quality check: {non_ws_chars} chars >= {min_chars_per_page} min. "
            f"Result: {is_sufficient}"
        )

        return is_sufficient
