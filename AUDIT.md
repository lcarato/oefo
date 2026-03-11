# OEFO Repository Audit

**Date:** 2026-03-11
**Status:** Comprehensive diagnostic covering packaging, runtime safety, and production readiness

---

## 1. Current File Tree (Flat Layout at Repo Root)

```
oefo/ (repository root - acts as package directory)
├── __init__.py              # Package marker; defines __version__ = "0.1.0"
├── __main__.py              # Entry for `python -m oefo`
├── cli.py                   # Main CLI implementation (8 commands)
├── models.py                # Pydantic v2 data models (ExtractionTier, Observation, QCResult, etc.)
├── llm_client.py            # Model-agnostic LLM router (Anthropic → OpenAI → Ollama)
│
├── config/                  # Configuration & settings
│   ├── __init__.py
│   ├── settings.py          # Runtime settings (paths, API keys, model params)
│   ├── sources.py           # Data source definitions
│   ├── taxonomy.py          # Energy finance taxonomy
│   ├── thresholds.py        # QC thresholds and benchmarks
│   └── README.md
│
├── extraction/              # PDF extraction pipeline (3 tiers)
│   ├── __init__.py
│   ├── pipeline.py          # ExtractionPipeline orchestrator
│   ├── text.py              # Tier 1: Native text extraction (pdfplumber)
│   ├── ocr.py               # Tier 2: Tesseract OCR processing
│   ├── vision.py            # Tier 3: Claude Vision API
│   ├── prompts/             # Source-specific extraction prompts
│   │   ├── __init__.py
│   │   ├── dfi.py           # Development Finance Institution prompts
│   │   ├── regulatory.py    # Regulatory agency prompts
│   │   ├── corporate.py     # Corporate filing prompts
│   │   └── bond.py          # Bond document prompts
│   └── ARCHITECTURE.md
│
├── scrapers/                # Web data scrapers
│   ├── __init__.py
│   ├── base.py              # BaseScraper abstract class
│   ├── ifc.py, ebrd.py, gcf.py          # DFI scrapers
│   ├── sec_edgar.py         # SEC EDGAR corporate scraper
│   ├── regulatory/          # Regulatory agency scrapers
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── aneel.py         # Brazil regulatory scraper
│   │   ├── aer.py           # Australia regulatory scraper
│   │   ├── ofgem.py         # UK regulatory scraper
│   │   └── ferc.py          # US regulatory scraper
│   └── ARCHITECTURE.md
│
├── qc/                      # Quality control (3-layer agent)
│   ├── __init__.py
│   ├── agent.py             # QCAgent orchestrator
│   ├── rules.py             # Layer 1: Rule-based validation
│   ├── benchmarks.py        # Layer 2: Statistical benchmarks
│   ├── llm_review.py        # Layer 3: LLM cross-validation
│   └── ARCHITECTURE.md
│
├── outputs/                 # Data exporters
│   ├── __init__.py
│   ├── excel.py             # Excel workbook generator
│   ├── csv_export.py        # CSV, Parquet, JSON exporters
│   └── visualisations.py    # Dashboard charts
│
├── dashboard/               # Real-time SSE monitoring
│   ├── __init__.py
│   ├── server.py            # Async HTTP + SSE server
│   ├── tracker.py           # Pipeline state tracker
│   └── index.html           # Frontend dashboard
│
├── data/                    # Observation storage layer
│   ├── __init__.py
│   └── storage.py           # ObservationStore persistence
│
├── tests/                   # Test suite (minimal)
│   ├── __init__.py
│   └── test_models.py       # Pydantic model validation tests
│
├── setup.py                 # setuptools configuration (legacy; redundant)
├── pyproject.toml           # Modern PEP 517/518 build config (created in prior fix)
├── requirements.txt         # pip dependencies (not referenced by setup.py)
├── MANIFEST.in              # Include additional files in dist
│
├── README.md                # Quick start & architecture overview
├── QUICK_START.md
├── .env.example             # Example environment variables
└── [other docs]/
    ├── CODE_SAMPLES.md
    ├── CONFIG_MODULE_SUMMARY.md
    ├── DATA_MODEL_INDEX.md
    ├── DATA_MODEL_SUMMARY.md
    ├── OEFO_Agent_Autonomous_Operations.md
    ├── SCRAPERS_REFERENCE.md
    └── SCRAPERS_SUMMARY.txt
```

