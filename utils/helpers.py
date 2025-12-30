"""
Helper functions for the trading system.
"""
import importlib
import orjson
import os
from typing import Any, List, Dict, Optional
from langchain_core.runnables.graph import MermaidDrawMethod
from colorama import Fore, Style
from tabulate import tabulate
from .constants import QUANTITY_DECIMALS


def import_strategy_class(class_path: str) -> Any:
    """
    Dynamically import a strategy class from a module path.
    
    Args:
        class_path: Dot-separated path like 'strategies.macd.MacdStrategy'
        
    Returns:
        The strategy class
    """
    module_path, class_name = class_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def save_graph_as_png(graph: Any, output_path: str) -> None:
    """
    Save workflow graph as PNG image.
    
    Args:
        graph: Compiled LangGraph
        output_path: Path to save the PNG file
    """
    png_image = graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
    file_path = output_path if output_path else "graph.png"
    with open(file_path, "wb") as f:
        f.write(png_image)


def parse_str_to_json(response: str) -> dict:
    """
    Parse JSON string to dictionary.
    
    Args:
        response: JSON string to parse
        
    Returns:
        Parsed dictionary or None if parsing fails
    """
    try:
        return orjson.loads(response)
    except (orjson.JSONDecodeError, TypeError) as e:
        print(f"JSON parsing error: {e}\nResponse: {repr(response)}")
        return {}
    except Exception as e:
        print(f"Unexpected error parsing JSON: {e}\nResponse: {repr(response)}")
        return {}


def format_backtest_row(
    date: str,
    ticker: str,
    action: str,
    quantity: float,
    price: float,
    shares_owned: float,
    position_value: float,
    bullish_count: int,
    bearish_count: int,
    neutral_count: int,
    is_summary: bool = False,
    total_value: float = None,
    return_pct: float = None,
    cash_balance: float = None,
    total_position_value: float = None,
    sharpe_ratio: float = None,
    sortino_ratio: float = None,
    max_drawdown: float = None,
) -> List[Any]:
    """Format a row for the backtest results table."""
    action_color = {
        "BUY": Fore.GREEN,
        "COVER": Fore.GREEN,
        "SELL": Fore.RED,
        "SHORT": Fore.RED,
        "HOLD": Fore.WHITE,
    }.get(action.upper(), Fore.WHITE)

    if is_summary:
        return_color = Fore.GREEN if return_pct >= 0 else Fore.RED
        return [
            date,
            f"{Fore.WHITE}{Style.BRIGHT}PORTFOLIO SUMMARY{Style.RESET_ALL}",
            "",
            "",
            "",
            "",
            f"{Fore.YELLOW}${total_position_value:,.2f}{Style.RESET_ALL}",
            f"{Fore.CYAN}${cash_balance:,.2f}{Style.RESET_ALL}",
            f"{Fore.WHITE}${total_value:,.2f}{Style.RESET_ALL}",
            f"{return_color}{return_pct:+.2f}%{Style.RESET_ALL}",
            f"{Fore.YELLOW}{sharpe_ratio:.2f}{Style.RESET_ALL}" if sharpe_ratio is not None else "",
            f"{Fore.YELLOW}{sortino_ratio:.2f}{Style.RESET_ALL}" if sortino_ratio is not None else "",
            f"{Fore.RED}{abs(max_drawdown):.2f}%{Style.RESET_ALL}" if max_drawdown is not None else "",
        ]
    else:
        return [
            date,
            f"{Fore.CYAN}{ticker}{Style.RESET_ALL}",
            f"{action_color}{action.upper()}{Style.RESET_ALL}",
            f"{action_color}{quantity:,.{QUANTITY_DECIMALS}f}{Style.RESET_ALL}",
            f"{Fore.WHITE}{price:,.2f}{Style.RESET_ALL}",
            f"{Fore.WHITE}{shares_owned:,.{QUANTITY_DECIMALS}f}{Style.RESET_ALL}",
            f"{Fore.YELLOW}{position_value:,.2f}{Style.RESET_ALL}",
            f"{Fore.GREEN}{bullish_count}{Style.RESET_ALL}",
            f"{Fore.RED}{bearish_count}{Style.RESET_ALL}",
            f"{Fore.BLUE}{neutral_count}{Style.RESET_ALL}",
        ]


