"""
Layer 2: Statistical benchmark checks for the OEFO data pipeline.

This module implements statistical validation against benchmarks:
- Damodaran cost of debt benchmarks by country/rating
- Peer comparison (technology × region groups)
- Macro consistency (risk-free rate alignment, etc.)

Uses external benchmark data and statistical outlier detection (>2 std deviations).
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import statistics

import pandas as pd
import numpy as np

from oefo.models import Observation, QCResult, QCStatus
from oefo.config import thresholds

logger = logging.getLogger(__name__)


class StatisticalQC:
    """
    Statistical quality control checks using benchmarks and peer comparison.

    Validates observations against market benchmarks and peer distributions.
    Flags outliers and inconsistencies with macroeconomic parameters.
    """

    def __init__(self, benchmark_data: Optional[pd.DataFrame] = None):
        """
        Initialize the statistical QC checker.

        Args:
            benchmark_data: Optional pre-loaded Damodaran benchmark data
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.benchmark_data = benchmark_data
        if self.benchmark_data is None:
            self.benchmark_data = self.load_damodaran_benchmarks()

    def check(
        self,
        observation: Observation,
        existing_observations: Optional[List[Observation]] = None,
        benchmark_data: Optional[pd.DataFrame] = None
    ) -> QCResult:
        """
        Run all statistical checks on an observation.

        Args:
            observation: The observation to validate
            existing_observations: Historical observations for peer comparison
            benchmark_data: Optional override benchmark data

        Returns:
            QCResult with score, status, flags, and details
        """
        self.logger.info(
            f"Running statistical checks on observation {observation.observation_id}"
        )

        if benchmark_data is not None:
            self.benchmark_data = benchmark_data

        flags = []

        # Run all check methods
        flags.extend(self.check_damodaran_benchmark(observation))
        if existing_observations:
            flags.extend(self.check_peer_comparison(observation, existing_observations))
        flags.extend(self.check_macro_consistency(observation))

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
            qc_id=f"qc_stat_{observation.observation_id}_{datetime.now().isoformat()}",
            observation_id=observation.observation_id,
            qc_timestamp=datetime.now(),
            qc_agent="StatisticalQC",
            qc_status=status,
            qc_score=score * 100,  # Convert to 0-100 scale
            qc_flags=flags,
            validation_errors=[f for f in flags if "ERROR" in f],
            validation_warnings=[f for f in flags if "WARNING" in f],
            summary=f"Statistical checks completed: {len(flags)} flags found",
            details=self._format_details(flags),
            recommended_action=self._recommend_action(status)
        )

        self.logger.info(
            f"Statistical QC complete: score={score:.2f}, status={status}, "
            f"flags={len(flags)}"
        )
        return result

    def check_damodaran_benchmark(self, obs: Observation) -> List[str]:
        """
        Compare cost of debt against Damodaran cost of debt benchmarks.

        Flags cases where observed Kd differs >2 std deviations from expected
        for the country/credit rating combination.

        Args:
            obs: Observation to check

        Returns:
            List of flag strings
        """
        flags = []

        # Skip if no kd_nominal or required metadata missing
        if obs.kd_nominal is None or obs.country is None:
            return flags

        if self.benchmark_data is None or self.benchmark_data.empty:
            self.logger.warning("No benchmark data available for Damodaran check")
            return flags

        try:
            # Filter benchmark data for this country and credit rating
            country_benchmarks = self.benchmark_data[
                self.benchmark_data['country'] == obs.country
            ]

            if country_benchmarks.empty:
                self.logger.debug(f"No benchmark data for country {obs.country}")
                return flags

            # Filter by credit rating if provided
            if obs.credit_rating and obs.credit_rating != 'not_rated':
                rating_benchmarks = country_benchmarks[
                    country_benchmarks['credit_rating'] == obs.credit_rating
                ]
                if not rating_benchmarks.empty:
                    country_benchmarks = rating_benchmarks

            # Calculate mean and std dev of benchmark Kd
            benchmark_kds = country_benchmarks['kd_nominal'].dropna()
            if len(benchmark_kds) < 2:
                return flags

            mean_kd = benchmark_kds.mean()
            std_kd = benchmark_kds.std()

            # Flag if observed Kd is >2 std devs from mean
            if std_kd > 0:
                z_score = abs(obs.kd_nominal - mean_kd) / std_kd
                if z_score > thresholds.OUTLIER_STD_DEVIATIONS:
                    flags.append(
                        f"WARNING: Damodaran benchmark check. "
                        f"Observed kd_nominal={obs.kd_nominal:.2f}% is {z_score:.1f} std devs "
                        f"from benchmark mean={mean_kd:.2f}% (std={std_kd:.2f}%) "
                        f"for {obs.country} {obs.credit_rating or 'unrated'}"
                    )

        except Exception as e:
            self.logger.warning(
                f"Error in Damodaran benchmark check: {e}", exc_info=True
            )

        return flags

    def check_peer_comparison(
        self,
        obs: Observation,
        existing: List[Observation]
    ) -> List[str]:
        """
        Compare observation against peers (same technology × region).

        Flags observations with financial parameters >2 std deviations from
        the peer group median.

        Args:
            obs: Observation to check
            existing: List of existing observations to use as peer set

        Returns:
            List of flag strings
        """
        flags = []

        if not obs.technology_l2 or not obs.country:
            return flags

        # Find peers: same technology and country
        peers = [
            e for e in existing
            if (e.technology_l2 == obs.technology_l2 and
                e.country == obs.country and
                e.observation_id != obs.observation_id)
        ]

        if len(peers) < 3:
            # Need at least 3 peers for meaningful statistics
            return flags

        # Check various financial parameters against peer distributions
        parameters_to_check = [
            ('kd_nominal', 'cost of debt'),
            ('ke_nominal', 'cost of equity'),
            ('wacc_nominal', 'WACC'),
            ('leverage_debt_pct', 'leverage ratio'),
        ]

        for param_name, param_label in parameters_to_check:
            obs_value = getattr(obs, param_name)
            if obs_value is None:
                continue

            # Get peer values
            peer_values = [
                getattr(p, param_name) for p in peers
                if getattr(p, param_name) is not None
            ]

            if len(peer_values) < 2:
                continue

            # Calculate statistics
            median = statistics.median(peer_values)
            stdev = statistics.stdev(peer_values) if len(peer_values) >= 2 else 0

            if stdev > 0:
                z_score = abs(obs_value - median) / stdev
                if z_score > thresholds.OUTLIER_STD_DEVIATIONS:
                    flags.append(
                        f"WARNING: Peer comparison flagged. "
                        f"Observed {param_label}={obs_value:.2f} is {z_score:.1f} std devs "
                        f"from peer median={median:.2f} ({len(peer_values)} peers: "
                        f"{obs.technology_l2} in {obs.country})"
                    )

        return flags

    def check_macro_consistency(self, obs: Observation) -> List[str]:
        """
        Check consistency with macroeconomic parameters.

        Currently checks:
        - Cost of debt should exceed risk-free rate (unless concessional)
        - Cost of equity should exceed cost of debt
        - Inflation implied by Kd_nominal - Kd_real should be plausible

        Args:
            obs: Observation to check

        Returns:
            List of flag strings
        """
        flags = []

        # TODO: Load country risk-free rates from external source
        # For now, use fixed assumptions
        risk_free_rates = {
            'USA': 4.5,  # Current approximate rate (March 2026)
            'EUR': 3.0,
            'GBR': 4.2,
            'JPN': 1.0,
            'CHN': 2.5,
            'IND': 6.5,
        }

        # Cost of debt should exceed risk-free rate (unless concessional)
        if (obs.kd_nominal is not None and obs.country in risk_free_rates and
            obs.confidence_level != 'high'):  # Relax for high-confidence extractions

            rfr = risk_free_rates[obs.country]
            if obs.kd_nominal < rfr - 0.5:  # Allow 50bps tolerance
                flags.append(
                    f"WARNING: Macro consistency. "
                    f"Cost of debt={obs.kd_nominal:.2f}% is below estimated risk-free rate "
                    f"≈{rfr:.2f}% for {obs.country}. May indicate concessional debt."
                )

        # Cost of equity should exceed cost of debt
        # (This is also checked in rules.py, but included here for completeness)
        if obs.ke_nominal is not None and obs.kd_nominal is not None:
            if obs.kd_nominal > obs.ke_nominal:
                flags.append(
                    f"WARNING: Macro consistency. "
                    f"Cost of equity={obs.ke_nominal:.2f}% < cost of debt={obs.kd_nominal:.2f}%. "
                    f"Equity should have higher required return than debt."
                )

        # Implied inflation from Kd_nominal and Kd_real
        if obs.kd_nominal is not None and obs.kd_real is not None:
            implied_inflation = obs.kd_nominal - obs.kd_real

            # Check against typical inflation ranges for country
            # TODO: Load expected inflation by country from config
            typical_inflation_low = 1.5
            typical_inflation_high = 5.0

            if implied_inflation < typical_inflation_low or implied_inflation > typical_inflation_high:
                flags.append(
                    f"WARNING: Macro consistency. "
                    f"Implied inflation={implied_inflation:.2f}% "
                    f"(from kd_nominal - kd_real) seems implausible for {obs.country}"
                )

        return flags

    def load_damodaran_benchmarks(self) -> pd.DataFrame:
        """
        Load Damodaran cost of debt benchmarks.

        This is a placeholder that would normally load from:
        - CSV file cached locally
        - Direct Damodaran website scrape
        - Database

        Returns:
            DataFrame with columns: country, credit_rating, kd_nominal, year
        """
        # TODO: Implement actual loading from config or cache
        self.logger.warning(
            "Damodaran benchmarks not yet implemented. "
            "Benchmark checks will be skipped."
        )

        # Return empty DataFrame for now
        return pd.DataFrame(columns=['country', 'credit_rating', 'kd_nominal', 'year'])

    def _compute_score_from_flags(self, num_flags: int) -> float:
        """
        Compute a QC score (0.0-1.0) based on number of statistical flags.

        Args:
            num_flags: Number of flags found

        Returns:
            Score between 0.0 and 1.0
        """
        # Start at 1.0, deduct 0.10 per statistical flag, floor at 0.0
        # Statistical flags are less severe than rule violations
        score = 1.0 - (num_flags * 0.10)
        return max(0.0, score)

    def _format_details(self, flags: List[str]) -> str:
        """Format flags into a detailed string for the QC result."""
        if not flags:
            return "All statistical checks passed."
        return "Statistical QC Flags:\n" + "\n".join(f"  - {f}" for f in flags)

    def _recommend_action(self, status: QCStatus) -> str:
        """Recommend an action based on QC status."""
        if status == QCStatus.PASSED:
            return "approve"
        elif status == QCStatus.FLAGGED:
            return "review"
        else:
            return "reject"
