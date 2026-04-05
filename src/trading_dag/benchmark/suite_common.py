"""
Shared orchestration helpers for multi-experiment benchmark suites.

Phase 1 and phase 2 share CSV export, ranking, and figure generation here.
"""
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from trading_dag.benchmark.experiment_types import ExperimentResult
from trading_dag.benchmark.figures import export_benchmark_figures


def _experiment_to_summary_row(exp: ExperimentResult) -> Dict[str, Any]:
    return {
        "experiment": exp.name,
        "category": exp.category,
        "initial_portfolio_value": exp.initial_portfolio_value,
        "final_portfolio_value": exp.final_portfolio_value,
        "total_return_pct": exp.total_return_pct,
        "sharpe_ratio": exp.sharpe_ratio,
        "sortino_ratio": exp.sortino_ratio,
        "max_drawdown_pct": exp.max_drawdown_pct,
        "win_rate_pct": exp.win_rate_pct,
        "num_points": exp.num_points,
    }


def export_ranked_suite_outputs(
    experiments: List[ExperimentResult],
    curves: List[pd.DataFrame],
    out_dir: Path,
    file_prefix: str,
    timestamp: str,
    export_individual_results: bool,
    export_charts: bool = True,
    chart_timezone: str = "UTC",
) -> Dict[str, Any]:
    """Build ranked summary DataFrame, write combined and optional per-experiment CSVs."""
    summary_rows = [_experiment_to_summary_row(exp) for exp in experiments]
    summary_df = pd.DataFrame(summary_rows).sort_values(
        by=["total_return_pct", "sharpe_ratio"], ascending=False
    ).reset_index(drop=True)
    summary_df.insert(0, "rank_by_return", range(1, len(summary_df) + 1))

    curves_df = pd.concat(curves, ignore_index=True) if curves else pd.DataFrame()
    if not curves_df.empty:
        curves_df = curves_df[["experiment", "date", "portfolio_value"]]

    summary_path = out_dir / f"{file_prefix}_summary_{timestamp}.csv"
    equity_path = out_dir / f"{file_prefix}_equity_{timestamp}.csv"

    summary_df.to_csv(summary_path, index=False)
    if not curves_df.empty:
        curves_df.to_csv(equity_path, index=False)
    if export_individual_results:
        for exp in experiments:
            single_summary_path = out_dir / f"{file_prefix}_summary_{exp.name}_{timestamp}.csv"
            pd.DataFrame([_experiment_to_summary_row(exp)]).to_csv(single_summary_path, index=False)

    figure_paths: Dict[str, Any] = {}
    if export_charts:
        figure_paths = export_benchmark_figures(
            summary_df,
            curves_df,
            out_dir,
            file_prefix,
            timestamp,
            chart_timezone=chart_timezone,
        )

    return {
        "summary_df": summary_df,
        "curves_df": curves_df,
        "summary_path": str(summary_path),
        "equity_path": str(equity_path) if not curves_df.empty else None,
        "figure_paths": figure_paths,
    }
