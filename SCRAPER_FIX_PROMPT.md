# OEFO Scraper Fine-Tuning Task

## Objective

Fix all 8 OEFO web scrapers so they successfully discover and download documents from their target websites. The scrapers currently connect to each site but return 0 documents because their HTML parsers don't match the current website structures.

## Project Context

OEFO (Open Energy Finance Observatory) is a data pipeline that scrapes financial documents (PDFs) from energy development banks, regulators, and corporate filings, then extracts cost-of-capital data (Kd, Ke, WACC, leverage) using LLMs.

**Repository root:** Current working directory
**Scraper code:** `src/oefo/scrapers/`
**Tests:** `tests/`
**Python:** Use system Python (`python` or `python -m pytest`)

## Architecture (DO NOT change)

```
BaseScraper (src/oefo/scrapers/base.py)
  ├── IFCScraper (ifc.py)
  ├── EBRDScraper (ebrd.py)
  ├── GCFScraper (gcf.py)
  ├── SECEdgarScraper (sec_edgar.py)
  └── RegulatoryScraperBase (regulatory/base.py)
       ├── ANEELScraper (regulatory/aneel.py)
       ├── AERScraper (regulatory/aer.py)
       ├── OfgemScraper (regulatory/ofgem.py)
       └── FERCScraper (regulatory/ferc.py)
```

Each scraper inherits from `BaseScraper` which provides: `get_page(url)`, `get_soup(url)`, `download_file(url, filename)`, `download_pdf(url, filename)`, `register_document(...)`, `is_duplicate(...)`. The `scrape()` method takes NO arguments — it returns `list[RawDocument]`.

Factory function `get_scraper(name, **kwargs)` passes kwargs to the constructor (e.g., `output_dir`).

## What Failed — Pipeline Run Log (March 2026)

```
Phase 2: Scraping 8 source(s)...

[IFC] disclosures.ifc.org
  - GET /projects returned HTML but search_projects() found 0 links matching "/projects/" pattern
  - Root cause: IFC site likely uses JS-rendered content or different URL structure

[EBRD] ebrd.com
  - CSV export URL https://www.ebrd.com/documents/projects/export.csv → 404
  - Fallback _scrape_project_list() finds 0 <tr> rows on /projects page
  - Root cause: EBRD no longer serves a CSV export; project list is API-driven

[GCF] greenclimate.fund
  - list_projects() found 13 links matching "/projects/" pattern
  - BUT all 13 were navigation links (/projects/commitment, /projects/dashboard, etc.)
  - download_funding_proposal() found no PDF links on any of those pages
  - Root cause: GCF project URLs follow /projects/FP### pattern, not scraped correctly

[ANEEL] aneel.gov.br
  - GET /regulacao-tarifaria → 404 (redirected to wrong URL: gov.br/aneelregulacao-tarifaria)
  - Root cause: URL construction bug or site migration to gov.br domain

[AER] aer.gov.au
  - GET /networks-pipelines/guidelines-schemes-models-reviews/rate-of-return → ReadTimeoutError (3 retries)
  - Root cause: AER site is slow or blocks automated requests; may need different URL

[Ofgem] ofgem.gov.uk
  - GET /networks-pipelines/financial-regulation-electricity-and-gas-networks/... → 404
  - Root cause: Ofgem has restructured their website; URL path is stale

[FERC] ferc.gov
  - GET /search/orders → 403 Forbidden
  - Root cause: FERC blocks direct scraping; need to use eLibrary API instead

[SEC] sec.gov
  - efts.sec.gov/LATEST/search-index → 403 Forbidden (all 5 keyword searches)
  - Root cause: SEC full-text search API endpoint is wrong or rate-limited
```

## What You Must Do

For each of the 8 scrapers:

1. **Visit the actual website** (use WebFetch or curl) to understand the current page structure
2. **Update the scraper code** to match what the website actually serves today
3. **Verify** the scraper can find at least 1 document URL (you can test individual methods)

### Specific Guidance Per Scraper

#### 1. IFC (`src/oefo/scrapers/ifc.py`)
- Target: `https://disclosures.ifc.org`
- The IFC disclosure portal may use a REST API or different search mechanism
- Try: `https://disclosures.ifc.org/enterprise-search-api/search?sectors_exact=Energy` or similar
- Goal: Find energy project disclosure PDFs (ESRS documents)

#### 2. EBRD (`src/oefo/scrapers/ebrd.py`)
- Target: `https://www.ebrd.com`
- The CSV export at `/documents/projects/export.csv` no longer exists
- Try: EBRD has an API at `https://www.ebrd.com/api/projects` or similar
- Alternative: Use their project search at `https://www.ebrd.com/work-with-us/project-finance/project-summary-documents.html`
- Goal: Find energy project summary document PDFs

