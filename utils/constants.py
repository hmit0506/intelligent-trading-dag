"""
Constants used throughout the trading system.
"""
import pandas as pd
from enum import Enum


# DataFrame columns for klines data
COLUMNS = [
    'open_time', 'open', 'high', 'low', 'close', 'volume',
    'close_time', 'quote_volume', 'count',
    'taker_buy_volume', 'taker_buy_quote_volume', 'ignore'
]

# Numeric columns that need type conversion
NUMERIC_COLUMNS = [
    'open', 'high', 'low', 'close', 'volume', 'quote_volume',
    'count', 'taker_buy_volume', 'taker_buy_quote_volume'
]

# Decimal places for quantity display
QUANTITY_DECIMALS = 3

# Risk-free rate (annual, as decimal) - typically US Treasury rate
# Default: 4.34% annual rate
RISK_FREE_RATE_ANNUAL = 0.0434


class Interval(Enum):
    """Time interval enumeration for market data."""
    MIN_1 = "1m"
    MIN_2 = "2m"
    MIN_3 = "3m"
    MIN_5 = "5m"
    MIN_10 = "10m"
    MIN_15 = "15m"
    MIN_30 = "30m"
    HOUR_1 = "1h"
    HOUR_2 = "2h"
    HOUR_4 = "4h"
    HOUR_6 = "6h"
    HOUR_8 = "8h"
    HOUR_12 = "12h"
    DAY_1 = "1d"
    DAY_3 = "3d"
    WEEK_1 = "1w"

    @staticmethod
    def from_string(value: str) -> "Interval":
        """Convert string to Interval enum."""
        try:
            return _STRING_TO_INTERVAL[value]
        except KeyError:
            raise ValueError(f"Invalid interval string: {value}")

    def to_timedelta(self) -> pd.Timedelta:
        """Convert interval to pandas Timedelta."""
        mapping = {
            Interval.MIN_1: pd.Timedelta(minutes=1),
            Interval.MIN_2: pd.Timedelta(minutes=2),
            Interval.MIN_3: pd.Timedelta(minutes=3),
            Interval.MIN_5: pd.Timedelta(minutes=5),
            Interval.MIN_10: pd.Timedelta(minutes=10),
            Interval.MIN_15: pd.Timedelta(minutes=15),
            Interval.MIN_30: pd.Timedelta(minutes=30),
            Interval.HOUR_1: pd.Timedelta(hours=1),
            Interval.HOUR_2: pd.Timedelta(hours=2),
            Interval.HOUR_4: pd.Timedelta(hours=4),
            Interval.HOUR_6: pd.Timedelta(hours=6),
            Interval.HOUR_8: pd.Timedelta(hours=8),
            Interval.HOUR_12: pd.Timedelta(hours=12),
            Interval.DAY_1: pd.Timedelta(days=1),
            Interval.DAY_3: pd.Timedelta(days=3),
            Interval.WEEK_1: pd.Timedelta(weeks=1),
        }
        return mapping[self]


# Build lookup map for fast string to Interval conversion
_STRING_TO_INTERVAL = {i.value: i for i in Interval}

