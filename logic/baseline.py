"""
Baseline demand generation.

This file creates the raw product-level baseline before any exceptional
events are applied. The baseline is driven by customer-product
relationships, customer size, product demand, light seasonality, and small
controlled variation so the data feels realistic without becoming random
noise.

Important modeling note:
"scenario_role" is included for synthetic data design traceability and
debugging, not as an input for the downstream detection logic.

The baseline is intentionally generated at product level for realism.
Downstream analytical baseline and signal detection should later work at a
more stable customer x category level instead of relying directly on noisy
raw product-level signals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from data_generation.seeds import CUSTOMER_PRODUCT_RELATIONSHIPS, END_DATE, SEED, START_DATE


MONTH_SEASONALITY = {
    1: 1.08,
    2: 1.04,
    3: 1.02,
    4: 1.00,
    5: 0.98,
    6: 0.95,
    7: 0.92,
    8: 0.94,
    9: 1.00,
    10: 1.03,
    11: 1.06,
    12: 1.10,
}

EFFORT_TYPE_VOLATILITY = {
    "effort_less": -0.012,
    "effort_driven": 0.018,
    "mixed": 0.008,
}

SUBSTITUTE_TYPE_VOLATILITY = {
    "none": -0.015,
    "project_specific": -0.008,
    "bundle": 0.004,
    "limited": 0.008,
    "direct": 0.015,
}


def build_customer_product_matrix(
    dim_customer: pd.DataFrame, dim_product: pd.DataFrame
) -> pd.DataFrame:
    """Create the allowed customer-product pairs from the fixed relationship map."""

    customer_info = dim_customer.set_index("customer_id")[
        ["dealer_launch_date", "size_multiplier", "baseline_volatility"]
    ]
    product_info = dim_product.set_index("product_id")[
        [
            "base_daily_demand",
            "list_price",
            "scenario_role",
            "platform_type",
            "category_l1",
            "category_l2",
            "effort_type",
            "substitute_type",
        ]
    ]

    rows = []
    for customer_id, products in CUSTOMER_PRODUCT_RELATIONSHIPS.items():
        for product_id, relationship_strength in products.items():
            rows.append(
                {
                    "customer_id": customer_id,
                    "product_id": product_id,
                    "relationship_strength": relationship_strength,
                    "dealer_launch_date": customer_info.loc[customer_id, "dealer_launch_date"],
                    "size_multiplier": customer_info.loc[customer_id, "size_multiplier"],
                    "baseline_volatility": customer_info.loc[customer_id, "baseline_volatility"],
                    "base_daily_demand": product_info.loc[product_id, "base_daily_demand"],
                    "list_price": product_info.loc[product_id, "list_price"],
                    "scenario_role": product_info.loc[product_id, "scenario_role"],
                    "platform_type": product_info.loc[product_id, "platform_type"],
                    "category_l1": product_info.loc[product_id, "category_l1"],
                    "category_l2": product_info.loc[product_id, "category_l2"],
                    "effort_type": product_info.loc[product_id, "effort_type"],
                    "substitute_type": product_info.loc[product_id, "substitute_type"],
                }
            )
    return pd.DataFrame(rows)


def generate_baseline(
    dim_calendar: pd.DataFrame, dim_customer: pd.DataFrame, dim_product: pd.DataFrame
) -> pd.DataFrame:
    """Build raw daily baseline demand for each allowed customer-product combination."""

    rng = np.random.default_rng(SEED)
    relation_df = build_customer_product_matrix(dim_customer, dim_product)
    calendar = dim_calendar.copy()
    calendar["weekday"] = calendar["date"].dt.weekday
    calendar["is_business_day"] = calendar["weekday"] < 5

    start = pd.Timestamp(START_DATE)
    end = pd.Timestamp(END_DATE)

    expanded = relation_df.merge(calendar, how="cross")
    expanded = expanded[
        (expanded["date"] >= expanded["dealer_launch_date"])
        & (expanded["date"] >= start)
        & (expanded["date"] <= end)
        & (expanded["is_business_day"])
    ].copy()

    expanded["month_factor"] = expanded["month"].map(MONTH_SEASONALITY)
    expanded["weekday_factor"] = np.where(expanded["weekday"] == 0, 1.05, 1.0)

    effort_adj = expanded["effort_type"].map(EFFORT_TYPE_VOLATILITY).fillna(0.0)
    substitute_adj = expanded["substitute_type"].map(SUBSTITUTE_TYPE_VOLATILITY).fillna(0.0)
    expanded["effective_volatility"] = (
        expanded["baseline_volatility"] + effort_adj + substitute_adj
    ).clip(lower=0.03, upper=0.18)

    # This is raw generation noise for realism.
    # Downstream detection should later aggregate to customer x category level
    # instead of using raw product-level volatility directly.
    volatility = expanded["effective_volatility"].to_numpy()
    random_factor = rng.normal(loc=1.0, scale=volatility, size=len(expanded))
    expanded["noise_factor"] = np.clip(random_factor, 0.80, 1.25)

    expanded["baseline_qty"] = (
        expanded["base_daily_demand"]
        * expanded["size_multiplier"]
        * expanded["relationship_strength"]
        * expanded["month_factor"]
        * expanded["weekday_factor"]
        * expanded["noise_factor"]
    )
    expanded["baseline_qty"] = expanded["baseline_qty"].clip(lower=0.02)
    expanded["adjusted_qty"] = expanded["baseline_qty"]
    expanded["event_id"] = pd.NA
    expanded["event_type"] = pd.NA
    expanded["event_layer"] = 0
    expanded["promo_id"] = pd.NA
    expanded["recall_case_id"] = pd.NA
    expanded["event_delta"] = 0.0

    columns = [
        "date",
        "year",
        "month",
        "week_number",
        "year_week",
        "customer_id",
        "product_id",
        "relationship_strength",
        "list_price",
        "category_l1",
        "category_l2",
        "effort_type",
        "substitute_type",
        "scenario_role",
        "platform_type",
        "baseline_qty",
        "adjusted_qty",
        "event_delta",
        "event_id",
        "event_type",
        "event_layer",
        "promo_id",
        "recall_case_id",
    ]
    return expanded[columns].sort_values(["date", "customer_id", "product_id"]).reset_index(drop=True)
