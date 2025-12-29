# 输出文件管理指南

## 概述

交易系统会在 `output/` 目录中生成各种输出文件：
- **日志文件** (`.log`)：回测执行日志
- **JSON文件** (`.json`)：交易日志和决策历史
- **CSV文件** (`.csv`)：性能数据
- **PNG文件** (`.png`)：投资组合价值图表

本指南介绍如何使用内置的文件管理工具来管理和清理这些文件。

## 文件类型

### 回测文件
- `backtest_YYYYMMDD_HHMMSS.log` - 执行日志
- `backtest_trades_YYYYMMDD_HHMMSS.json` - 详细交易日志
- `backtest_performance_YYYYMMDD_HHMMSS.csv` - 性能指标时间序列
- `backtest_portfolio_value_YYYYMMDD_HHMMSS.png` - 投资组合价值图表

### 实盘模式文件
- `live_decisions_YYYYMMDD_HHMMSS.json` - 带时间戳的决策历史

## 快速开始

### 方法 1：简单命令（推荐新手使用）

使用 `manage_output.py` 进行快速简单的文件管理：

#### 查看文件

```bash
# 列出所有文件
uv run python manage_output.py list

# 显示统计摘要
uv run python manage_output.py summary
```

**输出示例：**
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

#### 清理文件

```bash
# 清理旧文件（保留最新10个，删除30天前的）
uv run python manage_output.py cleanup

# 删除所有日志文件
uv run python manage_output.py delete-logs

# 删除所有JSON文件
uv run python manage_output.py delete-json

# 删除所有CSV文件
uv run python manage_output.py delete-csv

# 删除所有文件（请谨慎使用！）
uv run python manage_output.py delete-all
```

### 方法 2：高级命令（完全控制）

使用 `utils.file_manager` 模块进行高级操作：

#### 列出文件

```bash
# 列出所有文件
uv run python -m utils.file_manager --list

# 只列出JSON文件
uv run python -m utils.file_manager --list --type json

# 只列出CSV文件
uv run python -m utils.file_manager --list --type csv

# 只列出日志文件
uv run python -m utils.file_manager --list --type log
```

#### 查看摘要

```bash
uv run python -m utils.file_manager --summary
```

#### 按条件删除文件

```bash
# 删除7天前的文件
uv run python -m utils.file_manager --delete-older-than 7

# 只保留最新的5个文件（删除其余的）
uv run python -m utils.file_manager --keep-latest 5

# 只保留最新的10个JSON文件
uv run python -m utils.file_manager --keep-latest 10 --type json

# 删除所有JSON文件
uv run python -m utils.file_manager --delete-type json
```

#### 安全预览（Dry Run）

删除前始终先预览：

```bash
# 预览将要删除的文件
uv run python -m utils.file_manager --cleanup --dry-run

# 预览只保留最新5个文件的操作
uv run python -m utils.file_manager --keep-latest 5 --dry-run

# 预览删除7天前文件的操作
uv run python -m utils.file_manager --delete-older-than 7 --dry-run
```

## 常见使用场景

### 场景 1：查看当前文件

```bash
# 快速摘要
uv run python manage_output.py summary

# 详细列表
uv run python manage_output.py list
```

### 场景 2：清理旧文件

```bash
# 自动清理（推荐）
uv run python manage_output.py cleanup
```

这将：
- 保留每种类型的最新10个文件
- 删除30天前的文件
- 显示已删除的文件

### 场景 3：只保留最新文件

```bash
# 只保留最新的5个文件
uv run python -m utils.file_manager --keep-latest 5
```

### 场景 4：删除特定类型的文件

```bash
# 删除所有日志文件（通常比较大）
uv run python manage_output.py delete-logs

# 删除所有JSON文件
uv run python manage_output.py delete-json

# 删除所有CSV文件
uv run python manage_output.py delete-csv
```

### 场景 5：删除旧文件

```bash
# 删除7天前的文件
uv run python -m utils.file_manager --delete-older-than 7

# 先预览（推荐）
uv run python -m utils.file_manager --delete-older-than 7 --dry-run
```

## 基于配置的自动清理

你可以在 `config.yaml` 中启用自动文件清理：

```yaml
# 文件管理选项
auto_cleanup_files: true      # 自动清理旧文件
file_retention_days: 30      # 删除30天前的文件
file_keep_latest: 10         # 至少保留10个最新文件
```

启用后，系统会在每次运行前自动清理旧文件。

## Python API 使用

你也可以通过编程方式使用文件管理器：

