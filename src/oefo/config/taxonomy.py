"""
Controlled Vocabularies for the OEFO (Open Energy Finance Observatory) Project

This module defines all enumerated types and controlled vocabularies used across
the OEFO data pipeline. All enums use string values for proper JSON serialization
and downstream compatibility.

Categories include:
- Technology classifications (L2 granularity)
- Project scale and value chain positioning
- Project and extraction metadata
- Financial parameters and debt/equity terms
- Quality control and confidence metrics
"""

from enum import Enum


class Technology(Enum):
    """
    Technology L2 classification (~55 categories).
    Covers generation, fuel cycle, storage, demand-side, transmission/distribution,
    and carbon management technologies.
    """

    # Solar
    SOLAR_PV = "solar_pv"
    SOLAR_CSP = "solar_csp"
    SOLAR_THERMAL = "solar_thermal"

    # Wind
    WIND_ONSHORE = "wind_onshore"
    WIND_OFFSHORE_FIXED = "wind_offshore_fixed"
    WIND_OFFSHORE_FLOATING = "wind_offshore_floating"
    WIND_DISTRIBUTED = "wind_distributed"

    # Hydropower
    HYDRO_LARGE = "hydro_large"
    HYDRO_SMALL = "hydro_small"
    HYDRO_RUN_OF_RIVER = "hydro_run_of_river"

    # Biomass and Biogas
    BIOMASS_POWER = "biomass_power"
    BIOGAS = "biogas"
    BIOMETHANE = "biomethane"
    WASTE_TO_ENERGY = "waste_to_energy"
    BIOFUELS = "biofuels"

    # Geothermal
    GEOTHERMAL_POWER = "geothermal_power"
    GEOTHERMAL_DIRECT_USE = "geothermal_direct_use"

    # Marine
    TIDAL = "tidal"
    WAVE = "wave"

    # Gas
    GAS_CCGT = "gas_ccgt"
    GAS_PEAKER = "gas_peaker"
    GAS_COGENERATION = "gas_cogeneration"
    LNG_LIQUEFACTION = "lng_liquefaction"
    LNG_REGASIFICATION = "lng_regasification"
    GAS_DISTRIBUTION = "gas_distribution"
    GAS_MIDSTREAM = "gas_midstream"

    # Oil
    OIL_UPSTREAM_CONVENTIONAL = "oil_upstream_conventional"
    OIL_UPSTREAM_UNCONVENTIONAL = "oil_upstream_unconventional"
    OIL_MIDSTREAM = "oil_midstream"
    OIL_DOWNSTREAM = "oil_downstream"

    # Coal
    COAL_POWER = "coal_power"
    COAL_MINING = "coal_mining"

    # Nuclear
    NUCLEAR_LARGE = "nuclear_large"
    NUCLEAR_SMR = "nuclear_smr"
    NUCLEAR_FUEL_CYCLE = "nuclear_fuel_cycle"

    # Storage
    STORAGE_BATTERY_GRID = "storage_battery_grid"
    STORAGE_BATTERY_BTM = "storage_battery_btm"
    STORAGE_PUMPED_HYDRO = "storage_pumped_hydro"
    STORAGE_CAES = "storage_caes"
    STORAGE_THERMAL = "storage_thermal"
    STORAGE_MECHANICAL = "storage_mechanical"

    # Hydrogen and Fuels
    HYDROGEN_GREEN = "hydrogen_green"
    HYDROGEN_BLUE = "hydrogen_blue"
    HYDROGEN_PINK = "hydrogen_pink"
    HYDROGEN_INFRASTRUCTURE = "hydrogen_infrastructure"
    AMMONIA_GREEN = "ammonia_green"
    E_FUELS = "e_fuels"

    # Carbon Management
    CCS_POWER = "ccs_power"
    CCS_INDUSTRIAL = "ccs_industrial"
    CCS_DAC = "ccs_dac"
    CO2_TRANSPORT_STORAGE = "co2_transport_storage"

    # Electricity Infrastructure
    TRANSMISSION = "transmission"
    DISTRIBUTION = "distribution"

    # Electrification
    EV_CHARGING = "ev_charging"
    MICROGRIDS = "microgrids"

    # Efficiency
    EFFICIENCY_INDUSTRIAL = "efficiency_industrial"
    EFFICIENCY_BUILDINGS = "efficiency_buildings"
    DISTRICT_ENERGY = "district_energy"


class Scale(Enum):
    """Project or asset scale classification.

    Values aligned with models.py Scale enum for consistency.
    """
    UTILITY = "utility"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    RESIDENTIAL = "residential"
    COMMUNITY = "community"
    MICRO = "micro"
    DISTRIBUTED = "distributed"


