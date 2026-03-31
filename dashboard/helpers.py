"""
Shared utility helpers for the business dashboard.

This file keeps small presentation-friendly helpers out of the main app:
CSV loading, number formatting, and simple display utilities. Analytical
logic lives in dashboard/logic.py.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"


def load_dashboard_data(output_dir: Path = OUTPUT_DIR) -> dict[str, pd.DataFrame]:
    """Load the generated CSV files used by the dashboard."""

    tables = {}
    for table_name in [
        "fact_orders",
        "fact_events",
        "dim_product",
        "dim_customer",
        "fact_promotions",
        "fact_invoices",
    ]:
        tables[table_name] = pd.read_csv(output_dir / f"{table_name}.csv")
    return tables


def format_currency(value: float) -> str:
    """Format numeric values as business-friendly SEK strings."""

    if pd.isna(value):
        return "-"
    return f"SEK {value:,.0f}"


def format_percent(value: float) -> str:
    """Format ratio values as readable percentages."""

    if pd.isna(value):
        return "-"
    return f"{value:.1%}"
