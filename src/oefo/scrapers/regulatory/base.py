"""
Base class for regulatory agency scrapers.

Regulatory agencies publish rate-setting decisions that contain
WACC, cost of capital, and cost of equity parameters.

Each regulator is jurisdiction-specific with unique document formats
and publication practices. The base class provides common structure
while allowing subclasses to implement agency-specific logic.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from ..base import BaseScraper

logger = logging.getLogger(__name__)


class RegulatoryScraperBase(BaseScraper, ABC):
    """
    Abstract base class for regulatory agency scrapers.

    Regulatory scrapers focus on extracting rate-of-return and WACC
    parameters from agency decisions. These parameters are critical
    for understanding energy utility financing costs.

    Attributes:
        language: Language of documents (e.g., "Portuguese", "English")
        regulator_name: Full name of the regulatory agency
        country_code: ISO 3166-1 alpha-3 country code (e.g., "BRA", "AUS")
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        output_dir: str,
        language: str,
        regulator_name: str,
        country_code: str,
        rate_limit: float = 1.0,
    ) -> None:
        """
        Initialize regulatory scraper.

        Args:
            name: Short name of scraper (e.g., "ANEEL")
            base_url: Base URL of regulatory agency website
            output_dir: Directory for downloaded documents
            language: Language of documents (e.g., "Portuguese")
            regulator_name: Full regulatory agency name
            country_code: ISO 3166-1 alpha-3 country code
            rate_limit: Seconds between requests (default: 1.0)
        """
        super().__init__(
            name=name,
            base_url=base_url,
            output_dir=output_dir,
            rate_limit=rate_limit,
        )
        self.language = language
        self.regulator_name = regulator_name
        self.country_code = country_code

        logger.info(
            f"Initialized {self.regulator_name} ({self.country_code}) scraper"
        )

    @abstractmethod
    def list_decisions(self) -> list[dict]:
        """
        List regulatory decisions (rate cases, tariff reviews, etc.).

        Returns:
            List of decision metadata dicts with keys:
            - decision_id: Unique identifier
            - date: Decision date
            - title: Decision title
            - url: URL to decision document
            - subject: Main subject matter
        """
        pass

    @abstractmethod
    def download_decision(self, decision_id: str) -> Optional[str]:
        """
        Download a regulatory decision document.

        Args:
            decision_id: Unique identifier of the decision

        Returns:
            Path to downloaded document, or None if failed
        """
        pass

    @abstractmethod
    def classify_document(self, text: str) -> str:
        """
        Classify whether document contains relevant WACC/rate-of-return info.

        Args:
            text: Extracted text from document

        Returns:
            Classification: "relevant", "irrelevant", or "uncertain"
        """
        pass
