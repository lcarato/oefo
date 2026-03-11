"""
Storage layer for OEFO data.

Provides abstraction over file-based storage for observations and raw documents.
Supports reading/writing Parquet files and JSON-based document indexing.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date

import pandas as pd

from ..models import (
    Observation,
    RawDocument,
    DocumentStatus,
    SourceType,
)


# ============================================================================
# ObservationStore: Parquet-based storage for observations
# ============================================================================

class ObservationStore:
    """
    Storage layer for observations using Parquet format.

    Provides methods to:
    - Add/append observations to the data store
    - Retrieve all observations as DataFrame
    - Query observations with filters
    - Export to CSV and Excel formats
    """

    def __init__(self, storage_dir: Union[str, Path]):
        """
        Initialize the observation store.

        Args:
            storage_dir: Directory path where Parquet files will be stored.
                        Will be created if it doesn't exist.
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.parquet_path = self.storage_dir / "observations.parquet"

    def add_observations(self, observations: List[Union[Observation, Dict[str, Any]]]) -> int:
        """
        Add one or more observations to the store.

        Args:
            observations: List of Observation models or dictionaries to add.
                         If dictionaries, they will be validated as Observation models.

        Returns:
            int: Number of observations added.

        Raises:
            ValueError: If observations cannot be validated.
        """
        if not observations:
            return 0

        # Convert to Observation models if needed
        validated_obs = []
        for obs in observations:
            if isinstance(obs, dict):
                try:
                    obs = Observation(**obs)
                except Exception as e:
                    raise ValueError(f"Failed to validate observation: {e}")
            validated_obs.append(obs)

        # Convert to DataFrame
        obs_dicts = [obs.model_dump() for obs in validated_obs]
        new_df = pd.DataFrame(obs_dicts)

        # Load existing data and append
        if self.parquet_path.exists():
            existing_df = pd.read_parquet(self.parquet_path)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        # Write back to Parquet
        combined_df.to_parquet(self.parquet_path, index=False)

        return len(validated_obs)

    def get_all(self) -> pd.DataFrame:
        """
        Retrieve all observations as a DataFrame.

        Returns:
            pd.DataFrame: All observations in the store. Empty DataFrame if no data.
        """
        if not self.parquet_path.exists():
            return pd.DataFrame()

        return pd.read_parquet(self.parquet_path)

    def query(self, filters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Query observations with optional filtering.

        Supports filtering by column equality or column membership in a list.

        Args:
            filters: Dictionary of column names to filter values.
                    Examples:
                        {"country": "USA"}
                        {"technology_l2": ["Solar", "Wind"]}
                        {"year_of_observation": 2023}

        Returns:
            pd.DataFrame: Filtered observations.

        Raises:
            ValueError: If filter columns don't exist in the data.
        """
        df = self.get_all()

        if not filters:
            return df

        if df.empty:
            return df

        for col, value in filters.items():
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not found in observation data")

            if isinstance(value, (list, tuple)):
                df = df[df[col].isin(value)]
            else:
                df = df[df[col] == value]

        return df

    def export_csv(self, output_path: Union[str, Path]) -> str:
        """
        Export all observations to CSV format.

        Args:
            output_path: Path where CSV file will be written.

        Returns:
            str: Path to the exported file.
        """
        output_path = Path(output_path)
        df = self.get_all()
        df.to_csv(output_path, index=False)
        return str(output_path)

    def export_excel(self, output_path: Union[str, Path]) -> str:
        """
        Export all observations to Excel format.

        Args:
            output_path: Path where Excel file will be written.

        Returns:
            str: Path to the exported file.
        """
        output_path = Path(output_path)
        df = self.get_all()
        df.to_excel(output_path, index=False, sheet_name="observations")
        return str(output_path)

    def delete_observation(self, observation_id: str) -> bool:
        """
        Delete an observation by ID.

        Args:
            observation_id: The observation_id to delete.

        Returns:
            bool: True if an observation was deleted, False if not found.
        """
        df = self.get_all()

        if df.empty:
            return False

        initial_len = len(df)
        df = df[df["observation_id"] != observation_id]

        if len(df) < initial_len:
            df.to_parquet(self.parquet_path, index=False)
            return True

        return False

    def update_observation(self, observation: Union[Observation, Dict[str, Any]]) -> bool:
        """
        Update an observation by replacing matching observation_id.

        Args:
            observation: Updated Observation model or dictionary.

        Returns:
            bool: True if observation was updated, False if not found.
        """
        if isinstance(observation, dict):
            observation = Observation(**observation)

        df = self.get_all()

        if df.empty:
            return False

        if observation.observation_id not in df["observation_id"].values:
            return False

        # Remove old record and add new one
        df = df[df["observation_id"] != observation.observation_id]
        new_df = pd.DataFrame([observation.model_dump()])
        combined_df = pd.concat([df, new_df], ignore_index=True)
        combined_df.to_parquet(self.parquet_path, index=False)

        return True

    def count(self) -> int:
        """
        Get the total number of observations in the store.

        Returns:
            int: Count of observations.
        """
        df = self.get_all()
        return len(df)


# ============================================================================
# DocumentStore: JSON-based index for raw document metadata
# ============================================================================

class DocumentStore:
    """
    Storage layer for raw document metadata using JSON-based indexing.

    Maintains an index of downloaded documents and their properties
    to support deduplication and audit trails.

    Storage structure:
        storage_dir/
            documents_index.json  (main index)
            documents/
                {document_id}/
                    metadata.json
    """

    def __init__(self, storage_dir: Union[str, Path]):
        """
        Initialize the document store.

        Args:
            storage_dir: Directory path where document metadata will be stored.
                        Will be created if it doesn't exist.
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir = self.storage_dir / "documents"
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_dir / "documents_index.json"

    def _load_index(self) -> Dict[str, Any]:
        """Load the document index from disk."""
        if self.index_path.exists():
            with open(self.index_path, "r") as f:
                return json.load(f)
        return {"documents": {}, "by_url": {}, "by_hash": {}}

    def _save_index(self, index: Dict[str, Any]) -> None:
        """Save the document index to disk."""
        with open(self.index_path, "w") as f:
            json.dump(index, f, indent=2, default=str)

    def register_document(self, document: Union[RawDocument, Dict[str, Any]]) -> str:
        """
        Register a new document in the store.

        Args:
            document: RawDocument model or dictionary.

        Returns:
            str: The document_id of the registered document.
        """
        if isinstance(document, dict):
            document = RawDocument(**document)

        # Load index
        index = self._load_index()

        # Add to index
        doc_dict = document.model_dump(mode="json")
        index["documents"][document.document_id] = doc_dict
        index["by_url"][document.source_url] = document.document_id
        index["by_hash"][document.content_hash] = document.document_id

        # Save metadata to disk
        doc_metadata_dir = self.documents_dir / document.document_id
        doc_metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata_file = doc_metadata_dir / "metadata.json"

        with open(metadata_file, "w") as f:
            json.dump(doc_dict, f, indent=2, default=str)

        # Save index
        self._save_index(index)

        return document.document_id

    def get_by_url(self, url: str) -> Optional[RawDocument]:
        """
        Retrieve a document by its source URL.

        Args:
            url: The source URL to look up.

        Returns:
            RawDocument if found, None otherwise.
        """
        index = self._load_index()
        doc_id = index["by_url"].get(url)

        if not doc_id:
            return None

        doc_dict = index["documents"].get(doc_id)
        if not doc_dict:
            return None

        return RawDocument(**doc_dict)

    def get_by_hash(self, content_hash: str) -> Optional[RawDocument]:
        """
        Retrieve a document by its content hash.

        Args:
            content_hash: SHA-256 hash of document content.

        Returns:
            RawDocument if found, None otherwise.
        """
        index = self._load_index()
        doc_id = index["by_hash"].get(content_hash)

        if not doc_id:
            return None

        doc_dict = index["documents"].get(doc_id)
        if not doc_dict:
            return None

        return RawDocument(**doc_dict)

    def get_by_id(self, document_id: str) -> Optional[RawDocument]:
        """
        Retrieve a document by its ID.

        Args:
            document_id: The document ID.

        Returns:
            RawDocument if found, None otherwise.
        """
        index = self._load_index()
        doc_dict = index["documents"].get(document_id)

        if not doc_dict:
            return None

        return RawDocument(**doc_dict)

    def is_duplicate(self, url: Optional[str] = None, content_hash: Optional[str] = None) -> bool:
        """
        Check if a document already exists in the store.

        Args:
            url: URL to check (optional).
            content_hash: Content hash to check (optional).

        Returns:
            bool: True if document exists by either URL or hash.
        """
        if not url and not content_hash:
            return False

        index = self._load_index()

        if url and url in index["by_url"]:
            return True

        if content_hash and content_hash in index["by_hash"]:
            return True

        return False

    def get_all(self) -> List[RawDocument]:
        """
        Retrieve all documents from the store.

        Returns:
            List[RawDocument]: All documents.
        """
        index = self._load_index()
        documents = []

        for doc_dict in index["documents"].values():
            try:
                documents.append(RawDocument(**doc_dict))
            except Exception as e:
                print(f"Warning: Failed to parse document {doc_dict.get('document_id')}: {e}")

        return documents

    def get_by_source_type(self, source_type: SourceType) -> List[RawDocument]:
        """
        Retrieve all documents of a specific source type.

        Args:
            source_type: The SourceType to filter by.

        Returns:
            List[RawDocument]: Matching documents.
        """
        index = self._load_index()
        documents = []

        for doc_dict in index["documents"].values():
            if doc_dict.get("source_type") == source_type:
                try:
                    documents.append(RawDocument(**doc_dict))
                except Exception as e:
                    print(f"Warning: Failed to parse document {doc_dict.get('document_id')}: {e}")

        return documents

    def get_by_status(self, status: DocumentStatus) -> List[RawDocument]:
        """
        Retrieve all documents with a specific status.

        Args:
            status: The DocumentStatus to filter by.

        Returns:
            List[RawDocument]: Matching documents.
        """
        index = self._load_index()
        documents = []

        for doc_dict in index["documents"].values():
            if doc_dict.get("download_status") == status:
                try:
                    documents.append(RawDocument(**doc_dict))
                except Exception as e:
                    print(f"Warning: Failed to parse document {doc_dict.get('document_id')}: {e}")

        return documents

    def update_document(self, document: Union[RawDocument, Dict[str, Any]]) -> bool:
        """
        Update an existing document's metadata.

        Args:
            document: Updated RawDocument model or dictionary.

        Returns:
            bool: True if document was updated, False if not found.
        """
        if isinstance(document, dict):
            document = RawDocument(**document)

        index = self._load_index()

        if document.document_id not in index["documents"]:
            return False

        doc_dict = document.model_dump(mode="json")
        index["documents"][document.document_id] = doc_dict

        # Update URL/hash mappings
        old_doc = index["documents"].get(document.document_id, {})
        if old_doc and old_doc.get("source_url") != document.source_url:
            old_url = old_doc.get("source_url")
            if old_url and old_url in index["by_url"]:
                del index["by_url"][old_url]
        index["by_url"][document.source_url] = document.document_id

        if old_doc and old_doc.get("content_hash") != document.content_hash:
            old_hash = old_doc.get("content_hash")
            if old_hash and old_hash in index["by_hash"]:
                del index["by_hash"][old_hash]
        index["by_hash"][document.content_hash] = document.document_id

        # Save metadata file
        doc_metadata_dir = self.documents_dir / document.document_id
        doc_metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata_file = doc_metadata_dir / "metadata.json"

        with open(metadata_file, "w") as f:
            json.dump(doc_dict, f, indent=2, default=str)

        self._save_index(index)
        return True

    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the store.

        Args:
            document_id: The document ID to delete.

        Returns:
            bool: True if document was deleted, False if not found.
        """
        index = self._load_index()

        if document_id not in index["documents"]:
            return False

        doc_dict = index["documents"].pop(document_id)

        # Remove from URL/hash indices
        if doc_dict.get("source_url") in index["by_url"]:
            del index["by_url"][doc_dict["source_url"]]
        if doc_dict.get("content_hash") in index["by_hash"]:
            del index["by_hash"][doc_dict["content_hash"]]

        # Save index
        self._save_index(index)

        return True

    def count(self) -> int:
        """
        Get the total number of documents in the store.

        Returns:
            int: Count of documents.
        """
        index = self._load_index()
        return len(index["documents"])


# ============================================================================
# Helper utility functions
# ============================================================================

def compute_content_hash(content: Union[str, bytes]) -> str:
    """
    Compute SHA-256 hash of document content.

    Args:
        content: Document content as string or bytes.

    Returns:
        str: Hex-encoded SHA-256 hash.
    """
    if isinstance(content, str):
        content = content.encode("utf-8")

    return hashlib.sha256(content).hexdigest()


def serialize_for_json(obj: Any) -> Any:
    """
    Serialize objects for JSON storage.

    Handles:
    - date and datetime objects -> ISO strings
    - Enum values -> their values
    - Other objects -> string representation

    Args:
        obj: Object to serialize.

    Returns:
        JSON-serializable representation.
    """
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif hasattr(obj, "value"):  # Enum
        return obj.value
    else:
        return str(obj)


# ============================================================================
# Export public API
# ============================================================================

__all__ = [
    "ObservationStore",
    "DocumentStore",
    "compute_content_hash",
    "serialize_for_json",
]
