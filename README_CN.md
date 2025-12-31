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
- **历史数据预热**：自动在回测开始日期之前获取额外的历史数据，确保技术指标从第一个数据点就能正确工作
- **初始持仓支持**：回测和实盘模式都支持从现有持仓（多/空）开始，而不仅仅是现金
- **交易所集成**：实盘模式可以自动从币安交易所账户同步投资组合
- **统一决策机制**：回测和实盘模式使用相同的决策逻辑，确保结果一致（无未来价格预测）
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
├── core/              # 核心框架（状态、节点、工作流、运行器）
│   ├── node.py        # 基础节点类
│   ├── state.py       # Agent状态管理
│   ├── workflow.py    # 工作流创建
│   └── runner.py      # 统一交易系统运行器
├── nodes/             # 工作流节点
├── strategies/        # 交易策略
├── backtest/          # 回测引擎
├── data/              # 数据提供者（币安）
├── indicators/        # 技术指标
├── llm/               # LLM集成
├── utils/             # 工具和配置
│   └── file_manager.py  # 输出文件管理工具
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
cd intelligent-trading-dag
```

2. 使用uv设置（推荐）：
```bash
# 如果没有uv，先安装
curl -LsSf https://astral.sh/uv/install.sh | sh

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
- **DeepSeek 设置**：
  - 使用 `OPENAI_API_KEY` 环境变量（从 https://platform.deepseek.com/ 获取API密钥）
  - 在 `config.yaml` 中设置 `provider: "openai"` 和 `base_url: "https://api.deepseek.com/v1"`
  - 模型名称：`"deepseek-chat"` 或 `"deepseek-chat-32k"`
- 获取币安API密钥：https://www.binance.com/en/my/settings/api-management
- 从你选择的提供商网站获取LLM API密钥

4. 配置系统：
```bash
cp config.example.yaml config.yaml
# 编辑config.yaml设置你的参数
```

**注意**：`config.yaml` 和 `.env` 文件都是系统运行所必需的。

## 配置

**配置是项目的核心组件！**

```yaml
mode: backtest  # 或 "live"
start_date: 2025-01-01
end_date: 2025-02-01
primary_interval: 1h
initial_cash: 100000
margin_requirement: 0.0
show_reasoning: false
show_agent_graph: true

# 性能和输出选项
print_frequency: 1        # 每N次迭代打印一次
use_progress_bar: true    # 显示进度条
enable_logging: true      # 生成日志文件
save_decision_history: true  # 保存决策历史

# 文件管理选项
auto_cleanup_files: false     # 自动清理旧文件
file_retention_days: 30      # 删除N天前的文件
file_keep_latest: 10         # 至少保留N个最新文件

# 投资组合初始化（回测和实盘模式都支持）
# 选项1：从交易所同步（仅实盘模式，需要BINANCE_API_KEY和BINANCE_API_SECRET）
sync_from_exchange: false  # 设置为true以从币安账户同步投资组合

# 选项2：手动初始持仓（回测和实盘模式都支持）
# 注意：成本基础自动使用历史/实时价格设置
# initial_positions:
#   cash: 100000  # 可选：覆盖initial_cash
#   positions:
#     BTCUSDT:
#       long: 0.1  # 多头持仓数量
#       short: 0.0  # 空头持仓数量
#     ETHUSDT:
#       long: 2.0

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

# DeepSeek 配置示例：
# model:
#   name: "deepseek-chat"
#   provider: "openai"
#   base_url: "https://api.deepseek.com/v1"
#   temperature: 0.0
#   format: "json"
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

# 详细用法请参阅 [FILE_MANAGEMENT_CN.md](FILE_MANAGEMENT_CN.md)
```

### 回测模式

回测模式将：
1. 初始化投资组合（如果配置了初始持仓，则使用初始持仓，否则仅使用现金）
2. 获取指定日期范围的历史数据（包含预热期以确保技术指标有足够数据）
3. 为每个时间段运行DAG工作流，显示进度条
4. 根据生成的信号执行模拟交易
5. 计算并显示性能指标（回报率、夏普比率、索提诺比率、最大回撤）
6. 自动导出结果到CSV和JSON文件
7. 生成日志文件用于详细分析

**核心功能**：
- 历史数据预热，确保技术指标从第一个数据点就准确
- 初始持仓支持（成本基础自动从市场价格设置）
- 基于初始投资组合价值的准确收益率计算
- 进度跟踪、可配置输出和自动结果导出

### 实盘模式

