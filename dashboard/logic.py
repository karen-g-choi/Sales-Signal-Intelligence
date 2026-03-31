"""
Analytical logic for the Streamlit business dashboard.

This file keeps the dashboard explainable and modular. It prepares weekly
sales at customer x category level, reconstructs a simple baseline from
historical sales, and applies readable business rules for risk severity and
interpretation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_RULE_CONFIG = {
    "baseline_lookback_weeks": 8,
    "warning_drop_pct": 0.06,
    "critical_drop_pct": 0.12,
    "minimum_duration_weeks": 6,
    "consistency_threshold": 0.60,
    "high_impact_sales_threshold": 20000.0,
    "large_customer_weight": 1.15,
    "key_category_weight": 1.10,
    "detection_basis": "monthly",
}

SEVERITY_ORDER = {
    "Normal": 0,
    "Watch": 1,
    "Warning": 2,
    "Critical": 3,
}

SEVERITY_COLOR = {
    "Normal": "#2E7D32",
    "Watch": "#F9A825",
    "Warning": "#EF6C00",
    "Critical": "#C62828",
}

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
TARGET_FILE = OUTPUT_DIR / "target_monthly.csv"
TARGET_RECALIBRATION_FACTOR = 0.9746512296945459


def iso_year_week(series: pd.Series) -> pd.Series:
    """Format a datetime series as an ISO year-week label."""

    iso = series.dt.isocalendar()
    return iso.year.astype(str) + "-W" + iso.week.astype(str).str.zfill(2)


def get_default_rule_config() -> dict[str, float | int]:
    """Return a copy of the default configurable business rules."""

    return DEFAULT_RULE_CONFIG.copy()


def prepare_orders_enriched(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Merge orders with customer and product context for dashboard analytics.

    Important note:
    scenario_role is not used in this logic. The dashboard uses observed
    sales behavior and event-linked records only.
    """

    orders = tables["fact_orders"].copy()
    products = tables["dim_product"][["product_id", "category_l1", "product_name"]].copy()
    customers = tables["dim_customer"][["customer_id", "customer_name", "customer_size"]].copy()

    orders["order_date"] = pd.to_datetime(orders["order_date"])
    orders["week_start"] = orders["order_date"] - pd.to_timedelta(orders["order_date"].dt.weekday, unit="D")
    orders["year_week"] = iso_year_week(orders["week_start"])
    orders["event_linked_sales"] = orders["sales_amount"].where(orders["event_id"].notna(), 0.0)

    return (
        orders.merge(products, on="product_id", how="left")
        .merge(customers, on="customer_id", how="left")
        .sort_values(["customer_name", "category_l1", "order_date", "product_id"])
        .reset_index(drop=True)
    )


