"""
Lab13 Observability Dashboard — Streamlit
Monitors the FastAPI chatbot via GET /metrics and GET /health.
Displays alerts, SLO status, and time-based charts built from polled snapshots.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

import httpx
import plotly.graph_objects as go
import streamlit as st
import yaml
from streamlit_autorefresh import st_autorefresh

API_BASE = "http://localhost:8000"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
HISTORY_LIMIT = 120

st.set_page_config(
    page_title="Lab13 Observability Dashboard",
    page_icon="AI",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --bg: #f5efe4;
        --panel: rgba(255, 252, 246, 0.92);
        --panel-strong: #fffdf8;
        --ink: #172121;
        --muted: #5d6b66;
        --line: rgba(23, 33, 33, 0.10);
        --accent: #0f766e;
        --accent-soft: rgba(15, 118, 110, 0.12);
        --warn: #b45309;
        --warn-soft: rgba(180, 83, 9, 0.12);
        --danger: #b42318;
        --danger-soft: rgba(180, 35, 24, 0.12);
        --ok: #15803d;
        --ok-soft: rgba(21, 128, 61, 0.10);
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(15, 118, 110, 0.16), transparent 28%),
            radial-gradient(circle at top right, rgba(180, 83, 9, 0.12), transparent 24%),
            linear-gradient(180deg, #f7f0e3 0%, #f3eee6 46%, #ece8df 100%);
        color: var(--ink);
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    section[data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid var(--line);
    }

    section[data-testid="stSidebar"] * {
        color: var(--ink) !important;
    }

    /* Viền đỏ cho ô nhập API và Refresh time */
    section[data-testid="stSidebar"] div[data-baseweb="input"],
    section[data-testid="stSidebar"] div[data-baseweb="select"] {
        border: 2px solid var(--danger) !important;
        border-radius: 8px;
    }

    h1, h2, h3 {
        color: var(--ink) !important;
        letter-spacing: -0.02em;
    }

    .hero {
        background: linear-gradient(135deg, rgba(255, 253, 248, 0.96), rgba(250, 244, 233, 0.92));
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 1.4rem 1.6rem;
        box-shadow: 0 16px 40px rgba(65, 54, 32, 0.08);
        margin-bottom: 1rem;
    }

    .hero-kicker {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--accent);
        font-weight: 700;
    }

    .hero-title {
        font-size: 2.15rem;
        line-height: 1.05;
        font-weight: 800;
        margin: 0.2rem 0 0.45rem 0;
    }

    .hero-subtitle {
        color: var(--muted);
        font-size: 1rem;
        margin: 0;
    }

    .status-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        margin-top: 1rem;
    }

    .status-pill {
        border-radius: 999px;
        padding: 0.5rem 0.8rem;
        border: 1px solid var(--line);
        background: rgba(255, 255, 255, 0.62);
        font-size: 0.9rem;
        font-weight: 600;
    }

    .panel {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 1rem 1rem 0.75rem 1rem;
        box-shadow: 0 12px 28px rgba(66, 54, 37, 0.06);
        height: 100%;
    }

    .panel-title {
        font-size: 1.02rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }

    .panel-copy {
        color: var(--muted);
        font-size: 0.92rem;
        margin-bottom: 0.8rem;
    }

    [data-testid="stMetric"] {
        background: var(--panel-strong);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 0.9rem 1rem;
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted) !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
    }

    [data-testid="stMetricValue"] {
        color: var(--ink) !important;
        font-size: 1.6rem !important;
        font-weight: 800 !important;
    }

    .alert-card {
        border-radius: 16px;
        padding: 0.85rem 0.9rem;
        border: 1px solid var(--line);
        background: var(--panel-strong);
        margin-bottom: 0.75rem;
    }

    .alert-card.firing {
        border-color: rgba(180, 35, 24, 0.28);
        background: linear-gradient(180deg, rgba(180, 35, 24, 0.10), rgba(255, 253, 248, 0.96));
    }

    .alert-card.ok {
        border-color: rgba(21, 128, 61, 0.20);
    }

    .alert-topline {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        font-size: 0.93rem;
        font-weight: 800;
    }

    .alert-meta {
        color: var(--muted);
        font-size: 0.85rem;
        margin-top: 0.35rem;
    }

    .chip {
        display: inline-block;
        padding: 0.18rem 0.45rem;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 800;
    }

    .chip-ok {
        background: var(--ok-soft);
        color: var(--ok);
    }

    .chip-firing {
        background: var(--danger-soft);
        color: var(--danger);
    }

    .table-wrap {
        background: var(--panel-strong);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 0.25rem;
    }

    .incident-banner {
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(180, 83, 9, 0.14), rgba(255, 252, 246, 0.94));
        border: 1px solid rgba(180, 83, 9, 0.18);
        color: #7c4807;
        padding: 0.85rem 1rem;
        font-weight: 700;
        margin: 0.75rem 0 1rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300)
def load_alert_rules() -> list[dict]:
    path = CONFIG_DIR / "alert_rules.yaml"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data.get("alerts", [])


@st.cache_data(ttl=300)
def load_slo_config() -> dict:
    path = CONFIG_DIR / "slo.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def fetch_json(url: str) -> dict:
    try:
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception:
        return {}


def fetch_metrics(base_url: str = API_BASE) -> dict:
    return fetch_json(f"{base_url}/metrics")


def fetch_health(base_url: str = API_BASE) -> dict:
    return fetch_json(f"{base_url}/health")


def calculate_error_rate(metrics: dict) -> float:
    traffic = metrics.get("traffic", 0)
    total_errors = sum(metrics.get("error_breakdown", {}).values())
    if traffic <= 0:
        return 0.0
    return round((total_errors / traffic) * 100, 2)


def init_history() -> None:
    if "metric_history" not in st.session_state:
        st.session_state.metric_history = []
    if "last_api_url" not in st.session_state:
        st.session_state.last_api_url = API_BASE


def append_history(api_url: str, metrics: dict) -> None:
    init_history()
    if st.session_state.last_api_url != api_url:
        st.session_state.metric_history = []
        st.session_state.last_api_url = api_url

    now = datetime.now()
    current_traffic = metrics.get("traffic", 0)
    history = st.session_state.metric_history
    previous = history[-1] if history else None

    traffic_delta = current_traffic
    req_per_min = 0.0
    if previous is not None:
        traffic_delta = max(0, current_traffic - previous["traffic"])
        elapsed_seconds = max((now - previous["timestamp"]).total_seconds(), 1)
        req_per_min = round((traffic_delta / elapsed_seconds) * 60, 2)

    history.append(
        {
            "timestamp": now,
            "label": now.strftime("%H:%M:%S"),
            "traffic": current_traffic,
            "traffic_delta": traffic_delta,
            "req_per_min": req_per_min,
            "latency_p95": metrics.get("latency_p95", 0.0),
            "latency_p99": metrics.get("latency_p99", 0.0),
            "error_rate": calculate_error_rate(metrics),
            "avg_cost_usd": metrics.get("avg_cost_usd", 0.0),
            "quality_avg": metrics.get("quality_avg", 0.0),
        }
    )
    st.session_state.metric_history = history[-HISTORY_LIMIT:]


def evaluate_alerts(rules: list[dict], metrics: dict) -> list[dict]:
    error_rate = calculate_error_rate(metrics)
    checks = {
        "high_latency_p95": metrics.get("latency_p95", 0) > 5000,
        "high_error_rate": error_rate > 5,
        "cost_budget_spike": metrics.get("avg_cost_usd", 0) > 0.005,
        "low_quality_score": metrics.get("quality_avg", 1.0) < 0.70 and metrics.get("traffic", 0) > 0,
    }

    results = []
    for rule in rules:
        name = rule.get("name", "unknown")
        results.append(
            {
                "name": name,
                "severity": rule.get("severity", "P2"),
                "condition": rule.get("condition", ""),
                "runbook": rule.get("runbook", ""),
                "firing": checks.get(name, False),
            }
        )
    return results


def evaluate_slo(slo_cfg: dict, metrics: dict) -> list[dict]:
    error_rate = calculate_error_rate(metrics)
    mapping = {
        "latency_p95_ms": {
            "label": "Latency P95",
            "current": metrics.get("latency_p95", 0),
            "unit": "ms",
            "compare": "<=",
        },
        "error_rate_pct": {
            "label": "Error Rate",
            "current": error_rate,
            "unit": "%",
            "compare": "<=",
        },
        "daily_cost_usd": {
            "label": "Total Cost",
            "current": metrics.get("total_cost_usd", 0),
            "unit": "USD",
            "compare": "<=",
        },
        "quality_score_avg": {
            "label": "Quality Avg",
            "current": metrics.get("quality_avg", 0),
            "unit": "score",
            "compare": ">=",
        },
    }

    rows = []
    for key, meta in mapping.items():
        sli = slo_cfg.get("slis", {}).get(key, {})
        objective = sli.get("objective", "—")
        target = sli.get("target", "—")
        current = meta["current"]

        if isinstance(objective, (int, float)) and meta["compare"] == "<=":
            passing = current <= objective
        elif isinstance(objective, (int, float)) and meta["compare"] == ">=":
            passing = current >= objective
        else:
            passing = True

        rows.append(
            {
                "SLI": meta["label"],
                "Objective": f"{objective} {meta['unit']}",
                "Target": f"{target}%",
                "Current": f"{current:.2f} {meta['unit']}" if isinstance(current, float) else f"{current} {meta['unit']}",
                "Status": "PASS" if passing else "FAIL",
            }
        )
    return rows


PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#172121", family="Georgia, 'Times New Roman', serif"),
    margin=dict(l=24, r=18, t=44, b=20),
    height=300,
)


def build_timeseries_figure(
    history: Iterable[dict],
    title: str,
    series: list[dict],
    yaxis_title: str,
    threshold: float | None = None,
    threshold_label: str | None = None,
) -> go.Figure:
    points = list(history)
    fig = go.Figure()
    labels = [item["label"] for item in points]

    for line in series:
        fig.add_trace(
            go.Scatter(
                x=labels,
                y=[item[line["key"]] for item in points],
                mode="lines+markers",
                name=line["name"],
                line=dict(color=line["color"], width=3),
                marker=dict(size=7),
            )
        )

    if threshold is not None:
        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color="#b45309",
            line_width=2,
            annotation_text=threshold_label or "threshold",
            annotation_position="top left",
        )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=title, font=dict(size=17)),
        yaxis_title=yaxis_title,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(showgrid=False, tickangle=-25),
        yaxis=dict(gridcolor="rgba(23,33,33,0.10)"),
        hovermode="x unified",
    )
    return fig


def build_latency_distribution(metrics: dict) -> go.Figure:
    labels = ["P50", "P95", "P99"]
    values = [
        metrics.get("latency_p50", 0),
        metrics.get("latency_p95", 0),
        metrics.get("latency_p99", 0),
    ]

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=["#0f766e", "#c2410c", "#b42318"],
            text=[f"{value:.0f} ms" for value in values],
            textposition="outside",
        )
    )
    fig.add_hline(
        y=3000,
        line_dash="dash",
        line_color="#b45309",
        annotation_text="P95 SLO 3000 ms",
        annotation_position="top left",
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Latency Snapshot", font=dict(size=17)),
        yaxis_title="ms",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(23,33,33,0.10)"),
        showlegend=False,
    )
    return fig


def build_request_chart(history: Iterable[dict]) -> go.Figure:
    points = list(history)
    labels = [item["label"] for item in points]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=labels,
            y=[item["traffic_delta"] for item in points],
            name="New Requests",
            marker_color="#0f766e",
            opacity=0.78,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=[item["traffic"] for item in points],
            name="Total Traffic",
            mode="lines+markers",
            line=dict(color="#172121", width=3),
            yaxis="y2",
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Request Volume Over Time", font=dict(size=17)),
        yaxis=dict(title="new requests", gridcolor="rgba(23,33,33,0.10)"),
        yaxis2=dict(title="total requests", overlaying="y", side="right", showgrid=False),
        xaxis=dict(showgrid=False, tickangle=-25),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    return fig


def build_tokens_chart(metrics: dict) -> go.Figure:
    labels = ["Tokens In", "Tokens Out"]
    values = [metrics.get("tokens_in_total", 0), metrics.get("tokens_out_total", 0)]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=["#0f766e", "#c2410c"],
            text=[f"{value:,}" for value in values],
            textposition="outside",
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Token Totals", font=dict(size=17)),
        yaxis_title="tokens",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(23,33,33,0.10)"),
        showlegend=False,
    )
    return fig


def build_cost_quality_chart(history: Iterable[dict]) -> go.Figure:
    points = list(history)
    labels = [item["label"] for item in points]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=[item["avg_cost_usd"] for item in points],
            mode="lines+markers",
            name="Avg Cost USD",
            line=dict(color="#0f766e", width=3),
            marker=dict(size=7),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=[item["quality_avg"] for item in points],
            mode="lines+markers",
            name="Quality Avg",
            line=dict(color="#b45309", width=3),
            marker=dict(size=7),
            yaxis="y2",
        )
    )
    fig.add_shape(
        type="line",
        x0=0,
        x1=1,
        xref="paper",
        y0=0.75,
        y1=0.75,
        yref="y2",
        line=dict(color="#b45309", width=2, dash="dash"),
    )
    fig.add_annotation(
        x=0,
        xref="paper",
        y=0.75,
        yref="y2",
        text="Quality SLO 0.75",
        showarrow=False,
        xanchor="left",
        yanchor="bottom",
        font=dict(size=12, color="#b45309"),
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Cost / Quality Trend", font=dict(size=17)),
        xaxis=dict(showgrid=False, tickangle=-25),
        yaxis=dict(title="avg cost usd", gridcolor="rgba(23,33,33,0.10)"),
        yaxis2=dict(title="quality", overlaying="y", side="right", range=[0, 1]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    return fig


def render_panel_start(title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{title}</div>
            <div class="panel-copy">{copy}</div>
        """,
        unsafe_allow_html=True,
    )