实盘模式将：
1. 初始化投资组合（从交易所同步、手动配置或仅使用现金）
2. 获取当前市场数据
3. 运行DAG工作流
4. 生成交易信号
5. 显示当前投资组合状态和交易决策：
   - 当前现金余额和持仓
   - 当前投资组合价值
   - 交易决策及置信度
   - 所有策略的详细分析师信号（包含技术指标）
6. 保存决策历史到JSON文件

**投资组合初始化选项**：
- **从交易所同步**：自动从币安获取当前余额和持仓（需要API密钥）
- **手动配置**：在`config.yaml`中指定初始持仓（成本基础自动从市场价格设置）
- **仅现金**：仅使用初始现金开始（默认）

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
- DeepSeek（通过OpenAI兼容API）
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

## 可视化

### 投资组合价值图表
- **生成时机**：回测完成后自动生成
- **保存位置**：`output/backtest_portfolio_value_YYYYMMDD_HHMMSS.png`
- **格式**：高分辨率 PNG（300 DPI）
- **内容**：投资组合价值随时间变化，包含网格和标签

### Agent 工作流图
- **生成时机**：Agent 初始化时生成（如果 `show_agent_graph: true`）
- **保存位置**：项目根目录
- **格式**：PNG 文件
- **文件名**：`{strategy1}_{strategy2}_..._graph.png`
- **内容**：DAG 工作流结构，显示节点和连接关系

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

详细文档请参阅 [FILE_MANAGEMENT_CN.md](FILE_MANAGEMENT_CN.md)。

## 配置选项

详细示例请参阅上方的配置部分。主要选项包括：

- **投资组合初始化**：从交易所同步或手动持仓（成本基础自动设置）
- **性能选项**：打印频率、进度条、日志记录
- **文件管理**：自动清理、保留策略

## 技术细节

### 数据流和执行

**回测模式**：
- 数据范围由`config.yaml`中的`start_date`和`end_date`定义
- 为每个间隔至少获取500根K线，如果整个日期范围需要的K线数超过500根，则获取整个范围
- 根据日期范围和间隔时长计算所需的K线数
- 过滤数据，仅使用`start_date`到`end_date`范围内的点进行回测迭代
- 每个数据点触发完整的工作流执行：
  1. DataNode获取到当前时间点的历史数据
  2. 所有策略并行执行，分析所有交易对和时间间隔
  3. RiskManagementNode计算头寸规模
  4. PortfolioManagementNode使用LLM做出最终决策
- 决策在回测模式中立即执行

**实盘模式**：
- 从币安API按需获取实时数据
- 使用与回测相同的决策机制（无未来价格预测）
- 仅生成决策（不执行交易）
- 可以从交易所同步投资组合或使用配置的初始持仓

**统一决策机制**：
- 两种模式使用相同的决策逻辑，基于当前信号和价格
- 无未来价格预测，确保行为一致
- LLM分析当前市场条件，仅生成"现在"时间点的决策

### 策略执行

每个策略：
- 接收历史数据序列（非单个数据点）用于技术指标计算
- 并行分析所有配置的交易对和时间间隔
- 生成带置信度分数（0-100%）的信号
- 信号被聚合并由PortfolioManagementNode用于最终决策

### 历史数据获取

回测和实盘模式使用相似的数据获取机制：
- **实盘模式**：为每个配置的间隔获取恰好500根K线，以当前时间结束
- **回测模式**：至少获取500根K线，如果整个日期范围需要的K线数超过500根，则获取整个范围
  - 根据`start_date`到`end_date`的范围计算所需的K线数
  - 使用`max(500, required_k_lines)`确保有足够的数据覆盖
  - 过滤仅使用`start_date`到`end_date`范围内的数据进行迭代
- 这确保了技术指标计算的足够历史数据，同时保持效率

## 故障排除

### 导入错误
- 确保虚拟环境已激活
- 运行 `uv sync` 或 `pip install -r requirements.txt` 安装所有依赖

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

### 数据问题
- 如果回测显示数据不足，请检查 `start_date` 和 `end_date` 是否有效
- 回测模式自动获取足够的数据以覆盖整个日期范围（至少500根K线）
- 实盘模式为每个间隔获取恰好500根K线
- 确保币安API可访问以获取数据
- 对于实盘模式，请确保API密钥具有账户余额同步的读取权限

## 许可证

MIT许可证

版权所有 (c) 2025 FYP25019 Team  
版权所有 (c) 2025 Shi Qian (https://github.com/hmit0506)

本项目基于原始作品：
版权所有 (c) 2025 51bitquant (ai-hedge-fund-crypto)

完整许可证文本和归属详情请参阅 [LICENSE](LICENSE) 文件。

## 贡献者

- [Shi Qian](https://github.com/hmit0506) - 项目负责人和初始实现
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

