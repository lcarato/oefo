"""Tests for OEFO data models."""

import pytest
from datetime import date, datetime

from oefo.models import (
    Observation,
    ExtractionResult,
    QCResult,
    RawDocument,
    ProvenanceChain,
    SourceType,
    ConfidenceLevel,
    Scale,
    ExtractionTier,
    QCStatus,
    TraceabilityLevel,
)


class TestObservation:
    """Tests for the Observation model."""

    def _make_observation(self, **overrides):
        """Helper to create a valid Observation with defaults."""
        defaults = {
            "observation_id": "test-001",
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

    def test_valid_observation(self):
        obs = self._make_observation()
        assert obs.observation_id == "test-001"
        assert obs.country == "BRA"

    def test_kd_nominal_percentage_points(self):
        """kd_nominal should accept percentage points (e.g. 5.5 for 5.5%)."""
        obs = self._make_observation(kd_nominal=5.5)
        assert obs.kd_nominal == 5.5

    def test_kd_nominal_rejects_over_100(self):
        with pytest.raises(Exception):
            self._make_observation(kd_nominal=150)

    def test_leverage_sum_validation(self):
        """Leverage debt + equity should sum to ~100%."""
        obs = self._make_observation(leverage_debt_pct=70, leverage_equity_pct=30)
        assert obs.leverage_debt_pct == 70

    def test_leverage_sum_fails_if_not_100(self):
        with pytest.raises(Exception):
            self._make_observation(leverage_debt_pct=80, leverage_equity_pct=80)

    def test_country_code_validation(self):
        with pytest.raises(Exception):
            self._make_observation(country="brazil")

    def test_traceability_full(self):
        obs = self._make_observation(
            source_document_url="https://example.com/doc.pdf",
            source_page_number=5,
            source_quote="WACC of 8.5%",
        )
        assert obs.traceability_level == TraceabilityLevel.FULL

    def test_traceability_minimal(self):
        obs = self._make_observation()
        assert obs.traceability_level == TraceabilityLevel.MINIMAL


class TestProvenanceChain:
    """Tests for the ProvenanceChain model."""

    def test_auto_traceability_full(self):
        chain = ProvenanceChain(
            source_document_id="doc-001",
            source_document_url="https://example.com/doc.pdf",
            source_page_numbers=[1, 2],
            source_quotes=["WACC is 8.5%"],
        )
        assert chain.traceability_level == TraceabilityLevel.FULL

    def test_auto_traceability_partial(self):
        chain = ProvenanceChain(
            source_document_id="doc-001",
            source_document_url="https://example.com/doc.pdf",
            source_page_numbers=[1],
        )
        assert chain.traceability_level == TraceabilityLevel.PARTIAL
