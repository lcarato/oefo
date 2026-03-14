# OEFO Architecture Overview

This document describes the internal architecture of the Open Energy Finance Observatory system, including package layout, module responsibilities, data flow, and operational entry points.

## Package Layout

The OEFO project is organized under the `src/oefo/` namespace package:

```
src/oefo/
├── __init__.py              # Package initialization and version
├── cli.py                   # Command-line interface and subcommands
├── llm_client.py            # Model-agnostic LLM provider abstraction
├── models.py                # Pydantic v2 data models (Observation, ProvenanceChain)
│
├── scrapers/                # Source-specific web scrapers
│   ├── __init__.py
│   ├── base.py              # Abstract BaseScraper class
│   ├── ifc.py               # IFC portal scraper
│   ├── ebrd.py              # EBRD portal scraper
│   ├── gcf.py               # Green Climate Fund scraper
│   ├── sec.py               # SEC EDGAR scraper
│   └── regulatory/          # Regulatory agency scrapers
│       ├── aneel.py         # ANEEL (Brazil) scraper
│       ├── aer.py           # AER (Alberta) scraper
│       ├── ofgem.py         # Ofgem (UK) scraper
│       └── ferc.py          # FERC (USA) scraper
│
├── extraction/              # PDF text/table extraction pipeline
│   ├── __init__.py
│   ├── extractor.py         # Main extraction orchestrator
│   ├── text_layer.py        # Tier 1: PDF text extraction (pdfplumber)
│   ├── ocr_layer.py         # Tier 2: Tesseract OCR fallback
│   ├── vision_layer.py      # Tier 3: LLM vision-based extraction
│   └── prompt_templates.py  # LLM extraction prompts
│
├── qc/                      # Quality control (3-layer validation)
│   ├── __init__.py
│   ├── validator.py         # Main QC orchestrator
│   ├── rules_engine.py      # Layer 1: Rule-based validation
│   ├── statistical.py       # Layer 2: Statistical benchmarking
│   └── llm_cross_val.py     # Layer 3: LLM cross-validation
│
├── outputs/                 # Multi-format exporters
│   ├── __init__.py
│   ├── excel_exporter.py    # Excel workbook output
│   ├── csv_exporter.py      # CSV tabular export
│   ├── parquet_exporter.py  # Parquet columnar format
│   └── json_exporter.py     # JSON export
│
├── dashboard/               # Real-time SSE monitoring dashboard
│   ├── __init__.py
│   ├── server.py            # Async SSE web server
│   ├── handlers.py          # WebSocket/SSE event handlers
│   └── static/              # Frontend assets (HTML, CSS, JS)
│       └── index.html       # Real-time monitoring UI
│
├── data/                    # Persistence layer
│   ├── __init__.py
│   ├── store.py             # ObservationStore (in-memory + SQLite)
│   ├── models_db.py         # Database schema definitions
│   └── migrations/          # Schema migration scripts
│
└── config/                  # Configuration and settings
    ├── __init__.py
    ├── settings.py          # Environment-based configuration
    └── logging.py           # Logging setup
```

## Module Descriptions

### Core Modules

**`models.py`** — Pydantic v2 data models defining the structure of all domain objects:
- `Observation` — A single extracted data point (cost of equity, debt, WACC, etc.) with all supporting metadata
- `ProvenanceChain` — Immutable audit trail linking an observation to its source document, extraction method, and QC result
- Supporting enums: `SourceType`, `ExtractionMethod`, `QCStatus`

**`llm_client.py`** — Provider-agnostic LLM client layer:
- Abstracts Anthropic, OpenAI, and Ollama backends
- Handles API authentication, retry logic, rate limiting
- Enables seamless fallback between providers based on configuration
- Supports both text and vision modalities

**`cli.py`** — Command-line interface exposing all user-facing operations:
- Subcommands: `scrape`, `extract`, `extract-batch`, `qc`, `export`, `dashboard`, `status`, `config`
- Argument parsing and validation
- Orchestrates pipeline stages

### Scraper Modules

**`scrapers/base.py`** — Abstract base class defining the scraper interface:
- `BaseScraper.fetch()` — Download documents from a source
- `BaseScraper.parse()` — Extract metadata (title, date, issuer) from documents
- Error handling and retry logic

**`scrapers/{ifc,ebrd,gcf,sec}.py`** — Development finance institution scrapers:
- DFI-specific authentication, URL patterns, document discovery
- Metadata extraction (publication date, issuer, document type)

**`scrapers/regulatory/{aneel,aer,ofgem,ferc}.py`** — Regulatory agency scrapers:
- Jurisdiction-specific regulatory filings and rate schedules
- Parsing of standardized regulatory disclosure formats

### Extraction Pipeline

The extraction pipeline operates in three tiers, each invoked only if earlier tiers fail:

