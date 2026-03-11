# OEFO Data Model - Quick Start Guide

## Module Structure

```
oefo/
├── models.py                    # Core Pydantic data models
└── data/
    ├── __init__.py              # Public API exports
    ├── storage.py               # Storage layer (Parquet + JSON)
    └── [raw/extracted/final]/   # Data directories
```

## Core Classes

### Data Models (in `models.py`)

| Class | Purpose | Use Case |
|-------|---------|----------|
| `Observation` | Main data entity | Store energy project financing parameters |
| `ExtractionResult` | Pipeline intermediate | Track extracted data before QC |
| `QCResult` | QC validation output | Store QC agent results with scores/flags |
| `RawDocument` | Document metadata | Track downloaded source files |
| `ScrapingTask` | Collection task tracking | Manage and monitor scraping operations |

### Storage Classes (in `data/storage.py`)

| Class | Storage Format | Primary Use |
|-------|---|---|
| `ObservationStore` | Parquet + pandas | Store and query observation data |
| `DocumentStore` | JSON index + metadata files | Manage document metadata with deduplication |

## Quick Examples

### 1. Create and Store an Observation

```python
from datetime import date
from models import (
    Observation, SourceType, ConfidenceLevel,
    ProjectStatus, Scale, ValueChainPosition
)
from data import ObservationStore

# Initialize storage
store = ObservationStore("data/final")

# Create observation
observation = Observation(
    observation_id="OBS-2024-001",
    source_type=SourceType.BOND_PROSPECTUS,
    source_institution="Development Finance Institution",
    source_document_url="https://example.com/prospectus.pdf",
    source_document_date=date(2024, 1, 15),
    extraction_date=date.today(),
    extraction_method="llm",
    confidence_level=ConfidenceLevel.HIGH,

    # Project info
    project_or_entity_name="Renewable Energy Project A",
    country="BRA",  # ISO 3166-1 alpha-3
    region="São Paulo",

    # Technology
    technology_l2="Wind - Onshore",
    scale=Scale.UTILITY,
    value_chain_position=ValueChainPosition.GENERATION,
    project_status=ProjectStatus.OPERATIONAL,
    project_capacity_mw=150.0,
    project_capex_usd=450_000_000,
    year_of_observation=2023,

    # Financing
    kd_nominal=0.045,
    ke_nominal=0.11,
    leverage_debt_pct=65,
    leverage_equity_pct=35,
    wacc_nominal=0.068,

    qc_status="passed",
    notes="Data from official prospectus"
)

# Store it
store.add_observations([observation])
```

### 2. Query Observations

```python
from data import ObservationStore

store = ObservationStore("data/final")

# Get all data
all_obs = store.get_all()
print(f"Total observations: {len(all_obs)}")

# Filter by country and technology
filtered = store.query({
    "country": "BRA",
    "technology_l2": "Wind - Onshore"
})

# Export to formats
store.export_csv("output/observations.csv")
store.export_excel("output/observations.xlsx")
```

### 3. Register and Track Documents

```python
from datetime import datetime
from models import RawDocument, SourceType, DocumentStatus
from data import DocumentStore, compute_content_hash

# Initialize document storage
doc_store = DocumentStore("data/raw")

# Compute hash of file content
with open("prospectus.pdf", "rb") as f:
    content_hash = compute_content_hash(f.read())

# Create document record
document = RawDocument(
    document_id="DOC-2024-001",
    source_url="https://example.com/prospectus.pdf",
    local_file_path="data/raw/prospectus.pdf",
    content_hash=content_hash,
    source_type=SourceType.BOND_PROSPECTUS,
    source_institution="Development Finance Institution",
    download_date=datetime.now(),
    download_status=DocumentStatus.DOWNLOADED,
    file_size_bytes=2_048_576,
    mime_type="application/pdf",
    extracted_count=1
)

# Register document
doc_id = doc_store.register_document(document)

# Check for duplicates before downloading
if not doc_store.is_duplicate(url="https://example.com/prospectus.pdf"):
    # Download the document
    pass
else:
    print("Document already in store")

# Retrieve document
doc = doc_store.get_by_url("https://example.com/prospectus.pdf")
```

### 4. Extraction Result Pipeline

