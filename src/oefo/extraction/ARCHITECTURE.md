# Multi-Modal PDF Extraction Pipeline - Architecture

## System Overview

The OEFO extraction pipeline processes energy project PDFs through a three-tier decision tree to extract financial parameters (WACC, cost of debt, leverage, etc.).

```
Input PDF
    ↓
[Tier Selector] → Text quality assessment
    ↓
├─→ TIER 1: Native Text ─→ [pdfplumber/PyMuPDF]
│       ↓                   (if quality sufficient)
│       └─→ Financial pages detection
│
├─→ TIER 2: OCR ─→ [pdf2image + Tesseract]
│       ↓           (if Tier 1 fails)
│       └─→ Image preprocessing + OCR
│
└─→ TIER 3: Vision ─→ [Claude Vision API]
        ↓             (for tables + complex content)
        └─→ Structured JSON extraction
            
        ↓
    [Cross-Reference]
        ↓
    ExtractionResult[] → Quality Control Pipeline
```

## Module Details

### 1. text.py (Tier 1: Native Text Extraction)

**Class**: `TextExtractor`

**Key Components**:

#### Methods:
- `extract_text(pdf_path)` → dict
  - Returns page-level text with metadata
  - Primary: pdfplumber, Fallback: PyMuPDF
  - ~50-100ms per page
  - Result: `{"pages": [...], "metadata": {}, "success": bool, "error": str}`

- `extract_tables(pdf_path)` → List[DataFrame]
  - Extracts structured tables from PDF
  - Uses pdfplumber's table detection
  - Returns pandas DataFrames with source metadata
  - ~100ms per page

- `detect_financial_pages(pdf_path)` → List[int]
  - Keyword search for financial terms
  - WACC, cost of debt/equity, leverage, coupon, maturity, etc.
  - Returns 0-indexed page numbers
  - Enables cost-effective Tier 3 Vision application

- `is_text_quality_sufficient(text, min_chars=50)` → bool
  - Heuristic quality check
  - Minimum 50 characters per page
  - Used in tier selection

**Financial Keywords** (20 terms):
```
wacc, weighted average cost of capital, cost of debt, cost of equity,
rate of return, interest rate, leverage, gearing, spread, basis points,
coupon, maturity, tenor, discount rate, capm, capital asset pricing,
risk-free rate, market risk premium, beta, cost of capital
```

**Dependencies**:
- pdfplumber (primary)
- PyMuPDF/fitz (fallback)
- pandas (for table extraction)

---

### 2. ocr.py (Tier 2: OCR Extraction)

**Class**: `OCRExtractor`

**Key Components**:

#### Methods:
- `extract_text(pdf_path, languages=['eng'], dpi=300)` → dict
  - OCR-based text extraction
  - Multilingual support: eng, por, spa, deu, fra, ita
  - ~1-3 seconds per page
  - Includes confidence scores per word

- `preprocess_image(image: np.ndarray)` → np.ndarray
  - Grayscale conversion
  - Adaptive thresholding (Gaussian, C=11, constant=2)
  - Deskewing via contour detection
  - Optimizes OCR accuracy on low-quality docs

- `extract_table_regions(image: np.ndarray)` → List[(x,y,w,h)]
  - Contour-based table detection
  - Morphological operations (CLOSE then OPEN)
  - Filters by size thresholds (≥20% width, ≥10% height)
  - Returns bounding boxes sorted by area

- `ocr_table(image: np.ndarray, bbox, languages=['eng'])` → DataFrame
  - Cell-by-cell OCR extraction
  - Uses Tesseract PSM 6 (table layout)
  - Splits by whitespace for columns
  - Returns structured DataFrame

**Tesseract Configuration**:
```
--oem 1       # Legacy + LSTM engine
--psm 6       # Assume single uniform block of text
```

**Dependencies**:
- pdf2image
- pytesseract (requires system Tesseract-OCR)
- opencv-python (cv2)
- numpy

---

### 3. vision.py (Tier 3: Claude Vision API)

**Class**: `VisionExtractor`

**Key Components**:

#### Methods:
- `extract_financial_data(pdf_path, pages=None, source_type='regulatory', language=None)` → List[dict]
  - End-to-end Vision extraction
  - Renders pages, builds prompt, calls API, parses result
  - ~3-5 seconds per page (includes API latency)
  - Returns structured financial data

