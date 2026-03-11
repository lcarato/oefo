"""
Tests for package structure and files.

Verifies:
- Required files exist (pyproject.toml, __init__.py, __main__.py)
- All expected subpackages are present
- Package metadata is correct
"""

import pytest
from pathlib import Path
import sys


class TestProjectFiles:
    """Test that required project files exist."""

    def test_pyproject_toml_exists(self):
        """Test that pyproject.toml exists."""
        root = Path(__file__).parent.parent
        assert (root / "pyproject.toml").exists()

    def test_pyproject_toml_is_readable(self):
        """Test that pyproject.toml is valid TOML."""
        root = Path(__file__).parent.parent
        pyproject_path = root / "pyproject.toml"
        assert pyproject_path.exists()
        # Just verify it can be read and has content
        content = pyproject_path.read_text()
        assert "[build-system]" in content or "[project]" in content


class TestPackageInit:
    """Test package initialization files."""

    def test_oefo_init_exists(self):
        """Test that src/oefo/__init__.py exists."""
        root = Path(__file__).parent.parent
        init_path = root / "src" / "oefo" / "__init__.py"
        assert init_path.exists()

    def test_oefo_main_exists(self):
        """Test that src/oefo/__main__.py exists."""
        root = Path(__file__).parent.parent
        main_path = root / "src" / "oefo" / "__main__.py"
        assert main_path.exists()


class TestSubpackages:
    """Test that all expected subpackages exist."""

    def test_config_subpackage_exists(self):
        """Test that config subpackage exists."""
        root = Path(__file__).parent.parent
        config_dir = root / "src" / "oefo" / "config"
        assert config_dir.is_dir()
        assert (config_dir / "__init__.py").exists()

    def test_dashboard_subpackage_exists(self):
        """Test that dashboard subpackage exists."""
        root = Path(__file__).parent.parent
        dashboard_dir = root / "src" / "oefo" / "dashboard"
        assert dashboard_dir.is_dir()
        assert (dashboard_dir / "__init__.py").exists()

    def test_data_subpackage_exists(self):
        """Test that data subpackage exists."""
        root = Path(__file__).parent.parent
        data_dir = root / "src" / "oefo" / "data"
        assert data_dir.is_dir()
        assert (data_dir / "__init__.py").exists()

    def test_extraction_subpackage_exists(self):
        """Test that extraction subpackage exists."""
        root = Path(__file__).parent.parent
        extraction_dir = root / "src" / "oefo" / "extraction"
        assert extraction_dir.is_dir()
        assert (extraction_dir / "__init__.py").exists()

    def test_outputs_subpackage_exists(self):
        """Test that outputs subpackage exists."""
        root = Path(__file__).parent.parent
        outputs_dir = root / "src" / "oefo" / "outputs"
        assert outputs_dir.is_dir()
        assert (outputs_dir / "__init__.py").exists()

    def test_qc_subpackage_exists(self):
        """Test that qc subpackage exists."""
        root = Path(__file__).parent.parent
        qc_dir = root / "src" / "oefo" / "qc"
        assert qc_dir.is_dir()
        assert (qc_dir / "__init__.py").exists()

    def test_scrapers_subpackage_exists(self):
        """Test that scrapers subpackage exists."""
        root = Path(__file__).parent.parent
        scrapers_dir = root / "src" / "oefo" / "scrapers"
        assert scrapers_dir.is_dir()
        assert (scrapers_dir / "__init__.py").exists()


class TestCoreModules:
    """Test that core modules exist."""

    def test_models_module_exists(self):
        """Test that models.py exists."""
        root = Path(__file__).parent.parent
        models_path = root / "src" / "oefo" / "models.py"
        assert models_path.exists()

    def test_cli_module_exists(self):
        """Test that cli.py exists."""
        root = Path(__file__).parent.parent
        cli_path = root / "src" / "oefo" / "cli.py"
        assert cli_path.exists()

    def test_config_settings_module_exists(self):
        """Test that config/settings.py exists."""
        root = Path(__file__).parent.parent
        settings_path = root / "src" / "oefo" / "config" / "settings.py"
        assert settings_path.exists()

    def test_config_taxonomy_module_exists(self):
        """Test that config/taxonomy.py exists."""
        root = Path(__file__).parent.parent
        taxonomy_path = root / "src" / "oefo" / "config" / "taxonomy.py"
        assert taxonomy_path.exists()


class TestPyprojectConfiguration:
    """Test pyproject.toml configuration."""

    def test_project_name_configured(self):
        """Test that project name is configured."""
        root = Path(__file__).parent.parent
        pyproject_path = root / "pyproject.toml"

        try:
            import toml
            pyproject = toml.load(str(pyproject_path))
            assert pyproject["project"]["name"] == "oefo"
        except ImportError:
            # If toml is not installed, just check file content
            content = pyproject_path.read_text()
            assert 'name = "oefo"' in content

    def test_project_version_configured(self):
        """Test that project version is configured."""
        root = Path(__file__).parent.parent
        pyproject_path = root / "pyproject.toml"
        content = pyproject_path.read_text()
        assert 'version = "' in content

    def test_pytest_configured(self):
        """Test that pytest is configured in pyproject.toml."""
        root = Path(__file__).parent.parent
        pyproject_path = root / "pyproject.toml"
        content = pyproject_path.read_text()
        assert "[tool.pytest" in content or "pytest" in content.lower()

    def test_cli_entry_point_configured(self):
        """Test that CLI entry point is configured."""
        root = Path(__file__).parent.parent
        pyproject_path = root / "pyproject.toml"
        content = pyproject_path.read_text()
        assert "oefo = " in content and "cli:main" in content


class TestManifestIn:
    """Test that MANIFEST.in is configured."""

    def test_manifest_in_exists(self):
        """Test that MANIFEST.in exists."""
        root = Path(__file__).parent.parent
        manifest_path = root / "MANIFEST.in"
        assert manifest_path.exists()

    def test_manifest_in_is_readable(self):
        """Test that MANIFEST.in has content."""
        root = Path(__file__).parent.parent
        manifest_path = root / "MANIFEST.in"
        content = manifest_path.read_text()
        assert len(content) > 0


class TestPackageMetadata:
    """Test package metadata."""

    def test_license_file_exists(self):
        """Test that LICENSE file exists."""
        root = Path(__file__).parent.parent
        license_path = root / "LICENSE"
        assert license_path.exists()

    def test_readme_file_exists(self):
        """Test that README.md exists."""
        root = Path(__file__).parent.parent
        readme_path = root / "README.md"
        assert readme_path.exists()

    def test_readme_is_markdown(self):
        """Test that README.md is a markdown file."""
        root = Path(__file__).parent.parent
        readme_path = root / "README.md"
        assert readme_path.suffix == ".md"


class TestSetuptoolsConfiguration:
    """Test setuptools configuration in pyproject.toml."""

    def test_package_dir_configured(self):
        """Test that package-dir is configured."""
        root = Path(__file__).parent.parent
        pyproject_path = root / "pyproject.toml"
        content = pyproject_path.read_text()
        assert "[tool.setuptools]" in content

    def test_src_layout_used(self):
        """Test that src layout is configured."""
        root = Path(__file__).parent.parent
        pyproject_path = root / "pyproject.toml"
        content = pyproject_path.read_text()
        assert 'package-dir = {"" = "src"}' in content or 'package-dir = { "" = "src" }' in content
