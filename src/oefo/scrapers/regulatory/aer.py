"""
AER (Australian Energy Regulator) scraper for Australia.

Target: aer.gov.au

AER is the national energy regulator for Australia. It publishes:
- Rate of return determinations
- Allowed rate of return instruments (binding regulatory decisions)
- Excel models with detailed CAPM calculations
- Network service provider determinations

The AER framework is particularly valuable as it:
- Publishes binding rate of return decisions every 5 years
- Includes detailed CAPM decomposition
- Provides Excel models with all calculations
- Contains explicit cost of equity and cost of debt parameters

High-value source with detailed financial models.
"""

import logging
import re
import time
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ...models import RawDocument, SourceType
from .base import RegulatoryScraperBase

logger = logging.getLogger(__name__)


class AERScraper(RegulatoryScraperBase):
    """
    Scraper for Australian Energy Regulator (AER).

    Focuses on rate of return determinations with detailed CAPM models
    and cost of capital calculations for regulated network services.

    Attributes:
        base_url: https://www.aer.gov.au
        language: English
    """

    def __init__(self, output_dir: str = "data/raw/aer") -> None:
        """Initialize AER scraper."""
        super().__init__(
            name="AER",
            base_url="https://www.aer.gov.au",
            output_dir=output_dir,
            language="English",
            regulator_name="Australian Energy Regulator",
            country_code="AUS",
            rate_limit=1.0,
        )

    def scrape(self) -> list[RawDocument]:
        """
        Scrape AER rate of return determinations.

        Returns:
            List of RawDocument objects for downloaded decisions
        """
        documents = []

        try:
            logger.info("Starting AER scraping...")

            # List rate of return determinations
            decisions = self.list_decisions()
            logger.info(f"Found {len(decisions)} rate of return determinations")

            # Download each determination
            for idx, decision in enumerate(decisions, 1):
                logger.info(f"Processing determination {idx}/{len(decisions)}")

                try:
                    decision_id = decision.get("decision_id")
                    decision_url = decision.get("url")

                    doc_path = self.download_decision(decision_id)

                    if doc_path:
                        doc = self.register_document(
                            url=decision_url,
                            filepath=doc_path,
                            source_type=SourceType.REGULATORY_FILING,
                            source_institution="AER",
                            document_title=decision.get("title"),
                        )
                        documents.append(doc)
                        logger.info(f"  Registered: {doc.document_id}")

                except Exception as e:
                    logger.error(f"  Error processing determination: {e}")
                    continue

        except Exception as e:
            logger.error(f"AER scraping failed: {e}")

        logger.info(f"AER scraping complete. Downloaded {len(documents)} documents.")
        return documents

    def list_decisions(self) -> list[dict]:
        """
        List AER rate of return determinations.

        Returns:
            List of decision metadata
        """
        logger.debug("Listing AER rate of return determinations...")

        decisions = []

        try:
            # AER rate of return page
            url = (
                f"{self.base_url}/networks-pipelines/guidelines-schemes-models-reviews/"
                "rate-of-return"
            )

            soup = self.get_soup(url)

            # Look for determination links
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True)

                # Filter for rate of return determinations
                if any(
                    keyword in text.lower()
                    for keyword in [
                        "rate of return",
                        "wacc",
                        "cost of capital",
                        "determination",
                        "instrument",
                    ]
                ):
                    if not href.startswith("http"):
                        full_url = urljoin(self.base_url, href)
                    else:
                        full_url = href

                    decision_id = f"aer_{text.replace(' ', '_')}"

                    decisions.append(
                        {
                            "decision_id": decision_id,
                            "title": text,
                            "url": full_url,
                            "subject": "Rate of Return Determination",
                        }
                    )

            logger.debug(f"  Found {len(decisions)} determinations")
            return decisions

        except Exception as e:
            logger.error(f"Failed to list decisions: {e}")
            return []

    def download_decision(self, decision_id: str) -> Optional[str]:
        """
        Download a rate of return determination document.

        AER typically publishes both PDFs and Excel models.
        This method attempts to download both if available.

        Args:
            decision_id: Unique identifier

        Returns:
            Path to downloaded document
        """
        logger.debug(f"Downloading determination: {decision_id}")

        try:
            decisions = self.list_decisions()
            decision = next(
                (d for d in decisions if d.get("decision_id") == decision_id),
                None,
            )

            if not decision:
                logger.warning(f"Determination not found: {decision_id}")
                return None

            decision_url = decision.get("url")
            soup = self.get_soup(decision_url)

            # Look for main determination document (PDF)
            pdf_link = None
            excel_link = None

            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True).lower()

                if href.endswith(".pdf") and not excel_link:
                    pdf_link = href
                elif href.endswith((".xlsx", ".xls")):
                    excel_link = href

            # Download PDF first
            if pdf_link:
                pdf_url = urljoin(self.base_url, pdf_link)
                filename = f"aer_{decision_id}_{int(time.time())}.pdf"

                try:
                    filepath = self.download_pdf(pdf_url, filename)
                    logger.info(f"  Downloaded: {filepath}")
                    return str(filepath)

                except Exception as e:
                    logger.warning(f"  PDF download failed: {e}")

            # Try Excel model
            if excel_link:
                excel_url = urljoin(self.base_url, excel_link)
                filename = f"aer_{decision_id}_{int(time.time())}.xlsx"

                try:
                    filepath = self.download_file(excel_url, filename)
                    logger.info(f"  Downloaded Excel model: {filepath}")
                    return str(filepath)

                except Exception as e:
                    logger.warning(f"  Excel download failed: {e}")

            logger.warning(f"No documents found for: {decision_id}")
            return None

        except Exception as e:
            logger.error(f"Error downloading determination: {e}")
            return None

    def classify_document(self, text: str) -> str:
        """
        Check if document contains rate of return/WACC information.

        Args:
            text: Extracted document text

        Returns:
            "relevant", "uncertain", or "irrelevant"
        """
        keywords = [
            "rate of return",
            "wacc",
            "cost of capital",
            "cost of equity",
            "cost of debt",
            "capm",
            "beta",
            "risk premium",
            "allowed return",
        ]

        text_lower = text.lower()
        matches = sum(1 for keyword in keywords if keyword in text_lower)

        if matches >= 3:
            return "relevant"
        elif matches >= 1:
            return "uncertain"
        else:
            return "irrelevant"
