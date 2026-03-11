# OEFO Scraper Modules Reference

Complete scraper implementations for energy financing data collection from 8 sources across DFIs, corporate filings, and regulatory agencies.

## File Structure

```
scrapers/
├── __init__.py                    # Main module with factory functions
├── base.py                        # BaseScraper abstract class (340 lines)
├── ifc.py                         # IFC scraper (255 lines)
├── ebrd.py                        # EBRD scraper (313 lines)
├── gcf.py                         # GCF scraper (259 lines)
├── sec_edgar.py                   # SEC EDGAR scraper (341 lines)
└── regulatory/
    ├── __init__.py                # Regulatory submodule exports
    ├── base.py                    # RegulatoryScraperBase (110 lines)
    ├── aneel.py                   # Brazil ANEEL (297 lines)
    ├── aer.py                     # Australia AER (270 lines)
    ├── ofgem.py                   # UK Ofgem (258 lines)
    └── ferc.py                    # US FERC (262 lines)

Total: 12 files, 2,848 lines of code
```

## Base Scraper Features

**File:** `base.py`

Core functionality inherited by all scrapers:

- **HTTP Requests**: `get_page(url)` with built-in retries (3x with exponential backoff)
- **Rate Limiting**: Configurable delay between requests (default: 1.0s, SEC: 0.1s)
- **File Download**: `download_file(url, filename)` and `download_pdf(url, filename)`
- **HTML Parsing**: `get_soup(url)` returns BeautifulSoup object
- **Content Hash**: SHA-256 deduplication via `_compute_content_hash()`
- **Document Registration**: `register_document()` creates RawDocument metadata
- **Deduplication**: `is_duplicate()` checks against stored hashes
- **Logging**: Comprehensive debug/info/warning/error logs

Key Methods:
```python
class BaseScraper(ABC):
    def __init__(name, base_url, output_dir, rate_limit=1.0)
    def get_page(url) -> Response
    def get_soup(url) -> BeautifulSoup
    def download_file(url, filename) -> Path
    def download_pdf(url, filename) -> Path
    def is_duplicate(url, filepath) -> bool
    def register_document(url, filepath, source_type, ...) -> RawDocument
    @abstractmethod
    def scrape() -> list[RawDocument]
```

## Development Finance Institutions (DFIs)

### IFC - International Finance Corporation

**File:** `ifc.py` (255 lines)

Target: `disclosures.ifc.org`

Focus: Energy sector project disclosures
- Environmental & Social Review Summary (ESRS) documents
- Sector Information Summaries (SII)
- Project Appraisal Documents (PAD)

Methods:
- `search_projects(sector="energy", status=None)` - Find energy projects
- `scrape_project_page(url)` - Extract project metadata
- `download_project_documents(project_url)` - Download all disclosure PDFs
- `parse_project_metadata(soup)` - Parse name, country, sector, amount

### EBRD - European Bank for Reconstruction and Development

**File:** `ebrd.py` (313 lines)

Target: `ebrd.com/projects`

Focus: Energy projects with downloadable CSV master list
- Master project list (CSV) - unique feature
- Individual Project Summary Documents (PSDs)
- Energy sector filtering

Methods:
- `download_master_csv()` - Download official project list
- `filter_energy_projects(csv_path)` - Extract energy sector
- `scrape_project_page(url)` - Extract project details
- `download_project_summary(url)` - Download PSD PDF

### GCF - Green Climate Fund

**File:** `gcf.py` (259 lines)

Target: `greenclimate.fund/projects`

Focus: Climate mitigation and adaptation projects
- Energy sector project listings
- Funding proposals (50+ page PDFs)
- Detailed financial and technical information

Methods:
- `list_projects(sector="energy")` - Search by sector
- `scrape_project_page(url)` - Extract metadata
- `download_funding_proposal(url)` - Download full proposal PDF

## Corporate Filings

### SEC EDGAR - US Securities Exchange Commission

**File:** `sec_edgar.py` (341 lines)

Target: `efts.sec.gov` (Full-Text Search API) + `data.sec.gov` (XBRL API)

Focus: US company filings with financial metrics
- 10-K (annual reports) - WACC, cost of capital
- 10-Q (quarterly reports)
- 8-K (material events)
- S-1 (registration statements)

Features:
- Full-text search API for document discovery
- XBRL structured data API for machine-readable financials
- Rate limit: 0.1s between requests (SEC requirement: max 10/second)

Methods:
- `search_by_keyword(keyword, filing_types)` - Full-text search
- `search_filings(company, filing_type)` - Company-specific
- `get_company_cik(ticker_or_name)` - CIK lookup
- `get_xbrl_data(cik, filing_type)` - Extract structured data
- `download_filing(url)` - Download PDF or HTML

## Regulatory Agencies

All regulatory scrapers inherit from `RegulatoryScraperBase` (regulatory/base.py).

### ANEEL - Brazil (Agência Nacional de Energia Elétrica)

**File:** `regulatory/aneel.py` (297 lines)

Target: `aneel.gov.br/regulacao-tarifaria`

Language: Portuguese

Focus: Tariff review decisions with explicit WACC decomposition
- Revisões tarifárias (tariff reviews) every 4-5 years
- Full CAPM decomposition published
- Risk-free rate (taxa livre de risco)
- Equity risk premium (prêmio de risco)
- Beta coefficients
- Cost of debt calculations

**Very High Value**: ANEEL publishes complete WACC breakdown

Methods:
- `list_decisions()` - Get tariff review decisions
- `download_decision(decision_id)` - Download decision PDF
- `classify_document(text)` - Check for WACC content

### AER - Australia (Australian Energy Regulator)

**File:** `regulatory/aer.py` (270 lines)

