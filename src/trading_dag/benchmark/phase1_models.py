"""
Compatibility shim: use ``trading_dag.benchmark.experiment_types`` for new imports.
"""
from trading_dag.benchmark.experiment_types import ExperimentResult

__all__ = ["ExperimentResult"]