**Layout Summary:**
- **Flat structure at repository root** — all Python packages (config, extraction, scrapers, qc, outputs, dashboard, data) are immediate subdirectories of `/sessions/sharp-lucid-cori/oefo/`
- **No src/ directory** — there is no `src/oefo/` or similar; the repo root IS the package directory
- **Module is named `oefo`** — files import as `from oefo.X import Y` or use relative imports `from .X import Y`

---

## 2. Import Graph Summary

### Relative Imports (All Use Dot Prefix)

All internal relative imports correctly use the dot-prefix convention (PEP 328):

```python
from .cli import main                              # __main__.py
from . import __version__                          # cli.py
from .config.settings import RAW_DIR               # cli.py handlers
from .extraction import ExtractionPipeline         # cli.py
from .qc import QCAgent                            # cli.py
from .models import Observation                    # cli.py handlers
from oefo.dashboard.tracker import PipelineTracker # dashboard/server.py
```

**Relative imports found:** 54+ instances across all modules
**Absolute imports to `oefo` package:** Used in tests and some qc/ modules (e.g., `from oefo.models import Observation`)

### Package Expectation

The codebase expects to be installed as a package, with:
- `oefo` resolvable as the top-level package name
- Submodules accessible as `oefo.config`, `oefo.extraction`, `oefo.scrapers`, `oefo.qc`, `oefo.outputs`, `oefo.dashboard`
- Entry point script `oefo` callable after `pip install`

---

## 3. Command Map (CLI Commands from cli.py)

| Command | Handler | Purpose |
|---------|---------|---------|
| `scrape <source>` | `handle_scrape()` | Run web scraper for DFI/regulatory source (ifc, ebrd, gcf, sec, aneel, aer, ofgem, ferc, all) |
| `extract <pdf>` | `handle_extract()` | Extract financing data from single PDF; requires `--source-type` (regulatory, dfi, corporate, bond) |
| `extract-batch <dir>` | `handle_extract_batch()` | Batch-process PDFs from directory; supports `--parallel` workers (default 4) |
| `qc [--rules-only\|--full]` | `handle_qc()` | Run QC validation: rules-only (Layer 1), standard (Layers 1+2), or full (all 3 layers + LLM) |
| `export --format <fmt>` | `handle_export()` | Export observations to excel/csv/parquet/json; supports `--filter` for DataFrame queries |
| `dashboard [--port]` | `handle_dashboard()` | Start async SSE server for real-time pipeline monitoring (default: localhost:8765) |
| `status [--detailed]` | `handle_status()` | Show pipeline statistics (doc counts, API config, directory sizes) |
| `config [--validate]` | `handle_config()` | Display or validate current configuration (API keys, directories) |

**Global flags:**
- `--version` — show version
- `--verbose, -v` — enable DEBUG logging
- `--config <path>` — custom config file path (not implemented in handlers)

**Entry points:**
1. `oefo` (console script) → `oefo.cli:main()` [currently broken; see Packaging Mismatch]
2. `python -m oefo` → `__main__.py` → `cli.main()` [works from repo root only]

---

## 4. Packaging Mismatch Analysis

### Critical Issue: Flat Layout Won't Pip Install Correctly

#### Problem 1: Entry Point Registration Failure

**setup.py (line 74-77):**
```python
entry_points={
    'console_scripts': [
        'oefo=oefo.cli:main',
    ],
},
```

**pyproject.toml (line 33-34):**
```toml
[project.scripts]
oefo = "oefo.cli:main"
```

**Why it fails:**
- Entry point expects a package named `oefo` with submodule `cli`
- Current layout: `oefo/` IS the package root, so the module is at `oefo.cli`
- After `pip install`, the package is unpacked into site-packages as `oefo/`
- Entry point script tries to load `oefo.cli:main` — which works!
- **BUT:** The working directory is NOT the repo root, so relative imports fail

#### Problem 2: Relative Imports Break After Installation

**Code in cli.py (line 21):**
```python
from . import __version__
```

**Code in extraction/pipeline.py (line 21):**
```python
from ..models import ExtractionTier
```

