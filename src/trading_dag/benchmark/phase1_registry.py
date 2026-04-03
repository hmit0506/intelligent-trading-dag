"""
Experiment registry for phase 1 benchmark.
"""
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import pandas as pd

from trading_dag.benchmark.baseline_simulators import (
    simulate_buy_and_hold,
    simulate_equal_weight_rebalance,
)

# Reference run always prepended when using a selective list (see get_phase1_dag_registry).
PHASE1_FULL_DAG_NAME = "FullDAG"


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
    """
    Build DAG experiment registry for phase 1.

    If ``include_names`` is empty or omitted, all DAG variants run (reference plus singles).
    If it is non-empty, list **only** the comparison experiments to run (e.g. ``SingleMACD``);
    the full-DAG reference is **always** prepended automatically. Any ``FullDAG`` entry in the
    list is ignored so the config never needs to name it.
    """
    all_specs = [
        DagExperimentSpec(name=PHASE1_FULL_DAG_NAME, strategies=default_strategies),
        DagExperimentSpec(name="SingleMACD", strategies=["MacdStrategy"]),
        DagExperimentSpec(name="SingleRSI", strategies=["RSIStrategy"]),
        DagExperimentSpec(name="SingleBollinger", strategies=["BollingerStrategy"]),
    ]
    if not include_names:
        return all_specs
    include_set = {name.strip() for name in include_names if str(name).strip()}
    include_set.discard(PHASE1_FULL_DAG_NAME)
    filtered = [spec for spec in all_specs if spec.name in include_set]
    full_spec = next(s for s in all_specs if s.name == PHASE1_FULL_DAG_NAME)
    return [full_spec] + filtered


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