class ValueChainPosition(Enum):
    """Position in the energy value chain."""
    GENERATION = "generation"
    FUEL_PRODUCTION = "fuel_production"
    FUEL_TRANSPORT = "fuel_transport"
    FUEL_STORAGE = "fuel_storage"
    ELECTRICITY_TRANSMISSION = "electricity_transmission"
    ELECTRICITY_DISTRIBUTION = "electricity_distribution"
    ELECTRICITY_STORAGE = "electricity_storage"
    END_USE_EFFICIENCY = "end_use_efficiency"
    END_USE_TRANSPORT = "end_use_transport"
    CARBON_MANAGEMENT = "carbon_management"


class ProjectStatus(Enum):
    """Project development and operational status."""
    OPERATING = "operating"
    CONSTRUCTION = "construction"
    FINANCIAL_CLOSE = "financial_close"
    DEVELOPMENT = "development"
    DECOMMISSIONING = "decommissioning"


class SourceType(Enum):
    """Classification of data source document type."""
    DFI_DISCLOSURE = "DFI_disclosure"
    CORPORATE_FILING = "corporate_filing"
    BOND_PROSPECTUS = "bond_prospectus"
    REGULATORY_FILING = "regulatory_filing"


class ExtractionMethod(Enum):
    """Method used to extract data from source document."""
    MANUAL = "manual"
    AUTOMATED_HTML = "automated_html"
    AUTOMATED_PDF = "automated_pdf"
    LLM_ASSISTED = "llm_assisted"


class ExtractionTier(Enum):
    """Processing tier used for extraction (increasing complexity/cost).

    Values aligned with models.py ExtractionTier enum.
    """
    TIER_1 = "tier_1"  # High quality, direct text extraction
    TIER_2 = "tier_2"  # Moderate quality, OCR-based
    TIER_3 = "tier_3"  # Lower quality, vision-based inference


class QCStatus(Enum):
    """Quality control review status of extracted data.

    Values aligned with models.py QCStatus enum.
    """
    PASSED = "passed"
    FAILED = "failed"
    FLAGGED = "flagged"
    PENDING_REVIEW = "pending_review"


class ConfidenceLevel(Enum):
    """Confidence in the accuracy/specificity of a data point."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DebtType(Enum):
    """Classification of debt instrument by type.

    Values aligned with models.py DebtType enum.
    """
    BANK_LOAN = "bank_loan"
    BOND = "bond"
    CONVERTIBLE = "convertible"
    CREDIT_LINE = "credit_line"
    EQUIPMENT_FINANCING = "equipment_financing"
    MEZZANINE = "mezzanine"
    SUPPLIER_CREDIT = "supplier_credit"


class KDRateBenchmark(Enum):
    """Benchmark rate for floating-rate debt."""
    SOFR = "SOFR"
    EURIBOR = "EURIBOR"
    LIBOR = "LIBOR"
    FIXED = "fixed"
    LOCAL_REFERENCE_RATE = "local_reference_rate"


class KEEstimationMethod(Enum):
    """Method by which cost of equity (Ke) was determined or derived."""
    REGULATORY_ALLOWED = "regulatory_allowed"
    CAPM_DERIVED = "capm_derived"
    DISCLOSED = "disclosed"
    IMPLIED = "implied"


class LeverageBasis(Enum):
    """Level at which leverage is measured/calculated."""
    PROJECT_LEVEL = "project_level"
    CORPORATE_LEVEL = "corporate_level"


# Type aliases for convenience
TechnologyValue = str
ScaleValue = str
ValueChainValue = str
ProjectStatusValue = str
SourceTypeValue = str
ExtractionMethodValue = str
ExtractionTierValue = str
QCStatusValue = str
ConfidenceLevelValue = str
DebtTypeValue = str
KDRateBenchmarkValue = str
KEEstimationMethodValue = str
LeverageBasisValue = str


def get_technology_value(tech: Technology) -> str:
    """Extract string value from Technology enum."""
    return tech.value if isinstance(tech, Technology) else tech


def get_scale_value(scale: Scale) -> str:
    """Extract string value from Scale enum."""
    return scale.value if isinstance(scale, Scale) else scale


def validate_technology(value: str) -> bool:
    """Check if a value is a valid Technology."""
    try:
        Technology(value)
        return True
    except ValueError:
        return False


def validate_scale(value: str) -> bool:
    """Check if a value is a valid Scale."""
    try:
        Scale(value)
        return True
    except ValueError:
        return False