#### 3. GCF (`src/oefo/scrapers/gcf.py`)
- Target: `https://www.greenclimate.fund`
- Project URLs are like `/projects/FP001`, `/projects/FP002`, etc.
- The `/projects` page lists projects but the scraper picked up nav links instead
- Try: `https://www.greenclimate.fund/projects` and look for the actual project listing
- GCF may have an API or the project list may be in a JSON endpoint
- Goal: Find funding proposal PDFs for energy projects

#### 4. SEC EDGAR (`src/oefo/scrapers/sec_edgar.py`)
- Target: `https://efts.sec.gov/LATEST/search-index` → this is WRONG
- Correct endpoint: `https://efts.sec.gov/LATEST/search-index?q=...&dateRange=custom&startdt=2024-01-01&enddt=2026-03-14&forms=10-K,10-Q`
- OR use the newer EDGAR full-text search: `https://efts.sec.gov/LATEST/search-index?q=...`
- The SEC requires a proper User-Agent header with contact info (already set in BaseScraper)
- SEC rate limit: max 10 req/sec
- Goal: Find 10-K/10-Q filings from energy utilities

#### 5. ANEEL (`src/oefo/scrapers/regulatory/aneel.py`)
- Target: `https://www.gov.br/aneel/` (site has migrated from aneel.gov.br to gov.br/aneel)
- Update `base_url` to `https://www.gov.br/aneel/pt-br`
- Tariff review docs: look for "Revisão Tarifária" or "Custo de Capital" sections
- Goal: Find tariff review PDFs with WACC calculations

#### 6. AER (`src/oefo/scrapers/regulatory/aer.py`)
- Target: `https://www.aer.gov.au`
- The rate of return page URL may have changed
- Try: `https://www.aer.gov.au/industry/registers/resources/rate-of-return` or search the AER site
- AER publishes "Rate of Return Instrument" documents (2022 instrument is key)
- Goal: Find rate of return determination PDFs and Excel models

#### 7. Ofgem (`src/oefo/scrapers/regulatory/ofgem.py`)
- Target: `https://www.ofgem.gov.uk`
- Old URL path is 404; Ofgem has restructured
- Try: `https://www.ofgem.gov.uk/energy-policy-and-regulation/policy-and-regulatory-programmes/network-price-controls`
- RIIO-2 (ED2, T2, GD2) decisions contain WACC parameters
- Goal: Find RIIO price control decision PDFs

#### 8. FERC (`src/oefo/scrapers/regulatory/ferc.py`)
- Target: `https://www.ferc.gov` and `https://elibrary.ferc.gov`
- `/search/orders` returns 403 — FERC blocks direct page scraping
- Use eLibrary search API: `https://elibrary.ferc.gov/eLibrary/search?q=...`
- Alternative: FERC has a data API at `https://api.ferc.gov/` for Form 1 data
- Goal: Find rate case order PDFs or Form 1 data

## Constraints

- **DO NOT** change `BaseScraper`, `RegulatoryScraperBase`, or the `scrape()` method signature (no args)
- **DO NOT** change `__init__.py` or the factory function
- **DO NOT** add new pip dependencies (use only: requests, beautifulsoup4, pandas, which are already installed)
- **DO** update URLs, parsing logic, search patterns, and API calls within each scraper
- **DO** add fallback strategies (e.g., if main URL fails, try alternative)
- **DO** respect rate limits (already handled by BaseScraper)
- Each scraper must be able to find **at least some** documents even if the full catalog isn't accessible
- Run `python -m pytest tests/ -q` after changes to ensure nothing breaks

## Verification

After fixing, test each scraper individually:

```python
from oefo.scrapers import get_scraper

scraper = get_scraper("IFC", output_dir="/tmp/test_ifc")
# Test the search/list method first:
urls = scraper.search_projects()  # or list_decisions(), list_projects(), etc.
print(f"Found {len(urls)} items")

# Then test full scrape (downloads files):
docs = scraper.scrape()
print(f"Downloaded {len(docs)} documents")
```

A scraper is "fixed" when its search/list method returns >0 results pointing to real document URLs.

## Priority Order

Fix in this order (highest value first):
1. **SEC EDGAR** — richest data, just needs correct API endpoint
2. **GCF** — found 13 projects, just needs correct URL filtering
3. **EBRD** — needs API discovery or alternative URL
4. **IFC** — needs API or JS-rendered content handling
5. **AER** — may just need updated URL
6. **ANEEL** — domain migration to gov.br
7. **Ofgem** — URL restructure
8. **FERC** — most complex, may need eLibrary API