```python
from utils.file_manager import OutputFileManager

# 初始化管理器
manager = OutputFileManager("output")

# 列出所有文件
files = manager.list_files()
for f in files:
    print(f"{f['name']}: {f['size_mb']:.2f} MB")

# 只列出JSON文件
json_files = manager.list_files(file_type="json")

# 获取摘要
summary = manager.get_file_summary()
print(f"总计: {summary['total_files']} 个文件, {summary['total_size_mb']:.2f} MB")

# 删除7天前的文件
count, names = manager.delete_files(older_than_days=7)
print(f"删除了 {count} 个文件")

# 只保留最新10个文件
count, names = manager.delete_files(keep_latest=10)
print(f"保留10个最新文件，删除了 {count} 个文件")

# 自动清理
results = manager.cleanup_old_files(
    max_age_days=30,
    keep_latest=10
)
print(f"清理结果: {results}")
```

## 文件命名规范

文件使用时间戳命名，格式为：`TYPE_YYYYMMDD_HHMMSS.ext`

示例：
- `backtest_20251229_174633.log` - 2025年12月29日 17:46:33 创建的日志
- `backtest_trades_20251229_174730.json` - 同一次运行的交易日志
- `backtest_performance_20251229_174730.csv` - 性能数据
- `backtest_portfolio_value_20251229_174719.png` - 投资组合价值图表
- `live_decisions_20251229_150000.json` - 15:00:00 的实盘决策

## 最佳实践

1. **始终先预览**：删除前使用 `--dry-run`
   ```bash
   uv run python -m utils.file_manager --cleanup --dry-run
   ```

2. **定期清理**：在 `config.yaml` 中设置自动清理
   ```yaml
   auto_cleanup_files: true
   file_retention_days: 30
   file_keep_latest: 10
   ```

3. **删除前检查**：删除前始终先查看有哪些文件
   ```bash
   uv run python manage_output.py summary
   ```

4. **保留重要数据**：清理前导出重要结果
   - JSON文件包含详细的交易日志
   - CSV文件包含性能数据
   - PNG文件包含图表

5. **使用类型特定删除**：明确要删除的类型时使用
   ```bash
   uv run python manage_output.py delete-logs  # 只删除日志
   ```

## 示例

### 示例 1：每日清理脚本

```bash
#!/bin/bash
# daily_cleanup.sh

echo "正在清理旧输出文件..."
uv run python manage_output.py cleanup

echo "当前文件："
uv run python manage_output.py summary
```

### 示例 2：只保留最新5个文件

```bash
# 先预览
uv run python -m utils.file_manager --keep-latest 5 --dry-run

# 实际删除
uv run python -m utils.file_manager --keep-latest 5
```

### 示例 3：清理前归档旧文件

```bash
# 1. 查看当前文件
uv run python manage_output.py summary

# 2. 归档重要文件（手动步骤）
mkdir -p archive/$(date +%Y%m%d)
cp output/*.json archive/$(date +%Y%m%d)/

# 3. 清理
uv run python manage_output.py cleanup
```

### 示例 4：完整清理流程

```bash
# 1. 查看当前文件
uv run python manage_output.py summary

# 2. 预览将要删除的文件
uv run python -m utils.file_manager --cleanup --dry-run

# 3. 实际清理
uv run python manage_output.py cleanup

# 4. 验证清理结果
uv run python manage_output.py summary
```

## 快速参考

### 简单命令

| 命令 | 描述 |
|-----|------|
| `manage_output.py list` | 列出所有文件 |
| `manage_output.py summary` | 显示统计信息 |
| `manage_output.py cleanup` | 自动清理 |
| `manage_output.py delete-logs` | 删除日志文件 |
| `manage_output.py delete-json` | 删除JSON文件 |
| `manage_output.py delete-csv` | 删除CSV文件 |
| `manage_output.py delete-all` | 删除所有文件 |

### 高级选项

| 选项 | 描述 |
|-----|------|
| `--dry-run` | 预览不删除 |
| `--keep-latest N` | 保留最新N个文件 |
| `--delete-older-than N` | 删除N天前的文件 |
| `--type {log,json,csv}` | 按文件类型过滤 |
| `--output-dir PATH` | 指定输出目录 |

## 故障排除

### 找不到文件

如果找不到文件，请检查：
- `output/` 目录是否存在
- 文件权限是否允许读取
- 文件是否匹配预期的命名模式

```bash
# 检查输出目录是否存在
ls -la output/

# 列出文件的详细信息
uv run python manage_output.py list
```

### 权限错误

如果遇到权限错误：
- 检查文件权限：`ls -la output/`
- 确保你有删除文件的写权限
- 在Windows上，确保文件没有在其他程序中打开

```bash
# 检查文件权限
ls -la output/

# 使用显式路径尝试
uv run python -m utils.file_manager --output-dir output --list
```

### 文件过大

如果文件非常大：
- 考虑在配置中减少 `print_frequency`
- 使用 `--delete-older-than` 删除旧文件
- 考虑归档旧文件而不是删除

```bash
# 检查哪些文件较大
uv run python manage_output.py summary

# 删除旧的较大文件
uv run python -m utils.file_manager --delete-older-than 7
```

## 相关文档

- [README.md](README.md) - 项目主文档
- [README_CN.md](README_CN.md) - 中文文档

