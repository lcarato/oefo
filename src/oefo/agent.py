"""
OEFO Pipeline Agent - End-to-end orchestrator.

Runs the full OEFO pipeline autonomously:
  Phase 1: Pre-flight checks (API keys, directories, dependencies)
  Phase 2: Scrape data sources (DFI, regulatory, corporate)
  Phase 3: Extract financial data (multi-tier: text -> OCR -> vision)
  Phase 4: Quality control (rules, statistics, LLM cross-validation)
  Phase 5: Export (Excel, CSV, Parquet)
  Phase 6: Generate run report

Traceability guarantee: every run writes to its own {run_id}/ subdirectory.
Previous runs are never overwritten.  A ``latest`` symlink in each parent
directory always points to the most recent run for convenience.

Usage (Python):
    from oefo.agent import PipelineAgent
    agent = PipelineAgent()
    report = agent.run()

Usage (CLI):
    python -m oefo run --full
    python -m oefo run --sources ifc,ebrd --skip-export
    python -m oefo run --qc-only
"""

import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .metrics.health import SourceHealthScore, PipelineHealthScore
from .metrics.ledger import RunLedger
from .scrapers.probes import probe_all

logger = logging.getLogger(__name__)


class RunType(str, Enum):
    """Type of pipeline run."""
    FULL = "full"
    WEEKLY_DFI = "weekly_dfi"
    MONTHLY_REGULATORY = "monthly_regulatory"
    QUARTERLY_SEC = "quarterly_sec"
    QC_ONLY = "qc_only"
    EXPORT_ONLY = "export_only"


class PhaseName(str, Enum):
    """Pipeline phase names."""
    PREFLIGHT = "preflight"
    SCRAPE = "scrape"
    EXTRACT = "extract"
    QC = "qc"
    EXPORT = "export"
    REPORT = "report"


class Severity(str, Enum):
    """Error severity per OEFO agent protocol."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PhaseResult:
    """Result from a single pipeline phase."""
    phase: PhaseName
    success: bool
    duration_seconds: float
    details: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


@dataclass
class RunReport:
    """Structured run report following OEFO agent protocol."""
    run_id: str
    run_type: RunType
    start_time: datetime
    end_time: Optional[datetime] = None
    phases: list = field(default_factory=list)
    overall_success: bool = False
    halted: bool = False
    halt_reason: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def to_text(self) -> str:
        """Generate the OEFO-standard run report text."""
        lines = [
            "=== OEFO Pipeline Run Report ===",
            f"Run ID: {self.run_id}",
            f"Date: {self.start_time.strftime('%Y-%m-%d %H:%M UTC')}",
            f"Run type: {self.run_type.value}",
            f"Duration: {self.duration_seconds:.0f}s",
            f"Overall: {'SUCCESS' if self.overall_success else 'FAILED'}",
            "",
        ]

        for phase_result in self.phases:
            status = "OK" if phase_result.success else "FAILED"
            lines.append(
                f"--- {phase_result.phase.value.upper()} ({status}, "
                f"{phase_result.duration_seconds:.1f}s) ---"
            )
            for k, v in phase_result.details.items():
                lines.append(f"  {k}: {v}")
            for err in phase_result.errors:
                lines.append(f"  ERROR: {err}")
            for warn in phase_result.warnings:
                lines.append(f"  WARNING: {warn}")
            lines.append("")

        if self.halted:
            lines.append(f"HALTED: {self.halt_reason}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize to dict for JSON export."""
        return {
            "run_id": self.run_id,
            "run_type": self.run_type.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "overall_success": self.overall_success,
            "halted": self.halted,
            "halt_reason": self.halt_reason,
            "phases": [
                {
                    "phase": pr.phase.value,
                    "success": pr.success,
                    "duration_seconds": pr.duration_seconds,
                    "details": pr.details,
                    "errors": pr.errors,
                    "warnings": pr.warnings,
                }
                for pr in self.phases
            ],
        }


# ── Source groupings ────────────────────────────────────────────────────────