**`extraction/text_layer.py`** (Tier 1) — Fast, deterministic extraction:
- Uses `pdfplumber` to extract structured text from PDFs
- Identifies tables and key value pairs via regex patterns
- Returns immediately if confidence is high
- Fastest tier, zero LLM cost

**`extraction/ocr_layer.py`** (Tier 2) — Fallback for scanned/image-heavy PDFs:
- Uses Tesseract OCR to convert image content to text
- Re-applies text extraction rules to OCR output
- Slower but handles scanned documents that pdfplumber cannot parse
- Zero LLM cost

**`extraction/vision_layer.py`** (Tier 3) — Last resort, high-accuracy:
- Passes PDF page images directly to Claude's vision model
- Uses sophisticated prompts (in `prompt_templates.py`) to extract financial terms
- Cross-references against previously extracted values for consistency
- Highest accuracy, highest cost (LLM API calls)

Each tier returns a confidence score; pipeline advances if confidence is below threshold.

### Quality Control (QC) System

Three-layer validation ensures data integrity:

**`qc/rules_engine.py`** (Layer 1) — Heuristic rule-based validation:
- Data type checks (numeric bounds, format validation)
- Business logic checks (Ke > Kd, WACC in expected range)
- Source legitimacy checks (IFC/EBRD/etc. only)
- Fastest, zero compute cost
- Returns pass/fail and detailed violation list

**`qc/statistical.py`** (Layer 2) — Statistical benchmarking:
- Compares observation against historical distributions by sector/region/year
- Flags outliers (>3σ from mean)
- Provides context (percentile, similar observations)
- No LLM cost

**`qc/llm_cross_val.py`** (Layer 3) — LLM-powered cross-validation:
- Asks Claude: "Given these other observations in the sector, is this value reasonable?"
- Provides detailed reasoning for flagged observations
- Used for final human review of borderline cases
- Requires LLM API call

### Output Modules

**`outputs/{excel,csv,parquet,json}_exporter.py`** — Format-specific exporters:
- Serialize `Observation` objects to target format
- Include provenance chain (source, extraction method, QC status)
- Support filtering by source, status, date range
- Maintain consistent schema across formats

### Dashboard

**`dashboard/server.py`** — Real-time event streaming:
- Async Python web server using ASGI (Uvicorn/Hypercorn)
- Server-Sent Events (SSE) stream for live pipeline updates
- Broadcasts extraction progress, QC results, error conditions
- Minimal latency (<100ms per update)

**`dashboard/static/index.html`** — Frontend monitoring UI:
- Real-time progress bars (scraping, extraction, QC)
- Live log streaming
- Status indicators and error alerts
- No build step required (pure HTML/CSS/JS)

### Data Layer

**`data/store.py`** — ObservationStore abstraction:
- In-memory storage for current session
- SQLite persistent storage for long-term queries
- Atomic write operations with rollback support
- Schema versioning and migrations

**`data/models_db.py`** — SQLAlchemy table definitions:
- `observations` table with provenance columns
- Indexes on source, status, date for fast queries
- Foreign key relationships for referential integrity

### Configuration

**`config/settings.py`** — Environment-based configuration:
- Loads from `.env` file or environment variables
- Validates API keys and directory permissions
- Provides sensible defaults
- Runtime validation methods (`validate_api_keys()`, `validate_directories()`)

**`config/logging.py`** — Structured logging setup:
- JSON-formatted logs for downstream analysis
- Level configuration via `OEFO_LOG_LEVEL`
- File rotation and archival

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERACTION                        │
│ (CLI: oefo scrape ifc | oefo extract ./pdf.pdf)            │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────▼────────────┐
           │    SCRAPER LAYER       │
           │ (Fetch docs from web)  │
           └───────────┬────────────┘
                       │ (PDFs + metadata)
           ┌───────────▼────────────────────┐
           │  EXTRACTION PIPELINE (3-tier)  │
           │  ├─ Tier 1: pdfplumber text   │
           │  ├─ Tier 2: Tesseract OCR    │
           │  └─ Tier 3: LLM vision       │
           └───────────┬────────────────────┘
                       │ (Observations with ProvenanceChain)
           ┌───────────▼──────────────────┐
           │   QC VALIDATION (3-layer)    │
           │   ├─ Layer 1: Rules engine   │
           │   ├─ Layer 2: Statistical    │
           │   └─ Layer 3: LLM cross-val  │
           └───────────┬──────────────────┘
                       │ (Observations with QC status)
           ┌───────────▼──────────────┐
           │   OBSERVATION STORE      │
           │ (In-memory + SQLite)     │
           └───────────┬──────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────▼───┐  ┌──────▼──┐  ┌──────▼──┐
   │ Excel  │  │  CSV    │  │ Parquet │
   │Export  │  │ Export  │  │ Export  │
   └────────┘  └─────────┘  └─────────┘
