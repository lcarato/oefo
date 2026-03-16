"""
Strategy registry — tracks which scraping strategies work per source.

Each source can have multiple strategies (sitemap, api, dom_parse, known_docs).
The registry records success/failure stats and auto-promotes strategies that
yield more documents while demoting those that consistently fail.

Persisted as data/strategy_registry.json.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path("data/strategy_registry.json")


@dataclass
class StrategyRecord:
    """Performance record for a single scraping strategy."""

    name: str           # "sitemap", "api", "dom_parse", "known_docs"
    source: str         # "ifc", "ebrd", etc.
    priority: int = 0   # Lower = tried first
    success_count: int = 0
    failure_count: int = 0
    last_doc_count: int = 0
    last_run: str = ""  # ISO timestamp
    enabled: bool = True

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / max(total, 1)

    @property
    def total_runs(self) -> int:
        return self.success_count + self.failure_count


class StrategyRegistry:
    """Persistent registry of scraping strategies and their performance.

    Strategies are ordered by priority (lower = tried first). The registry
    auto-promotes strategies that find more documents and demotes/disables
    those that consistently fail.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or _DEFAULT_PATH
        self._records: dict[str, list[StrategyRecord]] = {}
        self._load()

    # ── Persistence ────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load registry from disk."""
        if not self.path.exists():
            self._records = {}
            return
        try:
            data = json.loads(self.path.read_text())
            self._records = {}
            for source, strategies in data.items():
                self._records[source] = [
                    StrategyRecord(**s) for s in strategies
                ]
        except (json.JSONDecodeError, OSError, TypeError) as e:
            logger.warning(f"Could not load strategy registry: {e}")
            self._records = {}

    def _save(self) -> None:
        """Persist registry to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            source: [asdict(r) for r in records]
            for source, records in self._records.items()
        }
        try:
            self.path.write_text(json.dumps(data, indent=2))
        except OSError as e:
            logger.warning(f"Could not save strategy registry: {e}")

    # ── Query ──────────────────────────────────────────────────────────

    def get_strategies(self, source: str) -> list[StrategyRecord]:
        """Get strategies for a source, ordered by priority (lowest first)."""
        records = self._records.get(source.lower(), [])
        return sorted(
            [r for r in records if r.enabled],
            key=lambda r: r.priority,
        )

    def get_all(self) -> dict[str, list[StrategyRecord]]:
        """Get all strategies for all sources."""
        return dict(self._records)

    # ── Update ─────────────────────────────────────────────────────────

    def record_result(
        self,
        source: str,
        strategy: str,
        doc_count: int,
        error: Optional[str] = None,
    ) -> None:
        """Record the result of a strategy execution.

        Args:
            source: Source name (e.g. "ifc")
            strategy: Strategy name (e.g. "sitemap")
            doc_count: Number of documents found
            error: Error message if the strategy failed
        """
        source = source.lower()
        if source not in self._records:
            self._records[source] = []

        record = next(
            (r for r in self._records[source] if r.name == strategy),
            None,
        )
        if record is None:
            record = StrategyRecord(
                name=strategy,
                source=source,
                priority=len(self._records[source]),
            )
            self._records[source].append(record)

        record.last_run = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record.last_doc_count = doc_count

        if error:
            record.failure_count += 1
        else:
            record.success_count += 1

        self._save()

    def promote(self, source: str, strategy: str) -> None:
        """Move a strategy to highest priority (priority 0), shift others down."""
        source = source.lower()
        records = self._records.get(source, [])
        target = next((r for r in records if r.name == strategy), None)
        if not target:
            return
        old_priority = target.priority
        target.priority = 0
        for r in records:
            if r.name != strategy and r.priority < old_priority:
                r.priority += 1
        self._save()

    def demote(self, source: str, strategy: str) -> None:
        """Move a strategy to lower priority (higher number)."""
        source = source.lower()
        records = self._records.get(source, [])
        for r in records:
            if r.name == strategy:
                r.priority += 1
        self._save()

    def disable(self, source: str, strategy: str) -> None:
        """Disable a strategy so it won't be tried."""
        source = source.lower()
        records = self._records.get(source, [])
        for r in records:
            if r.name == strategy:
                r.enabled = False
        self._save()

    def auto_adjust(self, source: str) -> None:
        """Auto-promote the best-performing strategy and demote failures.

        Called after a scrape run. Promotes the strategy with the highest
        last_doc_count and demotes strategies with 3+ consecutive failures.
        """
        source = source.lower()
        records = self._records.get(source, [])
        if not records:
            return

        # Find best performer
        enabled = [r for r in records if r.enabled]
        if not enabled:
            return

        best = max(enabled, key=lambda r: r.last_doc_count)

        # Promote best to priority 0, shift others
        for r in records:
            if r.name == best.name:
                r.priority = 0
            elif r.enabled:
                r.priority = max(r.priority, 1)

        # Disable strategies that have failed 3+ times consecutively
        # (approximation: failure_count > success_count + 3)
        for r in records:
            if r.failure_count > r.success_count + 3 and r.enabled:
                logger.info(
                    f"Auto-disabling strategy {r.name} for {source} "
                    f"(failures={r.failure_count}, successes={r.success_count})"
                )
                r.enabled = False

        self._save()

    # ── Display ────────────────────────────────────────────────────────

    def summary_table(self) -> str:
        """Format a summary table of all strategies."""
        lines = [
            f"{'Source':<10} {'Strategy':<15} {'Pri':>3} {'OK':>4} {'Fail':>4} "
            f"{'Last Docs':>9} {'Enabled':>7}",
            "-" * 65,
        ]
        for source in sorted(self._records):
            for r in sorted(self._records[source], key=lambda x: x.priority):
                lines.append(
                    f"{r.source:<10} {r.name:<15} {r.priority:>3} "
                    f"{r.success_count:>4} {r.failure_count:>4} "
                    f"{r.last_doc_count:>9} {'✓' if r.enabled else '✗':>7}"
                )
        return "\n".join(lines)