DFI_SOURCES = ["ifc", "ebrd", "gcf"]
REGULATORY_SOURCES = ["aneel", "aer", "ofgem", "ferc"]
CORPORATE_SOURCES = ["sec"]
ALL_SOURCES = DFI_SOURCES + REGULATORY_SOURCES + CORPORATE_SOURCES

SOURCE_TYPE_MAP = {
    "ifc": "dfi",
    "ebrd": "dfi",
    "gcf": "dfi",
    "aneel": "regulatory",
    "aer": "regulatory",
    "ofgem": "regulatory",
    "ferc": "regulatory",
    "sec": "corporate",
}


# ── Symlink helper ──────────────────────────────────────────────────────────

def _update_latest_symlink(parent_dir: Path, target_dir: Path) -> None:
    """
    Create or update a ``latest`` symlink in *parent_dir* pointing to
    *target_dir*.  Uses an atomic rename so concurrent readers never see a
    broken link.
    """
    link_path = parent_dir / "latest"
    tmp_link = parent_dir / f".latest_tmp_{os.getpid()}"
    try:
        # Remove stale temp link if a previous run crashed
        if tmp_link.is_symlink() or tmp_link.exists():
            tmp_link.unlink()
        tmp_link.symlink_to(target_dir)
        tmp_link.rename(link_path)          # atomic on POSIX
    except OSError:
        # Non-critical; the run data is still fully intact
        logger.debug(f"Could not update 'latest' symlink in {parent_dir}")


