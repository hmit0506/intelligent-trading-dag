"""
Compatibility shim: use ``trading_dag.benchmark.baseline_simulators`` for new imports.
"""
from trading_dag.benchmark.baseline_simulators import (
    ensure_same_length,
    prepare_primary_klines,
    simulate_buy_and_hold,
    simulate_equal_weight_rebalance,
)

__all__ = [
    "ensure_same_length",
    "prepare_primary_klines",
    "simulate_buy_and_hold",
    "simulate_equal_weight_rebalance",
]
