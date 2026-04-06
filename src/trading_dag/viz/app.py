"""Streamlit lab entrypoint."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from trading_dag.utils.output_layout import resolve_artifact_root_dirs
from trading_dag.viz.config_sync import get_viz_output_layout
from trading_dag.viz.constants import (
    SCREEN_BACKTEST_OUTPUT,
    SCREEN_BENCHMARK_SUITE,
    SCREEN_BUILDER,
    SCREEN_LIVE_BUILDER,
    SCREEN_LIVE_OUTPUT,
    SCREEN_SETUP,
    SCREEN_STD_BACKTEST_BUILDER,
    SCREENS,
)
from trading_dag.viz.helpers import _list_csvs, _list_jsons, _list_pngs, _short_path_for_ui, project_root
from trading_dag.viz.screens import (
    backtest_builder,
    backtest_output,
    benchmark_suite,
    builder,
    live_builder,
    live_output,
    setup,
)
from trading_dag.viz.theme import inject_theme_css


def main() -> None:
    st.set_page_config(
        page_title="Trading DAG · FYP Lab",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_theme_css()

    root = project_root()
    layout_cfg = get_viz_output_layout(root)
    default_out = (root / layout_cfg.root).expanduser().resolve()
    out_dir = Path(default_out).expanduser().resolve()
    path_ok = out_dir.is_dir()

    with st.sidebar:
        st.markdown("**Workspace**")
        st.caption(f"**Output root (fixed):** `{_short_path_for_ui(out_dir)}`")
        st.caption(
            f"Subfolders: `{layout_cfg.backtest_subdir}/`, `{layout_cfg.live_subdir}/` (config.yaml); "
            f"`{layout_cfg.benchmark_subdir}/` (benchmark.yaml)."
        )

        if path_ok:
            dirs = resolve_artifact_root_dirs(out_dir, layout_cfg)
            n_csv = (
                len(_list_csvs(dirs.backtest))
                + len(_list_csvs(dirs.benchmark))
                + len(_list_csvs(dirs.live))
            )
            n_png = len(_list_pngs(dirs.benchmark)) + len(_list_pngs(dirs.backtest))
            n_json = (
                len(_list_jsons(dirs.benchmark))
                + len(_list_jsons(dirs.backtest))
                + len(_list_jsons(dirs.live))
            )
            st.caption(f"{n_csv} CSV · {n_png} PNG · {n_json} JSON (all subfolders)")
        else:
            st.caption("Output root is invalid. Update `output_layout.root` in `config/config.yaml`.")

        screen = st.radio("Screen", SCREENS, index=0, label_visibility="visible")
        if st.button("Refresh"):
            st.rerun()

    if not path_ok:
        st.error(
            "Output root is not a directory. Update `output_layout.root` in `config/config.yaml`.",
        )
        st.stop()

    dirs = resolve_artifact_root_dirs(out_dir, layout_cfg)
    for sub in (dirs.backtest, dirs.benchmark, dirs.live):
        sub.mkdir(parents=True, exist_ok=True)

    if screen == SCREEN_BACKTEST_OUTPUT:
        backtest_output.render(dirs.backtest)
    elif screen == SCREEN_BENCHMARK_SUITE:
        benchmark_suite.render(dirs.benchmark)
    elif screen == SCREEN_LIVE_OUTPUT:
        live_output.render(dirs.live)
    elif screen == SCREEN_SETUP:
        setup.render()
    elif screen == SCREEN_BUILDER:
        builder.render(root)
    elif screen == SCREEN_STD_BACKTEST_BUILDER:
        backtest_builder.render(root)
    elif screen == SCREEN_LIVE_BUILDER:
        live_builder.render(root)
    else:
        st.error("Unknown screen.")
