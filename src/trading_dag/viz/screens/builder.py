"""Fusion Builder screen."""
from pathlib import Path

import streamlit as st

from trading_dag.viz.helpers import _page_header


def render(root: Path) -> None:
    _ = root
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
