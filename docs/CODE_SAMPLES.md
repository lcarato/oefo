# OEFO Configuration Module - Code Samples

Complete code snippets demonstrating key functionality from each configuration module.

---

## 1. Taxonomy Module (`taxonomy.py`)

### Define Controlled Vocabularies

```python
from oefo.config import Technology, Scale, ValueChainPosition, ProjectStatus

# Enumerate a technology
tech = Technology.SOLAR_PV
print(f"Technology: {tech.value}")  # Output: "solar_pv"

# Create a scale
scale = Scale.UTILITY_SCALE
print(f"Scale: {scale.value}")  # Output: "utility_scale"

# Value chain position
position = ValueChainPosition.GENERATION
print(f"Position: {position.value}")  # Output: "generation"

# Project status
status = ProjectStatus.OPERATING
print(f"Status: {status.value}")  # Output: "operating"
```

### Validate Enum Values

```python
from oefo.config import validate_technology, validate_scale

# Check if a string is a valid technology
if validate_technology("solar_pv"):
    print("Valid technology")
    
# Check if a string is a valid scale
if validate_scale("utility_scale"):
    print("Valid scale")
    
# Extract enum value safely
tech_value = Technology.WIND_OFFSHORE_FLOATING.value
print(f"Value: {tech_value}")  # "wind_offshore_floating"
```

### List All Technologies

```python
from oefo.config import Technology

# Iterate through all technologies
print("Available technologies:")
for tech in Technology:
    print(f"  - {tech.value}")

# Get all as strings
tech_list = [t.value for t in Technology]
print(f"Total: {len(tech_list)} technologies")
```

---

## 2. Thresholds Module (`thresholds.py`)

### Validate Financial Parameters

```python
from oefo.config import (
    is_kd_plausible,
    is_ke_plausible,
    is_wacc_plausible,
    is_leverage_plausible,
)

# Validate cost of debt (5.5%)
if is_kd_plausible(5.5):
    print("Valid cost of debt")

# Validate cost of equity (10%)
if is_ke_plausible(10.0):
    print("Valid cost of equity")

# Validate WACC (7.5%)
if is_wacc_plausible(7.5):
    print("Valid WACC")

# Validate leverage (65% D/D+E)
if is_leverage_plausible(65.0):
    print("Valid leverage ratio")
```

### Check WACC Reconciliation

```python
from oefo.config import wacc_reconciliation_passes

calculated_wacc = 8.2  # From Kd, Ke, D/E components
observed_wacc = 8.0    # From market data or disclosure

if wacc_reconciliation_passes(calculated_wacc, observed_wacc):
    print("WACC components reconcile with observed WACC")
else:
    print(f"Discrepancy: {abs(calculated_wacc - observed_wacc):.2f}% exceeds tolerance")
```

### QC Triage Decision Logic

```python
from oefo.config import (
    should_auto_accept,
    should_review,
    should_reject,
)

qc_score = 0.92  # QC scoring result (0.0 to 1.0)

if should_auto_accept(qc_score):
    print("Auto-accept: High confidence in extraction")
elif should_review(qc_score):
    print("Route to human review: Moderate confidence")
elif should_reject(qc_score):
    print("Reject: Low confidence, quality issues")
```

### Check Outliers

```python
from oefo.config import OUTLIER_STD_DEVIATIONS
import statistics

# Sample WACC data from a technology group
wacc_data = [7.5, 8.1, 7.8, 8.3, 7.9, 25.0]  # 25.0 is an outlier

mean = statistics.mean(wacc_data)
stdev = statistics.stdev(wacc_data)

print(f"Mean WACC: {mean:.2f}%")
print(f"Std Dev: {stdev:.2f}%")
print(f"Outlier threshold: {mean + OUTLIER_STD_DEVIATIONS * stdev:.2f}%")

for value in wacc_data:
    z_score = (value - mean) / stdev
    if abs(z_score) > OUTLIER_STD_DEVIATIONS:
        print(f"  {value}% is an outlier ({z_score:.2f}σ)")
```

---

## 3. Sources Module (`sources.py`)

### Discover DFI Sources

```python
from oefo.config import (
    get_dfi_names,
    get_dfi_by_name,
    DFI_SOURCES,
)

# Get all DFI codes
dfi_codes = get_dfi_names()
print(f"Available DFIs: {dfi_codes}")

# Lookup specific DFI
ifc_info = DFI_SOURCES["IFC"]
print(f"IFC: {ifc_info['name']}")
print(f"Portal: {ifc_info['portal_url']}")
print(f"Priority: {ifc_info['priority']}")
print(f"Scraping feasibility: {ifc_info['scraping_feasibility']}")

# Iterate through all DFIs
for code, info in DFI_SOURCES.items():
    print(f"{code}: {info['name']} ({info['country']})")
```

### Discover Regulatory Sources

