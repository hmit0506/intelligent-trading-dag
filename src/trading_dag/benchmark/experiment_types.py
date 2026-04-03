"""
Shared result types for benchmark suites (phase 1, phase 2, and future phases).
"""
from dataclasses import dataclass

import pandas as pd


@dataclass
class ExperimentResult:
    """Container for one benchmark experiment output."""

    name: str
    category: str
    total_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    final_portfolio_value: float
    initial_portfolio_value: float
    num_points: int
    equity_curve: pd.DataFrame
