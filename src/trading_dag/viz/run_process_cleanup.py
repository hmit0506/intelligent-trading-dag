"""Terminate Streamlit-spawned trading_dag CLI processes (including orphans)."""
from __future__ import annotations

import subprocess
from pathlib import Path

_CLI_MARKERS = (
    "trading_dag.cli.main",
    "trading_dag.cli.backtest",
    "trading_dag.cli.benchmark_phase1",
    "trading_dag.cli.benchmark_phase2",
)


def _pkill_full_command(pattern: str, sig: str) -> None:
    try:
        subprocess.run(
            ["pkill", sig, "-f", pattern],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except Exception:
        pass


def _pgrep_lines(pattern: str) -> list[str]:
    try:
        res = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False,
        )
        out = (res.stdout or "").strip()
        if not out:
            return []
        return [ln.strip() for ln in out.splitlines() if ln.strip()]
    except Exception:
        return []


def pkill_patterns_until_clear(patterns: list[str], *, aggressive: bool = True) -> str | None:
    """Send TERM then KILL to each pattern; return an error message if anything still matches."""
    seq = ("-TERM", "-KILL") if aggressive else ("-TERM",)
    for pat in patterns:
        if not pat.strip():
            continue
        for sig in seq:
            _pkill_full_command(pat, sig)
    leftover: list[str] = []
    for pat in patterns:
        if not pat.strip():
            continue
        if _pgrep_lines(pat):
            leftover.append(pat)
    if leftover:
        return "Processes still matched patterns after stop: " + "; ".join(leftover[:5])
    return None


def benchmark_suite_patterns(cfg_path: Path) -> list[str]:
    cfg_s = str(cfg_path.resolve())
    return [
        f"trading_dag.cli.benchmark_phase1 --config {cfg_s}",
        f"trading_dag.cli.benchmark_phase2 --config {cfg_s}",
    ]


def backtest_pattern(cfg_path: Path) -> str:
    cfg_s = str(cfg_path.resolve())
    return f"trading_dag.cli.backtest --config {cfg_s} --mode-override backtest"


def live_pattern(cfg_path: Path) -> str:
    cfg_s = str(cfg_path.resolve())
    return f"trading_dag.cli.main --config {cfg_s} --mode-override live"


def kill_benchmark_suite_for_config(cfg_path: Path) -> str | None:
    return pkill_patterns_until_clear(benchmark_suite_patterns(cfg_path))


def kill_backtest_for_config(cfg_path: Path) -> str | None:
    return pkill_patterns_until_clear([backtest_pattern(cfg_path)])


def kill_live_for_config(cfg_path: Path) -> str | None:
    return pkill_patterns_until_clear([live_pattern(cfg_path)])


def kill_all_trading_dag_cli_processes() -> str | None:
    """
    Kill every local process whose command line matches a trading_dag CLI module.

    This is intentionally broad (may affect other clones on the same machine).
    """
    leftover: list[str] = []
    for sig in ("-TERM", "-KILL"):
        for marker in _CLI_MARKERS:
            _pkill_full_command(marker, sig)
    for marker in _CLI_MARKERS:
        if _pgrep_lines(marker):
            leftover.append(marker)
    if leftover:
        return "Still running (by command match): " + ", ".join(leftover)
    return None
