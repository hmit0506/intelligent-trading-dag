"""Standard CLI backtest artifacts (``output/<backtest_subdir>/``)."""
from pathlib import Path
from typing import List

import json
import streamlit as st

from trading_dag.viz.helpers import (
    _kpis_from_value_series,
    _list_standard_backtest_logs,
    _list_standard_backtest_pngs,
    _list_standard_backtest_performance_csvs,
    _list_standard_backtest_trade_jsons,
    _page_header,
    _plotly_equity,
    _preview_json,
    _read_standard_backtest_perf_for_plot,
    _workspace_chart_timezone,
)


def _format_compact_currency(value: float | None) -> str:
    """Format currency in compact form to avoid metric truncation."""
    if value is None:
        return "—"
    sign = "-" if value < 0 else ""
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"{sign}${abs_value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"{sign}${abs_value / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"{sign}${abs_value / 1_000:.2f}k"
    return f"{sign}${abs_value:,.2f}"


def render(backtest_dir: Path) -> None:
    perf_csvs = _list_standard_backtest_performance_csvs(backtest_dir)
    trade_jsons = _list_standard_backtest_trade_jsons(backtest_dir)
    std_logs = _list_standard_backtest_logs(backtest_dir)
    std_pngs = _list_standard_backtest_pngs(backtest_dir)

    _page_header(
        "Standard backtest",
        "CLI backtest output",
        "Artifacts from `python -m trading_dag.cli.backtest`: `backtest_performance_*.csv`, "
        "`backtest_trades_*.json`, logs, and optional PNG charts. "
        "Files live under the **backtest** subfolder of the workspace root (see `config.yaml` → `output_layout`).",
    )
    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Artifact inventory</span></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Performance CSV", len(perf_csvs))
    c2.metric("Trade JSON", len(trade_jsons))
    c3.metric("Log files", len(std_logs))
    c4.metric("PNG charts", len(std_pngs))

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Equity & KPIs</span></div>',
        unsafe_allow_html=True,
    )
    if not perf_csvs:
        st.info(
            "No `backtest_performance_*.csv` in the backtest folder. Run a standard backtest from the repo root.",
        )
    else:
        choice = st.selectbox(
            "Performance run",
            perf_csvs,
            format_func=lambda p: p.name,
            key="std_bt_perf",
        )
        plot_df = _read_standard_backtest_perf_for_plot(choice)
        if plot_df is None or plot_df.empty:
            st.warning("Could not read portfolio value time series from this CSV.")
        else:
            chart_tz = _workspace_chart_timezone()
            tr, pnl, sharpe, mdd = _kpis_from_value_series(plot_df["portfolio_value"])
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total return", f"{tr:.2f}%" if tr is not None else "—")
            k2.metric(
                "P&L vs start",
                _format_compact_currency(pnl),
                help=f"Exact value: ${pnl:,.2f}" if pnl is not None else None,
            )
            k3.metric("Sharpe (approx.)", f"{sharpe:+.2f}" if sharpe is not None else "—")
            k4.metric("Max drawdown", f"{mdd:.2f}%" if mdd is not None else "—")
            st.caption(
                "Sharpe here is recomputed from this chart's value series (√252 heuristic). "
                "The backtest engine / exported CSV use √365 on the same run—compare numbers before drawing conclusions."
            )
            st.plotly_chart(_plotly_equity(plot_df, chart_timezone=chart_tz), use_container_width=True)
            with st.expander("Performance table preview"):
                show_cols = [c for c in plot_df.columns if c not in ("_plot_date", "experiment")]
                st.dataframe(plot_df[show_cols].head(500), use_container_width=True, hide_index=True)

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Trade log (JSON)</span></div>',
        unsafe_allow_html=True,
    )
    if not trade_jsons:
        st.caption("No `backtest_trades_*.json` in this folder.")
    else:
        jpath = st.selectbox(
            "Trade log file",
            trade_jsons,
            format_func=lambda p: p.name,
            key="std_bt_trades",
        )
        try:
            raw = Path(jpath).read_text(encoding="utf-8")
            data = json.loads(raw)
            st.json(data if isinstance(data, (dict, list)) else {"_": data})
        except json.JSONDecodeError:
            st.code(_preview_json(Path(jpath)), language="json")
        except Exception as exc:
            st.warning(str(exc))

    with st.expander("Logs & static charts"):
        if std_logs:
            lp = st.selectbox("Log file", std_logs, format_func=lambda p: p.name, key="std_bt_log")
            try:
                st.code(Path(lp).read_text(encoding="utf-8", errors="replace")[:24000], language="text")
            except Exception as exc:
                st.warning(str(exc))
        else:
            st.caption("No `backtest_*.log` files.")
        if std_pngs:
            pp = st.selectbox("PNG chart", std_pngs, format_func=lambda p: p.name, key="std_bt_png")
            st.image(str(pp), caption=pp.name, use_container_width=True)
        else:
            st.caption("No `backtest_portfolio_value_*.png` (saved when the backtest prints the matplotlib summary).")
