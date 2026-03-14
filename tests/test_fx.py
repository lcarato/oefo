"""
Tests for FX conversion utility.
"""

import pytest
from datetime import date

from oefo.utils.fx import get_fx_rate, convert_to_usd


class TestGetFXRate:
    """Tests for get_fx_rate function."""

    def test_usd_identity(self):
        """USD to USD should always return 1.0."""
        assert get_fx_rate("USD") == 1.0
        assert get_fx_rate("USD", date(2023, 6, 15)) == 1.0

    def test_known_currency_rates(self):
        """Known currencies should return approximate rates."""
        rate = get_fx_rate("EUR", date(2023, 6, 15))
        assert rate is not None
        assert 0.8 < rate < 1.1  # EUR/USD should be near parity

        rate = get_fx_rate("BRL", date(2023, 6, 15))
        assert rate is not None
        assert 4.0 < rate < 6.0  # BRL/USD should be in this range

    def test_unknown_currency(self):
        """Unknown currency should return None."""
        assert get_fx_rate("XYZ") is None

    def test_year_fallback_future(self):
        """Year beyond available data should use latest year."""
        rate = get_fx_rate("EUR", date(2030, 1, 1))
        assert rate is not None  # Should fall back to 2025

    def test_year_fallback_past(self):
        """Year before available data should use earliest year."""
        rate = get_fx_rate("EUR", date(2015, 1, 1))
        assert rate is not None  # Should fall back to 2020

    def test_case_insensitive(self):
        """Currency codes should be case-insensitive."""
        assert get_fx_rate("eur") is not None
        assert get_fx_rate("Eur") is not None

    def test_no_date_defaults_to_2025(self):
        """No date should default to 2025 rate."""
        rate = get_fx_rate("EUR")
        assert rate is not None
        assert rate == get_fx_rate("EUR", date(2025, 1, 1))


class TestConvertToUSD:
    """Tests for convert_to_usd function."""

    def test_usd_no_conversion(self):
        """USD amounts should pass through unchanged."""
        assert convert_to_usd(100.0, "USD") == 100.0

    def test_known_conversion(self):
        """Conversion with known rate should work correctly."""
        # 100 EUR at ~0.92 EUR/USD = ~108.7 USD
        result = convert_to_usd(100.0, "EUR", date(2025, 1, 1))
        assert result is not None
        assert 100 < result < 120  # Should be more than 100 (EUR stronger than USD)

    def test_unknown_currency_returns_none(self):
        """Unknown currency should return None."""
        assert convert_to_usd(100.0, "XYZ") is None
