"""
Run ledger — append-only TSV tracking every pipeline run.

Inspired by Karpathy's autoresearch experiment log: each run records its
health score, source counts, and a KEEP/DISCARD/CRASH-style status so
that trends are visible across runs.

File format: data/run_ledger.tsv  (tab-separated, one row per run)
"""

from __future__ import annotations

import csv
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .health import PipelineHealthScore


_COLUMNS = [
    "run_id",
    "timestamp",
    "git_commit",
    "health_score",
    "sources_ok",
    "sources_failed",
    "docs_discovered",
    "docs_downloaded",
    "obs_extracted",
    "obs_qc_passed",
    "duration_s",
    "status",
    "description",
]


class RunLedger:
    """Append-only TSV ledger at *path* (default ``data/run_ledger.tsv``)."""

    def __init__(self, path: Optional[str | Path] = None) -> None:
        self.path = Path(path or "data/run_ledger.tsv")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ── Write ──────────────────────────────────────────────────────────

    def append(
        self,
        score: PipelineHealthScore,
        status: str = "COMPLETE",
        description: str = "",
    ) -> None:
        """Append one row for a completed pipeline run."""
        write_header = not self.path.exists() or self.path.stat().st_size == 0

        row = {
            "run_id": score.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git_commit": score.git_commit or _current_git_commit(),
            "health_score": f"{score.health_score:.4f}",
            "sources_ok": str(score.sources_ok),
            "sources_failed": str(score.sources_failed),
            "docs_discovered": str(score.total_discovered),
            "docs_downloaded": str(score.total_downloaded),
            "obs_extracted": str(score.total_extracted),
            "obs_qc_passed": str(score.total_qc_passed),
            "duration_s": f"{score.duration_seconds:.0f}",
            "status": status,
            "description": description.replace("\t", " ").replace("\n", " "),
        }

        with open(self.path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=_COLUMNS, delimiter="\t")
            if write_header:
                writer.writeheader()
            writer.writerow(row)

    # ── Read ───────────────────────────────────────────────────────────

    def read_all(self) -> list[dict]:
        """Read all rows as list of dicts."""
        if not self.path.exists():
            return []
        with open(self.path, newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            return list(reader)

    def read_recent(self, n: int = 10) -> list[dict]:
        """Return the last *n* rows (most recent first)."""
        rows = self.read_all()
        return list(reversed(rows[-n:]))

    # ── Display ────────────────────────────────────────────────────────

    def trend_table(self, n: int = 10) -> str:
        """Return a formatted trend table for the last *n* runs."""
        rows = self.read_recent(n)
        if not rows:
            return "No runs recorded yet."

        lines = [
            f"{'Run ID':<14} {'Time':<22} {'Health':>7} {'OK':>3} {'Fail':>4} "
            f"{'Disc':>5} {'DL':>5} {'QC✓':>5} {'Status':<10}",
            "-" * 85,
        ]
        for r in rows:
            lines.append(
                f"{r.get('run_id', '')[:13]:<14} "
                f"{r.get('timestamp', '')[:21]:<22} "
                f"{r.get('health_score', ''):>7} "
                f"{r.get('sources_ok', ''):>3} "
                f"{r.get('sources_failed', ''):>4} "
                f"{r.get('docs_discovered', ''):>5} "
                f"{r.get('docs_downloaded', ''):>5} "
                f"{r.get('obs_qc_passed', ''):>5} "
                f"{r.get('status', ''):<10}"
            )
        return "\n".join(lines)

    def health_sparkline(self, n: int = 20) -> str:
        """Return an ASCII sparkline of health scores over last *n* runs."""
        rows = self.read_all()[-n:]
        if not rows:
            return "No data"
        scores = []
        for r in rows:
            try:
                scores.append(float(r["health_score"]))
            except (KeyError, ValueError):
                scores.append(0.0)
        blocks = " ▁▂▃▄▅▆▇█"
        if max(scores) == min(scores):
            return "".join(blocks[4] for _ in scores)
        span = max(scores) - min(scores)
        return "".join(
            blocks[min(int((s - min(scores)) / span * 8), 8)] for s in scores
        )


def _current_git_commit() -> str:
    """Return short git commit hash, or empty string."""
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        return ""
