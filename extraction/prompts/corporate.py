"""
Extraction prompt for corporate annual reports and financial filings.

Handles consolidated financial statements, debt schedules, cost of capital
calculations, and investor presentations from energy companies.
"""

from typing import Optional


def get_prompt(language: Optional[str] = None) -> str:
    """
    Get extraction prompt for corporate annual reports and filings.

    Args:
        language: Optional language code (e.g., 'en', 'pt', 'es', 'de', 'fr').

    Returns:
        Extraction prompt string.
    """
    base_instructions = """You are a corporate finance analyst specializing in energy companies.

Your task: Extract cost of capital and capital structure parameters from corporate annual reports, 10-K filings, and investor presentations.

IMPORTANT OUTPUT FORMAT:
Return ONLY valid JSON in this exact structure:
{
  "pages": [
    {
      "page_num": <integer>,
      "debt_information": {
        "total_debt_usd": {
          "value": <float or null>,
          "unit": "USD million",
          "source_quote": "<exact quote>"
        },
        "interest_expense_annual_usd": {
          "value": <float or null>,
          "unit": "USD million",
          "source_quote": "<exact quote>"
        },
        "implicit_cost_of_debt": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote or calculated from interest/debt>"
        },
        "average_maturity_years": {
          "value": <float or null>,
          "unit": "years",
          "source_quote": "<exact quote>"
        },
        "credit_rating": {
          "value": "<rating or null>",
          "source_quote": "<exact quote>"
        }
      },
      "equity_information": {
        "market_cap_usd": {
          "value": <float or null>,
          "unit": "USD million",
          "source_quote": "<exact quote>"
        },
        "book_equity_usd": {
          "value": <float or null>,
          "unit": "USD million",
          "source_quote": "<exact quote>"
        },
        "cost_of_equity_disclosed": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        }
      },
      "capital_structure": {
        "total_capitalization_usd": {
          "value": <float or null>,
          "unit": "USD million",
          "source_quote": "<exact quote>"
        },
        "leverage_ratio_book": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        },
        "leverage_ratio_market": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        }
      },
      "cost_of_capital": {
        "wacc_disclosed": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        },
        "tax_rate": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        }
      },
      "company_info": {
        "company_name": "<name or null>",
        "country": "<country code or null>",
        "fiscal_year": "<year or null>"
      },
      "confidence_score": <float between 0.0 and 1.0>,
      "notes": "<any adjustments, one-time items, or calculation notes>"
    }
  ]
}

EXTRACTION RULES:
1. For each value, provide source_quote: the exact text from the financial statements.
2. If value is ambiguous or not found, set to null and explain in notes.
3. All percentages in decimal form (5.5 for 5.5%, not 0.055).
4. Implicit cost of debt = annual interest expense / total debt (if not explicitly stated).
5. Confidence score: 1.0 for explicit statements, 0.5 for calculated, 0.0 for not found.
6. Note any one-time charges or non-recurring items affecting calculations.
7. Distinguish between book value and market value leverage if both present.

PRIORITY ITEMS TO EXTRACT:
- Total debt and interest expense (calculate cost of debt)
- Market capitalization and book equity (capital structure)
- Leverage ratios (book and market)
- Disclosed WACC and cost of equity (if provided)
- Tax rate (affects after-tax cost of debt)
- Credit rating (market discipline indicator)

MANDATORY TRACEABILITY REQUIREMENTS:
For EVERY extracted value you MUST provide:
1. source_quote: The EXACT verbatim text from the financial statements (copy-paste, do not paraphrase).
2. page_num: The page number where the data appears (1-indexed, matching the PDF page).
3. If the data comes from a table or balance sheet line item, also provide the table/statement name.
4. If the value is CALCULATED (e.g., implicit cost of debt = interest/debt), explain the
   calculation in notes and provide source_quote(s) for each input value.
5. NEVER leave source_quote empty for non-null values. If you cannot find a supporting quote,
   set the value to null and explain in notes.
"""

    if language and language.lower().startswith("pt"):
        return base_instructions + """

INSTRUÇÕES ADICIONAIS PARA RELATÓRIOS CORPORATIVOS EM PORTUGUÊS:
- Procure por: divida total, despesa com juros, patrimonio liquido
- Taxa de imposto: pode estar em notas às demonstrações financeiras
- Rating de crédito: procure por agências (Moody's, S&P, Fitch)
- Alavancagem: Dívida/(Dívida + Patrimônio)
- Confiança: explique se há inconsistências entre seções do relatório
- Grandes empresas de energia no Brasil: Petrobras, Vale, Eletrobras, EDP
"""

    elif language and language.lower().startswith("es"):
        return base_instructions + """

INSTRUCCIONES ADICIONALES PARA INFORMES CORPORATIVOS EN ESPAÑOL:
- Busque: deuda total, gasto por intereses, patrimonio neto
- Tasa fiscal: puede estar en notas a los estados financieros
- Calificación crediticia: busque agencias (Moody's, S&P, Fitch)
- Apalancamiento: Deuda/(Deuda + Patrimonio)
- Confianza: explique si hay inconsistencias entre secciones del informe
- Grandes empresas de energía: Repsol, Iberdrol, Enel, Acciona
"""

    elif language and language.lower().startswith("de"):
        return base_instructions + """

ZUSÄTZLICHE ANWEISUNGEN FÜR UNTERNEHMENSBERICHTE AUF DEUTSCH:
- Suchen Sie nach: Gesamtschuld, Zinsaufwand, Eigenkapital
- Steuersatz: kann in Anmerkungen zu den Abschlüssen stehen
- Kreditrating: Agenturen (Moody's, S&P, Fitch)
- Hebelwirkung: Schulden/(Schulden + Eigenkapital)
- Vertrauen: erklären Sie, wenn es Inkonsistenzen gibt
- Große Energieunternehmen: E.ON, RWE, Siemens Energy
"""

    elif language and language.lower().startswith("fr"):
        return base_instructions + """

INSTRUCTIONS SUPPLÉMENTAIRES POUR LES RAPPORTS D'ENTREPRISE EN FRANÇAIS:
- Recherchez: endettement total, frais d'intérêts, capitaux propres
- Taux d'impôt: peut être dans les notes aux états financiers
- Notation de crédit: agences (Moody's, S&P, Fitch)
- Effet de levier: Dette/(Dette + Capitaux propres)
- Confiance: expliquez s'il y a des incohérences
- Grandes entreprises énergétiques: TotalEnergies, EDF, GDF Suez, Shell
"""

    else:
        return base_instructions + """

EXAMPLE EXTRACTIONS:

Example 1 - Debt from Balance Sheet:
Balance Sheet excerpt:
"Long-term debt: USD 2,400M
Short-term debt: USD 150M
Interest expense (2023): USD 180M"
→ total_debt_usd.value = 2550 (2400 + 150)
→ interest_expense_annual_usd.value = 180
→ implicit_cost_of_debt.value = 7.06 (180/2550)
→ confidence_score = 1.0

Example 2 - Market Value Capital Structure:
"Market capitalization at fiscal year-end: USD 8,500M
Total debt: USD 2,550M
Total capitalization: USD 11,050M"
→ market_cap_usd.value = 8500
→ total_debt_usd.value = 2550
→ total_capitalization_usd.value = 11050
→ leverage_ratio_market.value = 23.1 (2550/11050)
→ confidence_score = 1.0

Example 3 - Tax Rate from Footnotes:
"The effective tax rate for 2023 was 24%. The company expects similar rates going forward."
→ tax_rate.value = 24
→ source_quote = "The effective tax rate for 2023 was 24%"
→ confidence_score = 1.0
→ notes = "Based on 2023 effective rate; company expects similar going forward"

Example 4 - Disclosed WACC:
"The company uses a WACC of 6.5% for project valuations, based on a 40% debt cost of 5% (after-tax) and 60% equity cost of 7.5%"
→ wacc_disclosed.value = 6.5
→ leverage_ratio_book.value = 40
→ implicit_cost_of_debt.value = 5.0
→ cost_of_equity_disclosed.value = 7.5
→ confidence_score = 1.0
"""
