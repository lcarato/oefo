"""
Tests for controlled vocabularies and enumerations.

Verifies:
- All enum values exist and are valid
- String values are properly defined
- Validation functions work correctly
- taxonomy.py is the single source of truth (models.py re-exports)
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

    def test_source_types_same_class(self):
        """taxonomy and models should export the same enum class."""
        from oefo.models import SourceType as ST_models
        from oefo.config.taxonomy import SourceType as ST_taxonomy

        assert ST_models is ST_taxonomy

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

    def test_new_scale_values(self):
        """All spec-required scale values should be valid."""
        from oefo.models import Scale

        assert Scale.UTILITY_SCALE.value == "utility_scale"
        assert Scale.COMMERCIAL_INDUSTRIAL.value == "commercial_industrial"
        assert Scale.DISTRIBUTED_RESIDENTIAL.value == "distributed_residential"
        assert Scale.PORTFOLIO.value == "portfolio"
        assert Scale.MEGA_PROJECT.value == "mega_project"
        assert Scale.REGULATED_ASSET.value == "regulated_asset"
        assert Scale.PILOT_DEMONSTRATION.value == "pilot_demonstration"

    def test_scale_from_taxonomy(self):
        """Test Scale enum from taxonomy module matches models."""
        from oefo.config.taxonomy import Scale

        assert Scale.UTILITY_SCALE.value == "utility_scale"
        assert Scale.COMMERCIAL_INDUSTRIAL.value == "commercial_industrial"
        assert Scale.DISTRIBUTED_RESIDENTIAL.value == "distributed_residential"

    def test_scale_enumeration(self):
        """Test that all Scale enum values are enumerable."""
        from oefo.models import Scale

        all_scales = list(Scale)
        assert len(all_scales) == 7

    def test_old_scale_values_removed(self):
        """Old scale values should no longer exist."""
        from oefo.models import Scale

        with pytest.raises(ValueError):
            Scale("utility")
        with pytest.raises(ValueError):
            Scale("commercial")
        with pytest.raises(ValueError):
            Scale("residential")

    def test_scale_same_class(self):
        """taxonomy and models should export the same Scale class."""
        from oefo.models import Scale as S_models
        from oefo.config.taxonomy import Scale as S_taxonomy

        assert S_models is S_taxonomy


class TestExtractionTierEnum:
    """Test ExtractionTier enumeration."""

    def test_extraction_tiers(self):
        """Test ExtractionTier enum values including new Tier 4."""
        from oefo.models import ExtractionTier

        assert ExtractionTier.TIER_1.value == "tier_1"
        assert ExtractionTier.TIER_2.value == "tier_2"
        assert ExtractionTier.TIER_3.value == "tier_3"
        assert ExtractionTier.TIER_4.value == "tier_4"

    def test_extraction_tiers_from_taxonomy(self):
        """Test ExtractionTier enum from taxonomy module."""
        from oefo.config.taxonomy import ExtractionTier

        assert ExtractionTier.TIER_1.value == "tier_1"
        assert ExtractionTier.TIER_2.value == "tier_2"
        assert ExtractionTier.TIER_3.value == "tier_3"
        assert ExtractionTier.TIER_4.value == "tier_4"

    def test_extraction_tiers_enumeration(self):
        """Test that all ExtractionTier enum values are enumerable."""
        from oefo.models import ExtractionTier

        all_tiers = list(ExtractionTier)
        assert len(all_tiers) == 4


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
        """Test DebtType enum values including new seniority-based values."""
        from oefo.models import DebtType

        # Existing instrument types
        assert DebtType.BANK_LOAN.value == "bank_loan"
        assert DebtType.BOND.value == "bond"
        assert DebtType.CONVERTIBLE.value == "convertible"
        assert DebtType.CREDIT_LINE.value == "credit_line"
        assert DebtType.EQUIPMENT_FINANCING.value == "equipment_financing"
        assert DebtType.MEZZANINE.value == "mezzanine"
        assert DebtType.SUPPLIER_CREDIT.value == "supplier_credit"
        # New seniority-based values
        assert DebtType.SENIOR.value == "senior"
        assert DebtType.SUBORDINATED.value == "subordinated"
        assert DebtType.CONCESSIONAL.value == "concessional"

    def test_new_debt_type_values(self):
        """All spec-required debt type values should be valid."""
        from oefo.models import DebtType

        for val in ["senior", "subordinated", "mezzanine", "bond", "concessional"]:
            assert DebtType(val)  # Should not raise

    def test_debt_types_enumeration(self):
        """Test that all DebtType enum values are enumerable."""
        from oefo.models import DebtType

        all_types = list(DebtType)
        assert len(all_types) == 10


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
        """Test scale validation function with new values."""
        from oefo.config.taxonomy import validate_scale

        assert validate_scale("utility_scale") is True
        assert validate_scale("commercial_industrial") is True
        assert validate_scale("invalid_scale") is False
        # Old values should be invalid
        assert validate_scale("utility") is False
        assert validate_scale("commercial") is False


class TestValueChainPositionEnum:
    """Test ValueChainPosition enumeration."""

    def test_value_chain_positions(self):
        """Test ValueChainPosition enum with spec-compliant values."""
        from oefo.models import ValueChainPosition

        assert ValueChainPosition.GENERATION.value == "generation"
        assert ValueChainPosition.FUEL_PRODUCTION.value == "fuel_production"
        assert ValueChainPosition.FUEL_TRANSPORT.value == "fuel_transport"
        assert ValueChainPosition.FUEL_STORAGE.value == "fuel_storage"
        assert ValueChainPosition.ELECTRICITY_TRANSMISSION.value == "electricity_transmission"
        assert ValueChainPosition.ELECTRICITY_DISTRIBUTION.value == "electricity_distribution"
        assert ValueChainPosition.ELECTRICITY_STORAGE.value == "electricity_storage"
        assert ValueChainPosition.END_USE_EFFICIENCY.value == "end_use_efficiency"
        assert ValueChainPosition.END_USE_TRANSPORT.value == "end_use_transport"
        assert ValueChainPosition.CARBON_MANAGEMENT.value == "carbon_management"

    def test_value_chain_enumeration(self):
        """Test that all ValueChainPosition values are enumerable."""
        from oefo.models import ValueChainPosition

        all_positions = list(ValueChainPosition)
        assert len(all_positions) == 10

    def test_old_value_chain_values_removed(self):
        """Old value chain values should no longer exist."""
        from oefo.models import ValueChainPosition

        with pytest.raises(ValueError):
            ValueChainPosition("transmission")
        with pytest.raises(ValueError):
            ValueChainPosition("storage")
        with pytest.raises(ValueError):
            ValueChainPosition("integration")


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
        """Test ProjectStatus enum with spec-compliant values."""
        from oefo.models import ProjectStatus

        assert ProjectStatus.OPERATING.value == "operating"
        assert ProjectStatus.CONSTRUCTION.value == "construction"
        assert ProjectStatus.FINANCIAL_CLOSE.value == "financial_close"
        assert ProjectStatus.DEVELOPMENT.value == "development"
        assert ProjectStatus.DECOMMISSIONING.value == "decommissioning"

    def test_project_status_enumeration(self):
        """Test that all ProjectStatus values are enumerable."""
        from oefo.models import ProjectStatus

        all_statuses = list(ProjectStatus)
        assert len(all_statuses) == 5

    def test_old_project_status_values_removed(self):
        """Old project status values should no longer exist."""
        from oefo.models import ProjectStatus

        with pytest.raises(ValueError):
            ProjectStatus("operational")
        with pytest.raises(ValueError):
            ProjectStatus("retired")
        with pytest.raises(ValueError):
            ProjectStatus("planned")


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


class TestDamodaranTechnologyMap:
    """Test DAMODARAN_TECHNOLOGY_MAP in taxonomy."""

    def test_map_exists_and_nonempty(self):
        from oefo.config.taxonomy import DAMODARAN_TECHNOLOGY_MAP

        assert len(DAMODARAN_TECHNOLOGY_MAP) > 50

    def test_map_covers_major_technologies(self):
        from oefo.config.taxonomy import DAMODARAN_TECHNOLOGY_MAP

        assert "solar_pv" in DAMODARAN_TECHNOLOGY_MAP
        assert "wind_onshore" in DAMODARAN_TECHNOLOGY_MAP
        assert "gas_ccgt" in DAMODARAN_TECHNOLOGY_MAP
        assert "coal_power" in DAMODARAN_TECHNOLOGY_MAP
        assert "nuclear_large" in DAMODARAN_TECHNOLOGY_MAP

    def test_map_values_are_valid_sectors(self):
        from oefo.config.taxonomy import DAMODARAN_TECHNOLOGY_MAP

        valid_sectors = {
            "Green & Renewable Energy",
            "Oil/Gas (Production)",
            "Oil/Gas (Distribution)",
            "Electric Utility (General)",
            "Power",
            "Coal & Related Energy",
            "Nuclear",
        }
        for tech, sector in DAMODARAN_TECHNOLOGY_MAP.items():
            assert sector in valid_sectors, f"{tech} maps to unknown sector '{sector}'"


class TestLeverageBasisEnum:
    """Test LeverageBasis enumeration."""

    def test_leverage_basis_values(self):
        from oefo.config.taxonomy import LeverageBasis

        assert LeverageBasis.PROJECT_LEVEL.value == "project_level"
        assert LeverageBasis.CORPORATE_LEVEL.value == "corporate_level"
