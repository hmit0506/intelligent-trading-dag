"""
Static figures for benchmark suites (aligned with backtest PNG exports in style).

Uses a non-interactive backend so automated runs do not require a display.
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd

def export_benchmark_figures(
    summary_df: pd.DataFrame,
    curves_df: pd.DataFrame,
    out_dir: Path,
    file_prefix: str,
    timestamp: str,
    *,
    chart_timezone: str = "UTC",
) -> Dict[str, Optional[str]]:
    """
    Write comparison charts next to CSV outputs.

    Returns paths keyed by figure role; values are None if a chart was skipped
    (e.g. empty input).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, Optional[str]] = {
        "equity_absolute": None,
        "equity_normalized": None,
        "returns_bar": None,
    }

    if curves_df is not None and not curves_df.empty and "experiment" in curves_df.columns:
        abs_path = out_dir / f"{file_prefix}_equity_absolute_{timestamp}.png"
        _plot_equity_overlay(
            curves_df,
            abs_path,
            normalized=False,
            title="Portfolio value by experiment",
            chart_timezone=chart_timezone,
        )
        paths["equity_absolute"] = str(abs_path)

        norm_path = out_dir / f"{file_prefix}_equity_normalized_{timestamp}.png"
        _plot_equity_overlay(
            curves_df,
            norm_path,
            normalized=True,
            title="Normalized equity (start = 100)",
            chart_timezone=chart_timezone,
        )
        paths["equity_normalized"] = str(norm_path)

    if summary_df is not None and not summary_df.empty and "experiment" in summary_df.columns:
        bar_path = out_dir / f"{file_prefix}_total_return_bar_{timestamp}.png"
        _plot_total_return_bars(summary_df, bar_path)
        paths["returns_bar"] = str(bar_path)

    return paths


def _merge_coincident_equity_curves(curves_df: pd.DataFrame) -> List[Tuple[str, pd.DataFrame]]:
    """
    Merge experiments whose equity series are numerically identical on the same date index.

    Buy-and-hold and equal-weight rebalance produce the same path when no rebalance fires
    within the window (e.g. fewer bars than ``rebalance_every_bars``), or with a single
    ticker. Plotting once avoids a hidden duplicate line in the legend.
    """
    groups: List[Tuple[str, pd.DataFrame]] = [
        (str(name), grp.sort_values("date").reset_index(drop=True))
        for name, grp in curves_df.groupby("experiment", sort=False)
    ]
    if not groups:
        return []
    atol = 1e-2
    rtol = 1e-9
    merged: List[Tuple[str, pd.DataFrame]] = []
    consumed = [False] * len(groups)

    for i in range(len(groups)):
        if consumed[i]:
            continue
        name_i, g_i = groups[i]
        dates_i = g_i["date"]
        y_i = g_i["portfolio_value"].astype(float).to_numpy()
        cluster_names = [name_i]
        for j in range(i + 1, len(groups)):
            if consumed[j]:
                continue
            name_j, g_j = groups[j]
            if len(g_j) != len(g_i):
                continue
            if not dates_i.equals(g_j["date"]):
                continue
            y_j = g_j["portfolio_value"].astype(float).to_numpy()
            if np.allclose(y_i, y_j, rtol=rtol, atol=atol):
                cluster_names.append(name_j)
                consumed[j] = True
        consumed[i] = True
        label = " / ".join(cluster_names)
        merged.append((label, g_i))

    return merged


def _plot_equity_overlay(
    curves_df: pd.DataFrame,
    out_path: Path,
    *,
    normalized: bool,
    title: str,
    chart_timezone: str = "UTC",
) -> None:
    plt.figure(figsize=(12, 6))
    ax = plt.gca()
    color_cycle = plt.cm.tab10.colors

    plot_series = _merge_coincident_equity_curves(curves_df)
    for i, (exp_name, g) in enumerate(plot_series):
        y = g["portfolio_value"].astype(float)
        if normalized and len(y) > 0:
            first = float(y.iloc[0])
            if abs(first) > 1e-12:
                y = y / first * 100.0
            else:
                y = y * 0.0 + 100.0
        color = color_cycle[i % len(color_cycle)]
        ax.plot(g["date"], y, label=str(exp_name), color=color, linewidth=2, alpha=0.9)

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel("Index (100 = start)" if normalized else "Portfolio value ($)", fontsize=12)
    ax.set_xlabel(f"Date ({chart_timezone})", fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def _plot_total_return_bars(summary_df: pd.DataFrame, out_path: Path) -> None:
    df = summary_df.copy()
    if "total_return_pct" not in df.columns:
        plt.close("all")
        return
    df = df.sort_values("total_return_pct", ascending=True)
    labels = df["experiment"].astype(str).tolist()
    values = df["total_return_pct"].astype(float).tolist()

    plt.figure(figsize=(10, max(4.0, 0.35 * len(labels))))
    colors = ["#2ca02c" if v >= 0 else "#d62728" for v in values]
    plt.barh(labels, values, color=colors, alpha=0.85)
    plt.axvline(0.0, color="black", linewidth=0.8, linestyle="-", alpha=0.4)
    plt.title("Total return by experiment (%)", fontsize=14, fontweight="bold")
    plt.xlabel("Total return %", fontsize=12)
    plt.ylabel("Experiment", fontsize=12)
    plt.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
