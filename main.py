"""
Main entry point for live trading mode and backtest mode.
"""
import os
import sys
from dotenv import load_dotenv
from datetime import datetime
from utils.config import load_config
from utils.helpers import format_live_results
from agent import Agent
from backtest.engine import Backtester

# Add parent directory to path to access gateway
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

load_dotenv()

if __name__ == "__main__":
    config = load_config("config.yaml")

    if config.mode == "backtest":
        # Run backtest mode
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
        sys.exit(0)

    # Initialize portfolio
    portfolio = {
        "cash": config.initial_cash,
        "margin_requirement": config.margin_requirement,
        "margin_used": 0.0,
        "positions": {
            ticker: {
                "long": 0.0,
                "short": 0.0,
                "long_cost_basis": 0.0,
                "short_cost_basis": 0.0,
                "short_margin_used": 0.0,
            }
            for ticker in config.signals.tickers
        },
        "realized_gains": {
            ticker: {
                "long": 0.0,
                "short": 0.0,
            }
            for ticker in config.signals.tickers
        },
    }

    # Create agent
    agent = Agent(
        intervals=config.signals.intervals,
        strategies=config.signals.strategies,
        show_agent_graph=config.show_agent_graph,
    )

    # Run agent
    result = agent.run(
        primary_interval=config.primary_interval,
        tickers=config.signals.tickers,
        end_date=datetime.now(),
        portfolio=portfolio,
        show_reasoning=config.show_reasoning,
        model_name=config.model.name,
        model_provider=config.model.provider,
        model_base_url=config.model.base_url
    )

    # Format and display results
    decisions = result.get('decisions', {})
    analyst_signals = result.get('analyst_signals', {})
    format_live_results(decisions, analyst_signals)

