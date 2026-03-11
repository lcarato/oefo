"""
Tests that all key imports work and basic module structure is sound.

Verifies:
- All major modules can be imported
- Version information is present
- Package structure is valid
"""

import pytest


class TestMainImports:
    """Test that main package imports work."""

    def test_import_oefo(self):
        """Test importing the main oefo module."""
        import oefo
        assert oefo is not None

    def test_import_oefo_cli(self):
        """Test importing CLI module."""
        import oefo.cli
        assert oefo.cli is not None

    def test_import_oefo_data_storage(self):
        """Test importing data storage module."""
        import oefo.data.storage
        assert oefo.data.storage is not None

    def test_import_oefo_dashboard_server(self):
        """Test importing dashboard server module."""
        import oefo.dashboard.server
        assert oefo.dashboard.server is not None

    def test_import_oefo_models(self):
        """Test importing models module."""
        import oefo.models
        assert oefo.models is not None

    def test_import_oefo_extraction(self):
        """Test importing extraction module."""
        import oefo.extraction
        assert oefo.extraction is not None

    def test_import_oefo_qc(self):
        """Test importing QC module."""
        import oefo.qc
        assert oefo.qc is not None

    def test_import_oefo_outputs(self):
        """Test importing outputs module."""
        import oefo.outputs
        assert oefo.outputs is not None

    def test_import_oefo_scrapers(self):
        """Test importing scrapers module."""
        import oefo.scrapers
        assert oefo.scrapers is not None

    def test_import_oefo_config(self):
        """Test importing config module."""
        import oefo.config
        assert oefo.config is not None

    def test_import_oefo_config_settings(self):
        """Test importing settings module."""
        import oefo.config.settings
        assert oefo.config.settings is not None

    def test_import_oefo_config_taxonomy(self):
        """Test importing taxonomy module."""
        import oefo.config.taxonomy
        assert oefo.config.taxonomy is not None


class TestVersionInfo:
    """Test that version information is present and valid."""

    def test_version_exists(self):
        """Test that __version__ is defined."""
        import oefo
        assert hasattr(oefo, "__version__")

    def test_version_is_string(self):
        """Test that __version__ is a string."""
        import oefo
        assert isinstance(oefo.__version__, str)

    def test_version_format(self):
        """Test that __version__ follows semantic versioning."""
        import oefo
        # Should be in format X.Y.Z
        parts = oefo.__version__.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_author_defined(self):
        """Test that __author__ is defined."""
        import oefo
        assert hasattr(oefo, "__author__")

    def test_description_defined(self):
        """Test that __description__ is defined."""
        import oefo
        assert hasattr(oefo, "__description__")


class TestLazyImports:
    """Test lazy import mechanism for backward compatibility."""

    def test_lazy_import_extraction_pipeline(self):
        """Test that ExtractionPipeline can be lazy-imported."""
        import oefo
        # This should trigger __getattr__ and lazy import
        assert hasattr(oefo, "ExtractionPipeline")

    def test_lazy_import_qc_agent(self):
        """Test that QCAgent can be lazy-imported."""
        import oefo
        assert hasattr(oefo, "QCAgent")

    def test_lazy_import_export_functions(self):
        """Test that export functions can be lazy-imported."""
        import oefo
        assert hasattr(oefo, "export_csv")
        assert hasattr(oefo, "export_parquet")
        assert hasattr(oefo, "export_json")

    def test_lazy_import_invalid_attribute_raises(self):
        """Test that accessing invalid attribute raises AttributeError."""
        import oefo
        with pytest.raises(AttributeError, match="has no attribute"):
            _ = oefo.nonexistent_attribute
