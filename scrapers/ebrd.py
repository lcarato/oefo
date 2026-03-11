"""
European Bank for Reconstruction and Development (EBRD) scraper.

Target: ebrd.com/projects

EBRD publishes a downloadable CSV master list of all projects, making it unique
among DFIs. The scraper downloads this CSV, filters for energy sector projects,
and then downloads individual Project Summary Documents (PSDs) for each project.

CSV contains: project name, country, sector, status, financing amount, URLs.
"""

import csv
import logging
import tempfile
import time
from io import StringIO
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup

from ..models import RawDocument, SourceType
from .base import BaseScraper

logger = logging.getLogger(__name__)


class EBRDScraper(BaseScraper):
    """
    Scraper for European Bank for Reconstruction and Development projects.

    EBRD is unique in providing a downloadable CSV master list of all projects.
    The scraper downloads this CSV, filters for energy sector, then downloads
    individual Project Summary Documents (PSDs).

    Attributes:
        base_url: https://www.ebrd.com
    """

    def __init__(self, output_dir: str = "data/raw/ebrd") -> None:
        """Initialize EBRD scraper."""
        super().__init__(
            name="EBRD",
            base_url="https://www.ebrd.com",
            output_dir=output_dir,
            rate_limit=1.0,
        )
        self.csv_cache: Optional[pd.DataFrame] = None

    def scrape(self) -> list[RawDocument]:
        """
        Scrape EBRD energy sector projects.

        Returns:
            List of RawDocument objects for downloaded PSDs
        """
        documents = []

        try:
            logger.info("Starting EBRD scraping...")

            # Download and cache master CSV
            csv_path = self.download_master_csv()
            logger.info(f"Downloaded master CSV: {csv_path}")

            # Filter for energy projects
            energy_projects = self.filter_energy_projects(csv_path)
            logger.info(f"Found {len(energy_projects)} energy sector projects")

            # Download PSD for each project
            for idx, (_, row) in enumerate(energy_projects.iterrows(), 1):
                logger.info(f"Processing project {idx}/{len(energy_projects)}")

                try:
                    project_url = row.get("Project URL") or row.get("URL")
                    project_name = row.get("Project Name") or row.get("Name")

                    if not project_url:
                        logger.warning(f"  No URL for project: {project_name}")
                        continue

                    # Download project summary
                    doc_path = self.download_project_summary(project_url)

                    if doc_path and doc_path.exists():
                        doc = self.register_document(
                            url=project_url,
                            filepath=doc_path,
                            source_type=SourceType.DFI_DISCLOSURE,
                            source_institution="EBRD",
                            document_title=project_name,
                        )
                        documents.append(doc)

                except Exception as e:
                    logger.error(f"  Error processing project: {e}")
                    continue

        except Exception as e:
            logger.error(f"EBRD scraping failed: {e}")

        logger.info(f"EBRD scraping complete. Downloaded {len(documents)} documents.")
        return documents

    def download_master_csv(self) -> Path:
        """
        Download EBRD master project CSV.

        EBRD publishes a downloadable CSV list at:
        https://www.ebrd.com/projects (with export option)

        Returns:
            Path to downloaded CSV file
        """
        logger.info("Downloading EBRD master project CSV...")

        # EBRD CSV export URL (this is a template; actual URL may vary)
        csv_url = "https://www.ebrd.com/documents/projects/export.csv"

        try:
            csv_path = self.download_file(csv_url, "ebrd_projects_master.csv")
            return csv_path

        except Exception as e:
            logger.error(f"Failed to download master CSV: {e}")
            # Try alternative approach: scrape project page
            return self._scrape_project_list()

    def _scrape_project_list(self) -> Path:
        """
        Fallback: scrape project list from web page if CSV unavailable.

        Returns:
            Path to CSV file with scraped data
        """
        logger.warning("Using fallback project list scraping...")

        projects = []
        search_url = f"{self.base_url}/projects"

        try:
            soup = self.get_soup(search_url)

            # Extract project information from page
            for row in soup.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) >= 3:
                    project_name = cols[0].get_text(strip=True)
                    country = cols[1].get_text(strip=True)
                    sector = cols[2].get_text(strip=True)

                    # Try to find project URL
                    link = cols[0].find("a")
                    project_url = urljoin(self.base_url, link["href"]) if link else None

                    projects.append(
                        {
                            "Project Name": project_name,
                            "Country": country,
                            "Sector": sector,
                            "Project URL": project_url,
                        }
                    )

            # Save to CSV
            csv_path = self.output_dir / "ebrd_projects_fallback.csv"
            df = pd.DataFrame(projects)
            df.to_csv(csv_path, index=False)

            logger.info(f"Saved {len(projects)} projects to {csv_path}")
            return csv_path

        except Exception as e:
            logger.error(f"Fallback scraping failed: {e}")
            raise

    def filter_energy_projects(self, csv_path: Path) -> pd.DataFrame:
        """
        Filter CSV for energy sector projects.

        Args:
            csv_path: Path to master CSV file

        Returns:
            DataFrame filtered for energy sector
        """
        logger.debug(f"Filtering energy projects from {csv_path}")

        try:
            df = pd.read_csv(csv_path)

            # Filter for energy sector
            energy_keywords = [
                "energy",
                "power",
                "renewable",
                "solar",
                "wind",
                "hydro",
                "electricity",
                "gas",
            ]

            mask = df["Sector"].str.contains(
                "|".join(energy_keywords), case=False, na=False
            )
            energy_df = df[mask].copy()

            logger.info(
                f"Filtered {len(energy_df)} energy projects from {len(df)} total"
            )
            self.csv_cache = energy_df

            return energy_df

        except Exception as e:
            logger.error(f"Filtering failed: {e}")
            return pd.DataFrame()

    def scrape_project_page(self, url: str) -> dict:
        """
        Extract metadata from EBRD project page.

        Args:
            url: Project URL

        Returns:
            Dictionary with project metadata
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

            # Parse project details (structure depends on EBRD site layout)
            for h in soup.find_all(["h1", "h2"]):
                text = h.get_text(strip=True)
                if len(text) < 200:
                    metadata["name"] = text
                    break

            # Look for metadata in div/span elements
            for elem in soup.find_all(["div", "span"]):
                text = elem.get_text(strip=True)
                if "Country:" in text:
                    metadata["country"] = text.replace("Country:", "").strip()
                elif "Sector:" in text:
                    metadata["sector"] = text.replace("Sector:", "").strip()
                elif "Amount:" in text or "Financing:" in text:
                    metadata["amount_usd"] = text.split(":")[-1].strip()

            return metadata

        except Exception as e:
            logger.error(f"Failed to scrape project page: {e}")
            return {}

    def download_project_summary(self, project_url: str) -> Optional[Path]:
        """
        Download Project Summary Document (PSD) PDF for a project.

        Args:
            project_url: URL of the project page

        Returns:
            Path to downloaded PDF, or None if not found
        """
        logger.debug(f"Downloading project summary from {project_url}")

        try:
            soup = self.get_soup(project_url)

            # Look for PSD or summary PDF link
            pdf_link = None
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True).upper()

                if ("PSD" in text or "SUMMARY" in text) and href.endswith(".pdf"):
                    pdf_link = href
                    break

            if not pdf_link:
                logger.warning(f"  No PSD found for {project_url}")
                return None

            pdf_url = urljoin(self.base_url, pdf_link)
            filename = f"ebrd_psd_{int(time.time())}.pdf"

            try:
                pdf_path = self.download_pdf(pdf_url, filename)
                logger.info(f"  Downloaded PSD: {pdf_path}")
                return pdf_path

            except Exception as e:
                logger.error(f"  Failed to download PSD: {e}")
                return None

        except Exception as e:
            logger.error(f"Error downloading project summary: {e}")
            return None
