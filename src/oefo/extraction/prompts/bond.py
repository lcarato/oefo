"""
Extraction prompt for bond prospectuses and offering documents.

Handles debt securities information including coupon rates, maturity, yield,
credit ratings, and use of proceeds from bond offering documents.
"""

from typing import Optional


def get_prompt(language: Optional[str] = None) -> str:
    """
    Get extraction prompt for bond prospectuses and offering documents.

    Args:
        language: Optional language code (e.g., 'en', 'pt', 'es', 'de', 'fr').

    Returns:
        Extraction prompt string.
    """
    base_instructions = """You are a fixed income analyst specializing in bond market analysis.

Your task: Extract bond terms and cost of debt parameters from prospectuses, offering documents, and bond term sheets.

IMPORTANT OUTPUT FORMAT:
Return ONLY valid JSON in this exact structure:
{
  "pages": [
    {
      "page_num": <integer>,
      "bond_terms": {
        "issuer_name": {
          "value": "<name or null>",
          "source_quote": "<exact quote>"
        },
        "issue_size_usd": {
          "value": <float or null>,
          "unit": "USD million",
          "source_quote": "<exact quote>"
        },
        "coupon_rate": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        },
        "maturity_date": {
          "value": "<date or null>",
          "source_quote": "<exact quote>"
        },
        "tenor_years": {
          "value": <float or null>,
          "unit": "years",
          "source_quote": "<exact quote>"
        },
        "currency": {
          "value": "<USD | EUR | GBP | other>",
          "source_quote": "<exact quote>"
        }
      },
      "pricing_terms": {
        "yield_to_maturity": {
          "value": <float or null>,
          "unit": "percent",
          "source_quote": "<exact quote>"
        },
        "benchmark_rate": {
          "value": "<US Treasury | Euribor | other benchmark>",
          "source_quote": "<exact quote>"
        },
        "spread_bps": {
          "value": <integer or null>,
          "unit": "basis points",
          "source_quote": "<exact quote>"
        },
        "issue_price": {
          "value": <float or null>,
          "unit": "percent of par",
          "source_quote": "<exact quote>"
        }
      },
      "credit_information": {
        "issuer_rating": {
          "value": "<rating or null>",
          "agency": "<Moody's | S&P | Fitch | other>",
          "source_quote": "<exact quote>"
        },
        "bond_rating": {
          "value": "<rating or null>",
          "agency": "<Moody's | S&P | Fitch | other>",
          "source_quote": "<exact quote>"
        },
        "seniority": {
          "value": "<senior | subordinated | mezzanine | null>",
          "source_quote": "<exact quote>"
        },
        "debt_type": "<senior | subordinated | mezzanine | bond | concessional | bank_loan | convertible | credit_line | equipment_financing | supplier_credit | null>"
      },
      "issuer_info": {
        "country": "<ISO 3166-1 alpha-3 code or null>",
        "scale": "<utility_scale | commercial_industrial | distributed_residential | portfolio | mega_project | regulated_asset | pilot_demonstration | null>",
        "project_status": "<operating | construction | financial_close | development | decommissioning | null>",
        "value_chain_position": "<generation | fuel_production | fuel_transport | fuel_storage | electricity_transmission | electricity_distribution | electricity_storage | end_use_efficiency | end_use_transport | carbon_management | null>"
      },
      "use_of_proceeds": {
        "primary_purpose": {
          "value": "<purpose or null>",
          "source_quote": "<exact quote>"
        }
      },
      "cost_of_debt": {
        "coupon_as_cost": {
          "value": <float or null>,
          "unit": "percent",
          "notes": "Coupon rate serves as cost of debt proxy"
        },
        "ytm_as_cost": {
          "value": <float or null>,
          "unit": "percent",
          "notes": "YTM reflects market cost of debt at issuance"
        }
      },
      "confidence_score": <float between 0.0 and 1.0>,
      "notes": "<any call provisions, special features, or market conditions>"
    }
  ]
}

EXTRACTION RULES:
1. For each value, provide source_quote: the exact text from the prospectus.
2. If value is ambiguous or not found, set to null and explain in notes.
3. All percentages in decimal form (5.5 for 5.5%, not 0.055).
4. Coupon rate is critical: explicit cost of debt for the bond.
5. YTM reflects market's cost of debt assessment at issuance time.
6. Tenor = years from issue date to maturity.
7. Confidence score: 1.0 for explicit prospectus statements, 0.5 for calculated, 0.0 for not found.
8. Note any special features (subordination, call options, conversion rights).

PRIORITY ITEMS TO EXTRACT:
- Coupon rate (most important for cost of debt)
- Maturity/tenor (timing of cash flows)
- Yield to maturity (market-based cost)
- Credit rating (risk assessment)
- Spread over benchmark (market risk premium)
- Issue size and currency (financing amount)

MANDATORY TRACEABILITY REQUIREMENTS:
For EVERY extracted value you MUST provide:
1. source_quote: The EXACT verbatim text from the prospectus (copy-paste, do not paraphrase).
2. page_num: The page number where the data appears (1-indexed, matching the PDF page).
3. If the data comes from a term sheet or pricing table, include the section heading.
4. If the value is CALCULATED (e.g., YTM from coupon + price), explain in notes and
   provide source_quote(s) for the input values used.
5. NEVER leave source_quote empty for non-null values. If you cannot find a supporting quote,
   set the value to null and explain in notes.
"""

    if language and language.lower().startswith("pt"):
        return base_instructions + """

INSTRUÇÕES ADICIONAIS PARA PROSPECTOS DE TÍTULOS EM PORTUGUÊS:
- Procure por: taxa de cupom, data de vencimento, rendimento até o vencimento
- Spread pode aparecer como "spread sobre" Tesouro ou ANBIMA
- Rating de crédito: agências (Moody's, S&P, Fitch)
- Moeda: pode ser em USD, EUR, ou Real brasileiro
- Confiança: explique se há mudanças nas condições de mercado
- Mercado: emissões em reais podem referenciar CDI ou IPCA
"""

    elif language and language.lower().startswith("es"):
        return base_instructions + """

INSTRUCCIONES ADICIONALES PARA PROSPECTOS DE BONOS EN ESPAÑOL:
- Busque: tasa de cupón, fecha de vencimiento, rendimiento al vencimiento
- Spread puede aparecer sobre Bonos del Tesoro o IBEX
- Calificación crediticia: agencias (Moody's, S&P, Fitch)
- Moneda: puede ser USD, EUR, GBP, o peso/sol local
- Confianza: explique si hay cambios en condiciones de mercado
- Mercados comunes: España, México, Argentina, Chile
"""

    elif language and language.lower().startswith("de"):
        return base_instructions + """

ZUSÄTZLICHE ANWEISUNGEN FÜR ANLEIHEREPROSPEKTE AUF DEUTSCH:
- Suchen Sie nach: Kuponrate, Fälligkeitsdatum, Rendite bis Fälligkeit
- Spread kann über deutsche Bundesanleihen oder EURIBOR erfolgen
- Kreditrating: Agenturen (Moody's, S&P, Fitch)
- Währung: EUR, USD, GBP, oder andere
- Vertrauen: erklären Sie, wenn es Änderungen gibt
- Märkte: Deutsche Börse, europäische Anleihen
"""

    elif language and language.lower().startswith("fr"):
        return base_instructions + """

INSTRUCTIONS SUPPLÉMENTAIRES POUR LES PROSPECTUS D'OBLIGATIONS EN FRANÇAIS:
- Recherchez: taux de coupon, date d'échéance, rendement à l'échéance
- Spread peut être au-dessus des obligations d'État français ou EURIBOR
- Notation de crédit: agences (Moody's, S&P, Fitch)
- Devise: EUR, USD, GBP, ou autre
- Confiance: expliquez s'il y a des changements
- Marchés: Euronext, obligations françaises, obligations souveraines
"""

    else:
        return base_instructions + """

EXAMPLE EXTRACTIONS:

Example 1 - Standard Bond Prospectus:
"Company XYZ issues a USD 500 million bond maturing on March 15, 2035 with a coupon of 4.75%.
The bond is rated Baa1 by Moody's and BBB+ by S&P.
Pricing: 99.5% of par, yield to maturity: 4.85%, spread over 10-year UST: +165 bps"
→ issue_size_usd.value = 500
→ coupon_rate.value = 4.75
→ maturity_date.value = "2035-03-15"
→ tenor_years.value ≈ 10 (2035 - 2025)
→ yield_to_maturity.value = 4.85
→ issuer_rating.value = "Baa1"
→ bond_rating.value = "BBB+"
→ spread_bps.value = 165
→ cost_of_debt (coupon): 4.75
→ cost_of_debt (YTM): 4.85
→ confidence_score = 1.0

Example 2 - Subordinated Bond:
"Subordinated notes, 6-year maturity, 6.5% coupon, rated Ba2/BB"
→ coupon_rate.value = 6.5
→ tenor_years.value = 6
→ seniority.value = "Subordinated"
→ bond_rating.value = "Ba2/BB"
→ confidence_score = 1.0
→ notes = "Higher coupon reflects subordinated status and lower rating"

Example 3 - Floating Rate Bond:
"Floating rate note: SOFR + 250 bps, maturity 5 years"
→ benchmark_rate.value = "SOFR"
→ spread_bps.value = 250
→ tenor_years.value = 5
→ coupon_rate.value = null (variable)
→ cost_of_debt.value ≈ current SOFR + 2.5%
→ confidence_score = 0.8
→ notes = "Floating rate; cost of debt depends on SOFR at each reset date. Example at current SOFR ~5.33%: cost ≈ 7.83%"

Example 4 - Green Bond:
"EUR 300M Green Bond, 10-year maturity, 2.5% coupon, rated A1 by Moody's.
Proceeds to finance renewable energy projects in EU."
→ issue_size_usd.value = 300 (EUR, note currency)
→ currency.value = "EUR"
→ coupon_rate.value = 2.5
→ tenor_years.value = 10
→ issuer_rating.value = "A1"
→ primary_purpose.value = "Renewable energy projects in EU"
→ confidence_score = 1.0
→ notes = "Amount in EUR, not USD; low coupon reflects investment-grade rating and favorable market conditions"
"""
