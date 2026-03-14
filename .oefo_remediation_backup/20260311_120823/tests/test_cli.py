"""
Tests for CLI argument parsing and command structure.

Verifies:
- Parser creation and configuration
- Version and help flags
- Subcommand parsing
- Argument validation
- Default values
"""

import pytest
import argparse
from oefo.cli import create_parser


class TestParserCreation:
    """Test parser creation and configuration."""

    def test_create_parser_returns_argument_parser(self):
        """Test that create_parser returns an ArgumentParser."""
        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_parser_has_prog_name(self):
        """Test that parser has correct program name."""
        parser = create_parser()
        assert parser.prog == "oefo"

    def test_parser_description_exists(self):
        """Test that parser has a description."""
        parser = create_parser()
        assert parser.description is not None
        assert "Energy" in parser.description or "finance" in parser.description


class TestVersionFlag:
    """Test --version flag."""

    def test_version_flag_exists(self):
        """Test that --version flag is recognized."""
        parser = create_parser()
        # Version is implemented via action='version', can't directly test output
        # but we can verify parsing doesn't fail with --version
        try:
            parser.parse_args(["--version"])
        except SystemExit:
            # argparse exits on --version, which is expected behavior
            pass


class TestHelpFlag:
    """Test --help flag."""

    def test_help_flag_exists(self):
        """Test that --help flag is recognized."""
        parser = create_parser()
        try:
            parser.parse_args(["--help"])
        except SystemExit:
            # argparse exits on --help, which is expected behavior
            pass


class TestScrapeCommand:
    """Test scrape subcommand parsing."""

    def test_scrape_command_exists(self):
        """Test that scrape subcommand is available."""
        parser = create_parser()
        args = parser.parse_args(["scrape", "ifc"])
        assert args.command == "scrape"
        assert args.source == "ifc"

    def test_scrape_valid_sources(self):
        """Test that all valid sources are accepted."""
        parser = create_parser()
        valid_sources = ["ifc", "ebrd", "gcf", "sec", "aneel", "aer", "ofgem", "ferc", "all"]
        for source in valid_sources:
            args = parser.parse_args(["scrape", source])
            assert args.source == source

    def test_scrape_invalid_source_fails(self):
        """Test that invalid source raises error."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["scrape", "invalid"])

    def test_scrape_with_output_dir(self):
        """Test scrape with --output-dir flag."""
        parser = create_parser()
        args = parser.parse_args(["scrape", "ifc", "--output-dir", "/tmp/data"])
        assert args.output_dir == "/tmp/data"

    def test_scrape_with_force_flag(self):
        """Test scrape with --force flag."""
        parser = create_parser()
        args = parser.parse_args(["scrape", "ifc", "--force"])
        assert args.force is True

    def test_scrape_has_handler(self):
        """Test that scrape command has associated handler."""
        parser = create_parser()
        args = parser.parse_args(["scrape", "ifc"])
        assert hasattr(args, "func")


class TestExtractCommand:
    """Test extract subcommand parsing."""

    def test_extract_command_exists(self):
        """Test that extract subcommand is available."""
        parser = create_parser()
        args = parser.parse_args(["extract", "test.pdf", "--source-type", "regulatory"])
        assert args.command == "extract"
        assert args.pdf_path == "test.pdf"

    def test_extract_requires_source_type(self):
        """Test that extract requires --source-type."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["extract", "test.pdf"])

    def test_extract_valid_source_types(self):
        """Test that valid source types are accepted."""
        parser = create_parser()
        valid_types = ["regulatory", "dfi", "corporate", "bond"]
        for source_type in valid_types:
            args = parser.parse_args(["extract", "test.pdf", "--source-type", source_type])
            assert args.source_type == source_type

    def test_extract_with_output(self):
        """Test extract with --output flag."""
        parser = create_parser()
        args = parser.parse_args(["extract", "test.pdf", "--source-type", "regulatory", "--output", "results.json"])
        assert args.output == "results.json"

    def test_extract_with_language(self):
        """Test extract with --language flag."""
        parser = create_parser()
        args = parser.parse_args(["extract", "test.pdf", "--source-type", "regulatory", "--language", "pt"])
        assert args.language == "pt"

    def test_extract_has_handler(self):
        """Test that extract command has associated handler."""
        parser = create_parser()
        args = parser.parse_args(["extract", "test.pdf", "--source-type", "regulatory"])
        assert hasattr(args, "func")


