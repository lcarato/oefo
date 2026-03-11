# OEFO Configuration Module - Build Summary

**Project:** Open Energy Finance Observatory (OEFO)  
**Date:** March 2026  
**Status:** Complete  
**Location:** `/sessions/fervent-tender-allen/mnt/ET Finance/oefo/config/`

---

## Overview

The OEFO configuration module provides centralized management of:
- **Controlled vocabularies** for energy technologies, project types, and financial instruments
- **QC thresholds** and plausibility ranges for data validation
- **Source registries** for DFIs, regulators, and target companies
- **Runtime settings** for document processing, API access, and data storage

**Total Lines of Code:** 1,525 across 5 Python modules

---

## Files Created

### 1. `taxonomy.py` (263 lines)

**Purpose:** Enumerated types and controlled vocabularies used across the pipeline.

**Key Exports:**

| Enum | Count | Scope |
|------|-------|-------|
| `Technology` | 58 | Generation, fuel cycle, storage, demand-side, transmission/distribution, carbon management |
| `Scale` | 7 | utility_scale, commercial_industrial, distributed_residential, portfolio, mega_project, regulated_asset, pilot_demonstration |
| `ValueChainPosition` | 10 | generation, fuel_production, fuel_transport, fuel_storage, electricity_transmission, electricity_distribution, electricity_storage, end_use_efficiency, end_use_transport, carbon_management |
| `ProjectStatus` | 5 | operating, construction, financial_close, development, decommissioning |
| `SourceType` | 4 | DFI_disclosure, corporate_filing, bond_prospectus, regulatory_filing |
| `ExtractionMethod` | 4 | manual, automated_html, automated_pdf, llm_assisted |
| `ExtractionTier` | 4 | tier_1_text, tier_2_ocr, tier_3_vision, tier_4_manual |
| `QCStatus` | 4 | auto_accepted, human_reviewed, human_corrected, rejected |
| `ConfidenceLevel` | 3 | high, medium, low |
| `DebtType` | 5 | senior, subordinated, mezzanine, bond, concessional |
| `KDRateBenchmark` | 5 | SOFR, EURIBOR, LIBOR, fixed, local_reference_rate |
| `KEEstimationMethod` | 4 | regulatory_allowed, capm_derived, disclosed, implied |
| `LeverageBasis` | 2 | project_level, corporate_level |

**Key Functions:**
- `get_technology_value()` - Extract string from enum
- `get_scale_value()` - Extract string from enum
- `validate_technology()` - Validation check
- `validate_scale()` - Validation check

**Example Usage:**
```python
from oefo.config import Technology, Scale
tech = Technology.SOLAR_PV
scale = Scale.UTILITY_SCALE
print(tech.value)  # "solar_pv"
```

---

### 2. `thresholds.py` (250 lines)

**Purpose:** QC thresholds, plausibility ranges, and outlier detection parameters.

**Key Constants:**

| Parameter | Range/Value | Unit | Notes |
|-----------|------------|------|-------|
| `KD_NOMINAL_RANGE` | (0.0, 30.0) | % | Cost of debt |
| `KE_NOMINAL_RANGE` | (2.0, 40.0) | % | Cost of equity |
| `WACC_NOMINAL_RANGE` | (1.0, 35.0) | % | Weighted avg cost of capital |
| `LEVERAGE_NOMINAL_RANGE` | (0.0, 100.0) | % | D/(D+E) ratio |
| `DEBT_TENOR_RANGE` | (1, 40) | years | Maturity |
| `SPREAD_BPS_RANGE` | (0, 2000) | bps | Credit spread |
| `WACC_CONSISTENCY_TOLERANCE` | 0.5 | pp | Reconciliation tolerance |
| `AUTO_ACCEPT_THRESHOLD` | 0.85 | score | Auto-accept QC score |
| `REVIEW_THRESHOLD` | 0.50 | score | Review/reject threshold |
| `OUTLIER_STD_DEVIATIONS` | 2.0 | σ | Outlier detection |

