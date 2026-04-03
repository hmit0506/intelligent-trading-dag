"""
Benchmark utilities for controlled experiment suites (phase 1 and phase 2).
"""

from trading_dag.benchmark.phase1 import run_phase1_benchmarks
from trading_dag.benchmark.phase2 import run_phase2_benchmarks

__all__ = ["run_phase1_benchmarks", "run_phase2_benchmarks"]