```

## Entry Points

OEFO is designed to be used in three ways:

### 1. Command-Line Interface (Primary)

```bash
oefo scrape ifc
oefo extract ./data/raw/report.pdf --source-type dfi
oefo qc --full
oefo export --format excel --output results.xlsx
oefo dashboard
```

Entry point: `src/oefo/cli.py:main()`

### 2. Python Module (Programmatic)

```python
from oefo.extraction import Extractor
from oefo.config import Settings

config = Settings()
extractor = Extractor(config)
observations = extractor.run("./report.pdf", source_type="dfi")
```

### 3. Real-Time Dashboard

```bash
oefo dashboard --port 8765
# Then open http://localhost:8765 in a browser
```

Entry point: `src/oefo/dashboard/server.py:main()`

## Configuration System

Configuration is hierarchical with environment variables taking precedence:

1. **Defaults** — Built into `settings.py`
2. **`.env` file** — Loaded at startup (highest precedence)
3. **Environment variables** — Checked at runtime

Example `.env`:
```env
ANTHROPIC_API_KEY=sk-ant-xxxxxx
OEFO_DATA_DIR=./data
OEFO_LOG_LEVEL=DEBUG
OEFO_TRACEABILITY=FULL
```

At runtime, access configuration via:
```python
from oefo.config import Settings
config = Settings()
api_key = config.anthropic_api_key
```

## Extraction Pipeline Overview

The **3-tier extraction pipeline** processes PDFs sequentially:

1. **Tier 1: Text Extraction** (pdfplumber)
   - Input: PDF file
   - Output: Extracted text, tables, metadata
   - Confidence: High for well-formatted PDFs
   - Cost: $0
   - Time: ~500ms per document

2. **Tier 2: OCR Fallback** (Tesseract)
   - Input: PDF (if Tier 1 confidence < 70%)
   - Output: Scanned text converted to structured data
   - Confidence: Medium for scanned documents
   - Cost: $0
   - Time: ~2-5s per document

3. **Tier 3: LLM Vision** (Claude)
   - Input: PDF pages as images (if Tier 2 confidence < 50%)
   - Output: Semantically understood financial terms
   - Confidence: Very high
   - Cost: ~$0.01-0.05 per document (depending on length)
   - Time: ~3-10s per document

**Decision Logic:**
- After each tier, confidence score is computed
- If confidence ≥ threshold, result is returned; next tier skipped
- If confidence < threshold, next tier is invoked
- All three tiers fail → Observation marked as `MANUAL_REVIEW` required

## QC System Overview

The **3-layer QC system** validates observations before export:

1. **Layer 1: Rules Engine** (Heuristic)
   - Numeric bounds: Ke in [0.05, 0.50], Kd in [0.01, 0.30], WACC in [0.05, 0.40]
   - Business logic: Ke > Kd, E/V + D/V ≈ 1.0
   - Source legitimacy: Only recognized DFI/regulatory sources
   - Cost: $0, Time: ~100ms

2. **Layer 2: Statistical Benchmarking**
   - Compares against historical observations (same sector, region, year)
   - Flags outliers (|z-score| > 3)
   - Provides percentile context
   - Cost: $0, Time: ~200ms

3. **Layer 3: LLM Cross-Validation**
   - Queries Claude: "Is this observation reasonable given peer data?"
   - Provides detailed reasoning for flagged values
   - Enables nuanced judgment (e.g., startup premium, crisis discount)
   - Cost: ~$0.001 per validation, Time: ~2-5s

**Output:** Each observation carries a `QCStatus` (PASS, FLAG_MANUAL_REVIEW, FAIL) and detailed reasoning.

## Performance Characteristics

| Operation | Time | Cost | Parallelizable |
|-----------|------|------|-----------------|
| Scrape 1 document | 1-3s | $0 | Yes |
| Extract Tier 1 (text) | ~500ms | $0 | Yes |
| Extract Tier 2 (OCR) | 2-5s | $0 | Yes |
| Extract Tier 3 (vision) | 5-10s | $0.01-0.05 | Yes |
| QC Layer 1 (rules) | ~100ms | $0 | Yes |
| QC Layer 2 (statistical) | ~200ms | $0 | Yes |
| QC Layer 3 (LLM) | 2-5s | $0.001 | Yes |
| Export to Excel (1000 obs) | ~500ms | $0 | No |

## Extensibility

OEFO is designed for extensibility:

- **New scrapers:** Inherit `BaseScraper`, implement `fetch()` and `parse()`
- **New extractors:** Add tier-specific logic to extraction pipeline
- **New QC rules:** Add rules to `rules_engine.py` without modifying orchestrator
- **New output formats:** Implement new exporter class, register in `cli.py`
- **New LLM providers:** Extend `llm_client.py` abstraction with provider implementation