def render_panel_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_alerts(alerts: list[dict]) -> None:
    render_panel_start("Alert Board", "Live alert evaluation based on the current metrics snapshot and configured rules.")
    if not alerts:
        st.info("No alert rules found in `config/alert_rules.yaml`.")
    for alert in alerts:
        card_class = "firing" if alert["firing"] else "ok"
        chip_class = "chip-firing" if alert["firing"] else "chip-ok"
        status = "FIRING" if alert["firing"] else "OK"
        st.markdown(
            f"""
            <div class="alert-card {card_class}">
                <div class="alert-topline">
                    <span>{alert["name"]}</span>
                    <span class="chip {chip_class}">{status} · {alert["severity"]}</span>
                </div>
                <div class="alert-meta">{alert["condition"]}</div>
                <div class="alert-meta">Runbook: {alert["runbook"] or "not provided"}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    render_panel_end()


def render_slo_table(rows: list[dict]) -> None:
    render_panel_start("SLO Scorecard", "Configured objectives from `config/slo.yaml` against current live values from the API.")
    if rows:
        st.markdown('<div class="table-wrap">', unsafe_allow_html=True)
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No SLO configuration found in `config/slo.yaml`.")
    render_panel_end()


def main() -> None:
    init_history()

    st.sidebar.markdown("## Dashboard Controls")
    api_url = st.sidebar.text_input("API Base URL", value=API_BASE)
    refresh_interval = st.sidebar.selectbox(
        "Refresh cadence",
        options=[5, 10, 15, 30, 60],
        index=2,
        format_func=lambda seconds: f"{seconds} seconds",
    )
    st_autorefresh(interval=refresh_interval * 1000, key="dashboard_refresh")
    st.sidebar.caption("The dashboard keeps a local rolling history of polled snapshots for time-series charts.")

    metrics = fetch_metrics(api_url)
    health = fetch_health(api_url)

    if not metrics:
        st.markdown(
            """
            <div class="hero">
                <div class="hero-kicker">Observability Console</div>
                <div class="hero-title">Dashboard is waiting for the API</div>
                <p class="hero-subtitle">Start the FastAPI app, then refresh this page or keep auto-refresh enabled.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.error(f"Cannot reach `{api_url}`. Expected `GET /metrics` and `GET /health` to be available.")
        return

    append_history(api_url, metrics)
    history = st.session_state.metric_history
    error_rate = calculate_error_rate(metrics)
    alert_results = evaluate_alerts(load_alert_rules(), metrics)
    slo_rows = evaluate_slo(load_slo_config(), metrics)

    last_updated = history[-1]["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    tracing_status = "On" if health.get("tracing_enabled", False) else "Off"
    active_incidents = [name for name, enabled in health.get("incidents", {}).items() if enabled]
    firing_count = sum(1 for item in alert_results if item["firing"])

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-kicker">Observability Console</div>
            <div class="hero-title">Lab13 AI Service Dashboard</div>
            <p class="hero-subtitle">Streamlit dashboard polling the FastAPI app and turning snapshots into a lightweight live control room.</p>
            <div class="status-strip">
                <span class="status-pill">API: {api_url}</span>
                <span class="status-pill">Last update: {last_updated}</span>
                <span class="status-pill">Refresh: every {refresh_interval}s</span>
                <span class="status-pill">Tracing: {tracing_status}</span>
                <span class="status-pill">Firing alerts: {firing_count}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if active_incidents:
        st.markdown(
            f'<div class="incident-banner">Active incidents: {", ".join(active_incidents)}</div>',
            unsafe_allow_html=True,
        )

    top_metrics = st.columns(5)
    top_metrics[0].metric("Traffic", f"{metrics.get('traffic', 0):,}")
    top_metrics[1].metric("Error Rate", f"{error_rate:.2f}%")
    top_metrics[2].metric("Latency P95", f"{metrics.get('latency_p95', 0):.0f} ms")
    top_metrics[3].metric("Avg Cost / Req", f"${metrics.get('avg_cost_usd', 0):.4f}")
    top_metrics[4].metric("Quality Avg", f"{metrics.get('quality_avg', 0):.2f}")

    row_a = st.columns([1.05, 1.35])
    with row_a[0]:
        render_alerts(alert_results)
    with row_a[1]:
        render_slo_table(slo_rows)

    row_b = st.columns(2)
    with row_b[0]:
        render_panel_start("Latency Over Time", "Tracks the live P95 and P99 values across refresh cycles, plus the configured P95 SLO.")
        st.plotly_chart(
            build_timeseries_figure(
                history,
                title="Latency Trend",
                series=[
                    {"key": "latency_p95", "name": "P95", "color": "#c2410c"},
                    {"key": "latency_p99", "name": "P99", "color": "#b42318"},
                ],
                yaxis_title="ms",
                threshold=3000,
                threshold_label="P95 SLO",
            ),
            use_container_width=True,
        )
        render_panel_end()
    with row_b[1]:
        render_panel_start("Request Volume", "Shows how many new requests arrive between polls and the total accumulated traffic.")
        st.plotly_chart(build_request_chart(history), use_container_width=True)
        render_panel_end()

    row_c = st.columns(2)
    with row_c[0]:
        render_panel_start("Error Rate Over Time", "Useful during incident drills to see whether failures are sustained or isolated.")
        st.plotly_chart(
            build_timeseries_figure(
                history,
                title="Error Trend",
                series=[{"key": "error_rate", "name": "Error Rate", "color": "#b42318"}],
                yaxis_title="%",
                threshold=2,
                threshold_label="SLO 2%",
            ),
            use_container_width=True,
        )
        render_panel_end()
    with row_c[1]:
        render_panel_start("Cost And Quality", "Pairs cost per request with quality score so spikes are easier to interpret.")
        st.plotly_chart(build_cost_quality_chart(history), use_container_width=True)
        render_panel_end()

    row_d = st.columns(2)
    with row_d[0]:
        render_panel_start("Latency Snapshot", "Quick distribution view for the current state of P50, P95, and P99.")
        st.plotly_chart(build_latency_distribution(metrics), use_container_width=True)
        render_panel_end()
    with row_d[1]:
        render_panel_start("Token Totals", "Cumulative token usage from the app metrics endpoint.")
        st.plotly_chart(build_tokens_chart(metrics), use_container_width=True)
        render_panel_end()

    st.caption("Current time-series data is built from dashboard polling. If the app restarts or the page is reloaded, the local chart history resets.")


if __name__ == "__main__":
    main()
