"""
Phase 1 benchmark CLI entry.
"""
import argparse
from pathlib import Path
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv

from trading_dag.benchmark.phase1 import run_phase1_benchmarks
from trading_dag.utils.config import Config, load_config

load_dotenv()

DEFAULT_MAIN_CONFIG = "config/benchmark.yaml"
DEFAULT_BENCHMARK_CONFIG = "config/benchmark_phase1.yaml"


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
    """Load yaml file as mapping."""
    yaml_path = Path(path)
    if not yaml_path.exists():
        return {}
    with yaml_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def _as_string_list(raw_value: Any) -> List[str]:
    """Normalize config value to a list of non-empty strings."""
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        return [normalized] if normalized else []
    return []


def main() -> Dict[str, Any]:
    """Run phase 1 benchmark suite."""
    parser = argparse.ArgumentParser(description="Run Phase 1 benchmark suite")
    parser.add_argument(
        "--config",
        default=DEFAULT_MAIN_CONFIG,
        help="Benchmark config path (single-file benchmark.yaml recommended)",
    )
    parser.add_argument(
        "--benchmark-config",
        default=DEFAULT_BENCHMARK_CONFIG,
        help="Benchmark options yaml path (optional)",
    )
    args = parser.parse_args()

    combined_config_data = _load_yaml_mapping(args.config)
    if "main" in combined_config_data:
        main_cfg = combined_config_data.get("main", {})
        if not isinstance(main_cfg, dict):
            raise ValueError("benchmark.yaml field 'main' must be a mapping")
        config = Config(**main_cfg)
        options = combined_config_data.get("phase1", {})
        if options is None:
            options = {}
        if not isinstance(options, dict):
            raise ValueError("benchmark.yaml field 'phase1' must be a mapping")
    else:
        # Backward-compatible behavior for legacy separated files.
        config = load_config(args.config)
        options = {}

    if config.mode != "backtest":
        raise ValueError("Phase 1 benchmark requires mode: backtest in config")

    # Optional external overrides (backward compatibility / quick experiments).
    options.update(_load_benchmark_options(args.benchmark_config))
    run_buy_and_hold = bool(options.get("run_buy_and_hold", True))
    run_equal_weight_rebalance = bool(options.get("run_equal_weight_rebalance", True))
    rebalance_every_bars = int(options.get("rebalance_every_bars", 24))
    output_dir = str(options.get("output_dir", "output"))
    dag_print_frequency = int(options.get("dag_print_frequency", getattr(config, "print_frequency", 1)))
    dag_use_progress_bar = bool(options.get("dag_use_progress_bar", False))
    include_dag_experiments = _as_string_list(options.get("include_dag_experiments"))
    include_baseline_experiments = _as_string_list(options.get("include_baseline_experiments"))
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

    summary_df = results["summary_df"]
    print("\nPhase 1 benchmark completed.")
    print(summary_df.to_string(index=False))
    print(f"\nSummary CSV: {results['summary_path']}")
    if results["equity_path"]:
        print(f"Equity CSV: {results['equity_path']}")
    figure_labels = {
        "equity_absolute": "Equity chart (absolute $)",
        "equity_normalized": "Equity chart (normalized, start=100)",
        "returns_bar": "Total return bar chart",
    }
    for key, path in sorted((results.get("figure_paths") or {}).items()):
        if path:
            print(f"{figure_labels.get(key, key)}: {path}")

    return results


if __name__ == "__main__":
    main()

