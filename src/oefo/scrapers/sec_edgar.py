"""
SEC EDGAR scraper for US corporate filings.

Target: eft.sec.gov (EDGAR Full-Text Search API) and data.sec.gov (XBRL API)

The SEC requires financial institutions, utilities, and public companies to
file disclosures including:
- 10-K (annual reports) - contain WACC, cost of capital estimates
- 10-Q (quarterly reports)
- 8-K (current reports on material events)
- S-1 (registration statements)

This scraper can access both:
1. Full-text search API for keyword-based document discovery
2. XBRL structured data API for extracting financial metrics programmatically

Rate limit: SEC requests max 10 requests/second (0.1s minimum between requests)
"""

import json
import logging
import time
from typing import Optional
from urllib.parse import urljoin, quote

import requests

from ..models import RawDocument, SourceType
from .base import BaseScraper

logger = logging.getLogger(__name__)

# Key XBRL concepts for energy finance extraction
XBRL_FINANCIAL_CONCEPTS = {
    # Debt parameters
    "us-gaap:LongTermDebt": "debt_amount",
    "us-gaap:LongTermDebtWeightedAverageInterestRate": "kd_nominal",
    "us-gaap:DebtInstrumentInterestRateStatedPercentage": "kd_nominal",
    "us-gaap:DebtInstrumentTerm": "debt_tenor_years",
    "us-gaap:InterestExpense": "interest_expense",

    # Capital structure
    "us-gaap:LongTermDebtAndCapitalLeaseObligations": "total_debt",
    "us-gaap:StockholdersEquity": "total_equity",
    "us-gaap:DebtToEquityRatio": "debt_to_equity",

    # Credit
    "dei:EntityCreditRating": "credit_rating",
}


