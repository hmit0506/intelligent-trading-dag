"""
Risk management node - controls position sizing based on risk factors.
"""
import json
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage

from trading_dag.core.node import BaseNode
from trading_dag.core.state import AgentState, show_agent_reasoning
from trading_dag.utils.constants import Interval


class RiskManagementNode(BaseNode):
    """Controls position sizing based on real-world risk factors."""

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Calculate position sizing and risk parameters for each ticker."""
        data = state.get('data', {})
        data['name'] = "RiskManagementNode"

        portfolio = data.get("portfolio", {})
        tickers = data.get("tickers", [])
        primary_interval: Optional[Interval] = data.get("primary_interval")

        risk_analysis = {}
        current_prices = {}

        for ticker in tickers:
            price_df = data.get(f"{ticker}_{primary_interval.value}")
            current_price = price_df["close"].iloc[-1]
            current_prices[ticker] = current_price

            risk_per_trade_pct = 0.02
            stop_loss_pct = 0.05
            stop_loss_price = current_price * (1 - stop_loss_pct)

            total_portfolio_value = portfolio["cash"]
            for t, pos_data in portfolio["positions"].items():
                total_portfolio_value += pos_data["long"] * current_prices.get(t, 0.0)
                total_portfolio_value -= pos_data["short"] * current_prices.get(t, 0.0)

            quantity_to_trade = 0.0
            if current_price > stop_loss_price:
                risk_amount_per_share = current_price - stop_loss_price
                if risk_amount_per_share > 0:
                    quantity_to_trade = (total_portfolio_value * risk_per_trade_pct) / risk_amount_per_share
                    quantity_to_trade = max(0.0, round(quantity_to_trade, 0))
                    min_quantity = 0.001
                    if quantity_to_trade > 0 and quantity_to_trade < min_quantity:
                        quantity_to_trade = min_quantity

            risk_analysis[ticker] = {
                "suggested_quantity": float(quantity_to_trade),
                "current_price": float(current_price),
                "reasoning": {
                    "portfolio_value": float(total_portfolio_value),
                    "risk_per_trade_pct": float(risk_per_trade_pct),
                    "stop_loss_pct": float(stop_loss_pct),
                    "stop_loss_price": float(stop_loss_price),
                    "calculated_quantity": float(quantity_to_trade),
                    "available_cash": float(portfolio["cash"]),
                },
            }

        message = HumanMessage(
            content=json.dumps(risk_analysis),
            name="risk_management_agent",
        )

        if state["metadata"]["show_reasoning"]:
            show_agent_reasoning(risk_analysis, "Risk Management Agent")

        data["analyst_signals"]["risk_management_agent"] = risk_analysis

        return {
            "messages": [message],
            "data": data,
        }