- `render_pages(pdf_path, pages, dpi=250)` → List[dict]
  - Converts PDF pages to PIL images
  - Base64 encodes for API transmission
  - Limits to MAX_PAGES_PER_EXTRACTION (10) for cost control
  - Default DPI 250: balance quality vs. token usage

- `build_prompt(source_type, language=None)` → str
  - Source-type specific prompts
  - Supports: regulatory, dfi, corporate, bond
  - Multilingual: en, pt, es, de, fr
  - Includes JSON schema + 2-3 examples

- `call_vision_api(images: List[dict], prompt: str, max_tokens=4096)` → str
  - Calls Claude Opus 4.6 Vision API
  - Sends images as base64 PNG
  - Returns raw JSON response
  - Error handling for API failures

- `parse_response(response: str)` → List[dict]
  - Extracts JSON from response (handles text before/after)
  - Calculates average confidence per page
  - Returns standardized ExtractionResult format

**Prompt Templates**: 4 specialized prompts in `/prompts/`
- `regulatory.py`: WACC/CAPM decomposition
- `dfi.py`: Loan terms, capital structure
- `corporate.py`: Debt, equity, leverage
- `bond.py`: Coupon, maturity, spread, rating

**Output Schema** (per prompt):
```json
{
  "pages": [
    {
      "page_num": 0,
      "extracted_items": [
        {
          "parameter": "wacc",
          "value": 7.5,
          "unit": "percent",
          "source_quote": "The WACC is estimated at 7.5%...",
          "confidence": 0.95,
          "notes": "Explicit statement in regulatory filing"
        }
      ]
    }
  ]
}
```

**Dependencies**:
- anthropic (SDK)
- pdf2image
- Pillow (PIL)

---

### 4. pipeline.py (Orchestrator)

**Class**: `ExtractionPipeline`

**Key Components**:

#### Core Methods:
- `extract(pdf_path, source_type, source_institution=None)` → List[ExtractionResult]
  - Main entry point
  - Orchestrates multi-tier extraction
  - Returns results from best-performing tier
  - Applies cross-reference when both text and Vision results exist

- `decide_tier(pdf_path)` → str
  - Analyzes text extraction quality
  - ≥70% pages with sufficient text → TIER_1
  - Otherwise → TIER_2
  - ~100ms decision time

- `run_tier1(pdf_path, source_type)` → List[ExtractionResult]
  - Text extraction + financial page filtering
  - Confidence: 0.6 (medium, unstructured)
  - Notes if tables present for later Vision processing

- `run_tier2(pdf_path, source_type)` → List[ExtractionResult]
  - OCR extraction with quality scoring
  - Confidence: 0.4-0.8 (depends on OCR confidence)
  - Useful for scanned documents

- `run_tier3(pdf_path, pages, source_type)` → List[ExtractionResult]
  - Claude Vision extraction
  - Applies financial page pre-filter to control cost
  - Confidence: Depends on prompt guidance (typically 0.7-0.95)

- `cross_reference(tier1_2_results, tier3_results)` → List[ExtractionResult]
  - Merges results from text-based and Vision tiers
  - Flags discrepancies for review
  - Prioritizes Vision for structured data (tables)

#### Helper Methods:
- `_results_quality_insufficient(results)` → bool
  - Average confidence < 0.5 → insufficient
  - No results → insufficient
  - Used for fallback logic

**Decision Tree Logic**:
```python
1. decide_tier(pdf)
   ├─→ Text quality ≥ 70%? → TIER_1
   └─→ Otherwise → TIER_2

2. run_tier1 or run_tier2 (primary extraction)

3. Check for tables
   ├─→ Tables found? → apply TIER_3 Vision

4. Results quality sufficient?
   ├─→ YES: return results
   └─→ NO: fallback to TIER_3 Vision for all pages

5. cross_reference (if both text and Vision results exist)
   └─→ Merge and flag discrepancies
```

**ExtractionResult Class**:
- `page_num`: int (0-indexed page)
- `tier`: str ("TIER_1_TEXT" | "TIER_2_OCR" | "TIER_3_VISION")
- `extracted_data`: dict (raw extracted content)
- `source_quote`: str (source text/quote)
- `confidence`: float (0.0-1.0)
- `notes`: str (caveats, special conditions)

Methods:
- `to_dict()` → dict (for serialization)
- `__repr__()` → str (human-readable)

---

