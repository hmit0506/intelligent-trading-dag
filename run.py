#!/usr/bin/env python3
"""
Convenience launcher for the trading system.
Run: python run.py (live mode), python run.py --backtest,
or python run.py --benchmark-phase1 / --benchmark-phase2
"""
import sys

if __name__ == "__main__":
    if "--benchmark-phase2" in sys.argv:
        sys.argv = [arg for arg in sys.argv if arg != "--benchmark-phase2"]
        from trading_dag.cli.benchmark_phase2 import main
    elif "--benchmark-phase1" in sys.argv:
        sys.argv = [arg for arg in sys.argv if arg != "--benchmark-phase1"]
        from trading_dag.cli.benchmark_phase1 import main
    elif "--backtest" in sys.argv or "-b" in sys.argv:
        sys.argv = [arg for arg in sys.argv if arg not in ("--backtest", "-b")]
        from trading_dag.cli.backtest import main
    else:
        from trading_dag.cli.main import main
    main()
