# 基于模块化DAG的加密货币交易智能信号融合系统

一个先进的加密货币交易系统，利用模块化有向无环图（DAG）架构融合多个交易信号，并使用大语言模型（LLM）做出智能交易决策。

## 概述

本系统采用LangGraph创建灵活的工作流，市场数据通过专门的节点进行多时间框架分析、技术指标计算、风险管理和AI驱动的投资组合决策。

## 核心特性

- **模块化DAG架构**：清晰的功能分离，包含数据获取、信号生成、风险管理和投资组合管理的专门节点
- **多策略支持**：结合多种交易策略（MACD、RSI、布林带）进行加权信号融合
- **多时间框架分析**：同时分析多个时间间隔（1分钟、5分钟、1小时、4小时等）以生成稳健信号
- **主要间隔优先级**：LLM决策优先考虑主要间隔的信号，同时将其他间隔作为补充信息
- **AI增强决策**：使用LLM（OpenAI、Groq、Anthropic、Ollama等）进行复杂的投资组合管理决策，具有明确的间隔权重指导
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
├── src/trading_dag/   # 主包（Python友好的下划线命名）
│   ├── cli/           # CLI入口（main, backtest, manage_output）
│   ├── core/          # 状态、节点、工作流、运行器
│   ├── nodes/         # 工作流节点
│   ├── strategies/    # 交易策略
│   ├── backtest/      # 回测引擎
│   ├── data/          # 数据提供者（币安）
│   ├── gateway/       # 币安API客户端
│   ├── indicators/    # 技术指标
│   ├── llm/           # LLM集成
│   └── utils/         # 配置和工具
├── config/            # 配置文件
│   ├── config.yaml    # 主配置（从 config.example.yaml 复制）
│   └── config.example.yaml
├── tests/             # 单元和集成测试
├── output/            # 生成的文件（日志、JSON、CSV）
├── run.py             # 便捷启动脚本
└── pyproject.toml     # 包配置和依赖
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
cp .env.example .env
# 编辑 .env 文件，填入你的API密钥
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
cp config/config.example.yaml config/config.yaml
# 编辑 config/config.yaml 设置你的参数
```

**注意**：`config/config.yaml` 和 `.env` 文件都是系统运行所必需的。

## 配置

**配置是项目的核心组件！**

```yaml
mode: backtest  # 或 "live"
start_date: 2025-01-01
end_date: 2025-02-01
primary_interval: 1h  # 决策的主要间隔。如果未在signals.intervals中列出，将自动添加。LLM优先考虑此间隔的信号。
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
# 起始现金写在 initial_positions.cash（仍兼容旧版顶层 initial_cash）。
# 注意：成本基础自动使用历史/实时价格设置
initial_positions:
  cash: 100000
#   positions:
#     BTCUSDT:
#       long: 0.1  # 多头持仓数量
#       short: 0.0  # 空头持仓数量
#     ETHUSDT:
#       long: 2.0

signals:
  intervals: ["1h", "4h"]  # 要分析的所有间隔。如果primary_interval未列出，将自动包含。
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
uv run python run.py
# 或
python run.py
```

系统会自动根据 `config.yaml` 检测模式：
- 如果 `mode: backtest` → 运行回测，显示进度条和详细指标
- 如果 `mode: live` → 运行实盘模式，显示投资组合和决策历史

2. **运行特定模式**：
```bash
# 回测模式
uv run python run.py --backtest
# 或
python run.py --backtest

# 实盘模式
uv run python run.py  # （在config.yaml中设置 mode: live）
# 或
python run.py
```

3. **运行 Phase 1 基准对照套件**（Full DAG + 单策略组 + 强基线组）：
```bash
# 可选：先创建统一 benchmark 配置
cp config/benchmark.example.yaml config/benchmark.yaml

# 使用 run.py 统一入口
uv run python run.py --benchmark-phase1
# 或
python run.py --benchmark-phase1

# 或直接调用 CLI
uv run python -m trading_dag.cli.benchmark_phase1 --config config/benchmark.yaml
```

4. **运行 Phase 2 基准套件**（DAG 消融：每次只关一个子系统，与完整管线对照）：
```bash
uv run python run.py --benchmark-phase2
# 或
python run.py --benchmark-phase2

