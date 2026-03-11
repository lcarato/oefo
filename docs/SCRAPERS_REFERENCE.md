# OEFO Scraper Reference

The scraper package lives in `src/oefo/scrapers/`.

## Available scraper entry names

- `ifc`
- `ebrd`
- `gcf`
- `sec`
- `aneel`
- `aer`
- `ofgem`
- `ferc`
- `all`

## Factory usage

```python
from oefo.scrapers import get_scraper, list_scrapers

print(list_scrapers())
scraper = get_scraper("IFC")
documents = scraper.scrape()
```

## CLI usage

```bash
oefo scrape ifc
oefo scrape all
```

## Package structure

- `src/oefo/scrapers/base.py`
- `src/oefo/scrapers/ifc.py`
- `src/oefo/scrapers/ebrd.py`
- `src/oefo/scrapers/gcf.py`
- `src/oefo/scrapers/sec_edgar.py`
- `src/oefo/scrapers/regulatory/aneel.py`
- `src/oefo/scrapers/regulatory/aer.py`
- `src/oefo/scrapers/regulatory/ofgem.py`
- `src/oefo/scrapers/regulatory/ferc.py`

## Notes

- Live scraping depends on network access and upstream site stability.
- The automated test suite avoids live-site assertions by design.
