"""
RSI Strategy - Relative Strength Index based trading strategy.
"""
from typing import Dict, Any
import json
import pandas as pd
from langchain_core.messages import HumanMessage

from trading_dag.core.node import BaseNode
from trading_dag.core.state import AgentState
from trading_dag.indicators.indicators import calculate_rsi


class RSIStrategy(BaseNode):
    """RSI-based trading strategy using multiple RSI periods."""

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Generate RSI-based trading signals across multiple timeframes."""
        data = state.get("data", {})
        data['name'] = "RSIStrategy"

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

                rsi_14 = calculate_rsi(df, period=14)
                rsi_28 = calculate_rsi(df, period=28)

                last_rsi_14 = rsi_14.iloc[-1] if not rsi_14.empty else float('nan')
                last_rsi_28 = rsi_28.iloc[-1] if not rsi_28.empty else float('nan')

                if pd.isna(last_rsi_14) or pd.isna(last_rsi_28):
                    technical_analysis[ticker][interval.value] = {
                        "signal": "neutral",
                        "confidence": 50,
                        "strategy_signals": {
                            "rsi": {
                                "signal": "neutral",
                                "confidence": 50,
                                "metrics": {
                                    "rsi_14": None,
                                    "rsi_28": None,
                                    "rsi_14_level": "insufficient_data",
                                    "rsi_28_level": "insufficient_data",
                                }
                            }
                        }
                    }
                    continue

                signal, confidence = "neutral", 50

                if last_rsi_14 < 30 and last_rsi_28 < 30:
                    signal, confidence = "bullish", min(75 + (30 - max(last_rsi_14, last_rsi_28)) * 2, 90)
                elif last_rsi_14 > 70 and last_rsi_28 > 70:
                    signal, confidence = "bearish", min(75 + (min(last_rsi_14, last_rsi_28) - 70) * 2, 90)
                elif last_rsi_14 < 30 and last_rsi_28 < 40:
                    signal, confidence = "bullish", 65
                elif last_rsi_14 > 70 and last_rsi_28 > 60:
                    signal, confidence = "bearish", 65
                elif last_rsi_14 < 30:
                    signal, confidence = "bullish", 60
                elif last_rsi_14 > 70:
                    signal, confidence = "bearish", 60
                else:
                    distance_from_neutral = abs(last_rsi_14 - 50) / 50.0
                    confidence = 50 + int(distance_from_neutral * 20) if not pd.isna(distance_from_neutral) else 50

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
