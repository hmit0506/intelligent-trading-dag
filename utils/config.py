"""
Configuration management.
"""
from pydantic_settings import BaseSettings
from pydantic import BaseModel, model_validator
from datetime import datetime
from typing import List, Optional
import yaml
from dotenv import load_dotenv
from .constants import Interval

load_dotenv()


class SignalConfig(BaseModel):
    """Signal generation configuration."""
    intervals: List[Interval]
    tickers: List[str]
    strategies: List[str]


class ModelConfig(BaseModel):
    """LLM model configuration."""
    name: str
    provider: str
    base_url: Optional[str] = None
    temperature: Optional[float] = 0.0
    format: Optional[str] = "json"


class Config(BaseSettings):
    """Main configuration class."""
    mode: str  # "backtest" or "live"
    start_date: datetime
    end_date: datetime
    primary_interval: Interval
    initial_cash: float
    margin_requirement: float = 0.0
    show_reasoning: bool = False
    show_agent_graph: bool = True
    signals: SignalConfig
    model: ModelConfig

    @model_validator(mode='after')
    def validate_primary_interval(self):
        """Ensure primary interval is in the intervals list."""
        if self.primary_interval not in self.signals.intervals:
            raise ValueError(
                f"primary_interval '{self.primary_interval}' must be in signals.intervals"
            )
        return self


def load_config(config_path: str = "config.yaml") -> Config:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config YAML file
        
    Returns:
        Config object
    """
    with open(config_path, "r") as f:
        yaml_data = yaml.safe_load(f)
    return Config(**yaml_data)

