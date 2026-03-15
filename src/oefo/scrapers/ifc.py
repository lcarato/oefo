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
import time
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
        self.api_base = "https://disclosuresservice.ifc.org"

    def scrape(self) -> list[RawDocument]:
        """
        Scrape IFC energy sector projects.

        Returns:
            List of RawDocument objects for downloaded disclosure documents
        """
        documents = []

        try:
            logger.info("Starting IFC scraping...")

            # Search for energy sector projects (returns project numbers)
            project_numbers = self.search_projects(sector="energy")
            logger.info(f"Found {len(project_numbers)} energy sector projects")

            # Download documents for each project
            for idx, project_number in enumerate(project_numbers, 1):
                logger.info(
                    f"Processing project {idx}/{len(project_numbers)}: {project_number}"
                )
                project_url = f"{self.base_url}/project-detail/SII/{project_number}"

                try:
                    doc_paths = self.download_project_documents(project_number)
                    logger.debug(f"  Downloaded {len(doc_paths)} documents")

                    # Register each downloaded document
                    detail = self._get_project_detail(project_number)
                    project_name = detail.get("ProjectName") or f"IFC-{project_number}"
                    for doc_path in doc_paths:
                        doc = self.register_document(
                            url=project_url,
                            filepath=doc_path,
                            source_type=SourceType.DFI_DISCLOSURE,
                            source_institution="IFC",
                            document_title=project_name,
                        )
                        documents.append(doc)

                except Exception as e:
                    logger.error(f"  Error processing {project_url}: {e}")
                    continue

        except Exception as e:
            logger.error(f"IFC scraping failed: {e}")

        logger.info(f"IFC scraping complete. Downloaded {len(documents)} documents.")
        return documents

    def _get_landing_projects(self) -> list[dict]:
        """Get recent projects from the IFC landing page API."""
        url = f"{self.api_base}/api/searchprovider/landingPageDetails"
        try:
            resp = self.session.get(url, params={"isLanding": "1"}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            projects = []
            for proj in data.get("investmentProjects", []):
                projects.append(proj)
            for proj in data.get("advisoryProjects", []):
                projects.append(proj)
            return projects
        except Exception as e:
            logger.warning(f"IFC landing page API failed: {e}")
            return []

    def _search_projects_api(self) -> list[dict]:
        """Search IFC projects via the enterprise search POST endpoint."""
        url = f"{self.api_base}/api/searchprovider/searchenterpriseprojects"
        # Try multiple body formats — the Angular app uses varying schemas
        search_bodies = [
            {"searchText": "", "sectorDesc": ["Power"], "pageNumber": 1, "pageSize": 50},
            {"SearchText": "", "IndustryId": [8], "PageNumber": 1, "PageSize": 50},
            {"keyword": "energy power", "page": 1, "pageSize": 50},
        ]
        for body in search_bodies:
            try:
                resp = self.session.post(url, json=body, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    results = (
                        data if isinstance(data, list)
                        else data.get("results",
                             data.get("investmentProjects",
                             data.get("projects", [])))
                    )
                    if results:
                        return results
            except Exception:
                continue
        return []

    def _get_project_detail(self, project_number: str) -> dict:
        """Get full project detail including SupportingDocuments."""
        url = f"{self.api_base}/api/ProjectAccess/SIIProject"
        try:
            resp = self.session.get(
                url, params={"projectId": project_number}, timeout=30
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}

    def search_projects(
        self,
        sector: str = "energy",
        status: Optional[str] = None,
    ) -> list[str]:
        """
        Search for IFC projects using the backend REST API.

        The IFC disclosure site is an Angular SPA — HTML scraping only
        gets the shell. This method uses the REST API at
        disclosuresservice.ifc.org instead.

        Args:
            sector: Project sector (e.g., "energy")
            status: Optional project status filter

        Returns:
            List of project numbers (used as identifiers)
        """
        logger.debug(f"Searching for {sector} sector projects via IFC API...")

        project_numbers = []
        seen = set()

        # Strategy 1: Landing page API (recent projects)
        landing_projects = self._get_landing_projects()
        for proj in landing_projects:
            pn = str(proj.get("ProjectNumber", ""))
            industry = (proj.get("Industry") or "").lower()
            if pn and pn not in seen:
                # Filter for energy/power if sector specified
                if sector == "energy" and not any(
                    kw in industry for kw in ["power", "energy", "infrastructure"]
                ):
                    continue
                seen.add(pn)
                project_numbers.append(pn)

        logger.debug(f"  Landing API: {len(project_numbers)} projects")

        # Strategy 2: Enterprise search POST
        search_results = self._search_projects_api()
        for item in search_results:
            pn = str(
                item.get("ProjectNumber")
                or item.get("projectNumber")
                or ""
            )
            if pn and pn not in seen:
                seen.add(pn)
                project_numbers.append(pn)

        logger.debug(f"  After search API: {len(project_numbers)} projects total")

        # Strategy 3: Fallback — brute-force validate recent project IDs
        if len(project_numbers) < 10:
            logger.info("  Using fallback: validating recent project IDs...")
            validate_url = f"{self.api_base}/api/ProjectAccess/validateProjectUrl"
            for pn_int in range(52000, 49000, -1):
                pn = str(pn_int)
                if pn in seen:
                    continue
                try:
                    resp = self.session.get(
                        validate_url,
                        params={"ProjectNumber": pn, "documentType": "SII"},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        seen.add(pn)
                        project_numbers.append(pn)
                except Exception:
                    continue
                if len(project_numbers) >= 50:
                    break

        logger.info(f"Found {len(project_numbers)} IFC projects")
        return project_numbers

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

    def download_project_documents(self, project_number: str) -> list:
        """
        Download all disclosure documents (ESRS, SII) for a project
        using the IFC REST API.

        Args:
            project_number: IFC project number (e.g., "50350")

        Returns:
            List of local file paths to downloaded PDFs
        """
        logger.debug(f"Downloading documents for project {project_number} via API")

        doc_paths = []

        try:
            detail = self._get_project_detail(project_number)
            supporting_docs = detail.get("SupportingDocuments", [])

            for doc in supporting_docs:
                doc_url = doc.get("Url") or doc.get("url") or ""
                doc_name = doc.get("Name") or doc.get("name") or ""

                if not doc_url:
                    continue

                # Build full URL if relative
                if not doc_url.startswith("http"):
                    doc_url = urljoin(self.api_base, doc_url)

                filename = f"ifc_{project_number}_{doc_name[:30]}_{int(time.time())}.pdf"
                filename = filename.replace(" ", "_").replace("/", "_")

                try:
                    filepath = self.download_pdf(doc_url, filename)
                    if filepath and not self.is_duplicate(doc_url, filepath):
                        doc_paths.append(filepath)
                except Exception as e:
                    logger.debug(f"  Failed to download {doc_url}: {e}")

            # If no documents from API, try the project page HTML as fallback
            if not doc_paths:
                project_url = f"{self.base_url}/project-detail/SII/{project_number}"
                try:
                    soup = self.get_soup(project_url)
                    for link in soup.find_all("a", href=True):
                        href = link.get("href", "")
                        if href.endswith(".pdf") or "pdf" in href.lower():
                            doc_url = urljoin(self.base_url, href)
                            filename = f"ifc_{project_number}_{int(time.time())}.pdf"
                            try:
                                filepath = self.download_pdf(doc_url, filename)
                                if filepath:
                                    doc_paths.append(filepath)
                            except Exception:
                                pass
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Error downloading documents for {project_number}: {e}")

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
