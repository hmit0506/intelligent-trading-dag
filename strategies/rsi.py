"""
RSI Strategy - Relative Strength Index based trading strategy.
"""
from typing import Dict, Any
import json
import pandas as pd
from langchain_core.messages import HumanMessage
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.node import BaseNode
from core.state import AgentState
from indicators.indicators import calculate_rsi


class RSIStrategy(BaseNode):
    """RSI-based trading strategy using multiple RSI periods."""
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Generate RSI-based trading signals across multiple timeframes.
        
        RSI Strategy Logic:
        - RSI < 30: Oversold condition, bullish signal
        - RSI > 70: Overbought condition, bearish signal
        - 30 <= RSI <= 70: Neutral condition
        - Uses multiple RSI periods (14 and 28) for confirmation
        """
        data = state.get("data", {})
        data['name'] = "RSIStrategy"  # Set strategy name for visualization

        tickers = data.get("tickers", [])
        intervals = data.get("intervals", [])

        technical_analysis = {}
        for ticker in tickers:
            technical_analysis[ticker] = {}

        for ticker in tickers:
            for interval in intervals:
                df = data.get(f"{ticker}_{interval.value}", pd.DataFrame())

                if df.empty:
                    continue

                # Calculate RSI with multiple periods
                rsi_14 = calculate_rsi(df, period=14)
                rsi_28 = calculate_rsi(df, period=28)

                # Get latest RSI values
                last_rsi_14 = rsi_14.iloc[-1]
                last_rsi_28 = rsi_28.iloc[-1]

                # Determine signal based on RSI values
                signal = "neutral"
                confidence = 50

                # Strong oversold condition (both RSI periods < 30)
                if last_rsi_14 < 30 and last_rsi_28 < 30:
                    signal = "bullish"
                    # Higher confidence when RSI is more extreme
                    confidence = min(75 + (30 - max(last_rsi_14, last_rsi_28)) * 2, 90)
                # Strong overbought condition (both RSI periods > 70)
                elif last_rsi_14 > 70 and last_rsi_28 > 70:
                    signal = "bearish"
                    # Higher confidence when RSI is more extreme
                    confidence = min(75 + (min(last_rsi_14, last_rsi_28) - 70) * 2, 90)
                # Moderate oversold (RSI 14 < 30, RSI 28 < 40)
                elif last_rsi_14 < 30 and last_rsi_28 < 40:
                    signal = "bullish"
                    confidence = 65
                # Moderate overbought (RSI 14 > 70, RSI 28 > 60)
                elif last_rsi_14 > 70 and last_rsi_28 > 60:
                    signal = "bearish"
                    confidence = 65
                # Weak oversold (only RSI 14 < 30)
                elif last_rsi_14 < 30:
                    signal = "bullish"
                    confidence = 60
                # Weak overbought (only RSI 14 > 70)
                elif last_rsi_14 > 70:
                    signal = "bearish"
                    confidence = 60
                # Neutral zone
                else:
                    signal = "neutral"
                    # Adjust confidence based on how close to neutral (50)
                    distance_from_neutral = abs(last_rsi_14 - 50) / 50.0
                    confidence = 50 + int(distance_from_neutral * 20)

                technical_analysis[ticker][interval.value] = {
                    "signal": signal,
                    "confidence": confidence,
                    "strategy_signals": {
                        "rsi": {
                            "signal": signal,
                            "confidence": confidence,
                            "metrics": {
                                "rsi_14": float(last_rsi_14),
                                "rsi_28": float(last_rsi_28),
                                "rsi_14_level": self._get_rsi_level(last_rsi_14),
                                "rsi_28_level": self._get_rsi_level(last_rsi_28),
                            }
                        }
                    }
                }

        message = HumanMessage(
            content=json.dumps(technical_analysis),
            name="rsi_strategy_agent",
        )

        if "analyst_signals" not in state["data"]:
            state["data"]["analyst_signals"] = {}
        state["data"]["analyst_signals"]["rsi_strategy_agent"] = technical_analysis

        return {
            "messages": [message],
            "data": data,
        }
    
    def _get_rsi_level(self, rsi_value: float) -> str:
        """Get RSI level description."""
        if rsi_value < 30:
            return "oversold"
        elif rsi_value > 70:
            return "overbought"
        elif rsi_value < 40:
            return "weak_oversold"
        elif rsi_value > 60:
            return "weak_overbought"
        else:
            return "neutral"
