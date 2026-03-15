"""
FERC (Federal Energy Regulatory Commission) scraper for the US.

Target: ferc.gov + elibrary.ferc.gov

FERC is the US federal regulator for interstate electricity and natural gas.
It publishes:
- Order 888 and 889 requirements
- Natural Gas Act rate cases
- Hydroelectric project licensing documents
- Pipeline rate case orders

Documents containing WACC/cost of capital info:
- Certificate applications with capital structure
- Rate case orders (cost of equity determinations)
- Tariff filings with return on equity
- Project orders with financial analyses

Medium-value source; WACC information varies by document type
and is less standardized than other regulators.
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


class FERCScraper(RegulatoryScraperBase):
    """
    Scraper for US Federal Energy Regulatory Commission (FERC).

    Searches for rate case orders and project approvals containing
    cost of equity and capital structure information.

    Attributes:
        base_url: https://www.ferc.gov
        elibrary_url: https://elibrary.ferc.gov
        language: English
    """

    def __init__(self, output_dir: str = "data/raw/ferc") -> None:
        """Initialize FERC scraper."""
        super().__init__(
            name="FERC",
            base_url="https://www.ferc.gov",
            output_dir=output_dir,
            language="English",
            regulator_name="Federal Energy Regulatory Commission",
            country_code="USA",
            rate_limit=1.0,
        )
        self.elibrary_url = "https://elibrary.ferc.gov"

    def scrape(self) -> list[RawDocument]:
        """
        Scrape FERC rate case orders and project decisions.

        Returns:
            List of RawDocument objects for downloaded documents
        """
        documents = []

        try:
            logger.info("Starting FERC scraping...")

            # List rate cases and project orders
            decisions = self.list_decisions()
            logger.info(f"Found {len(decisions)} rate cases and project orders")

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
                            source_institution="FERC",
                            document_title=decision.get("title"),
                        )
                        documents.append(doc)
                        logger.info(f"  Registered: {doc.document_id}")

                except Exception as e:
                    logger.error(f"  Error processing decision: {e}")
                    continue

        except Exception as e:
            logger.error(f"FERC scraping failed: {e}")

        logger.info(f"FERC scraping complete. Downloaded {len(documents)} documents.")
        return documents

    def list_decisions(self) -> list[dict]:
        """
        List FERC rate cases and project orders.

        Uses FERC's eLibrary search to find relevant documents.

        Returns:
            List of decision metadata
        """
        logger.debug("Listing FERC rate cases and project orders...")

        decisions = []
        seen_accessions = set()

        search_keywords = [
            "cost of equity",
            "return on equity",
            "cost of capital",
            "capital structure",
            "WACC",
            "allowed return",
            "base return on equity",
        ]

        relevance_keywords = [
            "order", "rate case", "cost of equity", "return on equity",
            "cost of capital", "capital structure", "roe",
        ]

        for keyword in search_keywords:
            try:
                # eLibrary uses GET form submission — server-rendered HTML
                search_url = f"{self.elibrary_url}/eLibrary/search"
                params = {
                    "Selectsearch": "general",
                    "textsearch": keyword,
                    "searchDescription": "on",
                    "searchFullText": "on",
                    "Issuance": "on",
                    "dFROM": "01/01/2020",
                    "dTO": "12/31/2026",
                    "submit": "Search",
                }

                # Build URL with params
                param_str = "&".join(f"{k}={v}" for k, v in params.items())
                full_search_url = f"{search_url}?{param_str}"
                soup = self.get_soup(full_search_url)

                # Parse result table rows
                for row in soup.find_all("tr"):
                    cells = row.find_all("td")
                    if len(cells) < 6:
                        continue

                    accession = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    description = cells[5].get_text(strip=True) if len(cells) > 5 else ""
                    class_type = cells[6].get_text(strip=True) if len(cells) > 6 else ""

                    if not accession or accession in seen_accessions:
                        continue

                    # Filter for relevant documents
                    desc_lower = description.lower()
                    if not (
                        any(kw in desc_lower for kw in relevance_keywords)
                        or "Order" in class_type
                    ):
                        continue

                    seen_accessions.add(accession)

                    # Extract file links from the last cell
                    file_links = []
                    files_cell = cells[-1]
                    for link in files_cell.find_all("a", href=True):
                        href = link.get("href", "")
                        if ".pdf" in href or ".html" in href:
                            file_links.append(urljoin(self.elibrary_url, href))

                    decision_id = f"ferc_{accession.split()[0] if accession else keyword[:10]}"
                    decisions.append({
                        "decision_id": decision_id,
                        "title": description[:200],
                        "url": file_links[0] if file_links else search_url,
                        "subject": "Rate Case or Project Order",
                        "accession": accession,
                        "class_type": class_type,
                    })

            except Exception as e:
                logger.warning(f"FERC eLibrary search failed for '{keyword}': {e}")
                continue

        logger.debug(f"  Found {len(decisions)} decisions")
        return decisions

    def download_decision(self, decision_id: str) -> Optional[str]:
        """
        Download a FERC order or decision document.

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

            try:
                soup = self.get_soup(decision_url)
            except Exception as e:
                logger.warning(f"Could not fetch decision page: {e}")
                return None

            # Look for PDF or document link
            pdf_link = None
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True).lower()

                if href.endswith(".pdf"):
                    pdf_link = href
                    break

            if not pdf_link:
                logger.warning(f"No PDF found for: {decision_id}")
                return None

            pdf_url = urljoin(self.base_url, pdf_link)
            filename = f"ferc_{decision_id}_{int(time.time())}.pdf"

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
        Check if document contains cost of capital/ROE information.

        Args:
            text: Extracted document text

        Returns:
            "relevant", "uncertain", or "irrelevant"
        """
        keywords = [
            "return on equity",
            "roe",
            "cost of equity",
            "cost of capital",
            "wacc",
            "weighted average cost of capital",
            "capital structure",
            "debt ratio",
            "equity ratio",
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
