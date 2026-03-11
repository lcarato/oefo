"""
Source Registry and Company Universe for OEFO Data Pipeline

This module maintains master registries of data sources, regulators, and the
target company universe. Used for discovery, prioritization, and validation
of data collection strategies.

Sources are organized by type:
1. Development Finance Institutions (DFIs) - multilateral and bilateral agencies
2. Regulatory bodies - national/regional energy and financial regulators
3. Corporate issuers - public companies and projects to track
"""

from typing import Dict, Any, List

# =============================================================================
# Development Finance Institutions (DFIs)
# =============================================================================
# Multilateral and bilateral development banks that finance energy projects.
# Listed by disclosure quality, coverage scope, and scraping feasibility.

DFI_SOURCES: Dict[str, Dict[str, Any]] = {
    "IFC": {
        "name": "International Finance Corporation",
        "parent": "World Bank Group",
        "country": "Global",
        "portal_url": "https://www.ifc.org/en/what-we-do/portfolio",
        "format": "web_portal + PDF disclosures",
        "priority": 1,
        "scraping_feasibility": "medium",
        "notes": "Strong disclosure on energy projects; searchable portal; XBRL available.",
    },
    "EBRD": {
        "name": "European Bank for Reconstruction and Development",
        "parent": None,
        "country": "Europe & Central Asia",
        "portal_url": "https://www.ebrd.com/work-with-us/project-finance.html",
        "format": "web portal + PDF prospectuses",
        "priority": 1,
        "scraping_feasibility": "medium",
        "notes": "Detailed project summaries; energy transition focus; some bond terms public.",
    },
    "ADB": {
        "name": "Asian Development Bank",
        "parent": None,
        "country": "Asia-Pacific",
        "portal_url": "https://www.adb.org/projects",
        "format": "web portal + XBRL/JSON API",
        "priority": 1,
        "scraping_feasibility": "high",
        "notes": "API access; project-level granularity; strong emerging market coverage.",
    },
    "AfDB": {
        "name": "African Development Bank",
        "parent": None,
        "country": "Africa",
        "portal_url": "https://www.afdb.org/en/projects-and-operations/operations",
        "format": "web portal + PDF",
        "priority": 1,
        "scraping_feasibility": "medium",
        "notes": "Growing renewable energy pipeline; project summaries available.",
    },
    "EIB": {
        "name": "European Investment Bank",
        "parent": None,
        "country": "Europe & Global",
        "portal_url": "https://www.eib.org/en/projects/index.htm",
        "format": "web portal + PDF reports",
        "priority": 1,
        "scraping_feasibility": "medium",
        "notes": "Publicly listed projects; strong climate finance data; impact reports.",
    },
    "DFC": {
        "name": "U.S. International Development Finance Corporation",
        "parent": "U.S. Government",
        "country": "Global (US focus)",
        "portal_url": "https://www.dfc.gov/projects",
        "format": "web portal + PDF fact sheets",
        "priority": 2,
        "scraping_feasibility": "medium",
        "notes": "Smaller deal count but high transparency; project fact sheets.",
    },
    "GCF": {
        "name": "Green Climate Fund",
        "parent": "UNFCCC",
        "country": "Global",
        "portal_url": "https://www.greenclimate.fund/projects",
        "format": "web portal + JSON API",
        "priority": 2,
        "scraping_feasibility": "high",
        "notes": "Climate-focused; structured data; API available.",
    },
    "AIIB": {
        "name": "Asian Infrastructure Investment Bank",
        "parent": None,
        "country": "Asia-Pacific",
        "portal_url": "https://www.aiib.org/en/projects/index.html",
        "format": "web portal + PDF summaries",
        "priority": 2,
        "scraping_feasibility": "medium",
        "notes": "Emerging infrastructure financier; growing energy portfolio.",
    },
}

# =============================================================================
# Regulatory Bodies - Allowed Returns and Rate-Setting
# =============================================================================
# National and regional energy/utility regulators that publish cost of equity
# and capital structure decisions. Direct observations of Ke and leverage.

