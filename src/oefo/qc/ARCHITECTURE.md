# OEFO QC Architecture

The QC package implements a layered validation pipeline:

1. rules-based checks
2. statistical checks
3. optional LLM review

## Modules

- `rules.py`
- `benchmarks.py`
- `llm_review.py`
- `agent.py`

`QCAgent` composes those layers and is invoked by the `oefo qc` command.