uv run python -m trading_dag.cli.benchmark_phase2 --config config/benchmark.yaml
```

### Phase 1 基准：原理与实现要点

**研究目的。** Phase 1 回答的是**整体 vs 分解**问题：在相同行情、资金与配置下，**完整多策略 DAG 管线**与「(a) 只启用**单一策略**的同一套回测引擎」以及「(b) **不走 DAG 的简单基线**」相比，行为与指标有何差异？目标不是证明在所有市场都最优，而是展示**集成框架**是否与「单模块抽取」和「朴素对照」有系统性差别，便于写进 FYP 的方法与实验章节。

**控制变量。** 所有 DAG 类实验（`FullDAG`、`SingleMACD`、`SingleRSI`、`SingleBollinger`）共用同一个 `Backtester` / `Agent`：`main` 中的日期、`signals.tickers`、`initial_positions`、保证金与 LLM（`model`）、以及 `signals.intervals` 均一致。`phase1_registry.py` 里每个 `DagExperimentSpec` **只改策略列表**，从而把差异归因到「图里激活了哪些策略节点」，数据加载与组合记账方式保持一致。

**DAG 实验组含义。**

- **FullDAG** — 使用配置中的完整 `strategies`（如 MACD + RSI + Bollinger）。各策略节点仍汇入既有风控与组合节点，与日常回测拓扑一致。
- **单策略变体** — 工作流中仍包含风控与组合层，但**仅注册一个**策略类。检验的是：在同一执行与决策外壳下，**单一指标族**相对**多源融合**的表现，而不是把指标拆到完全独立脚本里跑。

**非 DAG 基线。** 实现在 `baseline_simulators.py`，由 `get_phase1_baseline_registry()` 驱动：

- **买入并持有** — 期初一次性配置权重后静态持有，不读策略信号、不调 LLM。
- **等权定期再平衡** — 按 `rebalance_every_bars`（以 `primary_interval` 的 K 线为单位）调回各标的名义权重近似相等。

二者提供**可解释、易向答辩委员会说明**的对照，而非宣称其为「强模型下界」。

**指标与产物。** 每条权益曲线来自回测器组合价值或基线仿真；`equity_metrics.build_equity_metrics` 计算收益、Sharpe、Sortino、回撤、胜率等。汇总表按收益排序仅为速览；**正式报告**中仍应单独讨论显著性、成本敏感性、多窗口稳健性等（本 README 不替代统计小节）。

**代码结构。** `phase1.py` 负责 Phase 1 编排；共享的基线执行与 CSV 导出在 `suite_common.py`。`phase1_registry.py` 定义实验名与策略列表；单次 DAG 回测通过 `dag_backtest_runner.run_dag_backtest_experiment`（Phase 1 使用默认完整管线）。基线与 K 线准备见 `baseline_simulators.py`。结果类型见 `experiment_types.py`；历史模块名 `phase1_models` / `phase1_metrics` / `phase1_baselines` 仍为兼容重导出。

**使用提示。** 编排入口 `run_phase1_benchmarks(...)`；配置用 `config/benchmark.yaml` 的 `main` + `phase1`（须 `mode: backtest`）；`phase1.dag_print_frequency` / `dag_use_progress_bar` 控制日志；`include_dag_experiments`、`include_baseline_experiments` 可选子集；`export_individual_results` 可逐实验导出。**输出：** `output/benchmark_phase1_summary_*.csv`、`benchmark_phase1_equity_*.csv`。

**写作注意。** LLM 组合层仍受提供商、账户与提示词版本影响（示例中温度常为 0，但仍非数学确定性）。单策略跑法**仍经过相同风控与组合节点**，因此对比的是「策略集合」而非「裸指标脚本」。基线完全不执行 DAG，权益曲线形态与 DAG 实验不可直接等同。

---

### Phase 2 基准：消融原理与实现要点

**研究目的。** Phase 2 回答的是**模块必要性**：在其余设计尽量不变时，**拿掉 DAG 中的一类机制**（多周期、LLM 组合、或结构化风控 sizing）绩效与风险特征如何变化？这是典型的**单因素消融**：注册表里每次默认只关一个维度，并保留 `FullDAG` 作参照；**组合消融**（同时关两项）需自行在 `phase2_registry.py` 增加条目。

**参照组 `FullDAG`。** 与 Phase 1 全策略一致，且 `DAGAblationSettings` 全为默认：多周期数据路径、组合节点走 **LLM**、风控走**完整**分支（含 `risk.py` 中基于止损距离等的头寸逻辑）。

**各消融在实现上的含义（与论文表述对应）。**

| 实验名 | 报告可写的设计理念 | 实现要点 |
|--------|----------------------|----------|
| `Ablate_MultiInterval` | 去掉辅助周期，仅保留主周期信息 | `Backtester` 仅向 `Agent` 与预取传入 `primary_interval` 对应的区间，图上只跑单周期分支。 |
| `Ablate_LLMPortfolio` | 去掉 LLM 在多策略信号上的融合决策 | `PortfolioManagementNode` 走 `generate_rule_based_trading_decision`：按**主周期**聚合各代理信号，确定性映射为买卖开平，规模受风控建议与现金约束。 |
| `Ablate_RiskSizing` | 弱化结构化风险 sizing | `RiskManagementNode` 在简化分支用**固定账户比例 / 现价**头寸建议，**不再**经过原止损价门槛逻辑；组合与（默认）LLM 仍保留。 |

标志位由 `benchmark/ablation.py` 的 `DAGAblationSettings` 与 `workflow_metadata()` 传到 `Agent` 的 `state["metadata"]`（`use_llm_portfolio`、`ablation_full_risk`），并由 `backtest/engine.py` 的 `Backtester` 控制 `intervals`。详情见 `nodes/portfolio.py`、`nodes/risk.py`。

**Phase 2 中的基线。** 默认关闭（`phase2.run_buy_and_hold`、`run_equal_weight_rebalance`）；打开时复用 Phase 1 的基线仿真，便于同一图中叠加大盘式对照。

**与 LLM 账户的关系。** `FullDAG`、`Ablate_MultiInterval`、`Ablate_RiskSizing` 在组合层仍会调 LLM（除非你再改 registry）；需可用 API 与余额。`Ablate_LLMPortfolio`**不在组合层调 LLM**（策略本身仍为规则/指标），适合无余额时的管线调试，但**不能**代表「完整智能组合」对照。

**代码结构。** `ablation.py`（设置）、`phase2_registry.py`（实验表）、`dag_backtest_runner`（单次回测，传入 `ablation=`）、`phase2.py`（编排）、`cli/benchmark_phase2.py`（命令行）。

**使用提示。** `config/benchmark.yaml` 的 `phase2`；`include_ablation_experiments` 留空则跑注册表全部。**输出：** `benchmark_phase2_summary_*.csv`、`benchmark_phase2_equity_*.csv`。

**写作注意。** 规则组合是为了**可复现、单因素解释**，不是宣称最优非 LLM 策略；简化风控改变的是风险建模假设，须在结果讨论中说明。若面向发表级结论，建议在 README 方法之外增加多样本、多区间或敏感性分析。

---

### 输出文件

所有输出文件保存在 `output/` 目录：
- **日志文件** (`.log`)：回测执行日志
- **JSON文件** (`.json`)：交易日志和决策历史
- **CSV文件** (`.csv`)：性能数据

管理输出文件：
```bash
# 列出所有输出文件
python -m trading_dag.cli.manage_output list

