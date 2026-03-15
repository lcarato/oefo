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

    def _get_sitemap_urls(self, sitemap_url: str, filter_pattern: str = None) -> list[str]:
        """Fetch and parse sitemap XML for URLs matching a pattern."""
        try:
            response = self.session.get(sitemap_url, timeout=60)
            response.raise_for_status()
            urls = re.findall(r'<loc>(.*?)</loc>', response.text)
            if filter_pattern:
                urls = [u for u in urls if re.search(filter_pattern, u)]
            return urls
        except Exception as e:
            logger.warning(f"Sitemap fetch failed for {sitemap_url}: {e}")
            return []

    def _known_publications(self) -> list[dict]:
        """Return known high-value Ofgem RIIO publication URLs."""
        base = self.base_url
        return [
            {
                "decision_id": "ofgem_riio_ed2_final_determinations",
                "title": "RIIO-ED2 Final Determinations",
                "url": f"{base}/publications/riio-ed2-final-determinations",
                "subject": "RIIO Price Control Decision",
            },
            {
                "decision_id": "ofgem_riio2_sector_methodology",
                "title": "RIIO-2 Sector Specific Methodology Decision",
                "url": f"{base}/publications/riio-2-sector-specific-methodology-decision",
                "subject": "RIIO Methodology Decision",
            },
            {
                "decision_id": "ofgem_riio_ed2_draft_determinations",
                "title": "RIIO-ED2 Draft Determinations",
                "url": f"{base}/consultation/riio-ed2-draft-determinations",
                "subject": "RIIO Draft Determinations",
            },
            {
                "decision_id": "ofgem_riio2_final_determinations_core",
                "title": "RIIO-2 Final Determinations – Core Methodology",
                "url": f"{base}/publications/riio-2-final-determinations-core-methodology",
                "subject": "RIIO Price Control Decision",
            },
            {
                "decision_id": "ofgem_riio_gd2_final_determinations",
                "title": "RIIO-GD2 Final Determinations",
                "url": f"{base}/publications/riio-gd2-final-determinations",
                "subject": "RIIO Price Control Decision",
            },
            {
                "decision_id": "ofgem_riio_t2_final_determinations",
                "title": "RIIO-T2 Final Determinations",
                "url": f"{base}/publications/riio-t2-final-determinations",
                "subject": "RIIO Price Control Decision",
            },
        ]

    def list_decisions(self) -> list[dict]:
        """
        List Ofgem RIIO price control decisions.

        Combines: known publication URLs (primary) + sitemap filtering
        + publications search (complement).

        Returns:
            List of decision metadata
        """
        logger.debug("Listing Ofgem RIIO price control decisions...")

        decisions = []
        seen_urls = set()

        # Strategy 1: Known publication URLs (primary — verified working)
        for d in self._known_publications():
            if d["url"] not in seen_urls:
                seen_urls.add(d["url"])
                decisions.append(d)

        logger.debug(f"  Known publications: {len(decisions)}")

        # Strategy 2: Sitemap filtering for RIIO URLs
        riio_pattern = r"(?i)riio"
        exclude_pattern = r"/cy/"  # Exclude Welsh translations
        for page in range(1, 6):  # Up to 5 sitemap pages
            sitemap_url = f"{self.base_url}/sitemap.xml?page={page}"
            urls = self._get_sitemap_urls(sitemap_url, filter_pattern=riio_pattern)
            if not urls:
                break
            for url in urls:
                if url in seen_urls or re.search(exclude_pattern, url):
                    continue
                # Further filter for decision/determination/finance pages
                if any(kw in url.lower() for kw in [
                    "determination", "decision", "publication", "finance",
                    "cost-of", "allowed-return", "equity", "methodology",
                ]):
                    seen_urls.add(url)
                    slug = url.rstrip("/").split("/")[-1]
                    title = slug.replace("-", " ").title()
                    decisions.append({
                        "decision_id": f"ofgem_sitemap_{slug[:50]}",
                        "title": title,
                        "url": url,
                        "subject": "RIIO Price Control Decision",
                    })

        logger.debug(f"  After sitemap: {len(decisions)} decisions")

        # Strategy 3: Publications search (complement)
        relevance_keywords = [
            "riio", "cost of", "wacc", "price control",
            "final determination", "allowed return",
            "equity", "finance", "network price",
        ]

        search_keywords = [
            "RIIO cost of equity",
            "RIIO cost of capital",
            "RIIO WACC",
            "allowed return",
            "price control final determination",
        ]

        for keyword in search_keywords:
            try:
                search_url = f"{self.base_url}/search/publications?keyword={keyword.replace(' ', '+')}"
                soup = self.get_soup(search_url)

                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    text = link.get_text(strip=True)

                    if not any(kw in text.lower() for kw in relevance_keywords):
                        continue

                    full_url = urljoin(self.base_url, href) if href.startswith("/") else href

                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    decision_id = f"ofgem_{text[:50].replace(' ', '_')}"
                    decisions.append({
                        "decision_id": decision_id,
                        "title": text,
                        "url": full_url,
                        "subject": "RIIO Price Control Decision",
                    })

            except Exception as e:
                logger.debug(f"Ofgem search failed for '{keyword}': {e}")
                continue

        logger.debug(f"  Found {len(decisions)} decisions total")
        return decisions

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
