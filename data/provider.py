"""
Binance Data Provider - handles data retrieval from Binance.
"""
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Import from local gateway module
from gateway.binance.client import Client
from utils.constants import COLUMNS, NUMERIC_COLUMNS


class BinanceDataProvider:
    """Handles data retrieval from Binance and prepares it for the trading system."""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize the BinanceDataProvider with API credentials.
        
        Args:
            api_key: Binance API key (optional for public data)
            api_secret: Binance API secret (optional for public data)
        """
        self.client = Client(api_key=api_key, api_secret=api_secret)
        self.cache_dir = Path("./cache")
        self.cache_dir.mkdir(exist_ok=True)

    def _format_timeframe(self, timeframe: str) -> str:
        """Convert timeframe format to Binance's format."""
        return timeframe

    def get_historical_klines(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """Get historical klines (candlestick data) for a symbol and timeframe."""
        formatted_symbol = symbol.replace("/", "")

        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()

        cache_file = self.cache_dir / f"{formatted_symbol}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"

        if use_cache and cache_file.exists():
            print(f"Loading cached data for {formatted_symbol} {timeframe}")
            return pd.read_csv(cache_file, parse_dates=['open_time', 'close_time'])

        print(f"Fetching historical data for {formatted_symbol} {timeframe}")

        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)

        try:
            klines = self.client.get_historical_klines(
                symbol=formatted_symbol,
                interval=self._format_timeframe(timeframe),
                start_str=start_ts,
                end_str=end_ts
            )

            df = pd.DataFrame(klines, columns=COLUMNS)
            for col in NUMERIC_COLUMNS:
                df[col] = pd.to_numeric(df[col])

            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')

            if use_cache:
                df.to_csv(cache_file, index=False)

            return df

        except Exception as e:
            print(f"Error fetching historical data for {formatted_symbol} {timeframe}: {e}")
            return pd.DataFrame()

    def get_history_klines_with_end_time(
        self,
        symbol: str,
        timeframe: str,
        end_time: datetime,
        limit: int = 500,
    ) -> pd.DataFrame:
        """Get historical klines with end time."""
        formatted_symbol = symbol.replace("/", "")
        try:
            klines = self.client.futures_historical_klines_with_end_time(
                symbol=formatted_symbol,
                interval=self._format_timeframe(timeframe),
                end_str=end_time.strftime("%Y-%m-%d %H:%M:%S"),
                limit=limit
            )

            df = pd.DataFrame(klines, columns=COLUMNS)

            for col in NUMERIC_COLUMNS:
                df[col] = pd.to_numeric(df[col])

            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')

            return df

        except Exception as e:
            print(f"Error fetching latest data for {formatted_symbol} {timeframe}: {e}")
            return pd.DataFrame()

    def get_latest_data(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        """Get the latest candlestick data for a symbol and timeframe."""
        formatted_symbol = symbol.replace("/", "")

        try:
            klines = self.client.get_klines(
                symbol=formatted_symbol,
                interval=self._format_timeframe(timeframe),
                limit=limit
            )

            df = pd.DataFrame(klines, columns=COLUMNS)

            for col in NUMERIC_COLUMNS:
                df[col] = pd.to_numeric(df[col])

            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')

            return df

        except Exception as e:
            print(f"Error fetching latest data for {formatted_symbol} {timeframe}: {e}")
            return pd.DataFrame()

