---
name: oefo-full-pipeline
description: Run the complete OEFO pipeline end-to-end (scrape → extract → QC → export)
---

# OEFO Full Pipeline Skill

## Purpose
Execute the complete data pipeline from scraping through to database export.

## Environment Setup
```bash
# Required environment variables
export ANTHROPIC_API_KEY="your-key-here"
# Optional fallback providers
export OPENAI_API_KEY="your-key-here"
export GOOGLE_API_KEY="your-key-here"

# Optional configuration
export OEFO_LLM_PROVIDER="anthropic"          # preferred provider
export OEFO_LLM_FALLBACK_ORDER="anthropic,openai,google,ollama"
export OEFO_VISION_MODEL="claude-sonnet-4-20250514"
export OEFO_QC_MODEL="claude-sonnet-4-20250514"
```

## Steps

### Phase 1: Scrape Sources
```bash
# DFI portals (priority order)
python -m oefo scrape ifc
python -m oefo scrape ebrd
python -m oefo scrape gcf

# Regulatory filings (Phase 1 regulators)
python -m oefo scrape aneel
python -m oefo scrape aer
python -m oefo scrape ofgem
python -m oefo scrape ferc

# Corporate filings
python -m oefo scrape sec
```

### Phase 2: Extract Financial Data
```bash
# Extract from all downloaded documents
python -m oefo extract-batch data/raw/ --source-type auto
```
The pipeline auto-detects source type from directory structure and applies the appropriate extraction prompts and tier routing.

### Phase 3: Quality Control
```bash
# Full 3-layer QC
python -m oefo qc --full
```

### Phase 4: Export
```bash
# Generate all outputs
python -m oefo export --format excel --output outputs/oefo_database.xlsx
python -m oefo export --format csv --output outputs/oefo_database.csv
python -m oefo export --format parquet --output outputs/oefo_database.parquet

# Show final statistics
python -m oefo status
```

## Scheduling (Phase 3 automation)
For recurring runs, use cron or OpenClaw scheduler:
- Monthly: DFI scrapers + extraction + QC
- Quarterly: Corporate filings (SEC 10-K/10-Q cycle)
- Per regulatory calendar: Regulatory scrapers
