"""
Starting portfolio value for benchmark baselines (buy-and-hold, equal-weight).

Must match the DAG backtest notion of initial NAV when ``initial_positions`` include
holdings: baselines should not use cash-only while FullDAG uses cash + positions.
"""
from __future__ import annotations

from typing import Any, Dict


def benchmark_starting_portfolio_value_usd(
    config: Any,
    first_bar_close_by_ticker: Dict[str, float],
) -> float:
    """
    Total starting NAV in quote currency (USD) for passive baselines.

    - Starts from ``config.initial_cash`` (same merged cash as Backtester).
    - Adds long position value at first-bar close (aligned with klines used by baselines).
    Ignores shorts for this helper (rare in benchmark configs); extend if needed.
    """
    total = float(config.initial_cash)
    ip = getattr(config, "initial_positions", None)
    if not isinstance(ip, dict):
        return total
    positions = ip.get("positions")
    if not isinstance(positions, dict):
        return total
    for ticker, pdata in positions.items():
        if not isinstance(pdata, dict):
            continue
        px = float(first_bar_close_by_ticker.get(ticker, 0.0))
        if px <= 0.0:
            continue
        long_q = float(pdata.get("long", 0.0))
        if long_q > 0.0:
            total += long_q * px
    return total
