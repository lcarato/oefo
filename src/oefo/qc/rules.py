"""
Layer 1: Rule-based QC checks for the OEFO data pipeline.

This module implements deterministic, fast validation rules for observations:
- Range plausibility (ensures values fall within expected bounds)
- Internal consistency (cross-field validation)
- Format and type validation
- Duplicate detection

All checks are deterministic and do not require external data or ML models.
"""

import logging
import pprint
from typing import Dict, Any, List, Optional
from datetime import datetime, date
import re

from oefo.models import (
    Observation,
    QCResult,
    QCStatus,
    Scale,
    ValueChainPosition,
    ProjectStatus,
    SourceType,
    TraceabilityLevel,
)
from oefo.config import thresholds

logger = logging.getLogger(__name__)


class RuleBasedQC:
    """
    Deterministic rule-based quality control checks.

    Validates observations against hard constraints: ranges, formats, internal
    consistency, and deduplication rules. Fast, reproducible, and transparent.
    """

    # ISO 3166-1 alpha-3 country codes (sample - actual implementation should use pycountry)
    VALID_ISO_COUNTRIES = {
        'USA', 'GBR', 'DEU', 'FRA', 'ITA', 'ESP', 'NLD', 'BEL', 'AUT', 'CHE',
        'SWE', 'NOR', 'DNK', 'FIN', 'POL', 'CZE', 'HUN', 'ROU', 'BGR', 'HRV',
        'SVN', 'SVK', 'GRC', 'PRT', 'IRL', 'LUX', 'MLT', 'CYP', 'CAN', 'MEX',
        'BRA', 'CHI', 'ARG', 'COL', 'PER', 'VEN', 'ECU', 'BOL', 'PRY', 'URY',
        'JPN', 'CHN', 'IND', 'RUS', 'KOR', 'IDN', 'THA', 'MYS', 'SGP', 'PHL',
        'VNM', 'PAK', 'BGD', 'LKA', 'KEN', 'NGA', 'ZAF', 'EGY', 'MAR', 'ETH',
        'GHA', 'CIV', 'AUS', 'NZL', 'ZWE', 'UGA', 'TZA', 'AGO', 'MOZ', 'TUN',
        'ALG', 'JOR', 'SAU', 'ARE', 'OMN', 'QAT', 'KWT', 'IRN', 'IRQ', 'ISR',
        'ARE', 'VNM', 'TWN', 'HKG', 'MAC',
    }

    # ISO 4217 currency codes (subset)
    VALID_ISO_CURRENCIES = {
        'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD', 'CNY', 'INR',
        'RUB', 'BRL', 'ZAR', 'MXN', 'SGD', 'HKD', 'NOK', 'SEK', 'DKK', 'AED',
        'SAR', 'QAR', 'JOD', 'ILS', 'COP', 'PEN', 'CLP', 'TRY', 'KRW', 'THB',
        'IDR', 'PHP', 'MYR', 'ZWL', 'KES', 'NGN', 'GHS', 'RWF', 'EGP', 'MAD',
        'TND', 'DZD',
    }

    # Controlled vocabularies
    VALID_SCALES = {s.value for s in Scale}
    VALID_VALUE_CHAIN_POSITIONS = {v.value for v in ValueChainPosition}
    VALID_PROJECT_STATUSES = {s.value for s in ProjectStatus}

    def __init__(self):
        """Initialize the rule-based QC checker."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def check(self, observation: Observation) -> QCResult:
        """
        Run all rule-based checks on an observation.

        Args:
            observation: The observation to validate

        Returns:
            QCResult with score, status, flags, and details
        """
        self.logger.info(f"Running rule-based checks on observation {observation.observation_id}")

        flags = []

        # Run all check methods
        flags.extend(self.check_range_plausibility(observation))
        flags.extend(self.check_internal_consistency(observation))
        flags.extend(self.check_concessional(observation))
        flags.extend(self.check_format_and_types(observation))
        flags.extend(self.check_traceability_completeness(observation))

        # Compute score based on flags
        score = self._compute_score_from_flags(len(flags))

        # Determine status
        if thresholds.should_auto_accept(score):
            status = QCStatus.PASSED
        elif thresholds.should_review(score):
            status = QCStatus.FLAGGED
        else:
            status = QCStatus.FAILED

        # Create QC result
        result = QCResult(
            qc_id=f"qc_{observation.observation_id}_{datetime.now().isoformat()}",
            observation_id=observation.observation_id,
            qc_timestamp=datetime.now(),
            qc_agent="RuleBasedQC",
            qc_status=status,
            qc_score=score * 100,  # Convert to 0-100 scale
            qc_flags=flags,
            validation_errors=[f for f in flags if "ERROR" in f],
            validation_warnings=[f for f in flags if "WARNING" in f],
            summary=f"Rule-based checks completed: {len(flags)} flags found",
            details=self._format_details(flags),
            recommended_action=self._recommend_action(status)
        )

        self.logger.info(
            f"Rule-based QC complete: score={score:.2f}, status={status}, "
            f"flags={len(flags)}"
        )
        return result

    def check_range_plausibility(self, obs: Observation) -> List[str]:
        """
        Check if numeric parameters fall within plausible ranges.

        Args:
            obs: Observation to check

        Returns:
            List of flag strings for out-of-range values
        """
        flags = []

        # Cost of debt (nominal)
        if obs.kd_nominal is not None:
            min_kd, max_kd = thresholds.KD_NOMINAL_RANGE
            if not (min_kd <= obs.kd_nominal <= max_kd):
                flags.append(
                    f"WARNING: kd_nominal={obs.kd_nominal:.2f}% outside range "
                    f"[{min_kd}%, {max_kd}%]"
                )

        # Cost of equity (nominal)
        if obs.ke_nominal is not None:
            min_ke, max_ke = thresholds.KE_NOMINAL_RANGE
            if not (min_ke <= obs.ke_nominal <= max_ke):
                flags.append(
                    f"WARNING: ke_nominal={obs.ke_nominal:.2f}% outside range "
                    f"[{min_ke}%, {max_ke}%]"
                )

        # WACC (nominal)
        if obs.wacc_nominal is not None:
            min_wacc, max_wacc = thresholds.WACC_NOMINAL_RANGE
            if not (min_wacc <= obs.wacc_nominal <= max_wacc):
                flags.append(
                    f"WARNING: wacc_nominal={obs.wacc_nominal:.2f}% outside range "
                    f"[{min_wacc}%, {max_wacc}%]"
                )

        # Leverage ratio
        if obs.leverage_debt_pct is not None:
            min_lev, max_lev = thresholds.LEVERAGE_NOMINAL_RANGE
            if not (min_lev <= obs.leverage_debt_pct <= max_lev):
                flags.append(
                    f"WARNING: leverage_debt_pct={obs.leverage_debt_pct:.2f}% outside range "
                    f"[{min_lev}%, {max_lev}%]"
                )

        # Debt tenor
        if obs.debt_tenor_years is not None:
            min_tenor, max_tenor = thresholds.DEBT_TENOR_RANGE
            if not (min_tenor <= obs.debt_tenor_years <= max_tenor):
                flags.append(
                    f"WARNING: debt_tenor_years={obs.debt_tenor_years:.1f} outside range "
                    f"[{min_tenor}, {max_tenor}] years"
                )

        # Credit spread
        if obs.kd_spread_bps is not None:
            min_spread, max_spread = thresholds.SPREAD_BPS_RANGE
            if not (min_spread <= obs.kd_spread_bps <= max_spread):
                flags.append(
                    f"WARNING: kd_spread_bps={obs.kd_spread_bps:.0f} outside range "
                    f"[{min_spread}, {max_spread}] bps"
                )

        # Cost of equity (real)
        if obs.ke_real is not None:
            if obs.ke_nominal is not None and obs.ke_real > obs.ke_nominal:
                flags.append(
                    f"WARNING: ke_real={obs.ke_real:.2f}% > ke_nominal={obs.ke_nominal:.2f}% "
                    "(impossible, real should be <= nominal)"
                )

        # Cost of debt (real)
        if obs.kd_real is not None:
            if obs.kd_nominal is not None and obs.kd_real > obs.kd_nominal:
                flags.append(
                    f"WARNING: kd_real={obs.kd_real:.2f}% > kd_nominal={obs.kd_nominal:.2f}% "
                    "(impossible, real should be <= nominal)"
                )

        return flags

    def check_internal_consistency(self, obs: Observation) -> List[str]:
        """
        Check cross-field consistency and relationships.

        Args:
            obs: Observation to check

        Returns:
            List of flag strings for inconsistencies
        """
        flags = []

        # WACC reconciliation: WACC ≈ Ke*(E/V) + Kd*(1-t)*(D/V)
        if (obs.wacc_nominal is not None and
            obs.ke_nominal is not None and
            obs.kd_nominal is not None and
            obs.leverage_debt_pct is not None):

            tax_rate = obs.tax_rate_applied if obs.tax_rate_applied is not None else 0.0
            d_ratio = obs.leverage_debt_pct / 100.0
            e_ratio = 1.0 - d_ratio

            wacc_calculated = (e_ratio * obs.ke_nominal +
                              d_ratio * obs.kd_nominal * (1 - tax_rate))

            if not thresholds.wacc_reconciliation_passes(wacc_calculated, obs.wacc_nominal):
                flags.append(
                    f"WARNING: WACC reconciliation failed. "
                    f"Calculated={wacc_calculated:.2f}%, Observed={obs.wacc_nominal:.2f}%, "
                    f"Difference={abs(wacc_calculated - obs.wacc_nominal):.2f}% "
                    f"(tolerance={thresholds.WACC_CONSISTENCY_TOLERANCE}%)"
                )

        # Leverage percentages sum to ~100%
        if (obs.leverage_debt_pct is not None and obs.leverage_equity_pct is not None):
            total = obs.leverage_debt_pct + obs.leverage_equity_pct
            if not (95 <= total <= 105):  # 5% tolerance
                flags.append(
                    f"WARNING: Leverage percentages don't sum to 100%. "
                    f"Debt={obs.leverage_debt_pct:.1f}% + Equity={obs.leverage_equity_pct:.1f}% "
                    f"= {total:.1f}%"
                )

        # Ke > Kd (cost of equity should exceed cost of debt)
        if obs.ke_nominal is not None and obs.kd_nominal is not None:
            if obs.kd_nominal > obs.ke_nominal:
                flags.append(
                    f"WARNING: kd_nominal={obs.kd_nominal:.2f}% > ke_nominal={obs.ke_nominal:.2f}% "
                    "(equity should cost more than debt)"
                )

        # WACC should be between Kd and Ke
        if obs.wacc_nominal is not None:
            if obs.kd_nominal is not None and obs.wacc_nominal < obs.kd_nominal:
                flags.append(
                    f"WARNING: WACC={obs.wacc_nominal:.2f}% < Kd={obs.kd_nominal:.2f}% "
                    "(WACC should be >= cost of debt)"
                )
            if obs.ke_nominal is not None and obs.wacc_nominal > obs.ke_nominal:
                flags.append(
                    f"WARNING: WACC={obs.wacc_nominal:.2f}% > Ke={obs.ke_nominal:.2f}% "
                    "(WACC should be <= cost of equity)"
                )

        # Kd spread + benchmark should approximately equal Kd nominal
        # (only check if all three are present and benchmark is reasonably stated)
        if (obs.kd_spread_bps is not None and obs.kd_nominal is not None and
            obs.kd_benchmark is not None):
            # Try to extract benchmark rate if it's in the format "SOFR+X bps" or similar
            # For now, just flag if spread seems inconsistent
            if obs.kd_spread_bps > 2000 and obs.kd_nominal < 15:
                flags.append(
                    f"WARNING: High spread ({obs.kd_spread_bps:.0f} bps) but low kd_nominal "
                    f"({obs.kd_nominal:.2f}%), check consistency with benchmark"
                )

        return flags

    def check_format_and_types(self, obs: Observation) -> List[str]:
        """
        Check data format, types, and controlled vocabulary compliance.

        Args:
            obs: Observation to check

        Returns:
            List of flag strings for format issues
        """
        flags = []

        # Country code must be valid ISO 3166-1 alpha-3
        if obs.country and obs.country not in self.VALID_ISO_COUNTRIES:
            flags.append(
                f"ERROR: Country code '{obs.country}' not recognized ISO 3166-1 alpha-3. "
                f"Must be 3-letter uppercase code (e.g., 'USA', 'GBR')"
            )

        # Technology L2 - should not be empty or placeholder
        if not obs.technology_l2 or obs.technology_l2.strip() == "":
            flags.append("ERROR: technology_l2 is empty or missing")
        elif obs.technology_l2.lower() in ['n/a', 'unknown', 'see note', 'tbd']:
            flags.append(
                f"WARNING: technology_l2='{obs.technology_l2}' appears to be placeholder text"
            )

        # Scale must be valid enum value
        if obs.scale is not None:
            if isinstance(obs.scale, str):
                if obs.scale not in self.VALID_SCALES:
                    flags.append(
                        f"ERROR: scale='{obs.scale}' not in valid values: {self.VALID_SCALES}"
                    )
            # If it's already an enum, Pydantic should have validated it

        # Value chain position must be valid enum value
        if obs.value_chain_position is not None:
            if isinstance(obs.value_chain_position, str):
                if obs.value_chain_position not in self.VALID_VALUE_CHAIN_POSITIONS:
                    flags.append(
                        f"ERROR: value_chain_position='{obs.value_chain_position}' not valid"
                    )

        # Project status must be valid enum value
        if obs.project_status is not None:
            if isinstance(obs.project_status, str):
                if obs.project_status not in self.VALID_PROJECT_STATUSES:
                    flags.append(
                        f"ERROR: project_status='{obs.project_status}' not valid"
                    )

        # Currency code must be valid ISO 4217
        if obs.debt_currency is not None:
            if obs.debt_currency not in self.VALID_ISO_CURRENCIES:
                flags.append(
                    f"WARNING: debt_currency='{obs.debt_currency}' not recognized ISO 4217 code"
                )

        # Dates must be valid and not in future
        today = date.today()
        if obs.source_document_date and obs.source_document_date > today:
            flags.append(
                f"ERROR: source_document_date={obs.source_document_date} is in the future"
            )
        if obs.extraction_date and obs.extraction_date > today:
            flags.append(
                f"ERROR: extraction_date={obs.extraction_date} is in the future"
            )
        if obs.human_review_date and obs.human_review_date > today:
            flags.append(
                f"ERROR: human_review_date={obs.human_review_date} is in the future"
            )

        # Year of observation must be reasonable
        if obs.year_of_observation > today.year + 1:
            flags.append(
                f"WARNING: year_of_observation={obs.year_of_observation} is in future"
            )
        if obs.year_of_observation < 1990:
            flags.append(
                f"WARNING: year_of_observation={obs.year_of_observation} is before 1990"
            )

        # Numeric fields should not contain non-numeric strings like "see note 12"
        # (This is harder to check post-Pydantic validation, but we can check source_quote)
        if obs.source_quote and ("see note" in obs.source_quote.lower() or
                                   "note " in obs.source_quote.lower()):
            flags.append(
                f"WARNING: source_quote appears to reference footnote/note text: "
                f"'{obs.source_quote[:50]}...'"
            )

        return flags

    def check_traceability_completeness(self, obs: Observation) -> List[str]:
        """
        Check that the observation has sufficient provenance information
        for full traceability back to the original source document.

        Every observation MUST have:
        - source_document_url: Where the document was obtained
        - source_page_number: Which page contains the data
        - source_quote: Verbatim text supporting the extracted values

        Observations missing any of these are flagged for human review.

        Args:
            obs: Observation to check

        Returns:
            List of flag strings for traceability gaps
        """
        flags = []

        # Check source document URL
        if not obs.source_document_url:
            flags.append(
                "WARNING: TRACEABILITY — source_document_url is missing. "
                "Every observation must link to the original document URL."
            )

        # Check source page number
        if obs.source_page_number is None:
            flags.append(
                "WARNING: TRACEABILITY — source_page_number is missing. "
                "Every observation must reference the page where data was found."
            )

        # Check source quote
        if not obs.source_quote:
            flags.append(
                "WARNING: TRACEABILITY — source_quote is missing. "
                "Every observation must include a verbatim quote from the source."
            )
        elif len(obs.source_quote.strip()) < 10:
            flags.append(
                "WARNING: TRACEABILITY — source_quote is suspiciously short "
                f"({len(obs.source_quote.strip())} chars). "
                "Quote should contain the relevant passage supporting the data."
            )
        elif len(obs.source_quote) > 2000:
            flags.append(
                "WARNING: TRACEABILITY — source_quote exceeds 2000 chars. "
                "Quote should be a focused passage, not an entire page of text."
            )

        # Check source_document_id (links to RawDocument)
        if not obs.source_document_id:
            flags.append(
                "WARNING: TRACEABILITY — source_document_id is missing. "
                "Observation should reference the RawDocument for audit trail."
            )

        # Check provenance chain if present
        if obs.provenance:
            if not obs.provenance.source_quotes:
                flags.append(
                    "WARNING: TRACEABILITY — provenance chain has no source_quotes."
                )
            if not obs.provenance.source_page_numbers:
                flags.append(
                    "WARNING: TRACEABILITY — provenance chain has no page numbers."
                )
        else:
            flags.append(
                "WARNING: TRACEABILITY — no ProvenanceChain attached. "
                "Full provenance chain recommended for audit completeness."
            )

        # Compute and report traceability level
        if obs.traceability_level == TraceabilityLevel.MINIMAL:
            flags.append(
                "ERROR: TRACEABILITY — observation has MINIMAL traceability. "
                "Cannot verify data origin. Requires human review."
            )
        elif obs.traceability_level == TraceabilityLevel.PARTIAL:
            flags.append(
                "WARNING: TRACEABILITY — observation has PARTIAL traceability. "
                "Some provenance fields missing."
            )

        return flags

    def check_duplicates(
        self,
        obs: Observation,
        existing_observations: Optional[list] = None
    ) -> List[str]:
        """
        Detect near-identical or duplicate observations.

        Args:
            obs: Observation to check
            existing_observations: List of existing Observation objects to compare against

        Returns:
            List of flag strings for suspected duplicates
        """
        flags = []

        if not existing_observations:
            return flags

        # Define what constitutes a "near-identical" observation
        # Same: project, source_type, year, and values within tolerance
        for existing in existing_observations:
            if existing.observation_id == obs.observation_id:
                continue  # Skip self-comparison

            # Check project name and basic attributes match
            project_match = (
                obs.project_or_entity_name == existing.project_or_entity_name and
                obs.country == existing.country and
                obs.year_of_observation == existing.year_of_observation and
                obs.source_type == existing.source_type
            )

            if not project_match:
                continue

            # If projects match, check if financial parameters are similar
            params_to_check = [
                ('kd_nominal', 0.5),      # Within ±0.5 percentage points
                ('ke_nominal', 1.0),      # Within ±1.0 percentage points
                ('wacc_nominal', 0.5),    # Within ±0.5 percentage points
                ('leverage_debt_pct', 5), # Within ±5 percentage points
            ]

            similar_params = 0
            for param, tolerance in params_to_check:
                obs_val = getattr(obs, param)
                existing_val = getattr(existing, param)

                if obs_val is not None and existing_val is not None:
                    if abs(obs_val - existing_val) <= tolerance:
                        similar_params += 1

            # Flag if 2+ parameters are suspiciously similar
            if similar_params >= 2:
                flags.append(
                    f"WARNING: Potential duplicate found. Observation {existing.observation_id} "
                    f"has same project, country, year, source_type, and {similar_params} "
                    f"similar financial parameters"
                )

        return flags

    # Approximate sovereign yields by country (for concessional detection)
    # Source: Bloomberg/FRED approximate 10Y government bond yields as of 2025
    _RISK_FREE_RATES: Dict[str, float] = {
        'USA': 4.3, 'GBR': 4.5, 'DEU': 2.5, 'FRA': 3.0, 'JPN': 1.0,
        'AUS': 4.3, 'CAN': 3.5, 'BRA': 12.0, 'IND': 7.2, 'ZAF': 10.5,
        'MEX': 9.5, 'COL': 10.0, 'PER': 6.5, 'CHL': 5.5, 'IDN': 7.0,
        'PHL': 6.5, 'VNM': 5.0, 'KEN': 14.0, 'NGA': 15.0, 'EGY': 25.0,
        'CHN': 2.3, 'KOR': 3.5, 'THA': 2.8, 'MYS': 3.8, 'SGP': 3.0,
    }

    def _get_risk_free_rate(self, country: str) -> Optional[float]:
        """Get approximate risk-free rate for a country."""
        return self._RISK_FREE_RATES.get(country)

    def check_concessional(self, obs: Observation) -> List[str]:
        """
        Check if debt appears to be concessional (below-market rates from DFIs).

        If kd_nominal is below the sovereign yield for the country AND the source
        is a DFI disclosure, flag as likely concessional.

        Args:
            obs: Observation to check

        Returns:
            List of INFO flags suggesting concessional finance detection
        """
        flags = []
        if obs.kd_nominal is not None and obs.source_type == SourceType.DFI_DISCLOSURE:
            rfr = self._get_risk_free_rate(obs.country)
            if rfr is not None and obs.kd_nominal < rfr:
                flags.append(
                    f"INFO: Concessional finance likely. "
                    f"kd_nominal={obs.kd_nominal:.2f}% is below risk-free rate "
                    f"~{rfr:.2f}% for {obs.country}. "
                    f"Consider setting is_concessional=True."
                )
        return flags

    def _compute_score_from_flags(self, num_flags: int) -> float:
        """
        Compute a QC score (0.0-1.0) based on number of rule-based flags.

        Args:
            num_flags: Number of flags found

        Returns:
            Score between 0.0 and 1.0
        """
        # Start at 1.0, deduct 0.15 per flag, floor at 0.0
        score = 1.0 - (num_flags * 0.15)
        return max(0.0, score)

    def _format_details(self, flags: List[str]) -> str:
        """Format flags into a detailed string for the QC result."""
        if not flags:
            return "All rule-based checks passed."
        return "Rule-based QC Flags:\n" + "\n".join(f"  - {f}" for f in flags)

    def _recommend_action(self, status: QCStatus) -> str:
        """Recommend an action based on QC status."""
        if status == QCStatus.PASSED:
            return "approve"
        elif status == QCStatus.FLAGGED:
            return "review"
        else:
            return "reject"
