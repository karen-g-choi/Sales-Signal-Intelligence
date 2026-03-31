"""
Order and invoice fact generation.

This file converts daily demand into line-level orders using each customer's
order cycle, then creates line-level invoices with realistic delays and
partial fulfillment behavior.

Events are applied at demand level first. Orders then carry the selected
event information forward for traceability, while invoices intentionally
remain cleaner and more operationally realistic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from data_generation.seeds import SEED


ORDER_CYCLE_DAYS = {
    "weekly": 7,
    "biweekly": 14,
    "monthly": 28,
}


def assign_order_buckets(demand: pd.DataFrame, dim_customer: pd.DataFrame) -> pd.DataFrame:
    """Assign each daily demand row to a customer-specific replenishment bucket."""

    customer_cycle = dim_customer.set_index("customer_id")[["order_cycle", "dealer_launch_date"]]
    bucketed = demand.merge(customer_cycle, on="customer_id", how="left")
    cycle_days = bucketed["order_cycle"].map(ORDER_CYCLE_DAYS)
    elapsed_days = (bucketed["date"] - bucketed["dealer_launch_date"]).dt.days.clip(lower=0)
    bucketed["bucket_number"] = (elapsed_days // cycle_days).astype(int)
    bucketed["order_date"] = bucketed["dealer_launch_date"] + pd.to_timedelta(
        bucketed["bucket_number"] * cycle_days, unit="D"
    )
    bucketed["order_date"] = bucketed["order_date"].clip(lower=bucketed["date"].min())
    return bucketed


def select_order_event(order_rows: pd.DataFrame) -> pd.Series:
    """Pick the most relevant event to carry into the aggregated order line.

    Rule:
    - prefer a non-null event when one exists
    - if multiple events exist in the same order bucket, use the highest
      event_layer because it represents the latest and strongest business
      overlay in the scenario sequence
    - if no event exists, keep event_id and event_type null and event_layer 0

    "scenario_role" is not used here. It is only for synthetic design
    traceability and debugging, not for downstream logic.
    """

    event_candidates = order_rows[order_rows["event_id"].notna()].copy()
    if event_candidates.empty:
        return pd.Series(
            {
                "event_id": pd.NA,
                "event_type": pd.NA,
                "event_layer": 0,
                "promo_id": order_rows["promo_id"].dropna().iloc[-1] if order_rows["promo_id"].notna().any() else pd.NA,
                "recall_case_id": (
                    order_rows["recall_case_id"].dropna().iloc[-1]
                    if order_rows["recall_case_id"].notna().any()
                    else pd.NA
                ),
            }
        )

    chosen = event_candidates.sort_values(
        by=["event_layer", "date"],
        ascending=[False, False],
    ).iloc[0]
    return pd.Series(
        {
            "event_id": chosen["event_id"],
            "event_type": chosen["event_type"],
            "event_layer": int(chosen["event_layer"]),
            "promo_id": chosen["promo_id"] if pd.notna(chosen["promo_id"]) else pd.NA,
            "recall_case_id": (
                chosen["recall_case_id"] if pd.notna(chosen["recall_case_id"]) else pd.NA
            ),
        }
    )


def build_orders(
    demand: pd.DataFrame, dim_customer: pd.DataFrame, dim_product: pd.DataFrame
) -> pd.DataFrame:
    """Aggregate demand into explainable line-level orders."""

    rng = np.random.default_rng(SEED + 7)
    bucketed = assign_order_buckets(demand, dim_customer)
    product_prices = dim_product.set_index("product_id")["list_price"]

    grouping_keys = ["customer_id", "product_id", "order_date", "bucket_number"]
    quantity_summary = (
        bucketed.groupby(grouping_keys, as_index=False)
        .agg(
            quantity=("adjusted_qty", "sum"),
            event_delta=("event_delta", "sum"),
            baseline_qty=("baseline_qty", "sum"),
        )
        .copy()
    )
    event_summary = (
        bucketed.groupby(grouping_keys, group_keys=False)
        .apply(select_order_event, include_groups=False)
        .reset_index()
    )
    grouped = quantity_summary.merge(event_summary, on=grouping_keys, how="left")

    grouped["quantity"] = np.round(grouped["quantity"]).astype(int)
    grouped = grouped[grouped["quantity"] > 0].reset_index(drop=True)
    grouped["list_price"] = grouped["product_id"].map(product_prices)
    grouped["event_layer"] = grouped["event_layer"].fillna(0).astype(int)

    grouped["discount_pct"] = 0.02
    grouped.loc[grouped["promo_id"].notna(), "discount_pct"] = 0.12
    grouped.loc[grouped["event_type"] == "extreme_promotion", "discount_pct"] = 0.28
    grouped.loc[grouped["event_type"] == "promotion_absence", "discount_pct"] = 0.00

    relationship_noise = np.clip(rng.normal(1.0, 0.015, len(grouped)), 0.96, 1.03)
    grouped["net_price"] = grouped["list_price"] * (1 - grouped["discount_pct"]) * relationship_noise
    grouped["net_price"] = grouped["net_price"].round(2)
    grouped["sales_amount"] = grouped["quantity"] * grouped["net_price"]
    grouped["discount_amount"] = ((grouped["list_price"] - grouped["net_price"]) * grouped["quantity"]).round(2)
    grouped["discount_pct"] = grouped["discount_pct"].round(4)

    grouped = grouped.sort_values(["order_date", "customer_id", "product_id"]).reset_index(drop=True)
    grouped["order_id"] = [
        f"ORD_{row.customer_id}_{row.order_date.strftime('%Y%m%d')}" for row in grouped.itertuples()
    ]
    grouped["order_line_id"] = [f"OL_{i:06d}" for i in range(1, len(grouped) + 1)]

    columns = [
        "order_id",
        "order_line_id",
        "customer_id",
        "product_id",
        "quantity",
        "list_price",
        "net_price",
        "sales_amount",
        "discount_amount",
        "discount_pct",
        "promo_id",
        "recall_case_id",
        "event_id",
        "event_type",
        "event_layer",
        "order_date",
        "baseline_qty",
        "event_delta",
    ]
    return grouped[columns]


def build_invoices(orders: pd.DataFrame) -> pd.DataFrame:
    """Generate line-level invoices with partial fulfillment and delay behavior."""

    rng = np.random.default_rng(SEED + 19)
    invoice_rows = []
    invoice_counter = 1
    invoice_line_counter = 1

    for row in orders.itertuples(index=False):
        full_delay = int(rng.integers(2, 8))
        partial_delay = int(rng.integers(1, 4))
        final_delay = int(rng.integers(6, 16))
        partial_flag = rng.random() < 0.24 and row.quantity > 2

        if partial_flag:
            first_qty = max(1, int(np.floor(row.quantity * rng.uniform(0.55, 0.80))))
            second_qty = int(row.quantity - first_qty)
            first_date = pd.Timestamp(row.order_date) + pd.Timedelta(days=partial_delay)
            second_date = pd.Timestamp(row.order_date) + pd.Timedelta(days=final_delay)
            for qty, inv_date, status in [
                (first_qty, first_date, "partial"),
                (second_qty, second_date, "delayed"),
            ]:
                invoice_rows.append(
                    {
                        "invoice_id": f"INV_{invoice_counter:06d}",
                        "invoice_line_id": f"IL_{invoice_line_counter:06d}",
                        "linked_order_line_id": row.order_line_id,
                        "quantity": qty,
                        "net_price": row.net_price,
                        "sales_amount": qty * row.net_price,
                        "invoice_date": inv_date,
                        "status": status,
                    }
                )
                invoice_counter += 1
                invoice_line_counter += 1
        else:
            invoice_rows.append(
                {
                    "invoice_id": f"INV_{invoice_counter:06d}",
                    "invoice_line_id": f"IL_{invoice_line_counter:06d}",
                    "linked_order_line_id": row.order_line_id,
                    "quantity": row.quantity,
                    "net_price": row.net_price,
                    "sales_amount": row.quantity * row.net_price,
                    "invoice_date": pd.Timestamp(row.order_date) + pd.Timedelta(days=full_delay),
                    "status": "invoiced",
                }
            )
            invoice_counter += 1
            invoice_line_counter += 1

    return pd.DataFrame(invoice_rows).sort_values(["invoice_date", "invoice_line_id"]).reset_index(drop=True)