def prepare_event_reference(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Prepare a readable event table for event timelines and deep dives."""

    events = tables["fact_events"].copy()
    products = tables["dim_product"][["product_id", "category_l1", "product_name"]].copy()
    customers = tables["dim_customer"][["customer_id", "customer_name"]].copy()

    events["start_date"] = pd.to_datetime(events["start_date"])
    events["end_date"] = pd.to_datetime(events["end_date"])

    enriched = events.merge(products, on="product_id", how="left").merge(customers, on="customer_id", how="left")
    enriched["customer_name"] = enriched["customer_name"].fillna(enriched["customer_id"])
    return enriched.sort_values(["start_date", "event_layer", "customer_name"]).reset_index(drop=True)


def build_weekly_sales(orders_enriched: pd.DataFrame, lookback_weeks: int) -> pd.DataFrame:
    """Build weekly sales and reconstructed baseline at customer x category grain."""

    weekly = (
        orders_enriched.groupby(
            ["customer_id", "customer_name", "customer_size", "category_l1", "week_start", "year_week"],
            as_index=False,
        )
        .agg(
            total_sales=("sales_amount", "sum"),
            event_linked_sales=("event_linked_sales", "sum"),
            order_lines=("order_line_id", "count"),
        )
        .sort_values(["customer_id", "category_l1", "week_start"])
        .reset_index(drop=True)
    )
    weekly["baseline_like_sales"] = weekly["total_sales"] - weekly["event_linked_sales"]

    def baseline_for_group(group: pd.DataFrame) -> pd.DataFrame:
        group = group.sort_values("week_start").copy()
        prior_sales = group["total_sales"].shift(1)
        rolling_baseline = prior_sales.rolling(window=lookback_weeks, min_periods=max(3, lookback_weeks // 2)).median()
        expanding_baseline = prior_sales.expanding(min_periods=1).median()
        group["reconstructed_baseline_sales"] = rolling_baseline.fillna(expanding_baseline)
        group["reconstructed_baseline_sales"] = group["reconstructed_baseline_sales"].fillna(group["total_sales"])
        group["sales_delta"] = group["total_sales"] - group["reconstructed_baseline_sales"]
        group["sales_delta_pct"] = (
            group["sales_delta"] / group["reconstructed_baseline_sales"].replace(0, pd.NA)
        ).fillna(0.0)
        group["below_baseline_flag"] = group["total_sales"] < group["reconstructed_baseline_sales"]
        return group

    groups = []
    for _, group in weekly.groupby(["customer_id", "category_l1"], sort=False):
        groups.append(baseline_for_group(group))
    return pd.concat(groups, ignore_index=True)


def ensure_target_table(orders_enriched: pd.DataFrame, force_rebuild: bool = False) -> pd.DataFrame:
    """Create or load a synthetic monthly target table for reporting analysis."""

    if TARGET_FILE.exists() and not force_rebuild:
        target_table = pd.read_csv(TARGET_FILE)
        target_table["month_start"] = pd.to_datetime(target_table["month_start"])
        return target_table

    monthly_actual = (
        orders_enriched.assign(
            month_start=orders_enriched["order_date"].dt.to_period("M").dt.to_timestamp(),
            year=orders_enriched["order_date"].dt.year,
            month=orders_enriched["order_date"].dt.month,
        )
        .groupby(
            ["customer_id", "customer_name", "customer_size", "category_l1", "month_start", "year", "month"],
            as_index=False,
        )
        .agg(
            actual_sales_amount=("sales_amount", "sum"),
            actual_quantity=("quantity", "sum"),
        )
        .sort_values(["customer_id", "category_l1", "month_start"])
        .reset_index(drop=True)
    )

    # Targets should feel commercially realistic: some positions should land above
    # plan, some just below, and some materially below. We therefore use lighter
    # stretch factors than the initial version instead of pushing every line to
    # the same near-miss outcome.
    stretch_by_size = {"large": 1.020, "mid": 1.010, "small": 0.995}
    season_bias = {
        1: 1.010, 2: 1.005, 3: 1.010, 4: 1.005, 5: 1.000, 6: 0.995,
        7: 0.992, 8: 0.995, 9: 1.000, 10: 1.008, 11: 1.012, 12: 1.018,
    }
    category_bias = {
        "Accessories": 0.990,
        "EV Service": 0.995,
        "Service": 1.000,
        "Maintenance": 1.000,
        "Diagnostics": 1.005,
        "Powertrain": 1.008,
        "Repair": 1.012,
        "Dealer Launch": 1.020,
    }
    customer_bias = {
        "NordAuto Stockholm": 1.012,
        "Svea Mobility Parts": 1.000,
        "PromoDrive Retail": 1.000,
        "NewMotion Uppsala": 0.995,
        "Arctic Niche Auto": 0.990,
    }

    def build_group_targets(group: pd.DataFrame) -> pd.DataFrame:
        group = group.sort_values("month_start").copy()
        prior_sales = group["actual_sales_amount"].shift(1).rolling(3, min_periods=1).median()
        prior_qty = group["actual_quantity"].shift(1).rolling(3, min_periods=1).median()
        prior_year_sales = group["actual_sales_amount"].shift(12)
        prior_year_qty = group["actual_quantity"].shift(12)
        sales_base = prior_sales.fillna(group["actual_sales_amount"])
        qty_base = prior_qty.fillna(group["actual_quantity"])
        sales_anchor = (sales_base * 0.80) + (group["actual_sales_amount"] * 0.20)
        qty_anchor = (qty_base * 0.85) + (group["actual_quantity"] * 0.15)
        stretch = stretch_by_size.get(group["customer_size"].iloc[0], 1.02)
        month_factor = group["month"].map(season_bias).fillna(1.0)
        category_factor = category_bias.get(group["category_l1"].iloc[0], 1.0)
        customer_factor = customer_bias.get(group["customer_name"].iloc[0], 1.0)

        # A mild trend response keeps fast-growing positions a bit more ambitious
        # without forcing every current-month attainment to cluster at one value.
        trend_ratio = (group["actual_sales_amount"] / sales_base.replace(0, pd.NA)).replace([pd.NA], 1.0).fillna(1.0)
        trend_factor = (1 + (trend_ratio - 1) * 0.10).clip(0.985, 1.015)

        sales_multiplier = stretch * month_factor * category_factor * customer_factor * trend_factor
        qty_multiplier = min(max(stretch * category_factor * customer_factor, 0.96), 1.04)

        computed_sales_target = sales_anchor * sales_multiplier * TARGET_RECALIBRATION_FACTOR
        computed_qty_target = qty_anchor * qty_multiplier * TARGET_RECALIBRATION_FACTOR

        # Business realism: plans should generally step up versus prior year for
        # established, core commercial areas, but not every volatile or transition
        # category should be forced above last year in every month.
        apply_prior_year_floor = (
            group["customer_size"].iloc[0] in {"large", "mid"}
            and group["category_l1"].iloc[0] not in {"Accessories", "Dealer Launch", "EV Service", "Diagnostics", "Service"}
        )
        prior_year_sales_floor = prior_year_sales * 1.002
        prior_year_qty_floor = prior_year_qty * 1.002

        if apply_prior_year_floor:
            group["target_sales_amount"] = (
                pd.concat([computed_sales_target, prior_year_sales_floor], axis=1)
                .max(axis=1, skipna=True)
                .round(2)
            )
            group["target_quantity"] = (
                pd.concat([computed_qty_target, prior_year_qty_floor], axis=1)
                .max(axis=1, skipna=True)
                .round(0)
                .astype(int)
            )
        else:
            group["target_sales_amount"] = computed_sales_target.round(2)
            group["target_quantity"] = computed_qty_target.round(0).astype(int)
        return group

    target_groups = []
    for _, group in monthly_actual.groupby(["customer_id", "category_l1"], sort=False):
        target_groups.append(build_group_targets(group))

    target_table = pd.concat(target_groups, ignore_index=True)[
        ["month_start", "customer_id", "customer_name", "category_l1", "target_sales_amount", "target_quantity"]
    ]
    target_table.to_csv(TARGET_FILE, index=False)
    return target_table


def build_monthly_sales(orders_enriched: pd.DataFrame, target_table: pd.DataFrame) -> pd.DataFrame:
    """Aggregate sales monthly and merge synthetic targets for reporting."""

    monthly = (
        orders_enriched.assign(
            month_start=orders_enriched["order_date"].dt.to_period("M").dt.to_timestamp(),
            year=orders_enriched["order_date"].dt.year,
            month=orders_enriched["order_date"].dt.month,
            year_month=orders_enriched["order_date"].dt.strftime("%Y-%m"),
        )
        .groupby(
            ["customer_id", "customer_name", "customer_size", "category_l1", "month_start", "year", "month", "year_month"],
            as_index=False,
        )
        .agg(
            total_sales=("sales_amount", "sum"),
            total_quantity=("quantity", "sum"),
            event_linked_sales=("event_linked_sales", "sum"),
        )
        .sort_values(["customer_id", "category_l1", "month_start"])
        .reset_index(drop=True)
    )

    monthly = monthly.merge(
        target_table[["month_start", "customer_id", "category_l1", "target_sales_amount", "target_quantity"]],
        on=["month_start", "customer_id", "category_l1"],
        how="left",
    )

    def add_monthly_baseline(group: pd.DataFrame) -> pd.DataFrame:
        group = group.sort_values("month_start").copy()
        prior_sales = group["total_sales"].shift(1)
        rolling_baseline = prior_sales.rolling(window=3, min_periods=2).median()
        expanding_baseline = prior_sales.expanding(min_periods=1).median()
        group["reconstructed_baseline_sales"] = rolling_baseline.fillna(expanding_baseline)
        group["reconstructed_baseline_sales"] = group["reconstructed_baseline_sales"].fillna(group["total_sales"])
        group["sales_delta"] = group["total_sales"] - group["reconstructed_baseline_sales"]
        group["sales_delta_pct"] = (
            group["sales_delta"] / group["reconstructed_baseline_sales"].replace(0, pd.NA)
        ).fillna(0.0)
        group["prior_year_sales"] = group["total_sales"].shift(12)
        group["yoy_trend_pct"] = (
            (group["total_sales"] / group["prior_year_sales"].replace(0, pd.NA)) - 1.0
        ).fillna(0.0)
        group["target_attainment_pct"] = (
            group["total_sales"] / group["target_sales_amount"].replace(0, pd.NA)
        ).fillna(0.0)
        return group

    groups = []
    for _, group in monthly.groupby(["customer_id", "category_l1"], sort=False):
        groups.append(add_monthly_baseline(group))
    return pd.concat(groups, ignore_index=True)


def latest_reporting_month(monthly_sales: pd.DataFrame) -> pd.Timestamp:
    """Return the most recent month available in the dataset."""

    return pd.Timestamp(monthly_sales["month_start"].max())


def build_sales_overview_kpis(monthly_sales: pd.DataFrame) -> dict[str, float]:
    """Build headline commercial KPIs for the Sales Overview tab."""

    current_month = latest_reporting_month(monthly_sales)
    current_year = current_month.year

    ytd = monthly_sales[
        (monthly_sales["year"] == current_year) & (monthly_sales["month"] <= current_month.month)
    ]
    prior_ytd = monthly_sales[
        (monthly_sales["year"] == current_year - 1) & (monthly_sales["month"] <= current_month.month)
    ]
    current_month_frame = monthly_sales[monthly_sales["month_start"] == current_month]

    ytd_sales = float(ytd["total_sales"].sum())
    prior_ytd_sales = float(prior_ytd["total_sales"].sum())
    ytd_growth = (ytd_sales / prior_ytd_sales - 1.0) if prior_ytd_sales > 0 else 0.0
    ytd_target = float(ytd["target_sales_amount"].sum())
    target_attainment = (ytd_sales / ytd_target) if ytd_target > 0 else 0.0

    return {
        "ytd_sales_amount": ytd_sales,
        "current_month_sales_amount": float(current_month_frame["total_sales"].sum()),
        "current_month_sales_quantity": float(current_month_frame["total_quantity"].sum()),
        "ytd_growth_pct": ytd_growth,
        "target_achievement_pct": target_attainment,
        "current_month": current_month,
        "current_year": current_year,
    }


def build_ytd_customer_view(monthly_sales: pd.DataFrame) -> pd.DataFrame:
    """Rank customers by YTD sales for controller-style reporting."""

    kpis = build_sales_overview_kpis(monthly_sales)
    ytd = monthly_sales[
        (monthly_sales["year"] == kpis["current_year"])
        & (monthly_sales["month"] <= kpis["current_month"].month)
    ]
    return (
        ytd.groupby("customer_name", as_index=False)["total_sales"]
        .sum()
        .sort_values("total_sales", ascending=False)
        .reset_index(drop=True)
    )


def build_ytd_category_view(monthly_sales: pd.DataFrame) -> pd.DataFrame:
    """Summarize YTD sales and growth by product group."""

    kpis = build_sales_overview_kpis(monthly_sales)
    current = monthly_sales[
        (monthly_sales["year"] == kpis["current_year"])
        & (monthly_sales["month"] <= kpis["current_month"].month)
    ]
    prior = monthly_sales[
        (monthly_sales["year"] == kpis["current_year"] - 1)
        & (monthly_sales["month"] <= kpis["current_month"].month)
    ]

    current_group = current.groupby("category_l1", as_index=False)["total_sales"].sum().rename(columns={"total_sales": "ytd_sales"})
    prior_group = prior.groupby("category_l1", as_index=False)["total_sales"].sum().rename(columns={"total_sales": "prior_ytd_sales"})
    merged = current_group.merge(prior_group, on="category_l1", how="left")
    merged["growth_pct"] = ((merged["ytd_sales"] / merged["prior_ytd_sales"].replace(0, pd.NA)) - 1.0).fillna(0.0)
    return merged.sort_values("ytd_sales", ascending=False).reset_index(drop=True)


def build_sales_mix_view(monthly_sales: pd.DataFrame) -> pd.DataFrame:
    """Create a restrained sales mix view for business reporting."""

    kpis = build_sales_overview_kpis(monthly_sales)
    ytd = monthly_sales[
        (monthly_sales["year"] == kpis["current_year"])
        & (monthly_sales["month"] <= kpis["current_month"].month)
    ]
    total_sales = float(ytd["total_sales"].sum())
    event_sales = float(ytd["event_linked_sales"].sum())
    normal_sales = total_sales - event_sales
    hidden_gap = max(float(ytd["reconstructed_baseline_sales"].sum()) - total_sales, 0.0)
    return pd.DataFrame(
        {
            "sales_type": ["Normal Sales", "Event-Linked Sales", "Hidden Gap"],
            "sales_amount": [normal_sales, event_sales, hidden_gap],
        }
    )


def build_monthly_trend_view(monthly_sales: pd.DataFrame) -> pd.DataFrame:
    """Prepare monthly trend data for the current year and prior year."""

    kpis = build_sales_overview_kpis(monthly_sales)
    trend = (
        monthly_sales.groupby(["month_start", "year", "month"], as_index=False)
        .agg(
            total_sales=("total_sales", "sum"),
            target_sales_amount=("target_sales_amount", "sum"),
        )
        .sort_values("month_start")
        .reset_index(drop=True)
    )
    current = trend[trend["year"] == kpis["current_year"]].copy()
    prior = trend[trend["year"] == kpis["current_year"] - 1].copy()
    current = current.rename(columns={"total_sales": "current_year_sales", "target_sales_amount": "current_year_target"})
    prior = prior[["month", "total_sales"]].rename(columns={"total_sales": "previous_year_sales"})
    return current.merge(prior, on="month", how="left")


def build_target_insight_view(monthly_sales: pd.DataFrame) -> pd.DataFrame:
    """Highlight biggest over/under target areas for the latest month."""

    current_month = latest_reporting_month(monthly_sales)
    current = monthly_sales[monthly_sales["month_start"] == current_month].copy()
    current["target_gap"] = current["total_sales"] - current["target_sales_amount"]
    return current[
        ["customer_name", "category_l1", "total_sales", "target_sales_amount", "target_attainment_pct", "target_gap"]
    ].sort_values("target_gap").reset_index(drop=True)


def identify_key_categories(weekly_sales: pd.DataFrame, top_n: int = 2) -> list[str]:
    """Identify the highest-value categories to support optional business weighting."""

    category_sales = weekly_sales.groupby("category_l1", as_index=False)["total_sales"].sum()
    top_categories = category_sales.sort_values("total_sales", ascending=False).head(top_n)
    return top_categories["category_l1"].tolist()


def filter_dashboard_data(
    weekly_sales: pd.DataFrame,
    orders_enriched: pd.DataFrame,
    event_reference: pd.DataFrame,
    selected_customers: list[str],
    selected_categories: list[str],
    date_range: tuple[pd.Timestamp, pd.Timestamp],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Apply customer, category, and date filters consistently across datasets."""

    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])

    filtered_weekly = weekly_sales[weekly_sales["week_start"].between(start_date, end_date)].copy()
    filtered_orders = orders_enriched[orders_enriched["week_start"].between(start_date, end_date)].copy()
    filtered_events = event_reference[
        (event_reference["end_date"] >= start_date) & (event_reference["start_date"] <= end_date)
    ].copy()

    if selected_customers:
        filtered_weekly = filtered_weekly[filtered_weekly["customer_name"].isin(selected_customers)]
        filtered_orders = filtered_orders[filtered_orders["customer_name"].isin(selected_customers)]
        filtered_events = filtered_events[
            filtered_events["customer_name"].isin(selected_customers)
            | filtered_events["customer_id"].eq("MULTI_CUSTOMER")
        ]

    if selected_categories:
        filtered_weekly = filtered_weekly[filtered_weekly["category_l1"].isin(selected_categories)]
        filtered_orders = filtered_orders[filtered_orders["category_l1"].isin(selected_categories)]
        filtered_events = filtered_events[filtered_events["category_l1"].isin(selected_categories)]

    return (
        filtered_weekly.reset_index(drop=True),
        filtered_orders.reset_index(drop=True),
        filtered_events.reset_index(drop=True),
    )