class PipelineAgent:
    """
    End-to-end pipeline orchestrator for the OEFO data pipeline.

    Manages the full lifecycle: scraping public documents, extracting
    financial data, running quality control, exporting results, and
    generating structured run reports.

    **Traceability guarantee** — every run creates its own subdirectory
    under ``data/extracted/{run_id}/``, ``data/final/{run_id}/``, and
    ``outputs/{run_id}/``.  Previous runs are never overwritten.  A
    ``latest`` symlink in each parent directory points to the most recent
    run for convenience.

    Follows the OEFO Agent Protocol:
    - Conservative operation: flag for review rather than auto-accept
    - Full traceability: every value traces to a public source
    - Graceful error handling with severity-based escalation
    - Structured run reports after every execution
    """

    def __init__(
        self,
        run_type: RunType = RunType.FULL,
        sources: Optional[list[str]] = None,
        qc_full: bool = True,
        export_formats: Optional[list[str]] = None,
        skip_scrape: bool = False,
        skip_extract: bool = False,
        skip_qc: bool = False,
        skip_export: bool = False,
        force_scrape: bool = False,
        parallel_workers: int = 4,
        verbose: bool = False,
    ):
        """
        Initialize the Pipeline Agent.

        Args:
            run_type: Type of run (full, weekly_dfi, monthly_regulatory, etc.)
            sources: Specific sources to scrape (None = all for run_type)
            qc_full: Enable all 3 QC layers (rules + stats + LLM)
            export_formats: Output formats (default: excel, csv, parquet)
            skip_scrape: Skip the scraping phase
            skip_extract: Skip the extraction phase
            skip_qc: Skip the QC phase
            skip_export: Skip the export phase
            force_scrape: Force re-scraping even if data exists
            parallel_workers: Number of parallel extraction workers
            verbose: Enable verbose logging
        """
        self.run_type = run_type
        self.qc_full = qc_full
        self.export_formats = export_formats or ["excel", "csv", "parquet"]
        self.skip_scrape = skip_scrape
        self.skip_extract = skip_extract
        self.skip_qc = skip_qc
        self.skip_export = skip_export
        self.force_scrape = force_scrape
        self.parallel_workers = parallel_workers
        self.verbose = verbose

        # Resolve sources based on run_type
        if sources:
            self.sources = [s.lower() for s in sources]
        elif run_type == RunType.WEEKLY_DFI:
            self.sources = DFI_SOURCES
        elif run_type == RunType.MONTHLY_REGULATORY:
            self.sources = REGULATORY_SOURCES
        elif run_type == RunType.QUARTERLY_SEC:
            self.sources = CORPORATE_SOURCES
        elif run_type == RunType.QC_ONLY:
            self.sources = []
            self.skip_scrape = True
            self.skip_extract = True
        elif run_type == RunType.EXPORT_ONLY:
            self.sources = []
            self.skip_scrape = True
            self.skip_extract = True
            self.skip_qc = True
        else:
            self.sources = ALL_SOURCES

        # Run state — every run gets a unique ID used to namespace all outputs
        self.run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.report = RunReport(
            run_id=self.run_id,
            run_type=self.run_type,
            start_time=datetime.now(),
        )

        # Run-scoped output directories — set during preflight once settings
        # are loaded.  These are *subdirectories* named after the run_id so
        # that no two runs can ever collide.
        self._extracted_run_dir: Optional[Path] = None
        self._final_run_dir: Optional[Path] = None
        self._outputs_run_dir: Optional[Path] = None

        # Health tracking (wired to metrics/health.py and metrics/ledger.py)
        self.pipeline_health = PipelineHealthScore(run_id=self.run_id)
        self._ledger = RunLedger()

        if verbose:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

    # ── Main entry point ────────────────────────────────────────────────────

    def run(self) -> RunReport:
        """
        Execute the full pipeline.

        Runs phases in strict order. Halts on HIGH/CRITICAL errors.
        Returns a structured RunReport.
        """
        logger.info(f"Pipeline Agent starting: {self.run_id} ({self.run_type.value})")
        print(f"\n{'='*60}")
        print(f"  OEFO Pipeline Agent")
        print(f"  Run ID: {self.run_id}")
        print(f"  Type: {self.run_type.value}")
        print(f"  Sources: {', '.join(self.sources) if self.sources else 'N/A'}")
        print(f"{'='*60}\n")

        try:
            # Phase 1: Pre-flight checks (always runs)
            preflight_ok = self._run_phase(
                PhaseName.PREFLIGHT, self._preflight_checks
            )
            if not preflight_ok:
                self._halt("Pre-flight checks failed")
                return self._finalize()

            # Phase 2: Scrape
            if not self.skip_scrape and self.sources:
                scrape_ok = self._run_phase(PhaseName.SCRAPE, self._scrape)
                if not scrape_ok:
                    # Scrape failures are LOW/MEDIUM — continue if any data exists
                    logger.warning("Scrape had errors, checking if data exists to continue")

            # Phase 3: Extract
            if not self.skip_extract:
                extract_ok = self._run_phase(PhaseName.EXTRACT, self._extract)
                if not extract_ok:
                    logger.warning("Extraction had errors, continuing to QC with available data")

            # Phase 4: QC
            if not self.skip_qc:
                qc_ok = self._run_phase(PhaseName.QC, self._qc)
                if not qc_ok:
                    logger.warning("QC had errors")

            # Phase 5: Export
            if not self.skip_export:
                self._run_phase(PhaseName.EXPORT, self._export)

            # Phase 6: Report (always runs)
            self._run_phase(PhaseName.REPORT, self._generate_report)

        except Exception as e:
            logger.critical(f"Pipeline Agent crashed: {e}", exc_info=True)
            self._halt(f"Unhandled exception: {e}")

        return self._finalize()

    # ── Phase implementations ───────────────────────────────────────────────

    def _preflight_checks(self) -> PhaseResult:
        """Phase 1: Validate environment and create run-scoped directories."""
        details = {}
        errors = []
        warnings = []

        # Check oefo is importable
        try:
            from oefo import __version__
            details["oefo_version"] = __version__
        except ImportError as e:
            errors.append(f"Cannot import oefo: {e}")
            return PhaseResult(
                phase=PhaseName.PREFLIGHT,
                success=False,
                duration_seconds=0,
                details=details,
                errors=errors,
            )

        # Check API keys
        from oefo.config.settings import (
            ANTHROPIC_API_KEY,
            OPENAI_API_KEY,
            LLM_PROVIDER,
        )

        providers = []
        if ANTHROPIC_API_KEY:
            providers.append("anthropic")
        if OPENAI_API_KEY:
            providers.append("openai")
        if LLM_PROVIDER.lower() == "ollama":
            providers.append("ollama")

        details["llm_providers"] = ", ".join(providers) if providers else "none"

        if not providers:
            warnings.append(
                "No LLM providers configured. Tier 3 extraction and LLM QC "
                "will be unavailable. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
            )

        # Check and create directories
        from oefo.config.settings import ensure_directories, DATA_DIR, RAW_DIR, EXTRACTED_DIR, FINAL_DIR

        ensure_directories()
        details["data_dir"] = str(DATA_DIR)

        # Create run-scoped subdirectories (never overwrite previous runs)
        self._extracted_run_dir = EXTRACTED_DIR / self.run_id
        self._extracted_run_dir.mkdir(parents=True, exist_ok=True)

        self._final_run_dir = FINAL_DIR / self.run_id
        self._final_run_dir.mkdir(parents=True, exist_ok=True)

        self._outputs_run_dir = Path("outputs") / self.run_id
        self._outputs_run_dir.mkdir(parents=True, exist_ok=True)

        details["extracted_dir"] = str(self._extracted_run_dir)
        details["final_dir"] = str(self._final_run_dir)
        details["outputs_dir"] = str(self._outputs_run_dir)

        # Check disk space
        try:
            disk_usage = shutil.disk_usage(str(DATA_DIR))
            free_gb = disk_usage.free / (1024 ** 3)
            details["disk_free_gb"] = f"{free_gb:.1f}"
            if free_gb < 1.0:
                errors.append(f"Low disk space: {free_gb:.1f} GB free")
        except Exception:
            warnings.append("Could not check disk space")

        # Check system dependencies
        for dep, cmd in [("poppler", "pdftotext"), ("tesseract", "tesseract")]:
            if shutil.which(cmd):
                details[f"{dep}_installed"] = "yes"
            else:
                warnings.append(
                    f"{dep} not found ({cmd}). OCR extraction may not work. "
                    f"Install with: brew install {dep}"
                )
                details[f"{dep}_installed"] = "no"

        # Count existing data (across all runs)
        raw_count = len(list(RAW_DIR.glob("**/*.pdf"))) if RAW_DIR.exists() else 0
        extracted_count = len(list(EXTRACTED_DIR.glob("**/*.json"))) if EXTRACTED_DIR.exists() else 0
        final_count = len(list(FINAL_DIR.glob("**/*.json"))) if FINAL_DIR.exists() else 0
        details["existing_raw_pdfs"] = raw_count
        details["existing_extractions"] = extracted_count
        details["existing_final"] = final_count

        success = len(errors) == 0
        if success:
            print("  Phase 1: Pre-flight checks PASSED")
        else:
            print("  Phase 1: Pre-flight checks FAILED")
            for err in errors:
                print(f"    ERROR: {err}")

        return PhaseResult(
            phase=PhaseName.PREFLIGHT,
            success=success,
            duration_seconds=0,
            details=details,
            errors=errors,
            warnings=warnings,
        )

    def _scrape(self) -> PhaseResult:
        """Phase 2: Scrape data sources with health tracking and probe preflight."""
        from oefo.scrapers import get_scraper
        from oefo.config.settings import RAW_DIR

        details = {"sources_attempted": [], "sources_succeeded": [], "sources_failed": []}
        errors = []
        warnings = []
        total_docs = 0

        # ── Preflight probes ───────────────────────────────────────────
        print(f"\n  Phase 2a: Probing {len(self.sources)} source(s)...")
        try:
            probe_results = probe_all(self.sources)
            skip_sources = set()
            for pr in probe_results:
                icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(pr.status, "⚪")
                print(f"    {icon} {pr.source:<8} reach={'✓' if pr.reachable else '✗'}  "
                      f"sitemap={'✓' if pr.sitemap_available else '—'}  "
                      f"{pr.latency_ms:.0f}ms")
                if pr.status == "RED":
                    warnings.append(f"Probe {pr.source}: RED — {pr.error or 'unreachable'}")
                    skip_sources.add(pr.source.lower())
        except Exception as e:
            logger.warning(f"Probe preflight failed (continuing anyway): {e}")
            skip_sources = set()

        # ── Scrape each source ─────────────────────────────────────────
        print(f"\n  Phase 2b: Scraping {len(self.sources)} source(s)...")

        for source in self.sources:
            source_upper = source.upper()
            details["sources_attempted"].append(source)
            source_health = SourceHealthScore(source_name=source)
            source_start = time.time()

            if source.lower() in skip_sources:
                print(f"    [{source_upper}] SKIPPED (probe RED)")
                source_health.decision = "CRASH"
                source_health.decision_reason = "Probe returned RED"
                self.pipeline_health.source_scores.append(source_health)
                continue

            try:
                print(f"    [{source_upper}] Scraping...", end=" ", flush=True)
                output_dir = str(RAW_DIR / source.lower())
                scraper = get_scraper(source_upper, output_dir=output_dir)

                documents = scraper.scrape()
                count = len(documents) if documents else 0
                total_docs += count
                details["sources_succeeded"].append(source)
                details[f"docs_{source}"] = count
                print(f"{count} documents")

                source_health.discovery_count = count
                source_health.download_count = count
                source_health.decision = "KEEP" if count > 0 else "DISCARD"
                source_health.decision_reason = (
                    f"{count} docs" if count > 0 else "0 documents discovered"
                )

            except Exception as e:
                details["sources_failed"].append(f"{source}: {e}")
                errors.append(f"Scrape {source_upper} failed: {e}")
                print(f"FAILED ({e})")

                source_health.record_error(e)
                source_health.decision = "CRASH"
                source_health.decision_reason = str(e)[:200]

            source_health.duration_seconds = time.time() - source_start
            self.pipeline_health.source_scores.append(source_health)

        details["total_documents"] = total_docs
        success = len(details["sources_succeeded"]) > 0 or total_docs > 0

        # Print health summary
        print(f"\n    {self.pipeline_health.summary_line()}")
        print(f"\n{self.pipeline_health.detail_table()}")

        return PhaseResult(
            phase=PhaseName.SCRAPE,
            success=success,
            duration_seconds=0,
            details=details,
            errors=errors,
            warnings=warnings,
        )

    def _extract(self) -> PhaseResult:
        """Phase 3: Extract financial data from PDFs into run-scoped dir."""
        from oefo.extraction import ExtractionPipeline
        from oefo.config.settings import RAW_DIR, EXTRACTED_DIR

        details = {"batches_processed": 0, "total_pages": 0, "errors_count": 0}
        errors = []
        warnings = []

        run_dir = self._extracted_run_dir
        pipeline = ExtractionPipeline()

        # Determine which source dirs to extract from
        source_dirs = []
        for source in self.sources:
            source_dir = RAW_DIR / source.lower()
            if source_dir.exists():
                pdfs = list(source_dir.glob("*.pdf"))
                if pdfs:
                    source_type = SOURCE_TYPE_MAP.get(source, "corporate")
                    source_dirs.append((source, source_dir, source_type, pdfs))

        if not source_dirs:
            # Also check if there are any PDFs in raw dir at all
            all_pdfs = list(RAW_DIR.glob("**/*.pdf"))
            if all_pdfs:
                warnings.append(
                    f"Found {len(all_pdfs)} PDFs in {RAW_DIR} but none match "
                    f"the requested sources: {self.sources}"
                )
            else:
                warnings.append(f"No PDFs found in {RAW_DIR}")

            return PhaseResult(
                phase=PhaseName.EXTRACT,
                success=True,  # Not a failure, just nothing to do
                duration_seconds=0,
                details=details,
                errors=errors,
                warnings=warnings,
            )

        total_pdfs = sum(len(pdfs) for _, _, _, pdfs in source_dirs)
        print(f"\n  Phase 3: Extracting from {total_pdfs} PDFs across {len(source_dirs)} sources...")
        print(f"    Output dir: {run_dir}")

        processed = 0
        for source, source_dir, source_type, pdfs in source_dirs:
            print(f"    [{source.upper()}] {len(pdfs)} PDFs (type: {source_type})")

            for pdf_file in pdfs:
                processed += 1
                try:
                    results = pipeline.extract(
                        pdf_path=str(pdf_file),
                        source_type=source_type,
                        source_document_url=str(pdf_file.resolve()),
                        source_document_id=pdf_file.stem,
                    )

                    # Save extraction results to run-scoped directory
                    out_file = run_dir / f"{pdf_file.stem}.json"
                    with open(out_file, "w") as f:
                        json.dump(
                            [r.to_dict() for r in results],
                            f,
                            indent=2,
                            default=str,
                        )

                    details["total_pages"] += len(results)
                    details["batches_processed"] += 1

                except Exception as e:
                    details["errors_count"] += 1
                    errors.append(f"Extract {pdf_file.name}: {e}")
                    logger.error(f"Extraction failed for {pdf_file.name}: {e}")

        details["pdfs_processed"] = processed
        details["output_dir"] = str(run_dir)
        success = details["batches_processed"] > 0 or details["errors_count"] == 0

        # Update latest symlink
        _update_latest_symlink(EXTRACTED_DIR, run_dir)

        print(
            f"    Done: {details['batches_processed']} succeeded, "
            f"{details['errors_count']} failed, "
            f"{details['total_pages']} pages extracted"
        )

        return PhaseResult(
            phase=PhaseName.EXTRACT,
            success=success,
            duration_seconds=0,
            details=details,
            errors=errors,
            warnings=warnings,
        )

    def _qc(self) -> PhaseResult:
        """Phase 4: Quality control — reads from run dir, writes to run dir."""
        from oefo.qc import QCAgent
        from oefo.config.settings import EXTRACTED_DIR, FINAL_DIR
        from oefo.models import Observation

        details = {}
        errors = []
        warnings = []

        print("\n  Phase 4: Quality Control...")

        # Load extracted observations — prefer this run's extraction dir,
        # fall back to the global extracted dir (for qc_only runs).
        extract_dir = self._extracted_run_dir
        json_files = list(extract_dir.glob("*.json")) if extract_dir and extract_dir.exists() else []

        if not json_files:
            # Fall back: look across all run dirs in EXTRACTED_DIR
            json_files = list(EXTRACTED_DIR.glob("**/*.json")) if EXTRACTED_DIR.exists() else []

        if not json_files:
            warnings.append("No extraction files found. Run extraction first.")
            return PhaseResult(
                phase=PhaseName.QC,
                success=True,
                duration_seconds=0,
                details={"observations_found": 0},
                errors=errors,
                warnings=warnings,
            )

        observations = []
        for jf in json_files:
            try:
                with open(jf) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "extracted_data" in item:
                            obs_data = item.get("extracted_data", {})
                            if obs_data:
                                observations.append(obs_data)
            except Exception as e:
                warnings.append(f"Could not load {jf.name}: {e}")

        details["observations_found"] = len(observations)
        print(f"    Loaded {len(observations)} observations from {len(json_files)} files")

        if not observations:
            warnings.append("No valid observations found in extraction files")
            return PhaseResult(
                phase=PhaseName.QC,
                success=True,
                duration_seconds=0,
                details=details,
                errors=errors,
                warnings=warnings,
            )

        # Run QC
        mode = "full (3-layer)" if self.qc_full else "rules + stats"
        print(f"    Mode: {mode}")

        try:
            agent = QCAgent(
                enable_rules=True,
                enable_stats=True,
                enable_llm=self.qc_full,
            )

            results = agent.process_batch(
                observations=observations,
                existing_observations=[],
            )

            auto = len(results.get("auto_accepted", []))
            flagged = len(results.get("flagged_for_review", []))
            rejected = len(results.get("rejected", []))
            total = auto + flagged + rejected

            details["auto_accepted"] = auto
            details["flagged_for_review"] = flagged
            details["rejected"] = rejected
            details["total_processed"] = total
            details["auto_accept_rate"] = f"{auto/total*100:.1f}%" if total else "N/A"
            details["mean_qc_score"] = results.get("summary", {}).get(
                "avg_score_auto_accepted", 0
            )

            print(f"    Auto-accepted: {auto}")
            print(f"    Flagged for review: {flagged}")
            print(f"    Rejected: {rejected}")

            # Check for HIGH severity conditions
            if total > 0:
                mean_score = (
                    sum(
                        r.qc_score
                        for r in results.get("auto_accepted", [])
                        + results.get("flagged_for_review", [])
                        + results.get("rejected", [])
                    )
                    / total
                    / 100  # Convert from 0-100 to 0-1
                )
                details["mean_score_all"] = f"{mean_score:.2f}"

                if mean_score < 0.5:
                    errors.append(
                        f"HIGH: Mean QC score {mean_score:.2f} < 0.50. "
                        f"Halting pipeline per agent protocol."
                    )

            # Save QC results to run-scoped final directory
            run_dir = self._final_run_dir
            qc_output = run_dir / "qc_results.json"
            with open(qc_output, "w") as f:
                json.dump(results, f, indent=2, default=str)
            details["qc_output"] = str(qc_output)

            # Update latest symlink
            _update_latest_symlink(FINAL_DIR, run_dir)

        except Exception as e:
            errors.append(f"QC agent failed: {e}")
            logger.error(f"QC failed: {e}", exc_info=True)

        success = len(errors) == 0
        return PhaseResult(
            phase=PhaseName.QC,
            success=success,
            duration_seconds=0,
            details=details,
            errors=errors,
            warnings=warnings,
        )

    def _export(self) -> PhaseResult:
        """Phase 5: Export results to run-scoped outputs directory."""
        details = {"formats_exported": []}
        errors = []
        warnings = []

        print("\n  Phase 5: Export...")

        run_dir = self._outputs_run_dir
        print(f"    Output dir: {run_dir}")

        # Determine which QC results to export — prefer this run's final dir
        final_dir = self._final_run_dir
        if not final_dir or not any(final_dir.glob("*.json")):
            # Fall back to global latest
            from oefo.config.settings import FINAL_DIR
            final_dir = FINAL_DIR

        for fmt in self.export_formats:
            try:
                output_path = run_dir / f"oefo_database.{_ext(fmt)}"
                print(f"    Exporting {fmt.upper()} -> {output_path}...", end=" ", flush=True)

                import pandas as pd

                # Load data from the QC-approved final directory
                records = []
                if final_dir.exists():
                    for jf in final_dir.glob("**/*.json"):
                        try:
                            with open(jf) as f:
                                data = json.load(f)
                            if isinstance(data, list):
                                records.extend(data)
                            elif isinstance(data, dict):
                                records.append(data)
                        except Exception:
                            pass

                if not records:
                    warnings.append(f"No data to export for {fmt}")
                    print("SKIPPED (no data)")
                    continue

                df = pd.DataFrame(records)

                if fmt == "excel":
                    from oefo.outputs.excel import ExcelOutputGenerator
                    gen = ExcelOutputGenerator()
                    gen.generate_workbook(df, str(output_path))
                elif fmt == "csv":
                    from oefo.outputs.csv_export import export_csv
                    export_csv(df, str(output_path))
                elif fmt == "parquet":
                    from oefo.outputs.csv_export import export_parquet
                    export_parquet(df, str(output_path))
                elif fmt == "json":
                    from oefo.outputs.csv_export import export_json
                    export_json(df, str(output_path))

                details["formats_exported"].append(fmt)
                print("OK")

            except Exception as e:
                errors.append(f"Export {fmt} failed: {e}")
                print(f"FAILED ({e})")

        # Update latest symlink
        _update_latest_symlink(Path("outputs"), run_dir)

        return PhaseResult(
            phase=PhaseName.EXPORT,
            success=len(errors) == 0,
            duration_seconds=0,
            details=details,
            errors=errors,
            warnings=warnings,
        )

    def _generate_report(self) -> PhaseResult:
        """Phase 6: Generate and save run report to run-scoped dir."""
        details = {}
        errors = []

        try:
            run_dir = self._outputs_run_dir
            if run_dir is None:
                run_dir = Path("outputs") / self.run_id
                run_dir.mkdir(parents=True, exist_ok=True)

            # Save text report
            report_path = run_dir / "run_report.txt"
            report_text = self.report.to_text()
            with open(report_path, "w") as f:
                f.write(report_text)
            details["report_path"] = str(report_path)

            # Save JSON report
            json_path = run_dir / "run_report.json"
            with open(json_path, "w") as f:
                json.dump(self.report.to_dict(), f, indent=2, default=str)
            details["json_report_path"] = str(json_path)

            print(f"\n  Phase 6: Report saved to {run_dir}/")

        except Exception as e:
            errors.append(f"Report generation failed: {e}")

        return PhaseResult(
            phase=PhaseName.REPORT,
            success=len(errors) == 0,
            duration_seconds=0,
            details=details,
            errors=errors,
        )

    # ── Internal helpers ────────────────────────────────────────────────────

    def _run_phase(self, phase_name: PhaseName, phase_fn) -> bool:
        """Run a phase with timing and error handling."""
        start = time.time()

        try:
            result = phase_fn()
            result.duration_seconds = time.time() - start
            self.report.phases.append(result)
            return result.success

        except Exception as e:
            duration = time.time() - start
            logger.error(f"Phase {phase_name.value} crashed: {e}", exc_info=True)

            result = PhaseResult(
                phase=phase_name,
                success=False,
                duration_seconds=duration,
                errors=[f"Unhandled exception: {e}"],
            )
            self.report.phases.append(result)
            return False

    def _halt(self, reason: str):
        """Halt pipeline with reason."""
        logger.critical(f"Pipeline HALTED: {reason}")
        print(f"\n  HALTED: {reason}")
        self.report.halted = True
        self.report.halt_reason = reason

    def _finalize(self) -> RunReport:
        """Finalize the run report and append to the run ledger."""
        self.report.end_time = datetime.now()
        self.report.overall_success = (
            not self.report.halted
            and all(pr.success for pr in self.report.phases)
        )

        # Update pipeline health timing
        self.pipeline_health.duration_seconds = self.report.duration_seconds

        # Append to run ledger
        try:
            ledger_status = "HALTED" if self.report.halted else (
                "SUCCESS" if self.report.overall_success else "PARTIAL"
            )
            self._ledger.append(
                self.pipeline_health,
                status=ledger_status,
                description=f"{self.run_type.value} run",
            )
            logger.info(f"Run recorded in ledger: {self.run_id}")
        except Exception as e:
            logger.warning(f"Could not write to run ledger: {e}")

        # Print summary
        status = "SUCCESS" if self.report.overall_success else "COMPLETED WITH ISSUES"
        if self.report.halted:
            status = "HALTED"

        print(f"\n{'='*60}")
        print(f"  Pipeline Agent: {status}")
        print(f"  Pipeline health: {self.pipeline_health.health_score:.2f}")
        print(f"  Duration: {self.report.duration_seconds:.1f}s")
        for pr in self.report.phases:
            icon = "OK" if pr.success else "FAIL"
            print(f"    {pr.phase.value:<12} {icon} ({pr.duration_seconds:.1f}s)")
        print(f"{'='*60}\n")

        return self.report


def _ext(fmt: str) -> str:
    """Map format name to file extension."""
    return {"excel": "xlsx", "csv": "csv", "parquet": "parquet", "json": "json"}.get(
        fmt, fmt
    )
