"""
Phase 1 benchmark CLI entry.
"""
import argparse
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

from trading_dag.benchmark.phase1 import run_phase1_benchmarks
from trading_dag.utils.config import load_config

load_dotenv()

DEFAULT_MAIN_CONFIG = "config/config.yaml"
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


def main() -> Dict[str, Any]:
    """Run phase 1 benchmark suite."""
    parser = argparse.ArgumentParser(description="Run Phase 1 benchmark suite")
    parser.add_argument(
        "--config",
        default=DEFAULT_MAIN_CONFIG,
        help="Main trading config path",
    )
    parser.add_argument(
        "--benchmark-config",
        default=DEFAULT_BENCHMARK_CONFIG,
        help="Benchmark options yaml path (optional)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    if config.mode != "backtest":
        raise ValueError("Phase 1 benchmark requires mode: backtest in config")

    options = _load_benchmark_options(args.benchmark_config)
    run_buy_and_hold = bool(options.get("run_buy_and_hold", True))
    run_equal_weight_rebalance = bool(options.get("run_equal_weight_rebalance", True))
    rebalance_every_bars = int(options.get("rebalance_every_bars", 24))
    output_dir = str(options.get("output_dir", "output"))

    results = run_phase1_benchmarks(
        config=config,
        run_buy_and_hold=run_buy_and_hold,
        run_equal_weight_rebalance=run_equal_weight_rebalance,
        rebalance_every_bars=rebalance_every_bars,
        output_dir=output_dir,
    )

    summary_df = results["summary_df"]
    print("\nPhase 1 benchmark completed.")
    print(summary_df.to_string(index=False))
    print(f"\nSummary CSV: {results['summary_path']}")
    if results["equity_path"]:
        print(f"Equity CSV: {results['equity_path']}")

    return results


if __name__ == "__main__":
    main()

