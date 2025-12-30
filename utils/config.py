"""
Configuration management.
"""
from pydantic_settings import BaseSettings
from pydantic import BaseModel, ConfigDict, model_validator
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
    format: Optional[str] = "json"  # Only "json" format is supported
    
    @model_validator(mode='after')
    def validate_format(self):
        """Ensure format is 'json' (only JSON format is supported)."""
        if self.format and self.format != "json":
            raise ValueError(
                f"format must be 'json' (got '{self.format}'). Only JSON format is supported."
            )
        return self


class Config(BaseSettings):
    """Main configuration class."""
    model_config = ConfigDict(extra="allow")  # Allow extra fields for backward compatibility
    
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
    
    # Performance and output options
    print_frequency: int = 1  # Print results every N iterations
    use_progress_bar: bool = True  # Show progress bar during backtest
    enable_logging: bool = True  # Generate log files
    
    # Live mode options
    save_decision_history: bool = True  # Save decision history to JSON file
    
    # File management options
    auto_cleanup_files: bool = False  # Automatically clean up old files
    file_retention_days: int = 30  # Delete files older than N days
    file_keep_latest: int = 10  # Always keep at least N latest files

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

