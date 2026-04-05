"""
Export backtest trade log (JSON) and portfolio series (CSV), matching ``TradingSystemRunner`` output.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple


def _slugify_label(name: str) -> str:
    s = re.sub(r"[^\w\-.]+", "_", (name or "").strip())
    s = s.strip("_") or "run"
    return s[:200]


def slugify_experiment_label(name: str) -> str:
    """Safe filename segment shared by portfolio PNG, trades JSON, and performance CSV."""
    return _slugify_label(name)


def export_backtest_trades_and_performance(
    backtester: Any,
    output_dir: Path,
    *,
    experiment_label: str = "",
) -> Tuple[Path, Optional[Path]]:
    """
    Write ``backtest_trades_*.json`` (``trade_log``) and optional ``backtest_performance_*.csv``.

    Same structure as standalone backtest: JSON is ``json.dump(..., indent=2, default=str)``;
    CSV is ``DataFrame(portfolio_values).to_csv`` when values exist.

    When *experiment_label* is empty, filenames match the legacy runner:
    ``backtest_trades_{timestamp}.json``, ``backtest_performance_{timestamp}.csv``.
    When set (e.g. benchmark variant name), insert before the timestamp so runs do not overwrite.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if experiment_label.strip():
        slug = slugify_experiment_label(experiment_label)
        json_path = output_dir / f"backtest_trades_{slug}_{ts}.json"
        csv_stem = f"backtest_performance_{slug}_{ts}.csv"
    else:
        json_path = output_dir / f"backtest_trades_{ts}.json"
        csv_stem = f"backtest_performance_{ts}.csv"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(backtester.trade_log, f, indent=2, default=str)

    csv_path: Optional[Path] = None
    if hasattr(backtester, "portfolio_values") and backtester.portfolio_values:
        import pandas as pd

        df = pd.DataFrame(backtester.portfolio_values)
        csv_path = output_dir / csv_stem
        df.to_csv(csv_path, index=False)

    return json_path, csv_path
