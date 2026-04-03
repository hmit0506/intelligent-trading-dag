"""
Phase 2 benchmark CLI — DAG ablation experiments.
"""
import argparse
from pathlib import Path
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv

from trading_dag.benchmark.phase2 import run_phase2_benchmarks
from trading_dag.utils.config import Config, load_config

load_dotenv()

DEFAULT_MAIN_CONFIG = "config/benchmark.yaml"
DEFAULT_BENCHMARK_CONFIG = "config/benchmark_phase2.yaml"


def _load_benchmark_options(path: str) -> Dict[str, Any]:
    """Load optional benchmark overrides from yaml file."""
    benchmark_path = Path(path)
    if not benchmark_path.exists():
        return {}
    with benchmark_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Benchmark config must be a mapping: {path}")
    return data


def _load_yaml_mapping(path: str) -> Dict[str, Any]:
    yaml_path = Path(path)
    if not yaml_path.exists():
        return {}
    with yaml_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def _as_string_list(raw_value: Any) -> List[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        return [normalized] if normalized else []
    return []


def main() -> Dict[str, Any]:
    parser = argparse.ArgumentParser(description="Run Phase 2 (DAG ablation) benchmark suite")
    parser.add_argument(
        "--config",
        default=DEFAULT_MAIN_CONFIG,
        help="Benchmark config path (unified benchmark.yaml recommended)",
    )
    parser.add_argument(
        "--benchmark-config",
        default=DEFAULT_BENCHMARK_CONFIG,
        help="Optional external yaml overrides (legacy)",
    )
    args = parser.parse_args()

    combined_config_data = _load_yaml_mapping(args.config)
    if "main" in combined_config_data:
        main_cfg = combined_config_data.get("main", {})
        if not isinstance(main_cfg, dict):
            raise ValueError("benchmark.yaml field 'main' must be a mapping")
        config = Config(**main_cfg)
        options = combined_config_data.get("phase2", {})
        if options is None:
            options = {}
        if not isinstance(options, dict):
            raise ValueError("benchmark.yaml field 'phase2' must be a mapping")
    else:
        config = load_config(args.config)
        options = {}

    if config.mode != "backtest":
        raise ValueError("Phase 2 benchmark requires mode: backtest in config")

    options.update(_load_benchmark_options(args.benchmark_config))
    run_buy_and_hold = bool(options.get("run_buy_and_hold", False))
    run_equal_weight_rebalance = bool(options.get("run_equal_weight_rebalance", False))
    rebalance_every_bars = int(options.get("rebalance_every_bars", 24))
    output_dir = str(options.get("output_dir", "output"))
    dag_print_frequency = int(options.get("dag_print_frequency", getattr(config, "print_frequency", 1)))
    dag_use_progress_bar = bool(options.get("dag_use_progress_bar", False))
    include_ablation_experiments = _as_string_list(options.get("include_ablation_experiments"))
    include_baseline_experiments = _as_string_list(options.get("include_baseline_experiments"))
    export_individual_results = bool(options.get("export_individual_results", False))

    results = run_phase2_benchmarks(
        config=config,
        run_buy_and_hold=run_buy_and_hold,
        run_equal_weight_rebalance=run_equal_weight_rebalance,
        rebalance_every_bars=rebalance_every_bars,
        output_dir=output_dir,
        dag_print_frequency=dag_print_frequency,
        dag_use_progress_bar=dag_use_progress_bar,
        include_ablation_experiments=include_ablation_experiments or None,
        include_baseline_experiments=include_baseline_experiments or None,
        export_individual_results=export_individual_results,
    )

    summary_df = results["summary_df"]
    print("\nPhase 2 benchmark completed.")
    print(summary_df.to_string(index=False))
    print(f"\nSummary CSV: {results['summary_path']}")
    if results["equity_path"]:
        print(f"Equity CSV: {results['equity_path']}")
    return results


if __name__ == "__main__":
    main()
