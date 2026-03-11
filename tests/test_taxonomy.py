"""
Tests for controlled vocabularies and enumerations.

Verifies:
- All enum values exist and are valid
- String values are properly defined
- Validation functions work correctly
"""

import pytest


class TestSourceTypeEnum:
    """Test SourceType enumeration."""

    def test_source_types_from_models(self):
        """Test SourceType enum from models module."""
        from oefo.models import SourceType

        assert SourceType.DFI_DISCLOSURE.value == "DFI_disclosure"
        assert SourceType.CORPORATE_FILING.value == "corporate_filing"
        assert SourceType.BOND_PROSPECTUS.value == "bond_prospectus"
        assert SourceType.REGULATORY_FILING.value == "regulatory_filing"

    def test_source_types_from_taxonomy(self):
        """Test SourceType enum from taxonomy module."""
        from oefo.config.taxonomy import SourceType

        assert SourceType.DFI_DISCLOSURE.value == "DFI_disclosure"
        assert SourceType.CORPORATE_FILING.value == "corporate_filing"
        assert SourceType.BOND_PROSPECTUS.value == "bond_prospectus"
        assert SourceType.REGULATORY_FILING.value == "regulatory_filing"

    def test_source_types_enumeration(self):
        """Test that all SourceType enum values are enumerable."""
        from oefo.models import SourceType

        all_types = list(SourceType)
        assert len(all_types) == 4
        assert all(hasattr(t, "value") for t in all_types)


class TestConfidenceLevelEnum:
    """Test ConfidenceLevel enumeration."""

    def test_confidence_levels(self):
        """Test ConfidenceLevel enum values."""
        from oefo.models import ConfidenceLevel

        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"

    def test_confidence_levels_enumeration(self):
        """Test that all ConfidenceLevel enum values are enumerable."""
        from oefo.models import ConfidenceLevel

        all_levels = list(ConfidenceLevel)
        assert len(all_levels) == 3


class TestScaleEnum:
    """Test Scale enumeration."""

    def test_scale_values_models(self):
        """Test Scale enum from models module."""
        from oefo.models import Scale

        assert Scale.UTILITY.value == "utility"
        assert Scale.COMMERCIAL.value == "commercial"
        assert Scale.INDUSTRIAL.value == "industrial"
        assert Scale.RESIDENTIAL.value == "residential"
        assert Scale.COMMUNITY.value == "community"
        assert Scale.MICRO.value == "micro"
        assert Scale.DISTRIBUTED.value == "distributed"

    def test_scale_values_taxonomy(self):
        """Test Scale enum from taxonomy module."""
        from oefo.config.taxonomy import Scale

        assert Scale.UTILITY.value == "utility"
        assert Scale.COMMERCIAL.value == "commercial"
        assert Scale.INDUSTRIAL.value == "industrial"

    def test_scale_enumeration(self):
        """Test that all Scale enum values are enumerable."""
        from oefo.models import Scale

        all_scales = list(Scale)
        assert len(all_scales) == 7


class TestExtractionTierEnum:
    """Test ExtractionTier enumeration."""

    def test_extraction_tiers_models(self):
        """Test ExtractionTier enum from models module."""
        from oefo.models import ExtractionTier

        assert ExtractionTier.TIER_1.value == "tier_1"
        assert ExtractionTier.TIER_2.value == "tier_2"
        assert ExtractionTier.TIER_3.value == "tier_3"

    def test_extraction_tiers_taxonomy(self):
        """Test ExtractionTier enum from taxonomy module."""
        from oefo.config.taxonomy import ExtractionTier

        assert ExtractionTier.TIER_1.value == "tier_1"
        assert ExtractionTier.TIER_2.value == "tier_2"
        assert ExtractionTier.TIER_3.value == "tier_3"

    def test_extraction_tiers_enumeration(self):
        """Test that all ExtractionTier enum values are enumerable."""
        from oefo.models import ExtractionTier

        all_tiers = list(ExtractionTier)
        assert len(all_tiers) == 3


class TestQCStatusEnum:
    """Test QCStatus enumeration."""

    def test_qc_status_values_models(self):
        """Test QCStatus enum from models module."""
        from oefo.models import QCStatus

        assert QCStatus.PASSED.value == "passed"
        assert QCStatus.FAILED.value == "failed"
        assert QCStatus.FLAGGED.value == "flagged"
        assert QCStatus.PENDING_REVIEW.value == "pending_review"

    def test_qc_status_values_taxonomy(self):
        """Test QCStatus enum from taxonomy module."""
        from oefo.config.taxonomy import QCStatus

        assert QCStatus.PASSED.value == "passed"
        assert QCStatus.FAILED.value == "failed"
        assert QCStatus.FLAGGED.value == "flagged"
        assert QCStatus.PENDING_REVIEW.value == "pending_review"

    def test_qc_status_enumeration(self):
        """Test that all QCStatus enum values are enumerable."""
        from oefo.models import QCStatus

        all_statuses = list(QCStatus)
        assert len(all_statuses) == 4


