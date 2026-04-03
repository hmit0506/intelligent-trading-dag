"""
Streamlit UI aligned with the exported FYP prototype (light dashboard, blue accents).

Run from repo root:
    uv sync --extra viz
    uv run streamlit run src/trading_dag/viz/streamlit_app.py

Palette is sampled from ``FYP Prototype.pdf`` (light panels ~#c0d8f0, primary blue ~#0048f0).
Adjust ``THEME`` in ``inject_theme_css()`` if the source file changes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

import pandas as pd
import streamlit as st

# Screens (order follows prototype flow: setup → builder → run → detail → dashboard).
SCREEN_SETUP = "Setup & API"
SCREEN_BUILDER = "Fusion Builder"
SCREEN_BACKTEST = "Backtest session"
SCREEN_ANALYST = "Analyst signals"
SCREEN_DASHBOARD = "Dashboard"
SCREEN_EXPORTS = "Charts & files"

SCREENS = [
    SCREEN_DASHBOARD,
    SCREEN_SETUP,
    SCREEN_BUILDER,
    SCREEN_BACKTEST,
    SCREEN_ANALYST,
    SCREEN_EXPORTS,
]


def _project_root() -> Path:
    """Repo root: .../src/trading_dag/viz/streamlit_app.py -> parents[3]."""
    return Path(__file__).resolve().parents[3]


def inject_theme_css() -> None:
    """Inject design tokens derived from the FYP Prototype PDF export."""
    THEME = {
        "bg": "#e8edf5",
        "surface": "#c8dcf2",
        "surface_card": "#f5f8fd",
        "surface_alt": "#a8bcd4",
        "text": "#1c2230",
        "muted": "#5a6578",
        "accent": "#0048f0",
        "accent_soft": "#3078f0",
        "success": "#18a838",
        "danger": "#d82020",
        "font_ui": "'IBM Plex Sans', 'Segoe UI', sans-serif",
        "font_mono": "'IBM Plex Mono', 'Consolas', monospace",
        "radius": "8px",
    }
    st.markdown(
        """
        <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&display=swap" rel="stylesheet">
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <style>
            :root {{
                --viz-bg: {THEME["bg"]};
                --viz-surface: {THEME["surface"]};
                --viz-surface-card: {THEME["surface_card"]};
                --viz-surface-alt: {THEME["surface_alt"]};
                --viz-text: {THEME["text"]};
                --viz-muted: {THEME["muted"]};
                --viz-accent: {THEME["accent"]};
                --viz-accent-soft: {THEME["accent_soft"]};
                --viz-success: {THEME["success"]};
                --viz-danger: {THEME["danger"]};
                --viz-font-ui: {THEME["font_ui"]};
                --viz-font-mono: {THEME["font_mono"]};
                --viz-radius: {THEME["radius"]};
            }}
            html, body, [data-testid="stAppViewContainer"] {{
                background-color: var(--viz-bg) !important;
                color: var(--viz-text);
                font-family: var(--viz-font-ui);
            }}
            [data-testid="stSidebar"] {{
                background-color: var(--viz-surface-card) !important;
                border-right: 1px solid var(--viz-surface-alt);
            }}
            h1, h2, h3 {{ color: var(--viz-text) !important; font-weight: 600; letter-spacing: -0.02em; }}
            [data-testid="stMarkdownContainer"] p {{ color: var(--viz-muted); }}
            .stRadio label, .stCheckbox label, .stSelectbox label, .stTextInput label,
            .stMultiSelect label, .stDateInput label {{ color: var(--viz-text) !important; }}
            [data-testid="stMetricValue"] {{ color: var(--viz-accent) !important; }}
            [data-testid="stMarkdownContainer"] a {{ color: var(--viz-accent); }}
            div[data-baseweb="tab-list"] button {{ font-family: var(--viz-font-ui); }}
            .stButton > button {{
                background-color: var(--viz-accent);
                color: #ffffff;
                border: none;
                border-radius: var(--viz-radius);
                font-weight: 600;
            }}
            .stButton > button:hover {{ background-color: var(--viz-accent-soft); color: #ffffff; }}
            [data-testid="stMetricContainer"] {{
                background: var(--viz-surface-card) !important;
                border: 1px solid var(--viz-surface-alt);
                border-radius: var(--viz-radius);
                padding: 0.75rem 1rem;
            }}
            [data-testid="stMetricLabel"] {{ color: var(--viz-muted) !important; }}
            div[data-testid="stTabs"] [data-baseweb="tab-panel"] {{ padding-top: 1rem; }}
            .viz-page-title {{
                margin: 0 0 0.25rem 0;
                font-size: 1.65rem;
                font-weight: 600;
                color: var(--viz-text);
            }}
            .viz-kicker {{
                color: var(--viz-accent);
                font-size: 0.68rem;
                font-weight: 600;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                margin-bottom: 0.35rem;
            }}
            .viz-panel-title {{
                display: flex;
                align-items: center;
                gap: 0.6rem;
                margin: 1rem 0 0.75rem 0;
                padding-bottom: 0.45rem;
                border-bottom: 1px solid var(--viz-surface-alt);
            }}
            .viz-panel-title span:first-child {{
                width: 3px;
                height: 1.05rem;
                border-radius: 2px;
                background: var(--viz-accent);
            }}
            .viz-panel-title span:last-child {{
                color: var(--viz-text);
                font-weight: 600;
                font-size: 1.02rem;
            }}
            .viz-banner {{
                background: linear-gradient(90deg, var(--viz-surface) 0%, var(--viz-surface-card) 100%);
                border: 1px solid var(--viz-surface-alt);
                border-radius: var(--viz-radius);
                padding: 0.85rem 1.1rem;
                margin-bottom: 1rem;
                color: var(--viz-text);
            }}
            .viz-banner strong {{ color: var(--viz-accent); }}
            [data-testid="stDataFrame"] {{
                border: 1px solid var(--viz-surface-alt);
                border-radius: var(--viz-radius);
                background: var(--viz-surface-card);
                padding: 0.35rem;
            }}
            [data-testid="stPlotlyChart"] {{
                border: 1px solid var(--viz-surface-alt);
                border-radius: var(--viz-radius);
                background: var(--viz-surface-card);
                padding: 0.5rem;
            }}
            [data-testid="stImage"] {{
                border: 1px solid var(--viz-surface-alt);
                border-radius: var(--viz-radius);
                background: var(--viz-surface-card);
                padding: 0.5rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _list_csvs(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)


def _list_pngs(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)


def _list_jsons(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def _is_benchmark_equity_csv(path: Path) -> bool:
    name = path.name.lower()
    return "equity" in name and "benchmark" in name


def _is_benchmark_summary_csv(path: Path) -> bool:
    name = path.name.lower()
    return "summary" in name and "benchmark" in name


def _is_trade_history_csv(path: Path) -> bool:
    """Heuristic: date-like column + ticker + action."""
    try:
        df = pd.read_csv(path, nrows=3)
    except Exception:
        return False
    if df.empty:
        return False
    cols = {c.lower() for c in df.columns}
    if not {"ticker", "action"}.issubset(cols):
        return False
    date_like = bool(
        cols & {"date", "datetime", "time", "open_time", "close_time", "timestamp"}
    )
    return date_like


def _read_equity_df(path: Path) -> Optional[pd.DataFrame]:
    try:
        df = pd.read_csv(path)
    except Exception:
        return None
    if df.empty:
        return None
    cols = {c.lower(): c for c in df.columns}
    if "portfolio_value" not in cols and "Portfolio Value" in df.columns:
        df = df.rename(columns={"Portfolio Value": "portfolio_value"})
    if "experiment" not in df.columns and "Experiment" in df.columns:
        df = df.rename(columns={"Experiment": "experiment"})
    date_col = None
    for key in ("date", "Date", "datetime", "open_time", "close_time"):
        if key in df.columns:
            date_col = key
            break
    if date_col is None:
        return None
    df = df.copy()
    df["_plot_date"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=["_plot_date"])
    if "portfolio_value" not in df.columns:
        candidates = [c for c in df.columns if "value" in c.lower() or "equity" in c.lower()]
        if not candidates:
            return None
        df = df.rename(columns={candidates[0]: "portfolio_value"})
    if "experiment" not in df.columns:
        df["experiment"] = path.stem
    return df


def _plotly_equity(df: pd.DataFrame) -> Any:
    import plotly.express as px

    fig = px.line(
        df,
        x="_plot_date",
        y="portfolio_value",
        color="experiment",
        labels={"_plot_date": "Date", "portfolio_value": "Portfolio value", "experiment": "Run"},
        template="plotly_white",
        color_discrete_sequence=["#0048f0", "#18a838", "#d82020", "#c6a656", "#7c5cff"],
    )
    fig.update_layout(
        paper_bgcolor="#f5f8fd",
        plot_bgcolor="#ffffff",
        font=dict(family="IBM Plex Sans, sans-serif", color="#1c2230"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(90,101,120,0.2)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(90,101,120,0.2)")
    return fig


def _preview_json(path: Path, max_chars: int = 12000) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"(Could not read file: {exc})"
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n… (truncated)"
    return text


def _pick_summary_row(df: pd.DataFrame, experiment: Optional[str]) -> Optional[pd.Series]:
    if df.empty:
        return None
    if experiment and "experiment" in df.columns:
        m = df[df["experiment"].astype(str) == experiment]
        if not m.empty:
            return m.iloc[0]
    return df.iloc[0]


def _safe_float(val: Any) -> Optional[float]:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _metric_from_row(row: pd.Series, *candidates: str) -> Optional[float]:
    lower = {str(k).lower().replace(" ", "_"): k for k in row.index}
    for c in candidates:
        key = c.lower().replace(" ", "_")
        if key in lower:
            return _safe_float(row[lower[key]])
        if c in row.index:
            return _safe_float(row[c])
    return None


def _page_header(kicker: str, title: str, blurb: str) -> None:
    st.markdown(
        f"""
        <div class="viz-kicker">{kicker}</div>
        <div class="viz-page-title">{title}</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(blurb)


def render_screen_setup() -> None:
    _page_header(
        "Security & privacy",
        "Exchange & LLM credentials",
        "The desktop prototype collects keys in-session. **This lab app does not persist secrets.** "
        "Use `.env` / your exchange config for real runs.",
    )
    st.info(
        "Please use **testnet** API keys where possible; simulation is the default—no live orders "
        "from this dashboard."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            '<div class="viz-panel-title"><span></span><span>Exchange account (Binance)</span></div>',
            unsafe_allow_html=True,
        )
        st.text_input("API Key", value="", type="default", key="ex_key", disabled=True)
        st.text_input("API Secret", value="", type="password", key="ex_sec", disabled=True)
        st.caption("Enable inputs only after wiring session-secure storage; defaults are disabled.")
        st.button("Save", key="ex_save", disabled=True)
        st.button("Test", key="ex_test", disabled=True)
    with c2:
        st.markdown(
            '<div class="viz-panel-title"><span></span><span>LLM API</span></div>',
            unsafe_allow_html=True,
        )
        st.text_input("API Key ", value="", type="default", key="llm_key", disabled=True)
        st.text_input("API Secret ", value="", type="password", key="llm_sec", disabled=True)
        st.button("Save ", key="llm_save", disabled=True)
        st.button("Test ", key="llm_test", disabled=True)
    with st.expander("Security & privacy (copy from prototype)"):
        st.markdown(
            """
- API secrets are not kept in plain text in the browser long-term; they are only used for the session.
- Default is testnet / simulation—no real trading.
- Live mode should require explicit confirmation and additional verification.
- Use API keys with trading permissions only; disable withdrawal.
- Rotate keys regularly.
            """
        )


def render_screen_builder(root: Path) -> None:
    _page_header(
        "Fusion Builder",
        "Configure run parameters",
        "Match the prototype builder: dates, interval, tickers, and strategies. "
        "Benchmark execution still runs via the CLI; this block builds the **same intent** for documentation "
        "and copy-paste commands.",
    )
    c1, c2 = st.columns(2)
    with c1:
        st.date_input("Start date", value=None, key="b_start")
        st.date_input("End date", value=None, key="b_end")
        st.selectbox("Interval", ["1 hour", "4 hours", "1 day"], index=0, key="b_interval")
    with c2:
        st.text_input("Initial cash (USD)", value="100000", key="b_cash")
        st.text_input("Tickers (comma-separated)", value="BTCUSDT", key="b_tickers")
        st.text_input("Margin requirement", value="", key="b_margin", placeholder="Optional")
    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Strategies</span></div>',
        unsafe_allow_html=True,
    )
    st.multiselect(
        "Drag-and-drop is not available in Streamlit; select nodes to include",
        ["RSI", "MACD", "Bollinger", "Mean reversion"],
        default=["RSI", "MACD"],
        key="b_strat",
    )
    st.text_input("Model", value="DeepSeek", key="b_model")
    st.checkbox("Show LLM reasoning process", value=True, key="b_reason")
    st.checkbox("Generate and save workflow graph", value=False, key="b_graph")
    st.checkbox("Save decision history to JSON file", value=True, key="b_hist")

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Run via terminal</span></div>',
        unsafe_allow_html=True,
    )
    st.code(
        "uv run python -m trading_dag.cli.benchmark_phase1 --config config/benchmark.yaml\n"
        "# or\n"
        "uv run python -m trading_dag.cli.benchmark_phase2 --config config/benchmark.yaml",
        language="bash",
    )


def render_screen_backtest(
    out_dir: Path,
    summary_paths: List[Path],
    trade_csvs: List[Path],
) -> None:
    _page_header(
        "Backtesting",
        "Session overview",
        "Prototype **BACKTESTING** ribbon with performance tiles and trade history.",
    )
    st.markdown(
        '<div class="viz-banner"><strong>BACKTESTING</strong> — You are in backtesting mode. '
        "This strategy uses virtual funds. Switch to the main trading stack for live mode.</div>",
        unsafe_allow_html=True,
    )
    row_data = None
    if summary_paths:
        spath = st.selectbox("Summary source", summary_paths, format_func=lambda p: p.name, key="bt_sum")
        try:
            sdf = pd.read_csv(spath)
            exp_names: List[str] = []
            if "experiment" in sdf.columns:
                exp_names = sorted(sdf["experiment"].astype(str).unique().tolist())
            chosen = st.selectbox("Experiment", exp_names) if exp_names else None
            row_data = _pick_summary_row(sdf, chosen)
        except Exception as exc:
            st.warning(f"Could not load summary: {exc}")
    if row_data is not None:
        tr = _metric_from_row(row_data, "total_return_pct", "total_return")
        sharpe = _metric_from_row(row_data, "sharpe_ratio", "sharpe")
        mdd = _metric_from_row(row_data, "max_drawdown_pct", "max_drawdown")
        final_v = _metric_from_row(row_data, "final_portfolio_value", "final_value")
        init_v = _metric_from_row(row_data, "initial_portfolio_value", "initial_value")
        pnl = None
        if final_v is not None and init_v is not None:
            pnl = final_v - init_v
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Net P&L", f"${pnl:,.2f}" if pnl is not None else "—")
        m2.metric("Return", f"{tr:.2f}%" if tr is not None else "—")
        m3.metric("Max drawdown", f"{mdd:.2f}%" if mdd is not None else "—")
        m4.metric("Total value", f"${final_v:,.2f}" if final_v is not None else "—")
    else:
        st.info("Add a `benchmark_*_summary_*.csv` under the output folder to populate KPI tiles.")

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Trade history</span></div>',
        unsafe_allow_html=True,
    )
    if not trade_csvs:
        st.caption("No CSV with columns ticker + action + date found in this folder.")
        return
    tpath = st.selectbox("Trade log", trade_csvs, format_func=lambda p: p.name, key="bt_tr")
    try:
        tdf = pd.read_csv(tpath)
        st.dataframe(tdf, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.warning(f"Could not load trades: {exc}")


def render_screen_analyst(jsons: List[Path], other_csvs: List[Path]) -> None:
    _page_header(
        "Analyst signals",
        "Decision detail",
        "Read exported reasoning or narrative logs (JSON / text) in the same structure as the "
        "prototype’s “Detailed Reasoning” panel.",
    )
    if jsons:
        jpath = st.selectbox("Reasoning JSON", jsons, format_func=lambda p: p.name, key="an_json")
        try:
            raw = Path(jpath).read_text(encoding="utf-8")
            data = json.loads(raw)
            st.markdown(
                '<div class="viz-panel-title"><span></span><span>Structured</span></div>',
                unsafe_allow_html=True,
            )
            st.json(data if isinstance(data, (dict, list)) else {"_": data})
            st.markdown(
                '<div class="viz-panel-title"><span></span><span>Detailed reasoning (raw)</span></div>',
                unsafe_allow_html=True,
            )
            st.text_area("Text", value=raw, height=240, key="an_raw", label_visibility="collapsed")
        except json.JSONDecodeError:
            st.code(_preview_json(Path(jpath)), language="json")
    else:
        st.info("No JSON files in the output folder.")
    notes = [p for p in other_csvs if "reason" in p.name.lower() or "signal" in p.name.lower()]
    if notes:
        np_ = st.selectbox("Related CSV", notes, format_func=lambda p: p.name)
        try:
            st.dataframe(pd.read_csv(np_), use_container_width=True, hide_index=True)
        except Exception as exc:
            st.warning(str(exc))


def render_screen_dashboard(
    csvs: List[Path],
    pngs: List[Path],
    jsons: List[Path],
    summary_paths: List[Path],
) -> None:
    _page_header(
        "Dashboard",
        "Portfolio lab",
        "High-level KPIs and benchmark summary—as in the prototype’s results overview "
        "plus artifact counts.",
    )
    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Artifact inventory</span></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("CSV files", len(csvs))
    c2.metric("PNG figures", len(pngs))
    c3.metric("JSON logs", len(jsons))

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Performance summary</span></div>',
        unsafe_allow_html=True,
    )
    if not summary_paths:
        st.info("No `benchmark_*_summary_*.csv` found. Run a benchmark or set the output path.")
        return
    choice = st.selectbox("Summary file", summary_paths, format_func=lambda p: p.name, key="dash_sum")
    try:
        sdf = pd.read_csv(choice)
    except Exception as exc:
        st.warning(f"Could not load summary: {exc}")
        return
    row = _pick_summary_row(sdf, None)
    if row is not None:
        tr = _metric_from_row(row, "total_return_pct")
        sharpe = _metric_from_row(row, "sharpe_ratio")
        mdd = _metric_from_row(row, "max_drawdown_pct")
        final_v = _metric_from_row(row, "final_portfolio_value")
        init_v = _metric_from_row(row, "initial_portfolio_value")
        realized = None
        if final_v is not None and init_v is not None:
            realized = final_v - init_v
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total return", f"{tr:.2f}%" if tr is not None else "—")
        k2.metric(
            "Total realized gains",
            f"${realized:,.2f}" if realized is not None else "—",
        )
        k3.metric("Sharpe ratio", f"{sharpe:+.2f}" if sharpe is not None else "—")
        k4.metric("Maximum drawdown", f"{mdd:.2f}%" if mdd is not None else "—")
    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Exports (prototype copy)</span></div>',
        unsafe_allow_html=True,
    )
    st.caption("PNG — portfolio value chart · JSON — detailed trades · CSV — performance data")
    st.dataframe(sdf, use_container_width=True, hide_index=True)


def render_screen_exports(
    equity_paths: List[Path],
    csvs: List[Path],
    pngs: List[Path],
    jsons: List[Path],
    other_csvs: List[Path],
) -> None:
    _page_header("Charts & files", "Deep dive", "Equity interactively, chart images, and raw paths.")
    tab_eq, tab_fig, tab_raw = st.tabs(["Equity curve", "PNG charts", "Raw files"])
    with tab_eq:
        st.markdown(
            '<div class="viz-panel-title"><span></span><span>Interactive equity</span></div>',
            unsafe_allow_html=True,
        )
        candidates = equity_paths if equity_paths else csvs
        if not candidates:
            st.info("No CSV files.")
        else:
            eq_choice = st.selectbox("Equity CSV", candidates, format_func=lambda p: p.name, key="ex_eq")
            df_eq = _read_equity_df(eq_choice)
            if df_eq is None or df_eq.empty:
                st.warning("Could not parse equity time series (need date + portfolio value).")
            else:
                st.plotly_chart(_plotly_equity(df_eq), use_container_width=True)
                with st.expander("Table preview"):
                    show_cols = [c for c in df_eq.columns if c != "_plot_date"]
                    st.dataframe(df_eq[show_cols].head(500), use_container_width=True, hide_index=True)
    with tab_fig:
        st.markdown(
            '<div class="viz-panel-title"><span></span><span>Exported figures</span></div>',
            unsafe_allow_html=True,
        )
        if not pngs:
            st.info("Enable `export_charts` in benchmark config to generate PNGs.")
        else:
            pic = st.selectbox("Image", pngs, format_func=lambda p: p.name, key="ex_png")
            st.image(str(pic), caption=pic.name, use_container_width=True)
    with tab_raw:
        st.markdown(
            '<div class="viz-panel-title"><span></span><span>Other CSV / JSON</span></div>',
            unsafe_allow_html=True,
        )
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**CSVs**")
            for p in other_csvs[:50]:
                st.text(p.name)
            if len(other_csvs) > 50:
                st.caption(f"+ {len(other_csvs) - 50} more")
        with col_b:
            st.markdown("**JSON preview**")
            if not jsons:
                st.caption("No JSON")
            else:
                j = st.selectbox("Pick JSON", jsons, format_func=lambda p: p.name, key="ex_j")
                snippet = _preview_json(j)
                try:
                    data = json.loads(Path(j).read_text(encoding="utf-8"))
                    st.json(data if isinstance(data, (dict, list)) else {"_": data})
                except json.JSONDecodeError:
                    st.code(snippet, language="json")


def main() -> None:
    st.set_page_config(
        page_title="Trading DAG · FYP Lab",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_theme_css()

    root = _project_root()
    default_out = root / "output"

    with st.sidebar:
        st.markdown("**Workspace**")
        out_input = st.text_input(
            "Output directory",
            value=str(default_out),
            label_visibility="collapsed",
            help="Folder with benchmark/backtest outputs.",
        )
        out_dir = Path(out_input).expanduser().resolve()
        st.caption(f"Root: `{root}`")
        screen = st.radio("Screen", SCREENS, index=0, label_visibility="visible")
        if st.button("Refresh"):
            st.rerun()

    if not out_dir.is_dir():
        st.error(f"Output path is not a directory: `{out_dir}`")
        st.stop()

    csvs = _list_csvs(out_dir)
    pngs = _list_pngs(out_dir)
    jsons = _list_jsons(out_dir)
    equity_paths = [p for p in csvs if _is_benchmark_equity_csv(p)]
    summary_paths = [p for p in csvs if _is_benchmark_summary_csv(p)]
    other_csvs = [p for p in csvs if p not in equity_paths and p not in summary_paths]
    trade_csvs = [p for p in csvs if _is_trade_history_csv(p)]

    if screen == SCREEN_DASHBOARD:
        render_screen_dashboard(csvs, pngs, jsons, summary_paths)
    elif screen == SCREEN_SETUP:
        render_screen_setup()
    elif screen == SCREEN_BUILDER:
        render_screen_builder(root)
    elif screen == SCREEN_BACKTEST:
        render_screen_backtest(out_dir, summary_paths, trade_csvs)
    elif screen == SCREEN_ANALYST:
        render_screen_analyst(jsons, other_csvs)
    else:
        render_screen_exports(equity_paths, csvs, pngs, jsons, other_csvs)


if __name__ == "__main__":
    main()
