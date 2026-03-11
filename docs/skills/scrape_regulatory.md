---
name: oefo-scrape-regulatory
description: Scrape regulatory filings for WACC parameters across 15+ jurisdictions
---

# OEFO Regulatory Scraping Skill

## Phase 1 Regulators (Priority)
1. ANEEL (Brazil) - Portuguese, full CAPM decomposition
2. AER (Australia) - English, binding rate of return instrument
3. Ofgem (UK) - English, RIIO framework
4. FERC (USA) - English, rate case orders

## Steps
```bash
# Phase 1 regulators
python -m oefo scrape aneel
python -m oefo scrape aer
python -m oefo scrape ofgem
python -m oefo scrape ferc

# Phase 2 regulators (add as scrapers are built)
# python -m oefo scrape bnetza    # Germany
# python -m oefo scrape cnmc      # Spain
# python -m oefo scrape cre       # France
# python -m oefo scrape arera     # Italy
# python -m oefo scrape creg      # Colombia
# python -m oefo scrape osinergmin # Peru
# python -m oefo scrape nersa     # South Africa
# python -m oefo scrape cerc      # India
```

## Notes
- Regulatory documents are multilingual. The extraction pipeline handles Portuguese, Spanish, German, French, Italian natively via the model-agnostic Vision layer.
- WACC parameter tables in regulatory docs are best handled by Tier 3 (Vision) extraction.
- These produce the highest-confidence Ke observations in the database.
