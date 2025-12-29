"""
RSI Strategy.
"""
from typing import Dict, Any
from core.node import BaseNode
from core.state import AgentState


class RSIStrategy(BaseNode):
    """RSI-based trading strategy."""
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Generate RSI-based trading signals."""
        data = state['data']
        data['name'] = "RSIStrategy"
        return state
