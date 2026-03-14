"""
FX conversion utility for OEFO.

Phase 1: Static annual average rates for major currencies.
Phase 2+: Live rates from FRED / ECB.
"""
from datetime import date
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Static annual average FX rates (units of local currency per 1 USD)
# Source: Federal Reserve / ECB annual averages
# Update annually or when adding new currencies
STATIC_FX_RATES: dict[str, dict[int, float]] = {
    "EUR": {2020: 0.877, 2021: 0.846, 2022: 0.951, 2023: 0.925, 2024: 0.924, 2025: 0.920},
    "GBP": {2020: 0.780, 2021: 0.727, 2022: 0.811, 2023: 0.804, 2024: 0.790, 2025: 0.785},
    "BRL": {2020: 5.155, 2021: 5.395, 2022: 5.165, 2023: 4.994, 2024: 5.200, 2025: 5.800},
    "INR": {2020: 74.13, 2021: 73.93, 2022: 78.60, 2023: 82.60, 2024: 83.50, 2025: 85.00},
    "AUD": {2020: 1.452, 2021: 1.332, 2022: 1.442, 2023: 1.531, 2024: 1.535, 2025: 1.560},
    "ZAR": {2020: 16.46, 2021: 14.78, 2022: 16.37, 2023: 18.45, 2024: 18.30, 2025: 18.50},
    "MXN": {2020: 21.49, 2021: 20.28, 2022: 20.13, 2023: 17.76, 2024: 17.10, 2025: 20.00},
    "COP": {2020: 3693, 2021: 3743, 2022: 4255, 2023: 4327, 2024: 4050, 2025: 4200},
    "PEN": {2020: 3.495, 2021: 3.881, 2022: 3.835, 2023: 3.744, 2024: 3.750, 2025: 3.780},
    "CLP": {2020: 792, 2021: 759, 2022: 873, 2023: 840, 2024: 920, 2025: 950},
    "PHP": {2020: 49.62, 2021: 49.25, 2022: 54.47, 2023: 55.57, 2024: 56.00, 2025: 57.00},
    "IDR": {2020: 14582, 2021: 14308, 2022: 14850, 2023: 15237, 2024: 15700, 2025: 16000},
    "KES": {2020: 106.5, 2021: 109.6, 2022: 117.9, 2023: 139.3, 2024: 153.0, 2025: 155.0},
    "NGN": {2020: 381, 2021: 412, 2022: 426, 2023: 757, 2024: 1500, 2025: 1550},
    "JPY": {2020: 106.8, 2021: 109.8, 2022: 131.5, 2023: 140.5, 2024: 151.0, 2025: 148.0},
    "CNY": {2020: 6.900, 2021: 6.449, 2022: 6.730, 2023: 7.084, 2024: 7.200, 2025: 7.250},
    "USD": {2020: 1.0, 2021: 1.0, 2022: 1.0, 2023: 1.0, 2024: 1.0, 2025: 1.0},
}

# NOTE: These are approximate annual averages for Phase 1.
# Replace with actual FRED/ECB data in Phase 2.
STATIC_FX_RATES_AS_OF = "2025-03-01"


def get_fx_rate(currency: str, obs_date: Optional[date] = None) -> Optional[float]:
    """
    Get FX rate (local currency per 1 USD) for a given currency and date.

    Args:
        currency: ISO 4217 currency code
        obs_date: Date for rate lookup (uses year for static rates)

    Returns:
        FX rate or None if currency not found
    """
    if currency == "USD":
        return 1.0

    currency = currency.upper()
    if currency not in STATIC_FX_RATES:
        logger.warning(f"No FX rate available for currency {currency}")
        return None

    year = obs_date.year if obs_date else 2025
    rates = STATIC_FX_RATES[currency]

    # Use exact year if available, otherwise nearest available year
    if year in rates:
        return rates[year]

    available_years = sorted(rates.keys())
    if year < available_years[0]:
        return rates[available_years[0]]
    if year > available_years[-1]:
        return rates[available_years[-1]]

    return None


def convert_to_usd(amount: float, currency: str, obs_date: Optional[date] = None) -> Optional[float]:
    """Convert an amount from local currency to USD."""
    rate = get_fx_rate(currency, obs_date)
    if rate is None:
        return None
    return amount / rate
