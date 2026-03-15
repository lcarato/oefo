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

    # Search queries for comprehensive energy project coverage
    SEARCH_QUERIES = [
        "energy power renewable project",
        "wind solar hydro project",
        "power generation financing",
        "electricity transmission distribution",
        "cost of capital energy",
        "project finance energy",
    ]

    def _search_projects_api(self, query: str, page: int = 1) -> dict:
        """
        Search EBRD projects using the internal AEM search servlet.

        Args:
            query: Search keyword(s)
            page: Page number (starts at 1)

        Returns:
            JSON response dict with resultCount and searchResult arrays
        """
        search_url = f"{self.base_url}/bin/ebrd_dxp/ebrdsearchservlet"
        params = {
            "searchKey": query,
            "inCorrectSearchKey": "none",
            "currentPage": str(page),
            "sortBy": "most-relevant",
            "filters": "",
            "pageTypeFilters": "",
            "startDate": "",
            "endDate": "",
            "currentPageUrl": "/content/ebrd_dxp/uk/en/home/search/jcr:content/root/container/ebrd_search",
            "filterCount": "0",
            "IsLoggedIn": "false",
            "isAlumni": "false",
            "isBeeps": "false",
        }

        response = self.session.get(search_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def download_master_csv(self) -> Path:
        """
        Build EBRD energy project list via search servlet API.

        Uses the EBRD internal search API to find energy sector projects,
        then saves results as CSV for downstream filtering.

        Returns:
            Path to CSV file with project data
        """
        logger.info("Building EBRD project list via search API...")

        projects = []
        seen_paths = set()

        for query in self.SEARCH_QUERIES:
            try:
                data = self._search_projects_api(query)
                for result in data.get("searchResult", []):
                    path = result.get("pagePath", "")
                    tags = result.get("tags", "")
                    label = result.get("label", "")
                    title = result.get("title", "")

                    if path in seen_paths:
                        continue

                    # Filter for energy project PSDs
                    is_project = "project/psd" in tags or label == "Project"
                    is_energy = (
                        "sectors/energy" in tags
                        or any(kw in title.lower() for kw in [
                            "power", "energy", "renewable", "solar", "wind",
                            "hydro", "electricity", "grid", "generation",
                        ])
                    )

                    if is_project or is_energy:
                        seen_paths.add(path)
                        # Convert AEM internal path to public URL
                        public_url = self.base_url + path.replace(
                            "/content/ebrd_dxp/uk/en", ""
                        )
                        projects.append({
                            "Project Name": title,
                            "Project URL": public_url,
                            "Date": result.get("publishDate", ""),
                            "Sector": "Energy",
                            "Tags": tags,
                        })

                logger.debug(f"  Query '{query}': found {len(data.get('searchResult', []))} results")

            except Exception as e:
                logger.warning(f"EBRD search failed for '{query}': {e}")
                continue

        # Save to CSV
        csv_path = self.output_dir / "ebrd_projects_api.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(projects)
        df.to_csv(csv_path, index=False)

        logger.info(f"Built EBRD project list: {len(projects)} energy projects")
        return csv_path

    def _scrape_project_list(self) -> Path:
        """
        Fallback: scrape project list from web page if API unavailable.

        Returns:
            Path to CSV file with scraped data
        """
        logger.warning("Using fallback project list scraping...")

        projects = []
        # Try the search API with a simpler approach
        try:
            data = self._search_projects_api("energy")
            for result in data.get("searchResult", []):
                path = result.get("pagePath", "")
                public_url = self.base_url + path.replace(
                    "/content/ebrd_dxp/uk/en", ""
                )
                projects.append({
                    "Project Name": result.get("title", ""),
                    "Country": "",
                    "Sector": "Energy",
                    "Project URL": public_url,
                })
        except Exception as e:
            logger.error(f"Fallback scraping failed: {e}")

        csv_path = self.output_dir / "ebrd_projects_fallback.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(projects)
        df.to_csv(csv_path, index=False)

        logger.info(f"Saved {len(projects)} projects to {csv_path}")
        return csv_path

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
            # EBRD serves PDFs from /dam/ paths (AEM Digital Asset Manager)
            pdf_link = None
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                text = link.get_text(strip=True).upper()

                if href.endswith(".pdf") or "/dam/" in href:
                    # Prefer PSD/Summary documents
                    if "PSD" in text or "SUMMARY" in text or "PROJECT" in text:
                        pdf_link = href
                        break
                    elif not pdf_link:
                        pdf_link = href  # Keep first PDF as fallback

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
