# OEFO Quick Start

This guide uses the current `src/oefo/` package layout.

## Imports

```python
from datetime import date

from oefo.data import DocumentStore, ObservationStore, compute_content_hash
from oefo.models import ConfidenceLevel, Observation, RawDocument, SourceType
```

## Create and store an observation

```python
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
print(store.get_all())
```

## Register a source document

```python
doc_store = DocumentStore("data/raw")

document = RawDocument(
    document_id="doc-001",
    source_type=SourceType.DFI_DISCLOSURE,
    source_institution="IFC",
    document_title="Example report",
    source_url="https://example.com/report.pdf",
    content_hash=compute_content_hash(b"example"),
)

doc_store.register_document(document)
```

## Validate the install

```bash
python scripts/oefo_env_check.py
python scripts/oefo_smoke_test.py
pytest -q
```

## Next references

- `docs/INSTALL.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_MODEL_SUMMARY.md`
