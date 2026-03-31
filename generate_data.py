"""
Run the full synthetic sales data generation pipeline.

This is the entry point for the project. It builds dimensions, generates
baseline demand, applies the event layers, converts demand into line-level
orders and invoices, validates the outputs, and saves every table as CSV.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_generation.dimensions import build_dimension_tables
from logic.baseline import generate_baseline
from logic.events import apply_event_layers
from logic.orders_invoices import build_invoices, build_orders
from validation.checks import validate_outputs


OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def save_tables(tables: dict[str, pd.DataFrame]) -> None:
    """Save every generated table as a CSV file in the output folder."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for table_name, df in tables.items():
        df.to_csv(OUTPUT_DIR / f"{table_name}.csv", index=False)


def save_validation_summary(messages: list[str]) -> None:
    """Save the validation summary so reviewers can inspect it without rerunning code."""

    summary_path = OUTPUT_DIR / "validation_summary.txt"
    summary_text = "Validation summary\n" + "\n".join(f"- {message}" for message in messages) + "\n"
    summary_path.write_text(summary_text, encoding="utf-8")


def main() -> None:
    """Build the full portfolio dataset and print a short validation summary."""

    tables = build_dimension_tables()
    baseline = generate_baseline(
        dim_calendar=tables["dim_calendar"],
        dim_customer=tables["dim_customer"],
        dim_product=tables["dim_product"],
    )
    tables["fact_baseline_daily"] = baseline
    demand, promotions, recall_cases, case_vehicle_bridge, events = apply_event_layers(baseline)
    orders = build_orders(demand, tables["dim_customer"], tables["dim_product"])
    invoices = build_invoices(orders)

    tables["fact_orders"] = orders
    tables["fact_invoices"] = invoices
    tables["fact_promotions"] = promotions
    tables["fact_recall_warranty_cases"] = recall_cases
    tables["fact_events"] = events
    tables["bridge_case_vehicle_model"] = case_vehicle_bridge

    validation_messages = validate_outputs(tables)
    save_tables(tables)
    save_validation_summary(validation_messages)

    print("Generated tables:")
    for table_name, df in tables.items():
        print(f"- {table_name}: {len(df):,} rows")

    print("\nValidation summary:")
    for message in validation_messages:
        print(f"- {message}")


if __name__ == "__main__":
    main()
