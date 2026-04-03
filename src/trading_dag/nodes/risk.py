"""
Risk management node - controls position sizing based on risk factors.
"""
import json
import math
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from langchain_core.messages import HumanMessage

from trading_dag.core.node import BaseNode
from trading_dag.core.state import AgentState, show_agent_reasoning
from trading_dag.utils.constants import Interval, QUANTITY_DECIMALS


def _metadata_float(meta: Dict[str, Any], key: str, default: float) -> float:
    v = meta.get(key, default)
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _metadata_int(meta: Dict[str, Any], key: str, default: int) -> int:
    v = meta.get(key, default)
    try:
        return int(v)
    except (TypeError, ValueError):
        return int(default)


def _last_atr_from_ohlc(price_df: pd.DataFrame, period: int, fallback: float) -> float:
    """Wilder-style ATR approximation using EMA of true range."""
    if price_df is None or len(price_df) < 2:
        return max(fallback, 1e-9)
    try:
        high = price_df["high"].astype(float)
        low = price_df["low"].astype(float)
        close = price_df["close"].astype(float)
    except (KeyError, TypeError):
        return max(fallback, 1e-9)
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    if tr.isna().all():
        return max(fallback, 1e-9)
    atr_series = tr.ewm(alpha=1.0 / float(period), adjust=False).mean()
    last = atr_series.iloc[-1]
    if not math.isfinite(last) or last <= 0:
        return max(fallback, 1e-9)
    return float(last)


def _risk_per_share_full(
    *,
    mode: str,
    current_price: float,
    pos_long: float,
    pos_short: float,
    long_basis: float,
    short_basis: float,
    stop_loss_pct: float,
    price_df: pd.DataFrame,
    atr_period: int,
    atr_multiplier: float,
) -> Tuple[float, Dict[str, Any]]:
    """Return dollars at risk per share (unit) and debug fields."""
    debug: Dict[str, Any] = {"mode": mode}
    if current_price <= 0:
        return 0.0, debug

    if mode == "atr":
        atr = _last_atr_from_ohlc(price_df, atr_period, fallback=current_price * 0.01)
        r = max(1e-12, atr * float(atr_multiplier))
        debug.update({"atr": atr, "atr_multiplier": float(atr_multiplier), "risk_per_share": r})
        return r, debug

    # entry_or_spot_pct
    if pos_short > 1e-12 and short_basis > 0:
        stop_price = short_basis * (1.0 + stop_loss_pct)
        r = max(0.0, stop_price - current_price)
        debug.update(
            {
                "leg": "short",
                "reference_basis": float(short_basis),
                "stop_price": float(stop_price),
                "risk_per_share": float(r),
            }
        )
        return r, debug

    if pos_long > 1e-12 and long_basis > 0:
        stop_price = long_basis * (1.0 - stop_loss_pct)
        r = max(0.0, current_price - stop_price)
        debug.update(
            {
                "leg": "long",
                "reference_basis": float(long_basis),
                "stop_price": float(stop_price),
                "risk_per_share": float(r),
            }
        )
        return r, debug

    stop_price = current_price * (1.0 - stop_loss_pct)
    r = max(0.0, current_price - stop_price)
    debug.update(
        {
            "leg": "flat_spot",
            "stop_price": float(stop_price),
            "risk_per_share": float(r),
        }
    )
    return r, debug


def _finalize_quantity(
    raw: float,
    *,
    current_price: float,
    total_portfolio_value: float,
    max_notional_fraction: float,
    decimals: int,
    min_q: float,
) -> float:
    if current_price <= 0 or raw <= 0:
        return 0.0
    cap_notional = max_notional_fraction * total_portfolio_value
    max_shares = cap_notional / current_price if current_price > 0 else 0.0
    q = min(raw, max_shares)
    q = max(0.0, round(float(q), int(decimals)))
    if q > 0 and q < min_q:
        q = float(min_q)
    return float(q)


