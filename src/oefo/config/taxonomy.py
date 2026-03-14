"""
Controlled Vocabularies for the OEFO (Open Energy Finance Observatory) Project

This module defines all enumerated types and controlled vocabularies used across
the OEFO data pipeline. All enums use (str, Enum) for proper JSON serialization,
Pydantic v2 compatibility, and downstream use.

Categories include:
- Technology classifications (L2 granularity)
- Project scale and value chain positioning
- Project and extraction metadata
- Financial parameters and debt/equity terms
- Quality control and confidence metrics
"""

from enum import Enum


class Technology(str, Enum):
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


class Scale(str, Enum):
    """Project or asset scale classification.

    Values reflect financing-structure differences, not just physical size.
    Aligned with project strategy spec.
    """
    UTILITY_SCALE = "utility_scale"
    COMMERCIAL_INDUSTRIAL = "commercial_industrial"
    DISTRIBUTED_RESIDENTIAL = "distributed_residential"
    PORTFOLIO = "portfolio"
    MEGA_PROJECT = "mega_project"
    REGULATED_ASSET = "regulated_asset"
    PILOT_DEMONSTRATION = "pilot_demonstration"


class ValueChainPosition(str, Enum):
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


class ProjectStatus(str, Enum):
    """Project development and operational status."""
    OPERATING = "operating"
    CONSTRUCTION = "construction"
    FINANCIAL_CLOSE = "financial_close"
    DEVELOPMENT = "development"
    DECOMMISSIONING = "decommissioning"


class SourceType(str, Enum):
    """Classification of data source document type."""
    DFI_DISCLOSURE = "DFI_disclosure"
    CORPORATE_FILING = "corporate_filing"
    BOND_PROSPECTUS = "bond_prospectus"
    REGULATORY_FILING = "regulatory_filing"


class ExtractionMethod(str, Enum):
    """Method used to extract data from source document."""
    MANUAL = "manual"
    AUTOMATED_HTML = "automated_html"
    AUTOMATED_PDF = "automated_pdf"
    LLM_ASSISTED = "llm_assisted"


class ExtractionTier(str, Enum):
    """Processing tier used for extraction (increasing complexity/cost)."""
    TIER_1 = "tier_1"  # Native text extraction (pdfplumber/pymupdf)
    TIER_2 = "tier_2"  # OCR (Tesseract)
    TIER_3 = "tier_3"  # Vision (Claude Vision API)
    TIER_4 = "tier_4"  # Human-in-the-loop (manual extraction)


class QCStatus(str, Enum):
    """Quality control review status of extracted data."""
    PASSED = "passed"
    FAILED = "failed"
    FLAGGED = "flagged"
    PENDING_REVIEW = "pending_review"


