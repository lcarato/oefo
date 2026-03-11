"""
International Finance Corporation (IFC) scraper.

Target: disclosures.ifc.org

The IFC publishes disclosure documents for all investment projects, including:
- Environmental & Social Review Summary (ESRS) documents
- Sector Information Summaries (SII)
- Project Appraisal Documents (PAD)

This scraper focuses on energy sector projects and downloads their
environmental/social disclosure documents which contain detailed project
financing information.
"""

import logging
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import RawDocument, SourceType
from .base import BaseScraper

logger = logging.getLogger(__name__)


class IFCScraper(BaseScraper):
    """
    Scraper for International Finance Corporation project disclosures.

    Searches for energy sector projects on disclosures.ifc.org and
    downloads ESRS/SII PDF documents containing project details.

    Attributes:
        base_url: https://disclosures.ifc.org
    """

    def __init__(self, output_dir: str = "data/raw/ifc") -> None:
        """Initialize IFC scraper."""
        super().__init__(
            name="IFC",
            base_url="https://disclosures.ifc.org",
            output_dir=output_dir,
            rate_limit=1.0,
        )

    def scrape(self) -> list[RawDocument]:
        """
        Scrape IFC energy sector projects.

        Returns:
            List of RawDocument objects for downloaded disclosure documents
        """
        documents = []

        try:
            logger.info("Starting IFC scraping...")

            # Search for energy sector projects
            project_urls = self.search_projects(sector="energy")
            logger.info(f"Found {len(project_urls)} energy sector projects")

            # Download documents for each project
            for idx, project_url in enumerate(project_urls, 1):
                logger.info(
                    f"Processing project {idx}/{len(project_urls)}: {project_url}"
                )

                try:
                    doc_paths = self.download_project_documents(project_url)
                    logger.debug(f"  Downloaded {len(doc_paths)} documents")

                    # Register each downloaded document
                    for doc_path in doc_paths:
                        project_metadata = self.scrape_project_page(project_url)
                        doc = self.register_document(
                            url=project_url,
                            filepath=doc_path,
                            source_type=SourceType.DFI_DISCLOSURE,
                            source_institution="IFC",
                            document_title=project_metadata.get("name"),
                        )
                        documents.append(doc)

                except Exception as e:
                    logger.error(f"  Error processing {project_url}: {e}")
                    continue

        except Exception as e:
            logger.error(f"IFC scraping failed: {e}")

        logger.info(f"IFC scraping complete. Downloaded {len(documents)} documents.")
        return documents

    def search_projects(
        self,
        sector: str = "energy",
        status: Optional[str] = None,
    ) -> list[str]:
        """
        Search for IFC projects by sector.

        Args:
            sector: Project sector (e.g., "energy")
            status: Optional project status filter

        Returns:
            List of project URLs
        """
        logger.debug(f"Searching for {sector} sector projects...")

        search_url = f"{self.base_url}/projects"
        params = {"sector": sector}
        if status:
            params["status"] = status

        try:
            # Note: IFC site structure may vary; this is a template
            soup = self.get_soup(search_url)

            project_links = []
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if "/projects/" in href and href.startswith("/"):
                    project_links.append(urljoin(self.base_url, href))

            # Remove duplicates
            project_urls = list(set(project_links))
            logger.debug(f"  Found {len(project_urls)} unique project URLs")

            return project_urls

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def scrape_project_page(self, url: str) -> dict:
        """
        Extract metadata from a project page.

        Args:
            url: Project URL

        Returns:
            Dictionary with project metadata (name, country, sector, amount, etc.)
        """
        logger.debug(f"Scraping project page: {url}")

        try:
            soup = self.get_soup(url)
            metadata = self.parse_project_metadata(soup)
            logger.debug(f"  Extracted metadata: {metadata}")
            return metadata

        except Exception as e:
            logger.error(f"Failed to scrape project page: {e}")
            return {}

    def download_project_documents(self, project_url: str) -> list:
        """
        Download all disclosure documents (ESRS, SII) for a project.

        Args:
            project_url: URL of the project page

        Returns:
            List of local file paths to downloaded PDFs
        """
        logger.debug(f"Downloading project documents from {project_url}")

        doc_paths = []

        try:
            soup = self.get_soup(project_url)

            # Look for PDF links (ESRS, SII, PAD documents)
            doc_types = ["ESRS", "SII", "PAD", "Project Document"]
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True).upper()

                # Check if link is a document we want
                if any(doc_type in text for doc_type in doc_types):
                    if href.endswith(".pdf") or "pdf" in href.lower():
                        doc_url = urljoin(self.base_url, href)
                        filename = f"ifc_{text}_{int(time.time())}.pdf"

                        try:
                            filepath = self.download_pdf(doc_url, filename)
                            if not self.is_duplicate(doc_url, filepath):
                                doc_paths.append(filepath)
                        except Exception as e:
                            logger.error(f"  Failed to download {doc_url}: {e}")

        except Exception as e:
            logger.error(f"Error downloading documents: {e}")

        return doc_paths

    def parse_project_metadata(self, soup: BeautifulSoup) -> dict:
        """
        Parse project metadata from HTML.

        Extracts:
        - Project name
        - Country
        - Sector
        - Financing amount
        - Status

        Args:
            soup: BeautifulSoup object of project page

        Returns:
            Dictionary with metadata
        """
        metadata = {
            "name": None,
            "country": None,
            "sector": None,
            "amount_usd": None,
            "status": None,
        }

        try:
            # Look for project title (usually in h1 or similar)
            title = soup.find("h1") or soup.find("h2")
            if title:
                metadata["name"] = title.get_text(strip=True)

            # Look for metadata in common locations
            for dt in soup.find_all("dt"):
                label = dt.get_text(strip=True).lower()
                dd = dt.find_next("dd")

                if dd:
                    value = dd.get_text(strip=True)

                    if "country" in label:
                        metadata["country"] = value
                    elif "sector" in label:
                        metadata["sector"] = value
                    elif "amount" in label or "investment" in label:
                        metadata["amount_usd"] = value
                    elif "status" in label:
                        metadata["status"] = value

        except Exception as e:
            logger.warning(f"Error parsing metadata: {e}")

        return metadata


import time
