# Scraper Learnings — Live Run 2026-03-14

Results from running the full pipeline against live websites.

---

## Summary Table

| Scraper | Discovery | Documents | Status | Issue |
|---------|-----------|-----------|--------|-------|
| **SEC** | 24 filings | 0 (scrape only tested search) | WORKING | Search works; download untested |
| **EBRD** | 36 projects | CSV generated | WORKING | CSV field is "Project Name" not "title" |
| **GCF** | 166 projects | — | WORKING (slow) | HEAD requests to 300 URLs takes ~2 min |
| **IFC** | 50 projects | 0 | BROKEN (download) | SIIProject API returns empty `SupportingDocuments` for all projects |
| **ANEEL** | 1 decision | — | WORKING (limited) | Only finds 1 link on Proret page |
| **AER** | 0 | 0 | BROKEN | Site times out (HTTP/2 outage) |
| **Ofgem** | 2 decisions | — | WORKING (limited) | Only finds generic fallback links, not RIIO-specific |
| **FERC** | 0 | 0 | BROKEN | eLibrary is now an Angular SPA — BS4 gets empty shell |

---

## Detailed Findings

### SEC EDGAR — WORKING

- `search_by_keyword("cost of capital", filing_types=["10-K"])` returns **24 results**
- Companies found: American States Water Co, PG&E Corp, IPG Photonics Corp
- Proper field mapping: company names, CIKs, filing dates, accession numbers
- Filing URLs constructed correctly
- **Next step**: Test actual PDF download path

### EBRD — WORKING

- AEM search servlet at `/bin/ebrd_dxp/ebrdsearchservlet` returns **36 energy projects**
- CSV correctly saved to `data/raw/ebrd/ebrd_projects_api.csv`
- Fields: `Project Name`, `Project URL`, `Date`, `Sector`, `Tags`
- Project URLs correctly converted from AEM paths
- Mix of PSD project pages and news articles
- **Fix needed**: The `download_project_summary()` fallback reads CSV `title` column but CSV uses `Project Name`

### GCF — WORKING (Slow)

- `list_projects()` iterates FP numbers 1–300 with HEAD requests
- Found **166 valid projects** (e.g., fp001, fp005, fp006, fp007, fp009...)
- Takes ~2 minutes due to rate limiting (~0.5s per request x 300)
- **Optimization**: Could use the project listing page at `https://www.greenclimate.fund/projects` instead of brute-force, or cache known FP numbers

### IFC — BROKEN (Document Download)

- **Discovery works**: Landing API returns 5 investment + 5 advisory projects
- Search API (`searchenterpriseprojects`) returns **500 errors** for all 3 body format attempts
- Fallback brute-force ID validation (52000→51952) finds ~49 valid project numbers
- **Root cause**: `SIIProject` API returns project metadata but `SupportingDocuments` is ALWAYS an empty array `[]`
- The IFC site renders project documents client-side — the API simply doesn't serve them
- Tested projects: 51976 (Yakeey), 50350 (Vision One Growth Equity) — both have `SupportingDocuments: []`
- The actual disclosure content (Summary of Investment Information) is embedded in the `ProjectOverView.Project_Description` HTML field
- **Fix**: Either (a) extract data directly from `ProjectOverView` HTML instead of looking for PDF downloads, or (b) find a different endpoint that serves the actual SII PDF documents

### ANEEL — WORKING (Limited)

- Successfully scrapes `gov.br/aneel/pt-br` Proret page
- Finds **1 decision**: "Módulo 2 - Revisão Tarifária Periódica das Concessionárias de Distribuição de Energia Elétrica"
- The site structure has multiple submódulos but keyword matching is too narrow
- **Fix**: Broaden keyword list or directly scrape known submódulo 2.4 URL (cost of capital methodology)

### AER — BROKEN (Site Outage)

- `aer.gov.au` is experiencing HTTP/2 connection issues / timeouts
- First URL tried (`/industry/networks/rate-of-return`) hangs indefinitely
- This is an external issue, not a code bug
- The `_known_documents()` fallback would work if the site came back
- **Fix**: Add connection timeout (currently blocked on `get_soup`), and consider caching known URLs

### Ofgem — WORKING (Limited)

- Publications search returns no RIIO-specific results
- Falls back to network price controls page, finds **2 generic links**: "Finances", "Energy network price controls"
- These are navigation links, not actual RIIO decision documents
- **Fix**: The search URL may need updating, or try direct RIIO-2 decision page URLs:
  - `ofgem.gov.uk/publications/riio-2-final-determinations`
  - `ofgem.gov.uk/energy-policy-and-regulation/policy-and-regulatory-programmes/network-price-controls/riio-2`

### FERC — BROKEN (Angular SPA)

- FERC eLibrary has been **rewritten as an Angular SPA**
- Response is `<!DOCTYPE html>` with Material Icons, `<base href="/eLibrary/">` — classic Angular app shell
- Zero `<tr>` rows in response because content is rendered client-side
- BS4 cannot extract any data
- **Fix**: FERC eLibrary likely has a backing REST API. Need to inspect the Angular app's network requests to find the actual JSON endpoint. Alternatively, use Selenium/Playwright or switch to FERC's EDGAR-like public data feeds.

---

## Cross-Cutting Issues

### 1. SPA Sites (IFC, FERC)
Both IFC and FERC have moved to Angular SPAs. BS4 only gets the shell HTML. Options:
- Find and use their backing REST APIs (preferred — faster, more reliable)
- Use headless browser (Selenium/Playwright) as fallback
- IFC: REST API exists but document arrays are empty
- FERC: REST API needs to be discovered via browser dev tools

### 2. Timeout Handling
AER blocks indefinitely. The `get_soup()` method in `base.py` should have a configurable timeout (or the scrapers should set shorter timeouts for discovery vs download).

### 3. Rate Limiting vs Speed
GCF's brute-force HEAD approach is too slow. All scrapers should prefer API/listing endpoints over iterating.

### 4. Field Name Mismatches
EBRD CSV uses `Project Name` but downstream code may expect `title`. Need consistent field naming.

---

## Priority Fixes for Next Run

1. **FERC**: Discover the Angular app's REST API endpoint (highest value regulatory source)
2. **IFC**: Extract data from `ProjectOverView.Project_Description` instead of looking for PDFs, OR discover PDF endpoint
3. **AER**: Add connection timeout; use cached/known URLs until site recovers
4. **GCF**: Replace brute-force HEAD with project listing page scrape
5. **Ofgem**: Add direct RIIO-2 determination page URLs
6. **ANEEL**: Broaden keyword matching for submódulo pages
