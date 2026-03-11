# OEFO Multi-Modal PDF Extraction Pipeline

A production-ready three-tier extraction system for financial data from energy project PDFs.

## Architecture Overview

The extraction pipeline uses a decision tree to intelligently route documents through three tiers of increasing sophistication:

### Tier 1: Native Text Extraction (TIER_1_TEXT)
- **Methods**: `text.py` - TextExtractor class
- **Libraries**: pdfplumber (primary), PyMuPDF (fallback)
- **Speed**: Fastest (~100ms per page)
- **Cost**: Lowest (no API calls)
- **Best for**: PDFs with embedded, high-quality text

**Key Methods**:
- `extract_text(pdf_path)` → dict with page text and metadata
- `extract_tables(pdf_path)` → list of pandas DataFrames
- `detect_financial_pages(pdf_path)` → list of page numbers with financial keywords
- `is_text_quality_sufficient(text, min_chars=50)` → bool

**Financial Keywords**: WACC, cost of debt, cost of equity, leverage, interest rate, coupon, maturity, etc.

### Tier 2: OCR Extraction (TIER_2_OCR)
- **Methods**: `ocr.py` - OCRExtractor class
- **Libraries**: pdf2image, pytesseract (requires Tesseract-OCR system library)
- **Speed**: Medium (~1-2 seconds per page)
- **Cost**: Medium (no API calls, but computation-intensive)
- **Best for**: Scanned PDFs or low-quality embedded text

**Key Methods**:
- `extract_text(pdf_path, languages=['eng'], dpi=300)` → dict with OCR text
- `preprocess_image(image)` → numpy array (grayscale, adaptive threshold, deskew)
- `extract_table_regions(image)` → list of bounding boxes
- `ocr_table(image, bbox)` → pandas DataFrame

**Supported Languages**: eng, por, spa, deu, fra, ita

### Tier 3: Claude Vision API (TIER_3_VISION)
- **Methods**: `vision.py` - VisionExtractor class
- **Libraries**: Anthropic SDK, pdf2image, PIL
- **Speed**: Slow (~3-5 seconds per page, includes API latency)
- **Cost**: Highest (Claude API tokens)
- **Best for**: Complex tables, multilingual content, authoritative extraction

**Key Methods**:
- `extract_financial_data(pdf_path, pages=None, source_type='regulatory')` → list of dicts
- `render_pages(pdf_path, pages, dpi=250)` → list of PIL images in base64
- `call_vision_api(images, prompt)` → str (JSON response)
- `parse_response(response)` → list of ExtractionResult

**Source Types**: regulatory, dfi, corporate, bond (each with specialized prompts)

## Extraction Pipeline Decision Tree

### ExtractionPipeline Orchestrator (`pipeline.py`)

```python
from extraction import ExtractionPipeline

pipeline = ExtractionPipeline()
results = pipeline.extract(
    pdf_path="path/to/document.pdf",
    source_type="regulatory",  # or "dfi", "corporate", "bond"
    source_institution="ICBC"  # optional
)
```

**Decision Logic**:

1. **Tier Selection** (`decide_tier`):
   - Attempt Tier 1 text extraction
   - If ≥70% of pages have sufficient text quality → Use Tier 1
   - Otherwise → Use Tier 2 (OCR)

2. **Primary Extraction** (`run_tier1` or `run_tier2`):
   - Extract text from financial pages only (keyword filtering)
   - Return ExtractionResult objects with confidence scores

3. **Table Detection** (automatic upgrade to Vision):
   - If document has tables → apply Tier 3 Vision (authoritative)
   - Vision specifically designed for financial table recognition

4. **Cross-Reference** (`cross_reference`):
   - Reconcile Tier 1/2 text results with Tier 3 Vision
   - Flag discrepancies for review
   - Prioritize Vision for structured financial data

## Prompt Templates (`prompts/` directory)

Each source type has a specialized extraction prompt with:
- Exact JSON output schema
- 2-3 few-shot examples
- Multilingual support (en, pt, es, de, fr)
- Confidence scoring guidance
- Uncertainty handling ("if ambiguous, return null")

### Regulatory Documents (`regulatory.py`)
**Focus**: WACC decomposition, CAPM parameters, regulatory frameworks
- Cost of debt, cost of equity, leverage
- Risk-free rate, market risk premium, beta
- Discount rates and hurdle rates

**Example Output Schema**:
```json
{
  "wacc": 7.5,
  "cost_of_debt": 4.5,
  "cost_of_equity": 10.0,
  "leverage_debt_percent": 60,
  "capm_components": {
    "risk_free_rate": 2.5,
    "market_risk_premium": 5.0,
    "beta": 0.9
  },
  "confidence_score": 0.95,
  "notes": "Explicit regulatory WACC statement"
}
```