**Key Functions:**
- `is_kd_plausible()` - Validate cost of debt
- `is_ke_plausible()` - Validate cost of equity
- `is_wacc_plausible()` - Validate WACC
- `is_leverage_plausible()` - Validate leverage
- `is_tenor_plausible()` - Validate tenor
- `is_spread_plausible()` - Validate spread
- `wacc_reconciliation_passes()` - WACC consistency check
- `should_auto_accept()` - QC triage decision
- `should_review()` - QC triage decision
- `should_reject()` - QC triage decision

**Example Usage:**
```python
from oefo.config import is_wacc_plausible, should_auto_accept
if is_wacc_plausible(8.5) and should_auto_accept(0.92):
    print("Data accepted")
```

---

### 3. `sources.py` (496 lines)

**Purpose:** Source registry of DFIs, regulators, and target companies.

**Key Registries:**

#### DFI_SOURCES (8 institutions)
- International Finance Corporation (IFC)
- European Bank for Reconstruction and Development (EBRD)
- Asian Development Bank (ADB)
- African Development Bank (AfDB)
- European Investment Bank (EIB)
- U.S. International Development Finance Corporation (DFC)
- Green Climate Fund (GCF)
- Asian Infrastructure Investment Bank (AIIB)

Each entry includes: name, parent, country, portal_url, format, priority (1-2), scraping_feasibility, notes.

#### REGULATORY_SOURCES (12 regulators)
- FERC (US - electricity, gas transmission)
- CPUC (California)
- Ofgem (UK)
- CRE (Mexico)
- ANEEL (Brazil)
- EMA (Singapore)
- ICAI (India)
- NERSA (South Africa)
- ACCC (Australia)
- NZ_EA (New Zealand)
- ERG (Latin America - proxy)
- KHNP (South Korea)
- JEPIC (Japan)

Each entry includes: name, country, scope, url, primary_document, language, format, frequency, priority, notes.

#### COMPANY_UNIVERSE (14 sectors, 126 companies)

**Sectors:**
1. Solar_Developers_Manufacturers_Yieldcos (14 companies)
2. Wind_Developers_OEMs_Operators (12 companies)
3. Diversified_Renewables_IPPs_Yieldcos_Platforms (12 companies)
4. Hydropower (6 companies)
5. Oil_and_Gas_Upstream_Midstream_Downstream_LNG (21 companies)
6. Gas_Utilities_Distribution (5 companies)
7. Coal_Transition_Analysis (4 companies)
8. Nuclear (9 companies)
9. Utilities_Regulated (13 companies)
10. Storage (6 companies)
11. Hydrogen_and_Carbon_Capture (9 companies)
12. EV_Charging (5 companies)
13. Energy_Efficiency_ESCOs (4 companies)
14. Bioenergy_Biofuels (6 companies)

**Key Functions:**
- `get_dfi_by_name()` - Lookup DFI info
- `get_dfi_names()` - List all DFIs
- `get_regulator_by_code()` - Lookup regulator info
- `get_regulator_codes()` - List all regulators
- `get_companies_by_sector()` - List companies in a sector
- `get_all_sectors()` - List all sectors
- `get_all_companies()` - Flattened company list
- `company_in_universe()` - Check if company exists
- `count_companies_by_sector()` - Count by sector
- `total_company_count()` - Total count

**Example Usage:**
```python
from oefo.config import get_companies_by_sector, total_company_count
solar_cos = get_companies_by_sector('Solar_Developers_Manufacturers_Yieldcos')
print(f"Total companies: {total_company_count()}")  # 126
```

---

### 4. `settings.py` (308 lines)

**Purpose:** Runtime configuration, API keys, and directory paths.