REGULATORY_SOURCES: Dict[str, Dict[str, Any]] = {
    "FERC": {
        "regulator": "Federal Energy Regulatory Commission",
        "country": "United States",
        "scope": "Electricity transmission & gas pipelines (federal jurisdiction)",
        "url": "https://www.ferc.gov/industries/electric/general-info/electric-industry-overview/transmission-investment",
        "primary_document": "ROE orders and rate decisions",
        "language": "English",
        "format": "PDF (dockets database)",
        "frequency": "Ongoing (varies by company/rate case)",
        "priority": 1,
        "notes": "Extensive allowed ROE precedent; searchable FERC docket database.",
    },
    "CPUC": {
        "regulator": "California Public Utilities Commission",
        "country": "United States (California)",
        "scope": "Electricity, gas, water utilities",
        "url": "https://www.cpuc.ca.gov/ratecase",
        "primary_document": "General rate case decisions",
        "language": "English",
        "format": "PDF + web portal",
        "frequency": "Every 3 years (typical)",
        "priority": 1,
        "notes": "Major market; detailed cost of capital testimony; public portals.",
    },
    "Ofgem": {
        "regulator": "Office of Gas and Electricity Markets",
        "country": "United Kingdom",
        "scope": "Electricity and gas distribution/transmission",
        "url": "https://www.ofgem.gov.uk/publications",
        "primary_document": "Price control reviews (RIIO methodology)",
        "language": "English",
        "format": "PDF + consultation papers",
        "frequency": "5-yearly (RIIO cycles)",
        "priority": 1,
        "notes": "Transparent cost of capital methodology; extensive evidence base published.",
    },
    "CRE": {
        "regulator": "Comisión Reguladora de Energía",
        "country": "Mexico",
        "scope": "Electricity generation, transmission, distribution",
        "url": "https://www.gob.mx/cre",
        "primary_document": "Tariff and rate resolutions",
        "language": "Spanish",
        "format": "PDF + web portal",
        "frequency": "Annual (tariffs); varies (generation auctions)",
        "priority": 2,
        "notes": "Large Latin American market; competitive auction data available.",
    },
    "ANEEL": {
        "regulator": "Agência Nacional de Energia Elétrica",
        "country": "Brazil",
        "scope": "Electricity generation, transmission, distribution",
        "url": "https://www.aneel.gov.br/",
        "primary_document": "Tariff reviews and rate decisions",
        "language": "Portuguese",
        "format": "PDF + web portal",
        "frequency": "Varies by company (concession cycle-dependent)",
        "priority": 2,
        "notes": "Large emerging market; tariff data publicly available.",
    },
    "EMA": {
        "regulator": "Energy Market Authority",
        "country": "Singapore",
        "scope": "Electricity and gas",
        "url": "https://www.ema.gov.sg/",
        "primary_document": "Regulatory announcements and tariffs",
        "language": "English",
        "format": "PDF + web",
        "frequency": "Varies",
        "priority": 2,
        "notes": "Developed Asian market; transparent regulatory framework.",
    },
    "ICAI": {
        "regulator": "Indian Council of Arbitration (Proxy: Central Electricity Authority)",
        "country": "India",
        "scope": "Electricity generation and transmission",
        "url": "https://cea.nic.in/",
        "primary_document": "Tariff determinations and power station data",
        "language": "English",
        "format": "PDF + Excel",
        "frequency": "Annual",
        "priority": 2,
        "notes": "Large emerging market; CEA publishes tariff database.",
    },
    "NERSA": {
        "regulator": "National Energy Regulator of South Africa",
        "country": "South Africa",
        "scope": "Electricity, gas, pipeline",
        "url": "https://www.nersa.org.za/",
        "primary_document": "Tariff determination documents",
        "language": "English",
        "format": "PDF + web portal",
        "frequency": "Annual",
        "priority": 2,
        "notes": "Sub-Saharan African energy market; tariff hearings public.",
    },
    "ACCC": {
        "regulator": "Australian Competition and Consumer Commission",
        "country": "Australia",
        "scope": "Electricity networks (distribution/transmission)",
        "url": "https://www.accc.gov.au/regulated-infrastructure/electricity",
        "primary_document": "Network revenue determinations",
        "language": "English",
        "format": "PDF + consultation portal",
        "frequency": "5-yearly (varies by distributor)",
        "priority": 2,
        "notes": "Mature market; transparent cost of capital determination process.",
    },
    "NZ_EA": {
        "regulator": "New Zealand Electricity Authority",
        "country": "New Zealand",
        "scope": "Electricity",
        "url": "https://www.ea.govt.nz/",
        "primary_document": "Network revenue determinations",
        "language": "English",
        "format": "PDF + web",
        "frequency": "Varies",
        "priority": 3,
        "notes": "Small market; regulatory framework well-documented.",
    },
    "ERG": {
        "regulator": "Entidad Reguladora del Gobierno (or equivalent - varies by country)",
        "country": "Latin America (multiple)",
        "scope": "Energy (varies)",
        "url": "Varies by country",
        "primary_document": "Tariff and rate decisions",
        "language": "Spanish/Portuguese",
        "format": "PDF + web",
        "frequency": "Varies",
        "priority": 2,
        "notes": "Placeholder for Latin American regulators; specific entities vary.",
    },
    "KHNP": {
        "regulator": "Korea Hydro & Nuclear Power (proxy for Korean regulation)",
        "country": "South Korea",
        "scope": "Electricity generation (regulated tariffs)",
        "url": "https://www.khnp.co.kr/",
        "primary_document": "Regulated tariff schedules",
        "language": "Korean/English",
        "format": "PDF + web",
        "frequency": "Annual/varies",
        "priority": 2,
        "notes": "Developed Asian market; state-owned utility tariffs regulated.",
    },
    "JEPIC": {
        "regulator": "Japan Electric Power Information Center (proxy for regulation)",
        "country": "Japan",
        "scope": "Electricity",
        "url": "https://www.jepic.or.jp/",
        "primary_document": "Utility rate schedules and regulatory filings",
        "language": "Japanese/English",
        "format": "PDF + web",
        "frequency": "Varies",
        "priority": 2,
        "notes": "Developed market; regional utilities regulated by local authorities.",
    },
}

