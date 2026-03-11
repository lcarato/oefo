# OEFO Full Pipeline Skill

## Purpose

Run the repository's scrape, extract, QC, and export stages with commands that
match the current CLI surface.

## Environment Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/oefo_env_check.py
```

## Steps

### Phase 1: Scrape Sources

```bash
python -m oefo scrape ifc
python -m oefo scrape ebrd
python -m oefo scrape gcf
python -m oefo scrape aneel
python -m oefo scrape aer
python -m oefo scrape ofgem
python -m oefo scrape ferc
python -m oefo scrape sec
```

### Phase 2: Extract Financial Data

```bash
python -m oefo extract-batch data/raw/ifc --source-type dfi
python -m oefo extract-batch data/raw/ebrd --source-type dfi
python -m oefo extract-batch data/raw/gcf --source-type dfi
python -m oefo extract-batch data/raw/aneel --source-type regulatory
python -m oefo extract-batch data/raw/aer --source-type regulatory
python -m oefo extract-batch data/raw/ofgem --source-type regulatory
python -m oefo extract-batch data/raw/ferc --source-type regulatory
python -m oefo extract-batch data/raw/sec --source-type corporate
```

### Phase 3: Quality Control

```bash
python -m oefo qc --full --input data/extracted --output outputs/qc_report.json
```

### Phase 4: Export

```bash
python -m oefo export --format excel --output outputs/oefo.xlsx
python -m oefo export --format csv --output outputs/oefo.csv
python -m oefo status --detailed
```
