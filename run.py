#!/usr/bin/env python3
"""
Convenience launcher for the trading system.
Run: python run.py (live mode) or python run.py --backtest
"""
import sys

if __name__ == "__main__":
    if "--backtest" in sys.argv or "-b" in sys.argv:
        from trading_dag.cli.backtest import main
    else:
        from trading_dag.cli.main import main
    main()
