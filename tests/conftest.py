"""
Shared pytest fixtures for OEFO test suite.

Provides:
- tmp_data_dir: Temporary directory for test data
- sample_observation: Valid observation data for tests
"""

import pytest
from datetime import date
from pathlib import Path


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Provide a temporary directory for test data."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_observation():
    """Return a dictionary with valid observation data for testing."""
    return {
        "observation_id": "test-obs-001",
        "source_type": "DFI_disclosure",
        "source_institution": "IFC",
        "extraction_date": date(2024, 1, 15),
        "extraction_method": "llm",
        "confidence_level": "high",
        "project_or_entity_name": "Test Solar Farm",
        "country": "BRA",
        "technology_l2": "solar_pv",
        "year_of_observation": 2024,
        "scale": "utility",
        "project_status": "operational",
        "project_capacity_mw": 50.0,
        "project_capex_usd": 50000000.0,
        "kd_nominal": 4.5,
        "ke_nominal": 10.5,
        "leverage_debt_pct": 60.0,
        "leverage_equity_pct": 40.0,
        "wacc_nominal": 7.0,
        "qc_score": 95.0,
        "qc_status": "passed",
        "traceability_level": "full",
    }
