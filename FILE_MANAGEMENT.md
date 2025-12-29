# Output File Management Guide

## Overview

The trading system generates various output files in the `output/` directory:
- **Log files** (`.log`): Backtest execution logs
- **JSON files** (`.json`): Trade logs and decision history
- **CSV files** (`.csv`): Performance data

This guide explains how to manage and clean up these files.

## File Types

### Backtest Files
- `backtest_YYYYMMDD_HHMMSS.log` - Execution log
- `backtest_trades_YYYYMMDD_HHMMSS.json` - Detailed trade log
- `backtest_performance_YYYYMMDD_HHMMSS.csv` - Performance metrics over time

### Live Mode Files
- `live_decisions_YYYYMMDD_HHMMSS.json` - Decision history with timestamps

## Using the File Manager CLI

### List Files

```bash
# List all files
python -m utils.file_manager --list

# List only JSON files
python -m utils.file_manager --list --type json

# List only CSV files
python -m utils.file_manager --list --type csv

# List only log files
python -m utils.file_manager --list --type log
```

### View Summary

```bash
# Show summary statistics
python -m utils.file_manager --summary
```

### Delete Files

#### Delete All Files
```bash
# Dry run (preview what would be deleted)
python -m utils.file_manager --delete-all --dry-run

# Actually delete all files
python -m utils.file_manager --delete-all
```

#### Delete by Type
```bash
# Delete all JSON files
python -m utils.file_manager --delete-type json

# Delete all CSV files
python -m utils.file_manager --delete-type csv

# Delete all log files
python -m utils.file_manager --delete-type log
```

#### Delete Old Files
```bash
# Delete files older than 7 days
python -m utils.file_manager --delete-older-than 7

# Delete files older than 30 days (dry run)
python -m utils.file_manager --delete-older-than 30 --dry-run
```

#### Keep Only Latest Files
```bash
# Keep only the 5 latest files (delete the rest)
python -m utils.file_manager --keep-latest 5

# Keep only the 10 latest JSON files
python -m utils.file_manager --keep-latest 10 --type json
```

#### Automatic Cleanup
```bash
# Clean up old files (keeps latest 10, deletes older than 30 days)
python -m utils.file_manager --cleanup

# Preview cleanup (dry run)
python -m utils.file_manager --cleanup --dry-run
```

## Configuration-Based Auto-Cleanup

You can enable automatic file cleanup in `config.yaml`:

```yaml
# File management options
auto_cleanup_files: true      # Automatically clean up old files
file_retention_days: 30      # Delete files older than 30 days
file_keep_latest: 10         # Always keep at least 10 latest files
```

When enabled, the system will automatically clean up old files before each run.

## Examples

### Example 1: Clean up old logs
```bash
# Delete log files older than 7 days
python -m utils.file_manager --delete-type log --delete-older-than 7
```

### Example 2: Keep only recent files
```bash
# Keep only the 5 most recent files of each type
python -m utils.file_manager --keep-latest 5 --type json
python -m utils.file_manager --keep-latest 5 --type csv
python -m utils.file_manager --keep-latest 5 --type log
```

### Example 3: Full cleanup
```bash
# 1. View current files
python -m utils.file_manager --summary

# 2. Preview what would be deleted
python -m utils.file_manager --cleanup --dry-run

# 3. Actually clean up
python -m utils.file_manager --cleanup
```

### Example 4: Manual cleanup script
```bash
#!/bin/bash
# cleanup.sh - Clean up old output files

# Delete files older than 30 days
python -m utils.file_manager --delete-older-than 30

# Keep only latest 10 files of each type
python -m utils.file_manager --keep-latest 10 --type json
python -m utils.file_manager --keep-latest 10 --type csv
python -m utils.file_manager --keep-latest 10 --type log

# Show summary
python -m utils.file_manager --summary
```

## Python API Usage

You can also use the file manager programmatically:

```python
from utils.file_manager import OutputFileManager

# Initialize manager
manager = OutputFileManager("output")

# List all files
files = manager.list_files()

# List only JSON files
json_files = manager.list_files(file_type="json")

# Get summary
summary = manager.get_file_summary()
print(f"Total files: {summary['total_files']}")
print(f"Total size: {summary['total_size_mb']:.2f} MB")

# Delete files older than 7 days
count, names = manager.delete_files(older_than_days=7)
print(f"Deleted {count} files")

# Keep only latest 10 files
count, names = manager.delete_files(keep_latest=10)
print(f"Deleted {count} files, kept 10 latest")

# Automatic cleanup
results = manager.cleanup_old_files(
    max_age_days=30,
    keep_latest=10
)
print(f"Cleaned up: {results}")
```

## File Naming Convention

Files are named with timestamps in the format: `YYYYMMDD_HHMMSS`

Examples:
- `backtest_20250115_143022.log` - Created on Jan 15, 2025 at 14:30:22
- `backtest_trades_20250115_143022.json` - Trade log from same run
- `live_decisions_20250115_150000.json` - Live decisions at 15:00:00

## Best Practices

1. **Regular Cleanup**: Set up automatic cleanup or run manual cleanup regularly
2. **Keep Important Files**: Use `--keep-latest` to preserve recent files
3. **Monitor Disk Usage**: Use `--summary` to check total file size
4. **Dry Run First**: Always use `--dry-run` before deleting files
5. **Backup Important Data**: Export important results before cleanup

## Troubleshooting

### Files Not Found
If files are not found, check:
- The `output/` directory exists
- File permissions allow reading
- Files match the expected naming pattern

### Permission Errors
If you get permission errors:
- Check file permissions: `ls -la output/`
- Ensure you have write permissions to delete files
- On Windows, ensure files are not open in another program

### Large File Sizes
If files are very large:
- Consider reducing `print_frequency` in config
- Use `--delete-older-than` to remove old files
- Consider archiving old files instead of deleting

