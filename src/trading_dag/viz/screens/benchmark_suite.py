"""Benchmark phase 1/2 suite (``output/<benchmark_subdir>/``)."""
from pathlib import Path
from typing import List

import json
import pandas as pd
import streamlit as st

from trading_dag.viz.helpers import (
    _benchmark_suite_chart_timezone,
    _is_benchmark_equity_csv,
    _is_benchmark_summary_csv,
    _list_csvs,
    _list_jsons,
    _list_pngs,
    _metric_from_row,
    _page_header,
    _pick_summary_row,
    _plotly_equity,
    _preview_json,
    _read_equity_df,
)


def render(benchmark_dir: Path) -> None:
    csvs = _list_csvs(benchmark_dir)
    pngs = _list_pngs(benchmark_dir)
    jsons = _list_jsons(benchmark_dir)
    equity_paths = [p for p in csvs if _is_benchmark_equity_csv(p)]
    summary_paths = [p for p in csvs if _is_benchmark_summary_csv(p)]
    other_csvs = [p for p in csvs if p not in equity_paths and p not in summary_paths]

    _page_header(
        "Benchmark suite",
        "Phase 1 / Phase 2 outputs",
        "Suite summary CSVs, equity curves, comparison PNGs, and JSON logs under the **benchmark** subfolder.",
    )

    tab_sum, tab_eq, tab_fig, tab_raw = st.tabs(["Summary", "Equity curve", "PNG charts", "Raw files"])

    with tab_sum:
        st.markdown(
            '<div class="viz-panel-title"><span></span><span>Artifact inventory (all types)</span></div>',
            unsafe_allow_html=True,
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("CSV files", len(csvs))
        c2.metric("PNG figures", len(pngs))
        c3.metric("JSON logs", len(jsons))

        st.markdown(
            '<div class="viz-panel-title"><span></span><span>Benchmark performance summary</span></div>',
            unsafe_allow_html=True,
        )
        if not summary_paths:
            st.info("No `benchmark_*_summary_*.csv` found. Run phase 1/2 benchmarks.")
        else:
            choice = st.selectbox(
                "Summary file",
                summary_paths,
                format_func=lambda p: p.name,
                key="dash_sum",
            )
            try:
                sdf = pd.read_csv(choice)
            except Exception as exc:
                st.warning(f"Could not load summary: {exc}")
            else:
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
                    '<div class="viz-panel-title"><span></span><span>Suite summary table</span></div>',
                    unsafe_allow_html=True,
                )
                st.dataframe(sdf, use_container_width=True, hide_index=True)

    with tab_eq:
        st.markdown(
            '<div class="viz-panel-title"><span></span><span>Interactive equity</span></div>',
            unsafe_allow_html=True,
        )
        candidates: List[Path] = equity_paths if equity_paths else csvs
        if not candidates:
            st.info("No CSV files in the benchmark folder.")
        else:
            eq_choice = st.selectbox("Equity CSV", candidates, format_func=lambda p: p.name, key="ex_eq")
            df_eq = _read_equity_df(eq_choice)
            if df_eq is None or df_eq.empty:
                st.warning("Could not parse equity time series (need date + portfolio value).")
            else:
                chart_tz = _benchmark_suite_chart_timezone()
                st.plotly_chart(_plotly_equity(df_eq, chart_timezone=chart_tz), use_container_width=True)
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
