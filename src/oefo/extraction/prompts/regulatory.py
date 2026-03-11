"""
Extraction prompt for regulatory WACC documents.

Handles regulatory cost of capital filings with focus on WACC decomposition,
CAPM parameters, and regulatory frameworks.
"""

from typing import Optional


def get_prompt(language: Optional[str] = None) -> str:
    """
    Get extraction prompt for regulatory documents.

    Args:
        language: Optional language code (e.g., 'en', 'pt', 'es', 'de', 'fr').

    Returns:
        Extraction prompt string.
    """
    base_instructions = """You are a financial expert specializing in regulatory cost of capital documents.

Your task: Extract WACC (Weighted Average Cost of Capital) components and parameters from the provided regulatory document pages.

IMPORTANT OUTPUT FORMAT:
Return ONLY valid JSON in this exact structure:
{
  "pages": [
    {
      "page_num": <integer>,
      "wacc_parameters": {
        "wacc": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote from document>"
        },
        "cost_of_debt": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        },
        "cost_of_equity": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        },
        "leverage_debt_percent": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        },
        "leverage_equity_percent": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        }
      },
      "capm_components": {
        "risk_free_rate": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        },
        "market_risk_premium": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        },
        "beta": {
          "value": <float or null>,
          "unit": "unitless",
          "source_quote": "<exact quote>"
        }
      },
      "debt_parameters": {
        "risk_free_rate_debt": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        },
        "credit_spread": {
          "value": <float or null>,
          "unit": "basis points",
          "source_quote": "<exact quote>"
        },
        "tax_rate": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        }
      },
      "confidence_score": <float between 0.0 and 1.0>,
      "notes": "<any clarifications, ambiguities, or special notes>"
    }
  ]
}

EXTRACTION RULES:
1. For each value, provide source_quote: the exact text from the document supporting it.
2. If a value is ambiguous or not found, set to null and explain in notes field.
3. All percentages should be in decimal form (5.5 for 5.5%, not 0.055).
4. Confidence score reflects how clearly the value was stated (1.0 = explicit statement, 0.5 = implied, 0.0 = not found).
5. Look for regulatory frameworks (utility regulation, DFI guidelines, etc.) that constrain methodology.

PRIORITY ITEMS TO EXTRACT:
- WACC (most important)
- Cost of debt and cost of equity (fundamental components)
- Leverage ratios (capital structure)
- CAPM parameters (if present: risk-free rate, market risk premium, beta)
- Debt parameters (if disclosed: spread, tax rate)

MANDATORY TRACEABILITY REQUIREMENTS:
For EVERY extracted value you MUST provide:
1. source_quote: The EXACT verbatim text from the document (copy-paste, do not paraphrase).
2. page_num: The page number where the data appears (1-indexed, matching the PDF page).
3. If the data comes from a table, also provide the table title/header as context.
4. If the value is CALCULATED (not directly stated), explain the calculation in notes and
   still provide the source_quote(s) for the input values used.
5. NEVER leave source_quote empty for non-null values. If you cannot find a supporting quote,
   set the value to null and explain in notes.
"""

    if language and language.lower().startswith("pt"):
        return base_instructions + """

INSTRUÇÕES ADICIONAIS PARA DOCUMENTOS EM PORTUGUÊS:
- Procure por: CAPM, taxa livre de risco, prêmio de risco de mercado, beta
- Custo de dívida pode aparecer como: taxa de juros, spread, cupom
- Alavancagem pode ser listada como: relação D/E, capital próprio/capital de terceiros
- Confiança: explique se há ambiguidades no texto português
"""

    elif language and language.lower().startswith("es"):
        return base_instructions + """

INSTRUCCIONES ADICIONALES PARA DOCUMENTOS EN ESPAÑOL:
- Busque: CAPM, tasa libre de riesgo, prima de riesgo de mercado, beta
- Costo de deuda puede aparecer como: tasa de interés, spread, cupón
- Apalancamiento puede aparecer como: relación D/E, capital propio/deuda
- Confianza: explique si hay ambigüedades en el texto español
"""

    elif language and language.lower().startswith("de"):
        return base_instructions + """

ZUSÄTZLICHE ANWEISUNGEN FÜR DEUTSCHE DOKUMENTE:
- Suchen Sie nach: CAPM, risikofreier Satz, Marktrisiko-Prämie, Beta
- Fremdkapitalkosten können erscheinen als: Zinssatz, Spread, Coupon
- Hebelwirkung kann erscheinen als: D/E-Verhältnis, Eigenkapital/Fremdkapital
- Vertrauen: erklären Sie, wenn es Mehrdeutigkeiten im deutschen Text gibt
"""

    elif language and language.lower().startswith("fr"):
        return base_instructions + """

INSTRUCTIONS SUPPLÉMENTAIRES POUR LES DOCUMENTS EN FRANÇAIS:
- Recherchez: CAPM, taux sans risque, prime de risque de marché, bêta
- Coût de la dette peut apparaître comme: taux d'intérêt, spread, coupon
- Effet de levier peut apparaître comme: ratio D/E, capitaux propres/dette
- Confiance: expliquez s'il y a des ambigüités dans le texte français
"""

    else:
        return base_instructions + """

EXAMPLE EXTRACTIONS:

Example 1 - Clear WACC Statement:
"The WACC is estimated at 7.5% based on a cost of equity of 10.0% and cost of debt of 4.5%, with leverage of 60% debt and 40% equity."
→ wacc.value = 7.5
→ cost_of_equity.value = 10.0
→ cost_of_debt.value = 4.5
→ leverage_debt_percent.value = 60
→ confidence_score = 1.0

Example 2 - CAPM Decomposition Table:
Document shows a table:
Risk-free rate: 2.5%
Market risk premium: 5.0%
Beta: 0.9
→ risk_free_rate.value = 2.5
→ market_risk_premium.value = 5.0
→ beta.value = 0.9
→ cost_of_equity ≈ 2.5 + (5.0 * 0.9) = 7.0

Example 3 - Ambiguous Debt Terms:
"Debt costs are in the range of 4-6% depending on market conditions"
→ credit_spread.value = null
→ confidence_score = 0.3
→ notes = "Debt cost given as range (4-6%), unclear which value applies to this period"
"""
