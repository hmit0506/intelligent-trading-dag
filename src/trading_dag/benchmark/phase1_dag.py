"""
DAG-backed experiment runners for phase 1 benchmark.
"""
from typing import Any, List, Tuple

import pandas as pd

from trading_dag.backtest.engine import Backtester
from trading_dag.benchmark.phase1_metrics import build_equity_metrics, safe_float
from trading_dag.benchmark.phase1_models import ExperimentResult


def run_dag_variant(
    variant_name: str,
    strategy_list: List[str],
    config: Any,
) -> Tuple[ExperimentResult, pd.DataFrame]:
    """Run one DAG-based experiment via existing backtester."""
    backtester = Backtester(
        primary_interval=config.primary_interval,
        intervals=config.signals.intervals,
        tickers=config.signals.tickers,
        start_date=config.start_date,
        end_date=config.end_date,
        initial_capital=config.initial_cash,
        strategies=strategy_list,
        model_name=config.model.name,
        model_provider=config.model.provider,
        model_base_url=config.model.base_url,
        initial_margin_requirement=config.margin_requirement,
        show_agent_graph=False,
        show_reasoning=False,
        print_frequency=max(getattr(config, "print_frequency", 1), 1),
        use_progress_bar=False,
        log_file=None,
        initial_positions=getattr(config, "initial_positions", None),
    )
    backtester.run_backtest()

    portfolio_values = pd.DataFrame(backtester.portfolio_values)
    if portfolio_values.empty:
        raise ValueError(f"Backtester produced empty portfolio values for variant {variant_name}")

    equity_curve = portfolio_values.rename(
        columns={"Date": "date", "Portfolio Value": "portfolio_value"}
    )[["date", "portfolio_value"]]
    metrics = build_equity_metrics(equity_curve)

    result = ExperimentResult(
        name=variant_name,
        category="dag",
        total_return_pct=safe_float(metrics["total_return_pct"]),
        sharpe_ratio=safe_float(metrics["sharpe_ratio"]),
        sortino_ratio=safe_float(metrics["sortino_ratio"]),
        max_drawdown_pct=safe_float(metrics["max_drawdown_pct"]),
        win_rate_pct=safe_float(metrics["win_rate_pct"]),
        final_portfolio_value=safe_float(metrics["final_portfolio_value"]),
        initial_portfolio_value=safe_float(metrics["initial_portfolio_value"]),
        num_points=len(equity_curve),
        equity_curve=equity_curve,
    )
    return result, equity_curve