### 5. prompts/ (Extraction Prompt Templates)

**Module**: `prompts/__init__.py` - Loader

**Function**: `get_prompt(source_type, language=None)` → str
- Dynamically loads appropriate prompt
- Raises ValueError for unknown source_type

**Prompt Files** (4 templates):

#### regulatory.py
- Target: Regulatory WACC documents, utility commission filings, DFI guidelines
- Parameters: WACC, Kd, Ke, leverage, CAPM components, discount rate
- JSON Schema: `wacc_parameters`, `capm_components`, `debt_parameters`
- Examples: Clear WACC statement, CAPM table, ambiguous debt range

#### dfi.py
- Target: World Bank, ADB, IFC project disclosures
- Parameters: Loan amount, tenor, interest rate, benchmark, leverage
- JSON Schema: `loan_terms`, `capital_structure`, `cost_of_capital`
- Examples: Standard DFI loan, capital structure table, spread calculation

#### corporate.py
- Target: Annual reports, 10-K filings, investor presentations
- Parameters: Total debt, interest expense, equity, leverage, tax rate, credit rating
- JSON Schema: `debt_information`, `equity_information`, `capital_structure`, `cost_of_capital`
- Examples: Balance sheet debt, market value structure, effective tax rate, disclosed WACC

#### bond.py
- Target: Bond prospectuses, offering documents, term sheets
- Parameters: Coupon, maturity, YTM, spread, credit rating, issue size
- JSON Schema: `bond_terms`, `pricing_terms`, `credit_information`, `use_of_proceeds`
- Examples: Standard bond, subordinated notes, floating rate note, green bond