**Why it fails:**
- Relative imports use `.` prefix, expecting to be a submodule of a parent package
- **Correct structure for relative imports:** `src/oefo/__init__.py`, `src/oefo/cli.py`
- **Current structure:** `oefo/__init__.py`, `oefo/cli.py`
- When installed to site-packages, `oefo` IS the top-level package
- Relative import `from . import X` in `oefo/cli.py` tries to import from parent of `oefo` — which doesn't exist
- Result: `ImportError: attempted relative import in non-package`

#### Problem 3: setup.py Declares Wrong package_dir

**setup.py (line 34-35):**
```python
packages=find_packages(where='.'),
package_dir={'': '.'},
```

**Analysis:**
- `package_dir={'': '.'}` tells setuptools: "packages are in the current directory"
- `find_packages(where='.')` discovers: `config`, `extraction`, `scrapers`, `qc`, `outputs`, `dashboard`, `data`, `tests`
- Missing: the parent package `oefo` itself is NOT included!
- Distribution includes subpackages but NOT the root `__init__.py`
- Result: Entry point can't find `oefo` module; `ImportError: No module named 'oefo'`

#### Problem 4: Duplicate Configuration Files

Both `setup.py` and `pyproject.toml` define build system and metadata:

**setup.py:**
- Uses setuptools declarative syntax
- References `find_packages()` and `package_dir`
- Defines entry points, install_requires, extras_require

**pyproject.toml (created in prior fix round):**
- Uses PEP 517/518 modern format
- Delegates to setuptools backend
- Declares version dynamically from `oefo.__version__`

**Conflict:** Both files present but inconsistent package layout declarations.

---

## 5. Runtime Risk Summary

### Risk 1: Dashboard Binds to 0.0.0.0 (Security)

**File:** `dashboard/server.py:279-287` (start_server function)
**Code:**
```python
def start_server(host: str = "0.0.0.0", port: int = 8765, ...):
    """Start the dashboard server programmatically (called by cli.py)."""
```

**CLI default (cli.py:246):**
```python
parser.add_argument(
    '--host',
    type=str,
    default='0.0.0.0',
    help='Host to bind (default: 0.0.0.0)'
)
```

**Risk:**
- `0.0.0.0` listens on ALL network interfaces (exposed to network)
- Unencrypted HTTP; no authentication; no rate limiting
- Dashboard exposes pipeline statistics (doc counts, directory paths, configuration details)
- Remote access if server is public-facing

**Recommendation:** Default to `127.0.0.1` (localhost only)

### Risk 2: Wildcard CORS Header (Security)

**File:** `dashboard/server.py:205, 229`

**Code:**
```python
f"Access-Control-Allow-Origin: *\r\n"              # line 205 (_send_response)
"Access-Control-Allow-Origin: *\r\n"               # line 229 (_handle_sse)
```

**Risk:**
- Allows any domain to make cross-origin requests to the dashboard
- Enables data exfiltration from other sites
- No CSRF protection

**Recommendation:** Remove or restrict to specific domains (if dashboard needs to be remotely accessible)

### Risk 3: Config Module Delayed Directory Creation

**File:** `config/settings.py:145-152`

**Design (prior fix):**
```python
def ensure_directories() -> None:
    """Create required directories if they don't exist.

    Call this explicitly before pipeline operations rather than at import time,
    to avoid side effects when simply importing the config module.
    """
    for directory in [DATA_DIR, RAW_DIR, EXTRACTED_DIR, FINAL_DIR, LOGS_DIR, CACHE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
```

**Status:** ✓ Good — directories are NOT created at import time
**Requirement:** Callers must explicitly invoke `ensure_directories()` before pipeline operations
**Current usage:** CLI handlers should call `ensure_directories()` on startup

### Risk 4: Extraction Pipeline Imports ExtractionTier from models

**File:** `extraction/pipeline.py:21`

**Code:**
```python
from ..models import ExtractionTier
```

**Risk:**
- Relative import from parent package (`..`) assumes flat layout
- Will fail after pip install (see Packaging Mismatch above)

**Status:** ✓ Code is correct; issue is at installation layer

### Risk 5: No API Key Validation on Startup

**File:** `cli.py`, handlers (e.g., `handle_extract`)

