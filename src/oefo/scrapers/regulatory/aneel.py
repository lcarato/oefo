"""
ANEEL (Agência Nacional de Energia Elétrica) scraper for Brazil.

Target: aneel.gov.br

ANEEL is Brazil's electricity regulatory agency. It publishes:
- Tariff review decisions (revisões tarifárias)
- Rate-of-return studies with full CAPM decomposition
- Cost of capital calculations (Custo de Capital - WACC)

Brazilian utilities are required to undergo periodic tariff reviews
(every 4-5 years) where ANEEL calculates and publishes the cost of
capital including:
- Risk-free rate (taxa livre de risco)
- Equity risk premium (prêmio de risco)
- Beta coefficients
- Cost of debt

Very high value source due to explicit WACC decomposition.
"""

import logging
import re
import time
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ...models import DocumentStatus, RawDocument, SourceType
from .base import RegulatoryScraperBase

logger = logging.getLogger(__name__)


class ANEELScraper(RegulatoryScraperBase):
    """
    Scraper for Brazilian electricity regulator ANEEL.

    Focuses on tariff review decisions containing WACC calculations
    with full CAPM decomposition. ANEEL publishes these in Portuguese.

    Attributes:
        base_url: https://www.aneel.gov.br
        language: Portuguese
    """

    def __init__(self, output_dir: str = "data/raw/aneel") -> None:
        """Initialize ANEEL scraper."""
        super().__init__(
            name="ANEEL",
            base_url="https://www.gov.br/aneel/pt-br",
            output_dir=output_dir,
            language="Portuguese",
            regulator_name="Agência Nacional de Energia Elétrica",
            country_code="BRA",
            rate_limit=1.0,
        )

    def scrape(self) -> list[RawDocument]:
        """
        Scrape ANEEL tariff review decisions.

        Returns:
            List of RawDocument objects for downloaded decisions
        """
        documents = []

        try:
            logger.info("Starting ANEEL scraping...")

            # List all tariff review decisions
            decisions = self.list_decisions()
            logger.info(f"Found {len(decisions)} tariff review decisions")

            # Download and process each decision
            for idx, decision in enumerate(decisions, 1):
                logger.info(f"Processing decision {idx}/{len(decisions)}")

                try:
                    decision_id = decision.get("decision_id")
                    decision_url = decision.get("url")

                    # Download decision document
                    doc_path = self.download_decision(decision_id)

                    if doc_path:
                        # Check if document is relevant (contains WACC info)
                        is_relevant = self._check_wacc_content(doc_path)

                        if is_relevant:
                            doc = self.register_document(
                                url=decision_url,
                                filepath=doc_path,
                                source_type=SourceType.REGULATORY_FILING,
                                source_institution="ANEEL",
                                document_title=decision.get("title"),
                            )
                            documents.append(doc)
                            logger.info(f"  Registered document: {doc.document_id}")

                except Exception as e:
                    logger.error(f"  Error processing decision: {e}")
                    continue

        except Exception as e:
            logger.error(f"ANEEL scraping failed: {e}")

        logger.info(f"ANEEL scraping complete. Downloaded {len(documents)} documents.")
        return documents

    def list_decisions(self) -> list[dict]:
        """
        List ANEEL tariff review decisions.

        Searches ANEEL's tariff review page for decisions.

        Returns:
            List of decision metadata dicts
        """
        logger.debug("Listing ANEEL tariff review decisions...")

        decisions = []
        seen_urls = set()

        # Portuguese WACC keywords
        wacc_keywords_pt = [
            "custo de capital", "wacc", "taxa de retorno",
            "custo do capital próprio", "custo da dívida",
            "prêmio de risco", "taxa livre de risco",
            "beta", "estrutura de capital",
            "remuneração regulatória", "remuneração do capital",
            "capm", "submódulo 2.4", "submódulo 12.3",
            "revisão tarifária", "reajuste",
        ]

        # Try multiple pages (site structure may vary)
        urls_to_try = [
            f"{self.base_url}/centrais-de-conteudos/procedimentos-regulatorios/proret",
            f"{self.base_url}/assuntos/tarifas",
            f"{self.base_url}/assuntos/tarifas/regulacao-tarifaria-proret",
        ]

        for page_url in urls_to_try:
            try:
                soup = self.get_soup(page_url)

                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    text = link.get_text(strip=True)

                    if any(kw in text.lower() for kw in wacc_keywords_pt):
                        full_url = urljoin(self.base_url, href) if href.startswith("/") else href

                        if full_url in seen_urls:
                            continue
                        seen_urls.add(full_url)

                        date_match = re.search(r"(\d{4})", text)
                        year = date_match.group(1) if date_match else None

                        decision_id = f"aneel_{href.replace('/', '_')}"

                        decisions.append({
                            "decision_id": decision_id,
                            "title": text,
                            "url": full_url,
                            "year": year,
                            "subject": "Cost of Capital / Tariff Review",
                        })

            except Exception as e:
                logger.debug(f"Failed to fetch {page_url}: {e}")
                continue

        logger.debug(f"  Found {len(decisions)} decisions")
        return decisions

    def download_decision(self, decision_id: str) -> Optional[str]:
        """
        Download a tariff review decision document.

        Note: Called from scrape() which already has the decision list.
        We cache decisions to avoid re-fetching.

        Args:
            decision_id: Unique identifier of the decision

        Returns:
            Path to downloaded document, or None if failed
        """
        logger.debug(f"Downloading decision: {decision_id}")

        try:
            # Use cached decisions if available, otherwise re-fetch
            if not hasattr(self, "_decisions_cache"):
                self._decisions_cache = self.list_decisions()

            decision = next(
                (d for d in self._decisions_cache if d.get("decision_id") == decision_id),
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

            # Try to find PDF link on decision page
            pdf_link = None
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if href.endswith(".pdf") or "pdf" in href.lower():
                    pdf_link = href
                    break

            if not pdf_link:
                logger.warning(f"No PDF found for decision: {decision_id}")
                return None

            pdf_url = urljoin(self.base_url, pdf_link)
            filename = f"aneel_{decision_id}_{int(time.time())}.pdf"

            try:
                filepath = self.download_pdf(pdf_url, filename)
                logger.info(f"  Downloaded: {filepath}")
                return str(filepath)

            except Exception as e:
                logger.error(f"  Failed to download PDF: {e}")
                return None

        except Exception as e:
            logger.error(f"Error downloading decision: {e}")
            return None

    def classify_document(self, text: str) -> str:
        """
        Check if document contains WACC/cost of capital information.

        Args:
            text: Extracted document text

        Returns:
            "relevant" if WACC info found, else "irrelevant"
        """
        # Keywords indicating WACC/cost of capital content
        wacc_keywords = [
            "wacc",
            "custo de capital",
            "taxa de retorno",
            "taxa livre de risco",
            "prêmio de risco",
            "beta",
            "custo do capital próprio",
            "capm",
            "weighted average cost of capital",
        ]

        text_lower = text.lower()
        matches = sum(1 for keyword in wacc_keywords if keyword in text_lower)

        if matches >= 3:
            return "relevant"
        elif matches >= 1:
            return "uncertain"
        else:
            return "irrelevant"

    def _check_wacc_content(self, filepath) -> bool:
        """
        Check if PDF contains WACC information.

        Uses filename/metadata or attempts text extraction if available.

        Args:
            filepath: Path to PDF file

        Returns:
            True if likely to contain WACC info
        """
        try:
            # For now, use simple heuristics based on filename
            filename = str(filepath).lower()

            if any(
                keyword in filename
                for keyword in [
                    "capital",
                    "wacc",
                    "tarif",
                    "revisão",
                    "reajuste",
                ]
            ):
                return True

            # In production, could use PDF text extraction here
            return True  # Assume relevant if downloaded

        except Exception as e:
            logger.warning(f"Error checking WACC content: {e}")
            return False
