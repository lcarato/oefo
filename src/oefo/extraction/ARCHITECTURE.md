# OEFO Extraction Architecture

The extraction package lives in `src/oefo/extraction/` and routes PDFs through
three tiers:

1. native text extraction
2. OCR
3. vision-model extraction

## Modules

- `text.py`: native-text and table extraction helpers
- `ocr.py`: OCR flow using Poppler-generated images and Tesseract
- `vision.py`: vision-model extraction helpers
- `pipeline.py`: orchestration across the available tiers
- `prompts/`: source-type-specific prompt templates

## Operational note

OCR and image-based extraction depend on host tools such as Poppler and
Tesseract. Use `scripts/oefo_env_check.py` before running extraction commands.