**Prompt Features** (all templates):
1. Base instructions (generic structure for all source types)
2. Language-specific extensions (en, pt, es, de, fr)
3. Example extractions (2-3 realistic scenarios)
4. JSON schema with field descriptions
5. Extraction rules (handling ambiguity, confidence scoring)
6. Priority items (what's most important)

**Multilingual Support**:
- Base prompt in English
- Each language adds conditional block:
  - **Portuguese**: DFI focus (World Bank Latin America office)
  - **Spanish**: Spanish-language markets (Spain, LatAm)
  - **German**: European focus (DFI, rated utilities)
  - **French**: Francophone markets (AFD, African DFIs)

---

## Data Flow

### Extraction Flow
```
PDF File
  ↓
TextExtractor.extract_text()
  ├─→ pdfplumber try
  ├─→ pymupdf fallback
  └─→ Returns: pages[], metadata{}, success bool
        ↓
Decision: Quality sufficient?
  ├─→ YES (≥70% pages) → run_tier1()
  └─→ NO → run_tier2() [OCRExtractor]
        ↓
TextExtractor.detect_financial_pages()
  → Returns: page numbers with WACC/cost keywords
        ↓
Check for tables?
  ├─→ YES → run_tier3() [VisionExtractor with page pre-filter]
  └─→ NO → Skip Vision (unless quality insufficient)
        ↓
cross_reference() (if both text and Vision results)
  → Merge, flag discrepancies, prioritize Vision for tables
        ↓
ExtractionResult[]
  └─→ To QC Pipeline
```

### Confidence Scoring
```
Tier 1 (Text):      Confidence = 0.6 (unstructured)
Tier 2 (OCR):       Confidence = OCR confidence × 0.8
Tier 3 (Vision):    Confidence = Prompt guidance (0.7-0.95 typical)
Cross-referenced:   Confidence = Weighted average + discrepancy penalty
```

---

## Cost Analysis

### Tier 1 (Text)
- **Per document**: $0
- **Speed**: ~100ms per page
- **Typical doc**: 20 pages = 2 seconds
- **Best for**: 80%+ of native PDFs

### Tier 2 (OCR)
- **Per document**: $0 (CPU cost, not API)
- **Speed**: ~2 seconds per page (server), ~5-10 seconds per page (local)
- **Typical doc**: 20 pages = 40 seconds
- **Best for**: Scanned documents

### Tier 3 (Vision)
- **Per page**: ~$0.01-0.02 (depends on document complexity)
- **Speed**: ~3-5 seconds per page
- **Cost optimization**: Financial page pre-filtering
- **Typical doc**: 20 pages, 3 financial pages = $0.03-0.06
- **Best for**: Complex tables, authoritative extraction

### Example Costs
| Document | Tiers Applied | Cost | Speed |
|----------|---------------|------|-------|
| Native PDF, no tables | Tier 1 | $0 | 2s |
| Native PDF, 3 tables | Tier 1 + 3 | $0.05-0.10 | 10s |
| Scanned document | Tier 2 | $0 | 40s |
| Scanned + tables | Tier 2 + 3 | $0.05-0.10 | 50s |
| Mixed quality | Tier 1→2→3 | $0.05-0.10 | 15s |

---

## Integration Points

### Config Module
- `config/thresholds.py`: Cost of capital plausibility ranges
- `config/taxonomy.py`: Controlled vocabularies (SourceType, ExtractionTier, etc.)

### Models Module
- `models.py`: ExtractionResult, Observation (Pydantic models)
- Schema validation for extracted financial parameters

### QC Pipeline
- Results flow to `/oefo/qc/` for validation
- Confidence scores guide QC strategy selection
- Source quotes enable spot-checking

### Data Output
- Results saved to `/oefo/outputs/` as JSON/CSV
- ExtractionResult.to_dict() for serialization

---

## Performance Optimization

### Text Extraction
- Lazy loading: only extract when needed
- Fallback strategy: pdfplumber → PyMuPDF (no exception)
- Page-level processing: handle large documents gracefully

### OCR Extraction
- DPI optimization: 300 DPI for tables, 200 DPI for text
- Preprocessing: Gaussian threshold reduces noise
- Language selection: Reduces OCR ambiguity

### Vision Extraction
- Financial page pre-filtering: Process ~10-20% of pages
- DPI optimization: 250 DPI balances quality and tokens
- Max pages limit: Prevents runaway costs (MAX_PAGES_PER_EXTRACTION = 10)

### General
- Logging at INFO level for production
- DEBUG level for detailed diagnostics
- No unnecessary re-processing (cross-reference deduplication)

---

## Testing Strategy

### Unit Tests (per module)
- `test_text.py`: Native extraction on sample PDFs
- `test_ocr.py`: OCR quality on scanned images
- `test_vision.py`: API integration with mock responses
- `test_pipeline.py`: Decision tree logic, cross-reference
- `test_prompts.py`: Prompt rendering and schema validation

### Integration Tests
- End-to-end extraction on sample documents
- Multi-tier fallback scenarios
- Cross-reference reconciliation
- Result validation against Pydantic models

### Sample Documents
- `test_data/regulatory_wacc.pdf` (English, native text)
- `test_data/dfi_loan_terms.pdf` (Portuguese, with tables)
- `test_data/corporate_filing.pdf` (English, complex balance sheets)
- `test_data/bond_prospectus.pdf` (German, multilingual)
- `test_data/scanned_document.pdf` (Low-quality scan)

---

## Error Handling Strategy

### Graceful Degradation
```
Tier 1 fails
  ↓
Try Tier 2 (OCR)
  ↓
If still insufficient
  ↓
Apply Tier 3 (Vision) to all pages
  ↓
If all fail
  ↓
Return empty results with error logs
```

### Logging at Each Stage
- TextExtractor: WARN when fallback to PyMuPDF
- OCRExtractor: ERROR when Tesseract unavailable
- VisionExtractor: ERROR when API key invalid
- Pipeline: INFO for major decisions, ERROR for failures

### Dependencies Validation
- Startup check: Each __init__ validates required libraries
- Graceful warnings: Non-fatal missing deps → log + continue
- Fatal errors: API key missing, core library absent → raise

---

## Future Enhancements

1. **Caching Layer**: Store extracted text locally to avoid re-processing
2. **Batch Processing**: Process multiple documents in parallel
3. **Fine-tuned Models**: Custom extraction models for OEFO vocabulary
4. **Confidence Feedback**: Learn from QC corrections to improve scores
5. **Table Parsing**: Advanced cell merging/header detection
6. **Multilingual Expansion**: Add zh, ja, ar, ru language packs
7. **Performance Monitoring**: Token usage tracking, latency metrics

---

## References

- Pdfplumber Docs: https://github.com/jsvine/pdfplumber
- PyMuPDF Docs: https://pymupdf.readthedocs.io/
- Tesseract Docs: https://github.com/UB-Mannheim/tesseract/wiki
- Anthropic API: https://docs.anthropic.com/
- OEFO Models: `/sessions/fervent-tender-allen/mnt/ET Finance/oefo/models.py`
