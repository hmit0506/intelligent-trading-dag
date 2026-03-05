"""
Start node - initializes the workflow.
"""
from typing import Dict, Any
from trading_dag.core.node import BaseNode
from trading_dag.core.state import AgentState


class StartNode(BaseNode):
    """Start node that initializes the workflow."""

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Initialize the workflow state."""
        data = state['data']
        data['name'] = "StartNode"
        return state
