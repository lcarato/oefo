"""
Runtime Settings and Configuration for OEFO Data Pipeline

This module manages all runtime configuration including:
- OCR and vision model parameters
- API and model selection
- Directory paths for data storage
- API keys and authentication
- Language and scraping settings

Settings are loaded from environment variables with sensible defaults.
Sensitive credentials should be stored in a .env file (git-ignored).
"""

import os
from datetime import date
from pathlib import Path
from typing import Dict, Optional

# =============================================================================
# Document Processing - OCR and Vision Settings
# =============================================================================

OCR_DPI: int = 300
"""
Dots per inch (DPI) for Tesseract OCR processing.
Higher DPI improves accuracy but increases processing time.
300 DPI is standard for document digitization.
"""

VISION_DPI: int = 250
"""
DPI for vision model preprocessing.
Slightly lower than OCR to balance accuracy and cost.
Claude Vision API is optimized for 250-300 DPI range.
"""

VISION_MODEL: str = os.environ.get("OEFO_VISION_MODEL", "claude-sonnet-4-20250514")
"""
Default model for vision-based extraction from PDFs.
Supports any model name understood by the configured LLM provider.
Examples: 'claude-sonnet-4-20250514', 'gpt-4o', 'gemini-2.0-flash', 'llava:13b'
"""

QC_MODEL: str = os.environ.get("OEFO_QC_MODEL", "claude-sonnet-4-20250514")
"""
Default model for quality control and validation checks.
"""

LLM_PROVIDER: str = os.environ.get("OEFO_LLM_PROVIDER", "anthropic")
"""
Preferred LLM provider. Options: 'anthropic', 'openai', 'ollama'.
Fallback chain: Anthropic Claude → OpenAI GPT 5.4 → Ollama (Qwen 3.5 local).
"""

LLM_FALLBACK_ORDER: list = os.environ.get(
    "OEFO_LLM_FALLBACK_ORDER", "anthropic,openai,ollama"
).split(",")
"""
Fallback order for LLM providers. Comma-separated list.
Default: anthropic → openai (GPT 5.4) → ollama (Qwen 3.5).
"""

OPENAI_API_KEY: Optional[str] = os.environ.get("OPENAI_API_KEY")
"""OpenAI API key (for GPT 5.4 fallback). Optional."""

OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
"""Ollama server URL for Qwen 3.5 local fallback. Optional."""

OLLAMA_DEFAULT_MODEL: str = os.environ.get("OEFO_OLLAMA_MODEL", "qwen3.5")
"""Default Ollama model. Qwen 3.5 provides strong multilingual and reasoning."""

MAX_VISION_PAGES: int = 5
"""
Maximum number of pages to process via vision API per document.
Limits cost and processing time for large PDFs.
Falls back to OCR for pages beyond this threshold.
"""

TESSERACT_LANGUAGES: Dict[str, str] = {
    "eng": "English",
    "fra": "French",
    "deu": "German",
    "spa": "Spanish",
    "por": "Portuguese",
    "ita": "Italian",
    "jpn": "Japanese",
    "zho": "Chinese (Simplified)",
    "rus": "Russian",
    "ara": "Arabic",
}
"""
Mapping of Tesseract language codes to language names.
Default: English. Add language codes as needed for multi-language support.
"""

# =============================================================================
# Directory Structure
# =============================================================================
# All paths are absolute and can be overridden via environment variables.

BASE_DIR: Path = Path(
    os.environ.get(
        "OEFO_BASE_DIR",
        Path.cwd(),
    )
)
"""
Base directory for the OEFO project.
Defaults to the current working directory.
Can be overridden via OEFO_BASE_DIR environment variable.
"""

DATA_DIR: Path = Path(os.environ.get("OEFO_DATA_DIR", BASE_DIR / "data"))
"""
Root directory for all data storage.
"""

RAW_DIR: Path = Path(os.environ.get("OEFO_RAW_DIR", DATA_DIR / "raw"))
"""
Directory for raw, unprocessed documents (PDFs, HTML, etc.).
"""

