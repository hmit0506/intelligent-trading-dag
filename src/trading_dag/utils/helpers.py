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

from trading_dag.utils.constants import QUANTITY_DECIMALS


def import_strategy_class(class_path: str) -> Any:
    """
    Dynamically import a strategy class from a module path.

    Args:
        class_path: Dot-separated path like 'trading_dag.strategies.macd.MacdStrategy'

    Returns:
        The strategy class
    """
    if not class_path.startswith("trading_dag."):
        class_path = f"trading_dag.{class_path}"
    module_path, class_name = class_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def save_graph_as_png(graph: Any, output_path: str) -> None:
    """Save workflow graph as PNG image."""
    png_image = graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
    file_path = output_path if output_path else "graph.png"
    with open(file_path, "wb") as f:
        f.write(png_image)


def parse_str_to_json(response: str) -> dict:
    """Parse JSON string to dictionary."""
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
            "", "", "", "",
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
    """Print the backtest results in a formatted table."""
    if clear_screen:
        os.system("cls" if os.name == "nt" else "clear")
    ticker_rows = []
    summary_rows = []
    for row in table_rows:
        if isinstance(row[1], str) and "PORTFOLIO SUMMARY" in row[1]:
            summary_rows.append(row)
        else:
            ticker_rows.append(row)
    if len(ticker_rows) > max_rows:
        ticker_rows = ticker_rows[-max_rows:]
        if ticker_rows:
            ticker_rows.insert(0, ["...", "...", "...", "...", "...", "...", "...", "...", "...", "..."])
    if summary_rows:
        latest_summary = summary_rows[-1]
        try:
            cash_str = latest_summary[7].split("$")[1].split(Style.RESET_ALL)[0].replace(",", "")
            position_str = latest_summary[6].split("$")[1].split(Style.RESET_ALL)[0].replace(",", "")
            total_str = latest_summary[8].split("$")[1].split(Style.RESET_ALL)[0].replace(",", "")
        except (IndexError, AttributeError):
            cash_str, position_str, total_str = "0", "0", "0"
        print(f"\n{Fore.WHITE}{Style.BRIGHT}PORTFOLIO SUMMARY:{Style.RESET_ALL}")
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
        sharpe_str = latest_summary[10] if len(latest_summary) > 10 and latest_summary[10] else "N/A"
        sortino_str = latest_summary[11] if len(latest_summary) > 11 and latest_summary[11] else "N/A"
        drawdown_str = latest_summary[12] if len(latest_summary) > 12 and latest_summary[12] else "N/A"
        print(f"Sharpe Ratio: {sharpe_str} | Sortino Ratio: {sortino_str} | Max Drawdown: {drawdown_str}")
    if ticker_rows:
        print("\n" + tabulate(
            ticker_rows,
            headers=["Date", "Ticker", "Action", "Qty", "Price", "Shares", "Value", "B", "S", "N"],
            tablefmt="simple",
            colalign=("left", "left", "center", "right", "right", "right", "right", "right", "right", "right"),
        ))
    print()


