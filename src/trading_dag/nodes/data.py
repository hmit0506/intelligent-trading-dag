"""
Data node - fetches market data for specified timeframes.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pandas as pd

from trading_dag.core.node import BaseNode
from trading_dag.core.state import AgentState
from trading_dag.utils.constants import Interval
from trading_dag.data.provider import BinanceDataProvider

data_provider = BinanceDataProvider()


class DataNode(BaseNode):
    """Fetches market data for a specific timeframe."""

    def __init__(self, interval: Interval = Interval.DAY_1):
        """Initialize data node with a specific interval."""
        self.interval = interval

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Fetch data for all required tickers using prefetched data in backtest mode,
        or BinanceDataProvider in live trading mode.
        """
        data = state.get('data', {})
        data['name'] = "DataNode"
        timeframe: str = self.interval.value
        tickers = data.get('tickers', [])
        end_time = data.get('end_date', datetime.now()) + timedelta(milliseconds=500)

        prefetched_data = data.get('prefetched_data', {})

        for ticker in tickers:
            cache_key = f"{ticker}_{timeframe}"
            df: Optional[pd.DataFrame] = None

            if cache_key in prefetched_data:
                prefetched_df = prefetched_data[cache_key]
                if prefetched_df is not None and not prefetched_df.empty:
                    filtered_df = prefetched_df[prefetched_df['open_time'] <= end_time].copy()
                    if not filtered_df.empty:
                        df = filtered_df
                    else:
                        before_end_time = prefetched_df[prefetched_df['open_time'] < end_time]
                        if not before_end_time.empty:
                            df = before_end_time.tail(1).copy()
                        else:
                            df = prefetched_df.head(1).copy()

            if df is None or df.empty:
                df = data_provider.get_history_klines_with_end_time(
                    symbol=ticker,
                    timeframe=timeframe,
                    end_time=end_time
                )

            if df is not None and not df.empty:
                data[f"{ticker}_{timeframe}"] = df
            else:
                print(f"[Warning] No data returned for {ticker} at interval {timeframe}")

        return state