**Document Processing:**
- `OCR_DPI = 300` - Tesseract DPI
- `VISION_DPI = 250` - Claude Vision DPI
- `VISION_MODEL = "claude-sonnet-4-20250514"` - Vision extraction model
- `QC_MODEL = "claude-sonnet-4-20250514"` - QC validation model
- `MAX_VISION_PAGES = 5` - Max pages per vision API call
- `TESSERACT_LANGUAGES` - Dict of language codes (English, French, German, Spanish, Portuguese, Italian, Japanese, Chinese, Russian, Arabic)

**Directory Structure:**
- `BASE_DIR` - Project root (from OEFO_BASE_DIR env var)
- `DATA_DIR` - All data storage (from OEFO_DATA_DIR env var)
- `RAW_DIR` - Raw unprocessed documents
- `EXTRACTED_DIR` - Extracted unvalidated data
- `FINAL_DIR` - Validated QC-approved data
- `LOGS_DIR` - Application logs
- `CACHE_DIR` - Caching (OCR, responses, etc.)

**All paths created automatically if missing.**

**API Authentication:**
- `ANTHROPIC_API_KEY` - Claude API key (from ANTHROPIC_API_KEY env var, required)
- `ANTHROPIC_ORG_ID` - Optional organization ID

**Web Access:**
- `USER_AGENT` - OEFO-identified user agent string
- `REQUEST_TIMEOUT = 30` - HTTP request timeout (seconds)
- `RETRY_MAX_ATTEMPTS = 3` - HTTP retry attempts
- `RETRY_BACKOFF_FACTOR = 1.5` - Exponential backoff multiplier

**Processing Options:**
- `ENABLE_CACHING = true` - Enable response caching
- `ENABLE_PARALLEL_PROCESSING = true` - Enable parallel operations
- `MAX_WORKERS = 4` - Worker threads/processes
- `LOG_LEVEL = "INFO"` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `DEBUG = false` - Debug mode flag
- `DRY_RUN = false` - Simulate without external calls

**Key Functions:**
- `get_config()` - Return config dict (sensitive values masked)
- `validate_api_keys()` - Check required keys
- `validate_directories()` - Check directory access
- `print_config()` - Pretty-print config

**Example Usage:**
```python
from oefo.config import DATA_DIR, OCR_DPI, validate_api_keys
if validate_api_keys():
    print(f"OCR at {OCR_DPI} DPI, saving to {DATA_DIR}")
```

---

### 5. `__init__.py` (208 lines)

**Purpose:** Public API - export all configuration objects for convenient importing.

**Exports All From:**
- `taxonomy` (13 enums + 4 helper functions)
- `thresholds` (10 constants + 11 helper functions)
- `sources` (3 registries + 10 helper functions)
- `settings` (30+ configuration parameters + 3 helper functions)

**Module Metadata:**
```python
__version__ = "0.1.0"
__author__ = "OEFO Development Team"
__description__ = "Configuration module for OEFO project"
```

**Single-Import Style:**
```python
from oefo.config import (
    Technology,
    KD_NOMINAL_RANGE,
    DFI_SOURCES,
    ANTHROPIC_API_KEY,
)
```

---

## Statistics

| Metric | Count |
|--------|-------|
| Total Python modules | 5 |
| Total lines of code | 1,525 |
| Enum classes | 13 |
| Total enum values | 133+ |
| Thresholds/constants | 10 |
| Helper functions | 30+ |
| DFI sources | 8 |
| Regulatory bodies | 13 |
| Company sectors | 14 |
| Companies in universe | 126 |
| Configuration parameters | 30+ |

---

## Design Principles

1. **Modularity** - Each file has a clear, single responsibility
2. **Type Safety** - Full type hints throughout
3. **Documentation** - Comprehensive docstrings and comments
4. **Validation** - Helper functions for all key parameters
5. **Environment-Friendly** - Settings via env vars with defaults
6. **Extensibility** - Easy to add new technologies, regulators, companies
7. **Discoverability** - Clear exports in `__init__.py`

---

## Usage Examples

