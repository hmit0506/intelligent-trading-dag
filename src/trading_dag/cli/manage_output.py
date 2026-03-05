#!/usr/bin/env python3
"""
Convenience script for managing output files.
Usage: python -m trading_dag.cli.manage_output [command] [options]
"""
import sys
from trading_dag.utils.file_manager import OutputFileManager


def main():
    """Simple CLI for file management."""
    if len(sys.argv) < 2:
        print("Usage: python -m trading_dag.cli.manage_output [command]")
        print("\nCommands:")
        print("  list          - List all output files")
        print("  summary       - Show file summary")
        print("  cleanup       - Clean up old files (keeps latest 10, deletes >30 days)")
        print("  delete-all    - Delete all files (use with caution!)")
        print("  delete-logs   - Delete all log files")
        print("  delete-json   - Delete all JSON files")
        print("  delete-csv    - Delete all CSV files")
        print("\nExamples:")
        print("  python -m trading_dag.cli.manage_output list")
        print("  python -m trading_dag.cli.manage_output summary")
        print("  python -m trading_dag.cli.manage_output cleanup")
        return

    command = sys.argv[1].lower()
    manager = OutputFileManager()

    if command == "list":
        manager.print_file_list()
    elif command == "summary":
        manager.print_summary()
    elif command == "cleanup":
        print("Cleaning up old files...")
        results = manager.cleanup_old_files()
        print(f"\nCleaned up:")
        for ftype, count in results.items():
            print(f"  {ftype}: {count} files")
    elif command == "delete-all":
        confirm = input("Are you sure you want to delete ALL files? (yes/no): ")
        if confirm.lower() == "yes":
            count, names = manager.delete_files()
            print(f"\nDeleted {count} files")
        else:
            print("Cancelled.")
    elif command == "delete-logs":
        count, names = manager.delete_files(file_type="log")
        print(f"\nDeleted {count} log files")
    elif command == "delete-json":
        count, names = manager.delete_files(file_type="json")
        print(f"\nDeleted {count} JSON files")
    elif command == "delete-csv":
        count, names = manager.delete_files(file_type="csv")
        print(f"\nDeleted {count} CSV files")
    else:
        print(f"Unknown command: {command}")
        print("Use 'python -m trading_dag.cli.manage_output' to see available commands")


if __name__ == "__main__":
    main()
