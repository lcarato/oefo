---
name: oefo-export-database
description: Export the OEFO database to Excel, CSV, and other formats
---

# OEFO Database Export Skill

## Steps

1. **Export full Excel workbook** (with summary sheets, pivot tables, methodology)
   ```bash
   python -m oefo export --format excel --output outputs/oefo_database.xlsx
   ```

2. **Export flat CSV** (for researchers)
   ```bash
   python -m oefo export --format csv --output outputs/oefo_database.csv
   ```

3. **Export Parquet** (for data pipelines)
   ```bash
   python -m oefo export --format parquet --output outputs/oefo_database.parquet
   ```

4. **Show database statistics**
   ```bash
   python -m oefo status
   ```
