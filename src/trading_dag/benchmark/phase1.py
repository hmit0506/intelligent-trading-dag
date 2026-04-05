"""
Phase 1 benchmark runner.

Experiment set:
- Full DAG
- Single strategy variants (MACD / RSI / Bollinger)
"""
from time import perf_counter
from typing import Any, Dict, List, Optional

import pandas as pd

from trading_dag.benchmark.dag_backtest_runner import run_dag_backtest_experiment
from trading_dag.benchmark.experiment_types import ExperimentResult
from trading_dag.benchmark.phase1_registry import get_phase1_dag_registry
from trading_dag.benchmark.suite_common import export_ranked_suite_outputs
from trading_dag.utils.exchange_time import now_config_wall_strftime
from trading_dag.utils.output_layout import resolve_benchmark_output_path


def run_phase1_benchmarks(
    config: Any,
    output_dir: Optional[str] = None,
    dag_print_frequency: int = 1000,
    dag_use_progress_bar: bool = True,
    include_dag_experiments: Optional[List[str]] = None,
    export_individual_results: bool = True,
    export_charts: bool = True,
) -> Dict[str, Any]:
    """Run phase 1 benchmark set and export summary tables."""
    timestamp = now_config_wall_strftime("%Y%m%d_%H%M%S", getattr(config, "timezone", "UTC"))
    out_dir = resolve_benchmark_output_path(config, output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    file_prefix = "benchmark_phase1"
    phase_tag = "Phase1"

    experiments: List[ExperimentResult] = []
    curves: List[pd.DataFrame] = []

    dag_registry = get_phase1_dag_registry(
        default_strategies=config.signals.strategies,
        include_names=include_dag_experiments,
    )
    if not dag_registry:
        raise ValueError("No DAG experiments selected. Check include_dag_experiments.")
    total_experiments = len(dag_registry)
    experiment_idx = 0

    for spec in dag_registry:
        experiment_idx += 1
        print(f"\n[{phase_tag}][{experiment_idx}/{total_experiments}] DAG experiment: {spec.name} - start")
        start_time = perf_counter()
        result, curve = run_dag_backtest_experiment(
            spec.name,
            spec.strategies,
            config,
            print_frequency=dag_print_frequency,
            use_progress_bar=dag_use_progress_bar,
            ablation=None,
            category="dag",
        )
        elapsed = perf_counter() - start_time
        print(
            f"[{phase_tag}][{experiment_idx}/{total_experiments}] DAG experiment: {spec.name} - done "
            f"(return={result.total_return_pct:.2f}%, sharpe={result.sharpe_ratio:.2f}, {elapsed:.1f}s)"
        )
        experiments.append(result)
        curves.append(curve.assign(experiment=spec.name))
        if export_individual_results:
            single_curve_path = out_dir / f"{file_prefix}_equity_{spec.name}_{timestamp}.csv"
            curve.assign(experiment=spec.name)[["experiment", "date", "portfolio_value"]].to_csv(
                single_curve_path,
                index=False,
            )

    return export_ranked_suite_outputs(
        experiments,
        curves,
        out_dir,
        file_prefix,
        timestamp,
        export_individual_results,
        export_charts=export_charts,
        chart_timezone=getattr(config, "timezone", "UTC"),
    )
