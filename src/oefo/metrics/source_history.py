"""
Source performance history — feedback loops from past runs.

Reads the run ledger to determine per-source trends and make
automated decisions: skip chronically broken sources, escalate
extraction tiers, warn about degrading health.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from .ledger import RunLedger

logger = logging.getLogger(__name__)


class SourceHistory:
    """Analyse per-source trends from the run ledger."""

    def __init__(self, ledger: Optional[RunLedger] = None) -> None:
        self._ledger = ledger or RunLedger()

    def _source_rows(self, source: str, n: int = 10) -> list[dict]:
        """Extract per-source data from the last *n* run ledger rows.

        The ledger stores aggregate data; we also check for a companion
        JSON file written by the pipeline agent with per-source detail.
        """
        rows = self._ledger.read_all()
        results = []
        for row in rows[-n:]:
            # Try to read companion per-source JSON
            run_id = row.get("run_id", "")
            detail_path = Path("outputs") / run_id / "run_report.json"
            source_info = {"run_id": run_id, "status": row.get("status", "")}

            if detail_path.exists():
                try:
                    report = json.loads(detail_path.read_text())
                    # Look for source in scrape phase details
                    for phase in report.get("phases", []):
                        if phase.get("phase") == "scrape":
                            details = phase.get("details", {})
                            doc_key = f"docs_{source.lower()}"
                            if doc_key in details:
                                source_info["docs"] = details[doc_key]
                            if source.lower() in details.get("sources_failed", []):
                                source_info["source_status"] = "CRASH"
                            elif source.lower() in details.get("sources_succeeded", []):
                                source_info["source_status"] = "KEEP"
                            else:
                                source_info["source_status"] = "SKIP"
                except Exception:
                    pass

            results.append(source_info)
        return results

    def should_skip_source(self, source: str, n: int = 3) -> tuple[bool, str]:
        """Check if a source has crashed in the last *n* consecutive runs.

        Returns:
            (should_skip, reason) tuple
        """
        rows = self._source_rows(source, n=n)
        if len(rows) < n:
            return False, "Not enough history"

        recent = rows[-n:]
        crash_count = sum(
            1 for r in recent
            if r.get("source_status") == "CRASH"
        )

        if crash_count >= n:
            return True, f"Source {source} crashed in last {n} consecutive runs"
        return False, ""

    def recommended_extraction_tier(self, source: str, n: int = 5) -> int:
        """Recommend extraction tier based on historical success rates.

        Returns:
            1 (text), 2 (OCR), or 3 (vision) — start tier suggestion
        """
        # Default to Tier 1 if no history
        rows = self._source_rows(source, n=n)
        if not rows:
            return 1

        # Count runs where source had documents but low extraction success
        # For now, return 1 (full implementation needs extraction-level tracking)
        return 1

    def source_trend(self, source: str, n: int = 10) -> list[dict]:
        """Return per-source health data for last *n* runs.

        Returns:
            List of dicts with run_id, docs, status per run
        """
        return self._source_rows(source, n=n)

    def degrading_sources(self, n: int = 5) -> list[str]:
        """Identify sources whose document counts are declining.

        Returns:
            List of source names with declining trends.
        """
        from ..agent import ALL_SOURCES
        degrading = []

        for source in ALL_SOURCES:
            rows = self._source_rows(source, n=n)
            doc_counts = [r.get("docs", 0) for r in rows if "docs" in r]
            if len(doc_counts) >= 3:
                # Simple trend: is the latest count lower than the average?
                avg = sum(doc_counts[:-1]) / len(doc_counts[:-1])
                if doc_counts[-1] < avg * 0.5 and avg > 0:
                    degrading.append(source)

        return degrading
