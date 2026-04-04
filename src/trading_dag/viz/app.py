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
    SCREEN_LIVE_OUTPUT,
    SCREEN_SETUP,
    SCREENS,
)
from trading_dag.viz.helpers import _list_csvs, _list_jsons, _list_pngs, _short_path_for_ui, project_root
from trading_dag.viz.pickers import VIZ_FOLDER_FEEDBACK_KEY, pick_folder_native_dialog
from trading_dag.viz.screens import backtest_output, benchmark_suite, builder, live_output, setup
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

    if "viz_output_dir" not in st.session_state:
        st.session_state.viz_output_dir = str(default_out)

    out_dir = Path(st.session_state.viz_output_dir).expanduser().resolve()
    path_ok = out_dir.is_dir()

    with st.sidebar:
        st.markdown("**Workspace**")

        fb = st.session_state.pop(VIZ_FOLDER_FEEDBACK_KEY, None)
        if isinstance(fb, dict) and fb.get("kind") == "success":
            st.success(
                f"Output root updated — `{_short_path_for_ui(out_dir)}`",
            )
            st.toast("Output root updated", icon="✅")

        st.caption(f"**Output root:** `{_short_path_for_ui(out_dir)}`")
        st.caption(
            f"Subfolders: `{layout_cfg.backtest_subdir}/`, `{layout_cfg.live_subdir}/` (config.yaml); "
            f"`{layout_cfg.benchmark_subdir}/` (benchmark.yaml)."
        )

        with st.expander(
            "Set output root",
            expanded=not path_ok,
        ):
            st.caption(
                "Choose the **output root** directory (contains backtest, benchmark, and live subfolders). "
                "`output_layout.root` and backtest/live names: `config/config.yaml`. "
                "Benchmark folder name: `config/benchmark.yaml` → `main.output_layout.benchmark_subdir`."
            )
            browse_initial = out_dir if path_ok else default_out
            if st.button("Choose folder…", use_container_width=True, key="ws_browse"):
                picked, picker_err = pick_folder_native_dialog(browse_initial)
                if picked:
                    st.session_state.viz_output_dir = picked
                    st.session_state[VIZ_FOLDER_FEEDBACK_KEY] = {
                        "kind": "success",
                        "path": picked,
                    }
                    st.rerun()
                elif picker_err:
                    st.warning(
                        f"Could not open folder picker ({picker_err}). "
                        "Run Streamlit on a machine with a desktop session, or keep the default folder."
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
            st.caption("Set a valid output root above.")

        screen = st.radio("Screen", SCREENS, index=0, label_visibility="visible")
        if st.button("Refresh"):
            st.rerun()

    if not path_ok:
        st.error(
            "Output root is not a directory. Open **Set output root** in the sidebar and choose a folder.",
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
    else:
        st.error("Unknown screen.")
