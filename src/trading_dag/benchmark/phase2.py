"""
Phase 2 benchmark runner — DAG ablations (single-factor removals).
"""
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional

import pandas as pd

from trading_dag.benchmark.dag_backtest_runner import run_dag_backtest_experiment
from trading_dag.benchmark.experiment_types import ExperimentResult
from trading_dag.benchmark.phase1_registry import get_phase1_baseline_registry
from trading_dag.benchmark.phase2_registry import get_phase2_ablation_registry
from trading_dag.benchmark.suite_common import (
    export_ranked_suite_outputs,
    run_registered_baselines,
)
from trading_dag.utils.output_layout import resolve_benchmark_output_path


def run_phase2_benchmarks(
    config: Any,
    run_buy_and_hold: bool = False,
    run_equal_weight_rebalance: bool = False,
    rebalance_every_bars: int = 24,
    output_dir: Optional[str] = None,
    dag_print_frequency: int = 1,
    dag_use_progress_bar: bool = False,
    include_ablation_experiments: Optional[List[str]] = None,
    include_baseline_experiments: Optional[List[str]] = None,
    export_individual_results: bool = True,
    export_charts: bool = True,
) -> Dict[str, Any]:
    """Run phase 2 ablation set; optional baselines use the same wiring as phase 1."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = resolve_benchmark_output_path(config, output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    file_prefix = "benchmark_phase2"
    phase_tag = "Phase2"

    experiments: List[ExperimentResult] = []
    curves: List[pd.DataFrame] = []

    ablation_registry = get_phase2_ablation_registry(
        default_strategies=config.signals.strategies,
        include_names=include_ablation_experiments,
    )
    baseline_registry = get_phase1_baseline_registry(
        run_buy_and_hold=run_buy_and_hold,
        run_equal_weight_rebalance=run_equal_weight_rebalance,
        rebalance_every_bars=rebalance_every_bars,
        include_names=include_baseline_experiments,
    )
    if not ablation_registry and not baseline_registry:
        raise ValueError(
            "No experiments selected. Check include_ablation_experiments / baseline toggles."
        )
    total_experiments = len(ablation_registry) + len(baseline_registry)
    experiment_idx = 0

    for spec in ablation_registry:
        experiment_idx += 1
        print(f"\n[{phase_tag}][{experiment_idx}/{total_experiments}] Ablation: {spec.name} - start")
        start_time = perf_counter()
        result, curve = run_dag_backtest_experiment(
            spec.name,
            spec.strategies,
            config,
            print_frequency=dag_print_frequency,
            use_progress_bar=dag_use_progress_bar,
            ablation=spec.ablation,
            category="ablation",
        )
        elapsed = perf_counter() - start_time
        print(
            f"[{phase_tag}][{experiment_idx}/{total_experiments}] Ablation: {spec.name} - done "
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

    run_registered_baselines(
        config,
        baseline_registry,
        phase_tag=phase_tag,
        baseline_label="Baseline",
        prep_banner="Preparing baseline market data once for all baseline experiments...",
        file_prefix=file_prefix,
        out_dir=out_dir,
        timestamp=timestamp,
        export_individual_results=export_individual_results,
        experiments=experiments,
        curves=curves,
        experiment_idx=experiment_idx,
        total_experiments=total_experiments,
    )

    return export_ranked_suite_outputs(
        experiments,
        curves,
        out_dir,
        file_prefix,
        timestamp,
        export_individual_results,
        export_charts=export_charts,
    )
