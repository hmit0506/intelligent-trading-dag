"""
Configuration management.
"""
from pydantic_settings import BaseSettings
from pydantic import BaseModel, ConfigDict, model_validator
from datetime import datetime
from typing import List, Optional
import yaml
from pathlib import Path

from dotenv import load_dotenv
from trading_dag.utils.constants import Interval

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
