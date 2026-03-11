# OEFO QC Implementation Summary

The active QC implementation is the code in `src/oefo/qc/`.

## Current modules

- `rules.py`: deterministic validation rules
- `benchmarks.py`: statistical comparisons
- `llm_review.py`: optional model-assisted review
- `agent.py`: orchestration
- `__init__.py`: public exports

## CLI surface

```bash
oefo qc
oefo qc --rules-only
oefo qc --full
```
