"""
Shared data models for phase 1 benchmark.
"""
from dataclasses import dataclass

import pandas as pd


@dataclass
class ExperimentResult:
    """Container for one experiment output."""

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

