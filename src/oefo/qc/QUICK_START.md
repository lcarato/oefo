# OEFO QC Quick Start

## CLI

```bash
oefo qc --input data/extracted
oefo qc --rules-only --input data/extracted
oefo qc --full --input data/extracted --output outputs/qc_report.json
```

## Python

```python
from oefo.qc import QCAgent

agent = QCAgent(enable_rules=True, enable_stats=True, enable_llm=False)
```