def filter_monthly_sales(
    monthly_sales: pd.DataFrame,
    selected_customers: list[str],
    selected_categories: list[str],
    month_range: tuple[pd.Timestamp, pd.Timestamp],
) -> pd.DataFrame:
    """Apply customer, category, and month filters to monthly reporting data."""

    start_date, end_date = pd.to_datetime(month_range[0]), pd.to_datetime(month_range[1])
    filtered = monthly_sales[monthly_sales["month_start"].between(start_date, end_date)].copy()

    if selected_customers:
        filtered = filtered[filtered["customer_name"].isin(selected_customers)]
    if selected_categories:
        filtered = filtered[filtered["category_l1"].isin(selected_categories)]
    return filtered.reset_index(drop=True)


def _derive_interpretation(
    dominant_event_type: str | None,
    delta_pct: float,
    event_share: float,
    severity: str,
) -> str:
    """Map a simple business signal into an explainable interpretation label."""

    if dominant_event_type == "recurring_promotion" and delta_pct > 0.03:
        return "Recurring commercial uplift"
    if dominant_event_type in {"extreme_promotion", "one_off_bulk_order", "recall_warranty"} and delta_pct > 0.03:
        return "Event-driven uplift"
    if dominant_event_type == "promotion_absence" and delta_pct < 0:
        return "Promo gap"
    if dominant_event_type == "new_normal_shift":
        return "Structural shift / New normal"
    if severity in {"Watch", "Warning", "Critical"} and event_share < 0.40:
        return "Hidden drop"
    return "Needs review"