class TestExtractBatchCommand:
    """Test extract-batch subcommand parsing."""

    def test_extract_batch_command_exists(self):
        """Test that extract-batch subcommand is available."""
        parser = create_parser()
        args = parser.parse_args(["extract-batch", "/data/pdfs", "--source-type", "regulatory"])
        assert args.command == "extract-batch"
        assert args.directory == "/data/pdfs"

    def test_extract_batch_requires_source_type(self):
        """Test that extract-batch requires --source-type."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["extract-batch", "/data/pdfs"])

    def test_extract_batch_with_pattern(self):
        """Test extract-batch with --pattern flag."""
        parser = create_parser()
        args = parser.parse_args(["extract-batch", "/data", "--source-type", "regulatory", "--pattern", "*.pdf"])
        assert args.pattern == "*.pdf"

    def test_extract_batch_with_parallel(self):
        """Test extract-batch with --parallel flag."""
        parser = create_parser()
        args = parser.parse_args(["extract-batch", "/data", "--source-type", "regulatory", "--parallel", "8"])
        assert args.parallel == 8

    def test_extract_batch_has_handler(self):
        """Test that extract-batch command has associated handler."""
        parser = create_parser()
        args = parser.parse_args(["extract-batch", "/data", "--source-type", "regulatory"])
        assert hasattr(args, "func")


class TestQCCommand:
    """Test qc subcommand parsing."""

    def test_qc_command_exists(self):
        """Test that qc subcommand is available."""
        parser = create_parser()
        args = parser.parse_args(["qc"])
        assert args.command == "qc"

    def test_qc_rules_only_flag(self):
        """Test qc with --rules-only flag."""
        parser = create_parser()
        args = parser.parse_args(["qc", "--rules-only"])
        assert args.rules_only is True

    def test_qc_full_flag(self):
        """Test qc with --full flag."""
        parser = create_parser()
        args = parser.parse_args(["qc", "--full"])
        assert args.full is True

    def test_qc_with_input(self):
        """Test qc with --input flag."""
        parser = create_parser()
        args = parser.parse_args(["qc", "--input", "/data/extracted"])
        assert args.input == "/data/extracted"

    def test_qc_with_output(self):
        """Test qc with --output flag."""
        parser = create_parser()
        args = parser.parse_args(["qc", "--output", "/data/qc_report.json"])
        assert args.output == "/data/qc_report.json"

    def test_qc_has_handler(self):
        """Test that qc command has associated handler."""
        parser = create_parser()
        args = parser.parse_args(["qc"])
        assert hasattr(args, "func")


class TestExportCommand:
    """Test export subcommand parsing."""

    def test_export_command_exists(self):
        """Test that export subcommand is available."""
        parser = create_parser()
        args = parser.parse_args(["export", "--format", "excel", "--output", "results.xlsx"])
        assert args.command == "export"

    def test_export_requires_format(self):
        """Test that export requires --format."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["export", "--output", "results.xlsx"])

    def test_export_requires_output(self):
        """Test that export requires --output."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["export", "--format", "excel"])

    def test_export_valid_formats(self):
        """Test that all valid export formats are accepted."""
        parser = create_parser()
        valid_formats = ["excel", "csv", "parquet", "json"]
        for fmt in valid_formats:
            args = parser.parse_args(["export", "--format", fmt, "--output", f"results.{fmt}"])
            assert args.format == fmt

    def test_export_with_filter(self):
        """Test export with --filter flag."""
        parser = create_parser()
        args = parser.parse_args(["export", "--format", "csv", "--output", "results.csv", "--filter", "country=='BRA'"])
        assert args.filter == "country=='BRA'"

    def test_export_has_handler(self):
        """Test that export command has associated handler."""
        parser = create_parser()
        args = parser.parse_args(["export", "--format", "excel", "--output", "results.xlsx"])
        assert hasattr(args, "func")


class TestDashboardCommand:
    """Test dashboard subcommand parsing."""

    def test_dashboard_command_exists(self):
        """Test that dashboard subcommand is available."""
        parser = create_parser()
        args = parser.parse_args(["dashboard"])
        assert args.command == "dashboard"

    def test_dashboard_default_host(self):
        """Test dashboard default host."""
        parser = create_parser()
        args = parser.parse_args(["dashboard"])
        assert args.host == "127.0.0.1"

    def test_dashboard_default_port(self):
        """Test dashboard default port."""
        parser = create_parser()
        args = parser.parse_args(["dashboard"])
        assert args.port == 8765

    def test_dashboard_with_custom_port(self):
        """Test dashboard with custom port."""
        parser = create_parser()
        args = parser.parse_args(["dashboard", "--port", "9000"])
        assert args.port == 9000

    def test_dashboard_with_custom_host(self):
        """Test dashboard with custom host."""
        parser = create_parser()
        args = parser.parse_args(["dashboard", "--host", "0.0.0.0"])
        assert args.host == "0.0.0.0"

    def test_dashboard_public_flag(self):
        """Test dashboard with --public flag."""
        parser = create_parser()
        args = parser.parse_args(["dashboard", "--public"])
        assert args.public is True

    def test_dashboard_has_handler(self):
        """Test that dashboard command has associated handler."""
        parser = create_parser()
        args = parser.parse_args(["dashboard"])
        assert hasattr(args, "func")


class TestStatusCommand:
    """Test status subcommand parsing."""

    def test_status_command_exists(self):
        """Test that status subcommand is available."""
        parser = create_parser()
        args = parser.parse_args(["status"])
        assert args.command == "status"

    def test_status_with_detailed_flag(self):
        """Test status with --detailed flag."""
        parser = create_parser()
        args = parser.parse_args(["status", "--detailed"])
        assert args.detailed is True

    def test_status_has_handler(self):
        """Test that status command has associated handler."""
        parser = create_parser()
        args = parser.parse_args(["status"])
        assert hasattr(args, "func")


class TestConfigCommand:
    """Test config subcommand parsing."""

    def test_config_command_exists(self):
        """Test that config subcommand is available."""
        parser = create_parser()
        args = parser.parse_args(["config"])
        assert args.command == "config"

    def test_config_with_validate_flag(self):
        """Test config with --validate flag."""
        parser = create_parser()
        args = parser.parse_args(["config", "--validate"])
        assert args.validate is True

    def test_config_has_handler(self):
        """Test that config command has associated handler."""
        parser = create_parser()
        args = parser.parse_args(["config"])
        assert hasattr(args, "func")


class TestGlobalFlags:
    """Test global flags across all commands."""

    def test_verbose_flag(self):
        """Test --verbose flag (must come before subcommand)."""
        parser = create_parser()
        args = parser.parse_args(["--verbose", "status"])
        assert args.verbose is True

    def test_verbose_short_flag(self):
        """Test -v short flag (must come before subcommand)."""
        parser = create_parser()
        args = parser.parse_args(["-v", "status"])
        assert args.verbose is True

    def test_config_file_flag(self):
        """Test --config flag (must come before subcommand)."""
        parser = create_parser()
        args = parser.parse_args(["--config", "/etc/oefo.conf", "status"])
        assert args.config == "/etc/oefo.conf"
