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

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        # Force HTTP/1.1 — AER site has intermittent HTTP/2 protocol issues
        import urllib3
        self.session.headers.update({
            "Connection": "keep-alive",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        # Disable HTTP/2 by ensuring urllib3 uses HTTP/1.1 only
        adapter = HTTPAdapter(
            max_retries=Retry(total=3, backoff_factor=2.0, status_forcelist=[429, 500, 502, 503, 504]),
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

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
        seen_urls = set()

        relevance_keywords = [
            "rate of return", "wacc", "cost of capital",
            "cost of equity", "cost of debt",
            "determination", "instrument",
            "allowed return", "equity beta",
            "debt risk premium", "market risk premium",
        ]

        # Try multiple URL patterns (AER site has been restructured)
        urls_to_try = [
            f"{self.base_url}/industry/networks/rate-of-return",
            f"{self.base_url}/industry/registers/resources/rate-of-return",
            f"{self.base_url}/industry/registers/resources/reviews",
            f"{self.base_url}/industry/networks",
        ]

        for url in urls_to_try:
            try:
                # Use short timeout — AER site has HTTP/2 outage issues
                resp = self.session.get(url, timeout=10)
                resp.raise_for_status()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")

                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    text = link.get_text(strip=True)

                    if not any(kw in text.lower() for kw in relevance_keywords):
                        continue

                    full_url = urljoin(self.base_url, href) if not href.startswith("http") else href
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    decisions.append({
                        "decision_id": f"aer_{text[:50].replace(' ', '_')}",
                        "title": text,
                        "url": full_url,
                        "subject": "Rate of Return Determination",
                    })

                if decisions:
                    break  # Found results, stop trying
            except Exception:
                continue

        # Fallback: AER site search (also with short timeout)
        if not decisions:
            decisions = self._search_decisions()

        # Always include known documents to ensure minimum coverage
        known = self._known_documents()
        for d in known:
            if d["url"] not in seen_urls:
                seen_urls.add(d["url"])
                decisions.append(d)

        logger.debug(f"  Found {len(decisions)} determinations")
        return decisions

    def _search_decisions(self) -> list[dict]:
        """Fallback: use AER site search with short timeout."""
        decisions = []
        search_terms = [
            "rate of return instrument",
            "rate of return",
        ]

        for term in search_terms:
            try:
                search_url = f"{self.base_url}/search?query={term.replace(' ', '+')}"
                resp = self.session.get(search_url, timeout=10)
                resp.raise_for_status()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    text = link.get_text(strip=True)
                    if any(kw in text.lower() for kw in ["rate of return", "cost of", "wacc", "instrument"]):
                        full_url = urljoin(self.base_url, href) if not href.startswith("http") else href
                        if not any(d["url"] == full_url for d in decisions):
                            decisions.append({
                                "decision_id": f"aer_{text[:50].replace(' ', '_')}",
                                "title": text,
                                "url": full_url,
                                "subject": "Rate of Return Determination",
                            })
            except Exception:
                continue

        return decisions

    def _known_documents(self) -> list[dict]:
        """Return known AER rate of return document URLs."""
        return [
            {
                "decision_id": "aer_ror_instrument_2022",
                "title": "Rate of Return Instrument 2022 - Final Decision",
                "url": f"{self.base_url}/industry/networks/rate-of-return",
                "subject": "Rate of Return Instrument",
            },
            {
                "decision_id": "aer_ror_instrument_2018_pdf",
                "title": "Rate of Return Instrument - December 2018",
                "url": f"{self.base_url}/system/files/2020-06/Rate%20of%20Return%20Instrument%20-%20December%202018.pdf",
                "subject": "Rate of Return Instrument",
            },
            {
                "decision_id": "aer_ror_instrument_2022_page",
                "title": "Rate of Return Instrument 2022 - Overview",
                "url": f"{self.base_url}/industry/networks/rate-of-return/rate-of-return-instrument-2022",
                "subject": "Rate of Return Final Decision",
            },
            {
                "decision_id": "aer_ror_explanatory_statement_2022",
                "title": "Rate of Return Instrument - Explanatory Statement 2022",
                "url": f"{self.base_url}/system/files/2023-02/AER%20-%20Rate%20of%20return%20instrument%20-%20Explanatory%20Statement%20-%20February%202023.pdf",
                "subject": "Rate of Return Explanatory Statement",
            },
            {
                "decision_id": "aer_ror_overview_paper_2022",
                "title": "Rate of Return - Overview Paper 2022",
                "url": f"{self.base_url}/system/files/2022-06/AER%20-%20Rate%20of%20return%20-%20Overview%20paper%20-%20June%202022.pdf",
                "subject": "Rate of Return Overview",
            },
        ]

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
            if not hasattr(self, "_decisions_cache"):
                self._decisions_cache = self.list_decisions()

            decision = next(
                (d for d in self._decisions_cache if d.get("decision_id") == decision_id),
                None,
            )

            if not decision:
                logger.warning(f"Determination not found: {decision_id}")
                return None

            decision_url = decision.get("url")

            # Direct PDF download for known PDF URLs
            if decision_url.endswith(".pdf"):
                filename = f"aer_{decision_id}_{int(time.time())}.pdf"
                try:
                    filepath = self.download_pdf(decision_url, filename)
                    logger.info(f"  Downloaded: {filepath}")
                    return str(filepath)
                except Exception as e:
                    logger.warning(f"  Direct PDF failed: {e}")
                    return None

            try:
                resp = self.session.get(decision_url, timeout=10)
                resp.raise_for_status()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
            except Exception as e:
                logger.warning(f"Could not fetch decision page (timeout/error): {e}")
                return None

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
