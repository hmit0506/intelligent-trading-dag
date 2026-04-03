"""
Experiment registry for phase 2 (DAG ablation) benchmark.
"""
from dataclasses import dataclass, replace
from typing import List, Optional

from trading_dag.benchmark.ablation import DAGAblationSettings

PHASE2_FULL_DAG_NAME = "FullDAG"


@dataclass(frozen=True)
class AblationDagSpec:
    """One ablation experiment (full DAG + ablation flags)."""

    name: str
    strategies: List[str]
    ablation: DAGAblationSettings


def get_phase2_ablation_registry(
    default_strategies: List[str],
    include_names: Optional[List[str]] = None,
) -> List[AblationDagSpec]:
    """
    Build phase 2 ablation registry (reference DAG + single-factor ablations).

    If ``include_names`` is empty or omitted, all variants run.
    If it is non-empty, list **only** ablation experiments (e.g. ``Ablate_MultiInterval``);
    the full-DAG reference is **always** prepended. Any ``FullDAG`` entry in the list is ignored.
    """
    base = DAGAblationSettings()
    all_specs = [
        AblationDagSpec(name=PHASE2_FULL_DAG_NAME, strategies=list(default_strategies), ablation=base),
        AblationDagSpec(
            name="Ablate_MultiInterval",
            strategies=list(default_strategies),
            ablation=replace(base, multi_interval=False),
        ),
        AblationDagSpec(
            name="Ablate_LLMPortfolio",
            strategies=list(default_strategies),
            ablation=replace(base, llm_portfolio=False),
        ),
        AblationDagSpec(
            name="Ablate_RiskSizing",
            strategies=list(default_strategies),
            ablation=replace(base, full_risk_sizing=False),
        ),
    ]
    if not include_names:
        return all_specs
    include_set = {name.strip() for name in include_names if str(name).strip()}
    include_set.discard(PHASE2_FULL_DAG_NAME)
    filtered = [spec for spec in all_specs if spec.name in include_set]
    full_spec = next(s for s in all_specs if s.name == PHASE2_FULL_DAG_NAME)
    return [full_spec] + filtered