### DFI Project Disclosures (`dfi.py`)
**Focus**: Loan terms, capital structure, project financing conditions
- Loan amount, tenor, interest rate
- Benchmark rate and spread (SOFR, EURIBOR, etc.)
- Leverage ratios and financing composition

**Example Output Schema**:
```json
{
  "loan_terms": {
    "loan_amount_usd": 45,
    "loan_tenor_years": 15,
    "interest_rate": 5.2,
    "benchmark_rate": "SOFR",
    "spread_bps": 350
  },
  "capital_structure": {
    "debt_amount_usd": 80,
    "equity_amount_usd": 45,
    "leverage_ratio": 64
  },
  "confidence_score": 0.92
}
```

### Corporate Filings (`corporate.py`)
**Focus**: Consolidated financial statements, debt schedules, capital structure
- Total debt and interest expense (calculate Kd)
- Market capitalization and equity
- Disclosed WACC and cost of capital metrics

**Example Output Schema**:
```json
{
  "debt_information": {
    "total_debt_usd": 2550,
    "interest_expense_annual_usd": 180,
    "implicit_cost_of_debt": 7.06,
    "credit_rating": "Baa1"
  },
  "capital_structure": {
    "leverage_ratio_book": 40,
    "leverage_ratio_market": 23.1
  },
  "confidence_score": 0.88
}
```

### Bond Prospectuses (`bond.py`)
**Focus**: Debt terms, coupon rate, maturity, yield, credit ratings
- Coupon rate (explicit cost of debt)
- Yield to maturity (market cost assessment)
- Spread over benchmark (SOFR + X bps)
- Credit rating by agency

**Example Output Schema**:
```json
{
  "bond_terms": {
    "coupon_rate": 4.75,
    "maturity_date": "2035-03-15",
    "tenor_years": 10,
    "issue_size_usd": 500,
    "currency": "USD"
  },
  "pricing_terms": {
    "yield_to_maturity": 4.85,
    "spread_bps": 165,
    "benchmark_rate": "US Treasury"
  },
  "bond_rating": "BBB+",
  "confidence_score": 0.98
}
```

## Installation & Dependencies

### Core Dependencies
```bash
pip install pdfplumber PyMuPDF pdf2image Pillow pytesseract anthropic
```

### System Dependencies
**Tesseract-OCR** (required for Tier 2):
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download installer: https://github.com/UB-Mannheim/tesseract/wiki
```

**poppler-utils** (required for pdf2image):
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# macOS
brew install poppler

# Windows
# Download: https://github.com/oschwartz10612/poppler-windows/releases/
```

### Environment Variables
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

## Usage Examples

### Basic Extraction
```python
from extraction import ExtractionPipeline

pipeline = ExtractionPipeline()

# Extract from regulatory document
results = pipeline.extract(
    pdf_path="path/to/wacc_filing.pdf",
    source_type="regulatory",
    source_institution="ICBC"
)

for result in results:
    print(f"Page {result.page_num}:")
    print(f"  Tier: {result.tier}")
    print(f"  Confidence: {result.confidence:.0%}")
    print(f"  Data: {result.extracted_data}")
```

### Direct Tier Usage
```python
from extraction import TextExtractor, OCRExtractor, VisionExtractor

# Tier 1: Text extraction
text_extractor = TextExtractor()
text_data = text_extractor.extract_text("document.pdf")
financial_pages = text_extractor.detect_financial_pages("document.pdf")

# Tier 2: OCR extraction
ocr_extractor = OCRExtractor()
ocr_data = ocr_extractor.extract_text("scanned.pdf", languages=["eng", "por"])

# Tier 3: Vision extraction
vision_extractor = VisionExtractor()
vision_results = vision_extractor.extract_financial_data(
    "document.pdf",
    pages=[0, 1, 2],
    source_type="bond"
)
```

### Table Extraction
```python
from extraction import TextExtractor

text_extractor = TextExtractor()

# Extract all tables as DataFrames
tables = text_extractor.extract_tables("document.pdf")

for i, table in enumerate(tables):
    print(f"Table {i}:")
    print(table)
    print(f"  Page: {table['_source_page'].iloc[0]}")
    print()
```

### Multilingual OCR
```python
from extraction import OCRExtractor

ocr_extractor = OCRExtractor()

# Extract Portuguese and English text
results = ocr_extractor.extract_text(
    "multilingual.pdf",
    languages=["por", "eng"],
    dpi=300
)
```

