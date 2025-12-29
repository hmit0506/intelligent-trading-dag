"""
Trading Agent - main agent class that orchestrates the workflow.
"""
import os
import sys
from typing import List, Dict, Optional, Any
from langchain_core.messages import HumanMessage
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.workflow import Workflow
from utils.constants import Interval
from utils.helpers import save_graph_as_png, parse_str_to_json


class Agent:
    """Main trading agent that orchestrates the DAG workflow."""
    
    def __init__(self, intervals: List[Interval], strategies: List[str], show_agent_graph: bool = True):
        """
        Initialize the agent with workflow configuration.
        
        Args:
            intervals: List of time intervals to analyze
            strategies: List of strategy names to use
            show_agent_graph: Whether to save workflow graph visualization
        """
        workflow = Workflow.create_workflow(intervals=intervals, strategies=strategies)
        self.intervals = intervals
        self.strategies = strategies
        self.agent = workflow.compile()
        
        if show_agent_graph:
            file_path = ""
            for strategy_name in strategies:
                file_path += strategy_name + "_"
            file_path += "graph.png"
            save_graph_as_png(self.agent, file_path)

    def run(
        self,
        primary_interval: Interval,
        tickers: List[str],
        end_date: datetime,
        portfolio: Dict,
        show_reasoning: bool = False,
        model_name: str = "gpt-4o",
        model_provider: str = "openai",
        model_base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the trading workflow.
        
        Args:
            primary_interval: Primary time interval for decision making
            tickers: List of asset symbols
            end_date: End date for historical data
            portfolio: Initial portfolio state
            show_reasoning: Whether to show model reasoning
            model_name: LLM model name
            model_provider: LLM provider
            model_base_url: Optional base URL for LLM
            
        Returns:
            Dictionary with decisions and analyst signals
        """
        final_state = self.agent.invoke({
            "messages": [
                HumanMessage(
                    content="Make trading decisions based on the provided data.",
                )
            ],
            "data": {
                "primary_interval": primary_interval,
                "intervals": self.intervals,
                "tickers": tickers,
                "portfolio": portfolio,
                "end_date": end_date,
                "analyst_signals": {},
            },
            "metadata": {
                "show_reasoning": show_reasoning,
                "model_name": model_name,
                "model_provider": model_provider,
                "model_base_url": model_base_url,
            },
        })
        
        return {
            "decisions": parse_str_to_json(final_state["messages"][-1].content),
            "analyst_signals": final_state["data"]["analyst_signals"],
        }

