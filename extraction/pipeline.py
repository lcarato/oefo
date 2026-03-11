"""
Extraction Pipeline Orchestrator

Implements the multi-tier extraction decision tree:
1. Tier 1 (Text): Native text extraction with LLM structuring
2. Tier 2 (OCR): OCR with LLM post-processing for scanned documents
3. Tier 3 (Vision): Claude Vision API for authoritative table recognition
4. Cross-reference: Reconciliation between text-based and vision results

Decision Logic:
- Start with Tier 1 (fast, cheap). If text quality sufficient and financial terms found → use it
- If Tier 1 fails → apply Tier 2 (OCR). If clean text → use it
- For ALL documents with tables → apply Tier 3 Vision (authoritative)
- When both Tier 1/2 and Tier 3 exist → cross-reference and flag discrepancies
"""

import logging
from pathlib import Path
from typing import List, Optional

from .text import TextExtractor
from .ocr import OCRExtractor
from .vision import VisionExtractor

logger = logging.getLogger(__name__)


class ExtractionResult:
    """
    Represents a data extraction result from the pipeline.

    Every ExtractionResult carries full traceability metadata:
    - source_document_url: URL of the original document
    - source_document_id: Foreign key to RawDocument
    - page_num: Page number where data was found
    - source_quote: Verbatim quote supporting the extraction
    - source_table_or_section: Table/section identifier within the page

    Attributes:
        page_num: Page number where data was extracted
        tier: Extraction tier used (TIER_1_TEXT, TIER_2_OCR, TIER_3_VISION)
        extracted_data: Dict of extracted financial parameters
        source_quote: Direct quote from source document
        confidence: Confidence score (0.0-1.0)
        notes: Additional notes and caveats
        source_document_url: URL of the source document
        source_document_id: Foreign key to RawDocument
        source_table_or_section: Table/section reference within the page
        extraction_model: LLM model used for extraction
    """

    def __init__(
        self,
        page_num: int,
        tier: str,
        extracted_data: dict,
        source_quote: Optional[str] = None,
        confidence: float = 0.5,
        notes: Optional[str] = None,
        source_document_url: Optional[str] = None,
        source_document_id: Optional[str] = None,
        source_table_or_section: Optional[str] = None,
        extraction_model: Optional[str] = None,
    ):
        self.page_num = page_num
        self.tier = tier
        self.extracted_data = extracted_data
        self.source_quote = source_quote
        self.confidence = confidence
        self.notes = notes or ""
        self.source_document_url = source_document_url
        self.source_document_id = source_document_id
        self.source_table_or_section = source_table_or_section
        self.extraction_model = extraction_model

    def to_dict(self) -> dict:
        """Convert result to dictionary including full provenance."""
        return {
            "page_num": self.page_num,
            "tier": self.tier,
            "extracted_data": self.extracted_data,
            "source_quote": self.source_quote,
            "confidence": self.confidence,
            "notes": self.notes,
            "source_document_url": self.source_document_url,
            "source_document_id": self.source_document_id,
            "source_table_or_section": self.source_table_or_section,
            "extraction_model": self.extraction_model,
        }

    @property
    def has_full_traceability(self) -> bool:
        """Check if this result has full traceability back to the source."""
        return bool(
            self.source_document_url
            and self.page_num
            and self.source_quote
        )

    def __repr__(self) -> str:
        traceable = "TRACEABLE" if self.has_full_traceability else "INCOMPLETE"
        return (
            f"ExtractionResult(page={self.page_num}, tier={self.tier}, "
            f"confidence={self.confidence:.2f}, {traceable})"
        )