def format_live_results(decisions: Dict[str, Any], analyst_signals: Optional[Dict[str, Any]] = None) -> None:
    """Format and display live trading results."""
    from tabulate import tabulate
    from colorama import init
    init(autoreset=True)
    print("\n" + "=" * 80)
    print(f"{Fore.WHITE}{Style.BRIGHT}LIVE TRADING RESULTS{Style.RESET_ALL}".center(80))
    print("=" * 80 + "\n")
    if not decisions:
        print(f"{Fore.YELLOW}No trading decisions generated.{Style.RESET_ALL}\n")
        return
    first_ticker = list(decisions.keys())[0] if decisions else None
    is_timepoint_format = first_ticker and isinstance(decisions.get(first_ticker), dict) and "now" in decisions.get(first_ticker, {})
    if is_timepoint_format:
        timepoints = ["now", "1h", "4h", "1d"]
        for timepoint in timepoints:
            has_timepoint = any(timepoint in decisions.get(ticker, {}) for ticker in decisions.keys())
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
                action_color = {"BUY": Fore.GREEN, "COVER": Fore.GREEN, "SELL": Fore.RED, "SHORT": Fore.RED, "HOLD": Fore.YELLOW}.get(action, Fore.WHITE)
                conf_color = Fore.GREEN if confidence >= 70 else (Fore.YELLOW if confidence >= 40 else Fore.RED)
                table_rows.append([f"{Fore.CYAN}{ticker}{Style.RESET_ALL}", f"{action_color}{action}{Style.RESET_ALL}",
                                  f"{Fore.WHITE}{quantity:,.4f}{Style.RESET_ALL}", f"{conf_color}{confidence:.1f}%{Style.RESET_ALL}"])
            if table_rows:
                print(tabulate(table_rows, headers=[f"{Fore.CYAN}Ticker{Style.RESET_ALL}", f"{Fore.WHITE}Action{Style.RESET_ALL}",
                    f"{Fore.WHITE}Quantity{Style.RESET_ALL}", f"{Fore.WHITE}Confidence{Style.RESET_ALL}"],
                    tablefmt="grid", colalign=("left", "center", "right", "right")))
        print(f"\n{Fore.WHITE}{Style.BRIGHT}DETAILED REASONING BY TIMEPOINT:{Style.RESET_ALL}\n")
        for ticker, ticker_decisions in decisions.items():
            if not isinstance(ticker_decisions, dict):
                continue
            print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n{Fore.CYAN}{Style.BRIGHT}{ticker}{Style.RESET_ALL}\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
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
                print(f"{Fore.WHITE}{reasoning}{Style.RESET_ALL}\n\n" + "-" * 80 + "\n")
    else:
        table_rows = []
        for ticker, decision in decisions.items():
            action = decision.get("action", "hold").upper()
            quantity = decision.get("quantity", 0.0)
            confidence = decision.get("confidence", 0.0)
            action_color = {"BUY": Fore.GREEN, "COVER": Fore.GREEN, "SELL": Fore.RED, "SHORT": Fore.RED, "HOLD": Fore.YELLOW}.get(action, Fore.WHITE)
            conf_color = Fore.GREEN if confidence >= 70 else (Fore.YELLOW if confidence >= 40 else Fore.RED)
            table_rows.append([f"{Fore.CYAN}{ticker}{Style.RESET_ALL}", f"{action_color}{action}{Style.RESET_ALL}",
                              f"{Fore.WHITE}{quantity:,.4f}{Style.RESET_ALL}", f"{conf_color}{confidence:.1f}%{Style.RESET_ALL}"])
        print(f"{Fore.WHITE}{Style.BRIGHT}TRADING DECISIONS:{Style.RESET_ALL}\n")
        print(tabulate(table_rows, headers=[f"{Fore.CYAN}Ticker{Style.RESET_ALL}", f"{Fore.WHITE}Action{Style.RESET_ALL}",
            f"{Fore.WHITE}Quantity{Style.RESET_ALL}", f"{Fore.WHITE}Confidence{Style.RESET_ALL}"],
            tablefmt="grid", colalign=("left", "center", "right", "right")))
        print(f"\n{Fore.WHITE}{Style.BRIGHT}DETAILED REASONING:{Style.RESET_ALL}\n")
        for ticker, decision in decisions.items():
            reasoning = decision.get("reasoning", "")
            if reasoning:
                print(f"{Fore.CYAN}{ticker}{Style.RESET_ALL}:\n{Fore.WHITE}{reasoning}{Style.RESET_ALL}\n\n" + "-" * 80 + "\n")
    if analyst_signals:
        print(f"\n{Fore.WHITE}{Style.BRIGHT}ANALYST SIGNALS:{Style.RESET_ALL}\n")
        for agent_name, signals in analyst_signals.items():
            if agent_name == "risk_management_agent" or not isinstance(signals, dict):
                continue
            agent_display_name = agent_name.replace("_", " ").title()
            print(f"{Fore.CYAN}{Style.BRIGHT}{agent_display_name}:{Style.RESET_ALL}\n")
            signal_rows = []
            for ticker, signal_data in signals.items():
                if not isinstance(signal_data, dict):
                    continue
                is_interval_based = any(isinstance(v, dict) and ("signal" in v or "confidence" in v) for v in signal_data.values())
                if is_interval_based:
                    for interval, interval_data in signal_data.items():
                        if not isinstance(interval_data, dict):
                            continue
                        direction = interval_data.get("signal", "neutral")
                        confidence = interval_data.get("confidence", 0.0)
                        direction = "BULLISH" if direction == "bullish" else ("BEARISH" if direction == "bearish" else "NEUTRAL")
                        direction_color = {"BULLISH": Fore.GREEN, "BEARISH": Fore.RED, "NEUTRAL": Fore.YELLOW}.get(direction, Fore.WHITE)
                        conf_color = Fore.GREEN if confidence >= 70 else (Fore.YELLOW if confidence >= 40 else Fore.RED)
                        signal_display = f"{direction_color}{direction}{Style.RESET_ALL} {conf_color}({confidence:.0f}%){Style.RESET_ALL}"
                        signal_rows.append([f"{Fore.CYAN}{ticker}{Style.RESET_ALL}", f"{Fore.YELLOW}{interval.upper()}{Style.RESET_ALL}", signal_display])
                else:
                    direction = signal_data.get("signal", "neutral")
                    confidence = signal_data.get("confidence", 0.0)
                    direction = "BULLISH" if direction == "bullish" else ("BEARISH" if direction == "bearish" else "NEUTRAL")
                    direction_color = {"BULLISH": Fore.GREEN, "BEARISH": Fore.RED, "NEUTRAL": Fore.YELLOW}.get(direction, Fore.WHITE)
                    signal_rows.append([f"{Fore.CYAN}{ticker}{Style.RESET_ALL}", f"{Fore.YELLOW}ALL{Style.RESET_ALL}",
                                       f"{direction_color}{direction}{Style.RESET_ALL} ({confidence:.0f}%)"])
            if signal_rows:
                print(tabulate(signal_rows, headers=[f"{Fore.CYAN}Ticker{Style.RESET_ALL}", f"{Fore.YELLOW}Interval{Style.RESET_ALL}",
                    f"{Fore.WHITE}Signal & Details{Style.RESET_ALL}"], tablefmt="grid", colalign=("left", "center", "left")))
            else:
                print(f"{Fore.YELLOW}  No signals available for {agent_display_name}{Style.RESET_ALL}")
            print()
    print("\n" + "=" * 80 + "\n")
