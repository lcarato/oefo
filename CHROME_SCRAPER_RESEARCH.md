# Chrome-Based Scraper Research Instructions

Use Claude in Chrome (MCP tool) to navigate each target site and discover alternative scraping methods that complement the sitemap-first strategy.

---

## 1. FERC eLibrary (HIGHEST PRIORITY)

**URL**: https://elibrary.ferc.gov/eLibrary/search

**Tasks**:
1. Open Chrome DevTools → Network tab (filter XHR/Fetch)
2. Navigate to eLibrary and perform a search for "cost of equity"
3. Log ALL API calls the Angular app makes — especially:
   - The actual REST endpoint URL (likely `/api/v2/...`)
   - Request method (GET/POST), headers, and body
   - Response format (JSON structure)
4. Try searching for "return on equity" and "rate case" to see if different endpoints are used
5. Check if the API requires specific headers (Origin, Referer, CSRF tokens)
6. Look for any cookie/session requirements
7. Test if the API calls work from a different browser tab (copy as cURL)

**What we know**: The Angular app uses `this.ApiUrl + "/GetFileList/"` and `"/GetFileListByAccession/"` endpoints. Direct calls return "Request Rejected" (WAF). Need to identify what headers/cookies bypass the WAF.

---

## 2. IFC Disclosures

**URL**: https://disclosures.ifc.org/project-detail/SII/51976

**Tasks**:
1. Open a project detail page with Chrome DevTools → Network tab
2. Check if document download links appear after JS rendering
3. Look for any additional API calls that load document lists
4. Check if there's a "Documents" tab or section that loads lazily
5. Navigate to https://disclosures.ifc.org and use the search/filter to find energy projects
6. Log the search API calls and their parameters
7. Check the `searchenterpriseprojects` POST endpoint — what body format does the browser actually send?

**What we know**: The `SIIProject` API returns `SupportingDocuments: []`. The site is Angular SPA. The sitemap has 3,638 AS-SII project URLs.

---

## 3. Ofgem Publications

**URL**: https://www.ofgem.gov.uk/search/publications?keyword=RIIO+cost+of+equity

**Tasks**:
1. Open the publications search page with DevTools → Network tab
2. Check if search results are loaded via AJAX/Fetch calls
3. If so, capture the API endpoint and response format
4. Navigate to known working pages:
   - https://www.ofgem.gov.uk/publications/riio-ed2-final-determinations
   - https://www.ofgem.gov.uk/publications/riio-2-sector-specific-methodology-decision
5. Identify the pattern for RIIO publication URLs
6. Check if there's a publications API that returns JSON

---

## 4. FERC Alternative Data Sources

**Tasks**:
1. Navigate to https://www.ferc.gov/industries-data
2. Look for any downloadable data files (CSV, Excel, XML)
3. Check https://www.ferc.gov/ferc-online — what tools are available?
4. Search for "Form 1" data downloads (utility financial data)
5. Check if FERC publishes on data.gov: https://catalog.data.gov/organization/ferc-gov
6. Look for FERC XBRL data feeds

---

## 5. Open Data Portals

Check if any of our regulators publish on national open data portals:

- **US**: https://data.gov — search for "FERC", "SEC energy"
- **UK**: https://data.gov.uk — search for "Ofgem", "RIIO", "energy regulation"
- **Brazil**: https://dados.gov.br — search for "ANEEL", "tarifa", "WACC"
- **Australia**: https://data.gov.au — search for "AER", "rate of return", "energy regulation"
- **International**: https://data.worldbank.org — search for "cost of capital energy"

---

## 6. Direct PDF URL Patterns

For each regulator, check if PDFs follow predictable naming:

- **Ofgem**: Already found pattern: `/sites/default/files/YYYY-MM/RIIO-*.pdf`
- **ANEEL**: Check if `www2.aneel.gov.br/cedoc/` has a browsable directory
- **AER**: Check `www.aer.gov.au/system/files/` pattern
- **FERC**: Check if eLibrary PDFs are at predictable URLs like `elibrary.ferc.gov/idmws/common/opennat.asp?fileID=...`

---

## 7. Browser Headers Analysis

For each site that blocks Python requests:
1. Open the page in Chrome
2. Copy the successful request as cURL (Right-click → Copy → Copy as cURL)
3. Compare headers with what Python requests sends
4. Identify which headers are required (likely: Referer, Origin, specific cookies, Accept)

---

## Output

Document all findings in a structured format:
```
### [Site Name]
- **API Endpoint**: [URL]
- **Method**: [GET/POST]
- **Required Headers**: [list]
- **Request Body**: [if POST]
- **Response Format**: [JSON structure]
- **Notes**: [any additional findings]
```
