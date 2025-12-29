"""
Portfolio management node - makes final trading decisions using LLM.
"""
import json
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.node import BaseNode
from core.state import AgentState, show_agent_reasoning
from llm.llm import get_llm, json_parser


class PortfolioManagementNode(BaseNode):
    """Makes final trading decisions and generates orders for multiple tickers."""
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Generate trading decisions based on all signals and portfolio state.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with trading decisions
        """
        data = state.get('data', {})
        data['name'] = "PortfolioManagementNode"
        
        portfolio = data.get("portfolio", {})
        analyst_signals = data.get("analyst_signals", {})
        tickers = data.get("tickers", [])

        # Extract risk management data for each ticker
        position_limits = {}
        current_prices = {}
        max_shares = {}
        suggested_quantities = {}
        signals_by_ticker = {}
        
        for ticker in tickers:
            risk_data = analyst_signals.get("risk_management_agent", {}).get(ticker, {})
            position_limits[ticker] = risk_data.get("remaining_position_limit", 0.0)
            current_prices[ticker] = risk_data.get("current_price", 0.0)
            suggested_quantities[ticker] = risk_data.get("suggested_quantity", 0.0)

            if current_prices[ticker] > 0.0:
                max_shares[ticker] = float(position_limits[ticker] / current_prices[ticker])
            else:
                max_shares[ticker] = 0.0

            # Get signals for the ticker
            ticker_signals = {}
            for agent_name, signals in analyst_signals.items():
                if ticker in signals and agent_name != "risk_management_agent":
                    ticker_signals[agent_name] = signals[ticker]

            signals_by_ticker[ticker] = ticker_signals

        # Generate the trading decision
        result = generate_trading_decision(
            tickers=tickers,
            signals_by_ticker=signals_by_ticker,
            current_prices=current_prices,
            max_shares=max_shares,
            suggested_quantities=suggested_quantities,
            portfolio=portfolio,
            model_name=state["metadata"]["model_name"],
            model_provider=state["metadata"]["model_provider"],
            model_base_url=state["metadata"]["model_base_url"],
        )

        message = HumanMessage(
            content=json.dumps(result.get("decisions", {})),
            name="portfolio_management",
        )

        if state["metadata"]["show_reasoning"]:
            show_agent_reasoning(result.get("decisions"), "Portfolio Management Agent")

        return {
            "messages": [message],
            "data": state["data"],
        }


def generate_trading_decision(
    tickers: List[str],
    signals_by_ticker: Dict[str, Dict[str, Any]],
    current_prices: Dict[str, float],
    max_shares: Dict[str, float],
    suggested_quantities: Dict[str, float],
    portfolio: Dict[str, Any],
    model_name: str,
    model_provider: str,
    model_base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate trading decisions using LLM.
    
    Args:
        tickers: List of ticker symbols
        signals_by_ticker: Signals from various strategies
        current_prices: Current prices for each ticker
        max_shares: Maximum shares allowed per ticker
        suggested_quantities: Quantities suggested by risk management
        portfolio: Current portfolio state
        model_name: LLM model name
        model_provider: LLM provider
        model_base_url: Optional base URL for LLM
        
    Returns:
        Dictionary with trading decisions
    """
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are a portfolio manager making final trading decisions based on multiple tickers.
            
            Trading Rules:
            - For long positions:
              * Only buy if you have available cash
              * Only sell if you currently hold long shares of that ticker
              * Sell quantity must be ≤ current long position shares
              * Buy quantity must be ≤ max_shares for that ticker, AND ideally respect suggested_quantity from risk management.
            
            - For short positions:
              * Only short if you have available margin (position value × margin requirement)
              * Only cover if you currently have short shares of that ticker
              * Cover quantity must be ≤ current short position shares
              * Short quantity must respect margin requirements
            
            - The max_shares values are pre-calculated to respect overall position limits.
            - The suggested_quantities are calculated by the risk management node using a Fixed Fractional method. Prioritize these quantities if possible.
            - Consider both long and short opportunities based on signals
            - Maintain appropriate risk management with both long and short exposure
            
            Available Actions:
            - "buy": Open or add to long position
            - "sell": Close or reduce long position
            - "short": Open or add to short position
            - "cover": Close or reduce short position
            - "hold": No action
            
            Inputs:
            - signals_by_ticker: dictionary of ticker → signals from various analyst agents
            - max_shares: maximum shares allowed per ticker based on overall position limits
            - suggested_quantities: quantities suggested by the risk management node
            - portfolio_cash: current cash in portfolio
            - portfolio_positions: current positions (both long and short)
            - current_prices: current prices for each ticker
            - margin_requirement: current margin requirement for short positions
            - total_margin_used: total margin currently in use
            """,
        ),
        (
            "human",
            """Based on the team's analysis, make your trading decisions for each ticker.
            
            Here are the aggregated signals from various strategies by ticker:
            {signals_by_ticker}
            
            Current Prices:
            {current_prices}
            
            Maximum Shares Allowed (Overall Limit):
            {max_shares}
            
            Suggested Quantities (from Risk Management, prioritize this if feasible):
            {suggested_quantities}
            
            Portfolio Cash: {portfolio_cash}
            Current Positions: {portfolio_positions}
            Current Margin Requirement: {margin_requirement}
            Total Margin Used: {total_margin_used}
            
            Output strictly in JSON with the following structure:
            {{
              "decisions": {{
                "TICKER1": {{
                  "action": "buy/sell/short/cover/hold",
                  "quantity": float,
                  "confidence": float between 0 and 100,
                  "reasoning": "string"
                }},
                "TICKER2": {{
                  ...
                }},
                ...
              }}
            }}
            """,
        ),
    ])

    llm = get_llm(provider=model_provider, model=model_name, base_url=model_base_url)
    chain = prompt | llm | json_parser
    
    result = chain.invoke({
        "signals_by_ticker": json.dumps(signals_by_ticker, indent=2),
        "current_prices": json.dumps(current_prices, indent=2),
        "max_shares": json.dumps(max_shares, indent=2),
        "suggested_quantities": json.dumps(suggested_quantities, indent=2),
        "portfolio_cash": f"{portfolio.get('cash', 0.0):.2f}",
        "portfolio_positions": json.dumps(portfolio.get('positions', {}), indent=2),
        "margin_requirement": f"{portfolio.get('margin_requirement', 0.0):.2f}",
        "total_margin_used": f"{portfolio.get('margin_used', 0.0):.2f}",
    })
    
    return result

