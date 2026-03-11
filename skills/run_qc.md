---
name: oefo-run-qc
description: Run the QC Agent on extracted observations
---

# OEFO QC Agent Skill

## Purpose
Validate extracted observations through 3-layer QC (rules → statistics → LLM) and route them to auto-accept, human review, or rejection.

## Steps

1. **Run full QC pipeline**
   ```bash
   python -m oefo qc --full
   ```
   This runs all three layers:
   - Layer 1: Rule-based checks (range plausibility, internal consistency, format validation)
   - Layer 2: Statistical checks (Damodaran benchmarks, peer comparison, macro consistency)
   - Layer 3: LLM cross-validation (source quote verification, coherence check)

2. **Or run rules-only QC** (fast, no API calls)
   ```bash
   python -m oefo qc --rules-only
   ```

3. **Review QC results**
   ```bash
   python -m oefo status
   ```
   Expected breakdown: ~40% auto-accept, ~45% flagged, ~15% rejected.

4. **Export flagged observations for human review**
   ```bash
   python -m oefo export --format excel --output outputs/flagged_for_review.xlsx --filter qc_status=flagged
   ```

## QC Scoring
- Score >0.85: Auto-accept → enters database
- Score 0.50-0.85: Flagged → human review queue
- Score <0.50: Rejected → re-extract or discard

## Model-Agnostic LLM Layer
Layer 3 uses the LLMClient with automatic fallback:
- Primary: Claude (ANTHROPIC_API_KEY)
- Fallback 1: GPT-4o (OPENAI_API_KEY)
- Fallback 2: Gemini (GOOGLE_API_KEY)
- Fallback 3: Ollama (local, no API key needed)
- If no LLM available: Layer 3 returns INSUFFICIENT, observation flagged for human review
