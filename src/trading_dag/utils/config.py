"""
Configuration management.
"""
from pydantic_settings import BaseSettings
from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
import yaml
from pathlib import Path

from dotenv import load_dotenv
from trading_dag.utils.constants import Interval, QUANTITY_DECIMALS

load_dotenv()


class SignalConfig(BaseModel):
    """Signal generation configuration."""
    intervals: List[Interval]
    tickers: List[str]
    strategies: List[str]


class RiskManagementConfig(BaseModel):
    """
    Position sizing inputs for RiskManagementNode (wired via AgentState metadata).

    - stop_distance_mode ``entry_or_spot_pct``: use average cost for open long/short legs;
      when flat, fall back to spot-based distance (same structure as the legacy node).
    - ``atr``: use ATR(tr) * atr_multiplier as dollars risk per unit (volatility scaling).
    """

    model_config = ConfigDict(extra="ignore")

    risk_per_trade_pct: float = Field(default=0.02, gt=0.0, le=1.0)
    stop_loss_pct: float = Field(default=0.05, gt=0.0, le=1.0)
    min_quantity: float = Field(default=0.001, ge=0.0)
    quantity_decimals: int = Field(default=QUANTITY_DECIMALS, ge=0, le=12)
    stop_distance_mode: Literal["entry_or_spot_pct", "atr"] = "entry_or_spot_pct"
    atr_period: int = Field(default=14, ge=2, le=500)
    atr_multiplier: float = Field(default=1.0, gt=0.0, le=100.0)
    max_notional_fraction_per_ticker: float = Field(
        default=1.0,
        gt=0.0,
        le=10.0,
        description="Cap per-ticker suggested size: min(cash, fraction * total_portfolio_value) "
        "as position limit; 1.0 matches legacy 'cash only' cap when portfolio <= cash + holdings.",
    )


def risk_config_to_metadata(risk: RiskManagementConfig) -> Dict[str, Any]:
    """Flatten risk settings for LangGraph metadata (JSON-serializable)."""
    return {
        "risk_per_trade_pct": risk.risk_per_trade_pct,
        "risk_stop_loss_pct": risk.stop_loss_pct,
        "risk_min_quantity": risk.min_quantity,
        "risk_quantity_decimals": risk.quantity_decimals,
        "risk_stop_distance_mode": risk.stop_distance_mode,
        "risk_atr_period": risk.atr_period,
        "risk_atr_multiplier": risk.atr_multiplier,
        "risk_max_notional_fraction_per_ticker": risk.max_notional_fraction_per_ticker,
    }


class ModelConfig(BaseModel):
    """LLM model configuration."""
    name: str
    provider: str
    base_url: Optional[str] = None
    temperature: Optional[float] = 0.0
    format: Optional[str] = "json"

    @model_validator(mode='after')
    def validate_format(self):
        """Ensure format is 'json'."""
        if self.format and self.format != "json":
            raise ValueError(f"format must be 'json' (got '{self.format}'). Only JSON format is supported.")
        return self


class Config(BaseSettings):
    """Main configuration class."""
    model_config = ConfigDict(extra="allow")

    mode: str
    start_date: datetime
    end_date: datetime
    primary_interval: Interval
    initial_cash: float
    initial_positions: Optional[Any] = None
    margin_requirement: float = 0.0
    show_reasoning: bool = False
    show_agent_graph: bool = True
    signals: SignalConfig
    model: ModelConfig

    print_frequency: int = 1
    use_progress_bar: bool = True
    enable_logging: bool = True
    save_decision_history: bool = True
    auto_cleanup_files: bool = False
    file_retention_days: int = 30
    file_keep_latest: int = 10

    risk: RiskManagementConfig = Field(default_factory=RiskManagementConfig)

    @model_validator(mode="before")
    @classmethod
    def merge_portfolio_cash(cls, data: Any) -> Any:
        """
        Single source of truth for starting cash: prefer initial_positions.cash.

        YAML may omit top-level initial_cash when initial_positions.cash is set.
        For backward compatibility, legacy initial_cash-only configs still work.
        If both are set to different numbers, validation fails to avoid silent mismatch.
        """
        if not isinstance(data, dict):
            return data
        initial_positions = data.get("initial_positions")
        top_raw = data.get("initial_cash")
        cash_from_positions: Optional[float] = None
        if isinstance(initial_positions, dict) and initial_positions.get("cash") is not None:
            cash_from_positions = float(initial_positions["cash"])
        top_cash: Optional[float] = float(top_raw) if top_raw is not None else None

        if cash_from_positions is not None and top_cash is not None and cash_from_positions != top_cash:
            raise ValueError(
                "initial_cash and initial_positions.cash disagree; remove initial_cash and use only "
                "initial_positions.cash, or make them the same."
            )

        resolved = cash_from_positions if cash_from_positions is not None else top_cash
        if resolved is None:
            raise ValueError(
                "Portfolio starting cash is required: set initial_positions.cash "
                "(recommended) or legacy initial_cash."
            )

        merged = {**data, "initial_cash": float(resolved)}
        return merged

    @model_validator(mode='after')
    def validate_primary_interval(self):
        """Ensure primary interval is in the intervals list."""
        if self.primary_interval not in self.signals.intervals:
            self.signals.intervals.append(self.primary_interval)
            seen = set()
            unique_intervals = []
            for interval in self.signals.intervals:
                if interval not in seen:
                    seen.add(interval)
                    unique_intervals.append(interval)
            self.signals.intervals = unique_intervals
        return self


def load_config(config_path: str = "config/config.yaml") -> Config:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config YAML file. Tries config/config.yaml, then config.yaml.

    Returns:
        Config object
    """
    path = Path(config_path)
    if not path.exists():
        path = Path("config.yaml")
    if not path.exists():
        raise FileNotFoundError(f"Config file not found. Tried: {config_path}, config.yaml")
    with open(path, "r") as f:
        yaml_data = yaml.safe_load(f)
    return Config(**yaml_data)
