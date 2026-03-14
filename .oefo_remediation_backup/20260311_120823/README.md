# OEFO — Open Energy Finance Observatory

A comprehensive toolkit for collecting, analyzing, and publishing energy finance data from multiple international sources.

OEFO automates the extraction of observed financing terms — cost of debt (Kd), cost of equity (Ke), capital structure, and WACC — from publicly available documents published by development finance institutions and regulatory bodies worldwide.

## Key Features

- **Multi-source scraping** — IFC, EBRD, GCF, SEC EDGAR, plus regulatory agencies (ANEEL, AER, Ofgem, FERC)
- **3-tier extraction pipeline** — pdfplumber text → Tesseract OCR → LLM Vision (with cross-referencing)
- **3-layer QC agent** — rule-based validation → statistical benchmarks → LLM cross-validation
- **Full traceability** — every observation carries a provenance chain from source document to final value
- **Multiple output formats** — Excel workbooks, CSV, Parquet, JSON
- **Live dashboard** — real-time pipeline monitoring via Server-Sent Events

## System Dependencies

Before installing OEFO, ensure you have the required system dependencies:

**macOS (via Homebrew):**
```bash
brew install poppler tesseract
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install -y poppler-utils tesseract-ocr
```

For complete installation instructions including Windows support, Python virtual environment setup, and environment configuration, see [Installation Guide](docs/INSTALL.md).

## Quick Start

```bash
# Clone and install
git clone https://github.com/lcarato/oefo.git
cd oefo
pip install -e .

# Set your API key (at least one LLM provider)
export ANTHROPIC_API_KEY=your-key-here

# Run the full pipeline for a source
oefo scrape ifc
oefo extract ./data/raw/ifc/report.pdf --source-type dfi
oefo extract-batch ./data/raw/ifc --source-type dfi
oefo qc --full
oefo export --format excel --output results.xlsx
```

## Architecture

OEFO is organized under `src/oefo/` with the following structure:

```
src/oefo/
├── scrapers/          # Source-specific web scrapers (DFI + regulatory)
├── extraction/        # 3-tier PDF extraction pipeline (text → OCR → vision)
├── qc/                # 3-layer quality control system
├── outputs/           # Excel, CSV, Parquet, JSON exporters
├── dashboard/         # Real-time SSE monitoring dashboard
├── data/              # Persistence layer (in-memory + SQLite)
├── config/            # Configuration and settings
├── models.py          # Pydantic v2 data models (Observation, ProvenanceChain)
├── llm_client.py      # Model-agnostic LLM client (Anthropic → OpenAI → Ollama)
└── cli.py             # Command-line interface
```

For detailed architecture information including module descriptions, data flow diagrams, and extensibility patterns, see [Architecture Overview](docs/ARCHITECTURE.md).

## CLI Reference

| Command | Description |
|---------|-------------|
| `oefo scrape <source>` | Scrape documents from a source (ifc, ebrd, ofgem, etc.) |
| `oefo extract <pdf> --source-type <type>` | Extract financing terms from a single PDF |
| `oefo extract-batch <dir> --source-type <type>` | Batch extraction from a directory of PDFs |
| `oefo qc [--rules-only\|--full]` | Run QC validation on extracted observations |
| `oefo export --format <fmt> --output <path>` | Export observations to Excel/CSV/Parquet/JSON |
| `oefo dashboard [--port 8765]` | Launch the live monitoring dashboard |
| `oefo status [--detailed]` | Show pipeline status and statistics |
| `oefo config [--validate]` | Display or validate current configuration |

## Configuration

OEFO is configured via environment variables or a `.env` file:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes* | Anthropic API key for Claude |
| `OPENAI_API_KEY` | No | OpenAI fallback API key |
| `OEFO_DATA_DIR` | No | Data storage directory (default: `./data`) |
| `OEFO_LOG_LEVEL` | No | Logging level (default: `INFO`) |
| `OEFO_TRACEABILITY` | No | Traceability level: `FULL`, `PARTIAL`, `MINIMAL` |

*At least one LLM provider API key is required for extraction and LLM-based QC.

## Core Formula

**WACC = Ke × (E/V) + Kd × (1−t) × (D/V)**

Where Ke = cost of equity, Kd = cost of debt, E/V = equity weight, D/V = debt weight, t = tax rate.

## Documentation

- [Installation Guide](docs/INSTALL.md) — Step-by-step setup, system dependencies, troubleshooting
- [Architecture Overview](docs/ARCHITECTURE.md) — System design, module descriptions, data flow, performance characteristics
- [OpenClaw Integration](docs/OPENCLAW.md) — Scheduled operations, wrapper commands, security model, approval workflows
- [Agent Operations](OEFO_Agent_Autonomous_Operations.md) — Autonomous pipeline decision logic and error handling protocols

## Requirements

- Python 3.10+
- See `requirements.txt` for full dependency list

## License

MIT

## Author

ET Finance