class SECEdgarScraper(BaseScraper):
    """
    Scraper for SEC EDGAR corporate filings.

    Supports both full-text search API and XBRL structured data API.
    Focuses on extracting financial information from 10-K, 10-Q filings.

    Attributes:
        base_url: https://www.sec.gov
        xbrl_api_url: https://data.sec.gov/submissions/CIK{cik}.json
    """

    def __init__(self, output_dir: str = "data/raw/sec") -> None:
        """Initialize SEC EDGAR scraper with SEC-compliant rate limiting."""
        super().__init__(
            name="SEC_EDGAR",
            base_url="https://www.sec.gov",
            output_dir=output_dir,
            rate_limit=0.1,  # SEC: max 10 requests/second
        )
        self.xbrl_api_url = "https://data.sec.gov/submissions"

    def scrape(self) -> list[RawDocument]:
        """
        Scrape energy sector company filings from SEC EDGAR.

        Searches for companies in utilities/renewable energy and downloads
        their 10-K and 10-Q filings.

        Returns:
            List of RawDocument objects for downloaded filings
        """
        documents = []

        try:
            logger.info("Starting SEC EDGAR scraping...")

            # Search for energy companies by keyword
            keywords = [
                "renewable energy",
                "solar power",
                "wind power",
                "utility",
                "power generation",
            ]

            all_filings = []
            for keyword in keywords:
                filings = self.search_by_keyword(
                    keyword, filing_types=["10-K", "10-Q"]
                )
                all_filings.extend(filings)
                logger.debug(f"  Found {len(filings)} filings for '{keyword}'")

            # Remove duplicates
            unique_filings = list(
                {filing["url"]: filing for filing in all_filings}.values()
            )
            logger.info(f"Found {len(unique_filings)} unique filings")

            # Download each filing
            for idx, filing in enumerate(unique_filings, 1):
                logger.info(f"Processing filing {idx}/{len(unique_filings)}")

                try:
                    doc_path = self.download_filing(filing["url"])

                    if doc_path and doc_path.exists():
                        doc = self.register_document(
                            url=filing["url"],
                            filepath=doc_path,
                            source_type=SourceType.CORPORATE_FILING,
                            source_institution=filing.get("company"),
                            document_title=f"{filing.get('filing_type')} - {filing.get('company')}",
                        )
                        documents.append(doc)

                except Exception as e:
                    logger.error(f"  Error downloading filing: {e}")
                    continue

        except Exception as e:
            logger.error(f"SEC EDGAR scraping failed: {e}")

        logger.info(f"SEC scraping complete. Downloaded {len(documents)} documents.")
        return documents

    def search_by_keyword(
        self, keyword: str, filing_types: Optional[list[str]] = None
    ) -> list[dict]:
        """
        Search SEC EDGAR for filings by keyword using full-text search API.

        Args:
            keyword: Search term (e.g., "renewable energy")
            filing_types: List of filing types to search (e.g., ["10-K", "10-Q"])

        Returns:
            List of filing objects with metadata
        """
        logger.debug(f"Searching for filings with keyword: {keyword}")

        filings = []

        try:
            # SEC Full-Text Search API endpoint
            search_url = "https://efts.sec.gov/LATEST/search-index"

            # Build query
            query = quote(keyword)
            if filing_types:
                type_filter = " OR ".join([f'form_type:"{t}"' for t in filing_types])
                query = f"{query} AND ({type_filter})"

            params = {"q": query, "from": 0, "size": 100}

            response = requests.get(search_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            hits = data.get("hits", {}).get("hits", [])

            for hit in hits:
                source = hit.get("_source", {})
                filings.append(
                    {
                        "company": source.get("company_name"),
                        "cik": source.get("cik_str"),
                        "filing_type": source.get("form_type"),
                        "date": source.get("filing_date"),
                        "url": source.get("filename"),
                        "accession": source.get("accession_number"),
                    }
                )

            logger.debug(f"  Found {len(filings)} results")
            return filings

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def search_filings(
        self,
        company: str,
        filing_type: str = "10-K",
    ) -> list[dict]:
        """
        Search filings for a specific company.

        Args:
            company: Company name or ticker
            filing_type: Type of filing (e.g., "10-K", "10-Q")

        Returns:
            List of filing objects
        """
        logger.debug(f"Searching filings for {company}...")

        # Try to get CIK first
        cik = self.get_company_cik(company)
        if not cik:
            logger.warning(f"Could not find CIK for {company}")
            return []

        return self.search_by_keyword(f"cik:{cik} AND form_type:{filing_type}")

    def get_company_cik(self, ticker_or_name: str) -> Optional[str]:
        """
        Get SEC CIK for a company by ticker or name.

        Args:
            ticker_or_name: Company ticker symbol or name

        Returns:
            CIK as zero-padded string, or None if not found
        """
        logger.debug(f"Looking up CIK for {ticker_or_name}...")

        try:
            # SEC provides a company tickers JSON file
            tickers_url = (
                "https://www.sec.gov/files/company_tickers.json"
            )

            response = requests.get(tickers_url, timeout=30)
            response.raise_for_status()

            data = response.json()

            search_term = ticker_or_name.upper()
            for entry in data.values():
                if (
                    entry.get("ticker") == search_term
                    or search_term in entry.get("title", "").upper()
                ):
                    cik = str(entry.get("cik_str", "")).zfill(10)
                    logger.debug(f"  Found CIK: {cik}")
                    return cik

            logger.warning(f"CIK not found for {ticker_or_name}")
            return None

        except Exception as e:
            logger.error(f"CIK lookup failed: {e}")
            return None

    def get_xbrl_data(
        self,
        cik: str,
        filing_type: str = "10-K",
    ) -> dict:
        """
        Download XBRL structured financial data for a company.

        XBRL (eXtensible Business Reporting Language) provides
        machine-readable financial statements with standardized
        tagging for metrics like cost of capital, debt ratios, etc.

        Args:
            cik: 10-digit company CIK (zero-padded)
            filing_type: Type of filing to extract data from

        Returns:
            Dictionary of extracted financial metrics
        """
        logger.debug(f"Fetching XBRL data for CIK {cik}...")

        try:
            # SEC XBRL API
            xbrl_url = f"{self.xbrl_api_url}/CIK{cik}.json"

            response = requests.get(xbrl_url, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Extract financial metrics from filings
            filings = data.get("filings", {}).get("recent", {})
            metrics = {
                "cik": cik,
                "company_name": data.get("entityName"),
                "filings": [],
            }

            for filing in filings.get("accessionNumber", []):
                metrics["filings"].append(
                    {
                        "accession": filing,
                        "form_type": filing.get("form"),
                        "filing_date": filing.get("filingDate"),
                    }
                )

            logger.debug(f"  Found {len(metrics['filings'])} filings")
            return metrics

        except Exception as e:
            logger.error(f"XBRL data fetch failed: {e}")
            return {}

    def get_xbrl_financial_data(self, cik: str) -> dict:
        """
        Extract structured financial data from SEC XBRL companyfacts API.

        Uses the SEC XBRL API (data.sec.gov/api/xbrl/companyfacts/) to retrieve
        company facts, then extracts the relevant financial concepts defined in
        XBRL_FINANCIAL_CONCEPTS and maps them to OEFO Observation fields.

        Args:
            cik: 10-digit company CIK (zero-padded)

        Returns:
            Dictionary mapping OEFO field names to extracted values with metadata:
            {
                "company_name": str,
                "cik": str,
                "fields": {
                    "field_name": {
                        "value": float,
                        "unit": str,
                        "fiscal_year": int,
                        "filing_date": str,
                        "xbrl_concept": str
                    },
                    ...
                }
            }
        """
        logger.info(f"Fetching XBRL financial data for CIK {cik}...")

        result = {
            "cik": cik,
            "company_name": None,
            "fields": {},
        }

        try:
            # SEC XBRL companyfacts API
            companyfacts_url = (
                f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            )

            response = requests.get(
                companyfacts_url,
                headers={"User-Agent": self.user_agent},
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            result["company_name"] = data.get("entityName")

            # Iterate through XBRL concepts we care about
            facts = data.get("facts", {})

            for xbrl_concept, oefo_field in XBRL_FINANCIAL_CONCEPTS.items():
                # Split namespace and concept name
                namespace, concept = xbrl_concept.split(":", 1)

                # Map namespace to XBRL taxonomy prefix
                ns_map = {
                    "us-gaap": "us-gaap",
                    "dei": "dei",
                }
                ns_key = ns_map.get(namespace, namespace)

                # Look up the concept in the facts
                ns_facts = facts.get(ns_key, {})
                concept_data = ns_facts.get(concept)

                if concept_data is None:
                    continue

                # Extract the most recent value from available units
                units = concept_data.get("units", {})

                # Try USD first, then pure numbers
                for unit_key in ["USD", "pure", "shares"]:
                    if unit_key not in units:
                        continue

                    entries = units[unit_key]
                    if not entries:
                        continue

                    # Get the most recent 10-K filing entry
                    annual_entries = [
                        e for e in entries
                        if e.get("form") == "10-K"
                    ]

                    if not annual_entries:
                        annual_entries = entries

                    # Sort by end date to get most recent
                    annual_entries.sort(
                        key=lambda e: e.get("end", ""),
                        reverse=True,
                    )

                    latest = annual_entries[0]

                    # Only store if we don't already have this field,
                    # or if this entry is more recent
                    if oefo_field not in result["fields"]:
                        result["fields"][oefo_field] = {
                            "value": latest.get("val"),
                            "unit": unit_key,
                            "fiscal_year": latest.get("fy"),
                            "filing_date": latest.get("filed"),
                            "period_end": latest.get("end"),
                            "xbrl_concept": xbrl_concept,
                        }
                    break  # Found a unit with data, move to next concept

            logger.info(
                f"  Extracted {len(result['fields'])} financial fields "
                f"for {result['company_name'] or cik}"
            )
            return result

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"No XBRL data available for CIK {cik}")
            else:
                logger.error(f"XBRL financial data fetch failed: {e}")
            return result
        except Exception as e:
            logger.error(f"XBRL financial data fetch failed: {e}")
            return result

    def download_filing(self, url: str) -> Optional:
        """
        Download a filing document from SEC EDGAR.

        Args:
            url: URL to filing (usually index.htm for HTML version or .txt)

        Returns:
            Path to downloaded file, or None if failed
        """
        logger.debug(f"Downloading filing from {url}")

        try:
            # Convert to actual document URL if needed
            if url.endswith("/0001193125-"):
                # This might be an index page; look for actual document
                doc_url = url.replace("index.htm", "-xslF10K01/")
            elif not url.endswith(".pdf"):
                # Try PDF version
                doc_url = url.replace(".htm", ".pdf")
            else:
                doc_url = url

            # Build full URL if relative
            if not doc_url.startswith("http"):
                doc_url = urljoin(self.base_url, doc_url)

            filename = f"sec_{int(time.time())}.pdf"

            try:
                filepath = self.download_pdf(doc_url, filename)
                logger.info(f"  Downloaded filing: {filepath}")
                return filepath

            except Exception as e:
                # Try HTML version as fallback
                logger.debug(f"  PDF download failed, trying HTML: {e}")
                html_url = doc_url.replace(".pdf", ".htm")
                filename = f"sec_{int(time.time())}.htm"

                filepath = self.download_file(html_url, filename)
                logger.info(f"  Downloaded filing (HTML): {filepath}")
                return filepath

        except Exception as e:
            logger.error(f"Failed to download filing: {e}")
            return None
