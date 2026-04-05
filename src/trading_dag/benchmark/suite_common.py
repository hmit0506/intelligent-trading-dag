"""
Shared orchestration helpers for multi-experiment benchmark suites.

Phase 1 and phase 2 reuse baseline execution, CSV export, and ranking logic here.
"""
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, TYPE_CHECKING

import pandas as pd

from trading_dag.benchmark.baseline_simulators import prepare_primary_klines
from trading_dag.benchmark.initial_nav import benchmark_starting_portfolio_value_usd
from trading_dag.benchmark.equity_metrics import build_equity_metrics, safe_float
from trading_dag.benchmark.experiment_types import ExperimentResult
from trading_dag.benchmark.figures import export_benchmark_figures

if TYPE_CHECKING:
    from trading_dag.benchmark.phase1_registry import BaselineExperimentSpec


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


def run_registered_baselines(
    config: Any,
    baseline_registry: List["BaselineExperimentSpec"],
    *,
    phase_tag: str,
    baseline_label: str,
    prep_banner: str,
    file_prefix: str,
    out_dir: Path,
    timestamp: str,
    export_individual_results: bool,
    experiments: List[ExperimentResult],
    curves: List[pd.DataFrame],
    experiment_idx: int,
    total_experiments: int,
) -> int:
    """
    Execute baseline simulators, append ExperimentResult rows and curves.

    Returns the next experiment index after baselines complete.
    """
    if not baseline_registry:
        return experiment_idx

    print(f"\n[{phase_tag}] {prep_banner}")
    klines = prepare_primary_klines(
        tickers=config.signals.tickers,
        primary_interval=config.primary_interval,
        start_date=config.start_date,
        end_date=config.end_date,
        naive_timezone=getattr(config, "timezone", "UTC"),
    )

    first_bar_close = {
        t: float(klines[t].iloc[0]["close"]) for t in config.signals.tickers
    }
    starting_nav = benchmark_starting_portfolio_value_usd(config, first_bar_close)
    tz = getattr(config, "timezone", "UTC")

    for spec in baseline_registry:
        experiment_idx += 1
        print(f"\n[{phase_tag}][{experiment_idx}/{total_experiments}] {baseline_label}: {spec.name} - start")
        start_time = perf_counter()
        baseline_curve = spec.simulator(
            tickers=config.signals.tickers,
            klines=klines,
            initial_cash=starting_nav,
            display_timezone=tz,
            **spec.kwargs,
        )
        baseline_metrics = build_equity_metrics(baseline_curve)
        experiments.append(
            ExperimentResult(
                name=spec.name,
                category="baseline",
                total_return_pct=safe_float(baseline_metrics["total_return_pct"]),
                sharpe_ratio=safe_float(baseline_metrics["sharpe_ratio"]),
                sortino_ratio=safe_float(baseline_metrics["sortino_ratio"]),
                max_drawdown_pct=safe_float(baseline_metrics["max_drawdown_pct"]),
                win_rate_pct=safe_float(baseline_metrics["win_rate_pct"]),
                final_portfolio_value=safe_float(baseline_metrics["final_portfolio_value"]),
                initial_portfolio_value=safe_float(baseline_metrics["initial_portfolio_value"]),
                num_points=len(baseline_curve),
                equity_curve=baseline_curve,
            )
        )
        curves.append(baseline_curve.assign(experiment=spec.name))
        if export_individual_results:
            single_curve_path = out_dir / f"{file_prefix}_equity_{spec.name}_{timestamp}.csv"
            baseline_curve.assign(experiment=spec.name)[["experiment", "date", "portfolio_value"]].to_csv(
                single_curve_path,
                index=False,
            )
        elapsed = perf_counter() - start_time
        print(
            f"[{phase_tag}][{experiment_idx}/{total_experiments}] {baseline_label}: {spec.name} - done "
            f"(return={safe_float(baseline_metrics['total_return_pct']):.2f}%, "
            f"sharpe={safe_float(baseline_metrics['sharpe_ratio']):.2f}, {elapsed:.1f}s)"
        )

    return experiment_idx


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
