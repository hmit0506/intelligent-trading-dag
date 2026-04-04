"""Streamlit: resolve output layout (config.yaml + benchmark subdir from benchmark.yaml)."""
from __future__ import annotations

from pathlib import Path

from trading_dag.utils.output_layout import (
    OutputLayoutConfig,
    read_benchmark_main_output_layout,
    resolve_output_layout_for_benchmark,
)


def get_viz_output_layout(project_root: Path) -> OutputLayoutConfig:
    """
    Same merge as benchmark CLIs: tree root and backtest/live names from ``config/config.yaml``;
    benchmark folder name from ``config/benchmark.yaml`` ``main.output_layout``. Never raise.
    """
    cfg_yaml = project_root / "config" / "config.yaml"
    bench_yaml = project_root / "config" / "benchmark.yaml"
    try:
        return resolve_output_layout_for_benchmark(
            cfg_yaml,
            read_benchmark_main_output_layout(bench_yaml),
        )
    except Exception:
        return OutputLayoutConfig()
