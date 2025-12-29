"""
Main entry point for live trading mode and backtest mode.
Uses unified TradingSystemRunner for consistent interface.
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
    
    # Create unified runner
    runner = TradingSystemRunner(config)
    
    # Run the trading system
    results = runner.run()
    
    print("\nExecution completed successfully.")

