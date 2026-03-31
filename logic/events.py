"""
Ordered event layering.

This file applies business events strictly after baseline generation and in
the exact sequence requested in the project brief. Each event is recorded
in a dedicated event table so analysts can trace why demand changed.

The launch logic is intentionally split into:
- an initial exceptional launch phase
- a stabilization phase
- a later baseline-only phase once the temporary launch effect has ended
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from data_generation.seeds import EVENT_ORDER

PRODUCT_NAME_MAP = {
    "P3": "Campaign Brake Pad Kit",
    "P4": "Seasonal Wiper Set",
    "P5": "Workshop Battery Pack",
    "P6": "Cooling Recall Repair Kit",
    "P7": "Launch Essentials Bundle",
    "P8": "Alignment Sensor Kit",
    "P9": "Promo Support Air Filter",
    "P10": "Flash Sale Charge Cable",
    "P11": "ICE Ignition Coil",
    "P12": "ICE Fuel System Cleaner",
    "P13": "EV Thermal Module",
    "P14": "Hybrid Demand Diagnostic Pack",
}


def _apply_multiplier_event(
    demand: pd.DataFrame,
    mask: pd.Series,
    event_id: str,
    event_type: str,
    event_layer: int,
    multiplier: float,
    promo_id: str | None = None,
    recall_case_id: str | None = None,
) -> None:
    """Apply a multiplicative event to the selected daily demand rows."""

    before = demand.loc[mask, "adjusted_qty"].copy()
    demand.loc[mask, "adjusted_qty"] = before * multiplier
    demand.loc[mask, "event_delta"] = demand.loc[mask, "event_delta"] + (before * (multiplier - 1.0))
    demand.loc[mask, "event_id"] = event_id
    demand.loc[mask, "event_type"] = event_type
    demand.loc[mask, "event_layer"] = event_layer
    if promo_id is not None:
        demand.loc[mask, "promo_id"] = promo_id
    if recall_case_id is not None:
        demand.loc[mask, "recall_case_id"] = recall_case_id


def _apply_additive_event(
    demand: pd.DataFrame,
    mask: pd.Series,
    event_id: str,
    event_type: str,
    event_layer: int,
    add_qty: float,
    promo_id: str | None = None,
    recall_case_id: str | None = None,
) -> None:
    """Apply an additive event to the selected daily demand rows."""

    demand.loc[mask, "adjusted_qty"] = demand.loc[mask, "adjusted_qty"] + add_qty
    demand.loc[mask, "event_delta"] = demand.loc[mask, "event_delta"] + add_qty
    demand.loc[mask, "event_id"] = event_id
    demand.loc[mask, "event_type"] = event_type
    demand.loc[mask, "event_layer"] = event_layer
    if promo_id is not None:
        demand.loc[mask, "promo_id"] = promo_id
    if recall_case_id is not None:
        demand.loc[mask, "recall_case_id"] = recall_case_id


def apply_event_layers(
    demand: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Apply all event layers in strict order and return fact tables for tracing."""

    demand = demand.copy()
    promotions = []
    recall_cases = []
    case_vehicle_links = []
    events = []

    def add_event_row(
        event_id: str,
        event_type: str,
        event_layer: int,
        customer_id: str,
        product_id: str,
        start_date: str,
        end_date: str,
        description: str,
        business_reason: str,
        interpretation_hint: str | None = None,
        review_flag: bool = False,
    ) -> None:
        events.append(
            {
                "event_id": event_id,
                "event_type": event_type,
                "event_layer": event_layer,
                "event_sequence_label": EVENT_ORDER[event_layer - 1],
                "customer_id": customer_id,
                "product_id": product_id,
                "start_date": pd.Timestamp(start_date),
                "end_date": pd.Timestamp(end_date),
                "description": description,
                "business_reason": business_reason,
                "interpretation_hint": interpretation_hint,
                "review_flag": review_flag,
            }
        )

    recurring_promos = [
        ("PROMO_001", "CUST_C", "P3", "2024-02-12", "2024-02-25", 1.30, "Quarter-start brake campaign"),
        ("PROMO_002", "CUST_C", "P3", "2024-06-10", "2024-06-23", 1.28, "Summer brake campaign"),
        ("PROMO_003", "CUST_C", "P3", "2025-02-10", "2025-02-23", 1.27, "Repeat brake campaign"),
        ("PROMO_004", "CUST_A", "P4", "2024-10-07", "2024-10-20", 1.22, "Autumn visibility push"),
        ("PROMO_005", "CUST_C", "P4", "2024-11-04", "2024-11-17", 1.35, "Retail wiper promotion"),
        ("PROMO_006", "CUST_D", "P3", "2025-04-07", "2025-04-20", 1.20, "Dealer support campaign"),
    ]
    for promo_id, customer_id, product_id, start_date, end_date, multiplier, promo_name in recurring_promos:
        mask = (
            (demand["customer_id"] == customer_id)
            & (demand["product_id"] == product_id)
            & (demand["date"].between(start_date, end_date))
        )
        _apply_multiplier_event(
            demand,
            mask,
            event_id=promo_id.replace("PROMO", "EVT"),
            event_type="recurring_promotion",
            event_layer=1,
            multiplier=multiplier,
            promo_id=promo_id,
        )
        promotions.append(
            {
                "promo_id": promo_id,
                "promotion_name": promo_name,
                "promotion_type": "recurring",
                "customer_id": customer_id,
                "product_id": product_id,
                "start_date": pd.Timestamp(start_date),
                "end_date": pd.Timestamp(end_date),
                "uplift_multiplier": multiplier,
                "promotion_status": "executed",
                "recurring_flag": True,
                "one_off_campaign_flag": False,
                "promo_classification_hint": "normal",
            }
        )
        add_event_row(
            promo_id.replace("PROMO", "EVT"),
            "recurring_promotion",
            1,
            customer_id,
            product_id,
            start_date,
            end_date,
            promo_name,
            f"Repeated promotion on {PRODUCT_NAME_MAP[product_id]} creates a moderate, explainable uplift above baseline demand.",
        )

    bulk_event_id = "EVT_2001"
    bulk_mask = (
        (demand["customer_id"] == "CUST_A")
        & (demand["product_id"] == "P5")
        & (demand["date"].between("2024-09-16", "2024-09-20"))
    )
    _apply_additive_event(demand, bulk_mask, bulk_event_id, "one_off_bulk_order", 2, add_qty=7.5)
    add_event_row(
        bulk_event_id,
        "one_off_bulk_order",
        2,
        "CUST_A",
        "P5",
        "2024-09-16",
        "2024-09-20",
        "Pre-winter Workshop Battery Pack stock-up",
        "A one-time bulk purchase of Workshop Battery Pack units creates a single visible spike above normal replenishment.",
    )

    recall_case_id = "CASE_3001"
    recall_event_id = "EVT_3001"
    recall_cases.append(
        {
            "recall_case_id": recall_case_id,
            "case_name": "Cooling hose warranty action",
            "product_id": "P6",
            "start_date": pd.Timestamp("2025-02-03"),
            "end_date": pd.Timestamp("2025-03-09"),
            "case_status": "closed",
            "severity": "high",
        }
    )
    for vehicle_model_id in ["VM001", "VM002"]:
        case_vehicle_links.append(
            {"recall_case_id": recall_case_id, "vehicle_model_id": vehicle_model_id}
        )
    for customer_id, multiplier in [("CUST_A", 2.8), ("CUST_B", 2.3)]:
        mask = (
            (demand["customer_id"] == customer_id)
            & (demand["product_id"] == "P6")
            & (demand["date"].between("2025-02-03", "2025-03-09"))
        )
        _apply_multiplier_event(
            demand,
            mask,
            event_id=recall_event_id,
            event_type="recall_warranty",
            event_layer=3,
            multiplier=multiplier,
            recall_case_id=recall_case_id,
        )
        add_event_row(
            recall_event_id,
            "recall_warranty",
            3,
            customer_id,
            "P6",
            "2025-02-03",
            "2025-03-09",
            "Cooling Recall Repair Kit warranty surge",
            "A field warranty action temporarily pushes Cooling Recall Repair Kit demand far above normal service demand.",
        )

    new_dealer_event_id = "EVT_4001"
    # Phase 1 is the exceptional launch burst.
    # Phase 2 is a transition toward repeat demand.
    # After 2024-06-30, the launch effect ends and only baseline remains.
    launch_masks = [
        (
            (demand["customer_id"] == "CUST_D")
            & (demand["product_id"] == "P7")
            & (demand["date"].between("2024-03-04", "2024-04-14")),
            1.85,
        ),
        (
            (demand["customer_id"] == "CUST_D")
            & (demand["product_id"] == "P7")
            & (demand["date"].between("2024-04-15", "2024-06-30")),
            1.25,
        ),
    ]
    for mask, multiplier in launch_masks:
        _apply_multiplier_event(
            demand,
            mask,
            event_id=new_dealer_event_id,
            event_type="new_dealer_launch",
            event_layer=4,
            multiplier=multiplier,
        )
    add_event_row(
        new_dealer_event_id,
        "new_dealer_launch",
        4,
        "CUST_D",
        "P7",
        "2024-03-04",
        "2024-06-30",
        "Launch Essentials Bundle launch burst and stabilization",
        "The new dealer starts with an exceptional Launch Essentials Bundle loading phase, transitions through stabilization, and then moves to baseline-only demand after the launch window.",
    )

    extreme_promo_id = "PROMO_9001"
    extreme_event_id = "EVT_5001"
    extreme_mask = (
        (demand["customer_id"] == "CUST_C")
        & (demand["product_id"] == "P10")
        & (demand["date"].between("2025-11-17", "2025-11-30"))
    )
    _apply_multiplier_event(
        demand,
        extreme_mask,
        event_id=extreme_event_id,
        event_type="extreme_promotion",
        event_layer=5,
        multiplier=3.8,
        promo_id=extreme_promo_id,
    )
    promotions.append(
        {
            "promo_id": extreme_promo_id,
            "promotion_name": "Black week charging blitz",
            "promotion_type": "extreme",
            "customer_id": "CUST_C",
            "product_id": "P10",
            "start_date": pd.Timestamp("2025-11-17"),
            "end_date": pd.Timestamp("2025-11-30"),
            "uplift_multiplier": 3.8,
            "promotion_status": "executed",
            "recurring_flag": False,
            "one_off_campaign_flag": True,
            "promo_classification_hint": "exceptional",
        }
    )
    add_event_row(
        extreme_event_id,
        "extreme_promotion",
        5,
        "CUST_C",
        "P10",
        "2025-11-17",
        "2025-11-30",
        "Flash Sale Charge Cable black week blitz",
        "A short, very aggressive Flash Sale Charge Cable campaign creates an intentionally outsized spike.",
    )

    absence_event_id = "EVT_6001"
    absence_promo_id = "PROMO_6001"
    absence_mask = (
        (demand["customer_id"] == "CUST_C")
        & (demand["product_id"] == "P9")
        & (demand["date"].between("2025-05-05", "2025-05-18"))
    )
    _apply_multiplier_event(
        demand,
        absence_mask,
        event_id=absence_event_id,
        event_type="promotion_absence",
        event_layer=6,
        multiplier=0.72,
    )
    promotions.append(
        {
            "promo_id": absence_promo_id,
            "promotion_name": "Spring air-filter campaign not repeated",
            "promotion_type": "planned_but_absent",
            "customer_id": "CUST_C",
            "product_id": "P9",
            "start_date": pd.Timestamp("2025-05-05"),
            "end_date": pd.Timestamp("2025-05-18"),
            "uplift_multiplier": 0.72,
            "promotion_status": "missed",
            "recurring_flag": True,
            "one_off_campaign_flag": False,
            "promo_classification_hint": "normal_expected_but_missing",
        }
    )
    add_event_row(
        absence_event_id,
        "promotion_absence",
        6,
        "CUST_C",
        "P9",
        "2025-05-05",
        "2025-05-18",
        "Promo Support Air Filter campaign missing",
        "Demand drops because the expected recurring Promo Support Air Filter uplift does not happen this year.",
    )

    hidden_event_id = "EVT_7001"
    hidden_mask = (
        (demand["customer_id"] == "CUST_A")
        & (demand["product_id"] == "P8")
        & (demand["date"] >= pd.Timestamp("2025-01-06"))
    )
    hidden_days = (demand.loc[hidden_mask, "date"] - pd.Timestamp("2025-01-06")).dt.days.to_numpy()
    hidden_multiplier = np.clip(1.0 - (hidden_days / 365.0) * 0.28, 0.72, 1.0)
    before_hidden = demand.loc[hidden_mask, "adjusted_qty"].to_numpy()
    demand.loc[hidden_mask, "adjusted_qty"] = before_hidden * hidden_multiplier
    demand.loc[hidden_mask, "event_delta"] = demand.loc[hidden_mask, "event_delta"] + (
        before_hidden * (hidden_multiplier - 1.0)
    )
    demand.loc[hidden_mask, "event_id"] = hidden_event_id
    demand.loc[hidden_mask, "event_type"] = "hidden_drop"
    demand.loc[hidden_mask, "event_layer"] = 7
    add_event_row(
        hidden_event_id,
        "hidden_drop",
        7,
        "CUST_A",
        "P8",
        "2025-01-06",
        "2025-12-31",
        "Slow erosion in Alignment Sensor Kit demand",
        "A gradual decline appears inside a large established dealer on Alignment Sensor Kit, without a visible campaign trigger, making it a meaningful hidden-drop case.",
    )

    trend_start = pd.Timestamp("2025-01-01")
    for product_id, end_multiplier, description, reason in [
        ("P11", 0.78, "ICE ignition demand softens", "ICE share declines and demand settles lower over time."),
        ("P12", 0.82, "ICE fuel cleaner demand softens", "The market gradually buys fewer ICE maintenance items."),
        ("P13", 1.38, "EV thermal module becomes more common", "Growing EV parc creates a new higher normal."),
    ]:
        mask = (demand["product_id"] == product_id) & (demand["date"] >= trend_start)
        trend_days = (demand.loc[mask, "date"] - trend_start).dt.days.to_numpy()
        slope = 1.0 + ((end_multiplier - 1.0) / 365.0) * trend_days
        before_trend = demand.loc[mask, "adjusted_qty"].to_numpy()
        demand.loc[mask, "adjusted_qty"] = before_trend * slope
        demand.loc[mask, "event_delta"] = demand.loc[mask, "event_delta"] + (before_trend * (slope - 1.0))
        demand.loc[mask, "event_id"] = f"EVT_800{product_id[-1]}"
        demand.loc[mask, "event_type"] = "new_normal_shift"
        demand.loc[mask, "event_layer"] = 8
        add_event_row(
            f"EVT_800{product_id[-1]}",
            "new_normal_shift",
            8,
            "MULTI_CUSTOMER",
            product_id,
            "2025-01-01",
            "2025-12-31",
            description,
            reason,
        )

    mixed_event_id = "EVT_9001"
    mixed_mask = (
        (demand["product_id"] == "P14")
        & (demand["customer_id"].isin(["CUST_A", "CUST_C", "CUST_E"]))
        & (demand["date"] >= pd.Timestamp("2025-06-02"))
    )
    mixed_days = (demand.loc[mixed_mask, "date"] - pd.Timestamp("2025-06-02")).dt.days.to_numpy()
    wave = 1.0 + 0.12 * np.sin(mixed_days / 21.0)
    drag = np.clip(1.0 - mixed_days * 0.00035, 0.88, 1.0)
    mixed_multiplier = wave * drag
    before_mixed = demand.loc[mixed_mask, "adjusted_qty"].to_numpy()
    demand.loc[mixed_mask, "adjusted_qty"] = before_mixed * mixed_multiplier
    demand.loc[mixed_mask, "event_delta"] = demand.loc[mixed_mask, "event_delta"] + (
        before_mixed * (mixed_multiplier - 1.0)
    )
    demand.loc[mixed_mask, "event_id"] = mixed_event_id
    demand.loc[mixed_mask, "event_type"] = "mixed_ambiguous_behavior"
    demand.loc[mixed_mask, "event_layer"] = 9
    add_event_row(
        mixed_event_id,
        "mixed_ambiguous_behavior",
        9,
        "MULTI_CUSTOMER",
        "P14",
        "2025-06-02",
        "2025-12-31",
        "Mixed signal pattern on Hybrid Demand Diagnostic Pack",
        "This product combines mild campaign-like bumps with a soft downward drift, creating ambiguous behavior.",
        interpretation_hint="Pattern mixes temporary uplift and soft structural drift; analyst review is recommended.",
        review_flag=True,
    )

    demand["adjusted_qty"] = demand["adjusted_qty"].clip(lower=0.0)

    return (
        demand,
        pd.DataFrame(promotions).sort_values(["start_date", "promo_id"]).reset_index(drop=True),
        pd.DataFrame(recall_cases),
        pd.DataFrame(case_vehicle_links),
        pd.DataFrame(events).sort_values(["event_layer", "event_id", "customer_id"]).reset_index(drop=True),
    )
