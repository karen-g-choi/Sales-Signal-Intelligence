"""
Dimension and reference table builders.

This file converts the fixed seed dictionaries into clean pandas DataFrames
 and adds a few derived fields such as dealer launch week and ISO year-week.
"""

from __future__ import annotations

import pandas as pd

from data_generation.seeds import (
    CUSTOMERS,
    EFFORT_RULES,
    END_DATE,
    PRODUCTS,
    PRODUCT_VEHICLE_MAP,
    REGIONS,
    START_DATE,
    VEHICLE_MODELS,
)


def build_calendar() -> pd.DataFrame:
    """Create the daily calendar dimension for the full project date range."""

    calendar = pd.DataFrame({"date": pd.date_range(START_DATE, END_DATE, freq="D")})
    iso = calendar["date"].dt.isocalendar()
    calendar["year"] = calendar["date"].dt.year
    calendar["month"] = calendar["date"].dt.month
    calendar["week_number"] = iso.week.astype(int)
    calendar["year_week"] = iso.year.astype(str) + "-W" + iso.week.astype(str).str.zfill(2)
    return calendar


def build_regions() -> pd.DataFrame:
    """Return the region master table exactly from the seed data."""

    return pd.DataFrame(REGIONS)


def build_customers() -> pd.DataFrame:
    """Return the customer master and add the ISO week of each dealer launch."""

    customers = pd.DataFrame(CUSTOMERS)
    customers["dealer_launch_date"] = pd.to_datetime(customers["dealer_launch_date"])
    launch_iso = customers["dealer_launch_date"].dt.isocalendar()
    customers["dealer_launch_week"] = (
        launch_iso.year.astype(str) + "-W" + launch_iso.week.astype(str).str.zfill(2)
    )
    ordered_columns = [
        "customer_id",
        "customer_name",
        "customer_contact_name",
        "delivery_address",
        "region_id",
        "order_cycle",
        "channel_type",
        "dealer_launch_date",
        "dealer_launch_week",
        "customer_status",
        "customer_size",
        "size_multiplier",
        "baseline_volatility",
        "role_description",
    ]
    return customers[ordered_columns]


def build_products() -> pd.DataFrame:
    """Return the product master with scenario roles and commercial settings."""

    columns = [
        "product_id",
        "product_name",
        "category_l1",
        "category_l2",
        "substitute_type",
        "platform_type",
        "effort_type",
        "effort_rule_id",
        "lifecycle_stage",
        "scenario_role",
        "base_daily_demand",
        "list_price",
    ]
    return pd.DataFrame(PRODUCTS)[columns]


def build_vehicle_models() -> pd.DataFrame:
    """Return the fixed vehicle model master table."""

    return pd.DataFrame(VEHICLE_MODELS)


def build_product_vehicle_bridge() -> pd.DataFrame:
    """Expand the strict product-to-vehicle mapping into a bridge table."""

    rows = []
    for product_id, vehicle_ids in PRODUCT_VEHICLE_MAP.items():
        for vehicle_model_id in vehicle_ids:
            rows.append(
                {
                    "product_id": product_id,
                    "vehicle_model_id": vehicle_model_id,
                }
            )
    return pd.DataFrame(rows)


def build_effort_rules() -> pd.DataFrame:
    """Return the effort classification reference table."""

    return pd.DataFrame(EFFORT_RULES)


def build_dimension_tables() -> dict[str, pd.DataFrame]:
    """Build all required dimensions, bridges, and reference tables."""

    return {
        "dim_calendar": build_calendar(),
        "dim_region": build_regions(),
        "dim_customer": build_customers(),
        "dim_product": build_products(),
        "dim_vehicle_model": build_vehicle_models(),
        "bridge_product_vehicle_model": build_product_vehicle_bridge(),
        "ref_effort_classification_rules": build_effort_rules(),
    }
