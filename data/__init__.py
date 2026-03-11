"""
Data module for the Open Energy Finance Observatory (OEFO) project.

Provides:
- Storage classes for observations and documents (ObservationStore, DocumentStore)
- Utilities for data serialization and hashing
"""

from .storage import (
    ObservationStore,
    DocumentStore,
    compute_content_hash,
    serialize_for_json,
)

__all__ = [
    "ObservationStore",
    "DocumentStore",
    "compute_content_hash",
    "serialize_for_json",
]