def print_backtest_results(table_rows: List[List[Any]]) -> None:
    """Print the backtest results in a nicely formatted table."""
    os.system("cls" if os.name == "nt" else "clear")

    ticker_rows = []
    summary_rows = []

    for row in table_rows:
        if isinstance(row[1], str) and "PORTFOLIO SUMMARY" in row[1]:
            summary_rows.append(row)
        else:
            ticker_rows.append(row)

    if summary_rows:
        latest_summary = summary_rows[-1]
        print(f"\n{Fore.WHITE}{Style.BRIGHT}PORTFOLIO SUMMARY:{Style.RESET_ALL}")

        cash_str = latest_summary[7].split("$")[1].split(Style.RESET_ALL)[0].replace(",", "")
        position_str = latest_summary[6].split("$")[1].split(Style.RESET_ALL)[0].replace(",", "")
        total_str = latest_summary[8].split("$")[1].split(Style.RESET_ALL)[0].replace(",", "")

        print(f"Cash Balance: {Fore.CYAN}${float(cash_str):,.2f}{Style.RESET_ALL}")
        print(f"Total Position Value: {Fore.YELLOW}${float(position_str):,.2f}{Style.RESET_ALL}")
        print(f"Total Value: {Fore.WHITE}${float(total_str):,.2f}{Style.RESET_ALL}")
        print(f"Return: {latest_summary[9]}")

        if latest_summary[10]:
            print(f"Sharpe Ratio: {latest_summary[10]}")
        if latest_summary[11]:
            print(f"Sortino Ratio: {latest_summary[11]}")
        if latest_summary[12]:
            print(f"Max Drawdown: {latest_summary[12]}")

    print("\n" * 2)

    print(
        tabulate(
            ticker_rows,
            headers=[
                "Date",
                "Ticker",
                "Action",
                "Quantity",
                "Price",
                "Shares",
                "Position Value",
                "Bullish",
                "Bearish",
                "Neutral",
            ],
            tablefmt="grid",
            colalign=(
                "left", "left", "center", "right", "right",
                "right", "right", "right", "right", "right",
            ),
        )
    )

    print("\n" * 4)


