"""
QC Thresholds and Plausibility Ranges for OEFO Data Pipeline

This module defines numerical bounds, scoring thresholds, and outlier detection
parameters used across data validation, quality control, and feasibility screening.
All thresholds are expressed in consistent units (percentages, basis points, years, etc.)
and documented with their rationale and source.
"""

from typing import Tuple

# =============================================================================
# Cost of Capital Parameters - Nominal Ranges
# =============================================================================
# These ranges reflect observed distributions in institutional cost of capital
# studies (IRENA, IEA, BNEF) and represent the plausible bounds for energy projects
# across different markets and technology types.

KD_NOMINAL_RANGE: Tuple[float, float] = (0.0, 30.0)
"""
Cost of debt (Kd) range in percentage points [0%, 30%].
- Lower bound: 0% reflects zero-coupon or concessional debt.
- Upper bound: 30% reflects high-risk emerging market project debt.
- Typical: 3% - 8% for developed market senior debt, 8% - 15% for mezzanine.
"""

KE_NOMINAL_RANGE: Tuple[float, float] = (2.0, 40.0)
"""
Cost of equity (Ke) range in percentage points [2%, 40%].
- Lower bound: 2% reflects regulated utility equity in mature markets.
- Upper bound: 40% reflects frontier market venture/growth equity.
- Typical: 7% - 12% for developed market infrastructure, 12% - 25% for emerging.
"""

WACC_NOMINAL_RANGE: Tuple[float, float] = (1.0, 35.0)
"""
Weighted average cost of capital (WACC) range in percentage points [1%, 35%].
- Lower bound: 1% reflects concessional-heavy capital structures or negative real rates.
- Upper bound: 35% reflects high-risk, unlevered emerging market projects.
- Typical: 4% - 10% for developed market renewables, 8% - 18% for emerging.
"""

LEVERAGE_NOMINAL_RANGE: Tuple[float, float] = (0.0, 100.0)
"""
Leverage ratio (D/[D+E]) range in percentage points [0%, 100%].
- Lower bound: 0% represents fully equity-financed projects.
- Upper bound: 100% would be (theoretically) fully debt-financed.
- Typical: 50% - 75% for renewable energy project finance, 30% - 50% for corporates.
"""

DEBT_TENOR_RANGE: Tuple[int, int] = (1, 40)
"""
Debt tenor (maturity) range in years [1, 40].
- Lower bound: 1 year reflects short-term or working capital facilities.
- Upper bound: 40 years reflects long-dated infrastructure/project finance.
- Typical: 10 - 25 years for renewable energy PPAs, 20 - 30 for regulated utilities.
"""

SPREAD_BPS_RANGE: Tuple[int, int] = (0, 2000)
"""
Credit spread above benchmark (SOFR, EURIBOR, etc.) in basis points [0, 2000].
- Lower bound: 0 bps reflects zero-spread or risk-free rates.
- Upper bound: 2000 bps (20%) reflects distressed emerging market or unsecured debt.
- Typical: 50 - 300 bps for investment-grade corporate, 300 - 800 for project finance.
"""

# =============================================================================
# WACC Consistency and Reconciliation
# =============================================================================

WACC_CONSISTENCY_TOLERANCE: float = 0.5
"""
Tolerance (in percentage points) for reconciling WACC from component estimates
(Kd, Ke, D/E) versus disclosed/implied WACC.
E.g., if |WACC_calculated - WACC_disclosed| > 0.5%, flag for review.
"""

# =============================================================================
# Quality Control Scoring Thresholds
# =============================================================================
# Used to triage extracted data into auto-accept, review, or reject buckets.

AUTO_ACCEPT_THRESHOLD: float = 0.85
"""
QC score threshold for automatic acceptance of extracted data point.
Scores >= 0.85 are auto-accepted without human review.
Reflects high confidence in extraction accuracy, source credibility, and plausibility.
"""

REVIEW_THRESHOLD: float = 0.50
"""
QC score threshold for flagging data as requiring human review.
Scores < 0.50 are rejected outright; scores 0.50-0.85 are routed to review queue.
Below 0.50, extraction quality or plausibility is too low for inclusion.
"""

# =============================================================================
# Outlier Detection
# =============================================================================

OUTLIER_STD_DEVIATIONS: float = 2.0
"""
Number of standard deviations from the mean used to flag potential outliers.
Data points >2 sigma from the technology/market group mean are flagged for review.
Default 2.0 captures ~95% of normal variation (assumes normal distribution).
"""