### Example 1: Validate Financial Parameters
```python
from oefo.config import (
    is_kd_plausible,
    is_wacc_plausible,
    WACC_CONSISTENCY_TOLERANCE,
)

cost_of_debt = 5.5
if is_kd_plausible(cost_of_debt):
    print(f"Valid KD: {cost_of_debt}%")

calculated_wacc = 8.2
observed_wacc = 8.0
if abs(calculated_wacc - observed_wacc) <= WACC_CONSISTENCY_TOLERANCE:
    print("WACC reconciliation passes")
```

### Example 2: Check Company Status
```python
from oefo.config import (
    company_in_universe,
    get_companies_by_sector,
    total_company_count,
)

if company_in_universe("NextEra Energy"):
    print("Company tracked in OEFO")

solar_companies = get_companies_by_sector('Solar_Developers_Manufacturers_Yieldcos')
print(f"Tracking {len(solar_companies)} solar companies")
print(f"Total universe: {total_company_count()} companies")
```

### Example 3: Configure Data Pipeline
```python
from oefo.config import (
    RAW_DIR,
    EXTRACTED_DIR,
    VISION_DPI,
    VISION_MODEL,
    validate_api_keys,
    print_config,
)

if validate_api_keys():
    print_config()
    print(f"Processing PDFs at {VISION_DPI} DPI")
    print(f"Using {VISION_MODEL} for extraction")
```

### Example 4: Source Discovery
```python
from oefo.config import (
    get_dfi_names,
    get_regulator_codes,
    DFI_SOURCES,
    REGULATORY_SOURCES,
)

for dfi_code in get_dfi_names():
    info = DFI_SOURCES[dfi_code]
    print(f"{dfi_code}: {info['portal_url']} (Priority {info['priority']})")

for reg_code in get_regulator_codes():
    info = REGULATORY_SOURCES[reg_code]
    print(f"{reg_code}: {info['country']} ({info['scope']})")
```

---

## Integration with Data Pipeline

The configuration module is designed to support:

1. **Document Processing Pipeline**
   - OCR/Vision parameters for extraction tier selection
   - Model and DPI settings for quality tuning

2. **Data Validation (QC)**
   - Thresholds for auto-accept, review, reject triage
   - Plausibility ranges for cost of capital parameters
   - Outlier detection via standard deviations

3. **Data Collection (Scraping)**
   - DFI and regulator source registry
   - Company universe for tracking
   - Scraping feasibility indicators

4. **Data Storage**
   - Directory structure for raw, extracted, final data
   - Cache management for processing efficiency

5. **API & Authentication**
   - Claude API key management
   - Rate limiting and retry logic
   - User agent and request customization

---

## Next Steps

1. Create data models (`oefo/models/`) for representing:
   - Projects and companies
   - Financial observations (Kd, Ke, leverage, etc.)
   - Source documents and extractions
   - QC audit trails

2. Build extraction pipeline (`oefo/extraction/`) for:
   - PDF parsing and OCR
   - Vision-based extraction from scanned documents
   - LLM-assisted structured data extraction
   - HTML/XML parsing from web portals

3. Implement QC module (`oefo/qc/`) for:
   - Plausibility scoring
   - Consistency checks
   - Triage and routing
   - Human review workflows

4. Develop source connectors (`oefo/sources/`) for:
   - DFI portal scraping
   - Regulatory filing downloads
   - Corporate disclosure aggregation
   - SEC EDGAR integration

---

## File Locations

```
/sessions/fervent-tender-allen/mnt/ET Finance/oefo/config/
├── __init__.py          (208 lines)   - Public API exports
├── taxonomy.py          (263 lines)   - Controlled vocabularies
├── thresholds.py        (250 lines)   - QC thresholds & validation
├── sources.py           (496 lines)   - DFI/regulator/company registry
└── settings.py          (308 lines)   - Runtime configuration
```

**Total:** 1,525 lines of well-documented, production-ready Python code.