class TestDebtTypeEnum:
    """Test DebtType enumeration."""

    def test_debt_types(self):
        """Test DebtType enum values."""
        from oefo.models import DebtType

        assert DebtType.BANK_LOAN.value == "bank_loan"
        assert DebtType.BOND.value == "bond"
        assert DebtType.CONVERTIBLE.value == "convertible"
        assert DebtType.CREDIT_LINE.value == "credit_line"
        assert DebtType.EQUIPMENT_FINANCING.value == "equipment_financing"
        assert DebtType.MEZZANINE.value == "mezzanine"
        assert DebtType.SUPPLIER_CREDIT.value == "supplier_credit"

    def test_debt_types_enumeration(self):
        """Test that all DebtType enum values are enumerable."""
        from oefo.models import DebtType

        all_types = list(DebtType)
        assert len(all_types) == 7


class TestTechnologyEnum:
    """Test Technology enumeration from taxonomy."""

    def test_technology_values_exist(self):
        """Test that Technology enum has expected values."""
        from oefo.config.taxonomy import Technology

        # Test a sample of technologies
        assert Technology.SOLAR_PV.value == "solar_pv"
        assert Technology.WIND_ONSHORE.value == "wind_onshore"
        assert Technology.HYDRO_LARGE.value == "hydro_large"
        assert Technology.BIOMASS_POWER.value == "biomass_power"

    def test_technology_enumeration(self):
        """Test that Technology enum is enumerable."""
        from oefo.config.taxonomy import Technology

        all_technologies = list(Technology)
        assert len(all_technologies) > 50  # Should have ~55 categories

    def test_validate_technology_function(self):
        """Test technology validation function."""
        from oefo.config.taxonomy import validate_technology

        assert validate_technology("solar_pv") is True
        assert validate_technology("wind_onshore") is True
        assert validate_technology("invalid_tech") is False


class TestScaleValidation:
    """Test scale validation functions."""

    def test_validate_scale_function(self):
        """Test scale validation function."""
        from oefo.config.taxonomy import validate_scale

        assert validate_scale("utility") is True
        assert validate_scale("commercial") is True
        assert validate_scale("invalid_scale") is False


class TestValueChainPositionEnum:
    """Test ValueChainPosition enumeration."""

    def test_value_chain_positions(self):
        """Test ValueChainPosition enum values."""
        from oefo.models import ValueChainPosition

        assert ValueChainPosition.GENERATION.value == "generation"
        assert ValueChainPosition.TRANSMISSION.value == "transmission"
        assert ValueChainPosition.DISTRIBUTION.value == "distribution"
        assert ValueChainPosition.STORAGE.value == "storage"

    def test_value_chain_enumeration(self):
        """Test that all ValueChainPosition values are enumerable."""
        from oefo.models import ValueChainPosition

        all_positions = list(ValueChainPosition)
        assert len(all_positions) == 10


class TestTraceabilityLevelEnum:
    """Test TraceabilityLevel enumeration."""

    def test_traceability_levels(self):
        """Test TraceabilityLevel enum values."""
        from oefo.models import TraceabilityLevel

        assert TraceabilityLevel.FULL.value == "full"
        assert TraceabilityLevel.PARTIAL.value == "partial"
        assert TraceabilityLevel.MINIMAL.value == "minimal"

    def test_traceability_enumeration(self):
        """Test that all TraceabilityLevel values are enumerable."""
        from oefo.models import TraceabilityLevel

        all_levels = list(TraceabilityLevel)
        assert len(all_levels) == 3


class TestProjectStatusEnum:
    """Test ProjectStatus enumeration."""

    def test_project_status_values(self):
        """Test ProjectStatus enum values."""
        from oefo.models import ProjectStatus

        all_statuses = list(ProjectStatus)
        assert len(all_statuses) == 5
        assert any(s.value == "operational" for s in all_statuses)
        assert any(s.value == "construction" for s in all_statuses)


class TestDocumentStatusEnum:
    """Test DocumentStatus enumeration."""

    def test_document_status_values(self):
        """Test DocumentStatus enum values."""
        from oefo.models import DocumentStatus

        assert DocumentStatus.PENDING.value == "pending"
        assert DocumentStatus.DOWNLOADING.value == "downloading"
        assert DocumentStatus.DOWNLOADED.value == "downloaded"
        assert DocumentStatus.FAILED.value == "failed"

    def test_document_status_enumeration(self):
        """Test that all DocumentStatus values are enumerable."""
        from oefo.models import DocumentStatus

        all_statuses = list(DocumentStatus)
        assert len(all_statuses) == 5
