"""
QC Agent orchestrator for the OEFO data pipeline.

This module coordinates the three-layer QC process:
1. Layer 1 (Rules): Deterministic rule checks
2. Layer 2 (Benchmarks): Statistical peer comparison
3. Layer 3 (LLM): Cross-validation and verification

Combines results into a final QC score and routing decision.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import pandas as pd

from oefo.models import Observation, QCResult, QCStatus
from oefo.config import thresholds
from oefo.qc.rules import RuleBasedQC
from oefo.qc.benchmarks import StatisticalQC
from oefo.qc.llm_review import LLMReviewQC

logger = logging.getLogger(__name__)


class RoutingDecision(str, Enum):
    """Routing decision enum."""
    AUTO_ACCEPT = "auto_accept"
    FLAG_FOR_REVIEW = "flag_for_review"
    REJECT = "reject"


@dataclass
class QCScoreBreakdown:
    """Detailed breakdown of QC score computation."""
    rule_score: float
    stat_score: float
    llm_score: float
    final_score: float
    rule_flags_count: int
    stat_flags_count: int
    llm_flags_count: int


class QCAgent:
    """
    Orchestrates the three-layer QC process for OEFO observations.

    Coordinates rule-based, statistical, and LLM-based quality checks,
    combines scores, and routes to appropriate workflow (auto-accept, review, reject).
    """

    def __init__(
        self,
        enable_rules: bool = True,
        enable_stats: bool = True,
        enable_llm: bool = True,
        llm_model: str = "claude-opus-4-6"
    ):
        """
        Initialize the QC Agent.

        Args:
            enable_rules: Enable Layer 1 rule-based checks
            enable_stats: Enable Layer 2 statistical checks
            enable_llm: Enable Layer 3 LLM verification
            llm_model: Claude model to use for LLM checks
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        self.enable_rules = enable_rules
        self.enable_stats = enable_stats
        self.enable_llm = enable_llm

        # Initialize QC modules
        self.rule_qc = RuleBasedQC() if enable_rules else None
        self.stat_qc = StatisticalQC() if enable_stats else None
        self.llm_qc = LLMReviewQC(model=llm_model) if enable_llm else None

    def run(
        self,
        observation: Observation,
        existing_observations: Optional[List[Observation]] = None,
        source_text: Optional[str] = None,
        benchmark_data: Optional[pd.DataFrame] = None
    ) -> Tuple[QCResult, RoutingDecision, QCScoreBreakdown]:
        """
        Run the full three-layer QC process on an observation.

        Args:
            observation: The observation to validate
            existing_observations: Historical observations for peer comparison
            source_text: Source document text for LLM verification
            benchmark_data: Optional benchmark data for statistical checks

        Returns:
            Tuple of:
            - Combined QCResult with final score and routing
            - RoutingDecision (auto_accept, flag_for_review, reject)
            - QCScoreBreakdown with detailed scoring information
        """
        self.logger.info(
            f"Starting QC Agent run for observation {observation.observation_id}"
        )

        score_breakdown = QCScoreBreakdown(
            rule_score=1.0,
            stat_score=1.0,
            llm_score=1.0,
            final_score=1.0,
            rule_flags_count=0,
            stat_flags_count=0,
            llm_flags_count=0
        )

        all_flags = []
        all_errors = []
        all_warnings = []

        # Layer 1: Rule-based checks
        if self.enable_rules:
            self.logger.info("Running Layer 1: Rule-based checks")
            rule_result = self.rule_qc.check(observation)
            score_breakdown.rule_score = rule_result.qc_score / 100.0
            score_breakdown.rule_flags_count = len(rule_result.qc_flags)
            all_flags.extend(rule_result.qc_flags)
            all_errors.extend(rule_result.validation_errors)
            all_warnings.extend(rule_result.validation_warnings)
            self.logger.debug(
                f"Layer 1 score: {score_breakdown.rule_score:.2f}, "
                f"flags: {score_breakdown.rule_flags_count}"
            )

        # Layer 2: Statistical checks
        if self.enable_stats:
            self.logger.info("Running Layer 2: Statistical checks")
            stat_result = self.stat_qc.check(
                observation,
                existing_observations=existing_observations,
                benchmark_data=benchmark_data
            )
            score_breakdown.stat_score = stat_result.qc_score / 100.0
            score_breakdown.stat_flags_count = len(stat_result.qc_flags)
            all_flags.extend(stat_result.qc_flags)
            all_errors.extend(stat_result.validation_errors)
            all_warnings.extend(stat_result.validation_warnings)
            self.logger.debug(
                f"Layer 2 score: {score_breakdown.stat_score:.2f}, "
                f"flags: {score_breakdown.stat_flags_count}"
            )

        # Layer 3: LLM verification
        if self.enable_llm and source_text:
            self.logger.info("Running Layer 3: LLM verification")
            llm_result = self.llm_qc.check(observation, source_text=source_text)
            score_breakdown.llm_score = llm_result.qc_score / 100.0
            score_breakdown.llm_flags_count = len(llm_result.qc_flags)
            all_flags.extend(llm_result.qc_flags)
            all_errors.extend(llm_result.validation_errors)
            all_warnings.extend(llm_result.validation_warnings)
            self.logger.debug(
                f"Layer 3 score: {score_breakdown.llm_score:.2f}, "
                f"flags: {score_breakdown.llm_flags_count}"
            )

        # Layer 1 duplicate detection (separate check)
        if self.enable_rules and existing_observations:
            self.logger.info("Running duplicate detection")
            dup_flags = self.rule_qc.check_duplicates(observation, existing_observations)
            all_flags.extend(dup_flags)
            score_breakdown.rule_flags_count += len(dup_flags)
            self.logger.debug(f"Duplicate flags: {len(dup_flags)}")

        # Compute final score
        final_score = self.compute_score(
            score_breakdown.rule_score,
            score_breakdown.stat_score,
            score_breakdown.llm_score
        )
        score_breakdown.final_score = final_score

        # Route based on score
        routing = self.route(final_score)

        # Determine final QC status
        if routing == RoutingDecision.AUTO_ACCEPT:
            qc_status = QCStatus.PASSED
        elif routing == RoutingDecision.FLAG_FOR_REVIEW:
            qc_status = QCStatus.FLAGGED
        else:
            qc_status = QCStatus.FAILED

        # Create combined QC result
        combined_result = QCResult(
            qc_id=f"qc_final_{observation.observation_id}_{datetime.now().isoformat()}",
            observation_id=observation.observation_id,
            qc_timestamp=datetime.now(),
            qc_agent="QCAgent",
            qc_status=qc_status,
            qc_score=final_score * 100,  # Convert to 0-100 scale
            qc_flags=list(dict.fromkeys(all_flags)),  # Deduplicate while preserving order
            validation_errors=list(dict.fromkeys(all_errors)),
            validation_warnings=list(dict.fromkeys(all_warnings)),
            summary=self._create_summary(
                score_breakdown, routing, len(all_flags)
            ),
            details=self._create_detailed_report(
                score_breakdown, all_flags, all_errors, all_warnings
            ),
            recommended_action=routing.value
        )

        self.logger.info(
            f"QC Agent complete: final_score={final_score:.2f}, "
            f"routing={routing.value}, total_flags={len(all_flags)}"
        )

        return combined_result, routing, score_breakdown

    def compute_score(
        self,
        rule_score: float,
        stat_score: float,
        llm_score: float
    ) -> float:
        """
        Compute final QC score from component layer scores.

        Uses a weighted average approach, with each layer contributing equally
        if enabled. Handles disabled layers gracefully.

        Args:
            rule_score: Layer 1 (rule-based) score (0.0-1.0)
            stat_score: Layer 2 (statistical) score (0.0-1.0)
            llm_score: Layer 3 (LLM) score (0.0-1.0)

        Returns:
            Final score (0.0-1.0)
        """
        layers = []

        if self.enable_rules:
            layers.append(rule_score)
        if self.enable_stats:
            layers.append(stat_score)
        if self.enable_llm:
            layers.append(llm_score)

        if not layers:
            self.logger.warning("No QC layers enabled, defaulting to score=0.5")
            return 0.5

        # Simple average of enabled layers
        return sum(layers) / len(layers)

    def route(self, score: float) -> RoutingDecision:
        """
        Route observation based on QC score.

        Routing logic:
        - >0.85: auto_accept (confidence high, proceed without review)
        - 0.50-0.85: flag_for_review (requires human judgment)
        - <0.50: reject (quality too low)

        Args:
            score: QC score (0.0-1.0)

        Returns:
            RoutingDecision enum value
        """
        if thresholds.should_auto_accept(score):
            return RoutingDecision.AUTO_ACCEPT
        elif thresholds.should_review(score):
            return RoutingDecision.FLAG_FOR_REVIEW
        else:
            return RoutingDecision.REJECT

    def process_batch(
        self,
        observations: List[Observation],
        existing_observations: Optional[List[Observation]] = None,
        source_texts: Optional[Dict[str, str]] = None,
        benchmark_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Process a batch of observations through the QC pipeline.

        Args:
            observations: List of observations to validate
            existing_observations: Historical observations for peer comparison
            source_texts: Dict mapping observation_id -> source_text
            benchmark_data: Optional benchmark data for statistical checks

        Returns:
            Dict with keys:
            - auto_accepted: List of QCResult for accepted observations
            - flagged_for_review: List of QCResult for review
            - rejected: List of QCResult for rejected observations
            - summary: Dict with counts and aggregate statistics
        """
        self.logger.info(f"Processing batch of {len(observations)} observations")

        auto_accepted = []
        flagged = []
        rejected = []

        for i, obs in enumerate(observations):
            self.logger.debug(
                f"Processing {i+1}/{len(observations)}: {obs.observation_id}"
            )

            source_text = None
            if source_texts:
                source_text = source_texts.get(obs.observation_id)

            qc_result, routing, _ = self.run(
                observation=obs,
                existing_observations=existing_observations,
                source_text=source_text,
                benchmark_data=benchmark_data
            )

            if routing == RoutingDecision.AUTO_ACCEPT:
                auto_accepted.append(qc_result)
            elif routing == RoutingDecision.FLAG_FOR_REVIEW:
                flagged.append(qc_result)
            else:
                rejected.append(qc_result)

        # Create summary
        summary = {
            "total_processed": len(observations),
            "auto_accepted_count": len(auto_accepted),
            "flagged_count": len(flagged),
            "rejected_count": len(rejected),
            "auto_accept_rate": len(auto_accepted) / len(observations) if observations else 0,
            "avg_score_auto_accepted": (
                sum(r.qc_score for r in auto_accepted) / len(auto_accepted)
                if auto_accepted else 0
            ),
            "avg_score_flagged": (
                sum(r.qc_score for r in flagged) / len(flagged)
                if flagged else 0
            ),
            "avg_score_rejected": (
                sum(r.qc_score for r in rejected) / len(rejected)
                if rejected else 0
            ),
            "total_flags": sum(
                len(r.qc_flags) for r in auto_accepted + flagged + rejected
            ),
        }

        self.logger.info(
            f"Batch processing complete: {len(auto_accepted)} accepted, "
            f"{len(flagged)} flagged, {len(rejected)} rejected"
        )

        return {
            "auto_accepted": auto_accepted,
            "flagged_for_review": flagged,
            "rejected": rejected,
            "summary": summary
        }

    def _create_summary(
        self,
        score_breakdown: QCScoreBreakdown,
        routing: RoutingDecision,
        total_flags: int
    ) -> str:
        """Create a concise summary of QC results."""
        return (
            f"QC Score: {score_breakdown.final_score*100:.1f} "
            f"(Rules: {score_breakdown.rule_score*100:.0f}, "
            f"Stats: {score_breakdown.stat_score*100:.0f}, "
            f"LLM: {score_breakdown.llm_score*100:.0f}) | "
            f"Routing: {routing.value} | "
            f"Flags: {total_flags}"
        )

    def _create_detailed_report(
        self,
        score_breakdown: QCScoreBreakdown,
        all_flags: List[str],
        all_errors: List[str],
        all_warnings: List[str]
    ) -> str:
        """Create a detailed QC report."""
        report = f"""
QC AGENT DETAILED REPORT
========================

SCORE BREAKDOWN:
  Layer 1 (Rules):         {score_breakdown.rule_score*100:6.1f}% ({score_breakdown.rule_flags_count} flags)
  Layer 2 (Statistics):    {score_breakdown.stat_score*100:6.1f}% ({score_breakdown.stat_flags_count} flags)
  Layer 3 (LLM):           {score_breakdown.llm_score*100:6.1f}% ({score_breakdown.llm_flags_count} flags)
  ─────────────────────────────────
  FINAL SCORE:             {score_breakdown.final_score*100:6.1f}%

ISSUES ({len(all_flags)} total):
"""

        if all_errors:
            report += f"\nERRORS ({len(all_errors)}):\n"
            for error in all_errors[:10]:  # Show first 10
                report += f"  • {error}\n"
            if len(all_errors) > 10:
                report += f"  ... and {len(all_errors) - 10} more\n"

        if all_warnings:
            report += f"\nWARNINGS ({len(all_warnings)}):\n"
            for warning in all_warnings[:10]:  # Show first 10
                report += f"  • {warning}\n"
            if len(all_warnings) > 10:
                report += f"  ... and {len(all_warnings) - 10} more\n"

        if not all_flags:
            report += "  ✓ No issues found\n"

        return report
