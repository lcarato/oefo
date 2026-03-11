"""
OEFO Web Scraper Modules.

Provides scrapers for energy financing data from:

Development Finance Institutions (DFIs):
- IFC (International Finance Corporation)
- EBRD (European Bank for Reconstruction and Development)
- GCF (Green Climate Fund)

Corporate Filings:
- SEC EDGAR (US Securities and Exchange Commission)

Regulatory Agencies:
- ANEEL (Brazil - Agência Nacional de Energia Elétrica)
- AER (Australia - Australian Energy Regulator)
- Ofgem (UK - Office of Gas and Electricity Markets)
- FERC (US - Federal Energy Regulatory Commission)

All scrapers inherit from BaseScraper and implement:
- Rate limiting (respect server resources)
- Retry logic (handle transient failures)
- Content deduplication (SHA-256 hashing)
- Document registration (metadata tracking)
- Comprehensive logging

Usage:
    from scrapers import get_scraper

    # Get a scraper instance
    ifc = get_scraper("IFC")

    # Run scraping
    documents = ifc.scrape()

    # Each document is a RawDocument with metadata
    for doc in documents:
        print(f"Downloaded: {doc.document_title}")
        print(f"  File: {doc.local_file_path}")
        print(f"  Hash: {doc.content_hash[:8]}...")
"""

import logging
from typing import Optional

from .base import BaseScraper
from .ifc import IFCScraper
from .ebrd import EBRDScraper
from .gcf import GCFScraper
from .sec_edgar import SECEdgarScraper
from .regulatory import ANEELScraper, AERScraper, OfgemScraper, FERCScraper

logger = logging.getLogger(__name__)


# Scraper registry
_SCRAPERS = {
    "IFC": IFCScraper,
    "EBRD": EBRDScraper,
    "GCF": GCFScraper,
    "SEC": SECEdgarScraper,
    "ANEEL": ANEELScraper,
    "AER": AERScraper,
    "OFGEM": OfgemScraper,
    "FERC": FERCScraper,
}


def get_scraper(name: str, **kwargs) -> BaseScraper:
    """
    Factory function to get a scraper instance.

    Args:
        name: Scraper name (IFC, EBRD, GCF, SEC, ANEEL, AER, Ofgem, FERC)
        **kwargs: Additional arguments passed to scraper constructor

    Returns:
        Initialized scraper instance

    Raises:
        ValueError: If scraper name not recognized

    Example:
        ifc = get_scraper("IFC")
        documents = ifc.scrape()
    """
    # Normalize to uppercase for case-insensitive lookup
    normalized = name.upper()
    if normalized not in _SCRAPERS:
        raise ValueError(
            f"Unknown scraper: {name}. "
            f"Available: {', '.join(_SCRAPERS.keys())}"
        )

    scraper_class = _SCRAPERS[normalized]
    return scraper_class(**kwargs)


def list_scrapers() -> list[str]:
    """
    List available scrapers.

    Returns:
        List of scraper names
    """
    return list(_SCRAPERS.keys())


__all__ = [
    # Base class
    "BaseScraper",
    # DFI Scrapers
    "IFCScraper",
    "EBRDScraper",
    "GCFScraper",
    # Corporate filing scrapers
    "SECEdgarScraper",
    # Regulatory scrapers
    "ANEELScraper",
    "AERScraper",
    "OfgemScraper",
    "FERCScraper",
    # Factory functions
    "get_scraper",
    "list_scrapers",
]
