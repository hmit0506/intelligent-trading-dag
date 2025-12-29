from typing import Dict, Any
import json
import pandas as pd
from langchain_core.messages import HumanMessage
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.node import BaseNode
from core.state import AgentState
from indicators.indicators import calculate_bollinger_bands

class BollingerStrategy(BaseNode):
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Bollinger Band strategy implementation that processes market data across multiple timeframes.
        """
        data = state.get("data", {})
        data['name'] = "BollingerStrategy"  # Set strategy name for visualization

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

                # Calculate Bollinger Bands
                upper_band, lower_band = calculate_bollinger_bands(df)
                sma = df['close'].rolling(window=20).mean() # Assuming default window 20

                signal = "neutral"
                confidence = 50

                last_close = df['close'].iloc[-1]
                last_upper = upper_band.iloc[-1]
                last_lower = lower_band.iloc[-1]
                last_sma = sma.iloc[-1]

                if last_close < last_lower:
                    signal = "bullish" # Price below lower band, potential buy signal
                    confidence = 75
                elif last_close > last_upper:
                    signal = "bearish" # Price above upper band, potential sell signal
                    confidence = 75
                elif last_close > last_sma:
                    signal = "bullish" # Price above SMA, indicating upward momentum within bands
                    confidence = 60
                elif last_close < last_sma:
                    signal = "bearish" # Price below SMA, indicating downward momentum within bands
                    confidence = 60

                technical_analysis[ticker][interval.value] = {
                    "signal": signal,
                    "confidence": confidence,
                    "strategy_signals": {
                        "bollinger_bands": {
                            "signal": signal,
                            "confidence": confidence,
                            "metrics": {
                                "close": float(last_close),
                                "upper_band": float(last_upper),
                                "lower_band": float(last_lower),
                                "sma": float(last_sma),
                            }
                        }
                    }
                }

        message = HumanMessage(
            content=json.dumps(technical_analysis),
            name="bollinger_strategy_agent",
        )

        if "analyst_signals" not in state["data"]:
            state["data"]["analyst_signals"] = {}
        state["data"]["analyst_signals"]["bollinger_strategy_agent"] = technical_analysis

        return {
            "messages": [message],
            "data": data,
        }

