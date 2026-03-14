"""
WACC derivation utility for OEFO.

Derives Weighted Average Cost of Capital from observed components
when sufficient data exists but no WACC is directly disclosed.

Spec reference: Section 7.3 — WACC Derivation Rules.
"""
from typing import Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from oefo.models import Observation

logger = logging.getLogger(__name__)


def derive_wacc(obs: "Observation") -> tuple[Optional[float], Optional[float], str]:
    """
    Attempt to derive WACC from observed components.

    Returns:
        (wacc_nominal, wacc_real, derivation_notes)

    WACC derivation rules (from spec Section 7.3):
    - Kd (or reasonable proxy) AND capital structure must be observed
    - Ke must be either observed (regulatory) or estimable
    - Where Ke is estimated rather than observed, flag the estimation method
    - Do NOT default to theoretical WACC where empirical data is insufficient
    """
    wacc_nominal = None
    wacc_real = None
    notes = []

    # Check minimum required data
    has_kd = obs.kd_nominal is not None
    has_leverage = (obs.leverage_debt_pct is not None and obs.leverage_equity_pct is not None)
    has_ke = obs.ke_nominal is not None

    if not (has_kd and has_leverage):
        return None, None, "Insufficient data: need at minimum kd and capital structure"

    debt_ratio = obs.leverage_debt_pct / 100.0
    equity_ratio = obs.leverage_equity_pct / 100.0
    tax_rate = obs.tax_rate_applied if obs.tax_rate_applied is not None else 0.25  # default assumption

    if obs.tax_rate_applied is None:
        notes.append("Tax rate assumed at 25% (not disclosed)")

    if has_ke:
        wacc_nominal = (
            obs.ke_nominal * equity_ratio +
            obs.kd_nominal * (1 - tax_rate) * debt_ratio
        )
        notes.append(
            f"WACC derived from observed ke={obs.ke_nominal:.2f}%, "
            f"kd={obs.kd_nominal:.2f}%, D/V={obs.leverage_debt_pct:.1f}%"
        )
    else:
        notes.append("Ke not observed; WACC not derived (spec rule: missing data stays missing)")
        return None, None, "; ".join(notes)

    # Derive real WACC if real components available
    if obs.ke_real is not None and obs.kd_real is not None:
        wacc_real = (
            obs.ke_real * equity_ratio +
            obs.kd_real * (1 - tax_rate) * debt_ratio
        )
        notes.append("Real WACC derived from observed real components")

    return wacc_nominal, wacc_real, "; ".join(notes)
