"""
Visualization generators for OEFO observations.

Creates publication-quality charts and maps:
- WACC heatmaps by technology and country
- Cost of debt (Kd) distributions
- Time series of WACC changes
- Global coverage maps
"""

from pathlib import Path
from typing import Optional

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np


def plot_wacc_heatmap(
    df: pd.DataFrame,
    output_path: str,
    figsize: tuple = (14, 8),
    cmap: str = 'RdYlGn_r'
) -> Path:
    """
    Create a WACC heatmap showing technology × country matrix.

    Args:
        df: Observations DataFrame containing 'technology', 'country', and WACC column
        output_path: Path to save the figure
        figsize: Figure size as (width, height) in inches
        cmap: Matplotlib colormap name

    Returns:
        Path to the saved figure

    Raises:
        ValueError: If required columns are missing
        KeyError: If WACC column not found
    """
    required_cols = ['technology', 'country']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")

    wacc_col = 'wacc_percent' if 'wacc_percent' in df.columns else 'wacc'
    if wacc_col not in df.columns:
        raise KeyError(f"Could not find WACC column (tried 'wacc_percent' and 'wacc')")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create pivot table
    pivot = pd.pivot_table(
        df,
        values=wacc_col,
        index='technology',
        columns='country',
        aggfunc='mean'
    )

    # Create heatmap
    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(pivot.values, cmap=cmap, aspect='auto')

    # Set ticks and labels
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_xticklabels(pivot.columns, rotation=45, ha='right')
    ax.set_yticklabels(pivot.index)

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('WACC (%)', rotation=270, labelpad=20)

    # Add text annotations
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            value = pivot.values[i, j]
            if not np.isnan(value):
                text = ax.text(j, i, f'{value:.1f}%',
                              ha="center", va="center", color="black", fontsize=8)

    ax.set_title('Weighted Average Cost of Capital by Technology and Country', fontsize=14, fontweight='bold')
    ax.set_xlabel('Country', fontsize=12)
    ax.set_ylabel('Technology', fontsize=12)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return output_path