**Observation:**
- LLM operations assume ANTHROPIC_API_KEY is set
- No preflight check before launching extraction pipeline
- Errors only surface when API call is made

**Recommendation:** Add startup check in `main()` or per-handler to validate API keys before processing

---

## 6. Missing System Prerequisites

The codebase requires several OS-level dependencies not listed in `requirements.txt`:

### Required External Tools

| Tool | Package | Used By | Status |
|------|---------|---------|--------|
| **Poppler** (pdftoimage) | `poppler-utils` (Debian/Ubuntu) or `poppler` (Homebrew) | `extraction/ocr.py` via `pdf2image` | ⚠️ Not checked at runtime |
| **Tesseract OCR** | `tesseract-ocr` (system package) | `extraction/ocr.py` via `pytesseract` | ⚠️ Not checked at runtime |
| **ImageMagick** (optional) | `imagemagick` | PDF preprocessing (optional) | Optional |

### Python Version

- **Declared:** Python 3.10+ (setup.py line 36)
- **Not enforced:** No runtime check for version

### Missing Preflight Checks

```python
# Example: should verify before first use
import shutil
if shutil.which('tesseract') is None:
    raise RuntimeError("Tesseract OCR not found. Install: apt-get install tesseract-ocr")
if shutil.which('pdftoimage') is None:
    raise RuntimeError("Poppler not found. Install: apt-get install poppler-utils")
```

---

## 7. Documentation Mismatches

### Existing Documentation

| File | Status | Issue |
|------|--------|-------|
| `README.md` | Present | References `pip install -e .` (works from repo root only) |
| `QUICK_START.md` | Present | Same issue |
| `OEFO_User_Guide.docx` | External file | Not in git repo |
| `OEFO_Installation_Procedure.docx` | External file | Not in git repo |

### Missing Documentation

| Document | Required For | Status |
|----------|--------------|--------|
| `INSTALL.md` | Step-by-step installation guide (accounts for src/ restructure) | Missing |
| `ARCHITECTURE.md` (root) | High-level system design and data flow | Missing (partial: extraction/ARCHITECTURE.md exists) |
| `DEVELOPMENT.md` | Contributing guidelines, dev setup, testing | Missing |
| `DEPLOYMENT.md` | Production deployment (systemd, Docker, cloud) | Missing |
| `TROUBLESHOOTING.md` | Common errors and solutions | Missing |

### Partially Fixed in Prior Round

- `config/settings.py` documentation updated (good)
- Directory creation deferred from import time (good)

---

## 8. Security Defaults Review

### 8.1 Network Binding

| Component | Default | Risk | Recommendation |
|-----------|---------|------|---|
| Dashboard (HTTP) | `0.0.0.0:8765` | Exposed to network | Change to `127.0.0.1:8765` |
| Dashboard (CORS) | `Access-Control-Allow-Origin: *` | Cross-origin attacks | Remove or restrict |
| LLM API calls | Via HTTP (Anthropic endpoint) | Standard SSL/TLS | ✓ Safe |

### 8.2 Credential Handling

| Item | Status | Notes |
|------|--------|-------|
| API keys in environment | ✓ Good | Loaded from `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` |
| .env file support | ✓ Good | `.env.example` provided |
| Secrets in logs | ⚠️ Masked | `config.py:284` masks API keys in output: `"***"` |
| Config file paths | ⚠️ Not checked | CLI accepts `--config <path>` but not implemented in handlers |

### 8.3 File Permissions

| Path | Permissions | Risk | Status |
|------|-------------|------|--------|
| `data/raw/` | World-readable (default) | Exposes scraped documents | ⚠️ No umask set |
| `data/extracted/` | World-readable (default) | Exposes extracted data | ⚠️ No umask set |
| `.env` | World-readable (default) | Exposes API keys | ⚠️ Not enforced |

**Recommendation:** Document umask requirements; add startup warnings if files are too permissive

---

## 9. Test Coverage Gaps

### Current Test Suite

**File:** `tests/test_models.py` (only test file)
**Content:** Pydantic model validation tests for `Observation`, `ExtractionResult`, `QCResult`, etc.
**Coverage:** ~50 model tests, basic validation

### Missing Test Coverage

