"""
Portfolio management node - makes final trading decisions using LLM.
"""
import json
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from trading_dag.core.node import BaseNode
from trading_dag.core.state import AgentState, show_agent_reasoning
from trading_dag.llm.llm import get_llm, json_parser


class PortfolioManagementNode(BaseNode):
    """Makes final trading decisions and generates orders for multiple tickers."""

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Generate trading decisions based on all signals and portfolio state."""
        data = state.get('data', {})
        data['name'] = "PortfolioManagementNode"

        portfolio = data.get("portfolio", {})
        analyst_signals = data.get("analyst_signals", {})
        tickers = data.get("tickers", [])

        position_limits = {}
        current_prices = {}
        max_shares = {}
        suggested_quantities = {}
        signals_by_ticker = {}

        for ticker in tickers:
            risk_data = analyst_signals.get("risk_management_agent", {}).get(ticker, {})
            lim = float(risk_data.get("remaining_position_limit", 0.0))
            if lim <= 0.0:
                lim = float(portfolio.get("cash", 0.0))
            position_limits[ticker] = lim
            current_prices[ticker] = risk_data.get("current_price", 0.0)
            suggested_quantities[ticker] = risk_data.get("suggested_quantity", 0.0)

            if current_prices[ticker] > 0.0:
                max_shares[ticker] = float(position_limits[ticker] / current_prices[ticker])
            else:
                max_shares[ticker] = 0.0

            ticker_signals = {}
            for agent_name, signals in analyst_signals.items():
                if ticker in signals and agent_name != "risk_management_agent":
                    ticker_signals[agent_name] = signals[ticker]
            signals_by_ticker[ticker] = ticker_signals

        future_timepoints = data.get("future_timepoints", None)
        intervals = data.get("intervals", [])
        interval_strings = [interval.value if hasattr(interval, 'value') else str(interval) for interval in intervals] if intervals else None
        primary_interval = data.get("primary_interval")
        primary_interval_str = primary_interval.value if primary_interval and hasattr(primary_interval, 'value') else (str(primary_interval) if primary_interval else None)

        use_llm = bool(state["metadata"].get("use_llm_portfolio", True))
        if use_llm:
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
                future_timepoints=future_timepoints,
                intervals=interval_strings,
                primary_interval=primary_interval_str,
            )
        else:
            result = generate_rule_based_trading_decision(
                tickers=tickers,
                signals_by_ticker=signals_by_ticker,
                current_prices=current_prices,
                max_shares=max_shares,
                suggested_quantities=suggested_quantities,
                portfolio=portfolio,
                primary_interval=primary_interval_str,
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


def _signal_direction_score(signal: str) -> float:
    label = str(signal).lower()
    if label in ("bullish", "buy", "long"):
        return 1.0
    if label in ("bearish", "sell", "short"):
        return -1.0
    return 0.0


def generate_rule_based_trading_decision(
    tickers: List[str],
    signals_by_ticker: Dict[str, Dict[str, Any]],
    current_prices: Dict[str, float],
    max_shares: Dict[str, float],
    suggested_quantities: Dict[str, float],
    portfolio: Dict[str, Any],
    primary_interval: Optional[str],
) -> Dict[str, Any]:
    """
    Deterministic portfolio policy using primary-interval strategy votes only.

    Used when LLM portfolio decisions are disabled (ablation). Behavior is intentionally
    simple so results stay reproducible and comparable to the LLM path.
    """
    decisions: Dict[str, Any] = {}
    threshold = 0.12

    for ticker in tickers:
        per_agent = signals_by_ticker.get(ticker, {})
        weighted = 0.0
        weight_sum = 0.0
        for _, interval_map in per_agent.items():
            if not isinstance(interval_map, dict):
                continue
            if primary_interval and primary_interval in interval_map:
                block = interval_map[primary_interval]
            elif interval_map:
                block = next(iter(interval_map.values()))
            else:
                block = {}
            if not isinstance(block, dict):
                continue
            conf = float(block.get("confidence", 50.0)) / 100.0
            weighted += _signal_direction_score(str(block.get("signal", "neutral"))) * conf
            weight_sum += 1.0

        net_score = (weighted / weight_sum) if weight_sum > 0 else 0.0
        price = float(current_prices.get(ticker, 0.0))
        cash = float(portfolio.get("cash", 0.0))
        pos = portfolio.get("positions", {}).get(ticker, {})
        long_amt = float(pos.get("long", 0.0))
        suggested = float(suggested_quantities.get(ticker, 0.0))
        max_sh = float(max_shares.get(ticker, 0.0))
        affordable = cash / price if price > 0 else 0.0
        if max_sh <= 0.0:
            max_sh = affordable

        action = "hold"
        quantity = 0.0
        if net_score > threshold:
            action = "buy"
            raw_qty = suggested if suggested > 0 else affordable * 0.1
            quantity = min(max(raw_qty, 0.0), max_sh, affordable)
        elif net_score < -threshold:
            if long_amt > 1e-9:
                action = "sell"
                quantity = min(long_amt, max(long_amt * 0.5, 0.0))
            else:
                action = "short"
                raw_qty = suggested if suggested > 0 else affordable * 0.05
                cap = max_sh * 0.5 if max_sh > 0 else affordable * 0.25
                quantity = min(max(raw_qty, 0.0), cap)

        decisions[ticker] = {
            "now": {
                "action": action,
                "quantity": float(max(0.0, quantity)),
                "confidence": float(min(95.0, 50.0 + abs(net_score) * 45.0)),
                "reasoning": (
                    f"Rule-based aggregate on primary_interval={primary_interval}, "
                    f"net_score={net_score:.3f}"
                ),
            }
        }

    return {"decisions": decisions}


def generate_trading_decision(
    tickers: List[str],
    signals_by_ticker: Dict[str, Dict[str, Any]],
    current_prices: Dict[str, float],
    max_shares: Dict[str, float],
    suggested_quantities: Dict[str, float],
    portfolio: Dict[str, Any],
    model_name: str,
    model_provider: str,
    model_base_url: Optional[str] = None,
    future_timepoints: Optional[Dict[str, Dict[str, float]]] = None,
    intervals: Optional[List[str]] = None,
    primary_interval: Optional[str] = None
) -> Dict[str, Any]:
    """Generate trading decisions using LLM."""
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
            
            IMPORTANT: You must provide COMPLETE and DETAILED reasoning for each decision. Do not truncate or summarize your reasoning. 
            Explain your thought process thoroughly, including:
            - Analysis of current market conditions
            - Consideration of signals from different strategies
            - Risk assessment
            - Expected outcomes and rationale
            
            Available Actions:
            - "buy": Open or add to long position
            - "sell": Close or reduce long position
            - "short": Open or add to short position
            - "cover": Close or reduce short position
            - "hold": No action
            
            Signal Analysis Guidelines:
            - Each strategy agent provides signals for multiple time intervals (e.g., "1h", "4h", "1d")
            - Signals are organized by ticker → agent → interval → signal/confidence
            - You will see signals from ALL intervals for each strategy
            - PRIMARY INTERVAL: {primary_interval_info}
            - When multiple intervals show conflicting signals, prioritize the PRIMARY INTERVAL signal
            - Consider signals from other intervals as supplementary information
            - Higher confidence signals (closer to 100%) should be given more weight
            - Combine signals from different strategies and intervals to form a comprehensive view
            
            Inputs:
            - signals_by_ticker: dictionary of ticker → signals from various analyst agents (organized by interval)
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
            
            {interval_weighting_info}
            
            Current Prices (Now):
            {current_prices}
            
            {future_analysis_section}
            
            Maximum Shares Allowed (Overall Limit):
            {max_shares}
            
            Suggested Quantities (from Risk Management, prioritize this if feasible):
            {suggested_quantities}
            
            Portfolio Cash: {portfolio_cash}
            Current Positions: {portfolio_positions}
            Current Margin Requirement: {margin_requirement}
            Total Margin Used: {total_margin_used}
            
            CRITICAL INSTRUCTIONS:
            {timepoint_instructions}
            
            Output strictly in JSON with the following structure:
            {{
              "decisions": {{
                "TICKER1": {{
                  "now": {{
                    "action": "buy/sell/short/cover/hold",
                    "quantity": float,
                    "confidence": float between 0 and 100,
                    "reasoning": "Complete analysis for CURRENT timepoint - explain current market conditions, signal interpretation, risk assessment, and immediate trading rationale."
                  }}{future_timepoint_structure}
                }},
                "TICKER2": {{
                  "now": {{ ... }}{future_timepoint_structure}
                }},
                ...
              }}
            }}
            
            IMPORTANT: 
            - ALWAYS include "now" timepoint for current analysis
            {future_timepoint_important}
            """,
        ),
    ])

    if primary_interval:
        primary_interval_info = f"The PRIMARY INTERVAL is '{primary_interval}'. This interval should be given HIGHEST PRIORITY when analyzing signals. If signals from different intervals conflict, prioritize the '{primary_interval}' interval signals."
    else:
        primary_interval_info = "No primary interval specified. All intervals should be considered with equal weight."

    if intervals and primary_interval:
        interval_list = ", ".join(intervals)
        interval_weighting_info = f"""
=== INTERVAL WEIGHTING GUIDELINES ===
Available Intervals: {interval_list}
Primary Interval: {primary_interval} (HIGHEST PRIORITY)

Weighting Strategy:
1. PRIMARY INTERVAL ({primary_interval}): Give this interval the HIGHEST WEIGHT in your decision-making
   - If primary interval signals are strong (confidence > 60%), they should heavily influence your decision
   - Use primary interval signals as the primary basis for trading decisions

2. Other Intervals ({', '.join([i for i in intervals if i != primary_interval])}): Use as supplementary information
   - Consider these signals to confirm or contradict primary interval signals
   - If other intervals strongly contradict primary interval (e.g., primary is bullish but others are bearish with high confidence), exercise caution
   - Higher confidence signals from other intervals should be given more consideration

3. Signal Confidence:
   - Signals with confidence > 70% are considered STRONG
   - Signals with confidence 50-70% are considered MODERATE
   - Signals with confidence < 50% are considered WEAK
   - When combining signals, weight them by their confidence levels

Decision Making Process:
- Start by analyzing the PRIMARY INTERVAL signals for each strategy
- Check if other intervals confirm or contradict the primary interval signals
- If all intervals agree (same direction), increase your confidence in the decision
- If intervals conflict, prioritize PRIMARY INTERVAL but consider the strength of conflicting signals
- Combine signals from multiple strategies, giving more weight to strategies with higher confidence
=== END OF INTERVAL WEIGHTING GUIDELINES ===
"""
    elif intervals:
        interval_list = ", ".join(intervals)
        interval_weighting_info = f"""
=== INTERVAL WEIGHTING GUIDELINES ===
Available Intervals: {interval_list}
No Primary Interval Specified: All intervals should be considered with equal weight.

Weighting Strategy:
- All intervals ({interval_list}) should be given equal consideration
- Look for consensus across intervals - if multiple intervals show the same signal direction, increase confidence
- If intervals conflict, consider the confidence levels of each signal
- Higher confidence signals should be given more weight regardless of interval

Signal Confidence:
- Signals with confidence > 70% are considered STRONG
- Signals with confidence 50-70% are considered MODERATE
- Signals with confidence < 50% are considered WEAK
=== END OF INTERVAL WEIGHTING GUIDELINES ===
"""
    else:
        interval_weighting_info = ""

    future_analysis_section = ""
    available_timepoints = ["now"]

    if future_timepoints and intervals:
        interval_strings = []
        for interval_item in intervals:
            if hasattr(interval_item, 'value'):
                interval_strings.append(interval_item.value)
            else:
                interval_strings.append(str(interval_item))

        future_analysis_section = "\n=== FUTURE PRICE PROJECTIONS ===\n"
        future_analysis_section += "You MUST provide SEPARATE analysis for EACH of these timepoints:\n\n"
        future_analysis_section += "1. NOW (Current timepoint):\n"
        future_analysis_section += "   Use current prices and signals for immediate trading decisions.\n\n"

        timepoint_index = 2
        for interval_str in interval_strings:
            if interval_str in future_timepoints:
                available_timepoints.append(interval_str)
                future_analysis_section += f"{timepoint_index}. {interval_str.upper()} FUTURE TIMEPOINT:\n"
                for ticker, price in future_timepoints[interval_str].items():
                    if ticker in tickers:
                        current_price = current_prices.get(ticker, 0.0)
                        change_pct = ((price - current_price) / current_price * 100) if current_price > 0 else 0.0
                        future_analysis_section += f"   {ticker}: Projected price ${price:.2f} ({change_pct:+.2f}% from current ${current_price:.2f})\n"
                future_analysis_section += f"   Analyze market conditions at this {interval_str} future timepoint and provide a SEPARATE trading decision.\n\n"
                timepoint_index += 1

        future_analysis_section += "=== END OF FUTURE PROJECTIONS ===\n"
        future_analysis_section += "\nREMEMBER: You must provide a SEPARATE decision and reasoning for EACH timepoint (now, 1h, 4h, etc.)\n"

        timepoint_instructions = """You MUST provide SEPARATE analysis and trading decisions for EACH timepoint:
1. "now" - Current timepoint analysis
2. For each future timepoint provided (e.g., "1h", "4h"), provide a separate analysis

For EACH timepoint, you need to:
- Analyze market conditions at that specific timepoint
- Consider the projected price at that timepoint
- Make an independent trading decision for that timepoint
- Provide complete and detailed reasoning for that timepoint"""

        future_timepoint_structure = """,
                  "<interval1>": {{
                    "action": "buy/sell/short/cover/hold",
                    "quantity": float,
                    "confidence": float between 0 and 100,
                    "reasoning": "Complete analysis for <interval1> FUTURE timepoint - explain projected market conditions, expected price movement, signal evolution, and trading rationale for this timeframe."
                  }},
                  "<interval2>": {{
                    "action": "buy/sell/short/cover/hold",
                    "quantity": float,
                    "confidence": float between 0 and 100,
                    "reasoning": "Complete analysis for <interval2> FUTURE timepoint - explain projected market conditions, expected price movement, signal evolution, and trading rationale for this timeframe."
                  }}"""

        future_timepoint_important = """- Include each future timepoint mentioned in the future_analysis_section (e.g., "1h", "4h", etc.)
            - Use the EXACT interval string as the key (e.g., "1h", "4h", not "1H" or "1 hour")
            - Provide a SEPARATE decision and reasoning for EACH timepoint
            - If a timepoint is not provided in future_analysis_section, omit it from the output"""
    else:
        timepoint_instructions = """You MUST provide analysis and trading decisions for the CURRENT timepoint ("now") only.

            For the current timepoint, you need to:
            - Analyze current market conditions
            - Consider current prices and signals
            - Make trading decisions based on available information
            - Provide complete and detailed reasoning"""

        future_timepoint_structure = ""
        future_timepoint_important = """- Only provide the "now" timepoint decision (no future timepoints)"""

    llm = get_llm(provider=model_provider, model=model_name, base_url=model_base_url)
    chain = prompt | llm | json_parser

    result = chain.invoke({
        "signals_by_ticker": json.dumps(signals_by_ticker, indent=2),
        "current_prices": json.dumps(current_prices, indent=2),
        "future_analysis_section": future_analysis_section,
        "max_shares": json.dumps(max_shares, indent=2),
        "suggested_quantities": json.dumps(suggested_quantities, indent=2),
        "portfolio_cash": f"{portfolio.get('cash', 0.0):.2f}",
        "portfolio_positions": json.dumps(portfolio.get('positions', {}), indent=2),
        "margin_requirement": f"{portfolio.get('margin_requirement', 0.0):.2f}",
        "total_margin_used": f"{portfolio.get('margin_used', 0.0):.2f}",
        "timepoint_instructions": timepoint_instructions,
        "future_timepoint_structure": future_timepoint_structure,
        "future_timepoint_important": future_timepoint_important,
        "primary_interval_info": primary_interval_info,
        "interval_weighting_info": interval_weighting_info,
    })

    return result
