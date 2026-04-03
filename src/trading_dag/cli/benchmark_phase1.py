"""
Phase 1 benchmark CLI entry.
"""
import argparse
from typing import Any, Dict

from dotenv import load_dotenv

from trading_dag.benchmark.phase1 import run_phase1_benchmarks
from trading_dag.cli.benchmark_cli_common import (
    as_string_list,
    load_benchmark_options,
    load_unified_benchmark,
    print_suite_outputs,
)

load_dotenv()

DEFAULT_MAIN_CONFIG = "config/benchmark.yaml"
DEFAULT_BENCHMARK_CONFIG = "config/benchmark_phase1.yaml"


def main() -> Dict[str, Any]:
    """Run phase 1 benchmark suite."""
    parser = argparse.ArgumentParser(description="Run Phase 1 benchmark suite")
    parser.add_argument(
        "--config",
        default=DEFAULT_MAIN_CONFIG,
        help=(
            "Primary YAML path. Prefer unified benchmark.yaml with top-level 'main' (engine Config). "
            "If 'main' is absent, the whole file is load_config (legacy flat layout). "
            f"Default: {DEFAULT_MAIN_CONFIG}."
        ),
    )
    parser.add_argument(
        "--benchmark-config",
        default=DEFAULT_BENCHMARK_CONFIG,
        help=(
            "Optional YAML merged into phase options after benchmark.yaml's phase1 block; "
            "duplicate keys win from this file. If the path does not exist, it is ignored. "
            f"Default: {DEFAULT_BENCHMARK_CONFIG}."
        ),
    )
    args = parser.parse_args()

    config, options = load_unified_benchmark(args.config, "phase1")

    if config.mode != "backtest":
        raise ValueError("Phase 1 benchmark requires mode: backtest in config")

    options.update(load_benchmark_options(args.benchmark_config))
    run_buy_and_hold = bool(options.get("run_buy_and_hold", True))
    run_equal_weight_rebalance = bool(options.get("run_equal_weight_rebalance", True))
    rebalance_every_bars = int(options.get("rebalance_every_bars", 24))
    output_dir = str(options.get("output_dir", "output"))
    dag_print_frequency = int(options.get("dag_print_frequency", getattr(config, "print_frequency", 1)))
    dag_use_progress_bar = bool(options.get("dag_use_progress_bar", False))
    include_dag_experiments = as_string_list(options.get("include_dag_experiments"))
    include_baseline_experiments = as_string_list(options.get("include_baseline_experiments"))
    export_individual_results = bool(options.get("export_individual_results", True))
    export_charts = bool(options.get("export_charts", True))

    results = run_phase1_benchmarks(
        config=config,
        run_buy_and_hold=run_buy_and_hold,
        run_equal_weight_rebalance=run_equal_weight_rebalance,
        rebalance_every_bars=rebalance_every_bars,
        output_dir=output_dir,
        dag_print_frequency=dag_print_frequency,
        dag_use_progress_bar=dag_use_progress_bar,
        include_dag_experiments=include_dag_experiments or None,
        include_baseline_experiments=include_baseline_experiments or None,
        export_individual_results=export_individual_results,
        export_charts=export_charts,
    )

    print_suite_outputs(results, "Phase 1")
    return results


if __name__ == "__main__":
    main()