| Module | Component | Tests | Status |
|--------|-----------|-------|--------|
| `cli.py` | Command handlers (scrape, extract, qc, export, etc.) | 0 | ✗ Missing |
| `extraction/` | Pipeline orchestration, tier logic | 0 | ✗ Missing |
| `scrapers/` | Web scraper implementations | 0 | ✗ Missing |
| `qc/` | QC layers (rules, benchmarks, LLM) | 0 | ✗ Missing |
| `outputs/` | Export generators (Excel, CSV, Parquet) | 0 | ✗ Missing |
| `dashboard/` | Server and tracker | 0 | ✗ Missing |
| `config/` | Settings loading and validation | 0 | ✗ Missing |
| `data/` | Storage layer (ObservationStore) | 0 | ✗ Missing |

### Missing Test Infrastructure

- No `pytest` configuration (only stub in `pyproject.toml`)
- No fixtures for sample PDFs, mock API responses, temp directories
- No integration tests (end-to-end pipeline)
- No smoke tests (all CLI commands)
- No CI/CD pipeline (.github/workflows/)

---

## 10. Prioritized Backlog with Labels

### P0 Blockers — Must Fix Before Release

#### P0.1: Package Won't Install via pip

**Problem:** Flat layout with entry points to `oefo.cli:main` won't work after pip install; relative imports will fail.

**Root causes:**
- No `src/oefo/` subdirectory (flat layout)
- `package_dir` and `find_packages()` don't include top-level package
- Relative imports (`from . import`, `from ..models import`) expect package hierarchy that doesn't exist

**Solution (choose one):**

**Option A (Recommended):** Restructure to src/ layout
```
src/
└── oefo/
    ├── __init__.py
    ├── cli.py
    ├── models.py
    └── [all packages]
```

**Steps:**
1. Create `src/oefo/` directory
2. Move all oefo code into `src/oefo/`
3. Update `setup.py`: `package_dir={'': 'src'}` and `packages=find_packages(where='src')`
4. Update `pyproject.toml` build backend to match
5. Verify `oefo` entry point now works
6. Verify `python -m oefo` still works
7. Update README.md and QUICK_START.md with new install instructions

**Option B (Workaround):** Keep flat layout but remove relative imports
- Replace all `from . import X` with `from oefo import X`
- Replace all `from ..X import Y` with `from oefo.X import Y`
- Entry point becomes self-contained (no parent package dependencies)
- Trade-off: Less maintainable; non-standard Python practice

**Effort:** Option A: 2-3 hours; Option B: 1-2 hours
**Recommendation:** Option A (proper structure)

---

#### P0.2: Console Script and `python -m oefo` Fail After pip install

**Problem:** Related to P0.1. Entry point tries to load `oefo.cli:main` but module isn't found correctly.

**Verification:**
```bash
pip install -e .
oefo --version  # Fails: No module named 'oefo'
python -m oefo --version  # Fails: can't find relative imports
```

**Fix:** Implement P0.1 (src/ restructure)

**Acceptance criteria:**
```bash
pip install -e .
oefo --version  # ✓ Shows version
oefo scrape --help  # ✓ Shows help
python -m oefo --version  # ✓ Works
```

---

#### P0.3: Dashboard Binds to 0.0.0.0 by Default (Security)

**Problem:** Dashboard exposes pipeline status on all network interfaces without authentication.

**File:** `cli.py:246`, `dashboard/server.py:279`

**Solution:**
1. Change default host from `0.0.0.0` to `127.0.0.1` in both files
2. Update help text to document security implications
3. Document how to expose dashboard securely (reverse proxy, VPN, Docker)

**Changes:**
```python
# cli.py
parser.add_argument(
    '--host',
    type=str,
    default='127.0.0.1',  # Changed from '0.0.0.0'
    help='Host to bind (default: 127.0.0.1; use 0.0.0.0 only behind reverse proxy)'
)

# dashboard/server.py
def start_server(host: str = "127.0.0.1", port: int = 8765, ...):  # Changed
```

**Verification:**
```bash
oefo dashboard  # Binds to 127.0.0.1:8765
```

**Effort:** 15 minutes

---

#### P0.4: Wildcard CORS Header (Security)

**Problem:** Dashboard allows cross-origin requests from any domain.

**File:** `dashboard/server.py:205, 229`

