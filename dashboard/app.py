"""
Main Streamlit app for the sales analytics portfolio dashboard.

The layout is intentionally business-first. Page one looks like a familiar
commercial reporting dashboard, page two interprets business risk, and page
three exposes the configurable rule settings behind the risk view.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.helpers import format_currency, format_percent, load_dashboard_data
from dashboard.logic import (
    SEVERITY_COLOR,
    build_monthly_sales,
    build_monthly_trend_view,
    build_sales_mix_view,
    build_sales_overview_kpis,
    build_severity_overview,
    build_weekly_sales,
    build_ytd_category_view,
    build_ytd_customer_view,
    build_target_insight_view,
    ensure_target_table,
    get_default_rule_config,
    identify_key_categories,
    prepare_orders_enriched,
    summarize_monthly_risks,
    summarize_signals,
)


st.set_page_config(page_title="Sales Analytics Portfolio", page_icon=":bar_chart:", layout="wide")


def apply_dashboard_style() -> None:
    """Apply a restrained corporate design system to the Streamlit app."""

    st.markdown(
        """
        <style>
        .stApp {
            background: #F5F6F8;
            color: #1A1A1A;
            font-family: "Inter", "Segoe UI", "Helvetica Neue", sans-serif;
        }
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2.2rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            margin-bottom: 1rem;
        }
        .stTabs [data-baseweb="tab"] {
            background: #FFFFFF;
            border: 1px solid #E6E8EB;
            border-radius: 12px;
            color: #5A5A5A;
            font-size: 14px;
            font-weight: 600;
            padding: 0.75rem 1rem;
        }
        .stTabs [aria-selected="true"] {
            color: #1F3A5F;
            border-color: #C9D2DF;
            box-shadow: inset 0 0 0 1px #C9D2DF;
        }
        .hero-card, .surface-card, .method-card, .settings-card {
            background: #FFFFFF;
            border: 1px solid #E6E8EB;
            border-radius: 12px;
            padding: 20px 22px;
            box-shadow: 0 6px 18px rgba(18, 38, 63, 0.05);
        }
        .kpi-card {
            background: #FFFFFF;
            border: 1px solid #E6E8EB;
            border-radius: 12px;
            padding: 20px 22px;
            min-height: 136px;
            box-shadow: 0 6px 18px rgba(18, 38, 63, 0.04);
        }
        .kpi-label {
            color: #5A5A5A;
            font-size: 13px;
            letter-spacing: 0.02em;
            margin-bottom: 0.55rem;
        }
        .kpi-value {
            color: #1A1A1A;
            font-size: 31px;
            font-weight: 700;
            line-height: 1.1;
        }
        .kpi-note {
            color: #5A5A5A;
            font-size: 13px;
            margin-top: 0.55rem;
        }
        .section-title {
            color: #1A1A1A;
            font-size: 18px;
            font-weight: 600;
            margin: 0.1rem 0 0.9rem 0;
        }
        .section-subtitle {
            color: #5A5A5A;
            font-size: 13px;
            margin-bottom: 0.95rem;
        }
        .risk-card {
            background: #FFFFFF;
            border: 1px solid #E6E8EB;
            border-left: 6px solid #EF6C00;
            border-radius: 12px;
            padding: 22px 22px 20px 22px;
            box-shadow: 0 8px 22px rgba(18, 38, 63, 0.06);
            min-height: 210px;
        }
        .risk-card-title {
            color: #1A1A1A;
            font-size: 21px;
            font-weight: 700;
            line-height: 1.22;
        }
        .risk-card-delta {
            color: #1A1A1A;
            font-size: 36px;
            font-weight: 700;
            margin-top: 0.8rem;
        }
        .risk-card-meta {
            color: #5A5A5A;
            font-size: 14px;
            margin-top: 0.65rem;
            line-height: 1.45;
        }
        .risk-card-impact {
            color: #1A1A1A;
            font-size: 16px;
            font-weight: 700;
            margin-top: 1rem;
        }
        .severity-chip {
            display: inline-block;
            padding: 0.34rem 0.68rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 650;
            color: #FFFFFF;
        }
        .risk-table-shell {
            background: #FFFFFF;
            border: 1px solid #E6E8EB;
            border-radius: 12px;
            box-shadow: 0 6px 18px rgba(18, 38, 63, 0.04);
            overflow: hidden;
        }
        .risk-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 14px;
        }
        .risk-table th {
            text-align: left;
            padding: 14px 16px;
            background: #FAFBFC;
            border-bottom: 1px solid #E6E8EB;
            color: #5A5A5A;
            font-weight: 600;
        }
        .risk-table td {
            padding: 18px 16px;
            border-bottom: 10px solid #F5F6F8;
            background: #FFFFFF;
            color: #1A1A1A;
            vertical-align: middle;
        }
        .metric-negative {
            color: #C62828;
            font-weight: 700;
        }
        .metric-emphasis {
            color: #1A1A1A;
            font-weight: 700;
        }
        .logic-bullets {
            color: #5A5A5A;
            font-size: 13px;
            line-height: 1.55;
        }
        .settings-note {
            color: #5A5A5A;
            font-size: 14px;
            line-height: 1.55;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_rule_state() -> None:
    """Seed Streamlit state with configurable business rule defaults."""

    defaults = get_default_rule_config()
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def current_rule_config() -> dict[str, float | int | str]:
    """Read the current settings from Streamlit session state."""

    return {
        "baseline_lookback_weeks": int(st.session_state["baseline_lookback_weeks"]),
        "warning_drop_pct": float(st.session_state["warning_drop_pct"]),
        "critical_drop_pct": float(st.session_state["critical_drop_pct"]),
        "minimum_duration_weeks": int(st.session_state["minimum_duration_weeks"]),
        "consistency_threshold": float(st.session_state["consistency_threshold"]),
        "high_impact_sales_threshold": float(st.session_state["high_impact_sales_threshold"]),
        "large_customer_weight": float(st.session_state["large_customer_weight"]),
        "key_category_weight": float(st.session_state["key_category_weight"]),
        "detection_basis": str(st.session_state["detection_basis"]),
    }


@st.cache_data(show_spinner=False)
def load_dashboard_model(lookback_weeks: int):
    """Load CSV data and prepare reusable reporting datasets."""

    tables = load_dashboard_data()
    orders_enriched = prepare_orders_enriched(tables)
    weekly_sales = build_weekly_sales(orders_enriched, lookback_weeks=lookback_weeks)
    target_table = ensure_target_table(orders_enriched)
    monthly_sales = build_monthly_sales(orders_enriched, target_table)
    key_categories = identify_key_categories(weekly_sales)
    return tables, orders_enriched, weekly_sales, monthly_sales, target_table, key_categories


def render_hero(title: str, subtitle: str) -> None:
    """Render the page title block."""

    st.markdown(
        f"""
        <div class="hero-card">
            <div style="font-size:12px; letter-spacing:0.08em; color:#5A5A5A; text-transform:uppercase;">
                Commercial Analytics Portfolio
            </div>
            <div style="font-size:30px; font-weight:700; color:#1A1A1A; margin-top:0.3rem;">
                {title}
            </div>
            <div style="font-size:14px; color:#5A5A5A; margin-top:0.6rem; max-width:940px; line-height:1.55;">
                {subtitle}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: str, note: str) -> None:
    """Render one KPI card."""

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_ranked_bar_chart(frame: pd.DataFrame, category_col: str, value_col: str, color: str = "#1F3A5F") -> go.Figure:
    """Create a restrained ranked horizontal bar chart."""

    chart_frame = frame.sort_values(value_col, ascending=True).tail(8)
    fig = go.Figure(
        data=[
            go.Bar(
                x=chart_frame[value_col],
                y=chart_frame[category_col],
                orientation="h",
                marker_color=color,
                text=[format_currency(v) for v in chart_frame[value_col]],
                textposition="outside",
                hovertemplate="%{y}<br>SEK %{x:,.0f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        template="plotly_white",
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#FFFFFF",
        xaxis_title="Sales Amount (SEK)",
        yaxis_title="",
    )
    fig.update_xaxes(gridcolor="#D8DDE5")
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    return fig


def build_sales_mix_chart(sales_mix: pd.DataFrame) -> go.Figure:
    """Create a simple business sales mix view without pie charts."""

    palette = {
        "Normal Sales": "#1F3A5F",
        "Event-Linked Sales": "#6B7A90",
        "Hidden Gap": "#EF6C00",
    }
    fig = go.Figure(
        data=[
            go.Bar(
                x=sales_mix["sales_type"],
                y=sales_mix["sales_amount"],
                marker_color=[palette.get(v, "#6B7A90") for v in sales_mix["sales_type"]],
                text=[format_currency(v) for v in sales_mix["sales_amount"]],
                textposition="outside",
                hovertemplate="%{x}<br>SEK %{y:,.0f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        template="plotly_white",
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#FFFFFF",
        xaxis_title="",
        yaxis_title="Sales Amount (SEK)",
    )
    fig.update_yaxes(gridcolor="#D8DDE5")
    return fig


def build_monthly_trend_chart(trend_view: pd.DataFrame) -> go.Figure:
    """Create the monthly commercial trend chart."""

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=trend_view["month_start"],
            y=trend_view["current_year_sales"],
            name="Current Year Sales",
            mode="lines+markers",
            line=dict(color="#1F3A5F", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=trend_view["month_start"],
            y=trend_view["current_year_target"],
            name="Monthly Target",
            mode="lines",
            line=dict(color="#6B7A90", width=2, dash="dot"),
        )
    )
    if trend_view["previous_year_sales"].notna().any():
        fig.add_trace(
            go.Scatter(
                x=trend_view["month_start"],
                y=trend_view["previous_year_sales"],
                name="Previous Year",
                mode="lines",
                line=dict(color="#B0B7C3", width=2, dash="dash"),
            )
        )

    fig.update_layout(
        template="plotly_white",
        height=370,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#FFFFFF",
        xaxis_title="Month",
        yaxis_title="Sales Amount (SEK)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_yaxes(gridcolor="#D8DDE5")
    fig.update_xaxes(gridcolor="rgba(0,0,0,0)")
    return fig


def build_risk_trend_chart(monthly_sales: pd.DataFrame) -> go.Figure:
    """Create a recent monthly actual-vs-baseline chart for risk interpretation."""

    trend = (
        monthly_sales.groupby("month_start", as_index=False)
        .agg(
            total_sales=("total_sales", "sum"),
            reconstructed_baseline_sales=("reconstructed_baseline_sales", "sum"),
            event_linked_sales=("event_linked_sales", "sum"),
        )
        .sort_values("month_start")
        .tail(12)
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=trend["month_start"],
            y=trend["total_sales"],
            name="Reported Sales",
            mode="lines+markers",
            line=dict(color="#1F3A5F", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=trend["month_start"],
            y=trend["reconstructed_baseline_sales"],
            name="Reconstructed Baseline",
            mode="lines",
            line=dict(color="#6B7A90", width=2, dash="dash"),
        )
    )

    gap_frame = trend[trend["reconstructed_baseline_sales"] > trend["total_sales"]]
    if not gap_frame.empty:
        fig.add_trace(
            go.Scatter(
                x=gap_frame["month_start"],
                y=gap_frame["reconstructed_baseline_sales"],
                mode="lines",
                line=dict(width=0),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=gap_frame["month_start"],
                y=gap_frame["total_sales"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(198,40,40,0.15)",
                hoverinfo="skip",
                name="Gap vs Baseline",
            )
        )

    fig.update_layout(
        template="plotly_white",
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#FFFFFF",
        xaxis_title="Month",
        yaxis_title="Sales Amount (SEK)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_yaxes(gridcolor="#D8DDE5")
    return fig


def build_risk_summary(signals: pd.DataFrame) -> dict[str, int]:
    """Build a concise monthly risk summary."""

    risk_rows = signals[signals["severity"].isin(["Critical", "Warning", "Watch"])].copy()
    return {
        "customers_at_risk": int(risk_rows["customer"].nunique()),
        "categories_at_risk": int(risk_rows["category_l1"].nunique()),
        "hidden_drop_signals": int((risk_rows["interpretation"] == "Hidden drop").sum()),
        "target_miss_signals": int((risk_rows["target_attainment_pct"] < 0.95).sum()),
        "structural_shift_signals": int(
            (risk_rows["possible_risk_factor"] == "Structural shift / New normal").sum()
        ),
    }


def render_top_risk_card(risk_row: pd.Series) -> None:
    """Render one executive risk card."""

    severity = risk_row["severity"]
    border_color = SEVERITY_COLOR.get(severity, "#EF6C00")
    st.markdown(
        f"""
        <div class="risk-card" style="border-left-color:{border_color};">
            <div class="risk-card-title">{risk_row['customer']}<br>{risk_row['category_l1']}</div>
            <div class="risk-card-delta">{format_percent(risk_row['delta_pct'])} vs baseline</div>
            <div class="risk-card-meta">{severity} • {risk_row['possible_risk_factor']}</div>
            <div class="risk-card-meta">Recent trend: {format_percent(risk_row['yoy_trend_pct'])} YoY • Target attainment: {format_percent(risk_row['target_attainment_pct'])}</div>
            <div class="risk-card-impact">{format_currency(risk_row['recent_sales'])} recent sales</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_prioritized_risk_table(risk_table: pd.DataFrame) -> None:
    """Render the business-priority risk table."""

    if risk_table.empty:
        st.info("No material business risk is currently flagged in the selected scope.")
        return

    html_rows = []
    for row in risk_table.itertuples(index=False):
        severity_color = SEVERITY_COLOR.get(row.severity, "#EF6C00")
        html_rows.append(
            f"""
            <tr>
                <td>{row.customer}</td>
                <td>{row.category_l1}</td>
                <td>{format_currency(row.recent_sales)}</td>
                <td>{format_currency(row.baseline_sales)}</td>
                <td><span class="metric-negative">{format_percent(row.delta_pct)}</span></td>
                <td>{format_percent(row.yoy_trend_pct)}</td>
                <td>{format_percent(row.target_attainment_pct)}</td>
                <td><span class="severity-chip" style="background:{severity_color};">{row.severity}</span></td>
                <td>{row.possible_risk_factor}</td>
            </tr>
            """
        )

    st.markdown(
        f"""
        <div class="risk-table-shell">
            <table class="risk-table">
                <thead>
                    <tr>
                        <th>Customer</th>
                        <th>Category</th>
                        <th>Recent Sales</th>
                        <th>Baseline</th>
                        <th>Delta vs Baseline</th>
                        <th>YoY Trend</th>
                        <th>Target Attainment</th>
                        <th>Severity</th>
                        <th>Possible Risk Factor</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(html_rows)}
                </tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_risk_view(
    weekly_sales: pd.DataFrame,
    monthly_sales: pd.DataFrame,
    orders_enriched: pd.DataFrame,
    config: dict[str, float | int | str],
    key_categories: list[str],
) -> pd.DataFrame:
    """Build the active risk view based on the selected business basis."""

    if config["detection_basis"] == "weekly":
        weekly_signals = summarize_signals(weekly_sales, orders_enriched, config, key_categories).copy()
        monthly_context = (
            monthly_sales.sort_values("month_start")
            .groupby(["customer_name", "category_l1"], as_index=False)
            .tail(1)[["customer_name", "category_l1", "yoy_trend_pct", "target_attainment_pct"]]
            .rename(columns={"customer_name": "customer"})
        )
        weekly_signals = weekly_signals.merge(monthly_context, on=["customer", "category_l1"], how="left")
        weekly_signals["yoy_trend_pct"] = weekly_signals["yoy_trend_pct"].fillna(0.0)
        weekly_signals["target_attainment_pct"] = weekly_signals["target_attainment_pct"].fillna(1.0)
        weekly_signals["possible_risk_factor"] = weekly_signals["interpretation"].replace(
            {
                "Promo gap": "Promo gap",
                "Structural shift / New normal": "Structural shift / New normal",
                "Event-driven uplift": "Event-driven volatility",
                "Recurring commercial uplift": "Event-driven volatility",
                "Hidden drop": "Demand softening",
                "Needs review": "Needs analyst review",
            }
        )
        return weekly_signals

    return summarize_monthly_risks(monthly_sales, orders_enriched, config, key_categories)


def render_sales_overview_tab(monthly_sales: pd.DataFrame) -> None:
    """Render the executive commercial reporting tab."""

    render_hero(
        "Sales Overview",
        "A business-first view of commercial performance. This page answers how the business is performing before moving into risk interpretation.",
    )
    st.write("")

    kpis = build_sales_overview_kpis(monthly_sales)
    customer_view = build_ytd_customer_view(monthly_sales)
    category_view = build_ytd_category_view(monthly_sales)
    sales_mix = build_sales_mix_view(monthly_sales)
    trend_view = build_monthly_trend_view(monthly_sales)
    target_view = build_target_insight_view(monthly_sales)

    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        render_kpi_card("YTD Sales Amount", format_currency(kpis["ytd_sales_amount"]), "Reported sales year to date")
    with kpi_cols[1]:
        render_kpi_card(
            "Current Month Sales Amount",
            format_currency(kpis["current_month_sales_amount"]),
            kpis["current_month"].strftime("%B %Y"),
        )
    with kpi_cols[2]:
        render_kpi_card(
            "Current Month Sales Quantity",
            f"{int(round(kpis['current_month_sales_quantity'])):,}",
            "Line-level order quantity in month",
        )
    with kpi_cols[3]:
        render_kpi_card("YTD Growth %", format_percent(kpis["ytd_growth_pct"]), "Versus same period last year")
    with kpi_cols[4]:
        render_kpi_card("Target Achievement %", format_percent(kpis["target_achievement_pct"]), "YTD actual versus target")

    st.write("")
    col_a, col_b = st.columns([1.05, 0.95], gap="large")
    with col_a:
        st.markdown('<div class="section-title">Top Customers by YTD Sales</div>', unsafe_allow_html=True)
        st.plotly_chart(build_ranked_bar_chart(customer_view, "customer_name", "total_sales"), use_container_width=True)
    with col_b:
        st.markdown('<div class="section-title">YTD Sales by Product Group</div>', unsafe_allow_html=True)
        st.plotly_chart(build_ranked_bar_chart(category_view, "category_l1", "ytd_sales", color="#6B7A90"), use_container_width=True)

    st.write("")
    col_c, col_d = st.columns([1.3, 0.9], gap="large")
    with col_c:
        st.markdown('<div class="section-title">Monthly Sales Trend</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-subtitle">Current year versus target, with previous year as a soft reference.</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(build_monthly_trend_chart(trend_view), use_container_width=True)
    with col_d:
        st.markdown('<div class="section-title">Sales Mix</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-subtitle">Separates normal sales from event-linked distortion and hidden gap.</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(build_sales_mix_chart(sales_mix), use_container_width=True)

    st.write("")
    st.markdown('<div class="section-title">Target Insight</div>', unsafe_allow_html=True)
    target_display = target_view.copy()
    target_display["Actual Sales"] = target_display["total_sales"].map(format_currency)
    target_display["Target Sales"] = target_display["target_sales_amount"].map(format_currency)
    target_display["Target Attainment"] = target_display["target_attainment_pct"].map(format_percent)
    target_display["Target Gap"] = target_display["target_gap"].map(format_currency)
    target_display = target_display.rename(
        columns={"customer_name": "Customer", "category_l1": "Category"}
    )[["Customer", "Category", "Actual Sales", "Target Sales", "Target Attainment", "Target Gap"]]
    st.dataframe(target_display.head(10), use_container_width=True, hide_index=True)


def render_risk_tab(
    monthly_sales: pd.DataFrame,
    weekly_sales: pd.DataFrame,
    orders_enriched: pd.DataFrame,
    config: dict[str, float | int | str],
    key_categories: list[str],
) -> None:
    """Render the monthly business risk interpretation tab."""

    risk_view = build_risk_view(weekly_sales, monthly_sales, orders_enriched, config, key_categories)
    risk_summary = build_risk_summary(risk_view)

    render_hero(
        "Risk & Detection",
        "A business interpretation layer that highlights where reported sales may be masking weaker underlying demand, target misses, or structural change.",
    )
    st.write("")

    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        render_kpi_card("Customers at Risk", str(risk_summary["customers_at_risk"]), "Active Watch, Warning, or Critical combinations")
    with kpi_cols[1]:
        render_kpi_card("Categories at Risk", str(risk_summary["categories_at_risk"]), "Product groups with current risk signals")
    with kpi_cols[2]:
        render_kpi_card("Hidden Drop Signals", str(risk_summary["hidden_drop_signals"]), "Signals without a strong event explanation")
    with kpi_cols[3]:
        render_kpi_card("Target Miss Signals", str(risk_summary["target_miss_signals"]), "Combinations materially below target")
    with kpi_cols[4]:
        render_kpi_card("Structural Shift Signals", str(risk_summary["structural_shift_signals"]), "Possible new-normal situations")

    st.write("")
    hero_col, logic_col = st.columns([1.65, 0.95], gap="large")
    risk_rows = risk_view[risk_view["severity"].isin(["Critical", "Warning", "Watch"])].copy()
    top_risks = risk_rows.sort_values(["severity_rank", "weighted_impact"], ascending=[False, False]).head(4)

    with hero_col:
        st.markdown('<div class="section-title">What should I worry about right now?</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-subtitle">Prioritized business risks based on sustained decline, target context, and the strength of event explanation.</div>',
            unsafe_allow_html=True,
        )
        if top_risks.empty:
            st.info("No material risk is currently flagged in the selected configuration.")
        else:
            columns = st.columns(len(top_risks), gap="medium")
            for column, (_, row) in zip(columns, top_risks.iterrows()):
                with column:
                    render_top_risk_card(row)

    with logic_col:
        st.markdown('<div class="section-title">Business Logic in Plain English</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="method-card">
                <div class="logic-bullets">
                    • Monthly performance is used for the visible risk view to reduce week-to-week noise.<br><br>
                    • Baseline is reconstructed from the recent historical median, not from scenario labels.<br><br>
                    • Event-linked sales help separate temporary distortion from ordinary commercial demand.<br><br>
                    • Alerts highlight sustained underperformance versus baseline, target, or recent trend.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    chart_col, table_col = st.columns([1.1, 1.25], gap="large")
    with chart_col:
        st.markdown('<div class="section-title">Recent Monthly Pattern</div>', unsafe_allow_html=True)
        st.plotly_chart(build_risk_trend_chart(monthly_sales), use_container_width=True)
    with table_col:
        st.markdown('<div class="section-title">Prioritized Risk List</div>', unsafe_allow_html=True)
        prioritized = risk_rows[
            [
                "customer",
                "category_l1",
                "recent_sales",
                "baseline_sales",
                "delta_pct",
                "yoy_trend_pct",
                "target_attainment_pct",
                "severity",
                "possible_risk_factor",
                "severity_rank",
                "weighted_impact",
            ]
        ].sort_values(["severity_rank", "weighted_impact"], ascending=[False, False])
        render_prioritized_risk_table(prioritized.drop(columns=["severity_rank", "weighted_impact"]).head(12))


def render_configuration_tab(
    monthly_sales: pd.DataFrame,
    weekly_sales: pd.DataFrame,
    orders_enriched: pd.DataFrame,
    config: dict[str, float | int | str],
    key_categories: list[str],
) -> None:
    """Render the business-friendly rule configuration tab."""

    render_hero(
        "Rule Configuration",
        "A lightweight BI settings screen that shows how sensitivity can be tuned for different business contexts.",
    )
    st.write("")

    left, right = st.columns([1.0, 1.15], gap="large")
    with left:
        st.markdown('<div class="settings-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Detection Settings</div>', unsafe_allow_html=True)
        st.radio(
            "Detection Basis",
            options=["monthly", "weekly"],
            key="detection_basis",
            format_func=lambda value: "Monthly view" if value == "monthly" else "Weekly view",
            horizontal=True,
        )
        warning_pct = st.slider(
            "Warning Threshold (%)",
            min_value=3,
            max_value=20,
            value=int(round(float(st.session_state["warning_drop_pct"]) * 100)),
            step=1,
        )
        st.session_state["warning_drop_pct"] = warning_pct / 100
        critical_pct = st.slider(
            "Critical Threshold (%)",
            min_value=5,
            max_value=30,
            value=int(round(float(st.session_state["critical_drop_pct"]) * 100)),
            step=1,
        )
        st.session_state["critical_drop_pct"] = critical_pct / 100
        st.slider("Minimum Duration", min_value=4, max_value=16, step=1, key="minimum_duration_weeks")
        consistency_pct = st.slider(
            "Consistency Threshold (%)",
            min_value=40,
            max_value=90,
            value=int(round(float(st.session_state["consistency_threshold"]) * 100)),
            step=5,
        )
        st.session_state["consistency_threshold"] = consistency_pct / 100
        st.slider(
            "Business Impact Threshold (SEK)",
            min_value=5000,
            max_value=60000,
            step=5000,
            key="high_impact_sales_threshold",
        )
        st.slider("Large-Customer Weighting", min_value=1.0, max_value=1.5, step=0.05, key="large_customer_weight")
        st.slider("Key-Category Weighting", min_value=1.0, max_value=1.4, step=0.05, key="key_category_weight")
        st.markdown(
            """
            <div class="settings-note" style="margin-top:0.9rem;">
                These settings are meant to feel like a reporting tool, not a model console.
                They let the business adjust sensitivity by context without changing the underlying data model.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        risk_view = build_risk_view(weekly_sales, monthly_sales, orders_enriched, config, key_categories)
        overview = build_severity_overview(risk_view)
        st.markdown('<div class="section-title">Current Signal Mix</div>', unsafe_allow_html=True)
        if overview.empty:
            st.info("No active signals under the current settings.")
        else:
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=overview["severity"],
                        y=overview["combination_count"],
                        marker_color=[SEVERITY_COLOR.get(v, "#6B7A90") for v in overview["severity"]],
                        text=overview["combination_count"],
                        textposition="outside",
                    )
                ]
            )
            fig.update_layout(
                template="plotly_white",
                height=320,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(255,255,255,0)",
                plot_bgcolor="#FFFFFF",
                xaxis_title="Severity",
                yaxis_title="Combination Count",
            )
            fig.update_yaxes(gridcolor="#D8DDE5")
            st.plotly_chart(fig, use_container_width=True)

        preview = risk_view[
            [
                "customer",
                "category_l1",
                "severity",
                "possible_risk_factor",
                "delta_pct",
                "target_attainment_pct",
            ]
        ].head(8).copy()
        preview["delta_pct"] = preview["delta_pct"].map(format_percent)
        preview["target_attainment_pct"] = preview["target_attainment_pct"].map(format_percent)
        preview = preview.rename(
            columns={
                "customer": "Customer",
                "category_l1": "Category",
                "severity": "Severity",
                "possible_risk_factor": "Possible Risk Factor",
                "delta_pct": "Delta vs Baseline",
                "target_attainment_pct": "Target Attainment",
            }
        )
        st.markdown('<div class="section-title" style="margin-top:1rem;">Sample Impact of Current Settings</div>', unsafe_allow_html=True)
        st.dataframe(preview, use_container_width=True, hide_index=True)


def main() -> None:
    """Run the Streamlit dashboard."""

    apply_dashboard_style()
    initialize_rule_state()

    config = current_rule_config()
    _, orders_enriched, weekly_sales, monthly_sales, _, key_categories = load_dashboard_model(
        int(config["baseline_lookback_weeks"])
    )

    tabs = st.tabs(["Sales Overview", "Risk & Detection", "Rule Configuration"])
    with tabs[0]:
        render_sales_overview_tab(monthly_sales)
    with tabs[1]:
        render_risk_tab(monthly_sales, weekly_sales, orders_enriched, config, key_categories)
    with tabs[2]:
        render_configuration_tab(monthly_sales, weekly_sales, orders_enriched, config, key_categories)


if __name__ == "__main__":
    main()
