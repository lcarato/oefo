# Installation

## 1. System dependencies

### macOS
```bash
brew install poppler tesseract
```

### Ubuntu or Debian
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr
```

## 2. Python environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 3. Configure credentials

Copy `.env.example` to `.env` and set at least one provider key:

- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

If you use a local Ollama instance instead of a cloud provider, set
`OEFO_LLM_PROVIDER=ollama`. Smoke tests and import checks do not require a
cloud API key.

## 4. Validate the installation

```bash
python scripts/oefo_env_check.py
oefo --help
python -m oefo --help
python scripts/oefo_smoke_test.py
pytest -q
```

## 5. Dashboard safety

The dashboard binds to `127.0.0.1` by default. If you need remote access, tunnel
it or pass an explicit bind address intentionally.

## 6. Troubleshooting

- Missing `pdftoppm` or `pdfinfo`: install Poppler.
- Missing `tesseract`: install Tesseract OCR.
- `oefo` command not found: activate the virtual environment and reinstall with
  `python -m pip install -e ".[dev]"`.
- Import errors from the repo root: make sure the package is installed from the
  `src` layout rather than run from an old flat checkout state.
