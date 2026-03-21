"""
Phase 1 benchmark runner.

Experiment set:
- Full DAG
- Single strategy variants (MACD / RSI / Bollinger)
- Strong baselines (Buy & Hold / Equal Weight Rebalance)
"""
from datetime import datetime
from time import perf_counter
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from trading_dag.benchmark.phase1_baselines import (
    prepare_primary_klines,
)
from trading_dag.benchmark.phase1_dag import run_dag_variant
from trading_dag.benchmark.phase1_metrics import build_equity_metrics, safe_float
from trading_dag.benchmark.phase1_models import ExperimentResult
from trading_dag.benchmark.phase1_registry import (
    get_phase1_baseline_registry,
    get_phase1_dag_registry,
)


def run_phase1_benchmarks(
    config: Any,
    run_buy_and_hold: bool = True,
    run_equal_weight_rebalance: bool = True,
    rebalance_every_bars: int = 24,
    output_dir: str = "output",
    dag_print_frequency: int = 1000,
    dag_use_progress_bar: bool = True,
    include_dag_experiments: Optional[List[str]] = None,
    include_baseline_experiments: Optional[List[str]] = None,
    export_individual_results: bool = False,
) -> Dict[str, Any]:
    """Run phase 1 benchmark set and export summary tables."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(output_dir)
    out_dir.mkdir(exist_ok=True)

    experiments: List[ExperimentResult] = []
    curves: List[pd.DataFrame] = []

    dag_registry = get_phase1_dag_registry(
        default_strategies=config.signals.strategies,
        include_names=include_dag_experiments,
    )
    baseline_registry = get_phase1_baseline_registry(
        run_buy_and_hold=run_buy_and_hold,
        run_equal_weight_rebalance=run_equal_weight_rebalance,
        rebalance_every_bars=rebalance_every_bars,
        include_names=include_baseline_experiments,
    )
    if not dag_registry and not baseline_registry:
        raise ValueError(
            "No experiments selected. Check include_dag_experiments/include_baseline_experiments "
            "or enable baseline switches."
        )
    total_experiments = len(dag_registry) + len(baseline_registry)
    experiment_idx = 0

    for spec in dag_registry:
        experiment_idx += 1
        print(f"\n[Phase1][{experiment_idx}/{total_experiments}] DAG experiment: {spec.name} - start")
        start_time = perf_counter()
        result, curve = run_dag_variant(
            spec.name,
            spec.strategies,
            config,
            print_frequency=dag_print_frequency,
            use_progress_bar=dag_use_progress_bar,
        )
        elapsed = perf_counter() - start_time
        print(
            f"[Phase1][{experiment_idx}/{total_experiments}] DAG experiment: {spec.name} - done "
            f"(return={result.total_return_pct:.2f}%, sharpe={result.sharpe_ratio:.2f}, {elapsed:.1f}s)"
        )
        experiments.append(result)
        curves.append(curve.assign(experiment=spec.name))
        if export_individual_results:
            single_curve_path = out_dir / f"benchmark_phase1_equity_{spec.name}_{timestamp}.csv"
            curve.assign(experiment=spec.name)[["experiment", "date", "portfolio_value"]].to_csv(
                single_curve_path,
                index=False,
            )

    # Prepare baseline data only once when baseline experiments exist.
    if baseline_registry:
        print("\n[Phase1] Preparing baseline market data once for all baseline experiments...")
        klines = prepare_primary_klines(
            tickers=config.signals.tickers,
            primary_interval=config.primary_interval,
            start_date=config.start_date,
            end_date=config.end_date,
        )

        for spec in baseline_registry:
            experiment_idx += 1
            print(f"\n[Phase1][{experiment_idx}/{total_experiments}] Baseline experiment: {spec.name} - start")
            start_time = perf_counter()
            baseline_curve = spec.simulator(
                tickers=config.signals.tickers,
                klines=klines,
                initial_cash=config.initial_cash,
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
                single_curve_path = out_dir / f"benchmark_phase1_equity_{spec.name}_{timestamp}.csv"
                baseline_curve.assign(experiment=spec.name)[["experiment", "date", "portfolio_value"]].to_csv(
                    single_curve_path,
                    index=False,
                )
            elapsed = perf_counter() - start_time
            print(
                f"[Phase1][{experiment_idx}/{total_experiments}] Baseline experiment: {spec.name} - done "
                f"(return={safe_float(baseline_metrics['total_return_pct']):.2f}%, "
                f"sharpe={safe_float(baseline_metrics['sharpe_ratio']):.2f}, {elapsed:.1f}s)"
            )

    summary_rows = []
    for exp in experiments:
        summary_rows.append(
            {
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
        )

    summary_df = pd.DataFrame(summary_rows).sort_values(
        by=["total_return_pct", "sharpe_ratio"], ascending=False
    ).reset_index(drop=True)
    summary_df.insert(0, "rank_by_return", range(1, len(summary_df) + 1))

    curves_df = pd.concat(curves, ignore_index=True) if curves else pd.DataFrame()
    if not curves_df.empty:
        curves_df = curves_df[["experiment", "date", "portfolio_value"]]

    summary_path = out_dir / f"benchmark_phase1_summary_{timestamp}.csv"
    equity_path = out_dir / f"benchmark_phase1_equity_{timestamp}.csv"

    summary_df.to_csv(summary_path, index=False)
    if not curves_df.empty:
        curves_df.to_csv(equity_path, index=False)
    if export_individual_results:
        for exp in experiments:
            single_summary_path = out_dir / f"benchmark_phase1_summary_{exp.name}_{timestamp}.csv"
            pd.DataFrame(
                [
                    {
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
                ]
            ).to_csv(single_summary_path, index=False)

    return {
        "summary_df": summary_df,
        "curves_df": curves_df,
        "summary_path": str(summary_path),
        "equity_path": str(equity_path) if not curves_df.empty else None,
    }

