# Intelligent Signal Fusion System for Cryptocurrency Trading via a Modular DAG

A sophisticated cryptocurrency trading system that leverages a modular Directed Acyclic Graph (DAG) architecture to fuse multiple trading signals and make intelligent trading decisions using Large Language Models (LLMs).

## Overview

This system employs LangGraph to create a flexible workflow where market data flows through specialized nodes for multi-timeframe analysis, technical indicator calculation, risk management, and AI-powered portfolio decision-making.

## Key Features

- **Modular DAG Architecture**: Clean separation of concerns with specialized nodes for data fetching, signal generation, risk management, and portfolio management
- **Multi-Strategy Support**: Combines multiple trading strategies (MACD, RSI, Bollinger Bands) with weighted signal fusion
- **Multi-Timeframe Analysis**: Simultaneously analyzes multiple time intervals (1m, 5m, 1h, 4h, etc.) for robust signal generation
- **Primary Interval Priority**: LLM decision-making prioritizes signals from the primary interval while considering other intervals as supplementary information
- **AI-Enhanced Decision Making**: Uses LLMs (OpenAI, Groq, Anthropic, Ollama, etc.) for sophisticated portfolio management decisions with explicit interval weighting guidance
- **Comprehensive Backtesting**: Robust historical performance evaluation with detailed metrics and visualizations
- **Historical Data Warmup**: Automatically fetches additional historical data before backtest start date to ensure technical indicators work correctly from the first data point
- **Initial Positions Support**: Both live and backtest modes support starting with existing positions (long/short), not just cash
- **Exchange Integration**: Live mode can automatically sync portfolio from Binance exchange account
- **Unified Decision Mechanism**: Live and backtest modes use identical decision-making logic for consistent results (no future price predictions)
- **Risk Management**: Configurable position sizing via YAML `risk` (documented under [Risk management](#risk-management) in Configuration)
- **Unified Runner**: Single entry point for both backtest and live modes with consistent interface
- **Progress Tracking**: Real-time progress bars and configurable output frequency for backtests
- **File Management**: Automatic export of results (CSV/JSON) and built-in file cleanup utilities
- **Enhanced Output**: Detailed portfolio information, decision history, and performance metrics

## Architecture

The system uses a DAG workflow with the following nodes:

1. **StartNode**: Initializes the workflow
2. **DataNode**: Fetches market data for each specified timeframe
3. **MergeNode**: Combines multi-timeframe data
4. **Strategy Nodes** (MacdStrategy, RSIStrategy, BollingerStrategy): Apply technical analysis
5. **RiskManagementNode**: Deterministic sizing from `risk` settings; portfolio LLM also gets a short `risk_context_summary` derived from its `reasoning` dict ([details below](#risk-management))
6. **PortfolioManagementNode**: Makes final trading decisions using LLM reasoning

## Project Structure

```
.
├── src/trading_dag/   # Main package (Python-friendly name with underscores)
│   ├── cli/           # CLI entry points (main, backtest, manage_output)
│   ├── core/          # State, nodes, workflow, runner
│   ├── nodes/         # Workflow nodes
│   ├── strategies/    # Trading strategies
│   ├── backtest/      # Backtesting engine
│   ├── data/          # Data providers (Binance)
│   ├── gateway/       # Binance API client
│   ├── indicators/    # Technical indicators
│   ├── llm/           # LLM integration
│   └── utils/         # Configuration and utilities
├── config/            # Configuration files
│   ├── config.yaml    # Main config (copy from config.example.yaml)
│   └── config.example.yaml
├── tests/             # Unit and integration tests
├── output/            # Generated files (logs, JSON, CSV)
├── run.py             # Convenience launcher
└── pyproject.toml     # Package config and dependencies
```

**Note**: This project is fully independent and does not require the original project directory.

## Installation

### Prerequisites

- Python 3.12 or higher
- Binance account (for market data access)

### Setup

1. Navigate to the project directory:
```bash
cd intelligent-trading-dag
```

2. Set up using uv (recommended):
```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Activate virtual environment (if needed)
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows
```

Alternatively, using standard Python:
```bash
# Create virtual environment
python3.12 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
```
BINANCE_API_KEY=your-binance-api-key
BINANCE_API_SECRET=your-binance-api-secret
OPENAI_API_KEY=your-openai-key  # If using OpenAI or OpenAI-compatible APIs (e.g., DeepSeek)
GROQ_API_KEY=your-groq-key      # If using Groq
# ... other LLM provider keys as needed
```

**Important**: 
- For OpenAI-compatible APIs (like DeepSeek), use `OPENAI_API_KEY` with the appropriate `base_url` in `config.yaml`
- **DeepSeek Setup**: 
  - Use `OPENAI_API_KEY` environment variable (get your API key from https://platform.deepseek.com/)
  - Set `provider: "openai"` and `base_url: "https://api.deepseek.com/v1"` in `config.yaml`
  - Model name: `"deepseek-chat"` or `"deepseek-chat-32k"`
- Get Binance API keys from: https://www.binance.com/en/my/settings/api-management
- Get LLM API keys from your chosen provider's website

4. Configure the system:
```bash
cp config/config.example.yaml config/config.yaml
# Edit config/config.yaml with your settings
```

**Note**: Both `config/config.yaml` and `.env` files are required for the system to function.

## Configuration

**Configuration is a core component of this project!**

Example `config.yaml`:

```yaml
mode: backtest  # or "live"
start_date: 2025-01-01
end_date: 2025-02-01
primary_interval: 1h  # Primary interval for decision-making. Automatically added to signals.intervals if not present. LLM prioritizes signals from this interval.
margin_requirement: 0.0
show_reasoning: false
show_agent_graph: true

# Performance and output options
print_frequency: 1        # Print every N iterations
use_progress_bar: true    # Show progress bar
enable_logging: true      # Generate log files
save_decision_history: true  # Save decision history

# File management options
auto_cleanup_files: false     # Automatically clean up old files
file_retention_days: 30      # Delete files older than N days
file_keep_latest: 10         # Always keep at least N latest files

# Portfolio initialization (works for both live and backtest modes)
# Option 1: Sync from exchange (live mode only, requires BINANCE_API_KEY and BINANCE_API_SECRET)
sync_from_exchange: false  # Set to true to sync portfolio from Binance account

# Option 2: Manual initial positions (works for both live and backtest modes)
# Starting cash belongs in initial_positions.cash (legacy top-level initial_cash is still accepted).
# Note: Cost basis is automatically set using historical/real-time prices
initial_positions:
  cash: 100000
#   positions:
#     BTCUSDT:
#       long: 0.1  # Long position quantity
#       short: 0.0  # Short position quantity
#     ETHUSDT:
#       long: 2.0

# risk: ...  # optional; see "Risk management" subsection below for defaults and fields

signals:
  intervals: ["1h", "4h"]  # All intervals to analyze. The primary_interval will be automatically included if not listed.
  tickers: ["BTCUSDT", "ETHUSDT"]
  strategies: ["MacdStrategy", "RSIStrategy", "BollingerStrategy"]
model:
  name: "gpt-4o-mini"
  provider: "openai"
  base_url: null
  temperature: 0.0
  format: "json"

# DeepSeek example configuration:
# model:
#   name: "deepseek-chat"
#   provider: "openai"
#   base_url: "https://api.deepseek.com/v1"
#   temperature: 0.0
#   format: "json"
```

### Risk management

This section is the **only** README reference for `RiskManagementNode`: config, outputs, what the portfolio LLM receives, sizing math, and benchmarks. Code: `nodes/risk.py`; schema: `RiskManagementConfig` in `utils/config.py`. The risk node is **deterministic** (pandas / arithmetic only) — **no LLM** inside it.

#### Configuration

Use the top-level `risk` key in `config/config.yaml` (and `config/config.example.yaml`). For benchmarks, duplicate the same block under `main` in `config/benchmark.yaml` so **FullDAG** matches a normal backtest when values are identical.

Example (omit the whole block to use code defaults):

```yaml
risk:
  risk_per_trade_pct: 0.02
  stop_loss_pct: 0.05
  min_quantity: 0.001
  quantity_decimals: 3
  stop_distance_mode: entry_or_spot_pct  # or "atr"
  atr_period: 14
  atr_multiplier: 1.0
  max_notional_fraction_per_ticker: 1.0
```

`risk_config_to_metadata()` flattens these into `AgentState` metadata. `Backtester`, `TradingSystemRunner`, and `dag_backtest_runner` all attach the same `Config.risk` so live, backtest, and DAG benchmarks stay aligned.

#### What the node produces (per ticker)

Written to `analyst_signals["risk_management_agent"][ticker]`:

| Field | Type | Role |
|--------|------|------|
| `suggested_quantity` | float | Suggested size after risk budget, notional cap, rounding, and `min_quantity`. |
| `current_price` | float | Primary-interval last **close** used for sizing. |
| `remaining_position_limit` | float | `min(cash, max_notional_fraction_per_ticker × portfolio value)` — nominal cap for that step. |
| `reasoning` | dict | Structured trace: e.g. `mode`, `stop_distance_mode`, `risk_per_share`, `leg`, `stop_price`, ATR fields, or `error` if OHLC is missing. For humans / logs / debugging; built in code, not by a model. |

A `HumanMessage` with the full JSON is also appended for the LangGraph message list; that is separate from the portfolio prompt.

#### What the portfolio LLM sees

`PortfolioManagementNode` does **not** paste the full `reasoning` dict into the strategy signal blob. Strategy agents appear under `signals_by_ticker` only. From the risk node it passes these **separate** JSON fields into the portfolio LLM prompt:

- **`current_prices`** — from `current_price`
- **`max_shares`** — `remaining_position_limit ÷ price` (or `0` if price invalid)
- **`suggested_quantities`** — from `suggested_quantity`
- **`risk_context_summary`** — **per ticker**, one or two short **English** sentences generated in `portfolio.py` (`summarize_risk_reasoning_for_prompt`) from `reasoning`, e.g. `stop_distance_mode`, `risk_per_share`, and reference stop / leg when applicable. This gives the LLM **context for why** the suggested size looks the way it does, without dumping the entire dict.

Turning on **`show_reasoning`** only affects **console** printing (`show_agent_reasoning`); it does not by itself add the full dict to the portfolio LLM.

**Rule-based portfolio** (e.g. `Ablate_LLMPortfolio`) does not call the portfolio LLM; it still uses `suggested_quantities`, `max_shares`, and `current_prices` from the risk node.

#### Sizing logic

**Full path** (default; `metadata["ablation_full_risk"]` true). Target dollars-at-risk per decision ≈ `risk_per_trade_pct × portfolio value`. Per-share risk (`risk_per_share`) depends on `stop_distance_mode`:

- **`entry_or_spot_pct`**: with open long/short, distance uses average cost and `stop_loss_pct`; if **flat**, a spot-based reference (see `nodes/risk.py`).
- **`atr`**: `risk_per_share = ATR × atr_multiplier` on the **primary** interval OHLC.

Then `suggested_quantity` scales from portfolio risk ÷ `risk_per_share`, with cap versus total portfolio value, decimals, and `min_quantity` as documented above.

**Simplified path** (`metadata["ablation_full_risk"]` false, Phase 2 `Ablate_RiskSizing`): fixed fraction of portfolio ÷ price only — no stop/ATR distance — same caps and rounding fields.

**Phase 2 quick reference.** `FullDAG` uses the full path with **`main.risk`**. `Ablate_RiskSizing` swaps in the simplified path. Flags: `benchmark/ablation.py`, `workflow_metadata` on `Agent`, `Backtester.ablation`.

## Usage

### Quick Start

1. **Run backtest** (mode is determined by `config.yaml`):
```bash
uv run python run.py
# or
python run.py
```

The system automatically detects the mode from `config.yaml`:
- If `mode: backtest` → runs backtest with progress bar and detailed metrics
- If `mode: live` → runs live mode with portfolio display and decision history

2. **Run specific mode**:
```bash
# Backtest mode
uv run python run.py --backtest
# or
python run.py --backtest

# Live mode
uv run python run.py  # (set mode: live in config.yaml)
# or
python run.py
```

3. **Run Phase 1 benchmark suite** (Full DAG + single-strategy variants + strong baselines):
```bash
# Optional: create unified benchmark config first
cp config/benchmark.example.yaml config/benchmark.yaml

# Run with run.py unified entry
uv run python run.py --benchmark-phase1
# or
python run.py --benchmark-phase1

# Alternative direct CLI
uv run python -m trading_dag.cli.benchmark_phase1 --config config/benchmark.yaml
```

4. **Run Phase 2 benchmark suite** (DAG ablations: turn off one subsystem at a time vs full pipeline):
```bash
uv run python run.py --benchmark-phase2
# or
python run.py --benchmark-phase2

uv run python -m trading_dag.cli.benchmark_phase2 --config config/benchmark.yaml
```

### Phase 1 benchmark — methodology and internals

**Purpose.** Phase 1 answers a *capacity vs. decomposition* question: under identical market data, capital, and configuration, how does the **full multi-strategy DAG pipeline** compare to (a) **running the same engine with only one strategy enabled**, and (b) **simple non-DAG baselines**? The goal is not to prove optimality on every market regime, but to show whether the *integrated framework* behaves differently from isolated components and naive references.

**What is held constant.** All DAG-based runs (`FullDAG`, `SingleMACD`, `SingleRSI`, `SingleBollinger`) share the same `Backtester` and `Agent`: same `main.start_date` / `end_date`, `signals.tickers`, `initial_positions`, margin settings, LLM (`model`), and `signals.intervals`. Only the **strategy list** changes per `DagExperimentSpec` in `phase1_registry.py`. That isolates “which strategies are active in the graph” while keeping data and portfolio mechanics aligned.

**DAG experiment groups.**

- **FullDAG** — Uses the full `strategies` list from config (e.g. MACD + RSI + Bollinger). All strategy nodes feed the risk and portfolio nodes as in normal backtest.
- **Single-strategy variants** — The workflow graph still contains risk and portfolio; only **one** strategy class is registered. This tests whether a *single indicator family* inside the same execution and decision shell matches the full fusion.

**Baselines (non-DAG).** Implemented in `baseline_simulators.py` and driven by `get_phase1_baseline_registry()`:

- **Buy and hold** — Initial capital allocated once to a static mix; no strategy signals or LLM.
- **Equal-weight rebalance** — Periodically reweights to equal nominal exposure across tickers (`rebalance_every_bars` in primary-interval bars).

These provide *interpretable* references (passive and rule-based) rather than competing “oracle” models.

**Metrics.** Per experiment, equity is the backtester’s portfolio value time series (or baseline simulation). `equity_metrics.build_equity_metrics` derives returns, Sharpe, Sortino, drawdown, win rate, etc. Summary rows are ranked for quick comparison; for a formal report you should treat statistical significance, transaction costs, and robustness across windows separately.

**Code layout.**

- `run_phase1_benchmarks` — Phase-specific orchestration (`phase1.py`); shared CSV/baseline logic lives in `suite_common.py`. Phase CLIs share `cli/benchmark_cli_common.py`.
- `phase1_registry.py` — Named experiments → strategy lists.
- `dag_backtest_runner.run_dag_backtest_experiment` — Invokes `Backtester` (phase 1 passes default ablation = full pipeline).
- `baseline_simulators.py` / `prepare_primary_klines` — Passive baseline paths and data prep.
- `experiment_types.py` — `ExperimentResult` dataclass (all phases). Legacy imports `phase1_models` / `phase1_metrics` / `phase1_baselines` remain as thin re-exports.

**Operational notes.**

- Single orchestration entry: `run_phase1_benchmarks(...)`.
- Config: `config/benchmark.yaml` → `main` + `phase1` (mode must be `backtest`). Optional `--benchmark-config` YAML merges into `phase1` (legacy).
- Noise control: `phase1.dag_print_frequency`, `dag_use_progress_bar`.
- **Experiment lists:** `include_dag_experiments` / `include_baseline_experiments` — list **comparison** names only; **`FullDAG` is always run first** and need not appear in YAML (an explicit `FullDAG` entry is ignored). Empty `include_dag_experiments` runs FullDAG plus **all** single-strategy variants.
- Exports: `export_individual_results` (per-experiment CSVs); `export_charts` (comparison PNGs: absolute equity overlay, normalized equity, total-return bars). CLI printing of paths is shared via `cli/benchmark_cli_common.py`.
- **Outputs (minimum):** `output/benchmark_phase1_summary_*.csv`, `benchmark_phase1_equity_*.csv`. Prefixes and chart types are printed at the end of a run and match `benchmark/phase1.py` / `figures.export_benchmark_figures`.

**Reporting caveats.** LLM portfolio decisions can vary with provider, temperature (kept at 0 in examples but still subject to API behavior), and prompt drift. Single-strategy runs still use the same **RiskManagementNode / portfolio** stack as FullDAG ([Risk management](#risk-management)), so they test “strategy set” rather than “raw indicator in isolation.” Baselines do not consume the DAG at all — differences in level or shape of equity are expected.

---

### Phase 2 benchmark — ablation methodology and internals

**Purpose.** Phase 2 answers a *component necessity* question: if we **remove one design choice** from an otherwise identical pipeline, what happens? This is classic **single-factor ablation**: one toggle off per named run (plus `FullDAG` as the reference), so interactions between ablations are **not** explored unless you add combined experiments to `phase2_registry.py`.

**Reference run: `FullDAG`.** Default `DAGAblationSettings`: multi-interval path, LLM portfolio, **full** risk sizing. Uses the same **`main.risk`** as a normal backtest when `benchmark.yaml` mirrors your project config ([Risk management](#risk-management)).

**Ablations (what changes under the hood).**

| Experiment | Principle | Implementation sketch |
|------------|-----------|------------------------|
| `Ablate_MultiInterval` | Remove auxiliary timeframes | `Backtester` passes only `primary_interval` into `Agent` / prefetch so the graph runs a single interval branch; strategies see one horizon instead of `signals.intervals`. |
| `Ablate_LLMPortfolio` | Remove LLM fusion at the portfolio node | `PortfolioManagementNode` uses `generate_rule_based_trading_decision`: deterministic aggregation of **primary-interval** signals across agents, then fixed mapping to buy/sell/short/hold with sizing caps from risk + cash. |
| `Ablate_RiskSizing` | Replace structured risk sizing | Simplified `RiskManagementNode` branch ([Risk management](#risk-management)). Portfolio and LLM stay on unless separately ablated. |

Ablation flags: `workflow_metadata` on `Agent` (`use_llm_portfolio`, `ablation_full_risk`) and `DAGAblationSettings` on `Backtester` (`multi_interval`). Code: `benchmark/ablation.py`, `nodes/portfolio.py`, `backtest/engine.py`; risk details: [Risk management](#risk-management).

**Baselines in Phase 2.** Optional and **off by default** (`phase2.run_buy_and_hold`, `run_equal_weight_rebalance`). They reuse Phase 1 baseline simulators when enabled, so you can plot DAG ablations and passive benchmarks on the same figure if desired.

**LLM dependency.** Any run with **LLM portfolio enabled** (`FullDAG`, `Ablate_MultiInterval`, `Ablate_RiskSizing`) requires a working API key and account balance. `Ablate_LLMPortfolio` does **not** call the LLM for final orders (strategies remain rule-based), which is useful for dry runs without credits — but it is **not** comparable to “full intelligence” along the portfolio dimension.

**Code layout.**

- `DAGAblationSettings` — `benchmark/ablation.py`
- Experiment list — `benchmark/phase2_registry.py`
- One backtest per spec — `dag_backtest_runner.run_dag_backtest_experiment` (with `ablation=` set)
- Runner — `benchmark/phase2.py`; CLI — `cli/benchmark_phase2.py`, `cli/benchmark_cli_common.py`

**Operational notes.**

- Config: `config/benchmark.yaml` → `phase2`; optional `--benchmark-config` merges into `phase2`. Empty `include_ablation_experiments` runs FullDAG plus **all** registered ablations. Non-empty lists **comparison** ablations only — **`FullDAG` is always prepended**; explicit `FullDAG` in the list is ignored.
- Same export switches as phase 1: `export_individual_results`, `export_charts` (see phase 1 notes above).
- **Outputs (minimum):** `output/benchmark_phase2_summary_*.csv`, `benchmark_phase2_equity_*.csv`.

**Reporting caveats.** Rule-based portfolio ablation is a **deliberately simple** policy for reproducibility, not a claim of best non-LLM execution. Simplified risk (`Ablate_RiskSizing`) drops the stop/ATR distance in sizing — say so when discussing drawdowns or turnover ([Risk management](#risk-management)). For publication-grade claims, add multi-seed or multi-window evaluation outside this README.

---

### Output Files

All output files are saved in the `output/` directory:
- **Log files** (`.log`): Backtest execution logs
- **JSON files** (`.json`): Trade logs and decision history
- **CSV files** (`.csv`): Performance data

Manage output files:
```bash
# List all output files
python -m trading_dag.cli.manage_output list

# Show summary
python -m trading_dag.cli.manage_output summary

# Clean up old files
python -m trading_dag.cli.manage_output cleanup

# See FILE_MANAGEMENT.md for detailed usage
```

### Backtest Mode

Backtest mode will:
1. Initialize portfolio (with initial positions if configured, or cash only)
2. Fetch historical data for the specified date range (with warmup period for technical indicators)
3. Run the DAG workflow for each time period with progress tracking
4. Execute simulated trades based on generated signals
5. Calculate and display performance metrics (returns, Sharpe ratio, Sortino ratio, max drawdown)
6. Export results to CSV and JSON files automatically
7. Generate log files for detailed analysis

**Key Features**:
- Historical data warmup for accurate technical indicators from the first data point
- Initial positions support (cost basis auto-set from market prices)
- Accurate return calculation based on initial portfolio value
- Progress tracking, configurable output, and automatic result export

### Live Mode

Live mode will:
1. Initialize portfolio (from exchange sync, manual config, or cash only)
2. Fetch current market data
3. Run the DAG workflow
4. Generate trading signals
5. Display current portfolio state and trading decisions:
   - Current cash balance and positions
   - Current portfolio value
   - Trading decisions with confidence levels
   - Detailed analyst signals from all strategies with technical indicators
6. Save decision history to JSON file

**Portfolio Initialization Options**:
- **Sync from Exchange**: Automatically fetch current balances and positions from Binance (requires API keys)
- **Manual Configuration**: Specify initial positions in `config/config.yaml` (cost basis auto-set from market prices)
- **Cash Only**: Start with initial cash only (default)

**Note**: This system generates signals but does NOT execute real trades. Use at your own risk.

## Adding New Strategies

1. Create a new strategy file in `src/trading_dag/strategies/`:

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
        
        # Your strategy logic here
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

2. Register in `src/trading_dag/strategies/__init__.py`
3. Add to `config/config.yaml` under `signals.strategies`

## Supported LLM Providers

- OpenAI (gpt-4o, gpt-4o-mini, etc.)
- DeepSeek (via OpenAI-compatible API)
- Groq
- OpenRouter
- Google Gemini
- Anthropic Claude
- Ollama (local models)

## Performance Metrics

The backtester provides:
- Total return percentage
- Sharpe ratio
- Sortino ratio
- Maximum drawdown
- Win rate and win/loss ratio
- Maximum consecutive wins/losses
- Trade-by-trade log (exported to JSON)
- Portfolio value over time (exported to CSV)
- Real-time progress tracking with progress bar

## Visualizations

### Portfolio Value Chart
- **When**: Generated automatically after backtest completion
- **Location**: Saved to `output/backtest_portfolio_value_YYYYMMDD_HHMMSS.png`
- **Format**: High-resolution PNG (300 DPI)
- **Content**: Portfolio value over time with grid and labels

### Agent Workflow Graph
- **When**: Generated when Agent is initialized (if `show_agent_graph: true`)
- **Location**: Project root directory
- **Format**: PNG file
- **Filename**: `{strategy1}_{strategy2}_..._graph.png`
- **Content**: DAG workflow structure showing nodes and connections

## File Management

The system automatically generates output files in the `output/` directory. Use the file management utilities to clean up:

```bash
# Quick commands
python -m trading_dag.cli.manage_output list      # List all files
python -m trading_dag.cli.manage_output summary  # Show statistics
python -m trading_dag.cli.manage_output cleanup  # Clean old files

# Advanced usage
python -m trading_dag.utils.file_manager --help
```

See [FILE_MANAGEMENT.md](FILE_MANAGEMENT.md) for detailed file management documentation.

## Configuration Options

See the Configuration section above for detailed examples. Key options include:

- **Portfolio Initialization**: Sync from exchange or manual positions (cost basis auto-set)
- **Risk**: [Risk management](#risk-management) (single subsection — YAML, sizing modes, benchmarks)
- **Performance Options**: Print frequency, progress bar, logging
- **File Management**: Auto-cleanup, retention policies

## Technical Details

### Data Flow and Execution

**Backtest Mode**:
- Data range is defined by `start_date` and `end_date` in `config.yaml`
- Fetches at least 500 K-lines per interval, or the entire date range if it needs more
- Calculates required K-lines based on the date range and interval duration
- Filters data to use only points within `start_date` to `end_date` for backtest iteration
- Each data point triggers a complete workflow execution:
  1. DataNode fetches historical data up to current timepoint
  2. All strategies execute in parallel, analyzing all tickers and intervals
  3. RiskManagementNode calculates suggested sizes and `reasoning`; portfolio LLM receives prices, caps, suggested quantities, and English `risk_context_summary`
  4. PortfolioManagementNode uses LLM to make final decisions
- Decisions are executed immediately in backtest mode

**Live Mode**:
- Fetches real-time data on-demand from Binance API
- Uses identical decision mechanism as backtest (no future price predictions)
- Only generates decisions (does not execute trades)
- Can sync portfolio from exchange or use configured initial positions

**Unified Decision Mechanism**:
- Both modes use the same decision logic based on current signals and prices
- No future price projections to ensure consistent behavior
- LLM analyzes current market conditions and generates decisions for "now" timepoint only

### Strategy Execution

Each strategy:
- Receives historical data sequences (not single data points) for technical indicator calculations
- Analyzes all configured tickers and intervals in parallel
- Generates signals with confidence scores (0-100%) for each interval
- Signals are organized by ticker → agent → interval → signal/confidence
- All interval signals are provided to PortfolioManagementNode for comprehensive analysis

### Interval Weighting and Primary Interval Priority

The system uses an intelligent interval weighting mechanism:

**Primary Interval Priority**:
- The `primary_interval` specified in `config.yaml` is given **HIGHEST PRIORITY** in LLM decision-making
- When signals from different intervals conflict, the primary interval signal takes precedence
- Primary interval signals serve as the primary basis for trading decisions

**Other Intervals**:
- Signals from other intervals (non-primary) are used as supplementary information
- They help confirm or contradict primary interval signals
- Higher confidence signals from other intervals are given more consideration
- If all intervals agree (same direction), confidence in the decision increases

**Signal Confidence Levels**:
- **STRONG**: Confidence > 70% - Highly influential signals
- **MODERATE**: Confidence 50-70% - Moderate influence
- **WEAK**: Confidence < 50% - Lower influence

**LLM Decision Process**:
1. Starts by analyzing PRIMARY INTERVAL signals for each strategy
2. Checks if other intervals confirm or contradict primary interval signals
3. If all intervals agree, increases confidence in the decision
4. If intervals conflict, prioritizes PRIMARY INTERVAL but considers the strength of conflicting signals
5. Combines signals from multiple strategies, weighting by confidence levels

This ensures that the LLM makes informed decisions by considering all available interval signals while respecting the primary interval's priority.

### Historical Data Fetching

Both backtest and live modes use similar data fetching mechanisms:
- **Live mode**: Fetches exactly 500 K-lines ending at current time for each configured interval
- **Backtest mode**: Fetches at least 500 K-lines, or the entire date range if it requires more than 500 K-lines
  - Calculates required K-lines based on `start_date` to `end_date` range
  - Uses `max(500, required_k_lines)` to ensure sufficient data coverage
  - Filters to use only data within `start_date` to `end_date` for iteration
- This ensures sufficient historical data for technical indicator calculations while maintaining efficiency

## Troubleshooting

### Import Errors
- Make sure virtual environment is activated
- Run `uv sync` or `pip install -r requirements.txt` to install all dependencies

### API Authentication Errors
- Check your `.env` file has correct API keys (not placeholder values)
- For OpenAI-compatible APIs (DeepSeek, etc.), ensure `OPENAI_API_KEY` is set
- Verify `base_url` in `config/config.yaml` matches your provider

### Strategy Loading Errors
- Ensure strategy names in `config/config.yaml` match class names exactly (case-sensitive)
- Strategy files should be in `src/trading_dag/strategies/` directory with matching class names

### Configuration Errors
- `primary_interval` will be automatically added to `signals.intervals` if not present (no manual configuration needed)
- Both `config/config.yaml` and `.env` files must exist and be properly configured

### Data Issues
- If backtest shows insufficient data, check that `start_date` and `end_date` are valid
- Backtest mode automatically fetches enough data to cover the entire date range (at least 500 K-lines)
- Live mode fetches exactly 500 K-lines per interval
- Ensure Binance API is accessible for data fetching
- For live mode, ensure API keys have read permissions for account balance sync

## License

MIT License

Copyright (c) 2025 FYP25019 Team  
Copyright (c) 2025 Shi Qian (https://github.com/hmit0506)

This project is based on the original work:
Copyright (c) 2025 51bitquant (ai-hedge-fund-crypto)

See [LICENSE](LICENSE) file for full license text and attribution details.

## Contributors

- [Shi Qian](https://github.com/hmit0506) - Project lead and initial implementation
- FYP25019 Team - Development team

## Acknowledgments

This project is a complete rewrite and extension of the original 
[ai-hedge-fund-crypto](https://github.com/51bitquant/ai-hedge-fund-crypto) 
project by 51bitquant, licensed under the MIT License.

While this implementation has been significantly refactored and enhanced, 
it maintains the core architectural concepts and design principles of the 
original work. We acknowledge and appreciate the foundational work provided 
by the original author.

**Original Repository**: https://github.com/51bitquant/ai-hedge-fund-crypto  
**Original License**: MIT License  
**Original Copyright**: Copyright (c) 2025 51bitquant

## Disclaimer

This project is provided "as is" without any warranty. Use at your own risk. Trading cryptocurrencies involves substantial risk of loss.
