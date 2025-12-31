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


def print_backtest_results(table_rows: List[List[Any]], clear_screen: bool = False, max_rows: int = 15) -> None:
    """Print the backtest results in a nicely formatted table.
    
    Args:
        table_rows: List of table rows to display
        clear_screen: Whether to clear screen (default: False for performance)
        max_rows: Maximum number of rows to display (default: 15, shows recent rows only)
    """
    # Only clear screen if explicitly requested (first iteration or final)
    if clear_screen:
        os.system("cls" if os.name == "nt" else "clear")

    ticker_rows = []
    summary_rows = []

    for row in table_rows:
        if isinstance(row[1], str) and "PORTFOLIO SUMMARY" in row[1]:
            summary_rows.append(row)
        else:
            ticker_rows.append(row)

    # Limit table size for performance - only show recent rows
    if len(ticker_rows) > max_rows:
        ticker_rows = ticker_rows[-max_rows:]
        if ticker_rows:
            ticker_rows.insert(0, ["...", "...", "...", "...", "...", "...", "...", "...", "...", "..."])

    if summary_rows:
        latest_summary = summary_rows[-1]
        # Simplified parsing for better performance
        try:
            cash_str = latest_summary[7].split("$")[1].split(Style.RESET_ALL)[0].replace(",", "")
            position_str = latest_summary[6].split("$")[1].split(Style.RESET_ALL)[0].replace(",", "")
            total_str = latest_summary[8].split("$")[1].split(Style.RESET_ALL)[0].replace(",", "")
        except (IndexError, AttributeError):
            cash_str = "0"
            position_str = "0"
            total_str = "0"

        print(f"\n{Fore.WHITE}{Style.BRIGHT}PORTFOLIO SUMMARY:{Style.RESET_ALL}")
        # Parse return percentage from summary[9] which contains the return string
        return_str = latest_summary[9] if len(latest_summary) > 9 else ""
        if return_str:
            print(f"Cash: {Fore.CYAN}${float(cash_str):,.2f}{Style.RESET_ALL} | "
                  f"Positions: {Fore.YELLOW}${float(position_str):,.2f}{Style.RESET_ALL} | "
                  f"Total: {Fore.WHITE}${float(total_str):,.2f}{Style.RESET_ALL} | "
                  f"Return (vs Initial Portfolio Value): {return_str}")
        else:
            print(f"Cash: {Fore.CYAN}${float(cash_str):,.2f}{Style.RESET_ALL} | "
                  f"Positions: {Fore.YELLOW}${float(position_str):,.2f}{Style.RESET_ALL} | "
                  f"Total: {Fore.WHITE}${float(total_str):,.2f}{Style.RESET_ALL}")

        # Always show metrics row, even if values are not yet calculated (will show empty or N/A)
        sharpe_str = latest_summary[10] if len(latest_summary) > 10 and latest_summary[10] else "N/A"
        sortino_str = latest_summary[11] if len(latest_summary) > 11 and latest_summary[11] else "N/A"
        drawdown_str = latest_summary[12] if len(latest_summary) > 12 and latest_summary[12] else "N/A"
        print(f"Sharpe Ratio: {sharpe_str} | Sortino Ratio: {sortino_str} | Max Drawdown: {drawdown_str}")

    # Use simpler table format for better performance
    if ticker_rows:
        print("\n" + tabulate(
            ticker_rows,
            headers=["Date", "Ticker", "Action", "Qty", "Price", "Shares", "Value", "B", "S", "N"],
            tablefmt="simple",  # Changed from "grid" to "simple" for 3-5x faster rendering
            colalign=("left", "left", "center", "right", "right", "right", "right", "right", "right", "right"),
        ))
    print()  # Single newline instead of multiple


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
        
        # Process each agent separately for detailed display
        for agent_name, signals in analyst_signals.items():
            if agent_name == "risk_management_agent":
                continue
            if not isinstance(signals, dict):
                continue
            
            # Get agent display name
            agent_display_name = agent_name.replace("_", " ").title()
            print(f"{Fore.CYAN}{Style.BRIGHT}{agent_display_name}:{Style.RESET_ALL}\n")
            
            # Process each ticker
            signal_rows = []
            for ticker, signal_data in signals.items():
                if not isinstance(signal_data, dict):
                    continue
                
                # Check if signal_data is interval-based (ticker -> interval -> signal)
                is_interval_based = any(
                    isinstance(v, dict) and ("signal" in v or "confidence" in v)
                    for v in signal_data.values()
                )
                
                if is_interval_based:
                    # Display signals for each interval
                    for interval, interval_data in signal_data.items():
                        if not isinstance(interval_data, dict):
                            continue
                        
                        direction = interval_data.get("signal", "neutral")
                        confidence = interval_data.get("confidence", 0.0)
                        
                        # Normalize direction
                        if direction == "bullish":
                            direction = "BULLISH"
                        elif direction == "bearish":
                            direction = "BEARISH"
                        else:
                            direction = "NEUTRAL"
                        
                        direction_color = {
                            "BULLISH": Fore.GREEN,
                            "BEARISH": Fore.RED,
                            "NEUTRAL": Fore.YELLOW,
                        }.get(direction, Fore.WHITE)
                        
                        # Extract detailed metrics
                        metrics_info = []
                        strategy_signals = interval_data.get("strategy_signals", {})
                        
                        if strategy_signals:
                            for sub_strategy, sub_data in strategy_signals.items():
                                if isinstance(sub_data, dict):
                                    sub_metrics = sub_data.get("metrics", {})
                                    if sub_metrics:
                                        # Format key metrics based on strategy type
                                        metric_strs = []
                                        for key, value in sub_metrics.items():
                                            if value is not None:
                                                try:
                                                    import pandas as pd
                                                    is_na = pd.isna(value) if isinstance(value, float) else False
                                                except ImportError:
                                                    is_na = False
                                                if not is_na:
                                                    # Format metric name and value
                                                    metric_name = key.replace("_", " ").title()
                                                    if isinstance(value, float):
                                                        metric_strs.append(f"{metric_name}: {value:.2f}")
                                                    elif isinstance(value, (int, str)):
                                                        metric_strs.append(f"{metric_name}: {value}")
                                        
                                        if metric_strs:
                                            # Limit to 2-3 key metrics per sub-strategy
                                            key_metrics = metric_strs[:3]
                                            metrics_info.append(f"{Fore.WHITE}{sub_strategy.replace('_', ' ').title()}{Style.RESET_ALL}: {', '.join(key_metrics)}")
                        
                        # Build signal display with color coding
                        conf_color = Fore.GREEN if confidence >= 70 else (Fore.YELLOW if confidence >= 40 else Fore.RED)
                        signal_display = f"{direction_color}{direction}{Style.RESET_ALL} {conf_color}({confidence:.0f}%){Style.RESET_ALL}"
                        
                        if metrics_info:
                            # Display metrics on new lines for better readability
                            signal_display += "\n" + "\n".join([f"  {info}" for info in metrics_info[:2]])  # Limit to 2 sub-strategies
                        
                        signal_rows.append([
                            f"{Fore.CYAN}{ticker}{Style.RESET_ALL}",
                            f"{Fore.YELLOW}{interval.upper()}{Style.RESET_ALL}",
                            signal_display
                        ])
                else:
                    # Direct signal format (backward compatibility)
                    direction = signal_data.get("signal", "neutral")
                    confidence = signal_data.get("confidence", 0.0)
                    
                    if direction == "bullish":
                        direction = "BULLISH"
                    elif direction == "bearish":
                        direction = "BEARISH"
                    else:
                        direction = "NEUTRAL"
                    
                    direction_color = {
                        "BULLISH": Fore.GREEN,
                        "BEARISH": Fore.RED,
                        "NEUTRAL": Fore.YELLOW,
                    }.get(direction, Fore.WHITE)
                    
                    signal_rows.append([
                        f"{Fore.CYAN}{ticker}{Style.RESET_ALL}",
                        f"{Fore.YELLOW}ALL{Style.RESET_ALL}",
                        f"{direction_color}{direction}{Style.RESET_ALL} ({confidence:.0f}%)"
                    ])
            
            if signal_rows:
                print(tabulate(
                    signal_rows,
                    headers=[
                        f"{Fore.CYAN}Ticker{Style.RESET_ALL}",
                        f"{Fore.YELLOW}Interval{Style.RESET_ALL}",
                        f"{Fore.WHITE}Signal & Details{Style.RESET_ALL}"
                    ],
                    tablefmt="grid",
                    colalign=("left", "center", "left"),
                ))
            else:
                print(f"{Fore.YELLOW}  No signals available for {agent_display_name}{Style.RESET_ALL}")
            
            print()  # Empty line between agents
    
    print("\n" + "=" * 80 + "\n")
