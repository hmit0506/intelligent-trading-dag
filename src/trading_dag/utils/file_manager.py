"""
File management utilities for output artifacts (logs, JSON, CSV).

Supports a single directory (legacy) or the standard layout: *backtest*, *benchmark*,
*live* under ``output_layout.root`` (see ``resolve_output_dirs``).
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from colorama import Fore, Style, init

from trading_dag.utils.output_layout import ResolvedOutputDirs, resolve_output_dirs

init(autoreset=True)


def output_file_manager_for_layout(dirs: ResolvedOutputDirs) -> "OutputFileManager":
    """Manage files across all three artifact subfolders (backtest / benchmark / live)."""
    return OutputFileManager(
        artifact_roots=[
            ("backtest", dirs.backtest),
            ("benchmark", dirs.benchmark),
            ("live", dirs.live),
        ],
    )


class OutputFileManager:
    """
    Manage output files under one directory or under labeled artifact roots (layout subfolders).

    When *artifact_roots* is set, ``list_files`` / cleanup aggregate non-recursive files
    in each root (same behavior as before, but across ``backtest/``, ``benchmark/``, ``live/``).
    """

    def __init__(
        self,
        output_dir: Optional[str] = None,
        *,
        artifact_roots: Optional[List[Tuple[str, Path]]] = None,
    ) -> None:
        if artifact_roots is not None:
            self.roots: List[Tuple[str, Path]] = [
                (label, Path(p).expanduser().resolve()) for label, p in artifact_roots
            ]
        elif output_dir is not None:
            p = Path(output_dir).expanduser().resolve()
            self.roots = [(p.name, p)]
        else:
            p = Path("output").expanduser().resolve()
            self.roots = [(p.name, p)]

    @classmethod
    def from_config(cls, cwd: Path, config_path: str) -> "OutputFileManager":
        """Load ``output_layout`` from YAML and scan all three subfolders under the artifact root."""
        from trading_dag.utils.config import load_config

        cfg = load_config(config_path)
        dirs = resolve_output_dirs(cwd, cfg.output_layout)
        return output_file_manager_for_layout(dirs)

    def list_files(self, file_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List output files, optionally filtered by type.

        Each entry includes ``bucket`` (subfolder label) and ``display_name`` (``bucket/filename``).
        """
        files: List[Dict[str, Any]] = []

        for bucket, root in self.roots:
            if not root.is_dir():
                continue
            for file_path in root.iterdir():
                if not file_path.is_file():
                    continue

                suffix = file_path.suffix.lower()
                if suffix == ".log":
                    ftype = "log"
                elif suffix == ".json":
                    ftype = "json"
                elif suffix == ".csv":
                    ftype = "csv"
                else:
                    ftype = "other"

                if file_type and ftype != file_type:
                    continue

                stat = file_path.stat()
                size_mb = stat.st_size / (1024 * 1024)

                files.append(
                    {
                        "path": file_path,
                        "name": file_path.name,
                        "bucket": bucket,
                        "display_name": f"{bucket}/{file_path.name}",
                        "type": ftype,
                        "size_mb": size_mb,
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime),
                        "created": datetime.fromtimestamp(stat.st_ctime),
                    }
                )

        files.sort(key=lambda x: x["modified"], reverse=True)
        return files

    def get_file_summary(self) -> Dict[str, Any]:
        """Summary statistics across all scanned roots."""
        all_files = self.list_files()

        summary: Dict[str, Any] = {
            "total_files": len(all_files),
            "total_size_mb": sum(f["size_mb"] for f in all_files),
            "by_type": {},
            "by_bucket": {},
            "roots": [{"bucket": b, "path": str(p)} for b, p in self.roots],
        }

        for file_info in all_files:
            ftype = file_info["type"]
            if ftype not in summary["by_type"]:
                summary["by_type"][ftype] = {"count": 0, "size_mb": 0.0}
            summary["by_type"][ftype]["count"] += 1
            summary["by_type"][ftype]["size_mb"] += file_info["size_mb"]

            bkt = file_info["bucket"]
            if bkt not in summary["by_bucket"]:
                summary["by_bucket"][bkt] = {"count": 0, "size_mb": 0.0}
            summary["by_bucket"][bkt]["count"] += 1
            summary["by_bucket"][bkt]["size_mb"] += file_info["size_mb"]

        return summary

    def delete_files(
        self,
        file_type: Optional[str] = None,
        older_than_days: Optional[int] = None,
        keep_latest: Optional[int] = None,
        dry_run: bool = False,
    ) -> Tuple[int, List[str]]:
        files = self.list_files(file_type=file_type)
        files_to_delete: List[Dict[str, Any]] = []

        if keep_latest is not None:
            files_to_delete = files[keep_latest:]
        elif older_than_days is not None:
            cutoff_date = datetime.now().timestamp() - (older_than_days * 24 * 60 * 60)
            files_to_delete = [f for f in files if f["modified"].timestamp() < cutoff_date]
        else:
            files_to_delete = files

        deleted_count = 0
        deleted_names: List[str] = []

        for file_info in files_to_delete:
            if not dry_run:
                try:
                    file_info["path"].unlink()
                    deleted_count += 1
                    deleted_names.append(file_info["display_name"])
                except OSError as e:
                    print(f"{Fore.RED}Error deleting {file_info['display_name']}: {e}{Style.RESET_ALL}")
            else:
                deleted_count += 1
                deleted_names.append(file_info["display_name"])

        return deleted_count, deleted_names

    def cleanup_old_files(
        self,
        max_age_days: int = 30,
        keep_latest: int = 10,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """Per file type: drop old files while keeping at least *keep_latest* newest overall."""
        results: Dict[str, int] = {}

        for file_type in ["log", "json", "csv"]:
            files = self.list_files(file_type=file_type)

            if len(files) <= keep_latest:
                results[file_type] = 0
                continue

            cutoff_date = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
            old_files = [f for f in files if f["modified"].timestamp() < cutoff_date]

            if len(old_files) > len(files) - keep_latest:
                old_files = files[keep_latest:]

            deleted_count = 0
            for file_info in old_files:
                if not dry_run:
                    try:
                        file_info["path"].unlink()
                        deleted_count += 1
                    except OSError as e:
                        print(f"{Fore.RED}Error deleting {file_info['display_name']}: {e}{Style.RESET_ALL}")
                else:
                    deleted_count += 1

            results[file_type] = deleted_count

        return results

    def print_summary(self) -> None:
        summary = self.get_file_summary()

        print(f"\n{Fore.WHITE}{Style.BRIGHT}OUTPUT FILES SUMMARY{Style.RESET_ALL}")
        print("=" * 80)
        print(f"Roots: {Fore.CYAN}{', '.join(f'{b}={p}' for b, p in self.roots)}{Style.RESET_ALL}")
        print(f"Total Files: {Fore.CYAN}{summary['total_files']}{Style.RESET_ALL}")
        print(f"Total Size: {Fore.CYAN}{summary['total_size_mb']:.2f} MB{Style.RESET_ALL}")
        print("\nBy bucket:")
        for bkt, stats in summary.get("by_bucket", {}).items():
            print(
                f"  {Fore.MAGENTA}{bkt}{Style.RESET_ALL}: "
                f"{Fore.CYAN}{stats['count']}{Style.RESET_ALL} files, "
                f"{Fore.CYAN}{stats['size_mb']:.2f} MB{Style.RESET_ALL}"
            )
        print("\nBy type:")
        for ftype, stats in summary["by_type"].items():
            print(
                f"  {Fore.YELLOW}{ftype.upper()}{Style.RESET_ALL}: "
                f"{Fore.CYAN}{stats['count']}{Style.RESET_ALL} files, "
                f"{Fore.CYAN}{stats['size_mb']:.2f} MB{Style.RESET_ALL}"
            )

    def print_file_list(self, file_type: Optional[str] = None, limit: int = 40) -> None:
        files = self.list_files(file_type=file_type)

        if not files:
            print(f"{Fore.YELLOW}No files found.{Style.RESET_ALL}")
            return

        print(f"\n{Fore.WHITE}{Style.BRIGHT}OUTPUT FILES{Style.RESET_ALL}")
        print("=" * 80)
        print(f"{'Type':<8} {'Bucket':<12} {'Size (MB)':<12} {'Modified':<20} {'File'}")
        print("-" * 80)

        for file_info in files[:limit]:
            ftype_color = {
                "log": Fore.RED,
                "json": Fore.GREEN,
                "csv": Fore.BLUE,
            }.get(file_info["type"], Fore.WHITE)

            print(
                f"{ftype_color}{file_info['type']:<8}{Style.RESET_ALL} "
                f"{Fore.MAGENTA}{file_info['bucket']:<12}{Style.RESET_ALL} "
                f"{file_info['size_mb']:<12.2f} "
                f"{file_info['modified'].strftime('%Y-%m-%d %H:%M:%S'):<20} "
                f"{file_info['display_name']}"
            )

        if len(files) > limit:
            print(f"\n{Fore.YELLOW}... and {len(files) - limit} more files{Style.RESET_ALL}")


def main() -> None:
    """CLI interface for file management (``python -m trading_dag.utils.file_manager``)."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage output files under output_layout")
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Trading config YAML (provides output_layout); default: config/config.yaml",
    )
    parser.add_argument(
        "--subdir",
        choices=["all", "backtest", "benchmark", "live"],
        default="all",
        help="Limit to one artifact subfolder (default: all three)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Single directory to scan (overrides --config layout)",
    )
    parser.add_argument("--list", action="store_true", help="List files")
    parser.add_argument("--summary", action="store_true", help="Show summary")
    parser.add_argument("--type", choices=["log", "json", "csv"], help="Filter by type")
    parser.add_argument("--delete-all", action="store_true", help="Delete all matching files")
    parser.add_argument("--delete-type", choices=["log", "json", "csv"], help="Delete by type")
    parser.add_argument("--delete-older-than", type=int, metavar="DAYS", help="Delete older than N days")
    parser.add_argument("--keep-latest", type=int, metavar="N", help="Keep N newest per list+type filter")
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Retention cleanup (default: keep 10 latest per type, drop older than 30 days)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not delete")

    args = parser.parse_args()

    if args.output_dir:
        manager = OutputFileManager(output_dir=args.output_dir)
    else:
        from trading_dag.utils.config import load_config

        cfg_path = Path(args.config)
        if not cfg_path.is_file():
            print(f"{Fore.RED}Config not found: {cfg_path}{Style.RESET_ALL}")
            raise SystemExit(1)
        cfg = load_config(str(cfg_path))
        dirs = resolve_output_dirs(Path.cwd(), cfg.output_layout)
        mapping = {
            "all": [("backtest", dirs.backtest), ("benchmark", dirs.benchmark), ("live", dirs.live)],
            "backtest": [("backtest", dirs.backtest)],
            "benchmark": [("benchmark", dirs.benchmark)],
            "live": [("live", dirs.live)],
        }
        manager = OutputFileManager(artifact_roots=mapping[args.subdir])

    has_action = any(
        [
            args.summary,
            args.list,
            args.delete_all,
            args.delete_type,
            args.delete_older_than,
            args.keep_latest is not None,
            args.cleanup,
        ]
    )
    if not has_action:
        parser.print_help()
        return

    if args.summary:
        manager.print_summary()

    if args.list:
        manager.print_file_list(file_type=args.type)

    if args.delete_all:
        if not args.dry_run:
            confirm = input(
                f"{Fore.RED}Delete ALL listed files under managed roots? (yes/no): {Style.RESET_ALL}"
            )
            if confirm.lower() != "yes":
                print("Cancelled.")
                return
        count, names = manager.delete_files(file_type=args.type, dry_run=args.dry_run)
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"\n{Fore.GREEN}{action} {count} files{Style.RESET_ALL}")

    if args.delete_type:
        count, names = manager.delete_files(file_type=args.delete_type, dry_run=args.dry_run)
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"\n{Fore.GREEN}{action} {count} {args.delete_type} files{Style.RESET_ALL}")

    if args.delete_older_than:
        count, names = manager.delete_files(
            file_type=args.type,
            older_than_days=args.delete_older_than,
            dry_run=args.dry_run,
        )
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"\n{Fore.GREEN}{action} {count} files older than {args.delete_older_than} days{Style.RESET_ALL}")

    if args.keep_latest is not None:
        count, names = manager.delete_files(
            keep_latest=args.keep_latest,
            file_type=args.type,
            dry_run=args.dry_run,
        )
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"\n{Fore.GREEN}{action} {count} files (keeping {args.keep_latest} latest){Style.RESET_ALL}")

    if args.cleanup:
        results = manager.cleanup_old_files(dry_run=args.dry_run)
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"\n{Fore.GREEN}{action} files:{Style.RESET_ALL}")
        for ftype, count in results.items():
            print(f"  {ftype}: {count} files")


if __name__ == "__main__":
    main()
