"""
Data node - fetches market data for specified timeframes.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import os
import sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.node import BaseNode
from core.state import AgentState
from utils.constants import Interval
from data.provider import BinanceDataProvider

# Initialize data provider
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
        
        Args:
            state: The current state with ticker information
            
        Returns:
            Updated state with market data
        """
        data = state.get('data', {})
        data['name'] = "DataNode"
        timeframe: str = self.interval.value
        tickers = data.get('tickers', [])
        end_time = data.get('end_date', datetime.now()) + timedelta(milliseconds=500)
        
        # Check if prefetched data is available (backtest mode)
        prefetched_data = data.get('prefetched_data', {})

        for ticker in tickers:
            cache_key = f"{ticker}_{timeframe}"
            df: Optional[pd.DataFrame] = None
            
            # Try to use prefetched data first (backtest mode)
            if cache_key in prefetched_data:
                prefetched_df = prefetched_data[cache_key]
                if prefetched_df is not None and not prefetched_df.empty:
                    # Filter data to only include rows up to end_time
                    filtered_df = prefetched_df[prefetched_df['open_time'] <= end_time].copy()
                    
                    if not filtered_df.empty:
                        # Use filtered data
                        df = filtered_df
                    else:
                        # If no data before end_time, get the most recent data point before end_time
                        # This handles cases where end_time is before the first data point
                        before_end_time = prefetched_df[prefetched_df['open_time'] < end_time]
                        if not before_end_time.empty:
                            # Take the last available data point before end_time
                            df = before_end_time.tail(1).copy()
                        else:
                            # If still empty, take the first available data point as fallback
                            df = prefetched_df.head(1).copy()
            
            # Fallback to network request if no prefetched data (live trading mode)
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