def _derive_possible_risk_factor(
    dominant_event_type: str | None,
    delta_pct: float,
    yoy_trend_pct: float,
    target_attainment_pct: float,
    event_share: float,
) -> str:
    """Translate the signal into a business-friendly explanation."""

    if dominant_event_type == "promotion_absence":
        return "Promo gap"
    if dominant_event_type == "new_normal_shift" or (yoy_trend_pct <= -0.08 and event_share < 0.30):
        return "Structural shift / New normal"
    if dominant_event_type in {"extreme_promotion", "one_off_bulk_order", "recall_warranty"}:
        return "Event-driven volatility"
    if dominant_event_type == "new_dealer_launch":
        return "Launch transition"
    if delta_pct <= -0.06 and target_attainment_pct < 0.95 and event_share < 0.35:
        return "Demand softening"
    return "Needs analyst review"


def summarize_monthly_risks(
    monthly_sales: pd.DataFrame,
    orders_enriched: pd.DataFrame,
    config: dict[str, float | int | str],
    key_categories: list[str],
) -> pd.DataFrame:
    """Create a business-facing monthly risk summary for executive reporting.

    The visible risk dashboard uses monthly aggregation to reduce week-to-week
    noise and keep the interpretation closer to how managers usually review
    performance. The underlying order and event traceability is still used to
    explain likely drivers.
    """

    signal_rows: list[dict[str, Any]] = []
    recent_window = max(int(round(int(config["minimum_duration_weeks"]) / 4)), 2)

    monthly_orders = orders_enriched.assign(
        month_start=orders_enriched["order_date"].dt.to_period("M").dt.to_timestamp()
    )

    for (customer_name, category_l1), group in monthly_sales.groupby(["customer_name", "category_l1"]):
        group = group.sort_values("month_start").copy()
        recent = group.tail(recent_window).copy()
        if len(recent) < recent_window:
            continue

        recent_orders = monthly_orders[
            (monthly_orders["customer_name"] == customer_name)
            & (monthly_orders["category_l1"] == category_l1)
            & (monthly_orders["month_start"].isin(recent["month_start"]))
        ].copy()

        recent_sales = float(recent["total_sales"].sum())
        baseline_sales = float(recent["reconstructed_baseline_sales"].sum())
        at_risk_sales = max(baseline_sales - recent_sales, 0.0)
        delta_pct = (recent_sales / baseline_sales - 1.0) if baseline_sales > 0 else 0.0
        below_threshold = recent["total_sales"] < recent["reconstructed_baseline_sales"]
        consistency_ratio = float(below_threshold.mean())
        below_periods = int(below_threshold.sum())
        event_share = float(recent["event_linked_sales"].sum()) / recent_sales if recent_sales > 0 else 0.0
        yoy_trend_pct = float(recent["yoy_trend_pct"].replace([pd.NA], 0.0).fillna(0.0).iloc[-1])
        target_attainment_pct = float(
            recent["target_attainment_pct"].replace([pd.NA], 0.0).fillna(0.0).mean()
        )

        event_sales = (
            recent_orders[recent_orders["event_id"].notna()]
            .groupby("event_type", as_index=False)["sales_amount"]
            .sum()
            .sort_values("sales_amount", ascending=False)
        )
        dominant_event_type = event_sales.iloc[0]["event_type"] if not event_sales.empty else None

        customer_size = recent["customer_size"].iloc[-1]
        customer_weight = float(config["large_customer_weight"]) if customer_size == "large" else 1.0
        category_weight = float(config["key_category_weight"]) if category_l1 in key_categories else 1.0
        weighted_impact = at_risk_sales * customer_weight * category_weight

        severity = "Normal"
        if (
            delta_pct <= -float(config["critical_drop_pct"])
            and consistency_ratio >= float(config["consistency_threshold"])
            and target_attainment_pct < 0.94
            and weighted_impact >= float(config["high_impact_sales_threshold"]) * 0.35
        ):
            severity = "Critical"
        elif (
            delta_pct <= -float(config["warning_drop_pct"])
            and consistency_ratio >= max(float(config["consistency_threshold"]) - 0.10, 0.45)
            and (target_attainment_pct < 0.98 or yoy_trend_pct < -0.04)
        ):
            severity = "Warning"
        elif (
            delta_pct <= -(float(config["warning_drop_pct"]) * 0.6)
            and below_periods >= max(int(recent_window * 0.5), 1)
        ):
            severity = "Watch"

        interpretation = _derive_interpretation(dominant_event_type, delta_pct, event_share, severity)
        possible_risk_factor = _derive_possible_risk_factor(
            dominant_event_type,
            delta_pct,
            yoy_trend_pct,
            target_attainment_pct,
            event_share,
        )

        signal_rows.append(
            {
                "customer": customer_name,
                "category_l1": category_l1,
                "customer_size": customer_size,
                "recent_sales": recent_sales,
                "baseline_sales": baseline_sales,
                "delta_pct": delta_pct,
                "consistency_ratio": consistency_ratio,
                "below_periods": below_periods,
                "recent_periods": recent_window,
                "event_share": event_share,
                "at_risk_sales": at_risk_sales,
                "weighted_impact": weighted_impact,
                "yoy_trend_pct": yoy_trend_pct,
                "target_attainment_pct": target_attainment_pct,
                "severity": severity,
                "interpretation": interpretation,
                "possible_risk_factor": possible_risk_factor,
                "dominant_event_type": dominant_event_type,
                "severity_rank": SEVERITY_ORDER[severity],
                "severity_color": SEVERITY_COLOR[severity],
            }
        )

    if not signal_rows:
        return pd.DataFrame(
            columns=[
                "customer",
                "category_l1",
                "customer_size",
                "recent_sales",
                "baseline_sales",
                "delta_pct",
                "consistency_ratio",
                "below_periods",
                "recent_periods",
                "event_share",
                "at_risk_sales",
                "weighted_impact",
                "yoy_trend_pct",
                "target_attainment_pct",
                "severity",
                "interpretation",
                "possible_risk_factor",
                "dominant_event_type",
                "severity_rank",
                "severity_color",
            ]
        )

    return (
        pd.DataFrame(signal_rows)
        .sort_values(["severity_rank", "weighted_impact", "delta_pct"], ascending=[False, False, True])
        .reset_index(drop=True)
    )