# 显示摘要
python -m trading_dag.cli.manage_output summary

# 清理旧文件
python -m trading_dag.cli.manage_output cleanup

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
- **手动配置**：在 `config/config.yaml` 中指定初始持仓（成本基础自动从市场价格设置）
- **仅现金**：仅使用初始现金开始（默认）

**注意**：本系统仅生成信号，不执行实际交易。使用风险自负。

## 添加新策略

1. 在 `src/trading_dag/strategies/` 目录创建新的策略文件：

```python
from trading_dag.core.node import BaseNode
from trading_dag.core.state import AgentState
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

2. 在 `src/trading_dag/strategies/__init__.py` 中注册
3. 在 `config/config.yaml` 的 `signals.strategies` 中添加

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
python -m trading_dag.cli.manage_output list      # 列出所有文件
python -m trading_dag.cli.manage_output summary  # 显示统计信息
python -m trading_dag.cli.manage_output cleanup  # 清理旧文件

# 高级用法
python -m trading_dag.utils.file_manager --help
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
- 为每个间隔生成带置信度分数（0-100%）的信号
- 信号按交易对 → 代理 → 间隔 → 信号/置信度的方式组织
- 所有间隔的信号都提供给PortfolioManagementNode进行全面分析

### 间隔权重和主要间隔优先级

系统使用智能间隔权重机制：

**主要间隔优先级**：
- `config.yaml`中指定的`primary_interval`在LLM决策中具有**最高优先级**
- 当不同间隔的信号冲突时，主要间隔的信号优先
- 主要间隔的信号作为交易决策的主要依据

**其他间隔**：
- 其他间隔（非主要）的信号作为补充信息使用
- 它们帮助确认或反驳主要间隔的信号
- 来自其他间隔的高置信度信号会被更多考虑
- 如果所有间隔都一致（相同方向），决策的置信度会增加

**信号置信度级别**：
- **强信号**：置信度 > 70% - 高度影响的信号
- **中等信号**：置信度 50-70% - 中等影响
- **弱信号**：置信度 < 50% - 较低影响

**LLM决策流程**：
1. 首先分析每个策略的主要间隔信号
2. 检查其他间隔是否确认或反驳主要间隔信号
3. 如果所有间隔都一致，增加决策的置信度
4. 如果间隔冲突，优先考虑主要间隔，但会考虑冲突信号的强度
5. 结合多个策略的信号，按置信度水平加权

这确保了LLM通过考虑所有可用的间隔信号做出明智的决策，同时尊重主要间隔的优先级。

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
- 验证 `config/config.yaml` 中的 `base_url` 与你的提供商匹配

### 策略加载错误
- 确保 `config/config.yaml` 中的策略名称与类名完全匹配（区分大小写）
- 策略文件应在 `src/trading_dag/strategies/` 目录中，类名匹配

### 配置错误
- `primary_interval` 如果未在 `signals.intervals` 中列出，将自动添加（无需手动配置）
- `config/config.yaml` 和 `.env` 文件必须存在并正确配置

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

