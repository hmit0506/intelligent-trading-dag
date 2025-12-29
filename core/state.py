"""
Agent state definition for LangGraph workflow.
"""
from typing import List, Dict, TypedDict, Annotated, Any
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
import json


def deep_merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = a.copy()
    for key, value in b.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


class AgentState(TypedDict):
    """State structure for the trading agent workflow."""
    messages: Annotated[List[BaseMessage], add_messages]
    data: Annotated[Dict[str, Any], deep_merge_dicts]
    metadata: Annotated[Dict[str, Any], deep_merge_dicts]


def show_agent_reasoning(output: Any, agent_name: str) -> None:
    """Print agent reasoning output in a formatted way."""
    print(f"\n{'=' * 10} {agent_name.center(28)} {'=' * 10}")

    def convert_to_serializable(obj: Any) -> Any:
        """Convert object to JSON-serializable format."""
        if hasattr(obj, "to_dict"):  # Pandas Series/DataFrame
            return obj.to_dict()
        elif hasattr(obj, "__dict__"):  # Custom objects
            return obj.__dict__
        elif isinstance(obj, (int, float, bool, str)):
            return obj
        elif isinstance(obj, (list, tuple)):
            return [convert_to_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: convert_to_serializable(value) for key, value in obj.items()}
        else:
            return str(obj)

    if isinstance(output, (dict, list)):
        serializable_output = convert_to_serializable(output)
        print(json.dumps(serializable_output, indent=2))
    else:
        try:
            parsed_output = json.loads(output)
            print(json.dumps(parsed_output, indent=2))
        except json.JSONDecodeError:
            print(output)

    print("=" * 48)