def summarize_signals(
    filtered_weekly_sales: pd.DataFrame,
    filtered_orders: pd.DataFrame,
    config: dict[str, float | int],
    key_categories: list[str],
) -> pd.DataFrame:
    """Create the main risk signal table used across dashboard pages."""

    signal_rows = []
    recent_window = max(int(config["minimum_duration_weeks"]), 4)

    for (customer_name, category_l1), group in filtered_weekly_sales.groupby(["customer_name", "category_l1"]):
        group = group.sort_values("week_start").copy()
        recent = group.tail(recent_window).copy()
        if len(recent) < recent_window:
            continue

        recent_orders = filtered_orders[
            (filtered_orders["customer_name"] == customer_name)
            & (filtered_orders["category_l1"] == category_l1)
            & (filtered_orders["week_start"].isin(recent["week_start"]))
        ].copy()

        recent_sales = float(recent["total_sales"].sum())
        baseline_sales = float(recent["reconstructed_baseline_sales"].sum())
        at_risk_sales = max(baseline_sales - recent_sales, 0.0)
        delta_pct = (recent_sales / baseline_sales - 1.0) if baseline_sales > 0 else 0.0
        below_threshold = recent["total_sales"] < recent["reconstructed_baseline_sales"]
        consistency_ratio = float(below_threshold.mean())
        below_weeks = int(below_threshold.sum())
        event_share = (
            float(recent["event_linked_sales"].sum()) / recent_sales if recent_sales > 0 else 0.0
        )

        event_sales = (
            recent_orders[recent_orders["event_id"].notna()]
            .groupby("event_type", as_index=False)["sales_amount"]
            .sum()
            .sort_values("sales_amount", ascending=False)
        )
        dominant_event_type = event_sales.iloc[0]["event_type"] if not event_sales.empty else None

        customer_size = recent["customer_size"].iloc[-1]
        customer_weight = float(config["large_customer_weight"]) if customer_size == "large" else 1.0
        category_weight = float(config["key_category_weight"]) if category_l1 in key_categories else 1.0
        weighted_impact = at_risk_sales * customer_weight * category_weight

        severity = "Normal"
        if (
            delta_pct <= -float(config["critical_drop_pct"])
            and consistency_ratio >= float(config["consistency_threshold"])
            and weighted_impact >= float(config["high_impact_sales_threshold"]) * 0.5
            and event_share < 0.45
        ):
            severity = "Critical"
        elif (
            delta_pct <= -float(config["warning_drop_pct"])
            and consistency_ratio >= max(float(config["consistency_threshold"]) - 0.10, 0.45)
            and event_share < 0.45
        ):
            severity = "Warning"
        elif (
            delta_pct <= -(float(config["warning_drop_pct"]) * 0.6)
            and below_weeks >= max(int(recent_window * 0.5), 2)
        ):
            severity = "Watch"
        elif event_share > 0.35 and delta_pct > 0.03:
            severity = "Normal"

        interpretation = _derive_interpretation(dominant_event_type, delta_pct, event_share, severity)

        signal_rows.append(
            {
                "customer": customer_name,
                "category_l1": category_l1,
                "customer_size": customer_size,
                "recent_sales": recent_sales,
                "baseline_sales": baseline_sales,
                "delta_pct": delta_pct,
                "below_weeks": below_weeks,
                "duration_weeks": recent_window,
                "consistency_ratio": consistency_ratio,
                "event_share": event_share,
                "at_risk_sales": at_risk_sales,
                "weighted_impact": weighted_impact,
                "severity": severity,
                "interpretation": interpretation,
                "dominant_event_type": dominant_event_type,
                "severity_rank": SEVERITY_ORDER[severity],
                "severity_color": SEVERITY_COLOR[severity],
            }
        )

    if not signal_rows:
        return pd.DataFrame(
            columns=[
                "customer",
                "category_l1",
                "customer_size",
                "recent_sales",
                "baseline_sales",
                "delta_pct",
                "below_weeks",
                "duration_weeks",
                "consistency_ratio",
                "event_share",
                "at_risk_sales",
                "weighted_impact",
                "severity",
                "interpretation",
                "dominant_event_type",
                "severity_rank",
                "severity_color",
            ]
        )

    return (
        pd.DataFrame(signal_rows)
        .sort_values(["severity_rank", "weighted_impact", "delta_pct"], ascending=[False, False, True])
        .reset_index(drop=True)
    )


