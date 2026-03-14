"""
Tests for OEFO Pipeline Agent.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from oefo.agent import (
    PipelineAgent,
    RunType,
    PhaseName,
    PhaseResult,
    RunReport,
    DFI_SOURCES,
    REGULATORY_SOURCES,
    CORPORATE_SOURCES,
    ALL_SOURCES,
    SOURCE_TYPE_MAP,
    _update_latest_symlink,
)


class TestRunType:
    """Test RunType enumeration."""

    def test_run_type_values(self):
        assert RunType.FULL.value == "full"
        assert RunType.WEEKLY_DFI.value == "weekly_dfi"
        assert RunType.MONTHLY_REGULATORY.value == "monthly_regulatory"
        assert RunType.QUARTERLY_SEC.value == "quarterly_sec"
        assert RunType.QC_ONLY.value == "qc_only"
        assert RunType.EXPORT_ONLY.value == "export_only"

    def test_run_type_from_string(self):
        assert RunType("full") == RunType.FULL
        assert RunType("weekly_dfi") == RunType.WEEKLY_DFI


class TestPhaseResult:
    """Test PhaseResult dataclass."""

    def test_default_values(self):
        result = PhaseResult(
            phase=PhaseName.PREFLIGHT,
            success=True,
            duration_seconds=1.5,
        )
        assert result.phase == PhaseName.PREFLIGHT
        assert result.success is True
        assert result.duration_seconds == 1.5
        assert result.details == {}
        assert result.errors == []
        assert result.warnings == []

    def test_with_errors(self):
        result = PhaseResult(
            phase=PhaseName.SCRAPE,
            success=False,
            duration_seconds=5.0,
            errors=["Source IFC failed"],
            warnings=["Slow network"],
        )
        assert len(result.errors) == 1
        assert len(result.warnings) == 1


class TestRunReport:
    """Test RunReport dataclass."""

    def test_to_text(self):
        report = RunReport(
            run_id="test-001",
            run_type=RunType.FULL,
            start_time=datetime(2025, 1, 1, 12, 0, 0),
            end_time=datetime(2025, 1, 1, 12, 5, 0),
            overall_success=True,
        )
        text = report.to_text()
        assert "test-001" in text
        assert "full" in text
        assert "SUCCESS" in text

    def test_to_dict(self):
        report = RunReport(
            run_id="test-002",
            run_type=RunType.WEEKLY_DFI,
            start_time=datetime(2025, 1, 1),
        )
        d = report.to_dict()
        assert d["run_id"] == "test-002"
        assert d["run_type"] == "weekly_dfi"
        assert d["overall_success"] is False

    def test_duration(self):
        report = RunReport(
            run_id="test-003",
            run_type=RunType.FULL,
            start_time=datetime(2025, 1, 1, 12, 0, 0),
            end_time=datetime(2025, 1, 1, 12, 2, 30),
        )
        assert report.duration_seconds == 150.0

    def test_halted_report(self):
        report = RunReport(
            run_id="test-004",
            run_type=RunType.FULL,
            start_time=datetime(2025, 1, 1),
            halted=True,
            halt_reason="API keys missing",
        )
        text = report.to_text()
        assert "HALTED" in text
        assert "API keys missing" in text


class TestSourceMappings:
    """Test source groupings and mappings."""

    def test_all_sources_union(self):
        assert set(ALL_SOURCES) == set(DFI_SOURCES + REGULATORY_SOURCES + CORPORATE_SOURCES)

    def test_source_type_map_complete(self):
        for source in ALL_SOURCES:
            assert source in SOURCE_TYPE_MAP

    def test_dfi_sources_map_to_dfi(self):
        for source in DFI_SOURCES:
            assert SOURCE_TYPE_MAP[source] == "dfi"

    def test_regulatory_sources_map_to_regulatory(self):
        for source in REGULATORY_SOURCES:
            assert SOURCE_TYPE_MAP[source] == "regulatory"

    def test_corporate_sources_map_to_corporate(self):
        for source in CORPORATE_SOURCES:
            assert SOURCE_TYPE_MAP[source] == "corporate"


class TestPipelineAgentInit:
    """Test PipelineAgent initialization."""

    def test_default_full_run(self):
        agent = PipelineAgent()
        assert agent.run_type == RunType.FULL
        assert set(agent.sources) == set(ALL_SOURCES)
        assert agent.qc_full is True
        assert agent.skip_scrape is False
        assert agent.skip_export is False

    def test_weekly_dfi_run(self):
        agent = PipelineAgent(run_type=RunType.WEEKLY_DFI)
        assert set(agent.sources) == set(DFI_SOURCES)

    def test_monthly_regulatory_run(self):
        agent = PipelineAgent(run_type=RunType.MONTHLY_REGULATORY)
        assert set(agent.sources) == set(REGULATORY_SOURCES)

    def test_quarterly_sec_run(self):
        agent = PipelineAgent(run_type=RunType.QUARTERLY_SEC)
        assert set(agent.sources) == set(CORPORATE_SOURCES)

    def test_qc_only_skips_scrape_and_extract(self):
        agent = PipelineAgent(run_type=RunType.QC_ONLY)
        assert agent.skip_scrape is True
        assert agent.skip_extract is True
        assert agent.skip_qc is False

    def test_export_only_skips_everything(self):
        agent = PipelineAgent(run_type=RunType.EXPORT_ONLY)
        assert agent.skip_scrape is True
        assert agent.skip_extract is True
        assert agent.skip_qc is True
        assert agent.skip_export is False

    def test_custom_sources(self):
        agent = PipelineAgent(sources=["ifc", "sec"])
        assert agent.sources == ["ifc", "sec"]

    def test_custom_export_formats(self):
        agent = PipelineAgent(export_formats=["json"])
        assert agent.export_formats == ["json"]

    def test_run_id_generated(self):
        agent = PipelineAgent()
        assert agent.run_id.startswith("run_")

    def test_report_initialized(self):
        agent = PipelineAgent()
        assert agent.report.run_type == RunType.FULL
        assert agent.report.start_time is not None
        assert agent.report.overall_success is False

    def test_run_scoped_dirs_initially_none(self):
        """Run-scoped directories should be None before preflight."""
        agent = PipelineAgent()
        assert agent._extracted_run_dir is None
        assert agent._final_run_dir is None
        assert agent._outputs_run_dir is None


class TestRunScopedDirectories:
    """Test that every run creates unique directories and never overwrites."""

    def test_preflight_creates_run_dirs(self):
        """Pre-flight should create run-scoped subdirectories."""
        with patch("oefo.agent.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024**3)
            agent = PipelineAgent(run_type=RunType.EXPORT_ONLY, skip_export=True)
            result = agent._preflight_checks()

            assert result.phase == PhaseName.PREFLIGHT
            assert "oefo_version" in result.details

            # Run-scoped directories should now be set
            assert agent._extracted_run_dir is not None
            assert agent._final_run_dir is not None
            assert agent._outputs_run_dir is not None

            # They should contain the run_id
            assert agent.run_id in str(agent._extracted_run_dir)
            assert agent.run_id in str(agent._final_run_dir)
            assert agent.run_id in str(agent._outputs_run_dir)

            # They should actually exist on disk
            assert agent._extracted_run_dir.is_dir()
            assert agent._final_run_dir.is_dir()
            assert agent._outputs_run_dir.is_dir()

    def test_two_runs_produce_different_dirs(self):
        """Two agent instances should never share output directories."""
        import time
        agent1 = PipelineAgent()
        time.sleep(1.1)  # Ensure different second in timestamp
        agent2 = PipelineAgent()

        assert agent1.run_id != agent2.run_id

    def test_latest_symlink_helper(self, tmp_path):
        """_update_latest_symlink should create an atomic symlink."""
        run_dir = tmp_path / "run_001"
        run_dir.mkdir()

        _update_latest_symlink(tmp_path, run_dir)

        link = tmp_path / "latest"
        assert link.is_symlink()
        assert link.resolve() == run_dir.resolve()

    def test_latest_symlink_updates(self, tmp_path):
        """A second call should atomically replace the symlink."""
        run1 = tmp_path / "run_001"
        run1.mkdir()
        run2 = tmp_path / "run_002"
        run2.mkdir()

        _update_latest_symlink(tmp_path, run1)
        assert (tmp_path / "latest").resolve() == run1.resolve()

        _update_latest_symlink(tmp_path, run2)
        assert (tmp_path / "latest").resolve() == run2.resolve()

    def test_preflight_details_include_dirs(self):
        """Preflight details should report the run-scoped paths."""
        with patch("oefo.agent.shutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(free=10 * 1024**3)
            agent = PipelineAgent()
            result = agent._preflight_checks()
            assert "extracted_dir" in result.details
            assert "final_dir" in result.details
            assert "outputs_dir" in result.details
            assert agent.run_id in result.details["extracted_dir"]


class TestPipelineAgentHalt:
    """Test halt behavior."""

    def test_halt_sets_report_fields(self):
        agent = PipelineAgent()
        agent._halt("Test halt reason")
        assert agent.report.halted is True
        assert agent.report.halt_reason == "Test halt reason"

    def test_finalize_marks_halted_run(self):
        agent = PipelineAgent()
        agent._halt("Something broke")
        report = agent._finalize()
        assert report.overall_success is False
        assert report.halted is True


class TestCLIRunCommand:
    """Test that the CLI 'run' command is registered."""

    def test_run_command_exists(self):
        from oefo.cli import create_parser
        parser = create_parser()
        # Parse a 'run' command — should not raise
        args = parser.parse_args(["run"])
        assert args.command == "run"
        assert args.type == "full"

    def test_run_command_with_sources(self):
        from oefo.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["run", "--sources", "ifc,ebrd", "--type", "weekly_dfi"])
        assert args.sources == "ifc,ebrd"
        assert args.type == "weekly_dfi"

    def test_run_command_skip_flags(self):
        from oefo.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["run", "--skip-scrape", "--skip-export", "--qc-rules-only"])
        assert args.skip_scrape is True
        assert args.skip_export is True
        assert args.qc_rules_only is True
