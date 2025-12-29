# 基于模块化DAG的加密货币交易智能信号融合系统

一个先进的加密货币交易系统，利用模块化有向无环图（DAG）架构融合多个交易信号，并使用大语言模型（LLM）做出智能交易决策。

## 概述

本系统采用LangGraph创建灵活的工作流，市场数据通过专门的节点进行多时间框架分析、技术指标计算、风险管理和AI驱动的投资组合决策。

## 核心特性

- **模块化DAG架构**：清晰的功能分离，包含数据获取、信号生成、风险管理和投资组合管理的专门节点
- **多策略支持**：结合多种交易策略（MACD、RSI、布林带）进行加权信号融合
- **多时间框架分析**：同时分析多个时间间隔（1分钟、5分钟、1小时、4小时等）以生成稳健信号
- **AI增强决策**：使用LLM（OpenAI、Groq、Anthropic、Ollama等）进行复杂的投资组合管理决策
- **全面回测**：具有详细指标和可视化的历史性能评估
- **风险管理**：使用固定分数头寸规模方法的内置头寸规模和风险控制
- **统一运行器**：回测和实盘模式的统一入口，提供一致的接口
- **进度跟踪**：实时进度条和可配置的输出频率
- **文件管理**：自动导出结果（CSV/JSON）和内置文件清理工具
- **增强输出**：详细的投资组合信息、决策历史和性能指标

## 架构

系统使用包含以下节点的DAG工作流：

1. **StartNode**：初始化工作流
2. **DataNode**：获取每个指定时间框架的市场数据
3. **MergeNode**：合并多时间框架数据
4. **策略节点**（MacdStrategy、RSIStrategy、BollingerStrategy）：应用技术分析
5. **RiskManagementNode**：计算头寸规模和风险参数
6. **PortfolioManagementNode**：使用LLM推理做出最终交易决策

## 项目结构

```
.
├── gateway/           # 币安API客户端（独立）
├── core/              # 核心框架（状态、节点、工作流）
├── nodes/             # 工作流节点
├── strategies/        # 交易策略
├── backtest/          # 回测引擎
├── data/              # 数据提供者（币安）
├── indicators/        # 技术指标
├── llm/               # LLM集成
├── utils/             # 工具和配置
│   └── file_manager.py  # 输出文件管理工具
├── core/              # 核心框架
│   └── runner.py      # 统一交易系统运行器
├── main.py            # 统一入口（支持两种模式）
├── backtest.py        # 回测入口（兼容旧版本，使用统一运行器）
├── manage_output.py   # 文件管理便捷脚本
├── config.yaml        # 配置文件
└── output/            # 输出目录（日志、JSON、CSV文件）
```

**注意**：本项目完全独立，不需要原始项目目录。

## 安装

### 前置要求

- Python 3.12 或更高版本
- 币安账户（用于市场数据访问）

### 设置

1. 进入项目目录：
```bash
cd new_project
```

2. 使用uv设置（推荐）：
```bash
# 如果没有uv，先安装
curl -fsSL https://install.lunarvim.org/uv.sh | sh

# 创建虚拟环境并安装依赖
uv sync

# 激活虚拟环境（如需要）
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate  # Windows
```

或使用标准Python：
```bash
# 创建虚拟环境
python3.12 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

3. 配置环境变量：
```bash
cp env.example .env
# 编辑.env文件，填入你的API密钥
```

必需的环境变量：
```
BINANCE_API_KEY=your-binance-api-key
BINANCE_API_SECRET=your-binance-api-secret
OPENAI_API_KEY=your-openai-key  # 如果使用OpenAI或兼容API（如DeepSeek）
GROQ_API_KEY=your-groq-key      # 如果使用Groq
# ... 其他LLM提供商的密钥
```

**重要提示**：
- 对于OpenAI兼容的API（如DeepSeek），使用 `OPENAI_API_KEY` 并在 `config.yaml` 中设置相应的 `base_url`
- 获取币安API密钥：https://www.binance.com/en/my/settings/api-management
- 从你选择的提供商网站获取LLM API密钥

4. 配置系统（核心步骤）：

**配置是项目的核心组件！**

```bash
# 创建config.yaml
cp config.example.yaml config.yaml
# 编辑config.yaml设置你的参数

# 创建.env文件
cp env.example .env
# 编辑.env填入你的API密钥
```

**注意**：`config.yaml` 和 `.env` 文件都是系统运行所必需的。

## 配置

编辑 `config.yaml`：

```yaml
mode: backtest  # 或 "live"
start_date: 2025-01-01
end_date: 2025-02-01
primary_interval: 1h
initial_cash: 100000
margin_requirement: 0.0
show_reasoning: false
show_agent_graph: true
signals:
  intervals: ["1h", "4h"]
  tickers: ["BTCUSDT", "ETHUSDT"]
  strategies: ["MacdStrategy", "RSIStrategy", "BollingerStrategy"]
model:
  name: "gpt-4o-mini"
  provider: "openai"
  base_url: null
  temperature: 0.0
  format: "json"
```

## 使用方法

### 快速开始

1. **运行系统**（模式由 `config.yaml` 决定）：
```bash
uv run main.py
# 或
python main.py
```

系统会自动根据 `config.yaml` 检测模式：
- 如果 `mode: backtest` → 运行回测，显示进度条和详细指标
- 如果 `mode: live` → 运行实盘模式，显示投资组合和决策历史

2. **运行特定模式**：
```bash
# 回测模式
uv run backtest.py
# 或
python backtest.py