class RiskManagementNode(BaseNode):
    """Controls position sizing based on configurable risk parameters (via metadata)."""

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """Calculate position sizing and risk parameters for each ticker."""
        data = state.get("data", {})
        data["name"] = "RiskManagementNode"

        portfolio = data.get("portfolio", {})
        tickers = data.get("tickers", [])
        primary_interval: Optional[Interval] = data.get("primary_interval")
        meta = state["metadata"]

        risk_per_trade_pct = _metadata_float(meta, "risk_per_trade_pct", 0.02)
        stop_loss_pct = _metadata_float(meta, "risk_stop_loss_pct", 0.05)
        min_quantity = _metadata_float(meta, "risk_min_quantity", 0.001)
        quantity_decimals = _metadata_int(meta, "risk_quantity_decimals", QUANTITY_DECIMALS)
        stop_mode = str(meta.get("risk_stop_distance_mode", "entry_or_spot_pct"))
        if stop_mode not in ("entry_or_spot_pct", "atr"):
            stop_mode = "entry_or_spot_pct"
        atr_period = _metadata_int(meta, "risk_atr_period", 14)
        atr_multiplier = _metadata_float(meta, "risk_atr_multiplier", 1.0)
        max_notional_frac = _metadata_float(meta, "risk_max_notional_fraction_per_ticker", 1.0)

        full_risk = bool(meta.get("ablation_full_risk", True))

        risk_analysis = {}
        current_prices: Dict[str, float] = {}

        for ticker in tickers:
            key = f"{ticker}_{primary_interval.value}" if primary_interval else None
            price_df = data.get(key) if key else None
            if price_df is None or len(price_df) < 1:
                risk_analysis[ticker] = {
                    "suggested_quantity": 0.0,
                    "current_price": 0.0,
                    "remaining_position_limit": float(portfolio.get("cash", 0.0)),
                    "reasoning": {"error": "missing_ohlc_for_primary_interval"},
                }
                continue

            current_price = float(price_df["close"].iloc[-1])
            current_prices[ticker] = current_price

            total_portfolio_value = float(portfolio["cash"])
            for t, pos_data in portfolio["positions"].items():
                total_portfolio_value += pos_data["long"] * current_prices.get(t, 0.0)
                total_portfolio_value -= pos_data["short"] * current_prices.get(t, 0.0)

            pos_row = portfolio["positions"][ticker]
            pos_long = float(pos_row.get("long", 0.0))
            pos_short = float(pos_row.get("short", 0.0))
            long_basis = float(pos_row.get("long_cost_basis", 0.0))
            short_basis = float(pos_row.get("short_cost_basis", 0.0))

            cash = float(portfolio.get("cash", 0.0))
            position_limit = min(cash, max_notional_frac * total_portfolio_value)

            if not full_risk:
                raw = 0.0
                if current_price > 0:
                    raw = (total_portfolio_value * risk_per_trade_pct) / current_price
                qty = _finalize_quantity(
                    raw,
                    current_price=current_price,
                    total_portfolio_value=total_portfolio_value,
                    max_notional_fraction=max_notional_frac,
                    decimals=quantity_decimals,
                    min_q=min_quantity,
                )
                risk_analysis[ticker] = {
                    "suggested_quantity": qty,
                    "current_price": current_price,
                    "remaining_position_limit": float(position_limit),
                    "reasoning": {
                        "mode": "simplified_fixed_fraction",
                        "portfolio_value": float(total_portfolio_value),
                        "risk_per_trade_pct": float(risk_per_trade_pct),
                        "calculated_quantity": float(qty),
                        "available_cash": cash,
                    },
                }
                continue

            risk_per_share, dbg = _risk_per_share_full(
                mode=stop_mode,
                current_price=current_price,
                pos_long=pos_long,
                pos_short=pos_short,
                long_basis=long_basis,
                short_basis=short_basis,
                stop_loss_pct=stop_loss_pct,
                price_df=price_df,
                atr_period=atr_period,
                atr_multiplier=atr_multiplier,
            )

            raw = 0.0
            if risk_per_share > 0:
                raw = (total_portfolio_value * risk_per_trade_pct) / risk_per_share

            qty = _finalize_quantity(
                raw,
                current_price=current_price,
                total_portfolio_value=total_portfolio_value,
                max_notional_fraction=max_notional_frac,
                decimals=quantity_decimals,
                min_q=min_quantity,
            )

            reasoning = {
                "mode": "full_risk_sizing",
                "portfolio_value": float(total_portfolio_value),
                "risk_per_trade_pct": float(risk_per_trade_pct),
                "stop_loss_pct": float(stop_loss_pct),
                "stop_distance_mode": stop_mode,
                "calculated_quantity": float(qty),
                "available_cash": cash,
                "risk_per_share": float(risk_per_share),
                **dbg,
            }

            risk_analysis[ticker] = {
                "suggested_quantity": float(qty),
                "current_price": float(current_price),
                "remaining_position_limit": float(position_limit),
                "reasoning": reasoning,
            }

        message = HumanMessage(
            content=json.dumps(risk_analysis),
            name="risk_management_agent",
        )

        if meta["show_reasoning"]:
            show_agent_reasoning(risk_analysis, "Risk Management Agent")

        data["analyst_signals"]["risk_management_agent"] = risk_analysis

        return {
            "messages": [message],
            "data": data,
        }