def build_kpi_summary(signal_summary: pd.DataFrame, filtered_weekly_sales: pd.DataFrame) -> dict[str, float | int]:
    """Build executive KPIs for the dashboard header."""

    risk_rows = signal_summary[signal_summary["severity"].isin(["Watch", "Warning", "Critical"])]
    return {
        "total_sales": float(filtered_weekly_sales["total_sales"].sum()),
        "reconstructed_baseline_sales": float(filtered_weekly_sales["reconstructed_baseline_sales"].sum()),
        "event_linked_sales": float(filtered_weekly_sales["event_linked_sales"].sum()),
        "hidden_drop_alert_count": int(len(risk_rows)),
        "at_risk_sales_amount": float(risk_rows["at_risk_sales"].sum()),
    }


def build_trend_frame(filtered_weekly_sales: pd.DataFrame) -> pd.DataFrame:
    """Aggregate filtered sales into a single weekly trend for plotting."""

    return (
        filtered_weekly_sales.groupby(["week_start", "year_week"], as_index=False)
        .agg(
            total_sales=("total_sales", "sum"),
            reconstructed_baseline_sales=("reconstructed_baseline_sales", "sum"),
            event_linked_sales=("event_linked_sales", "sum"),
        )
        .sort_values("week_start")
        .reset_index(drop=True)
    )


