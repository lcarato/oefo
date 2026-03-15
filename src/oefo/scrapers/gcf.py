"""
Green Climate Fund (GCF) scraper.

Target: greenclimate.fund/projects

GCF funds climate change mitigation and adaptation projects in developing
countries. The scraper searches for energy sector projects and downloads
their funding proposals (typically 50+ page PDFs) containing detailed
project design and financial information.
"""

import logging
import re
import time
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import RawDocument, SourceType
from .base import BaseScraper

logger = logging.getLogger(__name__)


class GCFScraper(BaseScraper):
    """
    Scraper for Green Climate Fund projects.

    Searches for energy sector projects on greenclimate.fund and downloads
    their funding proposals (Project Documents) which contain detailed
    financial and technical information.

    Attributes:
        base_url: https://www.greenclimate.fund
    """

    def __init__(self, output_dir: str = "data/raw/gcf") -> None:
        """Initialize GCF scraper."""
        super().__init__(
            name="GCF",
            base_url="https://www.greenclimate.fund",
            output_dir=output_dir,
            rate_limit=1.0,
        )

    def scrape(self) -> list[RawDocument]:
        """
        Scrape GCF energy sector projects.

        Returns:
            List of RawDocument objects for downloaded funding proposals
        """
        documents = []

        try:
            logger.info("Starting GCF scraping...")

            # List all energy sector projects
            project_urls = self.list_projects(sector="energy")
            logger.info(f"Found {len(project_urls)} energy sector projects")

            # Download funding proposal for each project
            for idx, project_url in enumerate(project_urls, 1):
                logger.info(f"Processing project {idx}/{len(project_urls)}")

                try:
                    project_metadata = self.scrape_project_page(project_url)
                    logger.debug(f"  Project: {project_metadata.get('name')}")

                    # Download funding proposal PDF
                    doc_path = self.download_funding_proposal(project_url)

                    if doc_path and doc_path.exists():
                        doc = self.register_document(
                            url=project_url,
                            filepath=doc_path,
                            source_type=SourceType.DFI_DISCLOSURE,
                            source_institution="GCF",
                            document_title=project_metadata.get("name"),
                        )
                        documents.append(doc)

                except Exception as e:
                    logger.error(f"  Error processing {project_url}: {e}")
                    continue

        except Exception as e:
            logger.error(f"GCF scraping failed: {e}")

        logger.info(f"GCF scraping complete. Downloaded {len(documents)} documents.")
        return documents

    # Energy keywords for filtering projects
    ENERGY_KEYWORDS = [
        "energy", "solar", "wind", "power", "renewable", "electricity",
        "hydropower", "geothermal", "biomass", "grid", "transmission",
        "generation", "photovoltaic", "turbine",
    ]

    # Maximum FP number to iterate through (fallback only)
    MAX_FP_NUMBER = 300

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

    def list_projects(self, sector: str = "energy") -> list[str]:
        """
        List GCF projects using sitemap (primary) or FP iteration (fallback).

        Primary: Parse sitemap for /project/fp URLs (371 projects, instant).
        Fallback: Iterate FP numbers with HEAD requests if sitemap fails.
        Energy filtering is deferred to download_funding_proposal().

        Args:
            sector: Sector name (e.g., "energy")

        Returns:
            List of project URLs
        """
        logger.debug(f"Listing {sector} sector projects...")

        project_urls = []

        # Strategy 1: Sitemap-based discovery (instant, complete)
        for page in range(1, 5):  # Check up to 4 sitemap pages
            sitemap_url = f"{self.base_url}/sitemap.xml?page={page}"
            urls = self._get_sitemap_urls(sitemap_url, filter_pattern=r"/project/fp\d")
            if not urls:
                break
            project_urls.extend(urls)

        if project_urls:
            # Deduplicate and normalize
            seen = set()
            unique_urls = []
            for url in project_urls:
                normalized = url.rstrip("/")
                if normalized not in seen:
                    seen.add(normalized)
                    unique_urls.append(normalized)
            project_urls = unique_urls
            logger.info(f"Sitemap: found {len(project_urls)} GCF project URLs")
        else:
            # Strategy 2: Fallback — HEAD scan (slow but reliable)
            logger.info("Sitemap unavailable, falling back to FP iteration...")
            consecutive_misses = 0
            for i in range(1, self.MAX_FP_NUMBER + 1):
                fp_id = f"fp{i:03d}"
                url = f"{self.base_url}/project/{fp_id}"
                try:
                    resp = self.session.head(url, timeout=10, allow_redirects=True)
                    if resp.status_code == 200:
                        project_urls.append(url)
                        consecutive_misses = 0
                    else:
                        consecutive_misses += 1
                except Exception:
                    consecutive_misses += 1
                if consecutive_misses >= 20 and project_urls:
                    break

        logger.info(f"Found {len(project_urls)} GCF project pages")
        return project_urls

    def _is_energy_project(self, url: str) -> bool:
        """Check if a project page contains energy-related keywords."""
        try:
            soup = self.get_soup(url)
            text = soup.get_text(separator=" ").lower()
            return any(kw in text for kw in self.ENERGY_KEYWORDS)
        except Exception:
            return False

    def scrape_project_page(self, url: str) -> dict:
        """
        Extract metadata from a GCF project page.

        Args:
            url: Project URL

        Returns:
            Dictionary with project metadata (name, country, sector, etc.)
        """
        logger.debug(f"Scraping project page: {url}")

        try:
            soup = self.get_soup(url)

            metadata = {
                "name": None,
                "country": None,
                "sector": None,
                "amount_usd": None,
                "status": None,
                "description": None,
            }

            # Extract project title (usually in h1)
            title = soup.find("h1") or soup.find("h2")
            if title:
                metadata["name"] = title.get_text(strip=True)

            # Look for metadata in structured elements
            for label_elem in soup.find_all("strong"):
                label = label_elem.get_text(strip=True).lower()
                next_elem = label_elem.find_next()

                if next_elem:
                    value = next_elem.get_text(strip=True)

                    if "country" in label:
                        metadata["country"] = value
                    elif "sector" in label:
                        metadata["sector"] = value
                    elif "amount" in label or "approval" in label:
                        metadata["amount_usd"] = value
                    elif "status" in label:
                        metadata["status"] = value

            # Try alternative metadata location (divs with data attributes)
            for div in soup.find_all("div"):
                data_label = div.get("data-label", "").lower()

                if "country" in data_label:
                    metadata["country"] = div.get_text(strip=True)
                elif "sector" in data_label:
                    metadata["sector"] = div.get_text(strip=True)
                elif "amount" in data_label:
                    metadata["amount_usd"] = div.get_text(strip=True)

            return metadata

        except Exception as e:
            logger.error(f"Failed to scrape project page: {e}")
            return {}

    def download_funding_proposal(self, project_url: str) -> Optional[str]:
        """
        Download the funding proposal (project document) PDF.

        GCF funding proposals are typically 50+ pages and contain:
        - Project description
        - Logical framework
        - Financial projections
        - Risk analysis
        - Environmental and social assessments

        Args:
            project_url: URL of the project page

        Returns:
            Path to downloaded PDF, or None if not found
        """
        logger.debug(f"Downloading funding proposal from {project_url}")

        try:
            soup = self.get_soup(project_url)

            # Look for project document/proposal PDF
            # GCF project pages list documents under a "Documents" section
            # PDF links may contain /document/ in the URL path
            pdf_link = None

            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True).lower()

                # Match funding proposal / approved documents
                is_proposal = any(kw in text for kw in [
                    "funding proposal", "approved", "project document",
                    "proposal", "funding document",
                ])
                is_pdf = (
                    ".pdf" in href.lower()
                    or "/document/" in href
                )

                if is_proposal and is_pdf:
                    pdf_link = href
                    break

            # Fallback: grab any PDF link on the page
            if not pdf_link:
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    if ".pdf" in href.lower() or "/document/" in href:
                        pdf_link = href
                        break

            if not pdf_link:
                logger.warning(f"  No funding proposal found for {project_url}")
                return None

            pdf_url = urljoin(self.base_url, pdf_link)
            filename = f"gcf_proposal_{int(time.time())}.pdf"

            try:
                pdf_path = self.download_pdf(pdf_url, filename)
                logger.info(f"  Downloaded proposal: {pdf_path}")
                return str(pdf_path)

            except Exception as e:
                logger.error(f"  Failed to download proposal: {e}")
                return None

        except Exception as e:
            logger.error(f"Error downloading funding proposal: {e}")
            return None