**Solution:**
1. Remove wildcard CORS header if dashboard is not meant to be accessed from browser
2. If browser access needed: Add CORS configuration that restricts origin

**Option 1 (Recommended if no browser access needed):**
```python
# Remove these lines:
# f"Access-Control-Allow-Origin: *\r\n"
```

**Option 2 (If browser access needed):**
```python
ALLOWED_ORIGINS = os.environ.get("OEFO_DASHBOARD_ORIGINS", "127.0.0.1:8765")
# Parse and validate origin header in request
```

**Effort:** 30 minutes

---

### P1 Production-Readiness — Should Fix Before Release

#### P1.1: No System Dependency Preflight Checks

**Problem:** Pipeline fails at runtime if Tesseract or Poppler not installed; no clear error message.

**Solution:**
1. Create `config/system.py` with preflight checks
2. Call preflight checks in `cli.main()` before processing

**Code:**
```python
# config/system.py
import shutil
import sys

def check_system_dependencies():
    """Verify all required OS-level tools are installed."""
    errors = []

    if shutil.which('tesseract') is None:
        errors.append(
            "Tesseract OCR not found.\n"
            "  Install: apt-get install tesseract-ocr (Debian/Ubuntu)\n"
            "           brew install tesseract (macOS)"
        )

    if shutil.which('pdftoimage') is None:
        errors.append(
            "Poppler not found.\n"
            "  Install: apt-get install poppler-utils (Debian/Ubuntu)\n"
            "           brew install poppler (macOS)"
        )

    if errors:
        print("ERROR: Missing system dependencies:\n")
        for error in errors:
            print(f"  - {error}\n")
        sys.exit(1)

# cli.py
def main(argv=None):
    from .config.system import check_system_dependencies
    check_system_dependencies()  # Early validation
    # ... rest of CLI
```

**Effort:** 1 hour

---

#### P1.2: Minimal Test Suite (Only test_models.py)

**Problem:** No tests for CLI commands, extraction pipeline, scrapers, QC logic, or exports.

**Solution:**
1. Create test structure:
   ```
   tests/
   ├── conftest.py           # pytest fixtures
   ├── test_models.py        # ✓ Exists
   ├── test_cli.py           # CLI command tests
   ├── test_extraction.py    # Pipeline tests
   ├── test_scrapers.py      # Scraper tests (mocked)
   ├── test_qc.py            # QC layer tests
   ├── test_outputs.py       # Export tests
   └── fixtures/
       └── sample.pdf        # Test PDF
   ```

2. Add `conftest.py` with fixtures:
   ```python
   @pytest.fixture
   def sample_pdf():
       """Return path to test PDF."""
       return Path(__file__).parent / "fixtures" / "sample.pdf"

   @pytest.fixture
   def mock_anthropic(monkeypatch):
       """Mock Anthropic client."""
       # ...
   ```

3. Minimum test targets:
   - CLI: 5 tests (scrape, extract, qc, export, dashboard)
   - Pipeline: 3 tests (text tier, OCR tier, vision tier)
   - QC: 3 tests (rules layer, benchmarks, LLM layer)
   - Exports: 2 tests (Excel, CSV)

4. Add coverage tracking:
   ```toml
   # pyproject.toml
   [tool.pytest.ini_options]
   testpaths = ["tests"]
   addopts = "--cov=oefo --cov-report=html"
   ```

**Effort:** 4-6 hours for minimum suite; more for comprehensive

---

#### P1.3: No CI/CD Pipeline

**Problem:** No automated testing, linting, or build verification on commits.

**Solution:**
1. Create `.github/workflows/ci.yml`:
   ```yaml
   name: CI
   on: [push, pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
           with:
             python-version: '3.10'
         - run: pip install -e .[dev]
         - run: pytest --cov
         - run: black --check oefo tests
         - run: flake8 oefo tests
   ```

2. Add linting configuration:
   - `pyproject.toml`: black, flake8, mypy config
   - `.flake8` or `setup.cfg`: flake8 rules

**Effort:** 1-2 hours

---

#### P1.4: Missing Documentation

**Create files:**

1. **INSTALL.md** — Step-by-step installation (after src/ restructure)
   - System prerequisites (Python 3.10+, Tesseract, Poppler)
   - Installation via pip/git
   - Environment variable setup
   - Verification steps

