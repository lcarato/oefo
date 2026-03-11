"""
Regulatory scraper module.

Provides scrapers for energy regulatory agencies that publish
rate-setting decisions and WACC/cost of capital parameters.

Available scrapers:
- ANEEL (Brazil): Tariff reviews with WACC decomposition
- AER (Australia): Rate of return decisions with Excel models
- Ofgem (UK): RIIO price control decisions
- FERC (US): Rate case orders with allowed ROE
"""

from .aneel import ANEELScraper
from .aer import AERScraper
from .ofgem import OfgemScraper
from .ferc import FERCScraper

__all__ = ["ANEELScraper", "AERScraper", "OfgemScraper", "FERCScraper"]