EXTRACTED_DIR: Path = Path(
    os.environ.get("OEFO_EXTRACTED_DIR", DATA_DIR / "extracted")
)
"""
Directory for extracted, unvalidated data (JSON).
"""

FINAL_DIR: Path = Path(os.environ.get("OEFO_FINAL_DIR", DATA_DIR / "final"))
"""
Directory for validated, QC-approved final data.
"""

LOGS_DIR: Path = Path(os.environ.get("OEFO_LOGS_DIR", BASE_DIR / "logs"))
"""
Directory for application logs.
"""

CACHE_DIR: Path = Path(os.environ.get("OEFO_CACHE_DIR", BASE_DIR / ".cache"))
"""
Directory for caching (OCR outputs, model responses, etc.).
"""

def ensure_directories() -> None:
    """Create required directories if they don't exist.

    Call this explicitly before pipeline operations rather than at import time,
    to avoid side effects when simply importing the config module.
    """
    for directory in [DATA_DIR, RAW_DIR, EXTRACTED_DIR, FINAL_DIR, LOGS_DIR, CACHE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

# =============================================================================
# API Keys and Authentication
# =============================================================================
# Load from environment; fail gracefully if not present.

ANTHROPIC_API_KEY: Optional[str] = os.environ.get("ANTHROPIC_API_KEY")
"""
Anthropic API key for Claude model access.
Required for vision and QC models.
Must be set in environment or .env file.
"""

ANTHROPIC_ORG_ID: Optional[str] = os.environ.get("ANTHROPIC_ORG_ID")
"""
Optional Anthropic organization ID for billing/access control.
"""

# =============================================================================
# Scraping and Web Access
# =============================================================================

USER_AGENT: str = os.environ.get(
    "OEFO_USER_AGENT",
    (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 "
        "+OEFO (Energy Finance Observatory Data Collection; "
        "contact: research@openenergyfinance.org)"
    ),
)
"""
User agent string for HTTP requests.
Identifies the OEFO pipeline to servers for ethical data collection.
"""

REQUEST_TIMEOUT: int = int(os.environ.get("OEFO_REQUEST_TIMEOUT", "30"))
"""
Timeout (seconds) for HTTP requests to external sources.
"""

RETRY_MAX_ATTEMPTS: int = int(os.environ.get("OEFO_RETRY_MAX_ATTEMPTS", "3"))
"""
Maximum number of retries for failed HTTP requests.
"""

RETRY_BACKOFF_FACTOR: float = float(
    os.environ.get("OEFO_RETRY_BACKOFF_FACTOR", "1.5")
)
"""
Exponential backoff factor for retry delays (seconds).
E.g., with factor 1.5: 1s, 1.5s, 2.25s for retries 1, 2, 3.
"""

# =============================================================================
# Logging Configuration
# =============================================================================

LOG_LEVEL: str = os.environ.get("OEFO_LOG_LEVEL", "INFO")
"""
Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
"""

LOG_FORMAT: str = (
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
"""
Log message format.
"""

# =============================================================================
# Processing Options
# =============================================================================

ENABLE_CACHING: bool = os.environ.get("OEFO_ENABLE_CACHING", "true").lower() == "true"
"""
Enable caching of API responses and OCR outputs.
"""

ENABLE_PARALLEL_PROCESSING: bool = (
    os.environ.get("OEFO_ENABLE_PARALLEL_PROCESSING", "true").lower() == "true"
)
"""
Enable parallel processing of multiple documents.
"""

MAX_WORKERS: int = int(os.environ.get("OEFO_MAX_WORKERS", "4"))
"""
Maximum number of worker threads/processes for parallel operations.
"""

# =============================================================================
# Environment and Debug
# =============================================================================

DEBUG: bool = os.environ.get("OEFO_DEBUG", "false").lower() == "true"
"""
Enable debug mode (verbose logging, no cleanup of temp files, etc.).
"""

DRY_RUN: bool = os.environ.get("OEFO_DRY_RUN", "false").lower() == "true"
"""
If True, simulate operations without writing to disk or calling external APIs.
Useful for testing pipelines.
"""

# =============================================================================
# Damodaran Benchmark Settings
# =============================================================================

DAMODARAN_DATA_AS_OF: date = date(2025, 1, 1)
"""Date as of which the Damodaran benchmark data was last refreshed."""

DAMODARAN_OUTLIER_THRESHOLD_SD: float = 2.0
"""Flag observations >2 standard deviations from Damodaran sector benchmark."""

# =============================================================================
# Helper Functions
# =============================================================================


def get_config() -> Dict[str, any]:
    """
    Return all current configuration settings as a dictionary.
    Useful for logging/debugging and passing config to submodules.

    Returns:
        Dictionary of all configuration parameters.
    """
    return {
        "OCR_DPI": OCR_DPI,
        "VISION_DPI": VISION_DPI,
        "VISION_MODEL": VISION_MODEL,
        "QC_MODEL": QC_MODEL,
        "MAX_VISION_PAGES": MAX_VISION_PAGES,
        "DATA_DIR": str(DATA_DIR),
        "RAW_DIR": str(RAW_DIR),
        "EXTRACTED_DIR": str(EXTRACTED_DIR),
        "FINAL_DIR": str(FINAL_DIR),
        "LOGS_DIR": str(LOGS_DIR),
        "CACHE_DIR": str(CACHE_DIR),
        "ANTHROPIC_API_KEY": "***" if ANTHROPIC_API_KEY else None,
        "OPENAI_API_KEY": "***" if OPENAI_API_KEY else None,
        "USER_AGENT": USER_AGENT,
        "REQUEST_TIMEOUT": REQUEST_TIMEOUT,
        "RETRY_MAX_ATTEMPTS": RETRY_MAX_ATTEMPTS,
        "RETRY_BACKOFF_FACTOR": RETRY_BACKOFF_FACTOR,
        "LOG_LEVEL": LOG_LEVEL,
        "ENABLE_CACHING": ENABLE_CACHING,
        "ENABLE_PARALLEL_PROCESSING": ENABLE_PARALLEL_PROCESSING,
        "MAX_WORKERS": MAX_WORKERS,
        "DEBUG": DEBUG,
        "DRY_RUN": DRY_RUN,
    }


def validate_api_keys() -> bool:
    """
    Validate that required API keys are present.

    Returns:
        True if all required keys are set, False otherwise.
    """
    configured = []
    if ANTHROPIC_API_KEY:
        configured.append("anthropic")
    if OPENAI_API_KEY:
        configured.append("openai")

    if configured:
        print(f"INFO: Cloud LLM credentials configured for {', '.join(configured)}.")
        return True

    if LLM_PROVIDER.lower() == "ollama":
        print("INFO: OEFO_LLM_PROVIDER=ollama; no cloud API key required.")
        return True

    print(
        "ERROR: No LLM credentials configured. Set ANTHROPIC_API_KEY or "
        "OPENAI_API_KEY, or set OEFO_LLM_PROVIDER=ollama for local-only use."
    )
    return False


def validate_directories() -> bool:
    """
    Validate that all required directories exist and are writable.

    Returns:
        True if all directories are valid, False otherwise.
    """
    for directory in [DATA_DIR, RAW_DIR, EXTRACTED_DIR, FINAL_DIR, LOGS_DIR, CACHE_DIR]:
        if not directory.exists():
            print(f"ERROR: Directory {directory} does not exist.")
            return False
        if not os.access(directory, os.W_OK):
            print(f"ERROR: Directory {directory} is not writable.")
            return False
    return True


def print_config() -> None:
    """Pretty-print all configuration settings (with sensitive values masked)."""
    config = get_config()
    print("\n" + "=" * 70)
    print("OEFO Configuration Settings")
    print("=" * 70)
    for key, value in sorted(config.items()):
        print(f"{key:.<40} {value}")
    print("=" * 70 + "\n")
