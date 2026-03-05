"""
Backtest entry point.
Uses unified TradingSystemRunner for consistency.
"""
import sys
from dotenv import load_dotenv
from trading_dag.utils.config import load_config
from trading_dag.core.runner import TradingSystemRunner

load_dotenv()

DEFAULT_CONFIG = "config/config.yaml"


def main():
    """Run backtest mode."""
    config_path = DEFAULT_CONFIG
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        config = load_config("config.yaml")

    if config.mode != "backtest":
        print("Please set mode to 'backtest' in config.yaml")
        sys.exit(1)

    runner = TradingSystemRunner(config)
    results = runner.run()

    print("\nBacktest completed successfully.")
    return results


if __name__ == "__main__":
    main()