```python
from datetime import datetime
from models import ExtractionResult, Observation
from data import ObservationStore

# LLM extracts data
extraction_result = ExtractionResult(
    extraction_id="EXT-2024-001",
    observation=observation,  # From step 1
    source_document_url="https://example.com/prospectus.pdf",
    extraction_timestamp=datetime.now(),
    extraction_agent="llm-claude",
    extraction_model="claude-opus-4.6",
    processing_time_seconds=5.23
)

# Later, after QC approval, store the observation
store = ObservationStore("data/extracted")
store.add_observations([extraction_result.observation])
```

### 5. QC Validation Results

```python
from datetime import datetime
from models import QCResult, QCStatus

qc_result = QCResult(
    qc_id="QC-2024-001",
    observation_id="OBS-2024-001",
    extraction_id="EXT-2024-001",
    qc_timestamp=datetime.now(),
    qc_agent="qc-validator",
    qc_status=QCStatus.PASSED,
    qc_score=95.0,
    qc_flags=[],
    validation_errors=[],
    validation_warnings=[],
    summary="Observation passed all validation checks",
    recommended_action="approve"
)
```

## Validation Rules

### Leverage Validation
```python
# Must sum to ~100% (±5% tolerance)
observation.leverage_debt_pct = 60
observation.leverage_equity_pct = 40
# Valid: 60 + 40 = 100

observation.leverage_debt_pct = 65
observation.leverage_equity_pct = 30
# ERROR: 65 + 30 = 95 (within tolerance)

observation.leverage_debt_pct = 70
observation.leverage_equity_pct = 20
# ERROR: 70 + 20 = 90 (outside tolerance)
```

### Cost of Capital Validation
```python
# Real costs must be <= nominal costs
observation.kd_nominal = 0.05
observation.kd_real = 0.02
# Valid

# Cost of debt must be <= cost of equity
observation.kd_nominal = 0.05
observation.ke_nominal = 0.10
# Valid

# WACC must be within bounds
observation.wacc_nominal = 0.06  # Between 0.05 (kd) and 0.10 (ke)
# Valid
```

### Country Code
```python
# Must be ISO 3166-1 alpha-3 code
observation.country = "USA"   # Valid
observation.country = "GBR"   # Valid
observation.country = "BRA"   # Valid
observation.country = "US"    # ERROR: Only 2 letters
observation.country = "us"    # ERROR: Must be uppercase
```

## File Paths

All created files are in:
```
/sessions/fervent-tender-allen/mnt/ET Finance/oefo/
```

Key files:
- **models.py** - 765 lines, all Pydantic models
- **data/storage.py** - 603 lines, ObservationStore and DocumentStore
- **data/__init__.py** - Public API exports
- **DATA_MODEL_SUMMARY.md** - Comprehensive documentation
- **QUICK_START.md** - This file

## Common Tasks

### Initialize Storage
```python
from data import ObservationStore, DocumentStore

obs_store = ObservationStore("data/final")
doc_store = DocumentStore("data/raw")
```

### Add Multiple Observations
```python
observations = [obs1, obs2, obs3]
count = obs_store.add_observations(observations)
print(f"Added {count} observations")
```

### Complex Filtering
```python
df = obs_store.get_all()

# Use pandas for complex queries
filtered = df[
    (df['country'] == 'USA') &
    (df['year_of_observation'] >= 2020) &
    (df['kd_nominal'] < 0.06)
]
```

### Check Document Deduplication
```python
# By URL
exists_by_url = doc_store.is_duplicate(
    url="https://example.com/doc.pdf"
)

# By content hash
exists_by_hash = doc_store.is_duplicate(
    content_hash="abc123..."
)

# Either
exists = doc_store.is_duplicate(
    url="https://example.com/doc.pdf",
    content_hash="abc123..."
)
```

## Type Hints for IDE Support

All models use proper type hints:
```python
from models import Observation
from typing import Optional

# IDE will auto-complete
obs: Observation
obs.country  # type: str
obs.kd_nominal  # type: Optional[float]
obs.qc_flags  # type: Optional[List[str]]
```

## Error Handling

```python
from pydantic import ValidationError
from models import Observation

try:
    obs = Observation(
        observation_id="OBS-001",
        # ... other required fields ...
        country="XX"  # Invalid: Not 3 letters
    )
except ValidationError as e:
    print(f"Validation error: {e}")
```

## Next Steps

1. Review `DATA_MODEL_SUMMARY.md` for detailed documentation
2. Check `models.py` for all available enums and fields
3. Explore `data/storage.py` for storage operations
4. Integrate with extraction pipeline
5. Connect QC agent for validation results

---

See `DATA_MODEL_SUMMARY.md` for comprehensive documentation.
