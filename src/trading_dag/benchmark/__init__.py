"""
Benchmark package (phase1/phase2 suites).

Eager imports are avoided here so ``trading_dag.backtest.engine`` can load without a
circular import (engine → ablation → package __init__ → phase1 → dag_backtest_runner → engine).
"""

from __future__ import annotations

from typing import Any

__all__ = ["run_phase1_benchmarks", "run_phase2_benchmarks"]


def __getattr__(name: str) -> Any:
    if name == "run_phase1_benchmarks":
        from trading_dag.benchmark.phase1 import run_phase1_benchmarks

        return run_phase1_benchmarks
    if name == "run_phase2_benchmarks":
        from trading_dag.benchmark.phase2 import run_phase2_benchmarks

        return run_phase2_benchmarks
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