2. **ARCHITECTURE.md** — High-level system design
   - Data flow diagram
   - Module responsibilities
   - Extraction tier decision tree
   - QC layer architecture

3. **DEVELOPMENT.md** — Contributing guidelines
   - Dev environment setup
   - Running tests
   - Code style (black, flake8)
   - PR process

4. **DEPLOYMENT.md** — Production deployment
   - Docker setup
   - systemd service
   - Reverse proxy (nginx) for dashboard
   - Scaling considerations

5. **TROUBLESHOOTING.md** — Common errors
   - "Tesseract not found"
   - "Poppler not found"
   - API key errors
   - Memory issues with large PDFs

**Effort:** 3-4 hours

---

#### P1.5: setup.py Should Be Removed (Use pyproject.toml Only)

**Problem:** Both `setup.py` and `pyproject.toml` exist; confusing and maintenance burden.

**Solution:**
1. Delete `setup.py`
2. Ensure all metadata in `pyproject.toml`
3. Update to modern PEP 518 backend:

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "oefo"
version = "0.1.0"  # Or use dynamic
description = "..."
# ... rest of metadata

[tool.setuptools]
packages = ["oefo"]

[tool.setuptools.package-data]
oefo = ["dashboard/*.html", "config/*.json"]
```

**Effort:** 30 minutes

---

### P2 Enhancement — Nice-to-Have

#### P2.1: OpenClaw Wrapper Scripts

**Implement OpenClaw-specific command shortcuts:**
```bash
openclaw scrape-all     # Run all scrapers
openclaw full-pipeline  # Scrape → extract → qc → export
openclaw export-latest  # Export final data to Excel
```

**File:** `scripts/openclaw.py` or shell wrappers

**Effort:** 2 hours

---

#### P2.2: Makefile or justfile

**For common development tasks:**
```makefile
.PHONY: install test lint format clean

install:
	pip install -e .[dev]

test:
	pytest --cov

lint:
	black --check oefo tests
	flake8 oefo tests
	mypy oefo

format:
	black oefo tests

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	rm -rf .pytest_cache build dist *.egg-info
```

**Effort:** 1 hour

---

#### P2.3: Lint Configuration

**Add to pyproject.toml:**
```toml
[tool.black]
line-length = 100
target-version = ["py310"]

[tool.isort]
profile = "black"

[tool.flake8]
max-line-length = 100
exclude = [".git", "__pycache__", "build", "dist"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
```

**Effort:** 30 minutes

---

#### P2.4: CONTRIBUTING.md

**Document contribution process:**
- Development setup
- Code style guidelines
- Test requirements
- PR review process
- Commit message format

**Effort:** 1 hour

---

## 11. Summary Table

| Category | Status | Count | Notes |
|----------|--------|-------|-------|
| **P0 Blockers** | ⚠️ Critical | 4 | Packaging, security, entry points |
| **P1 Production** | ⚠️ High | 5 | Tests, CI, docs, deps |
| **P2 Enhancement** | 📋 Medium | 4 | Scripts, Makefile, lint config |
| **Total Issues** | — | **13** | — |

### Recommended Fix Order

1. **P0.1** → P0.2 (package structure)
2. **P0.3** → P0.4 (security)
3. **P1.1** (system deps)
4. **P1.2** (tests)
5. **P1.3** (CI/CD)
6. **P1.4** (documentation)
7. **P1.5** (cleanup)
8. **P2.x** (nice-to-haves)

---

## 12. Conclusion

**OEFO is functionally complete but not production-ready for distribution.** The codebase has solid architecture and comprehensive feature set, but:

- **Packaging is broken** — won't install via pip; entry points fail
- **Security defaults are insecure** — dashboard bound to 0.0.0.0 with wildcard CORS
- **Test coverage is minimal** — only model tests exist
- **No CI/CD pipeline** — no automated quality checks
- **Documentation is incomplete** — missing installation, architecture, and deployment guides
- **System dependencies aren't checked** — unclear error messages if Tesseract/Poppler missing

**Estimated effort to P1 completeness:** 15-20 hours (depending on src/ restructure complexity)

**Estimated effort to full production readiness:** 25-30 hours

**Priority recommendation:** Fix P0 issues first (4-6 hours); then address P1 for release readiness.

