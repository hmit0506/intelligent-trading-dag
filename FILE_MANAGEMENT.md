# Output File Management Guide

## Overview

The trading system generates various output files in the `output/` directory:
- **Log files** (`.log`): Backtest execution logs
- **JSON files** (`.json`): Trade logs and decision history
- **CSV files** (`.csv`): Performance data
- **PNG files** (`.png`): Portfolio value charts

This guide explains how to manage and clean up these files using the built-in file management tools.

## File Types

### Backtest Files
- `backtest_YYYYMMDD_HHMMSS.log` - Execution log
- `backtest_trades_YYYYMMDD_HHMMSS.json` - Detailed trade log
- `backtest_performance_YYYYMMDD_HHMMSS.csv` - Performance metrics over time
- `backtest_portfolio_value_YYYYMMDD_HHMMSS.png` - Portfolio value chart

### Live Mode Files
- `live_decisions_YYYYMMDD_HHMMSS.json` - Decision history with timestamps

## Quick Start

### Method 1: Simple Commands (Recommended for Beginners)

Use `manage_output.py` for quick and easy file management:

#### View Files

```bash
# List all files
uv run python manage_output.py list

# Show summary statistics
uv run python manage_output.py summary
```

**Output Example:**
```
OUTPUT FILES SUMMARY
Total Files: 4
Total Size: 0.11 MB

By Type:
  CSV: 1 files, 0.00 MB
  JSON: 1 files, 0.01 MB
  PNG: 1 files, 0.10 MB
  LOG: 1 files, 0.00 MB
```

#### Clean Up Files

```bash
# Clean up old files (keeps latest 10, deletes >30 days)
uv run python manage_output.py cleanup

# Delete all log files
uv run python manage_output.py delete-logs

# Delete all JSON files
uv run python manage_output.py delete-json

# Delete all CSV files
uv run python manage_output.py delete-csv

# Delete ALL files (use with caution!)
uv run python manage_output.py delete-all
```

### Method 2: Advanced Commands (Full Control)

Use `utils.file_manager` module for advanced options:

#### List Files

```bash
# List all files
uv run python -m utils.file_manager --list

# List only JSON files
uv run python -m utils.file_manager --list --type json

# List only CSV files
uv run python -m utils.file_manager --list --type csv

# List only log files
uv run python -m utils.file_manager --list --type log
```

#### View Summary

```bash
uv run python -m utils.file_manager --summary
```

#### Delete Files with Conditions

```bash
# Delete files older than 7 days
uv run python -m utils.file_manager --delete-older-than 7

# Keep only the 5 latest files (delete the rest)
uv run python -m utils.file_manager --keep-latest 5

# Keep only the 10 latest JSON files
uv run python -m utils.file_manager --keep-latest 10 --type json

# Delete all JSON files
uv run python -m utils.file_manager --delete-type json
```

#### Safe Preview (Dry Run)

Always preview before deleting:

```bash
# Preview what would be deleted
uv run python -m utils.file_manager --cleanup --dry-run

# Preview keeping only latest 5 files
uv run python -m utils.file_manager --keep-latest 5 --dry-run

# Preview deleting files older than 7 days
uv run python -m utils.file_manager --delete-older-than 7 --dry-run
```

## Common Use Cases

### Use Case 1: Check Current Files

```bash
# Quick summary
uv run python manage_output.py summary

# Detailed list
uv run python manage_output.py list
```

### Use Case 2: Clean Up Old Files

```bash
# Automatic cleanup (recommended)
uv run python manage_output.py cleanup
```

This will:
- Keep the 10 latest files of each type
- Delete files older than 30 days
- Show what was deleted

### Use Case 3: Keep Only Recent Files

```bash
# Keep only the 5 most recent files
uv run python -m utils.file_manager --keep-latest 5
```

### Use Case 4: Delete Specific File Types

```bash
# Delete all log files (they're usually large)
uv run python manage_output.py delete-logs

# Delete all JSON files
uv run python manage_output.py delete-json

# Delete all CSV files
uv run python manage_output.py delete-csv
```

### Use Case 5: Delete Old Files

```bash
# Delete files older than 7 days
uv run python -m utils.file_manager --delete-older-than 7

# Preview first (recommended)
uv run python -m utils.file_manager --delete-older-than 7 --dry-run
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

## Python API Usage

You can also use the file manager programmatically:

```python
from utils.file_manager import OutputFileManager

# Initialize manager
manager = OutputFileManager("output")

# List all files
files = manager.list_files()
for f in files:
    print(f"{f['name']}: {f['size_mb']:.2f} MB")

# List only JSON files
json_files = manager.list_files(file_type="json")

