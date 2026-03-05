"""
Base strategy class.
"""
from typing import Dict, Any

from trading_dag.core.node import BaseNode
from trading_dag.core.state import AgentState


class BaseStrategy(BaseNode):
    """Base class for all trading strategies."""

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Process state and return updated state with strategy signals."""
        raise NotImplementedError("Subclasses must implement __call__")
