"""
Tier 2: OCR-Based Text Extraction from PDFs

This module provides optical character recognition (OCR) capabilities for
extracting text from scanned PDFs or documents with low-quality embedded text.

Key Features:
- Multi-language OCR support (eng, por, spa, deu, fra, ita)
- Image preprocessing (grayscale, adaptive threshold, deskew)
- Table region detection via contour analysis
- Cell-by-cell OCR for financial tables
- Configurable Tesseract parameters for table content extraction
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
import pandas as pd

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

logger = logging.getLogger(__name__)

# Default Tesseract configuration for table OCR
TESSERACT_TABLE_CONFIG = "--oem 1 --psm 6"

# Supported OCR languages
SUPPORTED_LANGUAGES = {"eng", "por", "spa", "deu", "fra", "ita"}


class OCRExtractor:
    """
    Extract text from PDFs using OCR (Optical Character Recognition).

    Provides methods for:
    - Converting PDF pages to images
    - Image preprocessing (contrast enhancement, deskew, etc.)
    - Table region detection
    - Cell-by-cell OCR with structural preservation
    """

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        """
        Initialize OCRExtractor.

        Args:
            logger_instance: Optional logger for detailed processing logs.

        Raises:
            ImportError: If required dependencies are not installed.
        """
        self.logger = logger_instance or logger
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Verify that required OCR libraries are available."""
        if convert_from_path is None:
            self.logger.warning(
                "pdf2image not installed. Install with: pip install pdf2image"
            )
        if pytesseract is None:
            self.logger.warning(
                "pytesseract not installed. Install with: pip install pytesseract. "
                "Also requires Tesseract-OCR system library."
            )

    def extract_text(
        self,
        pdf_path: str,
        languages: Optional[List[str]] = None,
        dpi: int = 300,
    ) -> dict:
        """
        Extract text from a PDF using OCR.

        Converts each page to an image, preprocesses it, and runs Tesseract OCR.

        Args:
            pdf_path: Path to the PDF file.
            languages: List of language codes for OCR. Default: ['eng'].
                Supported: 'eng', 'por', 'spa', 'deu', 'fra', 'ita'.
            dpi: DPI for rendering PDF to images. Default: 300.

        Returns:
            Dictionary containing:
                - pages: List of dicts with keys:
                    - page_num: 0-indexed page number
                    - text: OCR-extracted text
                    - confidence: Average confidence of OCR (0-100)
                - metadata: Document metadata
                - total_pages: Total number of pages
                - success: Boolean indicating successful extraction
                - error: Error message if extraction failed

        Raises:
            FileNotFoundError: If PDF file does not exist.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if convert_from_path is None or pytesseract is None:
            return {
                "pages": [],
                "metadata": {},
                "total_pages": 0,
                "success": False,
                "error": "pdf2image and/or pytesseract not installed",
            }

        if languages is None:
            languages = ["eng"]

        # Validate language codes
        for lang in languages:
            if lang not in SUPPORTED_LANGUAGES:
                self.logger.warning(
                    f"Language '{lang}' may not be supported. "
                    f"Supported: {SUPPORTED_LANGUAGES}"
                )

        try:
            # Convert PDF pages to images
            images = convert_from_path(str(pdf_path), dpi=dpi)
            self.logger.info(f"Converted PDF to {len(images)} images at {dpi} DPI")

            pages_data = []
            lang_str = "+".join(languages)

            for page_idx, image in enumerate(images):
                # Preprocess image
                processed = self.preprocess_image(np.array(image))

                # Run OCR
                try:
                    text = pytesseract.image_to_string(
                        processed, lang=lang_str
                    )
                    # Get confidence data
                    data = pytesseract.image_to_data(
                        processed, lang=lang_str, output_type="dict"
                    )
                    confidences = [
                        int(conf)
                        for conf in data["conf"]
                        if int(conf) > 0
                    ]
                    avg_confidence = (
                        sum(confidences) / len(confidences)
                        if confidences
                        else 0
                    )
                except Exception as ocr_error:
                    self.logger.error(
                        f"OCR failed for page {page_idx}: {str(ocr_error)}"
                    )
                    text = ""
                    avg_confidence = 0

                pages_data.append(
                    {
                        "page_num": page_idx,
                        "text": text,
                        "confidence": avg_confidence,
                    }
                )

            self.logger.info(f"OCR extraction complete for {len(pages_data)} pages")

            return {
                "pages": pages_data,
                "metadata": {},
                "total_pages": len(pages_data),
                "success": True,
                "error": None,
            }

        except Exception as e:
            self.logger.error(f"OCR extraction failed: {str(e)}")
            return {
                "pages": [],
                "metadata": {},
                "total_pages": 0,
                "success": False,
                "error": str(e),
            }

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for improved OCR accuracy.

        Applies grayscale conversion, adaptive thresholding, and deskewing.

        Args:
            image: Input image as numpy array (RGB or BGR).

        Returns:
            Preprocessed image as numpy array (grayscale).
        """
        if image is None or image.size == 0:
            self.logger.warning("Empty image provided to preprocess")
            return image

        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image

            # Apply adaptive threshold
            processed = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2,
            )

            # Deskew using OpenCV (simple rotation correction)
            processed = self._deskew(processed)

            self.logger.debug("Image preprocessing complete")
            return processed

        except Exception as e:
            self.logger.error(f"Image preprocessing failed: {str(e)}")
            return image

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """
        Deskew an image by detecting and correcting rotation.

        Uses contour detection to estimate text orientation.

        Args:
            image: Grayscale image as numpy array.

        Returns:
            Deskewed image.
        """
        try:
            # Detect contours
            contours, _ = cv2.findContours(
                image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if not contours:
                return image

            # Find minimum rotated rectangle
            all_points = np.vstack(contours)
            rect = cv2.minAreaRect(all_points)
            angle = rect[2]

            # Limit rotation to [-45, 45]
            if angle < -45:
                angle = angle + 90

            if abs(angle) > 45:
                return image

            # Apply rotation
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            deskewed = cv2.warpAffine(
                image, matrix, (w, h), borderMode=cv2.BORDER_REPLICATE
            )

            self.logger.debug(f"Image deskewed by {angle:.1f} degrees")
            return deskewed

        except Exception as e:
            self.logger.warning(f"Deskew operation failed: {str(e)}")
            return image

    def extract_table_regions(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect table regions in an image using contour analysis.

        Returns bounding boxes (x, y, width, height) for detected tables.

        Args:
            image: Grayscale preprocessed image as numpy array.

        Returns:
            List of bounding boxes as (x, y, width, height) tuples.
        """
        if image is None or image.size == 0:
            self.logger.warning("Empty image provided to table region detection")
            return []

        try:
            # Apply morphological operations to enhance table structure
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            morphed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
            morphed = cv2.morphologyEx(morphed, cv2.MORPH_OPEN, kernel)

            # Detect contours
            contours, _ = cv2.findContours(
                morphed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
            )

            table_regions = []

            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)

                # Filter by size to avoid noise (tables should be reasonably large)
                min_table_width = image.shape[1] // 5  # At least 20% of image width
                min_table_height = image.shape[0] // 10  # At least 10% of image height

                if w >= min_table_width and h >= min_table_height:
                    table_regions.append((x, y, w, h))

            # Sort by area (largest first)
            table_regions.sort(key=lambda bbox: bbox[2] * bbox[3], reverse=True)

            self.logger.debug(f"Detected {len(table_regions)} table regions")
            return table_regions

        except Exception as e:
            self.logger.error(f"Table region detection failed: {str(e)}")
            return []

    def ocr_table(
        self,
        image: np.ndarray,
        bbox: Tuple[int, int, int, int],
        languages: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Extract text from a table region using cell-by-cell OCR.

        Attempts to detect table structure and extract cell contents.

        Args:
            image: Grayscale preprocessed image as numpy array.
            bbox: Bounding box as (x, y, width, height).
            languages: List of language codes. Default: ['eng'].

        Returns:
            DataFrame representing the table. Empty DataFrame if extraction fails.
        """
        if pytesseract is None:
            self.logger.error("pytesseract not installed")
            return pd.DataFrame()

        if languages is None:
            languages = ["eng"]

        try:
            x, y, w, h = bbox
            # Extract table region
            table_region = image[y : y + h, x : x + w]

            lang_str = "+".join(languages)

            # Use table-specific Tesseract config
            text = pytesseract.image_to_string(
                table_region, lang=lang_str, config=TESSERACT_TABLE_CONFIG
            )

            # Simple parsing: split by lines and tabs/spaces
            lines = text.strip().split("\n")
            rows = []

            for line in lines:
                # Split by multiple spaces (heuristic for columns)
                cells = [cell.strip() for cell in line.split() if cell.strip()]
                if cells:
                    rows.append(cells)

            if not rows:
                return pd.DataFrame()

            # Create DataFrame
            # Use first row as header if it looks like one
            if len(rows) > 1:
                headers = rows[0]
                df = pd.DataFrame(rows[1:], columns=headers)
            else:
                df = pd.DataFrame(rows)

            self.logger.debug(
                f"Extracted table: {df.shape[0]} rows, {df.shape[1]} columns"
            )
            return df

        except Exception as e:
            self.logger.error(f"Table OCR failed: {str(e)}")
            return pd.DataFrame()
