---
name: oefo-extract-documents
description: Run multi-modal extraction pipeline on downloaded documents
---

# OEFO Document Extraction Skill

## Purpose
Extract structured financial data (Kd, Ke, WACC, leverage, etc.) from downloaded PDFs using the multi-modal pipeline (Text → OCR → Vision).

## Prerequisites
- Raw documents in data/raw/ (run scrape skill first)
- ANTHROPIC_API_KEY set (or OPENAI_API_KEY / GOOGLE_API_KEY for fallback)
- System packages: poppler-utils (for pdf2image), tesseract-ocr

## Steps

1. **Install system dependencies** (first run only)
   ```bash
   # macOS
   brew install poppler tesseract tesseract-lang

   # Ubuntu/Debian
   sudo apt-get install poppler-utils tesseract-ocr tesseract-ocr-por tesseract-ocr-spa tesseract-ocr-deu tesseract-ocr-fra tesseract-ocr-ita
   ```

2. **Extract from DFI documents**
   ```bash
   python -m oefo extract-batch data/raw/ifc/ --source-type dfi
   python -m oefo extract-batch data/raw/ebrd/ --source-type dfi
   python -m oefo extract-batch data/raw/gcf/ --source-type dfi
   ```

3. **Extract from regulatory documents**
   ```bash
   python -m oefo extract-batch data/raw/aneel/ --source-type regulatory
   python -m oefo extract-batch data/raw/aer/ --source-type regulatory
   python -m oefo extract-batch data/raw/ofgem/ --source-type regulatory
   python -m oefo extract-batch data/raw/ferc/ --source-type regulatory
   ```

4. **Extract from corporate filings**
   ```bash
   python -m oefo extract-batch data/raw/sec/ --source-type corporate
   python -m oefo extract-batch data/raw/annual_reports/ --source-type corporate
   ```

5. **Check extraction results**
   ```bash
   python -m oefo status
   ```

## Tier Decision Logic
- Tier 1 (text): Fast, free. Used for clean digital PDFs.
- Tier 2 (OCR): For scanned documents. Uses Tesseract with language packs.
- Tier 3 (Vision): For complex tables, merged cells, multilingual content.
  Model-agnostic: tries Claude → GPT-4o → Gemini → Ollama in fallback order.
- Tier 4 (human): Flagged for manual review.

## Cost Management
- Vision calls are ~$0.01-0.02/page. Pipeline only sends relevant pages (2-5 per doc).
- Set OEFO_LLM_PROVIDER=ollama for free local extraction (lower quality).

## Expected Output
- Extracted observations in data/extracted/ (Parquet format)
- Extraction logs with tier usage statistics
