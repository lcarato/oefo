# OEFO Data Model Summary

OEFO stores validated domain objects in `src/oefo/models.py` and file-backed
storage helpers in `src/oefo/data/storage.py`.

## Core models

- `Observation`: the main energy-finance record, with cross-field validation for
  values such as leverage and cost-of-capital relationships.
- `ProvenanceChain`: traceability metadata linking extracted values to source
  documents, pages, and quotes.
- `ExtractionResult`: intermediate extraction output before QC approval.
- `QCResult`: structured QC outcome for rules, statistics, and optional LLM review.
- `RawDocument`: metadata for scraped or downloaded source files.

## Storage layer

- `ObservationStore` writes and reads `observations.parquet` in a chosen
  directory and supports querying, CSV export, and Excel export.
- `DocumentStore` maintains a JSON index and per-document metadata for raw files
  and duplicate detection.

## Typical usage

```python
from datetime import date

from oefo.data import ObservationStore
from oefo.models import ConfidenceLevel, Observation, SourceType

store = ObservationStore("data/final")

observation = Observation(
    observation_id="example-001",
    source_type=SourceType.DFI_DISCLOSURE,
    source_institution="IFC",
    extraction_date=date(2024, 1, 1),
    extraction_method="llm",
    confidence_level=ConfidenceLevel.HIGH,
    project_or_entity_name="Example Solar Project",
    country="BRA",
    technology_l2="solar_pv",
    year_of_observation=2024,
)

store.add_observations([observation])
```

## Verification

- `tests/test_models.py`
- `tests/test_packaging.py`
