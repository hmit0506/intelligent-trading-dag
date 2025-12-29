"""
Unified trading system runner for both backtest and live modes.
"""
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from colorama import Fore, Style

from agent import Agent
from backtest.engine import Backtester
from utils.helpers import format_live_results
from utils.file_manager import OutputFileManager


class TradingSystemRunner:
    """
    Unified runner for both backtest and live trading modes.
    Provides consistent interface and enhanced features.
    """
    
    def __init__(self, config):
        """
        Initialize the trading system runner.
        
        Args:
            config: Configuration object from load_config()
        """
        self.config = config
        self.agent = None
        self.portfolio = self._init_portfolio()
        self.decision_history: List[Dict[str, Any]] = []
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        self.file_manager = OutputFileManager(str(self.output_dir))
        
        # Auto-cleanup old files if configured
        if getattr(config, 'auto_cleanup_files', False):
            self._auto_cleanup_files()
        
    def _init_portfolio(self) -> Dict[str, Any]:
        """Initialize portfolio structure."""
        return {
            "cash": self.config.initial_cash,
            "margin_requirement": self.config.margin_requirement,
            "margin_used": 0.0,
            "positions": {
                ticker: {
                    "long": 0.0,
                    "short": 0.0,
                    "long_cost_basis": 0.0,
                    "short_cost_basis": 0.0,
                    "short_margin_used": 0.0,
                }
                for ticker in self.config.signals.tickers
            },
            "realized_gains": {
                ticker: {
                    "long": 0.0,
                    "short": 0.0,
                }
                for ticker in self.config.signals.tickers
            },
        }
    
    def _create_agent(self) -> Agent:
        """Create and return an Agent instance."""
        if self.agent is None:
            self.agent = Agent(
                intervals=self.config.signals.intervals,
                strategies=self.config.signals.strategies,
                show_agent_graph=self.config.show_agent_graph,
            )
        return self.agent
    
    def run(self) -> Dict[str, Any]:
        """
        Run the trading system based on configured mode.
        
        Returns:
            Dictionary containing results and metrics
        """
        if self.config.mode == "backtest":
            return self._run_backtest()
        else:
            return self._run_live()
    
    def _run_backtest(self) -> Dict[str, Any]:
        """Run backtest mode with enhanced features."""
        # Generate log file path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = str(self.output_dir / f"backtest_{timestamp}.log")
        
        backtester = Backtester(
            primary_interval=self.config.primary_interval,
            intervals=self.config.signals.intervals,
            tickers=self.config.signals.tickers,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            initial_capital=self.config.initial_cash,
            strategies=self.config.signals.strategies,
            show_agent_graph=self.config.show_agent_graph,
            show_reasoning=self.config.show_reasoning,
            model_name=self.config.model.name,
            model_provider=self.config.model.provider,
            model_base_url=self.config.model.base_url,
            print_frequency=getattr(self.config, 'print_frequency', 1),  # Default: print every iteration
            use_progress_bar=getattr(self.config, 'use_progress_bar', True),  # Default: use progress bar
            log_file=log_file if getattr(self.config, 'enable_logging', True) else None,
        )
        
        print("Starting backtest...")
        performance_metrics = backtester.run_backtest()
        performance_df = backtester.analyze_performance()
        
        # Export trade log to CSV/JSON
        self._export_backtest_results(backtester)
        
        return {
            "mode": "backtest",
            "performance_metrics": performance_metrics,
            "performance_df": performance_df,
            "trade_log": backtester.trade_log,
        }
    
    def _run_live(self) -> Dict[str, Any]:
        """Run live trading mode with enhanced features."""
        agent = self._create_agent()
        
        # Run agent
        result = agent.run(
            primary_interval=self.config.primary_interval,
            tickers=self.config.signals.tickers,
            end_date=datetime.now(),
            portfolio=self.portfolio,
            show_reasoning=self.config.show_reasoning,
            model_name=self.config.model.name,
            model_provider=self.config.model.provider,
            model_base_url=self.config.model.base_url
        )
        
        decisions = result.get('decisions', {})
        analyst_signals = result.get('analyst_signals', {})
        
        # Record decision history
        decision_record = {
            "timestamp": datetime.now().isoformat(),
            "decisions": decisions,
            "analyst_signals": analyst_signals,
            "portfolio": self.portfolio.copy(),
        }
        self.decision_history.append(decision_record)
        
        # Enhanced display with portfolio information
        self._display_live_results(decisions, analyst_signals)
        
        # Save decision history if configured
        self._save_decision_history()
        
        return {
            "mode": "live",
            "decisions": decisions,
            "analyst_signals": analyst_signals,
            "portfolio": self.portfolio,
            "decision_history": self.decision_history,
        }
    
    def _display_live_results(
        self, 
        decisions: Dict[str, Any], 
        analyst_signals: Dict[str, Any]
    ) -> None:
        """
        Display live results with enhanced portfolio information.
        """
        from colorama import Fore, Style, init
        from tabulate import tabulate
        from data.provider import BinanceDataProvider
        
        init(autoreset=True)
        
        # Fetch current prices for portfolio valuation
        data_provider = BinanceDataProvider()
        current_prices = {}
        portfolio_value = self.portfolio["cash"]
        
        try:
            # Try to get current prices
            for ticker in self.config.signals.tickers:
                try:
                    # Get latest price from recent klines
                    latest_data = data_provider.get_history_klines_with_end_time(
                        symbol=ticker,
                        timeframe=self.config.primary_interval.value,
                        end_time=datetime.now()
                    )
                    if latest_data is not None and not latest_data.empty:
                        current_prices[ticker] = float(latest_data.iloc[-1]["close"])
                    else:
                        current_prices[ticker] = None
                except Exception as e:
                    print(f"Warning: Could not fetch price for {ticker}: {e}")
                    current_prices[ticker] = None
        except Exception as e:
            print(f"Warning: Could not fetch current prices: {e}")
        
        # Calculate portfolio value
        for ticker in self.config.signals.tickers:
            pos = self.portfolio["positions"][ticker]
            if current_prices.get(ticker) is not None:
                price = current_prices[ticker]
                portfolio_value += pos["long"] * price
                portfolio_value -= pos["short"] * price  # Short positions reduce value
        
        # Display portfolio summary
        print("\n" + "=" * 80)
        print(f"{Fore.WHITE}{Style.BRIGHT}PORTFOLIO SUMMARY{Style.RESET_ALL}".center(80))
        print("=" * 80)
        print(f"Cash Balance: {Fore.CYAN}${self.portfolio['cash']:,.2f}{Style.RESET_ALL}")
        print(f"Margin Used: {Fore.YELLOW}${self.portfolio['margin_used']:,.2f}{Style.RESET_ALL}")
        print(f"Total Portfolio Value: {Fore.GREEN}${portfolio_value:,.2f}{Style.RESET_ALL}")
        
        # Calculate return if we have initial capital
        if hasattr(self.config, 'initial_cash') and self.config.initial_cash > 0:
            total_return = ((portfolio_value - self.config.initial_cash) / self.config.initial_cash) * 100
            return_color = Fore.GREEN if total_return >= 0 else Fore.RED
            print(f"Total Return: {return_color}{total_return:+.2f}%{Style.RESET_ALL}")
        
        # Display positions
        position_rows = []
        for ticker in self.config.signals.tickers:
            pos = self.portfolio["positions"][ticker]
            if pos["long"] > 0 or pos["short"] > 0:
                current_price = current_prices.get(ticker, "N/A")
                price_str = f"${current_price:.2f}" if isinstance(current_price, (int, float)) else str(current_price)
                
                long_value = pos["long"] * current_price if isinstance(current_price, (int, float)) else 0
                short_value = pos["short"] * current_price if isinstance(current_price, (int, float)) else 0
                
                position_rows.append([
                    f"{Fore.CYAN}{ticker}{Style.RESET_ALL}",
                    f"{Fore.GREEN}Long: {pos['long']:.4f}{Style.RESET_ALL}" if pos["long"] > 0 else "",
                    f"{Fore.RED}Short: {pos['short']:.4f}{Style.RESET_ALL}" if pos["short"] > 0 else "",
                    price_str,
                    f"${long_value:.2f}" if long_value > 0 else f"-${short_value:.2f}" if short_value > 0 else "$0.00",
                ])
        
        if position_rows:
            print(f"\n{Fore.WHITE}{Style.BRIGHT}CURRENT POSITIONS:{Style.RESET_ALL}\n")
            print(tabulate(
                position_rows,
                headers=[
                    f"{Fore.CYAN}Ticker{Style.RESET_ALL}",
                    f"{Fore.WHITE}Long{Style.RESET_ALL}",
                    f"{Fore.WHITE}Short{Style.RESET_ALL}",
                    f"{Fore.WHITE}Current Price{Style.RESET_ALL}",
                    f"{Fore.WHITE}Position Value{Style.RESET_ALL}"
                ],
                tablefmt="grid",
            ))
        
        print("\n" + "=" * 80 + "\n")
        
        # Display trading decisions (using existing format_live_results)
        format_live_results(decisions, analyst_signals)
    
    def _export_backtest_results(self, backtester: Backtester) -> None:
        """Export backtest results to CSV and JSON formats."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export trade log to JSON
        json_path = self.output_dir / f"backtest_trades_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(backtester.trade_log, f, indent=2, default=str)
        print(f"\n{Fore.GREEN}Trade log exported to: {json_path}{Style.RESET_ALL}")
        
        # Export performance data to CSV
        if hasattr(backtester, 'portfolio_values') and backtester.portfolio_values:
            import pandas as pd
            df = pd.DataFrame(backtester.portfolio_values)
            csv_path = self.output_dir / f"backtest_performance_{timestamp}.csv"
            df.to_csv(csv_path, index=False)
            print(f"{Fore.GREEN}Performance data exported to: {csv_path}{Style.RESET_ALL}")
    
    def _save_decision_history(self) -> None:
        """Save decision history to file."""
        if not self.decision_history:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = self.output_dir / f"live_decisions_{timestamp}.json"
        
        with open(json_path, 'w') as f:
            json.dump(self.decision_history, f, indent=2, default=str)
        
        print(f"\n{Fore.GREEN}Decision history saved to: {json_path}{Style.RESET_ALL}")
    
    def _auto_cleanup_files(self) -> None:
        """Automatically clean up old files based on retention policy."""
        max_age_days = getattr(self.config, 'file_retention_days', 30)
        keep_latest = getattr(self.config, 'file_keep_latest', 10)
        
        results = self.file_manager.cleanup_old_files(
            max_age_days=max_age_days,
            keep_latest=keep_latest,
            dry_run=False
        )
        
        total_deleted = sum(results.values())
        if total_deleted > 0:
            print(f"\n{Fore.YELLOW}Auto-cleanup: Deleted {total_deleted} old files{Style.RESET_ALL}")