class ExtractionPipeline:
    """
    Multi-tier PDF extraction orchestrator.

    Implements decision tree for selecting extraction tier based on document
    characteristics and progressively applies more sophisticated methods
    (text → OCR → Vision) as needed.
    """

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        """
        Initialize ExtractionPipeline.

        Args:
            logger_instance: Optional logger for detailed logs.
        """
        self.logger = logger_instance or logger
        self.text_extractor = TextExtractor(logger_instance=self.logger)
        self.ocr_extractor = OCRExtractor(logger_instance=self.logger)
        self.vision_extractor = VisionExtractor(logger_instance=self.logger)

    def extract(
        self,
        pdf_path: str,
        source_type: str,
        source_institution: Optional[str] = None,
        source_document_url: Optional[str] = None,
        source_document_id: Optional[str] = None,
    ) -> List[ExtractionResult]:
        """
        Extract financial data from PDF using multi-tier pipeline.

        Orchestrates the extraction decision tree:
        1. Attempt Tier 1 (text extraction)
        2. If insufficient, apply Tier 2 (OCR)
        3. For tables, always apply Tier 3 (Vision)
        4. Cross-reference results

        Every ExtractionResult carries full traceability metadata (document URL,
        page number, source quote) to support end-to-end audit trails.

        Args:
            pdf_path: Path to PDF file.
            source_type: Type of document ('regulatory', 'dfi', 'corporate', 'bond').
            source_institution: Name of institution (for logging/filtering).
            source_document_url: URL where document was obtained (for traceability).
            source_document_id: RawDocument.document_id (for traceability).

        Returns:
            List of ExtractionResult objects with extracted data and provenance.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Store document metadata for traceability propagation
        self._current_doc_url = source_document_url
        self._current_doc_id = source_document_id

        self.logger.info(
            f"Starting extraction pipeline for {pdf_path.name} "
            f"(type={source_type}, institution={source_institution})"
        )

        all_results = []

        # Step 1: Decide tier
        tier = self.decide_tier(str(pdf_path))
        self.logger.info(f"Selected tier: {tier}")

        # Step 2: Run initial extraction
        if tier == "tier_1_text":
            results = self.run_tier1(str(pdf_path), source_type)
            all_results.extend(results)

            # If Tier 1 succeeds but document has tables, apply Tier 3 Vision
            text_result = self.text_extractor.extract_text(str(pdf_path))
            has_tables = any(
                p.get("tables_found", 0) > 0 for p in text_result.get("pages", [])
            )

            if has_tables and results:
                self.logger.info(
                    "Document has tables; applying Tier 3 Vision for table extraction"
                )
                vision_results = self.run_tier3(
                    str(pdf_path), None, source_type
                )
                all_results = self.cross_reference(results, vision_results)

        elif tier == "tier_2_ocr":
            results = self.run_tier2(str(pdf_path), source_type)
            all_results.extend(results)

        # Step 3: Check if Tier 1/2 failed but document still has financial content
        if not all_results or self._results_quality_insufficient(all_results):
            self.logger.warning(
                "Tier 1/2 results insufficient; attempting Tier 3 Vision"
            )
            financial_pages = self.text_extractor.detect_financial_pages(
                str(pdf_path)
            )
            if financial_pages:
                vision_results = self.run_tier3(
                    str(pdf_path), financial_pages, source_type
                )
                if vision_results:
                    all_results = vision_results

        # Propagate document-level traceability to all results
        for result in all_results:
            if not result.source_document_url and self._current_doc_url:
                result.source_document_url = self._current_doc_url
            if not result.source_document_id and self._current_doc_id:
                result.source_document_id = self._current_doc_id

        # Traceability audit
        traceable = sum(1 for r in all_results if r.has_full_traceability)
        self.logger.info(
            f"Extraction complete: {len(all_results)} results extracted, "
            f"{traceable}/{len(all_results)} with full traceability"
        )
        if traceable < len(all_results):
            self.logger.warning(
                f"TRACEABILITY GAP: {len(all_results) - traceable} results "
                f"missing full provenance (URL + page + quote)"
            )

        return all_results

    def decide_tier(self, pdf_path: str) -> str:
        """
        Determine which extraction tier to use based on document characteristics.

        Decision logic:
        1. If text extraction succeeds and quality sufficient → TIER_1
        2. Otherwise → TIER_2 (OCR)

        Args:
            pdf_path: Path to PDF file.

        Returns:
            Tier identifier: 'tier_1_text' or 'tier_2_ocr'
        """
        try:
            # Attempt text extraction
            result = self.text_extractor.extract_text(pdf_path)

            if not result.get("success", False):
                self.logger.info("Text extraction failed; using Tier 2 OCR")
                return "tier_2_ocr"

            # Check text quality across pages
            pages = result.get("pages", [])
            sufficient_quality_pages = sum(
                1
                for p in pages
                if self.text_extractor.is_text_quality_sufficient(p.get("text", ""))
            )

            quality_ratio = (
                sufficient_quality_pages / len(pages) if pages else 0
            )

            if quality_ratio >= 0.7:  # 70% of pages have sufficient text
                self.logger.info(
                    f"Text quality sufficient ({quality_ratio:.0%} pages). Using Tier 1."
                )
                return "tier_1_text"
            else:
                self.logger.info(
                    f"Text quality insufficient ({quality_ratio:.0%} pages). Using Tier 2 OCR."
                )
                return "tier_2_ocr"

        except Exception as e:
            self.logger.warning(f"Tier decision failed: {str(e)}. Defaulting to Tier 2.")
            return "tier_2_ocr"

    def run_tier1(self, pdf_path: str, source_type: str) -> List[ExtractionResult]:
        """
        Run Tier 1: Native text extraction with LLM structuring.

        Args:
            pdf_path: Path to PDF file.
            source_type: Document type for prompt selection.

        Returns:
            List of extraction results from text-based extraction.
        """
        self.logger.info("Running Tier 1 text extraction")
        results = []

        try:
            # Extract text and tables
            text_result = self.text_extractor.extract_text(pdf_path)
            tables = self.text_extractor.extract_tables(pdf_path)

            if not text_result.get("success", False):
                self.logger.error("Tier 1 text extraction failed")
                return results

            # Detect financial pages
            financial_pages = self.text_extractor.detect_financial_pages(
                pdf_path
            )

            # For each financial page, create extraction result
            for page_data in text_result.get("pages", []):
                page_num = page_data.get("page_num")

                if page_num not in financial_pages:
                    continue

                text = page_data.get("text", "")
                tables_found = page_data.get("tables_found", 0)

                # Simple heuristic: if text is quality and financial terms present
                if self.text_extractor.is_text_quality_sufficient(text):
                    result = ExtractionResult(
                        page_num=page_num,
                        tier="TIER_1_TEXT",
                        extracted_data={
                            "text_length": len(text),
                            "tables_detected": tables_found,
                            "source_type": source_type,
                        },
                        source_quote=text[:500],  # First 500 chars as quote
                        confidence=0.6,  # Medium confidence for text-only
                        notes="Tier 1 text extraction; requires LLM structuring",
                        source_document_url=getattr(self, '_current_doc_url', None),
                        source_document_id=getattr(self, '_current_doc_id', None),
                    )
                    results.append(result)
                    self.logger.debug(f"Tier 1 result for page {page_num}")

            self.logger.info(f"Tier 1 produced {len(results)} results")

        except Exception as e:
            self.logger.error(f"Tier 1 extraction failed: {str(e)}")

        return results

    def run_tier2(self, pdf_path: str, source_type: str) -> List[ExtractionResult]:
        """
        Run Tier 2: OCR-based extraction with LLM post-processing.

        Args:
            pdf_path: Path to PDF file.
            source_type: Document type for prompt selection.

        Returns:
            List of extraction results from OCR.
        """
        self.logger.info("Running Tier 2 OCR extraction")
        results = []

        try:
            # Run OCR on all pages
            ocr_result = self.ocr_extractor.extract_text(pdf_path)

            if not ocr_result.get("success", False):
                self.logger.error("Tier 2 OCR extraction failed")
                return results

            # Extract tables from OCR
            tables = self.ocr_extractor.extract_table_regions(
                None  # Would need preprocessed images
            )

            # For each page with financial content, create result
            for page_data in ocr_result.get("pages", []):
                page_num = page_data.get("page_num")
                text = page_data.get("text", "")
                confidence = page_data.get("confidence", 0.5) / 100

                if self.text_extractor.is_text_quality_sufficient(text):
                    result = ExtractionResult(
                        page_num=page_num,
                        tier="TIER_2_OCR",
                        extracted_data={
                            "ocr_confidence": confidence,
                            "text_length": len(text),
                            "source_type": source_type,
                        },
                        source_quote=text[:500],
                        confidence=confidence * 0.8,  # Slightly lower confidence
                        notes=f"OCR extraction with {confidence:.0%} confidence",
                        source_document_url=getattr(self, '_current_doc_url', None),
                        source_document_id=getattr(self, '_current_doc_id', None),
                    )
                    results.append(result)
                    self.logger.debug(f"Tier 2 result for page {page_num}")

            self.logger.info(f"Tier 2 produced {len(results)} results")

        except Exception as e:
            self.logger.error(f"Tier 2 OCR extraction failed: {str(e)}")

        return results

    def run_tier3(
        self,
        pdf_path: str,
        pages: Optional[List[int]],
        source_type: str,
    ) -> List[ExtractionResult]:
        """
        Run Tier 3: Claude Vision API extraction.

        Args:
            pdf_path: Path to PDF file.
            pages: Specific pages to extract (e.g., financial pages). If None, uses all.
            source_type: Document type for prompt selection.

        Returns:
            List of extraction results from Vision API.
        """
        self.logger.info(
            f"Running Tier 3 Vision extraction (pages: {pages or 'all'})"
        )
        results = []

        try:
            # Extract using Vision API
            vision_data = self.vision_extractor.extract_financial_data(
                pdf_path, pages=pages, source_type=source_type
            )

            # Convert Vision results to ExtractionResult objects
            for item in vision_data:
                page_num = item.get("page")
                extracted = item.get("extracted_data", [])
                confidence = item.get("confidence", 0.5)

                # Extract source quotes from Vision structured data
                vision_quotes = []
                for item_data in extracted:
                    if isinstance(item_data, dict):
                        for key, val in item_data.items():
                            if isinstance(val, dict) and "source_quote" in val:
                                quote = val["source_quote"]
                                if quote:
                                    vision_quotes.append(quote)

                result = ExtractionResult(
                    page_num=page_num,
                    tier="TIER_3_VISION",
                    extracted_data={
                        "items_extracted": len(extracted),
                        "structured_data": extracted,
                        "source_type": source_type,
                    },
                    source_quote="; ".join(vision_quotes[:3]) if vision_quotes else None,
                    confidence=confidence,
                    notes="Vision API extraction; structured JSON output",
                    source_document_url=getattr(self, '_current_doc_url', None),
                    source_document_id=getattr(self, '_current_doc_id', None),
                )
                results.append(result)
                self.logger.debug(f"Tier 3 result for page {page_num}")

            self.logger.info(f"Tier 3 produced {len(results)} results")

        except Exception as e:
            self.logger.error(f"Tier 3 Vision extraction failed: {str(e)}")

        return results

    def cross_reference(
        self,
        tier1_or_2_results: List[ExtractionResult],
        tier3_results: List[ExtractionResult],
    ) -> List[ExtractionResult]:
        """
        Cross-reference Tier 1/2 results with Tier 3 Vision results.

        Reconciles outputs, flags discrepancies, and prioritizes Vision results
        for structured data (especially tables).

        Args:
            tier1_or_2_results: Results from Tier 1 or 2.
            tier3_results: Results from Tier 3 Vision.

        Returns:
            Merged and reconciled results, prioritizing Vision for structured data.
        """
        self.logger.info(
            f"Cross-referencing {len(tier1_or_2_results)} text results "
            f"with {len(tier3_results)} Vision results"
        )

        # For pages with both text and Vision results, merge them
        merged = {}

        for result in tier1_or_2_results:
            page = result.page_num
            merged[page] = result

        for result in tier3_results:
            page = result.page_num
            if page in merged:
                # Both exist: note discrepancy
                self.logger.warning(
                    f"Page {page}: both text and Vision results. "
                    "Prioritizing Vision for structured data."
                )
                # Enhance with Vision data
                merged[page].extracted_data["vision_structured"] = (
                    result.extracted_data
                )
                merged[page].notes += (
                    f" [Vision cross-ref on page {page}]"
                )
            else:
                merged[page] = result

        return list(merged.values())

    def _results_quality_insufficient(
        self, results: List[ExtractionResult]
    ) -> bool:
        """
        Check if extraction results are of insufficient quality.

        Args:
            results: List of extraction results.

        Returns:
            True if average confidence is low or few results extracted.
        """
        if not results:
            return True

        avg_confidence = sum(r.confidence for r in results) / len(results)
        return avg_confidence < 0.5
