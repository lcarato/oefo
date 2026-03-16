"""
Pipeline health scoring — OEFO's equivalent of val_bpb.

Provides a single composite number (0.0–1.0) that summarises how well
the pipeline performed in a given run, both per-source and overall.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SourceHealthScore:
    """Health metrics for a single data source within a pipeline run."""

    source_name: str

    # Discovery → Download → Extraction → QC funnel
    discovery_count: int = 0
    download_count: int = 0
    download_failure_count: int = 0
    extraction_count: int = 0
    qc_pass_count: int = 0
    qc_flag_count: int = 0
    qc_reject_count: int = 0
    mean_qc_score: float = 0.0

    # Error classification (exception class name → count)
    error_types: dict[str, int] = field(default_factory=dict)

    # Timing
    duration_seconds: float = 0.0

    # Decision: KEEP / DISCARD / CRASH (set by pipeline agent)
    decision: str = "PENDING"
    decision_reason: str = ""

    # ── Derived metrics ────────────────────────────────────────────────

    @property
    def download_success_rate(self) -> float:
        """Fraction of discovered documents successfully downloaded."""
        total = self.download_count + self.download_failure_count
        return self.download_count / max(total, 1)

    @property
    def yield_rate(self) -> float:
        """End-to-end yield: QC-passed observations / documents discovered."""
        return self.qc_pass_count / max(self.discovery_count, 1)

    @property
    def crash_free(self) -> bool:
        """True if no unrecoverable errors occurred."""
        permanent_errors = sum(
            v for k, v in self.error_types.items()
            if "Permanent" in k or "ContentChanged" in k
        )
        return permanent_errors == 0

    @property
    def health_score(self) -> float:
        """
        Composite 0.0–1.0 health score.

        Weights:
          40%  yield rate (end-to-end effectiveness)
          30%  download success rate
          20%  mean QC score
          10%  crash-free bonus
        """
        score = (
            0.40 * min(self.yield_rate, 1.0)
            + 0.30 * self.download_success_rate
            + 0.20 * self.mean_qc_score
            + 0.10 * (1.0 if self.crash_free else 0.0)
        )
        return round(min(max(score, 0.0), 1.0), 4)

    def record_error(self, error: BaseException) -> None:
        """Increment the error counter for this exception type."""
        key = type(error).__name__
        self.error_types[key] = self.error_types.get(key, 0) + 1

    def to_dict(self) -> dict:
        """Serialise to a plain dict for JSON / ledger storage."""
        return {
            "source": self.source_name,
            "discovery": self.discovery_count,
            "downloaded": self.download_count,
            "download_failed": self.download_failure_count,
            "extracted": self.extraction_count,
            "qc_pass": self.qc_pass_count,
            "qc_flag": self.qc_flag_count,
            "qc_reject": self.qc_reject_count,
            "mean_qc": round(self.mean_qc_score, 4),
            "health": self.health_score,
            "decision": self.decision,
            "errors": dict(self.error_types),
            "duration_s": round(self.duration_seconds, 1),
        }


@dataclass
class PipelineHealthScore:
    """Aggregate health score across all sources for a full pipeline run."""

    source_scores: list[SourceHealthScore] = field(default_factory=list)
    run_id: str = ""
    git_commit: str = ""
    duration_seconds: float = 0.0

    # ── Aggregate properties ───────────────────────────────────────────

    @property
    def total_discovered(self) -> int:
        return sum(s.discovery_count for s in self.source_scores)

    @property
    def total_downloaded(self) -> int:
        return sum(s.download_count for s in self.source_scores)

    @property
    def total_extracted(self) -> int:
        return sum(s.extraction_count for s in self.source_scores)

    @property
    def total_qc_passed(self) -> int:
        return sum(s.qc_pass_count for s in self.source_scores)

    @property
    def sources_ok(self) -> int:
        return sum(1 for s in self.source_scores if s.decision == "KEEP")

    @property
    def sources_failed(self) -> int:
        return sum(1 for s in self.source_scores if s.decision == "CRASH")

    @property
    def health_score(self) -> float:
        """
        Overall pipeline health: weighted mean of source scores.

        Sources that discovered more documents contribute proportionally more.
        If no sources ran, returns 0.0.
        """
        if not self.source_scores:
            return 0.0
        total_disc = sum(s.discovery_count for s in self.source_scores)
        if total_disc == 0:
            # Fall back to simple average
            return round(
                sum(s.health_score for s in self.source_scores)
                / len(self.source_scores),
                4,
            )
        weighted = sum(
            s.health_score * s.discovery_count for s in self.source_scores
        )
        return round(weighted / total_disc, 4)

    # ── Display helpers ────────────────────────────────────────────────

    def summary_line(self) -> str:
        """One-line summary suitable for printing at the end of a run."""
        return (
            f"Pipeline health: {self.health_score:.2f}  |  "
            f"Sources: {self.sources_ok} OK / {self.sources_failed} CRASH / "
            f"{len(self.source_scores)} total  |  "
            f"Docs: {self.total_discovered} discovered → "
            f"{self.total_downloaded} downloaded → "
            f"{self.total_qc_passed} QC-passed  |  "
            f"{self.duration_seconds:.0f}s"
        )

    def detail_table(self) -> str:
        """Multi-line table of per-source results."""
        lines = [
            f"{'Source':<10} {'Health':>7} {'Decision':<9} "
            f"{'Disc':>5} {'DL':>5} {'Extr':>5} {'QC✓':>5} {'Time':>6}",
            "-" * 65,
        ]
        for s in sorted(self.source_scores, key=lambda x: -x.health_score):
            lines.append(
                f"{s.source_name:<10} {s.health_score:>7.2f} {s.decision:<9} "
                f"{s.discovery_count:>5} {s.download_count:>5} "
                f"{s.extraction_count:>5} {s.qc_pass_count:>5} "
                f"{s.duration_seconds:>5.0f}s"
            )
        lines.append("-" * 65)
        lines.append(self.summary_line())
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialise for the run ledger."""
        return {
            "run_id": self.run_id,
            "git_commit": self.git_commit,
            "health_score": self.health_score,
            "sources_ok": self.sources_ok,
            "sources_failed": self.sources_failed,
            "total_discovered": self.total_discovered,
            "total_downloaded": self.total_downloaded,
            "total_extracted": self.total_extracted,
            "total_qc_passed": self.total_qc_passed,
            "duration_s": round(self.duration_seconds, 1),
            "sources": [s.to_dict() for s in self.source_scores],
        }
