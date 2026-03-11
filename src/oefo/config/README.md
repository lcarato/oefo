# OEFO Configuration Module

This package provides the runtime configuration surface for OEFO.

## Modules

- `taxonomy.py`: enums and validation helpers for technologies, source types,
  scales, QC states, and related controlled vocabularies
- `thresholds.py`: plausibility ranges and QC thresholds
- `sources.py`: registries for DFIs, regulators, and tracked companies
- `settings.py`: environment-driven runtime settings and directory helpers
- `__init__.py`: re-export layer for convenient imports

## Typical usage

```python
from oefo.config import DATA_DIR, DFI_SOURCES, validate_technology
from oefo.config.settings import get_config
```
