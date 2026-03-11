"""
Multi-modal PDF Extraction Pipeline for OEFO (Open Energy Finance Observatory)

A three-tier extraction system for financial data from energy project PDFs:

Tier 1 (TIER_1_TEXT): Native text extraction using pdfplumber/PyMuPDF
  - Fast, cost-effective
  - Requires embedded text in PDF
  - Returns page-level text and tables

Tier 2 (TIER_2_OCR): Optical Character Recognition for scanned documents
  - Handles low-quality or scanned PDFs
  - Uses Tesseract OCR with image preprocessing
  - Supports multilingual documents (eng, por, spa, deu, fra, ita)

Tier 3 (TIER_3_VISION): Claude Vision API for authoritative table recognition
  - Specialized in financial table interpretation
  - Returns structured JSON matching data model schema
  - Source-type specific prompts (regulatory, dfi, corporate, bond)

Decision Tree:
1. Attempt Tier 1 text extraction
2. If quality insufficient → try Tier 2 OCR
3. For all tables → apply Tier 3 Vision (authoritative)
4. Cross-reference and reconcile results

Usage Example:
    from extraction import ExtractionPipeline

    pipeline = ExtractionPipeline()
    results = pipeline.extract(
        pdf_path="path/to/document.pdf",
        source_type="regulatory",
        source_institution="ICBC"
    )

    for result in results:
        print(f"Page {result.page_num}: {result.confidence:.0%}")
        print(f"Tier: {result.tier}")
        print(f"Data: {result.extracted_data}")
"""

from .pipeline import ExtractionPipeline, ExtractionResult
from .text import TextExtractor
from .ocr import OCRExtractor
from .vision import VisionExtractor
from .prompts import get_prompt

__all__ = [
    "ExtractionPipeline",
    "ExtractionResult",
    "TextExtractor",
    "OCRExtractor",
    "VisionExtractor",
    "get_prompt",
]

__version__ = "1.0.0"
