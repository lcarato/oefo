"""
Extraction prompt for DFI (Development Finance Institution) project disclosures.

Handles project finance loan terms, capital structure, and financing conditions
from multilateral development bank project documents.
"""

from typing import Optional


def get_prompt(language: Optional[str] = None) -> str:
    """
    Get extraction prompt for DFI project disclosure documents.

    Args:
        language: Optional language code (e.g., 'en', 'pt', 'es', 'de', 'fr').

    Returns:
        Extraction prompt string.
    """
    base_instructions = """You are a development finance expert specializing in project finance documents.

Your task: Extract loan terms and capital structure parameters from DFI (World Bank, ADB, IFC, etc.) project disclosure documents.

IMPORTANT OUTPUT FORMAT:
Return ONLY valid JSON in this exact structure:
{
  "pages": [
    {
      "page_num": <integer>,
      "loan_terms": {
        "loan_amount_usd": {
          "value": <float or null>,
          "unit": "USD million",
          "source_quote": "<exact quote>"
        },
        "loan_tenor_years": {
          "value": <float or null>,
          "unit": "years",
          "source_quote": "<exact quote>"
        },
        "interest_rate": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        },
        "benchmark_rate": {
          "value": "<SOFR | EURIBOR | LIBOR | other>",
          "spread_bps": <integer or null>,
          "unit": "basis points",
          "source_quote": "<exact quote>"
        },
        "grace_period_years": {
          "value": <float or null>,
          "unit": "years",
          "source_quote": "<exact quote>"
        }
      },
      "capital_structure": {
        "total_financing_usd": {
          "value": <float or null>,
          "unit": "USD million",
          "source_quote": "<exact quote>"
        },
        "debt_amount_usd": {
          "value": <float or null>,
          "unit": "USD million",
          "source_quote": "<exact quote>"
        },
        "equity_amount_usd": {
          "value": <float or null>,
          "unit": "USD million",
          "source_quote": "<exact quote>"
        },
        "leverage_ratio": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        }
      },
      "cost_of_capital": {
        "cost_of_debt": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        },
        "wacc": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        }
      },
      "project_info": {
        "project_name": "<name or null>",
        "country": "<country code or null>",
        "technology": "<technology type or null>"
      },
      "confidence_score": <float between 0.0 and 1.0>,
      "notes": "<any clarifications, currency conversions, or special conditions>"
    }
  ]
}

EXTRACTION RULES:
1. For each value, provide source_quote: the exact text from the document.
2. If value is ambiguous or not found, set to null and explain in notes.
3. All percentages in decimal form (5.5 for 5.5%, not 0.055).
4. Loan amounts typically in USD millions; note currency conversions if applied.
5. Confidence score: 1.0 for explicit statements, 0.5 for implied, 0.0 for not found.
6. Note any special terms (covenants, guarantees, subordination, prepayment options).

PRIORITY ITEMS TO EXTRACT:
- Loan amount and tenor (fundamental terms)
- Interest rate and benchmark (cost of debt components)
- Leverage/capital structure (financing composition)
- Cost of debt and WACC (if disclosed)
- Grace period and other special terms

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
- Procure por: taxa de juros, spread, prazo do empréstimo, estrutura de capital
- Valor do empréstimo pode estar em: USD, EUR, ou moeda local
- Alavancagem: relação dívida/capital total
- Confiança: explique se há ambigüidades na documentação portuguesa
- DFIs comuns: Banco Interamericano, Banco Asiático de Desenvolvimento, Banco Mundial
"""

    elif language and language.lower().startswith("es"):
        return base_instructions + """

INSTRUCCIONES ADICIONALES PARA DOCUMENTOS EN ESPAÑOL:
- Busque: tasa de interés, spread, plazo del préstamo, estructura de capital
- Monto del préstamo puede estar en: USD, EUR, o moneda local
- Apalancamiento: ratio deuda/capital total
- Confianza: explique si hay ambigüedades en los documentos españoles
- Instituciones DFI comunes: CAF, Banco Interamericano, Banco Asiático
"""

    elif language and language.lower().startswith("de"):
        return base_instructions + """

ZUSÄTZLICHE ANWEISUNGEN FÜR DEUTSCHE DOKUMENTE:
- Suchen Sie nach: Zinssatz, Spread, Kreditlaufzeit, Kapitalstruktur
- Darlehensbetrag kann sein: USD, EUR, oder lokale Währung
- Hebelwirkung: Verhältnis von Schulden zu Gesamtkapital
- Vertrauen: erklären Sie, wenn es Mehrdeutigkeiten gibt
- Übliche DFI: Europäische Investitionsbank, Kreditanstalt für Wiederaufbau
"""

    elif language and language.lower().startswith("fr"):
        return base_instructions + """

INSTRUCTIONS SUPPLÉMENTAIRES POUR LES DOCUMENTS EN FRANÇAIS:
- Recherchez: taux d'intérêt, spread, durée du prêt, structure du capital
- Montant du prêt peut être: USD, EUR, ou moneda locale
- Effet de levier: ratio dette/capital total
- Confiance: expliquez s'il y a des ambigüités
- IFD courantes: AFD, Banque africaine de développement, Banque mondiale
"""

    else:
        return base_instructions + """

EXAMPLE EXTRACTIONS:

Example 1 - Standard DFI Loan:
"IFC provides a senior loan of USD 45 million for 15 years at SOFR + 350 basis points. Grace period of 3 years."
→ loan_amount_usd.value = 45
→ loan_tenor_years.value = 15
→ benchmark_rate.value = "SOFR"
→ spread_bps.value = 350
→ grace_period_years.value = 3
→ interest_rate.value ≈ current SOFR + 3.5% (note as calculated)
→ confidence_score = 1.0

Example 2 - Capital Structure Table:
Project financing structure:
| Debt                | USD 80M | 64% |
| Equity              | USD 45M | 36% |
| Total               | USD 125M| 100%|
→ debt_amount_usd.value = 80
→ equity_amount_usd.value = 45
→ total_financing_usd.value = 125
→ leverage_ratio.value = 64
→ confidence_score = 1.0

Example 3 - Implied Cost of Debt:
"Bank loan at LIBOR + 200 bps, current LIBOR = 3.5%"
→ benchmark_rate.value = "LIBOR"
→ spread_bps.value = 200
→ interest_rate.value = 5.5 (or note: calculated as LIBOR[date] + 200bps)
→ cost_of_debt.value = 5.5
→ confidence_score = 0.8
→ notes = "Interest rate calculated from benchmark + spread at time of document"
"""
