# OEFO Scrapers Architecture

All scrapers live under `src/oefo/scrapers/` and share a common factory surface.

## Hierarchy

- `BaseScraper`
- DFI scrapers: `IFCScraper`, `EBRDScraper`, `GCFScraper`
- Corporate filings: `SECEdgarScraper`
- Regulatory scrapers: `ANEELScraper`, `AERScraper`, `OfgemScraper`, `FERCScraper`

## Public helpers

- `oefo.scrapers.get_scraper(name)`
- `oefo.scrapers.list_scrapers()`