def build_event_markers(filtered_orders: pd.DataFrame) -> pd.DataFrame:
    """Create a simple weekly event marker layer for charts."""

    event_sales = filtered_orders[filtered_orders["event_id"].notna()].copy()
    if event_sales.empty:
        return pd.DataFrame(columns=["week_start", "event_linked_sales", "event_label"])

    marker = (
        event_sales.groupby(["week_start", "event_type"], as_index=False)["sales_amount"]
        .sum()
        .sort_values(["week_start", "sales_amount"], ascending=[True, False])
    )
    top_event = marker.drop_duplicates("week_start").rename(columns={"sales_amount": "event_linked_sales"})
    top_event["event_label"] = top_event["event_type"].str.replace("_", " ").str.title()
    return top_event[["week_start", "event_linked_sales", "event_label"]]


def build_event_timeline(
    filtered_events: pd.DataFrame,
    selected_customer: str | None = None,
    selected_category: str | None = None,
) -> pd.DataFrame:
    """Prepare a readable event timeline table for deep dives."""

    timeline = filtered_events.copy()
    if selected_customer:
        timeline = timeline[
            timeline["customer_name"].eq(selected_customer) | timeline["customer_id"].eq("MULTI_CUSTOMER")
        ]
    if selected_category:
        timeline = timeline[timeline["category_l1"].eq(selected_category)]

    if timeline.empty:
        return pd.DataFrame(
            columns=[
                "event_type",
                "customer_name",
                "category_l1",
                "start_date",
                "end_date",
                "description",
                "business_reason",
            ]
        )

    timeline = timeline.copy()
    timeline["event_type"] = timeline["event_type"].str.replace("_", " ").str.title()
    return timeline[
        ["event_type", "customer_name", "category_l1", "start_date", "end_date", "description", "business_reason"]
    ].sort_values(["start_date", "event_type"]).reset_index(drop=True)


