# OEFO — Open Energy Finance Observatory

A comprehensive toolkit for collecting, analyzing, and publishing energy finance data from multiple international sources.

OEFO automates the extraction of observed financing terms — cost of debt (Kd), cost of equity (Ke), capital structure, and WACC — from publicly available documents published by development finance institutions and regulatory bodies worldwide.

## Key Features

- **Multi-source scraping** — IFC, EBRD, GCF, SEC EDGAR, plus regulatory agencies (ANEEL, AER, Ofgem, FERC)
- **4-tier extraction pipeline** — pdfplumber text → Tesseract OCR → LLM Vision → human-in-the-loop
- **3-layer QC agent** — rule-based validation → statistical benchmarks → LLM cross-validation
- **Full traceability** — every observation carries a provenance chain from source document to final value
- **Multiple output formats** — Excel workbooks, CSV, Parquet, JSON
- **Live dashboard** — real-time pipeline monitoring via Server-Sent Events

## Quick Start

```bash
# Clone and install
git clone https://github.com/et-finance/oefo.git
cd oefo
pip install -e .

# Set your API key (at least one LLM provider)
export ANTHROPIC_API_KEY=your-key-here

# Run the full pipeline for a source
oefo scrape ifc
oefo extract --source ifc
oefo qc --source ifc
oefo export --format excel
```

## Architecture

```
oefo/
├── scrapers/          # Source-specific web scrapers
│   └── regulatory/    # Regulatory agency scrapers
├── extraction/        # PDF text/table extraction pipeline
├── qc/                # Quality control agent (3 layers)
├── outputs/           # Excel, CSV, Parquet, JSON exporters
├── dashboard/         # Real-time SSE monitoring dashboard
├── data/              # Storage layer (ObservationStore)
├── config/            # Settings and environment config
├── models.py          # Pydantic v2 data models (Observation, ProvenanceChain)
├── llm_client.py      # Model-agnostic LLM client (Anthropic → OpenAI → Ollama)
└── cli.py             # Command-line interface
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `oefo scrape <source>` | Scrape documents from a source |
| `oefo extract --source <source>` | Extract financing terms from scraped documents |
| `oefo extract-batch --sources ifc,ebrd` | Batch extraction across multiple sources |
| `oefo qc --source <source>` | Run QC validation on extracted observations |
| `oefo export --format excel` | Export observations to Excel/CSV/Parquet/JSON |
| `oefo dashboard` | Launch the live monitoring dashboard |
| `oefo status` | Show pipeline status and statistics |
| `oefo config` | Display current configuration |

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

- [Deployment Guide](OEFO_Deployment_Guide.docx)
- [Installation Procedure](OEFO_Installation_Procedure.docx)
- [User Guide](OEFO_User_Guide.docx)
- [Agent Operations](OEFO_Agent_Autonomous_Operations.md)

## Requirements

- Python 3.10+
- See `requirements.txt` for full dependency list

## License

MIT

## Author

ET Finance
