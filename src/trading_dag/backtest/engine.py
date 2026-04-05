import itertools
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Any
from colorama import Fore, Style
import matplotlib.pyplot as plt

from trading_dag.utils.constants import Interval, QUANTITY_DECIMALS, RISK_FREE_RATE_ANNUAL
from trading_dag.utils.helpers import format_backtest_row, print_backtest_results
from trading_dag.agent import Agent
from trading_dag.benchmark.ablation import DAGAblationSettings
from trading_dag.data.provider import BinanceDataProvider
from trading_dag.utils.config import RiskManagementConfig, risk_config_to_metadata
from trading_dag.utils.output_layout import OutputLayoutConfig, resolve_output_dirs
from trading_dag.utils.backtest_export import slugify_experiment_label
from trading_dag.utils.exchange_time import (
    format_utc_naive_for_display,
    naive_in_zone_to_utc_naive,
    now_config_wall_strftime,
    utc_naive_instant_to_wall_naive,
)


class Backtester:
    def __init__(
            self,
            primary_interval: Interval,
            intervals: List[Interval],
            tickers: List[str],
            start_date: datetime,
            end_date: datetime,
            initial_capital: float,
            strategies: List[str],
            model_name: str = "gpt-4o",
            model_provider: str = "openai",
            model_base_url: Optional[str] = None,
            initial_margin_requirement: float = 0.0,
            show_agent_graph: bool = False,
            show_reasoning: bool = False,
            print_frequency: int = 1,
            use_progress_bar: bool = True,
            log_file: Optional[str] = None,
            initial_positions: Optional[Dict[str, Any]] = None,
            ablation: Optional[DAGAblationSettings] = None,
            risk_management: Optional[RiskManagementConfig] = None,
            export_output_dir: Optional[Path] = None,
            experiment_label: Optional[str] = None,
            naive_date_timezone: str = "UTC",
    ):
        """
        Backtester

        :param experiment_label: If set (e.g. benchmark variant name), portfolio PNG uses
            ``backtest_portfolio_value_{slug}_{timestamp}.png`` — same slug as
            ``export_backtest_trades_and_performance(..., experiment_label=...)``. Leave unset for
            standalone ``backtest_portfolio_value_{timestamp}.png``.
        :param naive_date_timezone: Timezone for naive ``start_date`` / ``end_date`` and for all
            user-facing timestamps (tables, CSV, JSON, charts). Must match ``Config.timezone``.
        :param primary_interval:
        :param intervals:
        :param tickers:
        :param start_date:
        :param end_date:
        :param initial_capital:
        :param strategies:
        :param model_name:
        :param model_provider:
        :param model_base_url: model base url
        :param initial_margin_requirement:
        :param show_agent_graph:
        :param show_reasoning:
        """
        self.primary_interval = primary_interval
        self.tickers = tickers
        self.ablation = ablation or DAGAblationSettings()
        self.risk_management = risk_management or RiskManagementConfig()
        if not self.ablation.multi_interval:
            self.intervals = [primary_interval]
        else:
            self.intervals = list(intervals)
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.strategies = strategies
        self.model_name = model_name
        self.model_provider = model_provider
        self.model_base_url = model_base_url
        self.show_agent_graph = show_agent_graph
        self.show_reasoning = show_reasoning
        self.print_frequency = print_frequency  # Print every N iterations
        self.use_progress_bar = use_progress_bar
        self.log_file = log_file
        self.initial_positions = initial_positions  # Store for later application
        self.initial_portfolio_value = None  # Will be calculated after initial positions are applied
        if export_output_dir is not None:
            self.output_dir = Path(export_output_dir)
        else:
            self.output_dir = resolve_output_dirs(Path.cwd(), OutputLayoutConfig()).backtest
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._experiment_label = (experiment_label or "").strip() or None
        self.naive_date_timezone = naive_date_timezone
        self.binance_data_provider = BinanceDataProvider(naive_timezone=naive_date_timezone)
        self.klines: Dict[str, pd.DataFrame] = {}
        self.trade_log: List[Dict[str, Any]] = []  # To store detailed trade and portfolio information
        
        # Setup logging if log_file is specified
        if self.log_file:
            import logging
            logging.basicConfig(
                filename=self.log_file,
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = None

        # Initialize portfolio with support for long/short positions
        self.portfolio_values = []
        self.portfolio = {
            "cash": initial_capital,
            "margin_requirement": initial_margin_requirement,  # The margin ratio required for shorts
            "margin_used": 0.0,  # total margin usage across all short positions
            "positions": {
                ticker: {
                    "long": 0.0,
                    "short": 0.0,
                    "long_cost_basis": 0.0,
                    "short_cost_basis": 0.0,
                    "short_margin_used": 0.0
                }
                for ticker in tickers
            },
            "realized_gains": {
                ticker: {
                    "long": 0.0,  # Realized gains from long positions
                    "short": 0.0,  # Realized gains from short positions
                }
                for ticker in tickers
            },
        }

    def execute_trade(self, ticker: str, action: str, quantity: float, current_price: float):
        """
        Execute trades with support for both long and short positions.
        `quantity` is the number of shares the agent wants to buy/sell/short/cover.
        We will only trade integer shares to keep it simple.
        """
        if quantity <= 0.0:
            return 0.0

        quantity = round(float(quantity), QUANTITY_DECIMALS)  # force to keep just 0.001
        position = self.portfolio["positions"][ticker]

        if action == "buy":
            cost = quantity * current_price
            if cost <= self.portfolio["cash"]:
                # Weighted average cost basis for the new total
                old_shares = position["long"]
                old_cost_basis = position["long_cost_basis"]
                new_shares = quantity
                total_shares = old_shares + new_shares

                if total_shares > 0.0:
                    total_old_cost = old_cost_basis * old_shares
                    total_new_cost = cost
                    position["long_cost_basis"] = (total_old_cost + total_new_cost) / total_shares

                position["long"] += quantity
                self.portfolio["cash"] -= cost
                return quantity
            else:
                # Calculate maximum affordable quantity
                max_quantity = round(float(self.portfolio["cash"] / current_price), QUANTITY_DECIMALS)
                if max_quantity > 0.0:
                    cost = max_quantity * current_price
                    old_shares = position["long"]
                    old_cost_basis = position["long_cost_basis"]
                    total_shares = old_shares + max_quantity

                    if total_shares > 0.0:
                        total_old_cost = old_cost_basis * old_shares
                        total_new_cost = cost
                        position["long_cost_basis"] = (total_old_cost + total_new_cost) / total_shares

                    position["long"] += max_quantity
                    self.portfolio["cash"] -= cost
                    return max_quantity
                return 0.0

        elif action == "sell":
            # You can only sell as many as you own
            quantity = min(quantity, position["long"])
            if quantity > 0.0:
                # Realized gain/loss using average cost basis
                avg_cost_per_share = position["long_cost_basis"] if position["long"] > 0.0 else 0.0
                realized_gain = (current_price - avg_cost_per_share) * quantity
                self.portfolio["realized_gains"][ticker]["long"] += realized_gain

                position["long"] -= quantity
                self.portfolio["cash"] += quantity * current_price

                if position["long"] == 0.0:
                    position["long_cost_basis"] = 0.0

                return quantity

        elif action == "short":
            """
            Typical short sale flow:
              1) Receive proceeds = current_price * quantity
              2) Post margin_required = proceeds * margin_ratio
              3) Net effect on cash = +proceeds - margin_required
            """
            proceeds = current_price * quantity
            margin_required = proceeds * self.portfolio["margin_requirement"]
            if margin_required <= self.portfolio["cash"]:
                # Weighted average short cost basis
                old_short_shares = position["short"]
                old_cost_basis = position["short_cost_basis"]
                new_shares = quantity
                total_shares = old_short_shares + new_shares

                if total_shares > 0.0:
                    total_old_cost = old_cost_basis * old_short_shares
                    total_new_cost = current_price * new_shares
                    position["short_cost_basis"] = (total_old_cost + total_new_cost) / total_shares

                position["short"] += quantity

                # Update margin usage
                position["short_margin_used"] += margin_required
                self.portfolio["margin_used"] += margin_required

                # Increase cash by proceeds, then subtract the required margin
                self.portfolio["cash"] += proceeds
                self.portfolio["cash"] -= margin_required
                return quantity
            else:
                # Calculate maximum shortable quantity
                margin_ratio = self.portfolio["margin_requirement"]
                if margin_ratio > 0.0:
                    max_quantity = int(self.portfolio["cash"] / (current_price * margin_ratio))
                else:
                    max_quantity = 0.0

                if max_quantity > 0.0:
                    proceeds = current_price * max_quantity
                    margin_required = proceeds * margin_ratio

                    old_short_shares = position["short"]
                    old_cost_basis = position["short_cost_basis"]
                    total_shares = old_short_shares + max_quantity

                    if total_shares > 0.0:
                        total_old_cost = old_cost_basis * old_short_shares
                        total_new_cost = current_price * max_quantity
                        position["short_cost_basis"] = (total_old_cost + total_new_cost) / total_shares

                    position["short"] += max_quantity
                    position["short_margin_used"] += margin_required
                    self.portfolio["margin_used"] += margin_required

                    self.portfolio["cash"] += proceeds
                    self.portfolio["cash"] -= margin_required
                    return max_quantity
                return 0.0

        elif action == "cover":
            """
            When covering shares:
              1) Pay cover cost = current_price * quantity
              2) Release a proportional share of the margin
              3) Net effect on cash = -cover_cost + released_margin
            """
            quantity = min(quantity, position["short"])
            if quantity > 0.0:
                cover_cost = quantity * current_price
                avg_short_price = position["short_cost_basis"] if position["short"] > 0.0 else 0.0
                realized_gain = (avg_short_price - current_price) * quantity

                if position["short"] > 0.0:
                    portion = quantity / position["short"]
                else:
                    portion = 1.0

                margin_to_release = portion * position["short_margin_used"]

                position["short"] -= quantity
                position["short_margin_used"] -= margin_to_release
                self.portfolio["margin_used"] -= margin_to_release

                # Pay the cost to cover, but get back the released margin
                self.portfolio["cash"] += margin_to_release
                self.portfolio["cash"] -= cover_cost

                self.portfolio["realized_gains"][ticker]["short"] += realized_gain

                if position["short"] == 0.0:
                    position["short_cost_basis"] = 0.0
                    position["short_margin_used"] = 0.0

                return quantity

        return 0.0

    def calculate_portfolio_value(self, current_prices):
        """
        Calculate total portfolio value, including:
          - cash
          - market value of long positions
          - unrealized gains/losses for short positions
        """
        total_value = self.portfolio["cash"]

        for ticker in self.tickers:
            position = self.portfolio["positions"][ticker]
            price = current_prices[ticker]

            # Long position value
            long_value = position["long"] * price
            total_value += long_value

            # Short position unrealized PnL = short_shares * (short_cost_basis - current_price)
            if position["short"] > 0.0:
                total_value -= position["short"] * price

        return total_value

    def prefetch_data(self):
        """
        Pre-fetch all data needed for the backtest period.
        Fetches at least 500 K-lines, or the entire date range if it requires more than 500 K-lines.
        This ensures sufficient data for backtest while maintaining consistency with live mode.
        """
        print("\nPre-fetching data for backtest...")
        
        if not hasattr(self, 'prefetched_data'):
            self.prefetched_data = {}
        
        from datetime import timedelta
        import pandas as pd
        
        # Calculate the date range for backtest
        date_range = self.end_date - self.start_date
        # Keep fetch end_time aligned with backtest filter boundary (<= self.end_date)
        # to avoid interval shifts caused by inconsistent end_time definitions.
        fetch_end_time = self.end_date
        
        print(
            f"Backtest date range: {self.start_date} to {self.end_date} ({date_range}) "
            f"[timezone {self.naive_date_timezone}; bar timestamps below are wall clock in this zone]"
        )

        start_utc_naive = naive_in_zone_to_utc_naive(self.start_date, self.naive_date_timezone)
        end_utc_naive = naive_in_zone_to_utc_naive(self.end_date, self.naive_date_timezone)

        for interval in self.intervals:
            for ticker in self.tickers:
                # Calculate how many K-lines are needed for the backtest date range
                interval_delta = interval.to_timedelta()
                required_k_lines = int(date_range / interval_delta) + 1  # +1 to include both start and end
                
                # Use at least 500 K-lines, or the entire range if it needs more
                k_lines_to_fetch = max(500, required_k_lines)
                
                print(f"  {ticker} {interval.value}: Backtest range needs ~{required_k_lines} K-lines, fetching {k_lines_to_fetch} K-lines")
                
                # Fetch data ending at the same boundary used by iteration filtering.
                data = self.binance_data_provider.get_history_klines_with_end_time(
                    symbol=ticker,
                    timeframe=interval.value,
                    end_time=fetch_end_time,
                    limit=k_lines_to_fetch
                )
                
                if not data.empty:
                    # Store all fetched data in prefetched_data for strategy calculations
                    cache_key = f"{ticker}_{interval.value}"
                    self.prefetched_data[cache_key] = data
                    
                    # Filter to backtest window (config dates in timezone vs exchange kline UTC instants)
                    backtest_data = data[
                        (data["open_time"] >= start_utc_naive)
                        & (data["open_time"] <= end_utc_naive)
                    ].reset_index(drop=True)
                    
                    if interval == self.primary_interval:
                        self.klines[ticker] = backtest_data
                    
                    # Count data points
                    total_count = len(data)
                    backtest_count = len(backtest_data)
                    warmup_count = total_count - backtest_count
                    
                    if backtest_count > 0:
                        o0 = format_utc_naive_for_display(
                            backtest_data.iloc[0]["open_time"], self.naive_date_timezone
                        )
                        o1 = format_utc_naive_for_display(
                            backtest_data.iloc[-1]["open_time"], self.naive_date_timezone
                        )
                        print(
                            f"    Retrieved {total_count} total K-lines, {backtest_count} in backtest range "
                            f"({o0} to {o1}, {self.naive_date_timezone}), {warmup_count} warmup bars before window"
                        )
                    elif total_count > 0:
                        print(f"    Retrieved {total_count} total K-lines, but none in backtest range (all before start_date)")
                    else:
                        print(f"    No data retrieved")
                else:
                    cache_key = f"{ticker}_{interval.value}"
                    self.prefetched_data[cache_key] = data
                    print(f"    No data retrieved")

        print("Data pre-fetch complete.")
    
    def _calculate_initial_portfolio_value(self) -> None:
        """
        Calculate initial portfolio value including positions.
        This is used as the baseline for return calculations in backtest mode.
        """
        # Start with cash
        initial_value = self.portfolio["cash"]
        
        # Add value of initial positions at cost basis
        for ticker in self.tickers:
            pos = self.portfolio["positions"][ticker]
            if pos["long"] > 0 and pos["long_cost_basis"] > 0:
                initial_value += pos["long"] * pos["long_cost_basis"]
            if pos["short"] > 0 and pos["short_cost_basis"] > 0:
                initial_value -= pos["short"] * pos["short_cost_basis"]  # Short reduces value
        
        self.initial_portfolio_value = initial_value

    def run_backtest(self):
        # Pre-fetch all data at the start
        self.prefetch_data()
        
        # Apply initial positions if provided (for backtest mode)
        # This allows backtesting with existing positions
        if hasattr(self, 'initial_positions') and self.initial_positions:
            from datetime import datetime
            from colorama import Fore, Style
            
            # Get prices at start_date for cost basis calculation
            start_prices = {}
            for ticker in self.tickers:
                try:
                    # Get price at start_date
                    start_data = self.binance_data_provider.get_history_klines_with_end_time(
                        symbol=ticker,
                        timeframe=self.primary_interval.value,
                        end_time=self.start_date,
                        limit=1
                    )
                    if start_data is not None and not start_data.empty:
                        start_prices[ticker] = float(start_data.iloc[-1]["close"])
                except Exception:
                    pass
            
            # Apply initial positions
            print(f"{Fore.GREEN}Applying initial positions to backtest portfolio{Style.RESET_ALL}")
            if "cash" in self.initial_positions:
                self.portfolio["cash"] = float(self.initial_positions["cash"])
                print(f"  Initial cash: ${self.portfolio['cash']:,.2f}")
            
            if "positions" in self.initial_positions:
                for ticker, position_data in self.initial_positions["positions"].items():
                    if ticker not in self.portfolio["positions"]:
                        print(f"{Fore.YELLOW}Warning: Ticker {ticker} not in configured tickers, skipping{Style.RESET_ALL}")
                        continue
                    
                    pos = self.portfolio["positions"][ticker]
                    
                    if "long" in position_data:
                        pos["long"] = float(position_data["long"])
                        # Always use start_date price as cost basis (no manual cost basis allowed)
                        # This ensures accurate evaluation of trading framework performance
                        if ticker not in start_prices or start_prices[ticker] == 0:
                            print(f"{Fore.YELLOW}Warning: Could not get price for {ticker} at start_date, skipping position{Style.RESET_ALL}")
                            pos["long"] = 0.0
                            continue
                        pos["long_cost_basis"] = start_prices[ticker]
                        if pos["long"] > 0:
                            # Initial positions are existing holdings, do NOT deduct from cash
                            # Cash remains unchanged, positions are added as existing assets
                            print(f"  Initial position: {ticker} long {pos['long']:.4f} @ ${pos['long_cost_basis']:.2f} (price at start_date)")
                    
                    if "short" in position_data:
                        pos["short"] = float(position_data["short"])
                        # Always use start_date price as cost basis (no manual cost basis allowed)
                        if ticker not in start_prices or start_prices[ticker] == 0:
                            print(f"{Fore.YELLOW}Warning: Could not get price for {ticker} at start_date, skipping position{Style.RESET_ALL}")
                            pos["short"] = 0.0
                            continue
                        pos["short_cost_basis"] = start_prices[ticker]
                        if pos["short"] > 0:
                            margin_required = pos["short"] * pos["short_cost_basis"] * self.portfolio["margin_requirement"]
                            pos["short_margin_used"] = margin_required
                            self.portfolio["margin_used"] += margin_required
                            # For short positions, margin is reserved but cash is not deducted
                            print(f"  Initial position: {ticker} short {pos['short']:.4f} @ ${pos['short_cost_basis']:.2f} (price at start_date, margin: ${margin_required:,.2f})")
            
            # Calculate initial portfolio value (for return calculation)
            self._calculate_initial_portfolio_value()
        else:
            # If no initial positions, calculate initial portfolio value (cash only)
            self._calculate_initial_portfolio_value()

        # Check all are DataFrames and collect lengths
        lengths = []
        for ticker in self.tickers:
            df = self.klines.get(ticker)
            if not isinstance(df, pd.DataFrame):
                raise TypeError(f"Data for {ticker} is not a DataFrame: {type(df)}")
            lengths.append(len(df))

        # Check if all lengths are equal
        if len(set(lengths)) != 1:
            raise ValueError(f"DataFrames have mismatched lengths: {dict(zip(self.tickers, lengths))}")

        ticker = self.tickers[0]
        data_df: pd.DataFrame = self.klines[ticker]
        # dates = pd.date_range(self.start_date, self.end_date, freq="B")
        table_rows = []
        performance_metrics = {"sharpe_ratio": None, "sortino_ratio": None, "max_drawdown": None,
                               "long_short_ratio": None, "gross_exposure": None, "net_exposure": None}

        print("\nStarting backtest...")

        # Initialize portfolio values list with initial portfolio value
        initial_value = self.initial_portfolio_value if self.initial_portfolio_value else self.initial_capital
        if len(data_df) > 0:
            _d0 = utc_naive_instant_to_wall_naive(data_df.loc[0, "open_time"], self.naive_date_timezone)
            self.portfolio_values = [{"Date": _d0, "Portfolio Value": initial_value}]
        else:
            self.portfolio_values = []

        if len(data_df) > 0:
            _fo = format_utc_naive_for_display(data_df.iloc[0]["open_time"], self.naive_date_timezone)
            _lo = format_utc_naive_for_display(data_df.iloc[-1]["open_time"], self.naive_date_timezone)
            print(
                f"Backtest will process {len(data_df)} primary-interval bars "
                f"(first open {self.primary_interval.value}: {_fo}, last open: {_lo}; "
                f"timezone {self.naive_date_timezone})"
            )
        else:
            print(f"Backtest will process 0 data points (config window {self.start_date} to {self.end_date})")
        
        # Display initial portfolio information
        from colorama import Fore, Style
        print(f"\n{Fore.WHITE}{Style.BRIGHT}INITIAL PORTFOLIO:{Style.RESET_ALL}")
        print(f"Initial Portfolio Value: {Fore.WHITE}${initial_value:,.2f}{Style.RESET_ALL}")
        print(f"Cash: {Fore.CYAN}${self.portfolio['cash']:,.2f}{Style.RESET_ALL}")
        
        # Display initial positions if any
        has_initial_positions = False
        for ticker in self.tickers:
            pos = self.portfolio["positions"][ticker]
            if pos["long"] > 0 or pos["short"] > 0:
                has_initial_positions = True
                break
        
        if has_initial_positions:
            print(f"{Fore.WHITE}Initial Positions:{Style.RESET_ALL}")
            for ticker in self.tickers:
                pos = self.portfolio["positions"][ticker]
                if pos["long"] > 0:
                    print(f"  {Fore.GREEN}{ticker}: Long {pos['long']:.4f} @ ${pos['long_cost_basis']:.2f}{Style.RESET_ALL}")
                if pos["short"] > 0:
                    print(f"  {Fore.RED}{ticker}: Short {pos['short']:.4f} @ ${pos['short_cost_basis']:.2f}{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}No initial positions (cash only){Style.RESET_ALL}")
        
        print()  # Empty line before backtest starts

        # print(self.portfolio_values)
        workflow_metadata = dict(self.ablation.workflow_metadata())
        workflow_metadata.update(risk_config_to_metadata(self.risk_management))
        agent = Agent(
            intervals=self.intervals,
            strategies=self.strategies,
            show_agent_graph=self.show_agent_graph,
            workflow_metadata=workflow_metadata,
        )
        
        # Setup progress bar if enabled
        if self.use_progress_bar:
            try:
                from tqdm import tqdm
                progress_bar = tqdm(
                    total=len(data_df),
                    desc="Backtesting",
                    unit="iter",
                    ncols=100
                )
            except ImportError:
                print("Warning: tqdm not installed. Progress bar disabled.")
                progress_bar = None
        else:
            progress_bar = None
        
        iteration_count = 0
        for row in data_df.itertuples(index=True):
            iteration_count += 1

            index = row.Index
            current_time = row.close_time
            wall_time = utc_naive_instant_to_wall_naive(current_time, self.naive_date_timezone)
            date_display = pd.Timestamp(wall_time).strftime("%Y-%m-%d %H:%M:%S")
            current_prices = {}
            for ticker in self.tickers:
                price_data = self.klines[ticker]
                current_prices[ticker] = price_data.iloc[index]["close"]

            # ---------------------------------------------------------------
            # 1) Execute the agent's trades
            # ---------------------------------------------------------------
            # Pass prefetched data to agent state for DataNode to use
            prefetched_data = getattr(self, 'prefetched_data', {})
            
            output = agent.run(
                primary_interval=self.primary_interval,
                tickers=self.tickers,
                end_date=current_time,
                portfolio=self.portfolio,
                model_name=self.model_name,
                model_provider=self.model_provider,
                model_base_url=self.model_base_url,
                show_reasoning=self.show_reasoning,
                prefetched_data=prefetched_data,
            )

            decisions = output.get("decisions")
            analyst_signals = output["analyst_signals"]

            # Execute trades for each ticker
            # Decisions structure: {ticker: {timepoint: {action, quantity, ...}}}
            executed_trades = {}
            for ticker in self.tickers:
                ticker_decisions = decisions.get(ticker, {})
                # Use "now" timepoint decision, fallback to first available timepoint
                decision = ticker_decisions.get("now", {})
                if not decision and ticker_decisions:
                    # Fallback to first available timepoint
                    decision = next(iter(ticker_decisions.values()), {})
                
                action = decision.get("action", "hold")
                quantity = decision.get("quantity", 0.0)

                executed_quantity = self.execute_trade(ticker, action, quantity, current_prices[ticker])
                executed_trades[ticker] = executed_quantity

            # ---------------------------------------------------------------
            # 2) Now that trades have executed trades, recalculate the final
            #    portfolio value for this day.
            # ---------------------------------------------------------------
            total_value = self.calculate_portfolio_value(current_prices)

            # Also compute long/short exposures for final post‐trade state
            long_exposure = sum(self.portfolio["positions"][t]["long"] * current_prices[t] for t in self.tickers)
            short_exposure = sum(self.portfolio["positions"][t]["short"] * current_prices[t] for t in self.tickers)

            # Calculate gross and net exposures
            gross_exposure = long_exposure + short_exposure
            net_exposure = long_exposure - short_exposure
            long_short_ratio = long_exposure / short_exposure if short_exposure > 1e-9 else float("inf")

            # Track each day's portfolio value in self.portfolio_values
            self.portfolio_values.append(
                {"Date": wall_time, "Portfolio Value": total_value, "Long Exposure": long_exposure,
                 "Short Exposure": short_exposure, "Gross Exposure": gross_exposure, "Net Exposure": net_exposure,
                 "Long/Short Ratio": long_short_ratio})

            # Record detailed trade and portfolio information
            trade_record = {
                "date": wall_time,
                "total_portfolio_value": total_value,
                "cash_balance": self.portfolio["cash"],
                "total_long_exposure": long_exposure,
                "total_short_exposure": short_exposure,
                "total_gross_exposure": gross_exposure,
                "total_net_exposure": net_exposure,
                "long_short_ratio": long_short_ratio,
                "trades": []  # List to store individual trades for this timestamp
            }

            for ticker in self.tickers:
                ticker_decisions = decisions.get(ticker, {})
                # Use "now" timepoint decision, fallback to first available
                decision = ticker_decisions.get("now", {})
                if not decision and ticker_decisions:
                    decision = next(iter(ticker_decisions.values()), {})
                
                action, quantity, reasoning = (
                    decision.get("action", "hold"),
                    decision.get("quantity", 0.0),
                    decision.get("reasoning", "")
                )
                executed_quantity = executed_trades.get(ticker, 0.0)
                current_price = current_prices[ticker]
                pos = self.portfolio["positions"][ticker]

                trade_record["trades"].append({
                    "ticker": ticker,
                    "action": action,
                    "quantity_desired": quantity,
                    "quantity_executed": executed_quantity,
                    "current_price": current_price,
                    "current_long_shares": pos["long"],
                    "current_short_shares": pos["short"],
                    "current_long_cost_basis": pos["long_cost_basis"],
                    "current_short_cost_basis": pos["short_cost_basis"],
                    "reasoning": reasoning,
                    "analyst_signals": analyst_signals.get(ticker, {}) # Include all signals for the ticker
                })
            self.trade_log.append(trade_record)

            # ---------------------------------------------------------------
            # 3) Build the table rows to display
            # ---------------------------------------------------------------
            date_rows = []

            # For each ticker, record signals/trades
            for ticker in self.tickers:
                ticker_signals = {}
                bullish_count = 0
                bearish_count = 0
                neutral_count = 0
                
                # Extract signals from each agent (signals structure: agent -> ticker -> interval -> signal)
                # Count signals per agent (one signal per agent, using primary interval)
                for agent_name, agent_data in analyst_signals.items():
                    if agent_name == "risk_management_agent":
                        continue
                    if ticker in agent_data:
                        ticker_data = agent_data[ticker]
                        if isinstance(ticker_data, dict):
                            # Use primary interval signal (same logic as portfolio node)
                            primary_signal = None
                            primary_interval_str = self.primary_interval.value if hasattr(self.primary_interval, 'value') else str(self.primary_interval)
                            
                            # Try to find primary interval signal first
                            if primary_interval_str in ticker_data:
                                primary_signal = ticker_data[primary_interval_str]
                            elif ticker_data:
                                # Fallback to first available interval
                                primary_signal = next(iter(ticker_data.values()), None)
                            
                            if primary_signal and isinstance(primary_signal, dict):
                                signal = primary_signal.get("signal", "neutral").lower()
                                if signal == "bullish":
                                    bullish_count += 1
                                elif signal == "bearish":
                                    bearish_count += 1
                                else:
                                    neutral_count += 1
                                # Store signal for reference
                                ticker_signals[agent_name] = primary_signal

                # Calculate net position value
                pos = self.portfolio["positions"][ticker]
                long_val = pos["long"] * current_prices[ticker]
                short_val = pos["short"] * current_prices[ticker]
                net_position_value = long_val - short_val

                # Get the action and quantity from the decisions
                # Decisions structure: {ticker: {timepoint: {action, quantity, ...}}}
                ticker_decisions = decisions.get(ticker, {})
                decision = ticker_decisions.get("now", {})
                if not decision and ticker_decisions:
                    # Fallback to first available timepoint
                    decision = next(iter(ticker_decisions.values()), {})
                
                action = decision.get("action", "hold")
                # Use executed quantity (actual quantity traded), not desired quantity
                quantity = executed_trades.get(ticker, 0.0)
                
                # If action is hold but quantity > 0, it means a trade was executed in previous iteration
                # Show the actual action that was executed
                if action == "hold" and quantity > 0:
                    # Try to infer action from position changes
                    pos = self.portfolio["positions"][ticker]
                    if pos["short"] > 0:
                        action = "short"  # Likely a short position was opened
                    elif pos["long"] > 0:
                        action = "buy"  # Likely a long position was opened

                # Append the agent action to the table rows
                date_rows.append(
                    format_backtest_row(
                        date=date_display,
                        ticker=ticker,
                        action=action,
                        quantity=quantity,
                        price=current_prices[ticker],
                        shares_owned=pos["long"] - pos["short"],  # net shares
                        position_value=net_position_value,
                        bullish_count=bullish_count,
                        bearish_count=bearish_count,
                        neutral_count=neutral_count,
                    )
                )
            # ---------------------------------------------------------------
            # 4) Calculate performance summary metrics
            # ---------------------------------------------------------------
            # Calculate portfolio return vs. initial portfolio value (including initial positions)
            # The realized gains are already reflected in cash balance, so we don't add them separately
            initial_value = self.initial_portfolio_value if self.initial_portfolio_value else self.initial_capital
            portfolio_return = (total_value / initial_value - 1) * 100

            # Add summary row for this day
            date_rows.append(
                format_backtest_row(
                    date=date_display,
                    ticker="",
                    action="",
                    quantity=0,
                    price=0,
                    shares_owned=0,
                    position_value=0,
                    bullish_count=0,
                    bearish_count=0,
                    neutral_count=0,
                    is_summary=True,
                    total_value=total_value,
                    return_pct=portfolio_return,
                    cash_balance=self.portfolio["cash"],
                    total_position_value=total_value - self.portfolio["cash"],
                    sharpe_ratio=performance_metrics["sharpe_ratio"],
                    sortino_ratio=performance_metrics["sortino_ratio"],
                    max_drawdown=performance_metrics["max_drawdown"],
                ),
            )

            # Print results based on frequency
            should_print = (iteration_count % self.print_frequency == 0) or (iteration_count == len(data_df))
            is_first = (iteration_count == 1)
            is_final = (iteration_count == len(data_df))
            
            if should_print:
                table_rows.extend(date_rows)
                # Never clear screen to preserve backtest execution history
                print_backtest_results(table_rows, clear_screen=False, max_rows=15)
                
                # Log to file if enabled
                if self.logger:
                    self.logger.info(f"Iteration {iteration_count}/{len(data_df)}: Portfolio Value = ${total_value:,.2f}")
            
            # Update progress bar (set_postfix defaults to refresh=True; avoid double refresh per iter)
            if progress_bar:
                progress_bar.set_postfix(
                    {
                        "Value": f"${total_value:,.2f}",
                        "Return": f"{portfolio_return:.2f}%",
                    },
                    refresh=False,
                )
                progress_bar.update(1)

            # Update performance metrics if we have enough data
            if len(self.portfolio_values) > 3:
                self._update_performance_metrics(performance_metrics)
        
        # Close progress bar
        if progress_bar:
            progress_bar.close()

        # Store the final performance metrics for reference in analyze_performance
        self.performance_metrics = performance_metrics
        return {"performance_metrics": performance_metrics, "trade_log": self.trade_log}

    def _update_performance_metrics(self, performance_metrics):
        """Helper method to update performance metrics using daily returns."""
        values_df = pd.DataFrame(self.portfolio_values).set_index("Date")
        values_df["Daily Return"] = values_df["Portfolio Value"].pct_change()
        clean_returns = values_df["Daily Return"].dropna()

        if len(clean_returns) < 2:
            return  # not enough data points

        # Assumes 365 trading days/year
        daily_risk_free_rate = RISK_FREE_RATE_ANNUAL / 365
        excess_returns = clean_returns - daily_risk_free_rate
        mean_excess_return = excess_returns.mean()
        std_excess_return = excess_returns.std()

        # Sharpe ratio
        if std_excess_return > 1e-12:
            performance_metrics["sharpe_ratio"] = np.sqrt(365) * (mean_excess_return / std_excess_return)
        else:
            performance_metrics["sharpe_ratio"] = 0.0

        # Sortino ratio
        negative_returns = excess_returns[excess_returns < 0]
        if len(negative_returns) > 0:
            downside_std = negative_returns.std()
            if downside_std > 1e-12:
                performance_metrics["sortino_ratio"] = np.sqrt(365) * (mean_excess_return / downside_std)
            else:
                performance_metrics["sortino_ratio"] = float("inf") if mean_excess_return > 0 else 0
        else:
            performance_metrics["sortino_ratio"] = float("inf") if mean_excess_return > 0 else 0

        # Maximum drawdown (ensure it's stored as a negative percentage)
        rolling_max = values_df["Portfolio Value"].cummax()
        drawdown = (values_df["Portfolio Value"] - rolling_max) / rolling_max

        if len(drawdown) > 0:
            min_drawdown = drawdown.min()
            # Store as a negative percentage
            performance_metrics["max_drawdown"] = min_drawdown * 100

            # Store the date of max drawdown (calendar day in display timezone; index is wall naive)
            if min_drawdown < 0:
                dd_ts = drawdown.idxmin()
                performance_metrics["max_drawdown_date"] = pd.Timestamp(dd_ts).strftime("%Y-%m-%d")
            else:
                performance_metrics["max_drawdown_date"] = None
        else:
            performance_metrics["max_drawdown"] = 0.0
            performance_metrics["max_drawdown_date"] = None

    def analyze_performance(self):
        """Creates a performance DataFrame, prints summary stats, and plots equity curve."""
        if not self.portfolio_values:
            print("No portfolio data found. Please run the backtest first.")
            return pd.DataFrame()

        performance_df = pd.DataFrame(self.portfolio_values).set_index("Date")
        if performance_df.empty:
            print("No valid performance data to analyze.")
            return performance_df

        final_portfolio_value = performance_df["Portfolio Value"].iloc[-1]
        initial_value = self.initial_portfolio_value if self.initial_portfolio_value else self.initial_capital
        total_return = ((final_portfolio_value - initial_value) / initial_value) * 100

        print(f"\n{Fore.WHITE}{Style.BRIGHT}PORTFOLIO PERFORMANCE SUMMARY:{Style.RESET_ALL}")
        print(f"Total Return (vs Initial Portfolio Value): {Fore.GREEN if total_return >= 0 else Fore.RED}{total_return:.2f}%{Style.RESET_ALL}")
        print(f"  Initial Portfolio Value: ${initial_value:,.2f}")
        print(f"  Final Portfolio Value: ${final_portfolio_value:,.2f}")

        # Print realized P&L for informational purposes only
        total_realized_gains = sum(
            self.portfolio["realized_gains"][ticker]["long"] + self.portfolio["realized_gains"][ticker]["short"] for
            ticker in self.tickers)
        print(
            f"Total Realized Gains/Losses: {Fore.GREEN if total_realized_gains >= 0 else Fore.RED}${total_realized_gains:,.2f}{Style.RESET_ALL}")

        # Plot the portfolio value over time (index is wall clock in naive_date_timezone)
        plt.figure(figsize=(12, 6))
        plt.plot(performance_df.index, performance_df["Portfolio Value"], color="blue", linewidth=2)
        plt.title("Portfolio Value Over Time", fontsize=14, fontweight='bold')
        plt.ylabel("Portfolio Value ($)", fontsize=12)
        plt.xlabel(f"Date ({self.naive_date_timezone})", fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save the plot to file (experiment_label matches export_backtest_trades_and_performance)
        timestamp = now_config_wall_strftime("%Y%m%d_%H%M%S", self.naive_date_timezone)
        if self._experiment_label:
            slug = slugify_experiment_label(self._experiment_label)
            plot_path = self.output_dir / f"backtest_portfolio_value_{slug}_{timestamp}.png"
        else:
            plot_path = self.output_dir / f"backtest_portfolio_value_{timestamp}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"{Fore.GREEN}Portfolio value chart saved to: {plot_path}{Style.RESET_ALL}")
        
        # Optionally show the plot (only if display is available)
        try:
            plt.show()
        except Exception:
            # If display is not available (e.g., headless server), skip showing
            pass
        
        plt.close()  # Close the figure to free memory

        # Compute daily returns
        performance_df["Daily Return"] = performance_df["Portfolio Value"].pct_change().fillna(0)
        daily_rf = RISK_FREE_RATE_ANNUAL / 365  # daily risk-free rate
        mean_daily_return = performance_df["Daily Return"].mean()
        std_daily_return = performance_df["Daily Return"].std()

        # Ensure performance_metrics has the latest values before printing
        self._update_performance_metrics(self.performance_metrics)

        # Print the key metrics from the updated performance_metrics
        sharpe_ratio = self.performance_metrics.get("sharpe_ratio", 0.0)
        max_drawdown = self.performance_metrics.get("max_drawdown", 0.0)
        max_drawdown_date = self.performance_metrics.get("max_drawdown_date", "N/A")

        print(f"Sharpe Ratio: {Fore.YELLOW}{sharpe_ratio:.2f}{Style.RESET_ALL}")
        if max_drawdown_date != "N/A":
            print(f"Maximum Drawdown: {Fore.RED}{abs(max_drawdown):.2f}%{Style.RESET_ALL} (on {max_drawdown_date})")
        else:
            print(f"Maximum Drawdown: {Fore.RED}{abs(max_drawdown):.2f}%{Style.RESET_ALL}")

        # Win Rate calculation is already correct, just ensure it's printed
        winning_days = len(performance_df[performance_df["Daily Return"] > 0])
        total_days = max(len(performance_df) - 1, 1) # Avoid division by zero
        win_rate = (winning_days / total_days) * 100
        print(f"Win Rate: {Fore.GREEN}{win_rate:.2f}%{Style.RESET_ALL}")

        # Average Win/Loss Ratio
        positive_returns = performance_df[performance_df["Daily Return"] > 0]["Daily Return"]
        negative_returns = performance_df[performance_df["Daily Return"] < 0]["Daily Return"]
        avg_win = positive_returns.mean() if not positive_returns.empty else 0
        avg_loss = abs(negative_returns.mean()) if not negative_returns.empty else 0
        if avg_loss != 0:
            win_loss_ratio = avg_win / avg_loss
        else:
            win_loss_ratio = float("inf") if avg_win > 0 else 0
        print(f"Win/Loss Ratio: {Fore.GREEN}{win_loss_ratio:.2f}{Style.RESET_ALL}")

        # Maximum Consecutive Wins / Losses
        returns_binary = (performance_df["Daily Return"] > 0).astype(int)
        if len(returns_binary) > 0:
            max_consecutive_wins = max((len(list(g)) for k, g in itertools.groupby(returns_binary) if k == 1),
                                       default=0)
            max_consecutive_losses = max((len(list(g)) for k, g in itertools.groupby(returns_binary) if k == 0),
                                         default=0)
        else:
            max_consecutive_wins = 0
            max_consecutive_losses = 0

        print(f"Max Consecutive Wins: {Fore.GREEN}{max_consecutive_wins}{Style.RESET_ALL}")
        print(f"Max Consecutive Losses: {Fore.RED}{max_consecutive_losses}{Style.RESET_ALL}")

        return performance_df