```python
from oefo.config import (
    get_regulator_codes,
    get_regulator_by_code,
    REGULATORY_SOURCES,
)

# Get all regulator codes
regulators = get_regulator_codes()
print(f"Available regulators: {regulators}")

# Lookup specific regulator
ferc_info = REGULATORY_SOURCES["FERC"]
print(f"Regulator: {ferc_info['regulator']}")
print(f"Country: {ferc_info['country']}")
print(f"Scope: {ferc_info['scope']}")
print(f"URL: {ferc_info['url']}")
print(f"Primary document: {ferc_info['primary_document']}")
print(f"Frequency: {ferc_info['frequency']}")

# Filter by country
for code, info in REGULATORY_SOURCES.items():
    if info['country'] == "Brazil":
        print(f"Brazil regulator: {code} - {info['regulator']}")
```

### Explore Company Universe

```python
from oefo.config import (
    get_companies_by_sector,
    get_all_sectors,
    get_all_companies,
    company_in_universe,
    count_companies_by_sector,
    total_company_count,
)

# List all sectors
sectors = get_all_sectors()
print(f"Available sectors: {len(sectors)}")
for sector in sectors:
    print(f"  - {sector}")

# Get companies in a sector
solar_companies = get_companies_by_sector("Solar_Developers_Manufacturers_Yieldcos")
print(f"\nSolar companies ({len(solar_companies)}):")
for company in solar_companies:
    print(f"  - {company}")

# Check if company is tracked
if company_in_universe("NextEra Energy"):
    print("NextEra Energy is in the OEFO universe")

# Count companies per sector
counts = count_companies_by_sector()
print(f"\nCompanies by sector:")
for sector, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {sector}: {count}")

# Get all companies
all_companies = get_all_companies()
print(f"\nTotal companies: {total_company_count()}")
print(f"First 10: {all_companies[:10]}")
```

---

## 4. Settings Module (`settings.py`)

### Access Configuration Parameters

```python
from oefo.config import (
    OCR_DPI,
    VISION_DPI,
    VISION_MODEL,
    QC_MODEL,
    MAX_VISION_PAGES,
    DATA_DIR,
    RAW_DIR,
    EXTRACTED_DIR,
    FINAL_DIR,
    LOGS_DIR,
    CACHE_DIR,
)

print(f"OCR settings:")
print(f"  OCR DPI: {OCR_DPI}")
print(f"  Vision DPI: {VISION_DPI}")
print(f"  Vision Model: {VISION_MODEL}")
print(f"  QC Model: {QC_MODEL}")
print(f"  Max Vision Pages: {MAX_VISION_PAGES}")

print(f"\nData directories:")
print(f"  Raw: {RAW_DIR}")
print(f"  Extracted: {EXTRACTED_DIR}")
print(f"  Final: {FINAL_DIR}")
print(f"  Logs: {LOGS_DIR}")
print(f"  Cache: {CACHE_DIR}")
```

### Validate API Keys and Directories

```python
from oefo.config import validate_api_keys, validate_directories

# Check API keys are set
if validate_api_keys():
    print("API keys are configured")
    # Proceed with API calls
else:
    print("ERROR: API keys missing")
    # Exit or prompt user

# Check directories are accessible
if validate_directories():
    print("All required directories exist and are writable")
    # Proceed with data pipeline
else:
    print("ERROR: Directory access issues")
    # Exit or fix permissions
```

### Get and Print Configuration

```python
from oefo.config import get_config, print_config

# Get all settings as dictionary
config = get_config()
for key, value in sorted(config.items()):
    print(f"{key}: {value}")

# Pretty-print configuration
print_config()
```

### Use Settings in Pipeline

```python
from oefo.config import (
    RAW_DIR,
    EXTRACTED_DIR,
    FINAL_DIR,
    VISION_DPI,
    VISION_MODEL,
    ENABLE_CACHING,
    MAX_WORKERS,
)

# Configure document processing
print(f"Processing PDFs at {VISION_DPI} DPI")
print(f"Using {VISION_MODEL} for extraction")

# Configure data flow
raw_documents = list(RAW_DIR.glob("*.pdf"))
print(f"Found {len(raw_documents)} documents to process")

# Configure caching and parallelism
if ENABLE_CACHING:
    print(f"Caching enabled")
    
print(f"Processing with {MAX_WORKERS} workers")

# Output paths
for doc in raw_documents[:3]:
    doc_name = doc.stem
    extracted_path = EXTRACTED_DIR / f"{doc_name}.json"
    final_path = FINAL_DIR / f"{doc_name}_approved.json"
    print(f"  {doc_name} -> {extracted_path} -> {final_path}")
```

---

## 5. Integrated Module (`__init__.py`)

### Single Import for Full Configuration

