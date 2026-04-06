"""
Backtest entry point.
Uses unified TradingSystemRunner for consistency.
"""
import argparse
import sys
from dotenv import load_dotenv
from trading_dag.utils.config import load_config
from trading_dag.core.runner import TradingSystemRunner

load_dotenv()

DEFAULT_CONFIG = "config/config.yaml"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run standard backtest mode.")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Path to config YAML.")
    parser.add_argument(
        "--mode-override",
        choices=["backtest", "live"],
        default=None,
        help="Override mode at runtime without editing the YAML file.",
    )
    return parser


def main():
    """Run backtest mode."""
    args = _build_parser().parse_args()
    config_path = args.config
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        config = load_config("config.yaml")

    if args.mode_override:
        config.mode = args.mode_override

    if config.mode != "backtest":
        print("Please set mode to 'backtest' in config.yaml")
        sys.exit(1)

    runner = TradingSystemRunner(config)
    results = runner.run()

    print("\nBacktest completed successfully.")
    return results


if __name__ == "__main__":
    main()
