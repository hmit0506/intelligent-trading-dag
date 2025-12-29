"""
Backtest entry point.
Uses unified TradingSystemRunner for consistency.
"""
import os
import sys
from dotenv import load_dotenv
from utils.config import load_config
from core.runner import TradingSystemRunner

# Add parent directory to path to access gateway
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

load_dotenv()

if __name__ == "__main__":
    config = load_config("config.yaml")

    if config.mode != "backtest":
        print("Please set mode to 'backtest' in config.yaml")
        sys.exit(1)

    # Use unified runner
    runner = TradingSystemRunner(config)
    results = runner.run()
    
    print("\nBacktest completed successfully.")

