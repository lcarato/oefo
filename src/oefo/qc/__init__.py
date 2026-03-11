"""
Quality Control (QC) Agent Module for the OEFO Data Pipeline

This package implements a three-layer quality control system for energy project
financing observations:

1. **rules.py (Layer 1)**: Rule-based deterministic checks
   - Range plausibility validation
   - Internal consistency checks (WACC reconciliation, leverage sums, etc.)
   - Format and type validation
   - Duplicate detection

2. **benchmarks.py (Layer 2)**: Statistical benchmark comparisons
   - Damodaran cost of debt benchmarks
   - Peer comparison (technology × region groups)
   - Macroeconomic consistency checks

3. **llm_review.py (Layer 3)**: LLM-powered cross-validation
   - Source quote verification
   - Cross-extraction consistency checking
   - Tier disagreement resolution

4. **agent.py**: QC Agent Orchestrator
   - Coordinates all three layers
   - Computes combined QC score
   - Routes to appropriate workflow (auto-accept, review, reject)
   - Batch processing support

USAGE EXAMPLE:

    from oefo.qc import QCAgent
    from oefo.models import Observation

    # Initialize agent with all layers enabled
    agent = QCAgent(
        enable_rules=True,
        enable_stats=True,
        enable_llm=True,
        llm_model="claude-opus-4-6"
    )

    # Run QC on a single observation
    qc_result, routing, breakdown = agent.run(
        observation=obs,
        existing_observations=historical_obs,
        source_text=document_text
    )

    # Or process a batch
    batch_results = agent.process_batch(
        observations=[obs1, obs2, obs3],
        existing_observations=historical_obs
    )

    print(f"Auto-accepted: {len(batch_results['auto_accepted'])}")
    print(f"Flagged: {len(batch_results['flagged_for_review'])}")
    print(f"Rejected: {len(batch_results['rejected'])}")

SCORING LOGIC:

Each layer computes a score (0.0-1.0):
- Layer 1: Start at 1.0, deduct 0.15 per rule violation
- Layer 2: Start at 1.0, deduct 0.10 per statistical outlier
- Layer 3: Start at 1.0, deduct 0.30 for contradictions, 0.10 for insufficient data

Final score is the simple average of enabled layers.

ROUTING DECISIONS:

- Score >= 0.85: AUTO_ACCEPT (skip human review)
- 0.50 <= Score < 0.85: FLAG_FOR_REVIEW (requires human judgment)
- Score < 0.50: REJECT (re-extract required)

CONFIGURATION:

All thresholds are imported from config.thresholds:
- KD_NOMINAL_RANGE: [0%, 30%]
- KE_NOMINAL_RANGE: [2%, 40%]
- WACC_NOMINAL_RANGE: [1%, 35%]
- LEVERAGE_NOMINAL_RANGE: [0%, 100%]
- DEBT_TENOR_RANGE: [1, 40] years
- SPREAD_BPS_RANGE: [0, 2000] basis points
- AUTO_ACCEPT_THRESHOLD: 0.85
- REVIEW_THRESHOLD: 0.50
- OUTLIER_STD_DEVIATIONS: 2.0
- WACC_CONSISTENCY_TOLERANCE: 0.5 percentage points
"""

from .rules import RuleBasedQC
from .benchmarks import StatisticalQC
from .llm_review import LLMReviewQC
from .agent import QCAgent, RoutingDecision, QCScoreBreakdown

__all__ = [
    "RuleBasedQC",
    "StatisticalQC",
    "LLMReviewQC",
    "QCAgent",
    "RoutingDecision",
    "QCScoreBreakdown",
]
