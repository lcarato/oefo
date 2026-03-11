# OEFO Configuration Module Summary

The authoritative configuration package lives in `src/oefo/config/`.

## Files

- `src/oefo/config/settings.py`: runtime settings, directory helpers, API-key
  validation, and masked config display.
- `src/oefo/config/taxonomy.py`: controlled vocabularies and validation helpers
  for technologies, scale, source types, QC states, and related enums.
- `src/oefo/config/thresholds.py`: plausibility ranges and QC thresholds used by
  rules-based validation.
- `src/oefo/config/sources.py`: source registries for DFIs, regulators, and the
  tracked company universe.
- `src/oefo/config/__init__.py`: curated re-export surface for the modules above.

## Runtime expectations

- Directory paths are derived from `OEFO_BASE_DIR` or the current working
  directory.
- Host prerequisites such as Poppler and Tesseract are checked by
  `scripts/oefo_env_check.py`, not by this package.
- Cloud credentials can be provided with `ANTHROPIC_API_KEY` or
  `OPENAI_API_KEY`. Local-only use is supported with `OEFO_LLM_PROVIDER=ollama`.

## Common imports

```python
from oefo.config import DATA_DIR, RAW_DIR, validate_technology, DFI_SOURCES
from oefo.config.settings import get_config, print_config
```

## Verification

- `tests/test_config.py`
- `tests/test_taxonomy.py`
