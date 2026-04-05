"""
Experiment registry for phase 1 benchmark.
"""
from dataclasses import dataclass
from typing import List, Optional

# Reference run always prepended when using a selective list (see get_phase1_dag_registry).
PHASE1_FULL_DAG_NAME = "FullDAG"


@dataclass(frozen=True)
class DagExperimentSpec:
    """Definition of one DAG-based experiment."""

    name: str
    strategies: List[str]


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
