"""
Merge node - merges data from multiple timeframe nodes.
"""
from typing import Dict, Any
from trading_dag.core.node import BaseNode
from trading_dag.core.state import AgentState


class MergeNode(BaseNode):
    """Merge node that combines data from multiple timeframe nodes."""

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Merge data from multiple timeframe nodes."""
        return state
