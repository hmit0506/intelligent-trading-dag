"""
Backtest entry point.
"""
import os
import sys
from dotenv import load_dotenv
from utils.config import load_config
from backtest.engine import Backtester

# Add parent directory to path to access gateway
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

load_dotenv()

if __name__ == "__main__":
    config = load_config("config.yaml")

    if config.mode != "backtest":
        print("Please set mode to 'backtest' in config.yaml")
        sys.exit(1)

    backtester = Backtester(
        primary_interval=config.primary_interval,
        intervals=config.signals.intervals,
        tickers=config.signals.tickers,
        start_date=config.start_date,
        end_date=config.end_date,
        initial_capital=config.initial_cash,
        strategies=config.signals.strategies,
        show_agent_graph=config.show_agent_graph,
        show_reasoning=config.show_reasoning,
        model_name=config.model.name,
        model_provider=config.model.provider,
        model_base_url=config.model.base_url,
    )

    print("Starting backtest...")
    performance_metrics = backtester.run_backtest()
    performance_df = backtester.analyze_performance()

