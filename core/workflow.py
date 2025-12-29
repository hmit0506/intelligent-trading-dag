"""
Workflow builder for creating LangGraph workflows.
"""
from typing import List
from langgraph.graph import END, StateGraph
from core.state import AgentState
from core.node import BaseNode
import os
import sys
import importlib

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from nodes.start import StartNode
from nodes.data import DataNode
from nodes.merge import MergeNode
from nodes.risk import RiskManagementNode
from nodes.portfolio import PortfolioManagementNode
from utils.constants import Interval
from utils.helpers import import_strategy_class


class Workflow:
    """Builds the trading workflow graph."""
    
    @staticmethod
    def create_workflow(intervals: List[Interval], strategies: List[str]) -> StateGraph:
        """
        Create the workflow graph with all nodes.
        
        Args:
            intervals: List of time intervals to analyze
            strategies: List of strategy names to use
            
        Returns:
            Compiled StateGraph ready to execute
        """
        workflow = StateGraph(AgentState)
        
        # Start node
        start_node = StartNode()
        workflow.add_node("start", start_node)
        
        # Data nodes for each interval
        merge_node = MergeNode()
        workflow.add_node("merge", merge_node)
        
        for interval in intervals:
            node_name = f"data_{interval.value}"
            data_node = DataNode(interval)
            workflow.add_node(node_name, data_node)
            workflow.add_edge("start", node_name)
            workflow.add_edge(node_name, "merge")
        
        # Strategy nodes - track successfully loaded strategies
        loaded_strategies = []
        for strategy_name in strategies:
            try:
                # Extract module name from strategy name (e.g., "MacdStrategy" -> "macd")
                # Remove "Strategy" suffix and convert to lowercase
                if strategy_name.endswith("Strategy"):
                    module_name = strategy_name[:-8].lower()  # Remove "Strategy" (8 chars)
                else:
                    module_name = strategy_name.lower()
                
                # Try importing from strategies module
                module = importlib.import_module(f"strategies.{module_name}")
                strategy_class = getattr(module, strategy_name)
                strategy_instance = strategy_class()
                workflow.add_node(strategy_name, strategy_instance)
                workflow.add_edge("merge", strategy_name)
                loaded_strategies.append(strategy_name)
            except Exception as e:
                print(f"Warning: Could not load strategy {strategy_name}: {e}")
        
        # Risk and portfolio management
        risk_node = RiskManagementNode()
        portfolio_node = PortfolioManagementNode()
        workflow.add_node("risk", risk_node)
        workflow.add_node("portfolio", portfolio_node)
        
        # Connect only successfully loaded strategies to risk management
        for strategy_name in loaded_strategies:
            workflow.add_edge(strategy_name, "risk")
        
        # Connect risk to portfolio, portfolio to end
        workflow.add_edge("risk", "portfolio")
        workflow.add_edge("portfolio", END)
        
        # Set entry point
        workflow.set_entry_point("start")
        
        return workflow

