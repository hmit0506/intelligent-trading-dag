"""
Compatibility shim: use ``trading_dag.benchmark.equity_metrics`` for new imports.
"""
from trading_dag.benchmark.equity_metrics import build_equity_metrics, safe_float

__all__ = ["build_equity_metrics", "safe_float"]