# =============================================================================
# Corporate Universe - Publicly Listed Energy Companies & Projects
# =============================================================================
# Target companies for disclosure mining (annual reports, bond prospectuses,
# investor presentations). Organized by sector/subsector.

COMPANY_UNIVERSE: Dict[str, List[str]] = {
    "Solar_Developers_Manufacturers_Yieldcos": [
        "NextEra Energy",
        "First Solar",
        "Canadian Solar",
        "JinkoSolar",
        "Enphase",
        "SunPower",
        "Array Technologies",
        "Maxeon",
        "LONGi Green Energy",
        "Trina Solar",
        "Scatec",
        "Neoen",
        "Lightsource BP",
        "Clearway Energy",
    ],
    "Wind_Developers_OEMs_Operators": [
        "Ørsted",
        "Vestas",
        "Siemens Gamesa",
        "Nordex",
        "Iberdrola Renewables",
        "EDP Renováveis",
        "RWE Renewables",
        "SSE Renewables",
        "CWP Global",
        "Mainstream Renewable Power",
        "Equinor (offshore wind segment)",
        "Vineyard Wind",
    ],
    "Diversified_Renewables_IPPs_Yieldcos_Platforms": [
        "Brookfield Renewable",
        "AES Corp",
        "Enel Green Power",
        "Engie",
        "ReNew Energy",
        "Adani Green",
        "Azure Power",
        "Globeleq",
        "Lekela Power",
        "ACWA Power",
        "Masdar",
        "Pattern Energy",
    ],
    "Hydropower": [
        "Statkraft",
        "Fortum",
        "Voith Hydro",
        "China Three Gorges",
        "Itaipu (public disclosure)",
        "Eletrobras",
    ],
    "Oil_and_Gas_Upstream_Midstream_Downstream_LNG": [
        "ExxonMobil",
        "Shell",
        "TotalEnergies",
        "BP",
        "Chevron",
        "Petrobras",
        "Equinor",
        "YPF",
        "Ecopetrol",
        "Saudi Aramco (limited)",
        "Woodside",
        "Santos",
        "ConocoPhillips",
        "EOG Resources",
        "Pioneer (now ExxonMobil)",
        "Enterprise Products Partners",
        "Kinder Morgan",
        "TC Energy",
        "Cheniere Energy (LNG)",
        "Sempra (LNG)",
        "Venture Global (LNG)",
    ],
    "Gas_Utilities_Distribution": [
        "Southern Union",
        "Atmos Energy",
        "National Fuel Gas",
        "CenterPoint Energy",
        "South Union Gas",
    ],
    "Coal_Transition_Analysis": [
        "Peabody Energy",
        "Glencore (coal segment)",
        "Adaro Energy",
        "Coal India",
    ],
    "Nuclear": [
        "Cameco",
        "Constellation Energy",
        "EDF (nuclear segment)",
        "KEPCO",
        "CGN Power",
        "Rosatom (limited public data)",
        "NuScale Power",
        "Rolls-Royce SMR (pre-revenue)",
        "Kazatomprom (fuel cycle)",
    ],
    "Utilities_Regulated": [
        "Duke Energy",
        "Southern Company",
        "Enel",
        "National Grid",
        "Dominion Energy",
        "Exelon",
        "AEP (American Electric Power)",
        "Xcel Energy",
        "Cemig",
        "CPFL Energia",
        "Iberdrola",
        "Fortis Inc",
        "Endesa",
    ],
    "Storage": [
        "Fluence Energy",
        "Tesla Energy (limited segment data)",
        "Powin",
        "ESS Inc",
        "Form Energy",
        "Wärtsilä (storage segment)",
    ],
    "Hydrogen_and_Carbon_Capture": [
        "Plug Power",
        "Nel ASA",
        "ITM Power",
        "Bloom Energy",
        "Air Liquide (hydrogen segment)",
        "Linde (hydrogen segment)",
        "Northern Lights (CO2 storage JV)",
        "Occidental (DAC via 1PointFive)",
        "Equinor (H2/CCS segment)",
    ],
    "EV_Charging": [
        "ChargePoint",
        "EVgo",
        "Fastned",
        "Tritium",
        "Allego",
    ],
    "Energy_Efficiency_ESCOs": [
        "Ameresco",
        "Siemens Smart Infrastructure (segment)",
        "Schneider Electric (segment)",
        "Johnson Controls (segment)",
    ],
    "Bioenergy_Biofuels": [
        "Enviva",
        "Drax Group",
        "Raízen (ethanol/SAF)",
        "POET LLC",
        "Neste (renewable fuels)",
        "Verbio",
    ],
}

