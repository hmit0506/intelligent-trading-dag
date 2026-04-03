"""
Equity curve metrics for benchmark evaluation (all phases).
"""
from typing import Any, Dict

import numpy as np
import pandas as pd

from trading_dag.utils.constants import RISK_FREE_RATE_ANNUAL


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float safely."""
    try:
        if value is None:
            return default
        if isinstance(value, (float, int)):
            if np.isnan(value) or np.isinf(value):
                return default
            return float(value)
        parsed = float(value)
        if np.isnan(parsed) or np.isinf(parsed):
            return default
        return parsed
    except Exception:
        return default


def build_equity_metrics(equity_curve: pd.DataFrame) -> Dict[str, float]:
    """Calculate equity metrics from an equity curve."""
    if equity_curve.empty or len(equity_curve) < 2:
        return {
            "total_return_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "win_rate_pct": 0.0,
            "initial_portfolio_value": 0.0,
            "final_portfolio_value": 0.0,
        }

    values = equity_curve["portfolio_value"].astype(float)
    initial_value = float(values.iloc[0])
    final_value = float(values.iloc[-1])
    total_return_pct = ((final_value / initial_value) - 1.0) * 100 if initial_value > 0 else 0.0

    daily_returns = values.pct_change().dropna()
    daily_rf = RISK_FREE_RATE_ANNUAL / 365
    excess_returns = daily_returns - daily_rf
    std_excess = float(excess_returns.std()) if len(excess_returns) > 0 else 0.0
    mean_excess = float(excess_returns.mean()) if len(excess_returns) > 0 else 0.0

    if std_excess > 1e-12:
        sharpe = float(np.sqrt(365) * (mean_excess / std_excess))
    else:
        sharpe = 0.0

    downside = excess_returns[excess_returns < 0]
    downside_std = float(downside.std()) if len(downside) > 0 else 0.0
    if downside_std > 1e-12:
        sortino = float(np.sqrt(365) * (mean_excess / downside_std))
    else:
        sortino = float("inf") if mean_excess > 0 else 0.0

    rolling_max = values.cummax()
    drawdown = (values - rolling_max) / rolling_max
    max_drawdown_pct = float(drawdown.min() * 100) if len(drawdown) > 0 else 0.0

    wins = (daily_returns > 0).sum()
    total_days = max(len(daily_returns), 1)
    win_rate_pct = float((wins / total_days) * 100)

    return {
        "total_return_pct": total_return_pct,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown_pct": max_drawdown_pct,
        "win_rate_pct": win_rate_pct,
        "initial_portfolio_value": initial_value,
        "final_portfolio_value": final_value,
    }