def format_live_results(decisions: Dict[str, Any], analyst_signals: Optional[Dict[str, Any]] = None) -> None:
    """
    Format and display live trading results in a beautiful way.
    
    Args:
        decisions: Trading decisions dictionary
        analyst_signals: Optional analyst signals dictionary
    """
    from colorama import Fore, Style, init
    from tabulate import tabulate
    
    # Initialize colorama for Windows compatibility
    init(autoreset=True)
    
    print("\n" + "=" * 80)
    print(f"{Fore.WHITE}{Style.BRIGHT}LIVE TRADING RESULTS{Style.RESET_ALL}".center(80))
    print("=" * 80 + "\n")
    
    if not decisions:
        print(f"{Fore.YELLOW}No trading decisions generated.{Style.RESET_ALL}\n")
        return
    
    # Check if decisions are structured by timepoints (new format)
    first_ticker = list(decisions.keys())[0] if decisions else None
    is_timepoint_format = first_ticker and isinstance(decisions.get(first_ticker), dict) and "now" in decisions.get(first_ticker, {})
    
    if is_timepoint_format:
        # New format: decisions organized by timepoints
        timepoints = ["now", "1h", "4h", "1d"]  # Common timepoints, will filter based on what exists
        
        # Display decisions for each timepoint
        for timepoint in timepoints:
            # Check if this timepoint exists in any ticker's decisions
            has_timepoint = any(
                timepoint in decisions.get(ticker, {}) 
                for ticker in decisions.keys()
            )
            
            if not has_timepoint:
                continue
            
            timepoint_label = "NOW (Current)" if timepoint == "now" else f"{timepoint.upper()} (Future)"
            print(f"\n{Fore.WHITE}{Style.BRIGHT}TRADING DECISIONS - {timepoint_label}:{Style.RESET_ALL}\n")
            
            table_rows = []
            for ticker, ticker_decisions in decisions.items():
                if not isinstance(ticker_decisions, dict) or timepoint not in ticker_decisions:
                    continue
                
                decision = ticker_decisions[timepoint]
                action = decision.get("action", "hold").upper()
                quantity = decision.get("quantity", 0.0)
                confidence = decision.get("confidence", 0.0)
                
                # Color code actions
                action_color = {
                    "BUY": Fore.GREEN,
                    "COVER": Fore.GREEN,
                    "SELL": Fore.RED,
                    "SHORT": Fore.RED,
                    "HOLD": Fore.YELLOW,
                }.get(action, Fore.WHITE)
                
                # Color code confidence
                if confidence >= 70:
                    conf_color = Fore.GREEN
                elif confidence >= 40:
                    conf_color = Fore.YELLOW
                else:
                    conf_color = Fore.RED
                
                table_rows.append([
                    f"{Fore.CYAN}{ticker}{Style.RESET_ALL}",
                    f"{action_color}{action}{Style.RESET_ALL}",
                    f"{Fore.WHITE}{quantity:,.4f}{Style.RESET_ALL}",
                    f"{conf_color}{confidence:.1f}%{Style.RESET_ALL}",
                ])
            
            if table_rows:
                print(tabulate(
                    table_rows,
                    headers=[
                        f"{Fore.CYAN}Ticker{Style.RESET_ALL}",
                        f"{Fore.WHITE}Action{Style.RESET_ALL}",
                        f"{Fore.WHITE}Quantity{Style.RESET_ALL}",
                        f"{Fore.WHITE}Confidence{Style.RESET_ALL}",
                    ],
                    tablefmt="grid",
                    colalign=("left", "center", "right", "right"),
                ))
        
        # Display detailed reasoning for each timepoint
        print(f"\n{Fore.WHITE}{Style.BRIGHT}DETAILED REASONING BY TIMEPOINT:{Style.RESET_ALL}\n")
        for ticker, ticker_decisions in decisions.items():
            if not isinstance(ticker_decisions, dict):
                continue
                
            print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{Style.BRIGHT}{ticker}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
            
            for timepoint in timepoints:
                if timepoint not in ticker_decisions:
                    continue
                
                decision = ticker_decisions[timepoint]
                reasoning = decision.get("reasoning", "")
                action = decision.get("action", "hold").upper()
                confidence = decision.get("confidence", 0.0)
                
                timepoint_label = "NOW (Current Timepoint)" if timepoint == "now" else f"{timepoint.upper()} (Future Timepoint)"
                
                print(f"{Fore.YELLOW}{Style.BRIGHT}[{timepoint_label}]{Style.RESET_ALL}")
                print(f"Action: {Fore.GREEN if action in ['BUY', 'COVER'] else Fore.RED if action in ['SELL', 'SHORT'] else Fore.YELLOW}{action}{Style.RESET_ALL} | Confidence: {confidence:.1f}%")
                print(f"{Fore.WHITE}{reasoning}{Style.RESET_ALL}\n")
                print("-" * 80 + "\n")
    else:
        # Old format: single decision per ticker (backward compatibility)
        table_rows = []
        for ticker, decision in decisions.items():
            action = decision.get("action", "hold").upper()
            quantity = decision.get("quantity", 0.0)
            confidence = decision.get("confidence", 0.0)
            reasoning = decision.get("reasoning", "")
            
            # Color code actions
            action_color = {
                "BUY": Fore.GREEN,
                "COVER": Fore.GREEN,
                "SELL": Fore.RED,
                "SHORT": Fore.RED,
                "HOLD": Fore.YELLOW,
            }.get(action, Fore.WHITE)
            
            # Color code confidence
            if confidence >= 70:
                conf_color = Fore.GREEN
            elif confidence >= 40:
                conf_color = Fore.YELLOW
            else:
                conf_color = Fore.RED
            
            table_rows.append([
                f"{Fore.CYAN}{ticker}{Style.RESET_ALL}",
                f"{action_color}{action}{Style.RESET_ALL}",
                f"{Fore.WHITE}{quantity:,.4f}{Style.RESET_ALL}",
                f"{conf_color}{confidence:.1f}%{Style.RESET_ALL}",
            ])
        
        # Print decisions table
        print(f"{Fore.WHITE}{Style.BRIGHT}TRADING DECISIONS:{Style.RESET_ALL}\n")
        print(tabulate(
            table_rows,
            headers=[
                f"{Fore.CYAN}Ticker{Style.RESET_ALL}",
                f"{Fore.WHITE}Action{Style.RESET_ALL}",
                f"{Fore.WHITE}Quantity{Style.RESET_ALL}",
                f"{Fore.WHITE}Confidence{Style.RESET_ALL}",
            ],
            tablefmt="grid",
            colalign=("left", "center", "right", "right"),
        ))
        
        # Display full reasoning separately for each ticker
        print(f"\n{Fore.WHITE}{Style.BRIGHT}DETAILED REASONING:{Style.RESET_ALL}\n")
        for ticker, decision in decisions.items():
            reasoning = decision.get("reasoning", "")
            if reasoning:
                print(f"{Fore.CYAN}{ticker}{Style.RESET_ALL}:")
                print(f"{Fore.WHITE}{reasoning}{Style.RESET_ALL}\n")
                print("-" * 80 + "\n")
    
    # Display analyst signals if available
    if analyst_signals:
        print(f"\n{Fore.WHITE}{Style.BRIGHT}ANALYST SIGNALS:{Style.RESET_ALL}\n")
        
        # Process signals by agent and ticker
        for agent_name, agent_signals in analyst_signals.items():
            if agent_name == "risk_management_agent":
                continue
            
            if not isinstance(agent_signals, dict):
                continue
            
            # Display agent header
            print(f"\n{Fore.CYAN}{Style.BRIGHT}{agent_name.upper().replace('_', ' ')}{Style.RESET_ALL}")
            print("-" * 80)
            
            # Process each ticker
            for ticker, ticker_data in agent_signals.items():
                if not isinstance(ticker_data, dict):
                    continue
                
                print(f"\n{Fore.YELLOW}{Style.BRIGHT}{ticker}{Style.RESET_ALL}")
                
                # Process each interval
                for interval_key, interval_data in ticker_data.items():
                    if not isinstance(interval_data, dict):
                        continue
                    
                    signal = interval_data.get("signal", "neutral").upper()
                    confidence = interval_data.get("confidence", 0.0)
                    
                    # Color code signal
                    signal_color = {
                        "BULLISH": Fore.GREEN,
                        "BEARISH": Fore.RED,
                        "NEUTRAL": Fore.YELLOW,
                    }.get(signal, Fore.WHITE)
                    
                    # Display interval summary
                    conf_color = Fore.GREEN if confidence >= 70 else Fore.YELLOW if confidence >= 40 else Fore.RED
                    print(f"  {Fore.WHITE}Interval {interval_key}:{Style.RESET_ALL} "
                          f"{signal_color}{signal}{Style.RESET_ALL} "
                          f"({conf_color}{confidence:.0f}%{Style.RESET_ALL})")
                    
                    # Display detailed strategy signals
                    strategy_signals = interval_data.get("strategy_signals", {})
                    if strategy_signals:
                        for strategy_name, strategy_data in strategy_signals.items():
                            if isinstance(strategy_data, dict):
                                strategy_signal = strategy_data.get("signal", "neutral").upper()
                                strategy_conf = strategy_data.get("confidence", 0.0)
                                metrics = strategy_data.get("metrics", {})
                                
                                strategy_signal_color = {
                                    "BULLISH": Fore.GREEN,
                                    "BEARISH": Fore.RED,
                                    "NEUTRAL": Fore.YELLOW,
                                }.get(strategy_signal, Fore.WHITE)
                                
                                print(f"    {Fore.CYAN}→ {strategy_name.replace('_', ' ').title()}:{Style.RESET_ALL} "
                                      f"{strategy_signal_color}{strategy_signal}{Style.RESET_ALL} "
                                      f"({strategy_conf:.0f}%)")
                                
                                # Display key metrics
                                if metrics:
                                    metric_strs = []
                                    for metric_name, metric_value in metrics.items():
                                        if isinstance(metric_value, (int, float)):
                                            # Format metric value based on type
                                            if "rsi" in metric_name.lower():
                                                metric_strs.append(f"{metric_name}: {metric_value:.2f}")
                                            elif "band" in metric_name.lower() or "sma" in metric_name.lower() or "close" in metric_name.lower():
                                                metric_strs.append(f"{metric_name}: ${metric_value:,.2f}")
                                            elif "level" in metric_name.lower():
                                                metric_strs.append(f"{metric_name}: {metric_value}")
                                            elif isinstance(metric_value, float) and abs(metric_value) < 1 and abs(metric_value) > 0:
                                                metric_strs.append(f"{metric_name}: {metric_value:.4f}")
                                            elif isinstance(metric_value, float) and abs(metric_value) < 0.0001:
                                                # Very small numbers, use scientific notation
                                                metric_strs.append(f"{metric_name}: {metric_value:.2e}")
                                            else:
                                                metric_strs.append(f"{metric_name}: {metric_value:.2f}")
                                        elif isinstance(metric_value, str):
                                            metric_strs.append(f"{metric_name}: {metric_value}")
                                    
                                    if metric_strs:
                                        # Display metrics in a more readable format
                                        metrics_line = ', '.join(metric_strs)
                                        # Wrap long lines
                                        max_line_length = 100
                                        if len(metrics_line) > max_line_length:
                                            # Split into multiple lines
                                            words = metrics_line.split(', ')
                                            current_line = []
                                            current_length = 0
                                            for word in words:
                                                if current_length + len(word) + 2 > max_line_length and current_line:
                                                    print(f"      {Fore.WHITE}Metrics:{Style.RESET_ALL} {', '.join(current_line)}")
                                                    current_line = [word]
                                                    current_length = len(word)
                                                else:
                                                    current_line.append(word)
                                                    current_length += len(word) + 2
                                            if current_line:
                                                print(f"      {Fore.WHITE}Metrics:{Style.RESET_ALL} {', '.join(current_line)}")
                                        else:
                                            print(f"      {Fore.WHITE}Metrics:{Style.RESET_ALL} {metrics_line}")
                
                print()  # Empty line between tickers
            
            print()  # Empty line between agents
    
    print("\n" + "=" * 80 + "\n")
