"""
Base node class for all workflow nodes.
"""
from typing import Dict, Any
from .state import AgentState


class BaseNode:
    """Base class for all workflow nodes."""
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Process the state and return updated state.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state dictionary
        """
        raise NotImplementedError("Subclasses must implement __call__")