# 实盘模式
uv run main.py  # （在config.yaml中设置 mode: live）
# 或
python main.py
```

### 输出文件

所有输出文件保存在 `output/` 目录：
- **日志文件** (`.log`)：回测执行日志
- **JSON文件** (`.json`)：交易日志和决策历史
- **CSV文件** (`.csv`)：性能数据

管理输出文件：
```bash
# 列出所有输出文件
python manage_output.py list

# 显示摘要
python manage_output.py summary

# 清理旧文件
python manage_output.py cleanup

# 详细用法请参阅 FILE_MANAGEMENT.md
```

### 回测模式

回测模式将：
1. 获取指定日期范围的历史数据
2. 为每个时间段运行DAG工作流，显示进度条
3. 根据生成的信号执行模拟交易
4. 计算并显示性能指标（回报率、夏普比率、索提诺比率、最大回撤）
5. 自动导出结果到CSV和JSON文件
6. 生成日志文件用于详细分析

**增强功能**：
- 显示回测进度的进度条
- 可配置的打印频率以减少I/O开销
- 自动导出交易日志和性能数据
- 生成日志文件用于调试

### 实盘模式

实盘模式将：
1. 获取当前市场数据
2. 运行DAG工作流
3. 生成交易信号
4. 显示增强的投资组合信息和决策：
   - 当前现金余额和保证金使用情况
   - 投资组合总价值和收益率
   - 当前持仓（多/空）及市场价格
   - 交易决策及置信度
   - 所有策略的分析师信号
5. 保存决策历史到JSON文件

**注意**：本系统仅生成信号，不执行实际交易。使用风险自负。

## 添加新策略

1. 在 `strategies/` 目录创建新的策略文件：

```python
from core.node import BaseNode
from core.state import AgentState
from typing import Dict, Any
import json
from langchain_core.messages import HumanMessage

class MyStrategy(BaseNode):
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        data = state.get("data", {})
        data['name'] = "MyStrategy"
        
        # 你的策略逻辑
        technical_analysis = {}
        
        message = HumanMessage(
            content=json.dumps(technical_analysis),
            name="my_strategy_agent",
        )
        
        data["analyst_signals"]["my_strategy_agent"] = technical_analysis
        
        return {
            "messages": [message],
            "data": data,
        }
```

2. 在 `strategies/__init__.py` 中注册
3. 在 `config.yaml` 的 `signals.strategies` 中添加

## 支持的LLM提供商

- OpenAI（gpt-4o、gpt-4o-mini等）
- Groq
- OpenRouter
- Google Gemini
- Anthropic Claude
- Ollama（本地模型）

## 性能指标

回测器提供：
- 总回报百分比
- 夏普比率
- 索提诺比率
- 最大回撤
- 胜率和盈亏比
- 最大连续盈利/亏损次数
- 逐笔交易日志（导出为JSON）
- 投资组合价值随时间变化（导出为CSV）
- 实时进度跟踪（进度条）

## 文件管理

系统会在 `output/` 目录自动生成输出文件。使用文件管理工具进行清理：

```bash
# 快速命令
python manage_output.py list      # 列出所有文件
python manage_output.py summary  # 显示统计信息
python manage_output.py cleanup  # 清理旧文件

# 高级用法
python -m utils.file_manager --help
```

详细文档请参阅 [FILE_MANAGEMENT.md](FILE_MANAGEMENT.md)。

## 配置选项

`config.yaml` 中的新配置选项：

```yaml
# 性能和输出选项
print_frequency: 1        # 每N次迭代打印一次
use_progress_bar: true    # 显示进度条
enable_logging: true      # 生成日志文件
save_decision_history: true  # 保存决策历史

# 文件管理
auto_cleanup_files: false     # 自动清理旧文件
file_retention_days: 30      # 删除N天前的文件
file_keep_latest: 10         # 至少保留N个最新文件
```

## 故障排除

### 导入错误
- 确保虚拟环境已激活
- 运行 `uv pip sync` 或 `pip install -r requirements.txt` 安装所有依赖

### API认证错误
- 检查 `.env` 文件中的API密钥是否正确（不是占位符值）
- 对于OpenAI兼容的API（DeepSeek等），确保设置了 `OPENAI_API_KEY`
- 验证 `config.yaml` 中的 `base_url` 与你的提供商匹配

### 策略加载错误
- 确保 `config.yaml` 中的策略名称与类名完全匹配（区分大小写）
- 策略文件应在 `strategies/` 目录中，类名匹配

### 配置错误
- 确保 `primary_interval` 在 `signals.intervals` 列表中
- `config.yaml` 和 `.env` 文件必须存在并正确配置

## 许可证

MIT许可证

版权所有 (c) 2025 FYP25019 Team  
版权所有 (c) 2025 qashi (https://github.com/hmit0506)

本项目基于原始作品：
版权所有 (c) 2025 51bitquant (ai-hedge-fund-crypto)

完整许可证文本和归属详情请参阅 [LICENSE](LICENSE) 文件。

## 贡献者

- [qashi](https://github.com/hmit0506) - 项目负责人和初始实现
- FYP25019 团队 - 开发团队

## 致谢

本项目是对原始 
[ai-hedge-fund-crypto](https://github.com/51bitquant/ai-hedge-fund-crypto) 
项目的完整重写和扩展，该项目由 51bitquant 开发，采用 MIT 许可证。

虽然本实现已进行了重大重构和增强，但它保持了原始工作的核心架构概念和设计原则。
我们感谢并赞赏原始作者提供的基础工作。

**原始仓库**: https://github.com/51bitquant/ai-hedge-fund-crypto  
**原始许可证**: MIT许可证  
**原始版权**: 版权所有 (c) 2025 51bitquant

## 免责声明

本项目按"原样"提供，不提供任何保证。使用风险自负。加密货币交易涉及重大损失风险。