### Custom Prompts
```python
from extraction.prompts import get_prompt

# Get specialized prompt for document type
regulatory_prompt = get_prompt("regulatory", language="en")
dfi_prompt = get_prompt("dfi", language="pt")
corporate_prompt = get_prompt("corporate", language="es")
bond_prompt = get_prompt("bond", language="de")
```

## ExtractionResult Object

Each result contains:
- `page_num`: Page number (0-indexed)
- `tier`: Extraction tier used (TIER_1_TEXT, TIER_2_OCR, TIER_3_VISION)
- `extracted_data`: Dictionary of extracted financial parameters
- `source_quote`: Direct quote from source document
- `confidence`: Confidence score (0.0-1.0)
- `notes`: Caveats, ambiguities, or special conditions

**Methods**:
- `to_dict()`: Convert to dictionary for serialization
- `__repr__()`: Human-readable string representation

## Confidence Scoring

Each extraction receives a confidence score (0.0-1.0):
- **1.0**: Explicit statement in document (e.g., "WACC is 7.5%")
- **0.8-0.9**: Clear inference with minimal ambiguity
- **0.5-0.7**: Calculated or partially ambiguous value
- **0.3-0.5**: Significant uncertainty or conditional on unstated assumptions
- **0.0-0.3**: Not found or highly ambiguous

## Quality Control Integration

Results are designed for seamless integration with QC module:
- `confidence`: Maps to QC scoring
- `source_quote`: Enables verification
- `page_num`: Allows spot-checking
- `tier`: Indicates extraction method (for QC strategy selection)
- `notes`: Flags special cases

See `/sessions/fervent-tender-allen/mnt/ET Finance/oefo/qc/` for QC pipeline.

## Cost Optimization

### Tier 1 (Preferred)
- Zero API cost
- Handles 80%+ of well-formed PDFs
- Automatic fallback if text quality insufficient

### Tier 2 (Selective)
- Only for scanned/low-quality documents
- No API cost but higher compute
- Preprocessing minimizes noise

### Tier 3 (Strategic)
- Applied only to pages with tables
- Cost: ~100-200 tokens per page for financial docs
- Example: 10-page doc with 3 financial tables ≈ $0.10-0.20

**Cost Management**:
- Financial page detection filters out non-relevant pages
- Tier 3 limited to MAX_PAGES_PER_EXTRACTION (default: 10)
- Results cached to avoid re-extraction

## Error Handling & Logging

All modules use Python `logging`:
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pipeline = ExtractionPipeline(logger_instance=logger)
```

**Log Levels**:
- DEBUG: Detailed extraction steps, page-level processing
- INFO: Tier selection, major milestones
- WARNING: Fallback operations, quality concerns
- ERROR: Failed extractions, missing dependencies

## Performance Characteristics

| Metric | Tier 1 | Tier 2 | Tier 3 |
|--------|--------|--------|--------|
| Speed (per page) | 50-100ms | 1-3s | 3-5s |
| Cost | None | CPU | ~$0.01-0.02/page |
| Text quality requirement | High | Low | N/A |
| Table quality | Medium | Low | High |
| Multilingual support | No | Yes | Yes |
| Typical use case | Native PDFs | Scans | Complex tables |

## Project Structure
```
extraction/
├── __init__.py                 # Package exports
├── text.py                     # Tier 1: TextExtractor (400 lines)
├── ocr.py                      # Tier 2: OCRExtractor (405 lines)
├── vision.py                   # Tier 3: VisionExtractor (450 lines)
├── pipeline.py                 # Orchestrator: ExtractionPipeline (465 lines)
├── prompts/
│   ├── __init__.py             # Prompt loader
│   ├── regulatory.py           # Regulatory WACC prompts (180 lines)
│   ├── dfi.py                  # DFI disclosure prompts (200 lines)
│   ├── corporate.py            # Corporate filing prompts (220 lines)
│   └── bond.py                 # Bond prospectus prompts (240 lines)
├── README.md                   # This file
└── ARCHITECTURE.md             # Detailed technical documentation
```

## Related Modules

- **`config/`**: Thresholds and controlled vocabularies
- **`models.py`**: Observation and ExtractionResult Pydantic models
- **`qc/`**: Quality control validation pipeline
- **`outputs/`**: Storage for extraction results

## Contributing

When adding new extractors or prompts:
1. Follow the established class structure (init, main method, helpers)
2. Add comprehensive docstrings (Google format)
3. Include type hints for all parameters and returns
4. Add error handling with logging
5. Update this README with new functionality
6. Test with sample documents across all source types

## License

Part of the OEFO (Open Energy Finance Observatory) project.