# =============================================================================
# Helper Functions
# =============================================================================


def get_dfi_by_name(name: str) -> Dict[str, Any]:
    """Retrieve DFI source registry entry by institution name."""
    return DFI_SOURCES.get(name.upper(), {})


def get_dfi_names() -> List[str]:
    """Get list of all DFI institution codes."""
    return list(DFI_SOURCES.keys())


def get_regulator_by_code(code: str) -> Dict[str, Any]:
    """Retrieve regulator source registry entry by code."""
    return REGULATORY_SOURCES.get(code.upper(), {})


def get_regulator_codes() -> List[str]:
    """Get list of all regulator codes."""
    return list(REGULATORY_SOURCES.keys())


def get_companies_by_sector(sector: str) -> List[str]:
    """
    Retrieve list of companies in a given sector.

    Args:
        sector: Sector key (e.g., 'Hydropower', 'Oil_and_Gas_Upstream_Midstream_Downstream_LNG')

    Returns:
        List of company names, or empty list if sector not found.
    """
    return COMPANY_UNIVERSE.get(sector, [])


def get_all_sectors() -> List[str]:
    """Get list of all sectors in the company universe."""
    return list(COMPANY_UNIVERSE.keys())


def get_all_companies() -> List[str]:
    """Get flattened list of all companies in the universe."""
    all_companies = []
    for companies in COMPANY_UNIVERSE.values():
        all_companies.extend(companies)
    return sorted(list(set(all_companies)))


def company_in_universe(company_name: str) -> bool:
    """Check if a company is in the target universe."""
    return company_name in get_all_companies()


def count_companies_by_sector() -> Dict[str, int]:
    """Return count of companies per sector."""
    return {sector: len(companies) for sector, companies in COMPANY_UNIVERSE.items()}


def total_company_count() -> int:
    """Return total count of unique companies in universe."""
    return len(get_all_companies())