class ConfidenceLevel(str, Enum):
    """Confidence in the accuracy/specificity of a data point."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DebtType(str, Enum):
    """Classification of debt instrument by seniority and type.

    Includes seniority-based categories (senior, subordinated, concessional)
    alongside instrument-type categories per project strategy spec.
    """
    SENIOR = "senior"
    SUBORDINATED = "subordinated"
    MEZZANINE = "mezzanine"
    BOND = "bond"
    CONCESSIONAL = "concessional"
    BANK_LOAN = "bank_loan"
    CONVERTIBLE = "convertible"
    CREDIT_LINE = "credit_line"
    EQUIPMENT_FINANCING = "equipment_financing"
    SUPPLIER_CREDIT = "supplier_credit"


class KDRateBenchmark(str, Enum):
    """Benchmark rate for floating-rate debt."""
    SOFR = "SOFR"
    EURIBOR = "EURIBOR"
    LIBOR = "LIBOR"
    FIXED = "fixed"
    LOCAL_REFERENCE_RATE = "local_reference_rate"


class KEEstimationMethod(str, Enum):
    """Method by which cost of equity (Ke) was determined or derived."""
    REGULATORY_ALLOWED = "regulatory_allowed"
    CAPM_DERIVED = "capm_derived"
    DISCLOSED = "disclosed"
    IMPLIED = "implied"


class LeverageBasis(str, Enum):
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


# =============================================================================
# Damodaran Technology Map
# =============================================================================

# Maps OEFO technology_l2 values to Damodaran sector names
# Used by QC benchmarks layer for cross-checking extracted values
DAMODARAN_TECHNOLOGY_MAP: dict[str, str] = {
    # Solar
    "solar_pv": "Green & Renewable Energy",
    "solar_csp": "Green & Renewable Energy",
    "solar_thermal": "Green & Renewable Energy",
    # Wind
    "wind_onshore": "Green & Renewable Energy",
    "wind_offshore_fixed": "Green & Renewable Energy",
    "wind_offshore_floating": "Green & Renewable Energy",
    "wind_distributed": "Green & Renewable Energy",
    # Hydro
    "hydro_large": "Power",
    "hydro_small": "Green & Renewable Energy",
    "hydro_run_of_river": "Green & Renewable Energy",
    # Bioenergy
    "biomass_power": "Green & Renewable Energy",
    "biogas": "Green & Renewable Energy",
    "biomethane": "Green & Renewable Energy",
    "waste_to_energy": "Green & Renewable Energy",
    "biofuels": "Green & Renewable Energy",
    # Geothermal
    "geothermal_power": "Green & Renewable Energy",
    "geothermal_direct_use": "Green & Renewable Energy",
    # Ocean
    "tidal": "Green & Renewable Energy",
    "wave": "Green & Renewable Energy",
    # Gas
    "gas_ccgt": "Oil/Gas (Production)",
    "gas_peaker": "Oil/Gas (Production)",
    "gas_cogeneration": "Oil/Gas (Production)",
    "lng_liquefaction": "Oil/Gas (Production)",
    "lng_regasification": "Oil/Gas (Distribution)",
    "gas_distribution": "Oil/Gas (Distribution)",
    "gas_midstream": "Oil/Gas (Distribution)",
    # Oil
    "oil_upstream_conventional": "Oil/Gas (Production)",
    "oil_upstream_unconventional": "Oil/Gas (Production)",
    "oil_midstream": "Oil/Gas (Distribution)",
    "oil_downstream": "Oil/Gas (Distribution)",
    # Coal
    "coal_power": "Coal & Related Energy",
    "coal_mining": "Coal & Related Energy",
    # Nuclear
    "nuclear_large": "Nuclear",
    "nuclear_smr": "Nuclear",
    "nuclear_fuel_cycle": "Nuclear",
    # Storage
    "storage_battery_grid": "Green & Renewable Energy",
    "storage_battery_btm": "Green & Renewable Energy",
    "storage_pumped_hydro": "Power",
    "storage_caes": "Green & Renewable Energy",
    "storage_thermal": "Green & Renewable Energy",
    "storage_mechanical": "Green & Renewable Energy",
    # Hydrogen
    "hydrogen_green": "Green & Renewable Energy",
    "hydrogen_blue": "Oil/Gas (Production)",
    "hydrogen_pink": "Nuclear",
    "hydrogen_infrastructure": "Oil/Gas (Distribution)",
    "ammonia_green": "Green & Renewable Energy",
    "e_fuels": "Green & Renewable Energy",
    # CCS
    "ccs_power": "Power",
    "ccs_industrial": "Oil/Gas (Production)",
    "ccs_dac": "Green & Renewable Energy",
    "co2_transport_storage": "Oil/Gas (Distribution)",
    # Grid
    "transmission": "Electric Utility (General)",
    "distribution": "Electric Utility (General)",
    "ev_charging": "Green & Renewable Energy",
    "microgrids": "Electric Utility (General)",
    # Efficiency
    "efficiency_industrial": "Power",
    "efficiency_buildings": "Power",
    "district_energy": "Electric Utility (General)",
}
