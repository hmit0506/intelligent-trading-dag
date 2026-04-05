#!/usr/bin/env python3
"""
CLI for listing and cleaning artifact files under ``output_layout`` (backtest / benchmark / live).

Usage examples:

  uv run trading-dag-manage-output list
  uv run trading-dag-manage-output summary --subdir backtest
  uv run trading-dag-manage-output cleanup --config config/config.yaml
  uv run trading-dag-manage-output delete-json --subdir benchmark

Single-directory override (legacy):

  uv run trading-dag-manage-output list --output-dir path/to/folder
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from colorama import Fore, Style, init

from trading_dag.utils.config import load_config
from trading_dag.utils.file_manager import OutputFileManager
from trading_dag.utils.output_layout import resolve_output_dirs

init(autoreset=True)


def _build_manager(args: argparse.Namespace) -> OutputFileManager:
    if getattr(args, "output_dir", None):
        return OutputFileManager(output_dir=args.output_dir)
    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        print(f"{Fore.RED}Config not found: {cfg_path}{Style.RESET_ALL}", file=sys.stderr)
        raise SystemExit(1)
    cfg = load_config(str(cfg_path))
    dirs = resolve_output_dirs(Path.cwd(), cfg.output_layout)
    mapping = {
        "all": [("backtest", dirs.backtest), ("benchmark", dirs.benchmark), ("live", dirs.live)],
        "backtest": [("backtest", dirs.backtest)],
        "benchmark": [("benchmark", dirs.benchmark)],
        "live": [("live", dirs.live)],
    }
    return OutputFileManager(artifact_roots=mapping[args.subdir])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage output files under config output_layout (backtest / benchmark / live)."
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="YAML with output_layout (default: config/config.yaml)",
    )
    parser.add_argument(
        "--subdir",
        choices=["all", "backtest", "benchmark", "live"],
        default="all",
        help="Limit to one artifact subfolder (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Scan a single directory instead of using config output_layout",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["list", "summary", "cleanup", "delete-all", "delete-logs", "delete-json", "delete-csv"],
        help="Action to run",
    )

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        raise SystemExit(0)

    manager = _build_manager(args)

    if args.command == "list":
        manager.print_file_list()
    elif args.command == "summary":
        manager.print_summary()
    elif args.command == "cleanup":
        max_age = 30
        keep_latest = 10
        if not args.output_dir:
            cfg = load_config(str(Path(args.config)))
            max_age = getattr(cfg, "file_retention_days", 30)
            keep_latest = getattr(cfg, "file_keep_latest", 10)
        print(
            f"Cleaning up (older than {max_age} days, keep {keep_latest} latest per type)..."
        )
        results = manager.cleanup_old_files(max_age_days=max_age, keep_latest=keep_latest)
        print("\nCleaned up:")
        for ftype, count in results.items():
            print(f"  {ftype}: {count} files")
    elif args.command == "delete-all":
        confirm = input(f"{Fore.RED}Delete ALL files under managed roots? (yes/no): {Style.RESET_ALL}")
        if confirm.lower() != "yes":
            print("Cancelled.")
            return
        count, _ = manager.delete_files()
        print(f"\nDeleted {count} files")
    elif args.command == "delete-logs":
        count, _ = manager.delete_files(file_type="log")
        print(f"\nDeleted {count} log files")
    elif args.command == "delete-json":
        count, _ = manager.delete_files(file_type="json")
        print(f"\nDeleted {count} JSON files")
    elif args.command == "delete-csv":
        count, _ = manager.delete_files(file_type="csv")
        print(f"\nDeleted {count} CSV files")


if __name__ == "__main__":
    main()
