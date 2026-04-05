"""
Binance Data Provider - handles data retrieval from Binance.
"""
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path

from trading_dag.gateway.binance.client import Client
from trading_dag.utils.constants import COLUMNS, NUMERIC_COLUMNS
from trading_dag.utils.exchange_time import exchange_timestamp_ms, naive_in_zone_to_utc_naive


class BinanceDataProvider:
    """Handles data retrieval from Binance and prepares it for the trading system."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        *,
        naive_timezone: str = "UTC",
    ):
        """
        Initialize the BinanceDataProvider.

        Args:
            api_key: Binance API key (optional for public data)
            api_secret: Binance API secret (optional for public data)
            naive_timezone: IANA timezone name for interpreting naive ``datetime`` arguments
                (must match backtest ``start_date`` / ``end_date`` semantics). Examples: ``UTC``,
                ``Asia/Hong_Kong``.
        """
        self.client = Client(api_key=api_key, api_secret=api_secret)
        self.cache_dir = Path("./cache")
        self.cache_dir.mkdir(exist_ok=True)
        self._naive_timezone = naive_timezone

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
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now(timezone.utc)

        cache_file = self.cache_dir / f"{formatted_symbol}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"

        start_utc_naive = naive_in_zone_to_utc_naive(start_date, self._naive_timezone)
        end_utc_naive = naive_in_zone_to_utc_naive(end_date, self._naive_timezone)

        if use_cache and cache_file.exists():
            print(f"Loading cached data for {formatted_symbol} {timeframe}")
            cached_df = pd.read_csv(cache_file, parse_dates=['open_time', 'close_time'])
            return cached_df[
                (cached_df['open_time'] >= start_utc_naive) &
                (cached_df['open_time'] <= end_utc_naive)
            ].reset_index(drop=True)

        print(f"Fetching historical data from Binance API for {formatted_symbol} {timeframe}")

        start_ts = exchange_timestamp_ms(start_date, self._naive_timezone)
        end_ts = exchange_timestamp_ms(end_date, self._naive_timezone)

        try:
            klines = self.client.get_historical_klines(
                symbol=formatted_symbol,
                interval=self._format_timeframe(timeframe),
                start_str=start_ts,
                end_str=end_ts
            )

            if not klines:
                print(f"Warning: No klines returned for {formatted_symbol} {timeframe}")
                return pd.DataFrame()

            df = pd.DataFrame(klines, columns=COLUMNS)
            for col in NUMERIC_COLUMNS:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            df = df.dropna(subset=['open_time', 'close_time', 'close', 'open', 'high', 'low']).reset_index(drop=True)
            df = df[(df['open_time'] >= start_utc_naive) & (df['open_time'] <= end_utc_naive)].reset_index(drop=True)

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
        """Get historical klines with end time. Always fetches fresh data from API."""
        formatted_symbol = symbol.replace("/", "")

        try:
            from trading_dag.utils.constants import Interval
            try:
                interval_delta = Interval.from_string(timeframe).to_timedelta()
            except Exception:
                interval_delta = pd.Timedelta(hours=1)

            start_time = end_time - (interval_delta * limit)
            start_ts = exchange_timestamp_ms(start_time, self._naive_timezone)
            end_ts = exchange_timestamp_ms(end_time, self._naive_timezone)

            klines = self.client.get_historical_klines(
                symbol=formatted_symbol,
                interval=self._format_timeframe(timeframe),
                start_str=start_ts,
                end_str=end_ts,
                limit=limit
            )

            if not klines:
                return pd.DataFrame()

            df = pd.DataFrame(klines, columns=COLUMNS)
            for col in NUMERIC_COLUMNS:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            df = df.dropna(subset=['open_time', 'close_time', 'close', 'open', 'high', 'low']).reset_index(drop=True)
            end_utc_naive = naive_in_zone_to_utc_naive(end_time, self._naive_timezone)
            df = df[df['open_time'] <= end_utc_naive].reset_index(drop=True)

            return df

        except Exception as e:
            print(f"Error fetching data for {formatted_symbol} {timeframe} at {end_time}: {e}")
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
