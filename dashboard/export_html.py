"""
Export a static HTML version of the business dashboard.

This preview mirrors the Streamlit dashboard structure for cases where opening
`localhost` is unreliable. It keeps the same three-tab business story:
Sales Overview, Risk & Detection, and Rule Configuration.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import plotly.graph_objects as go
from plotly.io import to_html

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.helpers import format_currency, format_percent, load_dashboard_data
from dashboard.logic import (
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
)


OUTPUT_HTML = PROJECT_ROOT / "output" / "dashboard_preview.html"


def build_ranked_bar_chart(frame: pd.DataFrame, category_col: str, value_col: str, color: str) -> go.Figure:
    """Create a restrained horizontal ranking chart."""

    plot_frame = frame.sort_values(value_col, ascending=True).tail(8)
    fig = go.Figure(
        data=[
            go.Bar(
                x=plot_frame[value_col],
                y=plot_frame[category_col],
                orientation="h",
                marker_color=color,
                text=[format_currency(v) for v in plot_frame[value_col]],
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
        xaxis_title="Sales Amount (SEK)",
        yaxis_title="",
    )
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(gridcolor="#D8DDE5")
    return fig


def build_sales_mix_chart(sales_mix: pd.DataFrame) -> go.Figure:
    """Build a business-friendly sales mix chart."""

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
            )
        ]
    )
    fig.update_layout(
        template="plotly_white",
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#FFFFFF",
        xaxis_title="",
        yaxis_title="Sales Amount (SEK)",
    )
    fig.update_yaxes(gridcolor="#D8DDE5")
    return fig


def build_monthly_trend_chart(trend_view: pd.DataFrame) -> go.Figure:
    """Build the monthly sales trend chart."""

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


def build_risk_trend_chart(monthly_sales: pd.DataFrame) -> go.Figure:
    """Build the recent monthly risk chart."""

    trend = (
        monthly_sales.groupby("month_start", as_index=False)
        .agg(
            total_sales=("total_sales", "sum"),
            reconstructed_baseline_sales=("reconstructed_baseline_sales", "sum"),
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
    fig.update_layout(
        template="plotly_white",
        height=330,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#FFFFFF",
        xaxis_title="Month",
        yaxis_title="Sales Amount (SEK)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_yaxes(gridcolor="#D8DDE5")
    return fig


def risk_summary(signals: pd.DataFrame) -> dict[str, int]:
    """Summarize risk counts for the hero row."""

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


def build_top_risk_cards(signals: pd.DataFrame) -> str:
    """Render the top risk cards."""

    top = signals[signals["severity"].isin(["Critical", "Warning", "Watch"])].sort_values(
        ["severity_rank", "weighted_impact"], ascending=[False, False]
    ).head(4)
    if top.empty:
        return '<div class="note-box">No material business risk is currently flagged in the full portfolio view.</div>'

    cards: list[str] = []
    for row in top.itertuples(index=False):
        border_color = {"Critical": "#C62828", "Warning": "#EF6C00", "Watch": "#F9A825"}.get(row.severity, "#EF6C00")
        cards.append(
            f"""
            <div class="risk-card" style="border-left-color:{border_color};">
              <div class="risk-card-title">{row.customer}<br>{row.category_l1}</div>
              <div class="risk-card-delta">{format_percent(row.delta_pct)} vs baseline</div>
              <div class="risk-card-meta">{row.severity} • {row.possible_risk_factor}</div>
              <div class="risk-card-meta">YoY {format_percent(row.yoy_trend_pct)} • Target {format_percent(row.target_attainment_pct)}</div>
              <div class="risk-card-impact">{format_currency(row.recent_sales)} recent sales</div>
            </div>
            """
        )
    return "".join(cards)


def build_risk_table(signals: pd.DataFrame) -> str:
    """Render the prioritized risk table."""

    risk_rows = signals[signals["severity"].isin(["Critical", "Warning", "Watch"])].sort_values(
        ["severity_rank", "weighted_impact"], ascending=[False, False]
    )
    if risk_rows.empty:
        return '<div class="note-box">No material business risk is currently flagged in the full portfolio view.</div>'

    severity_colors = {"Critical": "#C62828", "Warning": "#EF6C00", "Watch": "#F9A825", "Normal": "#2E7D32"}
    rows: list[str] = []
    for row in risk_rows.head(12).itertuples(index=False):
        rows.append(
            f"""
            <tr>
              <td>{row.customer}</td>
              <td>{row.category_l1}</td>
              <td>{format_currency(row.recent_sales)}</td>
              <td>{format_currency(row.baseline_sales)}</td>
              <td><span class="metric-negative">{format_percent(row.delta_pct)}</span></td>
              <td>{format_percent(row.yoy_trend_pct)}</td>
              <td>{format_percent(row.target_attainment_pct)}</td>
              <td><span class="severity-chip" style="background:{severity_colors.get(row.severity, '#EF6C00')};">{row.severity}</span></td>
              <td>{row.possible_risk_factor}</td>
            </tr>
            """
        )
    return f"""
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
          {''.join(rows)}
        </tbody>
      </table>
    </div>
    """


def build_target_table_html(target_view: pd.DataFrame) -> str:
    """Render the target insight table."""

    rows: list[str] = []
    for row in target_view.head(10).itertuples(index=False):
        rows.append(
            f"""
            <tr>
              <td>{row.customer_name}</td>
              <td>{row.category_l1}</td>
              <td>{format_currency(row.total_sales)}</td>
              <td>{format_currency(row.target_sales_amount)}</td>
              <td>{format_percent(row.target_attainment_pct)}</td>
              <td>{format_currency(row.target_gap)}</td>
            </tr>
            """
        )
    return f"""
    <div class="risk-table-shell">
      <table class="risk-table">
        <thead>
          <tr>
            <th>Customer</th>
            <th>Category</th>
            <th>Actual Sales</th>
            <th>Target Sales</th>
            <th>Target Attainment</th>
            <th>Target Gap</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </div>
    """


def build_html() -> str:
    """Build the full static HTML dashboard."""

    tables = load_dashboard_data()
    orders = prepare_orders_enriched(tables)
    weekly_sales = build_weekly_sales(orders, lookback_weeks=8)
    target_table = ensure_target_table(orders)
    monthly_sales = build_monthly_sales(orders, target_table)
    key_categories = identify_key_categories(weekly_sales)
    config = get_default_rule_config()
    signals = summarize_monthly_risks(monthly_sales, orders, config, key_categories)
    summary = risk_summary(signals)

    kpis = build_sales_overview_kpis(monthly_sales)
    customer_view = build_ytd_customer_view(monthly_sales)
    category_view = build_ytd_category_view(monthly_sales)
    sales_mix = build_sales_mix_view(monthly_sales)
    trend_view = build_monthly_trend_view(monthly_sales)
    target_view = build_target_insight_view(monthly_sales)
    severity_view = build_severity_overview(signals)

    customer_chart = to_html(build_ranked_bar_chart(customer_view, "customer_name", "total_sales", "#1F3A5F"), include_plotlyjs="cdn", full_html=False)
    category_chart = to_html(build_ranked_bar_chart(category_view, "category_l1", "ytd_sales", "#6B7A90"), include_plotlyjs=False, full_html=False)
    sales_mix_chart = to_html(build_sales_mix_chart(sales_mix), include_plotlyjs=False, full_html=False)
    monthly_trend_chart = to_html(build_monthly_trend_chart(trend_view), include_plotlyjs=False, full_html=False)
    risk_trend_chart = to_html(build_risk_trend_chart(monthly_sales), include_plotlyjs=False, full_html=False)

    if severity_view.empty:
        severity_chart = '<div class="note-box">No active signals under the current default settings.</div>'
    else:
        fig = go.Figure(
            data=[
                go.Bar(
                    x=severity_view["severity"],
                    y=severity_view["combination_count"],
                    marker_color=[{"Critical": "#C62828", "Warning": "#EF6C00", "Watch": "#F9A825", "Normal": "#2E7D32"}.get(v, "#6B7A90") for v in severity_view["severity"]],
                    text=severity_view["combination_count"],
                    textposition="outside",
                )
            ]
        )
        fig.update_layout(
            template="plotly_white",
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(255,255,255,0)",
            plot_bgcolor="#FFFFFF",
            xaxis_title="Severity",
            yaxis_title="Combination Count",
        )
        fig.update_yaxes(gridcolor="#D8DDE5")
        severity_chart = to_html(fig, include_plotlyjs=False, full_html=False)

    return f"""
    <html>
    <head>
      <meta charset="utf-8">
      <title>Sales Analytics Portfolio Dashboard</title>
      <style>
        body {{
          margin: 0;
          background: #F5F6F8;
          color: #1A1A1A;
          font-family: "Inter", "Segoe UI", sans-serif;
        }}
        .page {{
          max-width: 1360px;
          margin: 0 auto;
          padding: 28px 22px 40px 22px;
        }}
        .hero, .card, .method, .settings {{
          background: #FFFFFF;
          border: 1px solid #E6E8EB;
          border-radius: 12px;
          box-shadow: 0 6px 18px rgba(18, 38, 63, 0.05);
        }}
        .tab-bar {{
          display: inline-flex;
          gap: 8px;
          background: #FFFFFF;
          border: 1px solid #E6E8EB;
          border-radius: 12px;
          padding: 6px;
          margin-bottom: 20px;
        }}
        .tab-button {{
          border: 0;
          background: transparent;
          color: #5A5A5A;
          padding: 10px 16px;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
        }}
        .tab-button.active {{
          color: #1F3A5F;
          box-shadow: inset 0 0 0 1px #C9D2DF;
        }}
        .tab-panel {{ display: none; }}
        .tab-panel.active {{ display: block; }}
        .hero {{
          padding: 20px 22px;
          margin-bottom: 20px;
        }}
        .eyebrow {{
          font-size: 12px;
          color: #5A5A5A;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }}
        h1 {{
          margin: 8px 0;
          font-size: 30px;
        }}
        .sub {{
          color: #5A5A5A;
          max-width: 940px;
          line-height: 1.55;
          font-size: 14px;
        }}
        .kpi-grid {{
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          gap: 14px;
          margin-bottom: 22px;
        }}
        .kpi {{
          padding: 20px 22px;
          min-height: 134px;
        }}
        .kpi-label {{
          color: #5A5A5A;
          font-size: 13px;
          margin-bottom: 8px;
        }}
        .kpi-value {{
          font-size: 31px;
          font-weight: 700;
        }}
        .kpi-note {{
          color: #5A5A5A;
          font-size: 13px;
          margin-top: 8px;
        }}
        .grid-2 {{
          display: grid;
          grid-template-columns: 1.08fr 0.92fr;
          gap: 18px;
          margin-bottom: 22px;
        }}
        .grid-hero {{
          display: grid;
          grid-template-columns: 1.65fr 0.95fr;
          gap: 18px;
          margin-bottom: 22px;
        }}
        .grid-cards {{
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 14px;
        }}
        .card {{
          padding: 16px 18px 12px 18px;
        }}
        .section-title {{
          font-size: 18px;
          font-weight: 600;
          margin: 4px 0 8px 0;
        }}
        .section-subtitle {{
          color: #5A5A5A;
          font-size: 13px;
          margin-bottom: 10px;
        }}
        .risk-card {{
          background: #FFFFFF;
          border: 1px solid #E6E8EB;
          border-left: 6px solid #EF6C00;
          border-radius: 12px;
          padding: 22px;
          min-height: 206px;
          box-shadow: 0 8px 22px rgba(18, 38, 63, 0.06);
        }}
        .risk-card-title {{
          font-size: 21px;
          font-weight: 700;
          line-height: 1.22;
        }}
        .risk-card-delta {{
          font-size: 35px;
          font-weight: 700;
          margin-top: 12px;
        }}
        .risk-card-meta {{
          color: #5A5A5A;
          font-size: 14px;
          margin-top: 8px;
        }}
        .risk-card-impact {{
          font-size: 16px;
          font-weight: 700;
          margin-top: 14px;
        }}
        .method {{
          padding: 18px;
          color: #5A5A5A;
          font-size: 13px;
          line-height: 1.55;
        }}
        .settings {{
          padding: 18px;
          color: #5A5A5A;
          line-height: 1.55;
        }}
        .risk-table-shell {{
          background: #FFFFFF;
          border: 1px solid #E6E8EB;
          border-radius: 12px;
          overflow: hidden;
        }}
        .risk-table {{
          width: 100%;
          border-collapse: separate;
          border-spacing: 0;
          font-size: 14px;
        }}
        .risk-table th {{
          text-align: left;
          color: #5A5A5A;
          background: #FAFBFC;
          padding: 14px 16px;
          border-bottom: 1px solid #E6E8EB;
        }}
        .risk-table td {{
          padding: 18px 16px;
          background: #FFFFFF;
          border-bottom: 10px solid #F5F6F8;
        }}
        .severity-chip {{
          display: inline-block;
          padding: 0.34rem 0.68rem;
          border-radius: 999px;
          font-size: 0.78rem;
          font-weight: 650;
          color: white;
        }}
        .metric-negative {{
          color: #C62828;
          font-weight: 700;
        }}
        .note-box {{
          padding: 16px;
          border-radius: 12px;
          background: #FFFFFF;
          color: #5A5A5A;
          border: 1px solid #E6E8EB;
        }}
      </style>
      <script>
        function showTab(tabId) {{
          document.querySelectorAll('.tab-panel').forEach((panel) => panel.classList.remove('active'));
          document.querySelectorAll('.tab-button').forEach((button) => button.classList.remove('active'));
          document.getElementById(tabId).classList.add('active');
          document.querySelector('[data-tab="' + tabId + '"]').classList.add('active');
        }}
      </script>
    </head>
    <body>
      <div class="page">
        <div class="tab-bar">
          <button class="tab-button active" data-tab="sales-tab" onclick="showTab('sales-tab')">Sales Overview</button>
          <button class="tab-button" data-tab="risk-tab" onclick="showTab('risk-tab')">Risk & Detection</button>
          <button class="tab-button" data-tab="settings-tab" onclick="showTab('settings-tab')">Rule Configuration</button>
        </div>

        <div id="sales-tab" class="tab-panel active">
          <div class="hero">
            <div class="eyebrow">Commercial Analytics Portfolio</div>
            <h1>Sales Overview</h1>
            <div class="sub">A business-first view of commercial performance. This page answers how the business is performing before moving into risk interpretation.</div>
          </div>
          <div class="kpi-grid">
            <div class="card kpi"><div class="kpi-label">YTD Sales Amount</div><div class="kpi-value">{format_currency(kpis['ytd_sales_amount'])}</div><div class="kpi-note">Reported sales year to date</div></div>
            <div class="card kpi"><div class="kpi-label">Current Month Sales Amount</div><div class="kpi-value">{format_currency(kpis['current_month_sales_amount'])}</div><div class="kpi-note">{pd.Timestamp(kpis['current_month']).strftime('%B %Y')}</div></div>
            <div class="card kpi"><div class="kpi-label">Current Month Sales Quantity</div><div class="kpi-value">{int(round(kpis['current_month_sales_quantity'])):,}</div><div class="kpi-note">Line-level order quantity in month</div></div>
            <div class="card kpi"><div class="kpi-label">YTD Growth %</div><div class="kpi-value">{format_percent(kpis['ytd_growth_pct'])}</div><div class="kpi-note">Versus same period last year</div></div>
            <div class="card kpi"><div class="kpi-label">Target Achievement %</div><div class="kpi-value">{format_percent(kpis['target_achievement_pct'])}</div><div class="kpi-note">YTD actual versus target</div></div>
          </div>
          <div class="grid-2">
            <div class="card"><div class="section-title">Top Customers by YTD Sales</div>{customer_chart}</div>
            <div class="card"><div class="section-title">YTD Sales by Product Group</div>{category_chart}</div>
          </div>
          <div class="grid-2">
            <div class="card"><div class="section-title">Monthly Sales Trend</div><div class="section-subtitle">Current year versus target, with previous year as a soft reference.</div>{monthly_trend_chart}</div>
            <div class="card"><div class="section-title">Sales Mix</div><div class="section-subtitle">Separates normal sales from event-linked distortion and hidden gap.</div>{sales_mix_chart}</div>
          </div>
          <div class="card">
            <div class="section-title">Target Insight</div>
            {build_target_table_html(target_view)}
          </div>
        </div>

        <div id="risk-tab" class="tab-panel">
          <div class="hero">
            <div class="eyebrow">Commercial Analytics Portfolio</div>
            <h1>Risk & Detection</h1>
            <div class="sub">A business interpretation layer that highlights where reported sales may be masking weaker underlying demand, target misses, or structural change.</div>
          </div>
          <div class="kpi-grid">
            <div class="card kpi"><div class="kpi-label">Customers at Risk</div><div class="kpi-value">{summary['customers_at_risk']}</div><div class="kpi-note">Active Watch, Warning, or Critical combinations</div></div>
            <div class="card kpi"><div class="kpi-label">Categories at Risk</div><div class="kpi-value">{summary['categories_at_risk']}</div><div class="kpi-note">Product groups with current risk signals</div></div>
            <div class="card kpi"><div class="kpi-label">Hidden Drop Signals</div><div class="kpi-value">{summary['hidden_drop_signals']}</div><div class="kpi-note">Signals without a strong event explanation</div></div>
            <div class="card kpi"><div class="kpi-label">Target Miss Signals</div><div class="kpi-value">{summary['target_miss_signals']}</div><div class="kpi-note">Combinations materially below target</div></div>
            <div class="card kpi"><div class="kpi-label">Structural Shift Signals</div><div class="kpi-value">{summary['structural_shift_signals']}</div><div class="kpi-note">Possible new-normal situations</div></div>
          </div>
          <div class="grid-hero">
            <div>
              <div class="section-title">What should I worry about right now?</div>
              <div class="section-subtitle">Prioritized business risks based on sustained decline, target context, and the strength of event explanation.</div>
              <div class="grid-cards">{build_top_risk_cards(signals)}</div>
            </div>
            <div class="method">
              <div class="section-title" style="margin-top:0;">Business Logic in Plain English</div>
              • Monthly performance is used for the visible risk view to reduce week-to-week noise.<br><br>
              • Baseline is reconstructed from the recent historical median, not from scenario labels.<br><br>
              • Event-linked sales help separate temporary distortion from ordinary commercial demand.<br><br>
              • Alerts highlight sustained underperformance versus baseline, target, or recent trend.
            </div>
          </div>
          <div class="grid-2">
            <div class="card"><div class="section-title">Recent Monthly Pattern</div>{risk_trend_chart}</div>
            <div class="card"><div class="section-title">Prioritized Risk List</div>{build_risk_table(signals)}</div>
          </div>
        </div>

        <div id="settings-tab" class="tab-panel">
          <div class="hero">
            <div class="eyebrow">Commercial Analytics Portfolio</div>
            <h1>Rule Configuration</h1>
            <div class="sub">A lightweight BI settings screen that shows how sensitivity can be tuned for different business contexts.</div>
          </div>
          <div class="grid-2">
            <div class="settings">
              <div class="section-title">Current Default Settings</div>
              Detection basis: Monthly view<br><br>
              Warning threshold: {int(config['warning_drop_pct'] * 100)}%<br><br>
              Critical threshold: {int(config['critical_drop_pct'] * 100)}%<br><br>
              Minimum duration: {config['minimum_duration_weeks']} weeks<br><br>
              Consistency threshold: {int(config['consistency_threshold'] * 100)}%<br><br>
              Business impact threshold: {format_currency(config['high_impact_sales_threshold'])}<br><br>
              Large-customer weighting: {config['large_customer_weight']:.2f}<br><br>
              Key-category weighting: {config['key_category_weight']:.2f}
            </div>
            <div class="card">
              <div class="section-title">Current Signal Mix</div>
              {severity_chart}
            </div>
          </div>
        </div>
      </div>
    </body>
    </html>
    """


def main() -> None:
    """Write the static dashboard preview file."""

    OUTPUT_HTML.write_text(build_html(), encoding="utf-8")
    print(f"Saved static dashboard preview to: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
