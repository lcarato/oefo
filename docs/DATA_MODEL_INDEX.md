# OEFO Data Model Index

The active data-model implementation is split across two modules:

- `src/oefo/models.py`
- `src/oefo/data/storage.py`

## `src/oefo/models.py`

Defines the core Pydantic models and enums used across the pipeline, including:

- `Observation`
- `ExtractionResult`
- `QCResult`
- `RawDocument`
- `ProvenanceChain`
- enums such as `SourceType`, `ConfidenceLevel`, `Scale`, `ExtractionTier`,
  `QCStatus`, and `TraceabilityLevel`

## `src/oefo/data/storage.py`

Provides the file-backed storage layer:

- `ObservationStore` for Parquet-backed observation storage
- `DocumentStore` for JSON-backed raw-document indexing
- `compute_content_hash()` and JSON serialization helpers

## Public imports

```python
from oefo.models import Observation, RawDocument
from oefo.data import ObservationStore, DocumentStore, compute_content_hash
```

## Verification

- `tests/test_models.py`
- `tests/test_taxonomy.py`
- `tests/test_imports.py`
