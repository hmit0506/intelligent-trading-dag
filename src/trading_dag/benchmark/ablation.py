"""
DAG ablation settings for benchmark phase 2.

Each flag disables one subsystem while keeping the rest of the pipeline intact.
"""
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class DAGAblationSettings:
    """
    Ablation toggles (defaults = full pipeline, no ablation).

    - multi_interval: if False, workflows only load/analyze primary_interval
      (multi-timeframe branches are not run).
    - llm_portfolio: if False, portfolio decisions use deterministic rules
      from primary-interval signals instead of the LLM.
    - full_risk_sizing: if False, risk uses a simple fixed fraction of portfolio
      per ticker without stop-loss gating.
    """

    multi_interval: bool = True
    llm_portfolio: bool = True
    full_risk_sizing: bool = True

    def workflow_metadata(self) -> Dict[str, Any]:
        """Merged into AgentState metadata for node behavior."""
        return {
            "use_llm_portfolio": self.llm_portfolio,
            "ablation_full_risk": self.full_risk_sizing,
        }