# =============================================================================
# Helper Functions for Threshold Validation
# =============================================================================


def is_kd_plausible(kd: float) -> bool:
    """
    Check if a cost of debt value falls within nominal plausibility range.

    Args:
        kd: Cost of debt as a percentage (e.g., 5.5 for 5.5%)

    Returns:
        bool: True if within KD_NOMINAL_RANGE, False otherwise.
    """
    min_kd, max_kd = KD_NOMINAL_RANGE
    return min_kd <= kd <= max_kd


def is_ke_plausible(ke: float) -> bool:
    """
    Check if a cost of equity value falls within nominal plausibility range.

    Args:
        ke: Cost of equity as a percentage (e.g., 10.0 for 10%)

    Returns:
        bool: True if within KE_NOMINAL_RANGE, False otherwise.
    """
    min_ke, max_ke = KE_NOMINAL_RANGE
    return min_ke <= ke <= max_ke


def is_wacc_plausible(wacc: float) -> bool:
    """
    Check if a WACC value falls within nominal plausibility range.

    Args:
        wacc: WACC as a percentage (e.g., 8.5 for 8.5%)

    Returns:
        bool: True if within WACC_NOMINAL_RANGE, False otherwise.
    """
    min_wacc, max_wacc = WACC_NOMINAL_RANGE
    return min_wacc <= wacc <= max_wacc


def is_leverage_plausible(leverage: float) -> bool:
    """
    Check if a leverage ratio falls within nominal plausibility range.

    Args:
        leverage: Leverage ratio as a percentage (e.g., 60.0 for 60% D/D+E)

    Returns:
        bool: True if within LEVERAGE_NOMINAL_RANGE, False otherwise.
    """
    min_lev, max_lev = LEVERAGE_NOMINAL_RANGE
    return min_lev <= leverage <= max_lev


def is_tenor_plausible(tenor: int) -> bool:
    """
    Check if a debt tenor falls within nominal plausibility range.

    Args:
        tenor: Debt tenor in years

    Returns:
        bool: True if within DEBT_TENOR_RANGE, False otherwise.
    """
    min_tenor, max_tenor = DEBT_TENOR_RANGE
    return min_tenor <= tenor <= max_tenor


def is_spread_plausible(spread_bps: int) -> bool:
    """
    Check if a credit spread falls within nominal plausibility range.

    Args:
        spread_bps: Credit spread in basis points (e.g., 150 for +150 bps)

    Returns:
        bool: True if within SPREAD_BPS_RANGE, False otherwise.
    """
    min_spread, max_spread = SPREAD_BPS_RANGE
    return min_spread <= spread_bps <= max_spread


def wacc_reconciliation_passes(
    wacc_calculated: float, wacc_observed: float
) -> bool:
    """
    Check if calculated WACC (from Kd, Ke, D/E) reconciles with observed WACC
    within tolerance threshold.

    Args:
        wacc_calculated: WACC derived from component parameters (%)
        wacc_observed: WACC from disclosure or market data (%)

    Returns:
        bool: True if difference is within WACC_CONSISTENCY_TOLERANCE, False otherwise.
    """
    return abs(wacc_calculated - wacc_observed) <= WACC_CONSISTENCY_TOLERANCE


def should_auto_accept(qc_score: float) -> bool:
    """
    Determine if a data point should be auto-accepted based on QC score.

    Args:
        qc_score: QC score (0.0 - 1.0)

    Returns:
        bool: True if score >= AUTO_ACCEPT_THRESHOLD, False otherwise.
    """
    return qc_score >= AUTO_ACCEPT_THRESHOLD


def should_review(qc_score: float) -> bool:
    """
    Determine if a data point should be routed to human review.

    Args:
        qc_score: QC score (0.0 - 1.0)

    Returns:
        bool: True if REVIEW_THRESHOLD <= score < AUTO_ACCEPT_THRESHOLD, False otherwise.
    """
    return REVIEW_THRESHOLD <= qc_score < AUTO_ACCEPT_THRESHOLD


def should_reject(qc_score: float) -> bool:
    """
    Determine if a data point should be rejected.

    Args:
        qc_score: QC score (0.0 - 1.0)

    Returns:
        bool: True if score < REVIEW_THRESHOLD, False otherwise.
    """
    return qc_score < REVIEW_THRESHOLD
