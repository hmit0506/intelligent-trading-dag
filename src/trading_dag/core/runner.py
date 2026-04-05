"""
Unified trading system runner for both backtest and live modes.
"""
import os
import sys
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path
from colorama import Fore, Style, init

from trading_dag.agent import Agent
from trading_dag.backtest.engine import Backtester
from trading_dag.utils.helpers import format_live_results
from trading_dag.utils.file_manager import output_file_manager_for_layout
from trading_dag.utils.constants import Interval
from trading_dag.utils.config import risk_config_to_metadata
from trading_dag.utils.backtest_export import export_backtest_trades_and_performance
from trading_dag.utils.output_layout import resolve_output_dirs
from trading_dag.data.provider import BinanceDataProvider
import pandas as pd

init(autoreset=True)


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
        self.initial_portfolio_value = None  # Will be calculated after portfolio initialization
        self.decision_history: List[Dict[str, Any]] = []
        out = resolve_output_dirs(Path.cwd(), self.config.output_layout)
        self.output_root = out.root
        self.backtest_output_dir = out.backtest
        self.live_output_dir = out.live
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.backtest_output_dir.mkdir(parents=True, exist_ok=True)
        out.benchmark.mkdir(parents=True, exist_ok=True)
        self.live_output_dir.mkdir(parents=True, exist_ok=True)
        self.file_manager = output_file_manager_for_layout(out)
        
        # Calculate initial portfolio value (for return calculation)
        self._calculate_initial_portfolio_value()
        
        # Auto-cleanup old files if configured
        if getattr(config, 'auto_cleanup_files', False):
            self._auto_cleanup_files()
        
    def _init_portfolio(self) -> Dict[str, Any]:
        """
        Initialize portfolio structure.
        In both live and backtest modes, can use configured initial positions.
        In live mode, can also sync from exchange.
        """
        portfolio = {
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
        
        # Apply initial positions if configured (works for both live and backtest)
        initial_positions = getattr(self.config, 'initial_positions', None)
        if initial_positions:
            portfolio = self._apply_initial_positions(portfolio, initial_positions)
            mode_name = "live" if self.config.mode == "live" else "backtest"
            print(f"{Fore.GREEN}Portfolio initialized with configured positions ({mode_name} mode){Style.RESET_ALL}")
        
        # In live mode, can also sync from exchange
        if self.config.mode == "live":
            sync_from_exchange = getattr(self.config, 'sync_from_exchange', False)
            if sync_from_exchange:
                try:
                    portfolio = self._sync_portfolio_from_exchange(portfolio)
                    print(f"{Fore.GREEN}Portfolio synced from Binance exchange{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}Warning: Could not sync portfolio from exchange: {e}{Style.RESET_ALL}")
                    if initial_positions:
                        print(f"{Fore.YELLOW}Falling back to configured initial positions{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}Falling back to initial cash only{Style.RESET_ALL}")
            elif not initial_positions:
                print(f"{Fore.CYAN}Portfolio initialized with initial cash only (no positions){Style.RESET_ALL}")
        elif not initial_positions:
            print(f"{Fore.CYAN}Portfolio initialized with initial cash only (no positions){Style.RESET_ALL}")
        
        return portfolio
    
    def _calculate_initial_portfolio_value(self) -> None:
        """
        Calculate initial portfolio value including positions.
        This is used as the baseline for return calculations.
        """
        # Start with cash
        initial_value = self.portfolio["cash"]
        
        # Check if we have initial positions
        has_initial_positions = getattr(self.config, 'initial_positions', None) is not None
        sync_from_exchange = getattr(self.config, 'sync_from_exchange', False)
        
        if has_initial_positions or sync_from_exchange:
            # If we have initial positions, calculate their value at initialization
            # Use cost basis as initial value (what we paid for it)
            for ticker in self.config.signals.tickers:
                pos = self.portfolio["positions"][ticker]
                if pos["long"] > 0 and pos["long_cost_basis"] > 0:
                    initial_value += pos["long"] * pos["long_cost_basis"]
                if pos["short"] > 0 and pos["short_cost_basis"] > 0:
                    initial_value -= pos["short"] * pos["short_cost_basis"]  # Short reduces value
        else:
            # No initial positions, use initial_cash
            initial_value = self.config.initial_cash
        
        self.initial_portfolio_value = initial_value
    
    def _sync_portfolio_from_exchange(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync portfolio from Binance exchange account.
        Fetches current balances and positions.
        """
        from trading_dag.data.provider import BinanceDataProvider
        from colorama import Fore, Style
        
        # Get API credentials from environment
        import os
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        
        if not api_key or not api_secret:
            raise ValueError("BINANCE_API_KEY and BINANCE_API_SECRET must be set to sync from exchange")
        
        data_provider = BinanceDataProvider(
            api_key=api_key,
            api_secret=api_secret,
            naive_timezone=getattr(self.config, "timezone", "UTC"),
        )
        client = data_provider.client
        
        # Get account information
        account = client.get_account()
        
        if not account or "balances" not in account:
            raise ValueError("Could not retrieve account information from exchange")
        
        # Get current prices for valuation (Binance kline endTime is UTC)
        current_prices = {}
        for ticker in self.config.signals.tickers:
            try:
                latest_data = data_provider.get_history_klines_with_end_time(
                    symbol=ticker,
                    timeframe=self.config.primary_interval.value,
                    end_time=datetime.now(timezone.utc),
                    limit=1
                )
                if latest_data is not None and not latest_data.empty:
                    current_prices[ticker] = float(latest_data.iloc[-1]["close"])
            except Exception as e:
                print(f"{Fore.YELLOW}Warning: Could not fetch price for {ticker}: {e}{Style.RESET_ALL}")
        
        # Process balances
        usdt_balance = 0.0
        for balance in account["balances"]:
            asset = balance["asset"]
            free = float(balance.get("free", 0.0))
            locked = float(balance.get("locked", 0.0))
            total = free + locked
            
            if asset == "USDT":
                usdt_balance = total
            else:
                # Check if this asset is part of any ticker
                for ticker in self.config.signals.tickers:
                    # Extract base asset from ticker (e.g., BTCUSDT -> BTC)
                    base_asset = ticker.replace("USDT", "")
                    if asset == base_asset and total > 0:
                        # This is a long position
                        price = current_prices.get(ticker, 0.0)
                        if price > 0:
                            portfolio["positions"][ticker]["long"] = total
                            portfolio["positions"][ticker]["long_cost_basis"] = price  # Use current price as cost basis
                            print(f"  Found position: {ticker} long {total:.4f} @ ${price:.2f}")
        
        portfolio["cash"] = usdt_balance
        print(f"  USDT balance: ${usdt_balance:,.2f}")
        
        return portfolio
    
    def _apply_initial_positions(self, portfolio: Dict[str, Any], initial_positions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply manually configured initial positions to portfolio.
        Cost basis is automatically set using historical/real-time prices.
        
        Args:
            portfolio: Current portfolio structure
            initial_positions: Dict with format:
                {
                    "cash": float,  # Optional; must align with config after load (see initial_positions.cash)
                    "positions": {
                        "BTCUSDT": {
                            "long": float,  # Optional
                            "short": float,  # Optional
                            # Note: cost_basis is automatically set, not configurable
                        },
                        ...
                    }
                }
        """
        from colorama import Fore, Style
        from trading_dag.data.provider import BinanceDataProvider
        
        # Update cash if specified
        if "cash" in initial_positions:
            portfolio["cash"] = float(initial_positions["cash"])
            print(f"  Initial cash: ${portfolio['cash']:,.2f}")
        
        # Get current prices for positions without cost basis
        data_provider = BinanceDataProvider(naive_timezone=getattr(self.config, "timezone", "UTC"))
        current_prices = {}
        for ticker in self.config.signals.tickers:
            try:
                latest_data = data_provider.get_history_klines_with_end_time(
                    symbol=ticker,
                    timeframe=self.config.primary_interval.value,
                    end_time=datetime.now(timezone.utc),
                    limit=1
                )
                if latest_data is not None and not latest_data.empty:
                    current_prices[ticker] = float(latest_data.iloc[-1]["close"])
            except Exception:
                pass
        
        # Apply positions
        if "positions" in initial_positions:
            for ticker, position_data in initial_positions["positions"].items():
                if ticker not in portfolio["positions"]:
                    print(f"{Fore.YELLOW}Warning: Ticker {ticker} not in configured tickers, skipping{Style.RESET_ALL}")
                    continue
                
                pos = portfolio["positions"][ticker]
                
                # Set long position
                if "long" in position_data:
                    pos["long"] = float(position_data["long"])
                    # Always use current market price as cost basis (no manual cost basis allowed)
                    # This ensures accurate evaluation of trading framework performance
                    if ticker not in current_prices or current_prices[ticker] == 0:
                        print(f"{Fore.YELLOW}Warning: Could not get current price for {ticker}, skipping position{Style.RESET_ALL}")
                        pos["long"] = 0.0
                        continue
                    pos["long_cost_basis"] = current_prices[ticker]
                    if pos["long"] > 0:
                        # Initial positions are existing holdings, do NOT deduct from cash
                        # Cash remains unchanged, positions are added as existing assets
                        print(f"  Initial position: {ticker} long {pos['long']:.4f} @ ${pos['long_cost_basis']:.2f} (current market price)")
                
                # Set short position
                if "short" in position_data:
                    pos["short"] = float(position_data["short"])
                    # Always use current market price as cost basis (no manual cost basis allowed)
                    if ticker not in current_prices or current_prices[ticker] == 0:
                        print(f"{Fore.YELLOW}Warning: Could not get current price for {ticker}, skipping position{Style.RESET_ALL}")
                        pos["short"] = 0.0
                        continue
                    pos["short_cost_basis"] = current_prices[ticker]
                    if pos["short"] > 0:
                        margin_required = pos["short"] * pos["short_cost_basis"] * portfolio["margin_requirement"]
                        pos["short_margin_used"] = margin_required
                        portfolio["margin_used"] += margin_required
                        # For short positions, margin is reserved but cash is not deducted
                        print(f"  Initial position: {ticker} short {pos['short']:.4f} @ ${pos['short_cost_basis']:.2f} (current market price, margin: ${margin_required:,.2f})")
        
        return portfolio
    
    def _create_agent(self) -> Agent:
        """Create and return an Agent instance."""
        if self.agent is None:
            self.agent = Agent(
                intervals=self.config.signals.intervals,
                strategies=self.config.signals.strategies,
                show_agent_graph=self.config.show_agent_graph,
                workflow_metadata=risk_config_to_metadata(self.config.risk),
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
        log_file = str(self.backtest_output_dir / f"backtest_{timestamp}.log")

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
            initial_margin_requirement=self.config.margin_requirement,
            print_frequency=getattr(self.config, 'print_frequency', 1),  # Default: print every iteration
            use_progress_bar=getattr(self.config, 'use_progress_bar', True),  # Default: use progress bar
            log_file=log_file if getattr(self.config, 'enable_logging', True) else None,
            initial_positions=getattr(self.config, 'initial_positions', None),  # Support initial positions in backtest
            risk_management=self.config.risk,
            export_output_dir=self.backtest_output_dir,
            naive_date_timezone=getattr(self.config, "timezone", "UTC"),
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
        """
        Run live trading mode with enhanced features.
        Uses the same decision mechanism as backtest mode (no future price predictions).
        """
        agent = self._create_agent()
        
        # Run agent without future timepoints to match backtest mode behavior
        # This ensures consistent decision-making between live and backtest modes
        result = agent.run(
            primary_interval=self.config.primary_interval,
            tickers=self.config.signals.tickers,
            end_date=datetime.now(),
            portfolio=self.portfolio,
            show_reasoning=self.config.show_reasoning,
            model_name=self.config.model.name,
            model_provider=self.config.model.provider,
            model_base_url=self.config.model.base_url,
            # No future_timepoints - decisions based only on current signals
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
        Display live results: current state -> trading decisions -> projected state after execution.
        """
        from colorama import Fore, Style, init
        from tabulate import tabulate
        from trading_dag.data.provider import BinanceDataProvider
        
        init(autoreset=True)
        
        # Fetch current prices for portfolio valuation
        data_provider = BinanceDataProvider(naive_timezone=getattr(self.config, "timezone", "UTC"))
        current_prices = {}
        
        try:
            # Try to get current prices
            for ticker in self.config.signals.tickers:
                try:
                    # Get latest price from recent klines
                    latest_data = data_provider.get_history_klines_with_end_time(
                        symbol=ticker,
                        timeframe=self.config.primary_interval.value,
                        end_time=datetime.now(timezone.utc),
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
        
        # ========== STEP 1: Display Current Portfolio State ==========
        print("\n" + "=" * 80)
        print(f"{Fore.WHITE}{Style.BRIGHT}CURRENT PORTFOLIO STATE{Style.RESET_ALL}".center(80))
        print("=" * 80)
        
        # Calculate current portfolio value
        current_portfolio_value = self.portfolio["cash"]
        for ticker in self.config.signals.tickers:
            pos = self.portfolio["positions"][ticker]
            if current_prices.get(ticker) is not None:
                price = current_prices[ticker]
                current_portfolio_value += pos["long"] * price
                current_portfolio_value -= pos["short"] * price
        
        print(f"Cash Balance: {Fore.CYAN}${self.portfolio['cash']:,.2f}{Style.RESET_ALL}")
        
        # Display positions if any
        has_positions = any(
            self.portfolio["positions"][ticker]["long"] > 0 or 
            self.portfolio["positions"][ticker]["short"] > 0
            for ticker in self.config.signals.tickers
        )
        
        if has_positions:
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
                print(f"\n{Fore.WHITE}{Style.BRIGHT}Current Positions:{Style.RESET_ALL}\n")
                print(tabulate(
                    position_rows,
                    headers=[
                        f"{Fore.CYAN}Ticker{Style.RESET_ALL}",
                        f"{Fore.WHITE}Long{Style.RESET_ALL}",
                        f"{Fore.WHITE}Short{Style.RESET_ALL}",
                        f"{Fore.WHITE}Price{Style.RESET_ALL}",
                        f"{Fore.WHITE}Value{Style.RESET_ALL}"
                    ],
                    tablefmt="grid",
                ))
        else:
            print(f"{Fore.YELLOW}No current positions{Style.RESET_ALL}")
        
        print(f"\nCurrent Portfolio Value: {Fore.GREEN}${current_portfolio_value:,.2f}{Style.RESET_ALL}")
        print("\n" + "=" * 80 + "\n")
        
        # ========== STEP 2: Display Trading Decisions ==========
        format_live_results(decisions, analyst_signals)
    
    def _export_backtest_results(self, backtester: Backtester) -> None:
        """Export backtest results to CSV and JSON formats (same as benchmark DAG exports)."""
        json_path, csv_path = export_backtest_trades_and_performance(
            backtester,
            self.backtest_output_dir,
            experiment_label="",
        )
        print(f"\n{Fore.GREEN}Trade log exported to: {json_path}{Style.RESET_ALL}")
        if csv_path is not None:
            print(f"{Fore.GREEN}Performance data exported to: {csv_path}{Style.RESET_ALL}")
    
    def _save_decision_history(self) -> None:
        """Save decision history to file."""
        if not self.decision_history:
            return
        if not getattr(self.config, "save_decision_history", True):
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = self.live_output_dir / f"live_decisions_{timestamp}.json"
        
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
