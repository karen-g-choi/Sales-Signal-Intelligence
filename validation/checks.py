"""
Project validation checks.

This file runs simple, readable checks so the synthetic dataset remains
trustworthy. The checks focus on the project brief: required tables,
strict seed mappings, and valid fact relationships.
"""

from __future__ import annotations

import pandas as pd

from data_generation.seeds import END_DATE, EVENT_ORDER, PRODUCT_VEHICLE_MAP, START_DATE


def validate_outputs(tables: dict[str, pd.DataFrame]) -> list[str]:
    """Run lightweight business-rule validations and return human-readable messages."""

    messages = []

    required_tables = [
        "dim_calendar",
        "dim_customer",
        "dim_product",
        "dim_region",
        "dim_vehicle_model",
        "fact_orders",
        "fact_invoices",
        "fact_promotions",
        "fact_recall_warranty_cases",
        "fact_events",
        "bridge_case_vehicle_model",
        "bridge_product_vehicle_model",
        "ref_effort_classification_rules",
    ]
    missing = [name for name in required_tables if name not in tables]
    if missing:
        raise ValueError(f"Missing required tables: {missing}")
    messages.append("All required tables were generated.")

    calendar = tables["dim_calendar"]
    if calendar["date"].min() != pd.Timestamp(START_DATE) or calendar["date"].max() != pd.Timestamp(END_DATE):
        raise ValueError("Calendar date range does not match the requested project period.")
    messages.append("Calendar covers 2024-01-01 to 2025-12-31.")

    bridge = tables["bridge_product_vehicle_model"]
    actual_map = bridge.groupby("product_id")["vehicle_model_id"].apply(list).to_dict()
    for product_id, expected_vehicle_ids in PRODUCT_VEHICLE_MAP.items():
        if sorted(actual_map.get(product_id, [])) != sorted(expected_vehicle_ids):
            raise ValueError(f"Strict product-to-vehicle mapping failed for {product_id}.")
    messages.append("Strict product-to-vehicle mappings match the provided seed data.")

    events = tables["fact_events"]
    actual_order = events["event_layer"].drop_duplicates().sort_values().tolist()
    if actual_order != list(range(1, len(EVENT_ORDER) + 1)):
        raise ValueError("Event layers were not applied in the required strict order.")
    messages.append("All nine event layers exist in the correct order.")

    promotions = tables["fact_promotions"]
    required_promo_columns = [
        "recurring_flag",
        "one_off_campaign_flag",
        "promo_classification_hint",
    ]
    missing_promo_columns = [column for column in required_promo_columns if column not in promotions.columns]
    if missing_promo_columns:
        raise ValueError(f"Promotion traceability columns are missing: {missing_promo_columns}")
    messages.append("Promotion traceability fields are present for future classification logic.")

    mixed_events = events[events["event_type"] == "mixed_ambiguous_behavior"]
    if mixed_events.empty:
        raise ValueError("Mixed ambiguous event rows were not generated.")
    if "review_flag" not in events.columns and "interpretation_hint" not in events.columns:
        raise ValueError("Mixed ambiguous events must include a review or interpretation hint.")
    if "review_flag" in events.columns and not mixed_events["review_flag"].fillna(False).any():
        raise ValueError("Mixed ambiguous event rows must be marked for analyst review.")
    messages.append("Mixed ambiguous events carry an analyst review hint.")

    if "fact_baseline_daily" not in tables:
        raise ValueError("Raw baseline output is missing from generated tables.")
    baseline = tables["fact_baseline_daily"]
    required_baseline_columns = ["category_l1", "category_l2", "effort_type", "substitute_type"]
    missing_baseline_columns = [column for column in required_baseline_columns if column not in baseline.columns]
    if missing_baseline_columns:
        raise ValueError(f"Baseline context columns are missing: {missing_baseline_columns}")
    messages.append("Raw baseline output includes the required product context columns.")

    orders = tables["fact_orders"]
    invoices = tables["fact_invoices"]
    required_order_event_columns = ["event_id", "event_type", "event_layer"]
    missing_order_columns = [column for column in required_order_event_columns if column not in orders.columns]
    if missing_order_columns:
        raise ValueError(f"Order event traceability columns are missing: {missing_order_columns}")
    if not orders["event_id"].notna().any():
        raise ValueError("At least some order rows must carry a non-null event_id for traceability.")
    valid_event_layers = set(range(0, len(EVENT_ORDER) + 1))
    if not set(orders["event_layer"].dropna().astype(int).unique()).issubset(valid_event_layers):
        raise ValueError("fact_orders contains invalid event_layer values.")
    messages.append("Orders carry event traceability fields with valid event_layer values.")

    if "sales_amount" not in orders.columns:
        raise ValueError("fact_orders must include sales_amount.")
    if "sales_amount" not in invoices.columns:
        raise ValueError("fact_invoices must include sales_amount.")

    order_alignment = (orders["sales_amount"] - (orders["quantity"] * orders["net_price"])).abs()
    invoice_alignment = (invoices["sales_amount"] - (invoices["quantity"] * invoices["net_price"])).abs()
    if (order_alignment > 1e-9).any():
        raise ValueError("fact_orders sales_amount does not align with quantity * net_price.")
    if (invoice_alignment > 1e-9).any():
        raise ValueError("fact_invoices sales_amount does not align with quantity * net_price.")

    if (orders["sales_amount"] > 0).mean() < 0.95:
        raise ValueError("Most fact_orders rows should have positive sales_amount.")
    if (invoices["sales_amount"] > 0).mean() < 0.95:
        raise ValueError("Most fact_invoices rows should have positive sales_amount.")
    messages.append("Orders and invoices include valid line-level sales amounts.")

    if not invoices["linked_order_line_id"].isin(orders["order_line_id"]).all():
        raise ValueError("Every invoice line must link to a valid order line.")
    messages.append("Invoice lines link cleanly back to order lines.")

    partial_or_delayed = invoices["status"].isin(["partial", "delayed"]).any()
    if not partial_or_delayed:
        raise ValueError("Invoice fact must include partial fulfillment and delays.")
    messages.append("Invoices include both standard and delayed/partial fulfillment behavior.")

    return messages
