"""
Data node - fetches market data for specified timeframes.
"""
from datetime import datetime, timedelta
from typing import Dict, Any
import os
import sys
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
        Fetch data for all required tickers using the BinanceDataProvider.
        
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

        for ticker in tickers:
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

