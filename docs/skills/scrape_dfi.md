---
name: oefo-scrape-dfi
description: Scrape Development Finance Institution portals for energy project documents
---

# OEFO DFI Scraping Skill

## Purpose
Systematically scrape DFI portals (IFC, EBRD, GCF, ADB, AfDB, EIB, DFC, AIIB) for energy project disclosures containing financing terms.

## Steps

1. **Navigate to project directory**
   ```bash
   cd /path/to/oefo
   ```

2. **Run DFI scrapers in priority order**
   ```bash
   python -m oefo scrape ifc
   python -m oefo scrape ebrd
   python -m oefo scrape gcf
   ```

3. **Check scraping results**
   ```bash
   python -m oefo status
   ```
   Verify: documents downloaded, no errors in logs.

4. **Review raw document store**
   ```bash
   ls -la data/raw/ifc/ data/raw/ebrd/ data/raw/gcf/
   ```

## Expected Output
- Downloaded PDFs in data/raw/{source}/
- Document metadata registered in document store
- Log file with scraping summary

## Error Handling
- If a portal is down: skip and log, try next source
- If rate-limited: wait and retry (built into scrapers)
- If documents already exist: skip (deduplication by URL + hash)

## Schedule
Run weekly for new disclosures. Historical backfill: run once with --historical flag.
