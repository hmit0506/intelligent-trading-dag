"""
Main entry point for live trading mode and backtest mode.
Uses unified TradingSystemRunner for consistent interface.
"""
from dotenv import load_dotenv
from trading_dag.utils.config import load_config
from trading_dag.core.runner import TradingSystemRunner

load_dotenv()

DEFAULT_CONFIG = "config/config.yaml"


def main():
    """Run the trading system."""
    config_path = DEFAULT_CONFIG
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        config = load_config("config.yaml")

    runner = TradingSystemRunner(config)
    results = runner.run()

    print("\nExecution completed successfully.")
    return results


if __name__ == "__main__":
    main()
