"""
Tests for QC rules, WACC derivation, and concessional finance detection.
"""

import pytest
from datetime import date

from oefo.models import Observation, SourceType, ConfidenceLevel
from oefo.utils.wacc import derive_wacc
from oefo.qc.rules import RuleBasedQC


def _make_obs(**overrides):
    """Helper to create a valid Observation with defaults."""
    defaults = {
        "observation_id": "test-qc-001",
        "source_type": SourceType.DFI_DISCLOSURE,
        "source_institution": "IFC",
        "extraction_date": date(2024, 1, 1),
        "extraction_method": "llm",
        "confidence_level": ConfidenceLevel.HIGH,
        "project_or_entity_name": "Test Solar Project",
        "country": "BRA",
        "technology_l2": "solar_pv",
        "year_of_observation": 2024,
    }
    defaults.update(overrides)
    return Observation(**defaults)


class TestWACCDerivation:
    """Tests for WACC derivation utility."""

    def test_wacc_derivation_with_all_components(self):
        """WACC should be derived when ke, kd, leverage, and tax are all present."""
        obs = _make_obs(
            ke_nominal=10.0,
            kd_nominal=5.0,
            leverage_debt_pct=70.0,
            leverage_equity_pct=30.0,
            tax_rate_applied=0.25,
        )
        wacc, wacc_real, notes = derive_wacc(obs)
        # WACC = 10% * 0.3 + 5% * (1-0.25) * 0.7 = 3.0 + 2.625 = 5.625%
        assert wacc is not None
        assert abs(wacc - 5.625) < 0.01

    def test_wacc_not_derived_without_ke(self):
        """WACC should NOT be derived when ke is missing (spec: missing data stays missing)."""
        obs = _make_obs(
            kd_nominal=5.0,
            leverage_debt_pct=70.0,
            leverage_equity_pct=30.0,
        )
        wacc, _, notes = derive_wacc(obs)
        assert wacc is None
        assert "missing" in notes.lower() or "not observed" in notes.lower()

    def test_wacc_not_derived_without_leverage(self):
        """WACC should NOT be derived when leverage is missing."""
        obs = _make_obs(
            ke_nominal=10.0,
            kd_nominal=5.0,
        )
        wacc, _, notes = derive_wacc(obs)
        assert wacc is None
        assert "insufficient" in notes.lower()

    def test_wacc_default_tax_rate(self):
        """When tax_rate_applied is None, should assume 25% and note it."""
        obs = _make_obs(
            ke_nominal=10.0,
            kd_nominal=5.0,
            leverage_debt_pct=70.0,
            leverage_equity_pct=30.0,
            # tax_rate_applied is None
        )
        wacc, _, notes = derive_wacc(obs)
        assert wacc is not None
        assert "25%" in notes or "assumed" in notes.lower()

    def test_real_wacc_derivation(self):
        """Real WACC should be derived when real components are available."""
        obs = _make_obs(
            ke_nominal=10.0,
            ke_real=7.0,
            kd_nominal=5.0,
            kd_real=2.0,
            leverage_debt_pct=70.0,
            leverage_equity_pct=30.0,
            tax_rate_applied=0.25,
        )
        wacc_nom, wacc_real, notes = derive_wacc(obs)
        assert wacc_nom is not None
        assert wacc_real is not None
        assert "real" in notes.lower()


class TestConcessionalDetection:
    """Tests for concessional finance detection in QC rules."""

    def test_concessional_flag_below_risk_free(self):
        """DFI loans with kd below sovereign yield should be flagged as likely concessional."""
        obs = _make_obs(
            kd_nominal=3.0,  # Below Brazil's ~12% RFR
            source_type=SourceType.DFI_DISCLOSURE,
            country="BRA",
        )
        qc = RuleBasedQC()
        flags = qc.check_concessional(obs)
        assert len(flags) > 0
        assert "concessional" in flags[0].lower()

    def test_no_concessional_flag_for_market_rate(self):
        """Market-rate DFI loans should not be flagged."""
        obs = _make_obs(
            kd_nominal=14.0,  # Above Brazil's ~12% RFR
            source_type=SourceType.DFI_DISCLOSURE,
            country="BRA",
        )
        qc = RuleBasedQC()
        flags = qc.check_concessional(obs)
        assert len(flags) == 0

    def test_no_concessional_flag_for_non_dfi(self):
        """Non-DFI sources should not be flagged for concessional."""
        obs = _make_obs(
            kd_nominal=3.0,
            source_type=SourceType.CORPORATE_FILING,
            country="BRA",
        )
        qc = RuleBasedQC()
        flags = qc.check_concessional(obs)
        assert len(flags) == 0

    def test_no_concessional_flag_unknown_country(self):
        """Countries without RFR data should not be flagged."""
        obs = _make_obs(
            kd_nominal=1.0,
            source_type=SourceType.DFI_DISCLOSURE,
            country="LUX",  # Not in RFR table
        )
        qc = RuleBasedQC()
        flags = qc.check_concessional(obs)
        assert len(flags) == 0


class TestRuleBasedQCEnums:
    """Tests that QC rules work with new enum values."""

    def test_valid_new_scale_values(self):
        """New scale values should pass format validation."""
        from oefo.models import Scale

        obs = _make_obs(scale=Scale.UTILITY_SCALE)
        qc = RuleBasedQC()
        flags = qc.check_format_and_types(obs)
        scale_errors = [f for f in flags if "scale" in f.lower()]
        assert len(scale_errors) == 0

    def test_valid_new_project_status(self):
        """New project status values should pass format validation."""
        from oefo.models import ProjectStatus

        obs = _make_obs(project_status=ProjectStatus.OPERATING)
        qc = RuleBasedQC()
        flags = qc.check_format_and_types(obs)
        status_errors = [f for f in flags if "project_status" in f.lower()]
        assert len(status_errors) == 0
