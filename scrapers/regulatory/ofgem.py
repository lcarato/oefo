"""
Ofgem (Office of Gas and Electricity Markets) scraper for the UK.

Target: ofgem.gov.uk

Ofgem is the British electricity and gas regulator. It publishes:
- RIIO (Revenue = Incentives + Innovation + Outputs) price control decisions
- Cost of capital determinations
- Network price controls for transmission and distribution

The RIIO framework includes:
- Detailed WACC calculations
- Cost of equity and cost of debt determinations
- Allowed return on capital calculations
- 8-year regulatory periods with annual updates

Medium-high value source with explicit WACC parameters in price controls.
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


class OfgemScraper(RegulatoryScraperBase):
    """
    Scraper for UK electricity and gas regulator Ofgem.

    Focuses on RIIO price control decisions which include
    detailed WACC and cost of capital parameters.

    Attributes:
        base_url: https://www.ofgem.gov.uk
        language: English
    """

    def __init__(self, output_dir: str = "data/raw/ofgem") -> None:
        """Initialize Ofgem scraper."""
        super().__init__(
            name="Ofgem",
            base_url="https://www.ofgem.gov.uk",
            output_dir=output_dir,
            language="English",
            regulator_name="Ofgem (Office of Gas and Electricity Markets)",
            country_code="GBR",
            rate_limit=1.0,
        )

    def scrape(self) -> list[RawDocument]:
        """
        Scrape Ofgem RIIO price control decisions.

        Returns:
            List of RawDocument objects for downloaded decisions
        """
        documents = []

        try:
            logger.info("Starting Ofgem scraping...")

            # List RIIO price control decisions
            decisions = self.list_decisions()
            logger.info(f"Found {len(decisions)} price control decisions")

            # Download each decision
            for idx, decision in enumerate(decisions, 1):
                logger.info(f"Processing decision {idx}/{len(decisions)}")

                try:
                    decision_id = decision.get("decision_id")
                    decision_url = decision.get("url")

                    doc_path = self.download_decision(decision_id)

                    if doc_path:
                        doc = self.register_document(
                            url=decision_url,
                            filepath=doc_path,
                            source_type=SourceType.REGULATORY_FILING,
                            source_institution="Ofgem",
                            document_title=decision.get("title"),
                        )
                        documents.append(doc)
                        logger.info(f"  Registered: {doc.document_id}")

                except Exception as e:
                    logger.error(f"  Error processing decision: {e}")
                    continue

        except Exception as e:
            logger.error(f"Ofgem scraping failed: {e}")

        logger.info(f"Ofgem scraping complete. Downloaded {len(documents)} documents.")
        return documents

    def list_decisions(self) -> list[dict]:
        """
        List Ofgem RIIO price control decisions.

        Returns:
            List of decision metadata
        """
        logger.debug("Listing Ofgem RIIO price control decisions...")

        decisions = []

        try:
            # Ofgem price control pages
            price_control_url = f"{self.base_url}/networks-pipelines/financial-regulation-electricity-and-gas-networks/financial-incentives-network-innovation"

            soup = self.get_soup(price_control_url)

            # Look for RIIO decision links
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True)

                # Filter for RIIO/price control decisions
                if any(
                    keyword in text.lower()
                    for keyword in [
                        "riio",
                        "price control",
                        "final decision",
                        "determination",
                        "cost of capital",
                        "wacc",
                    ]
                ):
                    if not href.startswith("http"):
                        full_url = urljoin(self.base_url, href)
                    else:
                        full_url = href

                    decision_id = f"ofgem_{text.replace(' ', '_')}"

                    decisions.append(
                        {
                            "decision_id": decision_id,
                            "title": text,
                            "url": full_url,
                            "subject": "RIIO Price Control Decision",
                        }
                    )

            logger.debug(f"  Found {len(decisions)} decisions")
            return decisions

        except Exception as e:
            logger.error(f"Failed to list decisions: {e}")
            return []

    def download_decision(self, decision_id: str) -> Optional[str]:
        """
        Download an Ofgem price control decision document.

        Args:
            decision_id: Unique identifier

        Returns:
            Path to downloaded document
        """
        logger.debug(f"Downloading decision: {decision_id}")

        try:
            decisions = self.list_decisions()
            decision = next(
                (d for d in decisions if d.get("decision_id") == decision_id),
                None,
            )

            if not decision:
                logger.warning(f"Decision not found: {decision_id}")
                return None

            decision_url = decision.get("url")
            soup = self.get_soup(decision_url)

            # Look for main decision PDF
            pdf_link = None
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True).lower()

                # Prefer "Final Decision" or "Decision" PDFs
                if "decision" in text and href.endswith(".pdf"):
                    pdf_link = href
                    break

            # Fallback to any PDF
            if not pdf_link:
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    if href.endswith(".pdf"):
                        pdf_link = href
                        break

            if not pdf_link:
                logger.warning(f"No PDF found for: {decision_id}")
                return None

            pdf_url = urljoin(self.base_url, pdf_link)
            filename = f"ofgem_{decision_id}_{int(time.time())}.pdf"

            try:
                filepath = self.download_pdf(pdf_url, filename)
                logger.info(f"  Downloaded: {filepath}")
                return str(filepath)

            except Exception as e:
                logger.error(f"  Failed to download: {e}")
                return None

        except Exception as e:
            logger.error(f"Error downloading decision: {e}")
            return None

    def classify_document(self, text: str) -> str:
        """
        Check if document contains RIIO/cost of capital information.

        Args:
            text: Extracted document text

        Returns:
            "relevant", "uncertain", or "irrelevant"
        """
        keywords = [
            "riio",
            "cost of capital",
            "wacc",
            "cost of equity",
            "cost of debt",
            "allowed return",
            "capm",
            "beta",
            "price control",
            "financial resilience",
        ]

        text_lower = text.lower()
        matches = sum(1 for keyword in keywords if keyword in text_lower)

        if matches >= 3:
            return "relevant"
        elif matches >= 1:
            return "uncertain"
        else:
            return "irrelevant"
