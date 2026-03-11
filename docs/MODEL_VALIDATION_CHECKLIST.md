# OEFO Data Model Validation Checklist

Use this checklist against the current `src` layout.

## File structure

- `src/oefo/models.py` exists.
- `src/oefo/data/storage.py` exists.
- `src/oefo/data/__init__.py` re-exports storage helpers.

## Model coverage

- `Observation` validates required fields and basic financial constraints.
- `ProvenanceChain` computes traceability level from supplied evidence.
- `RawDocument`, `ExtractionResult`, and `QCResult` import cleanly.
- Enums in `oefo.models` and `oefo.config.taxonomy` stay aligned.

## Storage coverage

- `ObservationStore` can create a storage directory and write Parquet data.
- `ObservationStore.query()` rejects unknown columns.
- `DocumentStore` supports registration and duplicate checks.
- Hashing and JSON serialization helpers remain importable from `oefo.data`.

## Test references

- `tests/test_models.py`
- `tests/test_taxonomy.py`
- `tests/test_imports.py`

## Manual spot checks

```bash
python - <<'PY'
from oefo.models import Observation
from oefo.data import ObservationStore, DocumentStore
print("import-ok")
PY
```