Target: `aer.gov.au/networks-pipelines/guidelines-schemes-models-reviews/rate-of-return`

Language: English

Focus: Rate of return determinations with binding calculations
- RIIO-equivalent Australian framework
- 5-year regulatory periods
- Detailed CAPM models
- Excel spreadsheets with calculations
- Explicit cost of equity and debt

Methods:
- `list_decisions()` - Get rate of return determinations
- `download_decision(decision_id)` - Download PDF or Excel model
- `classify_document(text)` - Verify rate-of-return content

**High Value**: Binding determinations with Excel models

### Ofgem - UK (Office of Gas and Electricity Markets)

**File:** `regulatory/ofgem.py` (258 lines)

Target: `ofgem.gov.uk/networks-pipelines/.../price-control`

Language: English

Focus: RIIO (Revenue = Incentives + Innovation + Outputs) price controls
- Electricity transmission and distribution price controls
- 8-year regulatory periods with annual updates
- WACC determinations with cost of equity
- Cost of debt calculations
- Network company determinations

Methods:
- `list_decisions()` - Get price control decisions
- `download_decision(decision_id)` - Download decision PDF
- `classify_document(text)` - Verify WACC content

### FERC - US (Federal Energy Regulatory Commission)

**File:** `regulatory/ferc.py` (262 lines)

Target: `ferc.gov` + `elibrary.ferc.gov`

Language: English

Focus: Rate cases and project orders with financial analysis
- Natural Gas Act rate cases
- Certificate applications with capital structure
- Order 888/889 tariff filings
- Hydroelectric and pipeline licensing
- Return on equity (ROE) determinations

Methods:
- `list_decisions()` - Get rate cases and orders
- `download_decision(decision_id)` - Download order PDF
- `classify_document(text)` - Check for cost of capital

## Usage Examples

### Basic Usage

```python
from scrapers import get_scraper

# Initialize scraper
ifc = get_scraper("IFC")

# Run scraping
documents = ifc.scrape()

# Process results
for doc in documents:
    print(f"Downloaded: {doc.document_title}")
    print(f"  URL: {doc.source_url}")
    print(f"  File: {doc.local_file_path}")
    print(f"  Hash: {doc.content_hash}")
```

### Advanced Usage with Custom Output Dir

```python
# Get scraper with custom output directory
ebrd = get_scraper("EBRD", output_dir="data/raw/ebrd_custom")

# Scrape returns RawDocument objects with full metadata
docs = ebrd.scrape()

# Each document can be accessed for processing
for doc in docs:
    if doc.download_status == "downloaded":
        # Process PDF file
        with open(doc.local_file_path, 'rb') as f:
            # Extract text, tables, etc.
            pass
```

### List Available Scrapers

```python
from scrapers import list_scrapers

available = list_scrapers()
# ['IFC', 'EBRD', 'GCF', 'SEC', 'ANEEL', 'AER', 'Ofgem', 'FERC']
```

## Key Features

### Rate Limiting
- Default: 1.0 second between requests
- SEC EDGAR: 0.1 seconds (regulatory requirement)
- Configurable per scraper

### Retry Logic
- 3 automatic retries with exponential backoff (1s, 2s, 4s)
- Handles transient errors (429, 500, 502, 503, 504)
- Respects HTTP timeouts (30 seconds default)

### Content Deduplication
- SHA-256 hashing of downloaded files
- Detects and prevents duplicate downloads
- Hash stored in RawDocument for audit trail

### HTTP Headers
- Professional User-Agent string
- Includes "(OEFO Data Collection Bot)" identifier
- Respects robots.txt via requests library

### Logging
- DEBUG: Detailed HTTP requests and parsing
- INFO: Document downloads, registration
- WARNING: Missing content, failed operations
- ERROR: Scraping failures with context

### Error Handling
- Graceful degradation on network errors
- Fallback strategies (e.g., HTML when PDF unavailable)
- Comprehensive error messages
- Continues processing on individual failures

## Integration with OEFO Pipeline

1. **Data Collection**: Scrapers download documents
2. **Metadata Storage**: RawDocument objects track provenance
3. **Deduplication**: Content hash prevents duplicates
4. **Extraction Pipeline**: Documents fed to LLM extraction
5. **QC & Validation**: Observations validated against source

RawDocument fields used by downstream:
- `source_url`: Audit trail
- `content_hash`: Deduplication verification
- `local_file_path`: Access raw document
- `source_type`: Filter by document type
- `download_date`: Track collection timing
- `document_title`: Human-readable identification

## Dependencies

- `requests`: HTTP client with retry support
- `BeautifulSoup4`: HTML parsing
- `urllib3`: Retry logic (included with requests)
- `pandas`: CSV processing (EBRD)

All included in standard Python package management.

## Performance Notes

- Typical scraping rates: 20-50 documents/hour (respecting rate limits)
- Large PDFs (50+ pages) download in 5-10 seconds
- Content hashing adds minimal overhead (<100ms per file)
- Logging writes to stdout by default

## Extending Scrapers

To add a new scraper:

1. **Inherit from BaseScraper** or RegulatoryScraperBase
2. **Implement abstract methods**: `scrape()`, and for regulatory `list_decisions()`, `download_decision()`, `classify_document()`
3. **Use base class methods**: `get_page()`, `download_pdf()`, `register_document()`
4. **Add to registry** in `__init__.py`

Example template:
```python
class NewScraper(BaseScraper):
    def __init__(self, output_dir="data/raw/new"):
        super().__init__(
            name="NEW",
            base_url="https://example.com",
            output_dir=output_dir,
        )
    
    def scrape(self):
        documents = []
        # Implementation
        return documents
```

Then add to registry:
```python
_SCRAPERS = {
    "NEW": NewScraper,
    # ...
}
```
