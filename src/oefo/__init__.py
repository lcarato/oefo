"""
OEFO - Open Energy Finance Observatory

A comprehensive toolkit for collecting, analyzing, and publishing energy finance data
from multiple international sources.
"""

__version__ = "0.1.0"
__author__ = "ET Finance"
__description__ = "Open Energy Finance Observatory"

# Lazy imports to avoid heavy dependency loading on import.
# Users should import from subpackages directly:
#   from oefo.scrapers import get_scraper, IFCScraper
#   from oefo.extraction import ExtractionPipeline
#   from oefo.qc import QCAgent
#   from oefo.outputs import ExcelOutputGenerator

__all__ = [
    "__version__",
    "__author__",
    "__description__",
]


def __getattr__(name):
    """Lazy import helper for backward compatibility."""
    _lazy_imports = {
        "get_scraper": "oefo.scrapers",
        "IFCScraper": "oefo.scrapers",
        "EBRDScraper": "oefo.scrapers",
        "GCFScraper": "oefo.scrapers",
        "ExtractionPipeline": "oefo.extraction",
        "ExtractionResult": "oefo.extraction",
        "QCAgent": "oefo.qc",
        "RuleBasedQC": "oefo.qc",
        "ExcelOutputGenerator": "oefo.outputs",
        "export_csv": "oefo.outputs",
        "export_parquet": "oefo.outputs",
        "export_json": "oefo.outputs",
    }
    if name in _lazy_imports:
        import importlib
        module = importlib.import_module(_lazy_imports[name])
        return getattr(module, name)
    raise AttributeError(f"module 'oefo' has no attribute {name!r}")
