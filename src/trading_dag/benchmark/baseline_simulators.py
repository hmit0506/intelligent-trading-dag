"""
Non-DAG baseline simulations (buy-and-hold and periodic equal weight).

Used by phase 1 and optionally phase 2 for interpretable passive benchmarks.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd

from trading_dag.data.provider import BinanceDataProvider
from trading_dag.utils.constants import Interval
from trading_dag.utils.exchange_time import naive_in_zone_to_utc_naive


def prepare_primary_klines(
    tickers: List[str],
    primary_interval: Interval,
    start_date: datetime,
    end_date: datetime,
    naive_timezone: str = "UTC",
) -> Dict[str, pd.DataFrame]:
    """Fetch primary interval data for baseline simulations."""
    provider = BinanceDataProvider(naive_timezone=naive_timezone)
    date_range = end_date - start_date
    end_date_inclusive = end_date + timedelta(days=1) - timedelta(seconds=1)
    required_k_lines = int(date_range / primary_interval.to_timedelta()) + 1
    k_lines_to_fetch = max(500, required_k_lines)

    klines: Dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        data = provider.get_history_klines_with_end_time(
            symbol=ticker,
            timeframe=primary_interval.value,
            end_time=end_date_inclusive,
            limit=k_lines_to_fetch,
        )
        if data is None or data.empty:
            raise ValueError(f"No historical data for {ticker} at interval {primary_interval.value}")

        start_utc_naive = naive_in_zone_to_utc_naive(start_date, naive_timezone)
        end_utc_naive = naive_in_zone_to_utc_naive(end_date, naive_timezone)
        filtered = data[
            (data["open_time"] >= start_utc_naive) & (data["open_time"] <= end_utc_naive)
        ].reset_index(drop=True)

        if filtered.empty:
            raise ValueError(
                f"Historical data for {ticker} does not contain points in {start_date} - {end_date}"
            )
        klines[ticker] = filtered
    return klines


def ensure_same_length(klines: Dict[str, pd.DataFrame]) -> int:
    """Validate all ticker dataframes have equal length."""
    lengths = {ticker: len(df) for ticker, df in klines.items()}
    if len(set(lengths.values())) != 1:
        raise ValueError(f"Mismatched kline lengths across tickers: {lengths}")
    return next(iter(lengths.values()))


def simulate_buy_and_hold(
    tickers: List[str],
    klines: Dict[str, pd.DataFrame],
    initial_cash: float,
) -> pd.DataFrame:
    """Simulate equal-weight buy and hold baseline."""
    n = ensure_same_length(klines)
    if n < 1:
        return pd.DataFrame(columns=["date", "portfolio_value"])

    weights = {ticker: 1.0 / len(tickers) for ticker in tickers}
    first_prices = {ticker: float(klines[ticker].iloc[0]["close"]) for ticker in tickers}
    holdings = {
        ticker: (initial_cash * weights[ticker]) / first_prices[ticker]
        for ticker in tickers
    }

    rows: List[Dict[str, Any]] = []
    for idx in range(n):
        row_date = klines[tickers[0]].iloc[idx]["open_time"]
        value = 0.0
        for ticker in tickers:
            price = float(klines[ticker].iloc[idx]["close"])
            value += holdings[ticker] * price
        rows.append({"date": row_date, "portfolio_value": value})

    return pd.DataFrame(rows)


def simulate_equal_weight_rebalance(
    tickers: List[str],
    klines: Dict[str, pd.DataFrame],
    initial_cash: float,
    rebalance_every_bars: int,
) -> pd.DataFrame:
    """Simulate equal-weight periodic rebalance baseline (zero transaction costs)."""
    n = ensure_same_length(klines)
    if n < 1:
        return pd.DataFrame(columns=["date", "portfolio_value"])
    if rebalance_every_bars < 1:
        raise ValueError("rebalance_every_bars must be >= 1")

    weights = {ticker: 1.0 / len(tickers) for ticker in tickers}
    first_prices = {ticker: float(klines[ticker].iloc[0]["close"]) for ticker in tickers}
    holdings = {
        ticker: (initial_cash * weights[ticker]) / first_prices[ticker]
        for ticker in tickers
    }

    rows: List[Dict[str, Any]] = []
    for idx in range(n):
        prices = {ticker: float(klines[ticker].iloc[idx]["close"]) for ticker in tickers}
        total_value = sum(holdings[ticker] * prices[ticker] for ticker in tickers)
        row_date = klines[tickers[0]].iloc[idx]["open_time"]
        rows.append({"date": row_date, "portfolio_value": total_value})

        if idx > 0 and idx % rebalance_every_bars == 0:
            for ticker in tickers:
                target_value = total_value * weights[ticker]
                holdings[ticker] = target_value / prices[ticker]

    return pd.DataFrame(rows)