```python
# Import all configuration in one statement
from oefo.config import (
    # Enums
    Technology,
    Scale,
    ProjectStatus,
    ConfidenceLevel,
    
    # Thresholds
    KD_NOMINAL_RANGE,
    WACC_NOMINAL_RANGE,
    AUTO_ACCEPT_THRESHOLD,
    is_wacc_plausible,
    should_auto_accept,
    
    # Sources
    DFI_SOURCES,
    COMPANY_UNIVERSE,
    get_companies_by_sector,
    
    # Settings
    VISION_MODEL,
    DATA_DIR,
    validate_api_keys,
)

# Use them together
print(f"Using {VISION_MODEL} for extraction")
print(f"Processing technologies: {len(Technology)}")
print(f"Tracking {len(COMPANY_UNIVERSE)} company sectors")
print(f"WACC validation range: {WACC_NOMINAL_RANGE}")
```

---

## Complete Pipeline Example

### Data Extraction and QC Pipeline

```python
from oefo.config import (
    # Taxonomy
    Technology,
    SourceType,
    ExtractionTier,
    QCStatus,
    
    # Thresholds
    is_wacc_plausible,
    should_auto_accept,
    should_review,
    should_reject,
    
    # Sources
    company_in_universe,
    
    # Settings
    VISION_MODEL,
    RAW_DIR,
    EXTRACTED_DIR,
    FINAL_DIR,
    validate_api_keys,
)

def process_energy_project_disclosure(company_name: str, source_path: str):
    """
    Process an energy company disclosure document.
    """
    # Validate prerequisites
    if not validate_api_keys():
        raise RuntimeError("API keys not configured")
    
    if not company_in_universe(company_name):
        print(f"Warning: {company_name} not in tracked universe")
    
    # Extract data using vision model
    print(f"Extracting from {source_path} using {VISION_MODEL}")
    # ... extraction logic ...
    
    # Validate extracted data
    wacc_value = 8.5  # Example extracted value
    if is_wacc_plausible(wacc_value):
        print(f"WACC {wacc_value}% is plausible")
    
    # QC triage
    qc_score = 0.88  # Example QC score
    if should_auto_accept(qc_score):
        status = QCStatus.AUTO_ACCEPTED
        print("Data auto-accepted")
    elif should_review(qc_score):
        status = QCStatus.HUMAN_REVIEWED
        print("Data routed to human review")
    else:
        status = QCStatus.REJECTED
        print("Data rejected")
    
    # Store results
    return {
        "company": company_name,
        "technology": Technology.SOLAR_PV,
        "wacc": wacc_value,
        "qc_status": status,
        "source_type": SourceType.CORPORATE_FILING,
    }

# Run example
result = process_energy_project_disclosure(
    "NextEra Energy",
    str(RAW_DIR / "NextEra_2025_Annual.pdf")
)
print(f"Result: {result}")
```

---

## Environment Variable Usage

### Setting Configuration via Environment Variables

```bash
# Set in shell before running Python
export OEFO_BASE_DIR="/path/to/oefo"
export OEFO_DATA_DIR="/data/oefo"
export OEFO_RAW_DIR="/data/oefo/raw"
export OEFO_EXTRACTED_DIR="/data/oefo/extracted"
export OEFO_FINAL_DIR="/data/oefo/final"
export ANTHROPIC_API_KEY="sk-ant-..."
export OEFO_LOG_LEVEL="DEBUG"
export OEFO_MAX_WORKERS="8"

python3 my_pipeline.py
```

### Load from .env File

```python
from pathlib import Path
from dotenv import load_dotenv
from oefo.config import print_config, validate_api_keys

# Load from .env file
load_dotenv(Path.home() / ".oefo" / ".env")

# Validate configuration
if not validate_api_keys():
    raise RuntimeError("ANTHROPIC_API_KEY not configured")

# Print loaded configuration
print_config()
```

---

## Advanced Usage

### Custom Threshold Checks

```python
from oefo.config import (
    KD_NOMINAL_RANGE,
    KE_NOMINAL_RANGE,
    WACC_NOMINAL_RANGE,
    OUTLIER_STD_DEVIATIONS,
)

def calculate_wacc(kd: float, ke: float, d_ratio: float) -> float:
    """Calculate WACC from component parameters."""
    return kd * d_ratio + ke * (1 - d_ratio)

def validate_financial_structure(kd: float, ke: float, d_ratio: float) -> dict:
    """Comprehensive financial parameter validation."""
    results = {
        "kd_valid": KD_NOMINAL_RANGE[0] <= kd <= KD_NOMINAL_RANGE[1],
        "ke_valid": KE_NOMINAL_RANGE[0] <= ke <= KE_NOMINAL_RANGE[1],
        "wacc_calc": calculate_wacc(kd, ke, d_ratio),
    }
    
    wacc = results["wacc_calc"]
    results["wacc_valid"] = WACC_NOMINAL_RANGE[0] <= wacc <= WACC_NOMINAL_RANGE[1]
    
    return results

# Test validation
structure = validate_financial_structure(kd=5.5, ke=10.0, d_ratio=0.65)
print(f"Financial structure validation: {structure}")
```

---

This documentation provides practical, copy-paste-ready examples for every major feature of the OEFO configuration module.
