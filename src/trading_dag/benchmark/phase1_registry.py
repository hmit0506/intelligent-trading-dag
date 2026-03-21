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


def get_phase1_dag_registry(
    default_strategies: List[str],
    include_names: Optional[List[str]] = None,
) -> List[DagExperimentSpec]:
    """Build DAG experiment registry for phase 1."""
    all_specs = [
        DagExperimentSpec(name="FullDAG", strategies=default_strategies),
        DagExperimentSpec(name="SingleMACD", strategies=["MacdStrategy"]),
        DagExperimentSpec(name="SingleRSI", strategies=["RSIStrategy"]),
        DagExperimentSpec(name="SingleBollinger", strategies=["BollingerStrategy"]),
    ]
    if not include_names:
        return all_specs
    include_set = {name.strip() for name in include_names if str(name).strip()}
    return [spec for spec in all_specs if spec.name in include_set]


def get_phase1_baseline_registry(
    run_buy_and_hold: bool,
    run_equal_weight_rebalance: bool,
    rebalance_every_bars: int,
    include_names: Optional[List[str]] = None,
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
    if not include_names:
        return baselines
    include_set = {name.strip() for name in include_names if str(name).strip()}
    return [spec for spec in baselines if spec.name in include_set]

