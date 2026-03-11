# OEFO

OEFO is a Python toolkit for collecting, extracting, validating, and exporting
energy-finance observations from publicly available documents.

## Install

### System prerequisites

macOS:
```bash
brew install poppler tesseract
```

Ubuntu or Debian:
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr
```

### Python setup

```bash
git clone https://github.com/lcarato/oefo.git
cd oefo
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/oefo_env_check.py
```

## Quick verification

```bash
oefo --help
python -m oefo --help
python scripts/oefo_smoke_test.py
pytest -q
```

## Common commands

```bash
oefo config --validate
oefo scrape ifc
oefo extract ./data/raw/ifc/report.pdf --source-type dfi
oefo extract-batch ./data/raw/ifc --source-type dfi
oefo qc --full
oefo export --format excel --output results.xlsx
oefo dashboard
```

The dashboard binds to `127.0.0.1` by default. To expose it intentionally,
pass `--public`, or set `--host 0.0.0.0` when you control the client origin.

## Layout

```text
src/oefo/
  cli.py
  llm_client.py
  models.py
  config/
  dashboard/
  data/
  extraction/
  outputs/
  qc/
  scrapers/
```

## Docs

- `docs/INSTALL.md`
- `docs/ARCHITECTURE.md`
- `docs/OPENCLAW.md`

## Development

```bash
python -m build
python -m twine check dist/*
pytest -q
```
