"""
Trading Agent - main agent class that orchestrates the workflow.
"""
from typing import List, Dict, Optional, Any
from langchain_core.messages import HumanMessage
from datetime import datetime

from trading_dag.core.workflow import Workflow
from trading_dag.utils.constants import Interval
from trading_dag.utils.helpers import save_graph_as_png, parse_str_to_json


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
            file_path = "_".join(strategies) + "_graph.png"
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
        model_base_url: Optional[str] = None,
        future_timepoints: Optional[Dict[str, Dict[str, float]]] = None,
        prefetched_data: Optional[Dict[str, Any]] = None
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
            future_timepoints: Optional future price projections by interval and ticker
            prefetched_data: Optional prefetched data dictionary for backtest mode

        Returns:
            Dictionary with decisions and analyst signals
        """
        data_dict = {
            "primary_interval": primary_interval,
            "intervals": self.intervals,
            "tickers": tickers,
            "portfolio": portfolio,
            "end_date": end_date,
            "analyst_signals": {},
            "future_timepoints": future_timepoints,
        }

        if prefetched_data is not None:
            data_dict["prefetched_data"] = prefetched_data

        final_state = self.agent.invoke({
            "messages": [
                HumanMessage(
                    content="Make trading decisions based on the provided data.",
                )
            ],
            "data": data_dict,
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