def plot_kd_distribution(
    df: pd.DataFrame,
    technology: str,
    output_path: str,
    figsize: tuple = (10, 6),
    bins: int = 30
) -> Path:
    """
    Create a distribution plot of cost of debt (Kd) for a specific technology.

    Args:
        df: Observations DataFrame containing 'technology' and 'kd' or 'cost_of_debt' column
        technology: Technology to filter for
        output_path: Path to save the figure
        figsize: Figure size as (width, height) in inches
        bins: Number of histogram bins

    Returns:
        Path to the saved figure

    Raises:
        ValueError: If technology not found in data
        KeyError: If Kd column not found
    """
    kd_col = 'kd' if 'kd' in df.columns else 'cost_of_debt'
    if kd_col not in df.columns:
        raise KeyError(f"Could not find Kd column (tried 'kd' and 'cost_of_debt')")

    if 'technology' not in df.columns:
        raise ValueError("DataFrame must contain 'technology' column")

    tech_data = df[df['technology'] == technology]
    if tech_data.empty:
        raise ValueError(f"No data found for technology: {technology}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    kd_values = tech_data[kd_col].dropna()

    if len(kd_values) == 0:
        raise ValueError(f"No valid Kd values found for {technology}")

    fig, ax = plt.subplots(figsize=figsize)

    # Create histogram
    ax.hist(kd_values, bins=bins, color='steelblue', edgecolor='black', alpha=0.7)

    # Add statistics
    mean_kd = kd_values.mean()
    median_kd = kd_values.median()
    std_kd = kd_values.std()

    ax.axvline(mean_kd, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_kd:.2f}%')
    ax.axvline(median_kd, color='green', linestyle='--', linewidth=2, label=f'Median: {median_kd:.2f}%')

    ax.set_title(f'Cost of Debt (Kd) Distribution - {technology}', fontsize=14, fontweight='bold')
    ax.set_xlabel('Cost of Debt (%)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Add text box with statistics
    stats_text = f'N = {len(kd_values)}\nStd Dev = {std_kd:.2f}%\nMin = {kd_values.min():.2f}%\nMax = {kd_values.max():.2f}%'
    ax.text(0.98, 0.97, stats_text, transform=ax.transAxes,
           fontsize=10, verticalalignment='top', horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return output_path


def plot_time_series(
    df: pd.DataFrame,
    country: Optional[str] = None,
    technology: Optional[str] = None,
    output_path: str = 'wacc_timeseries.png',
    figsize: tuple = (12, 6)
) -> Path:
    """
    Create a time series plot of WACC changes over time.

    Args:
        df: Observations DataFrame containing 'date' and WACC column
        country: Filter to specific country (optional)
        technology: Filter to specific technology (optional)
        output_path: Path to save the figure
        figsize: Figure size as (width, height) in inches

    Returns:
        Path to the saved figure

    Raises:
        ValueError: If no date column or required filters not found
    """
    if 'date' not in df.columns:
        raise ValueError("DataFrame must contain 'date' column")

    wacc_col = 'wacc_percent' if 'wacc_percent' in df.columns else 'wacc'
    if wacc_col not in df.columns:
        raise KeyError(f"Could not find WACC column (tried 'wacc_percent' and 'wacc')")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Filter data
    filtered_df = df.copy()
    if country and 'country' in df.columns:
        filtered_df = filtered_df[filtered_df['country'] == country]
    if technology and 'technology' in df.columns:
        filtered_df = filtered_df[filtered_df['technology'] == technology]

    if filtered_df.empty:
        raise ValueError(f"No data found for country={country}, technology={technology}")

    # Convert date and sort
    filtered_df['date'] = pd.to_datetime(filtered_df['date'])
    filtered_df = filtered_df.sort_values('date')

    # Group by date and calculate mean WACC
    ts_data = filtered_df.groupby('date')[wacc_col].agg(['mean', 'std', 'count']).reset_index()

    fig, ax = plt.subplots(figsize=figsize)

    # Plot mean with confidence interval
    ax.plot(ts_data['date'], ts_data['mean'], color='steelblue', linewidth=2, label='Mean WACC')
    ax.fill_between(
        ts_data['date'],
        ts_data['mean'] - ts_data['std'],
        ts_data['mean'] + ts_data['std'],
        alpha=0.3, color='steelblue', label='±1 Std Dev'
    )

    # Labels and title
    title_parts = []
    if country:
        title_parts.append(f"{country}")
    if technology:
        title_parts.append(f"{technology}")
    if not title_parts:
        title_parts.append("All")
    title_parts.append("WACC Over Time")

    ax.set_title(' - '.join(title_parts), fontsize=14, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('WACC (%)', fontsize=12)
    ax.legend()
    ax.grid(alpha=0.3)

    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return output_path


def plot_coverage_map(
    df: pd.DataFrame,
    output_path: str = 'coverage_map.png',
    figsize: tuple = (14, 8)
) -> Path:
    """
    Create a simple world map showing data coverage by country.

    Note: Requires basemap or geopandas for full functionality.
    This version creates a bar chart of coverage by country.

    Args:
        df: Observations DataFrame containing 'country' column
        output_path: Path to save the figure
        figsize: Figure size as (width, height) in inches

    Returns:
        Path to the saved figure

    Raises:
        ValueError: If no country column found
    """
    if 'country' not in df.columns:
        raise ValueError("DataFrame must contain 'country' column")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Calculate coverage by country
    coverage = df['country'].value_counts().sort_values(ascending=True).tail(20)

    fig, ax = plt.subplots(figsize=figsize)

    # Create horizontal bar chart
    bars = ax.barh(range(len(coverage)), coverage.values, color='steelblue', edgecolor='black')

    # Color bars by intensity
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(bars)))
    for bar, color in zip(bars, colors):
        bar.set_color(color)

    ax.set_yticks(range(len(coverage)))
    ax.set_yticklabels(coverage.index)
    ax.set_xlabel('Number of Observations', fontsize=12)
    ax.set_title('Data Coverage by Country (Top 20)', fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)

    # Add value labels on bars
    for i, v in enumerate(coverage.values):
        ax.text(v + 0.5, i, str(v), va='center', fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return output_path
