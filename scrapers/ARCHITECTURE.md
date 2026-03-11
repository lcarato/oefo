# OEFO Scrapers Architecture

## Design Principles

1. **Inheritance Hierarchy**: All scrapers inherit common functionality from `BaseScraper`
2. **Rate Limiting**: Respect server resources with configurable delays
3. **Deduplication**: Content-based (SHA-256) prevents duplicate downloads
4. **Error Resilience**: Graceful degradation with automatic retries
5. **Metadata Tracking**: Full audit trail via `RawDocument` objects
6. **Extensibility**: Easy to add new scrapers via factory pattern

## Class Hierarchy

```
BaseScraper (abstract)
├── IFCScraper
├── EBRDScraper
├── GCFScraper
├── SECEdgarScraper
└── RegulatoryScraperBase (abstract)
    ├── ANEELScraper
    ├── AERScraper
    ├── OfgemScraper
    └── FERCScraper
```

## Module Dependencies

```
models.py
├── SourceType (enum)
├── DocumentStatus (enum)
└── RawDocument (model)

scrapers/
├── base.py (imports: models, requests, BeautifulSoup, urllib3)
│   └── __init__.py (imports: all scrapers, factory functions)
│
├── ifc.py (imports: base.BaseScraper, models)
├── ebrd.py (imports: base.BaseScraper, models, pandas)
├── gcf.py (imports: base.BaseScraper, models)
├── sec_edgar.py (imports: base.BaseScraper, models, requests)
│
└── regulatory/
    ├── __init__.py (imports: all regulatory scrapers)
    ├── base.py (imports: base.BaseScraper, models)
    ├── aneel.py (imports: regulatory.base, models)
    ├── aer.py (imports: regulatory.base, models)
    ├── ofgem.py (imports: regulatory.base, models)
    └── ferc.py (imports: regulatory.base, models)
```

## Data Flow

### Scraping Flow

```
Scraper.scrape()
    ↓
list_decisions() / search_projects()
    ↓
scrape_project_page() / download_decision()
    ↓
download_pdf() / download_file()
    ↓
_compute_content_hash()
    ↓
is_duplicate()
    ↓
register_document()
    ↓
RawDocument (with metadata)
    ↓
Return list[RawDocument]
```

### HTTP Request Flow

```
get_page(url)
    ↓
Rate limit check (time.sleep if needed)
    ↓
Session.get() with Retry adapter
    ↓
Retry strategy (3x with exponential backoff)
    ↓
response.raise_for_status()
    ↓
Return Response
```

## Feature Matrix

| Feature | BaseScraper | IFC | EBRD | GCF | SEC | ANEEL | AER | Ofgem | FERC |
|---------|-------------|-----|------|-----|-----|-------|-----|-------|------|
| Rate Limiting | Yes | Yes | Yes | Yes | Yes (0.1s) | Yes | Yes | Yes | Yes |
| Retry Logic | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Content Hash | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| PDF Download | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| HTML Parsing | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Metadata Registry | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Deduplication | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Multi-format Download | - | - | Yes* | - | Yes** | - | Yes* | - | - |
| CSV Processing | - | - | Yes | - | - | - | - | - | - |
| XBRL Support | - | - | - | - | Yes | - | - | - | - |
| Language Support | EN | EN | EN | EN | EN | PT | EN | EN | EN |

*EBRD: PDF + fallback scraping; AER: PDF + Excel models
**SEC: PDF + HTML alternatives

## Concurrency Model

All scrapers are **single-threaded** by design to respect rate limiting and server load.

For parallel scraping, implement external orchestration:

```python
from concurrent.futures import ThreadPoolExecutor
from scrapers import get_scraper

def scrape_source(name):
    scraper = get_scraper(name)
    return scraper.scrape()

sources = ["IFC", "EBRD", "GCF", "SEC", "ANEEL", "AER", "Ofgem", "FERC"]

with ThreadPoolExecutor(max_workers=2) as executor:
    results = executor.map(scrape_source, sources)
    all_documents = []
    for docs in results:
        all_documents.extend(docs)
```

Note: Adjust `max_workers` based on rate limits (e.g., 2 for typical operations, 1 for SEC).

## Error Handling Strategy

1. **HTTP Errors** (automatic retries via Retry adapter)
   - 429 (Rate Limited) → Exponential backoff
   - 5xx (Server Error) → Exponential backoff
   - Other errors → Fail immediately

2. **Network Errors** (caught and logged)
   - Timeout → Logged as warning, continue
   - Connection error → Logged as error, continue
   - DNS error → Logged as error, continue

3. **Parsing Errors** (caught and logged)
   - Missing expected elements → Log warning, use fallback
   - Invalid HTML → Log warning, continue
   - PDF parsing issues → Log error, skip document

