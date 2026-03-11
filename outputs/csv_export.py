"""
CSV and Parquet export functionality for OEFO observations.

Exports observations in various formats suitable for different workflows:
- CSV for spreadsheet applications and simple analysis
- Parquet for efficient storage and big data workflows
- JSON for web applications and APIs
"""

from pathlib import Path
from typing import Optional
import json

import pandas as pd


def export_csv(
    df: pd.DataFrame,
    path: str,
    index: bool = False,
    encoding: str = 'utf-8'
) -> Path:
    """
    Export observations to CSV format.

    Args:
        df: DataFrame containing observations
        path: Path where CSV should be saved
        index: Whether to include DataFrame index in CSV
        encoding: Character encoding (default: utf-8)

    Returns:
        Path to the created CSV file

    Raises:
        ValueError: If DataFrame is empty
        IOError: If file cannot be written
    """
    if df.empty:
        raise ValueError("Cannot export empty DataFrame to CSV")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        df.to_csv(path, index=index, encoding=encoding)
        return path
    except IOError as e:
        raise IOError(f"Failed to write CSV to {path}: {e}")


def export_parquet(
    df: pd.DataFrame,
    path: str,
    compression: str = 'snappy',
    index: bool = False
) -> Path:
    """
    Export observations to Parquet format.

    Parquet is an efficient columnar format ideal for:
    - Large datasets
    - Data science workflows
    - Preserving data types
    - Querying subsets of columns

    Args:
        df: DataFrame containing observations
        path: Path where Parquet file should be saved
        compression: Compression algorithm ('snappy', 'gzip', 'brotli', or None)
        index: Whether to include DataFrame index

    Returns:
        Path to the created Parquet file

    Raises:
        ValueError: If DataFrame is empty
        ImportError: If pyarrow is not installed
        IOError: If file cannot be written
    """
    if df.empty:
        raise ValueError("Cannot export empty DataFrame to Parquet")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        df.to_parquet(path, compression=compression, index=index, engine='pyarrow')
        return path
    except ImportError:
        raise ImportError(
            "pyarrow is required for Parquet export. "
            "Install with: pip install pyarrow"
        )
    except IOError as e:
        raise IOError(f"Failed to write Parquet to {path}: {e}")


def export_json(
    df: pd.DataFrame,
    path: str,
    orient: str = 'records',
    indent: Optional[int] = 2,
    date_format: str = 'iso'
) -> Path:
    """
    Export observations to JSON format.

    Useful for web applications, APIs, and JavaScript workflows.

    Args:
        df: DataFrame containing observations
        path: Path where JSON file should be saved
        orient: JSON format orientation:
            - 'records': List of row objects (default)
            - 'split': Dict with 'index', 'columns', 'data'
            - 'index': Dict with row indices as keys
            - 'columns': Dict with column names as keys
            - 'values': Nested list representation
        indent: Number of spaces for indentation (None for compact)
        date_format: How to format datetime objects ('iso' for ISO 8601)

    Returns:
        Path to the created JSON file

    Raises:
        ValueError: If DataFrame is empty
        IOError: If file cannot be written
    """
    if df.empty:
        raise ValueError("Cannot export empty DataFrame to JSON")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        df.to_json(
            path,
            orient=orient,
            indent=indent,
            date_format=date_format
        )
        return path
    except IOError as e:
        raise IOError(f"Failed to write JSON to {path}: {e}")


def batch_export(
    df: pd.DataFrame,
    output_dir: str,
    base_name: str = 'observations',
    formats: Optional[list[str]] = None
) -> dict[str, Path]:
    """
    Export observations to multiple formats simultaneously.

    Args:
        df: DataFrame containing observations
        output_dir: Directory where files should be saved
        base_name: Base name for output files (without extension)
        formats: List of formats to export ('csv', 'parquet', 'json')
                 Default: all formats

    Returns:
        Dictionary mapping format names to output paths

    Raises:
        ValueError: If DataFrame is empty or invalid formats specified
    """
    if df.empty:
        raise ValueError("Cannot export empty DataFrame")

    if formats is None:
        formats = ['csv', 'parquet', 'json']

    valid_formats = {'csv', 'parquet', 'json'}
    invalid = set(formats) - valid_formats
    if invalid:
        raise ValueError(f"Invalid formats: {invalid}. Must be one of {valid_formats}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    if 'csv' in formats:
        csv_path = output_dir / f"{base_name}.csv"
        results['csv'] = export_csv(df, str(csv_path))

    if 'parquet' in formats:
        parquet_path = output_dir / f"{base_name}.parquet"
        results['parquet'] = export_parquet(df, str(parquet_path))

    if 'json' in formats:
        json_path = output_dir / f"{base_name}.json"
        results['json'] = export_json(df, str(json_path))

    return results
