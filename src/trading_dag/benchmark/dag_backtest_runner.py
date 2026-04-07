"""
Single-experiment DAG backtest for benchmark suites.

Runs Backtester + Agent with optional ablation settings; shared by phase 1 (full
pipeline) and phase 2 (controlled subsystem toggles).
"""
from pathlib import Path
from typing import Any, List, Optional, Tuple

import pandas as pd

from trading_dag.backtest.engine import Backtester
from trading_dag.utils.backtest_export import export_backtest_trades_and_performance
from trading_dag.utils.output_layout import resolve_output_dirs
from trading_dag.benchmark.ablation import DAGAblationSettings
from trading_dag.benchmark.equity_metrics import build_equity_metrics, safe_float
from trading_dag.benchmark.experiment_types import ExperimentResult


def run_dag_backtest_experiment(
    variant_name: str,
    strategy_list: List[str],
    config: Any,
    print_frequency: int,
    use_progress_bar: bool,
    *,
    ablation: Optional[DAGAblationSettings] = None,
    category: str = "dag",
) -> Tuple[ExperimentResult, pd.DataFrame]:
    """
    Run one DAG-based benchmark experiment via the production Backtester.

    Args:
        variant_name: Label for logs and result rows.
        strategy_list: Strategy class names wired into the workflow.
        config: Loaded Config (backtest mode).
        print_frequency: Backtester console table frequency.
        use_progress_bar: tqdm vs table-style progress.
        ablation: Optional DAG ablation toggles (phase 2); None = full pipeline (phase 1).
        category: Result category string (e.g. \"dag\", \"ablation\").
    """
    bench_dir = resolve_output_dirs(Path.cwd(), config.output_layout).benchmark

    _mt = config.model.temperature
    _model_temp = 0.0 if _mt is None else float(_mt)
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
        model_temperature=_model_temp,
        initial_margin_requirement=config.margin_requirement,
        show_agent_graph=False,
        show_reasoning=bool(getattr(config, "show_reasoning", False)),
        print_frequency=max(print_frequency, 1),
        use_progress_bar=use_progress_bar,
        log_file=None,
        initial_positions=getattr(config, "initial_positions", None),
        ablation=ablation,
        risk_management=config.risk,
        export_output_dir=bench_dir,
        experiment_label=variant_name,
        naive_date_timezone=getattr(config, "timezone", "UTC"),
    )
    backtester.run_backtest()
    backtester.analyze_performance()

    export_backtest_trades_and_performance(
        backtester,
        bench_dir,
        experiment_label=variant_name,
    )

    portfolio_values = pd.DataFrame(backtester.portfolio_values)
    if portfolio_values.empty:
        raise ValueError(f"Backtester produced empty portfolio values for variant {variant_name}")

    equity_curve = portfolio_values.rename(
        columns={"Date": "date", "Portfolio Value": "portfolio_value"}
    )[["date", "portfolio_value"]]
    metrics = build_equity_metrics(equity_curve)

    result = ExperimentResult(
        name=variant_name,
        category=category,
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