4. **File I/O Errors** (caught and logged)
   - Permission denied → Raise error, stop scraper
   - Disk full → Raise error, stop scraper
   - Path issues → Log error, continue

## Logging Strategy

All scrapers use `logging` module with hierarchical loggers:

```
oefo.scrapers
├── oefo.scrapers.base
├── oefo.scrapers.ifc
├── oefo.scrapers.ebrd
├── oefo.scrapers.gcf
├── oefo.scrapers.sec_edgar
└── oefo.scrapers.regulatory
    ├── oefo.scrapers.regulatory.base
    ├── oefo.scrapers.regulatory.aneel
    ├── oefo.scrapers.regulatory.aer
    ├── oefo.scrapers.regulatory.ofgem
    └── oefo.scrapers.regulatory.ferc
```

Configure logging at application level:

```python
import logging

# Set all scrapers to INFO level
logging.getLogger("oefo.scrapers").setLevel(logging.INFO)

# Or DEBUG for detailed output
logging.getLogger("oefo.scrapers").setLevel(logging.DEBUG)
```

## Performance Characteristics

### HTTP Performance
- Average document download: 5-10 seconds
- Large PDFs (50+ pages): 10-30 seconds
- Rate-limited request rate: 1 doc/second (default), 10 docs/second (SEC)

### Computational Performance
- Content hash (SHA-256): ~100ms per file
- BeautifulSoup parsing: ~50ms per page
- CSV filtering (EBRD): ~500ms per 1000 rows

### Memory Performance
- Scraper instance: ~5MB
- Typical session: 50-100 documents = 50-100MB RAM
- Large PDF downloads: Streaming (no full buffer)

## Testing Strategies

### Unit Testing
```python
from unittest.mock import Mock, patch
from scrapers import get_scraper

@patch('scrapers.base.requests.Session.get')
def test_rate_limiting(mock_get):
    mock_get.return_value = Mock(status_code=200)
    scraper = get_scraper("IFC")
    # Assert rate_limit applied
```

### Integration Testing
```python
def test_ifc_scraping():
    ifc = get_scraper("IFC")
    docs = ifc.scrape()
    assert len(docs) > 0
    assert all(isinstance(d, RawDocument) for d in docs)
```

### Mock Scraping
```python
# Use responses library to mock HTTP
import responses

@responses.activate
def test_with_mock_responses():
    responses.add(responses.GET, 'https://example.com/api', json={})
    scraper = get_scraper("CustomScraper")
    docs = scraper.scrape()
```

## Configuration & Customization

### Per-Scraper Configuration

```python
# Custom rate limiting
scraper = get_scraper("IFC", rate_limit=2.0)

# Custom output directory
scraper = get_scraper("EBRD", output_dir="/data/custom/ebrd")

# Combined
scraper = get_scraper("SEC", 
                     output_dir="/data/sec",
                     rate_limit=0.1)
```

### Global Configuration

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("oefo.scrapers")
logger.setLevel(logging.DEBUG)

# Custom handler
handler = logging.FileHandler("scraping.log")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
```

## Monitoring & Observability

### Key Metrics to Track

1. **Download Metrics**
   - Total documents downloaded
   - Total bytes transferred
   - Average file size

2. **Performance Metrics**
   - Average request latency
   - Retry count by status code
   - Content hash computation time

3. **Quality Metrics**
   - Deduplication hit rate
   - Parse error rate
   - Network error rate

4. **Resource Metrics**
   - Memory usage
   - Disk space used
   - Concurrent connections

### Instrumentation Example

```python
import time
from scrapers import get_scraper

scraper = get_scraper("IFC")
start = time.time()
docs = scraper.scrape()
duration = time.time() - start

print(f"Downloaded {len(docs)} documents in {duration:.1f}s")
print(f"Rate: {len(docs)/duration:.1f} docs/sec")
print(f"Total bytes: {sum(d.file_size_bytes for d in docs if d.file_size_bytes)}")
```

## Future Enhancements

1. **Async Support**: Use `aiohttp` for concurrent requests
2. **Incremental Scraping**: Resume from checkpoint on failures
3. **Intelligent Scheduling**: Detect document publication cycles
4. **Advanced Filtering**: Content-based filtering before download
5. **API Support**: Direct integration with DFI/regulatory APIs (where available)
6. **Caching**: Local cache with TTL for frequently accessed content
7. **Proxy Support**: Rotate proxies for large-scale scraping
8. **Browser Automation**: Selenium for JavaScript-heavy sites

## License & Attribution

All scrapers respect:
- robots.txt guidelines
- Terms of Service of target websites
- Data usage policies
- Copyright and licensing terms

This tool is for research and authorized data collection only.