# Get summary
summary = manager.get_file_summary()
print(f"Total: {summary['total_files']} files, {summary['total_size_mb']:.2f} MB")

# Delete files older than 7 days
count, names = manager.delete_files(older_than_days=7)
print(f"Deleted {count} files")

# Keep only latest 10 files
count, names = manager.delete_files(keep_latest=10)
print(f"Kept 10 latest, deleted {count} files")

# Automatic cleanup
results = manager.cleanup_old_files(
    max_age_days=30,
    keep_latest=10
)
print(f"Cleaned up: {results}")
```

## File Naming Convention

Files are named with timestamps in the format: `TYPE_YYYYMMDD_HHMMSS.ext`

Examples:
- `backtest_20251229_174633.log` - Log from Dec 29, 2025 at 17:46:33
- `backtest_trades_20251229_174730.json` - Trade log from same run
- `backtest_performance_20251229_174730.csv` - Performance data
- `backtest_portfolio_value_20251229_174719.png` - Portfolio value chart
- `live_decisions_20251229_150000.json` - Live decisions at 15:00:00

## Best Practices

1. **Always Preview First**: Use `--dry-run` before deleting
   ```bash
   uv run python -m utils.file_manager --cleanup --dry-run
   ```

2. **Regular Cleanup**: Set up automatic cleanup in `config.yaml`
   ```yaml
   auto_cleanup_files: true
   file_retention_days: 30
   file_keep_latest: 10
   ```

3. **Check Before Deleting**: Always check what files exist first
   ```bash
   uv run python manage_output.py summary
   ```

4. **Keep Important Data**: Export important results before cleanup
   - JSON files contain detailed trade logs
   - CSV files contain performance data
   - PNG files contain charts

5. **Use Type-Specific Deletion**: Delete by type when you know what you want
   ```bash
   uv run python manage_output.py delete-logs  # Only logs
   ```

## Examples

### Example 1: Daily Cleanup Script

```bash
#!/bin/bash
# daily_cleanup.sh

echo "Cleaning up old output files..."
uv run python manage_output.py cleanup

echo "Current files:"
uv run python manage_output.py summary
```

### Example 2: Keep Only Latest 5 Files

```bash
# Preview first
uv run python -m utils.file_manager --keep-latest 5 --dry-run

# Actually delete
uv run python -m utils.file_manager --keep-latest 5
```

### Example 3: Archive Old Files Before Cleanup

```bash
# 1. Check current files
uv run python manage_output.py summary

# 2. Archive important files (manual step)
mkdir -p archive/$(date +%Y%m%d)
cp output/*.json archive/$(date +%Y%m%d)/

# 3. Clean up
uv run python manage_output.py cleanup
```

### Example 4: Full Cleanup Workflow

```bash
# 1. View current files
uv run python manage_output.py summary

# 2. Preview what would be deleted
uv run python -m utils.file_manager --cleanup --dry-run

# 3. Actually clean up
uv run python manage_output.py cleanup

# 4. Verify cleanup
uv run python manage_output.py summary
```

## Quick Reference

### Simple Commands

| Command | Description |
|---------|-------------|
| `manage_output.py list` | List all files |
| `manage_output.py summary` | Show statistics |
| `manage_output.py cleanup` | Auto cleanup |
| `manage_output.py delete-logs` | Delete log files |
| `manage_output.py delete-json` | Delete JSON files |
| `manage_output.py delete-csv` | Delete CSV files |
| `manage_output.py delete-all` | Delete everything |

### Advanced Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview without deleting |
| `--keep-latest N` | Keep N latest files |
| `--delete-older-than N` | Delete files older than N days |
| `--type {log,json,csv}` | Filter by file type |
| `--output-dir PATH` | Specify output directory |

## Troubleshooting

### Files Not Found

If files are not found, check:
- The `output/` directory exists
- File permissions allow reading
- Files match the expected naming pattern

```bash
# Check if output directory exists
ls -la output/

# List files with detailed info
uv run python manage_output.py list
```

### Permission Errors

If you get permission errors:
- Check file permissions: `ls -la output/`
- Ensure you have write permissions to delete files
- On Windows, ensure files are not open in another program

```bash
# Check file permissions
ls -la output/

# Try with explicit path
uv run python -m utils.file_manager --output-dir output --list
```

### Large File Sizes

If files are very large:
- Consider reducing `print_frequency` in config
- Use `--delete-older-than` to remove old files
- Consider archiving old files instead of deleting

```bash
# Check which files are large
uv run python manage_output.py summary

# Delete old large files
uv run python -m utils.file_manager --delete-older-than 7
```

## See Also

- [README.md](README.md) - Main project documentation
- [README_CN.md](README_CN.md) - 中文文档
