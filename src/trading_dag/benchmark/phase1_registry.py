"""
Experiment registry for phase 1 benchmark.
"""
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import pandas as pd

from trading_dag.benchmark.phase1_baselines import (
    simulate_buy_and_hold,
    simulate_equal_weight_rebalance,
)


@dataclass(frozen=True)
class DagExperimentSpec:
    """Definition of one DAG-based experiment."""

    name: str
    strategies: List[str]


@dataclass(frozen=True)
class BaselineExperimentSpec:
    """Definition of one baseline experiment."""

    name: str
    simulator: Callable[..., pd.DataFrame]
    kwargs: Dict[str, object]


def get_phase1_dag_registry(default_strategies: List[str]) -> List[DagExperimentSpec]:
    """Build DAG experiment registry for phase 1."""
    return [
        DagExperimentSpec(name="FullDAG", strategies=default_strategies),
        DagExperimentSpec(name="SingleMACD", strategies=["MacdStrategy"]),
        DagExperimentSpec(name="SingleRSI", strategies=["RSIStrategy"]),
        DagExperimentSpec(name="SingleBollinger", strategies=["BollingerStrategy"]),
    ]


def get_phase1_baseline_registry(
    run_buy_and_hold: bool,
    run_equal_weight_rebalance: bool,
    rebalance_every_bars: int,
) -> List[BaselineExperimentSpec]:
    """Build baseline experiment registry for phase 1."""
    baselines: List[BaselineExperimentSpec] = []
    if run_buy_and_hold:
        baselines.append(
            BaselineExperimentSpec(
                name="BuyAndHold",
                simulator=simulate_buy_and_hold,
                kwargs={},
            )
        )
    if run_equal_weight_rebalance:
        baselines.append(
            BaselineExperimentSpec(
                name="EqualWeightRebalance",
                simulator=simulate_equal_weight_rebalance,
                kwargs={"rebalance_every_bars": rebalance_every_bars},
            )
        )
    return baselines