def build_weekly_detail_frame(
    filtered_weekly_sales: pd.DataFrame,
    filtered_orders: pd.DataFrame,
    selected_customer: str,
    selected_category: str,
) -> pd.DataFrame:
    """Build a recent-week detail table for the deep-dive page."""

    weekly = filtered_weekly_sales[
        (filtered_weekly_sales["customer_name"] == selected_customer)
        & (filtered_weekly_sales["category_l1"] == selected_category)
    ].copy()

    event_weekly = (
        filtered_orders[
            (filtered_orders["customer_name"] == selected_customer)
            & (filtered_orders["category_l1"] == selected_category)
        ]
        .groupby(["week_start", "year_week"], as_index=False)["event_linked_sales"]
        .sum()
    )

    detail = weekly.merge(event_weekly, on=["week_start", "year_week"], how="left", suffixes=("", "_detail"))
    detail["event_linked_sales"] = detail["event_linked_sales_detail"].fillna(detail["event_linked_sales"])
    detail = detail.drop(columns=["event_linked_sales_detail"])
    return detail.sort_values("week_start", ascending=False).reset_index(drop=True)


def summarize_deep_dive_signal(
    signal_summary: pd.DataFrame, selected_customer: str, selected_category: str
) -> dict[str, Any]:
    """Return the signal summary row for one customer-category view."""

    row = signal_summary[
        (signal_summary["customer"] == selected_customer)
        & (signal_summary["category_l1"] == selected_category)
    ]
    if row.empty:
        return {
            "recent_sales": 0.0,
            "baseline_sales": 0.0,
            "delta_pct": 0.0,
            "severity": "Normal",
            "interpretation": "Needs review",
            "at_risk_sales": 0.0,
            "severity_color": SEVERITY_COLOR["Normal"],
        }
    return row.iloc[0].to_dict()


def build_severity_overview(signal_summary: pd.DataFrame) -> pd.DataFrame:
    """Create a small severity distribution table for the configuration page."""

    if signal_summary.empty:
        return pd.DataFrame(columns=["severity", "combination_count", "at_risk_sales"])

    overview = (
        signal_summary.groupby(["severity", "severity_rank"], as_index=False)
        .agg(
            combination_count=("customer", "count"),
            at_risk_sales=("at_risk_sales", "sum"),
        )
        .sort_values("severity_rank", ascending=False)
        .reset_index(drop=True)
    )
    return overview[["severity", "combination_count", "at_risk_sales"]]
