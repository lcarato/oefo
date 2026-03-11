# OEFO Extraction Package

The extraction package implements OEFO's PDF-to-structured-data flow.

## Entry points

- `oefo extract <pdf> --source-type {regulatory,dfi,corporate,bond}`
- `oefo extract-batch <directory> --source-type {regulatory,dfi,corporate,bond}`

## Package structure

- `pipeline.py`: orchestrates extraction
- `text.py`: native-text extraction
- `ocr.py`: OCR extraction
- `vision.py`: vision-model extraction
- `prompts/`: prompt definitions by source type

## Prerequisites

- Poppler (`pdftoppm`, `pdfinfo`)
- Tesseract OCR
- a configured LLM provider for vision-dependent flows
