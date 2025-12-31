# Intelligent Signal Fusion System for Cryptocurrency Trading via a Modular DAG

A sophisticated cryptocurrency trading system that leverages a modular Directed Acyclic Graph (DAG) architecture to fuse multiple trading signals and make intelligent trading decisions using Large Language Models (LLMs).

## Overview

This system employs LangGraph to create a flexible workflow where market data flows through specialized nodes for multi-timeframe analysis, technical indicator calculation, risk management, and AI-powered portfolio decision-making.

## Key Features

- **Modular DAG Architecture**: Clean separation of concerns with specialized nodes for data fetching, signal generation, risk management, and portfolio management
- **Multi-Strategy Support**: Combines multiple trading strategies (MACD, RSI, Bollinger Bands) with weighted signal fusion
- **Multi-Timeframe Analysis**: Simultaneously analyzes multiple time intervals (1m, 5m, 1h, 4h, etc.) for robust signal generation
- **AI-Enhanced Decision Making**: Uses LLMs (OpenAI, Groq, Anthropic, Ollama, etc.) for sophisticated portfolio management decisions
- **Comprehensive Backtesting**: Robust historical performance evaluation with detailed metrics and visualizations
- **Historical Data Warmup**: Automatically fetches additional historical data before backtest start date to ensure technical indicators work correctly from the first data point
- **Initial Positions Support**: Both live and backtest modes support starting with existing positions (long/short), not just cash
- **Exchange Integration**: Live mode can automatically sync portfolio from Binance exchange account
- **Unified Decision Mechanism**: Live and backtest modes use identical decision-making logic for consistent results (no future price predictions)
- **Risk Management**: Built-in position sizing and risk controls using Fixed Fractional Position Sizing
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
5. **RiskManagementNode**: Calculates position sizing and risk parameters
6. **PortfolioManagementNode**: Makes final trading decisions using LLM reasoning

## Project Structure

```
.
├── gateway/           # Binance API client (independent)
├── core/              # Core framework (state, nodes, workflow, runner)
│   ├── node.py        # Base node class
│   ├── state.py       # Agent state management
│   ├── workflow.py    # Workflow creation
│   └── runner.py      # Unified trading system runner
├── nodes/             # Workflow nodes
├── strategies/        # Trading strategies
├── backtest/          # Backtesting engine
├── data/              # Data providers (Binance)
├── indicators/        # Technical indicators
├── llm/               # LLM integration
├── utils/             # Utilities and configuration
│   └── file_manager.py  # Output file management utilities
├── main.py            # Unified entry point (supports both modes)
├── backtest.py        # Backtest entry point (legacy, uses unified runner)
├── manage_output.py   # File management convenience script
├── config.yaml        # Configuration file
└── output/            # Output directory (logs, JSON, CSV files)
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
cp env.example .env
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
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
```

**Note**: Both `config.yaml` and `.env` files are required for the system to function.

## Configuration

**Configuration is a core component of this project!**

Example `config.yaml`:

```yaml
mode: backtest  # or "live"
start_date: 2025-01-01
end_date: 2025-02-01
primary_interval: 1h
initial_cash: 100000
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
# Note: Cost basis is automatically set using historical/real-time prices
# initial_positions:
#   cash: 100000  # Optional: override initial_cash
#   positions:
#     BTCUSDT:
#       long: 0.1  # Long position quantity
#       short: 0.0  # Short position quantity
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

# DeepSeek example configuration:
# model:
#   name: "deepseek-chat"
#   provider: "openai"
#   base_url: "https://api.deepseek.com/v1"
#   temperature: 0.0
#   format: "json"
```

## Usage

### Quick Start

1. **Run backtest** (mode is determined by `config.yaml`):
```bash
uv run main.py
# or
python main.py
```

The system automatically detects the mode from `config.yaml`:
- If `mode: backtest` → runs backtest with progress bar and detailed metrics
- If `mode: live` → runs live mode with portfolio display and decision history

2. **Run specific mode**:
```bash
# Backtest mode
uv run backtest.py
# or
python backtest.py

# Live mode
uv run main.py  # (set mode: live in config.yaml)
# or
python main.py
```

### Output Files

All output files are saved in the `output/` directory:
- **Log files** (`.log`): Backtest execution logs
- **JSON files** (`.json`): Trade logs and decision history
- **CSV files** (`.csv`): Performance data

Manage output files:
```bash
# List all output files
python manage_output.py list

# Show summary
python manage_output.py summary

# Clean up old files
python manage_output.py cleanup

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
5. Display decisions with enhanced portfolio information:
   - Initial portfolio value (baseline for return calculation)
   - Current cash balance and margin usage
   - Total portfolio value and return percentage
   - Current positions (long/short) with market prices and cost basis
   - Position source indication (initial from config, synced from exchange, or current)
   - Trading decisions with confidence levels
   - Analyst signals from all strategies
6. Save decision history to JSON file

**Portfolio Initialization Options**:
- **Sync from Exchange**: Automatically fetch current balances and positions from Binance (requires API keys)
- **Manual Configuration**: Specify initial positions in `config.yaml` (cost basis auto-set from market prices)
- **Cash Only**: Start with initial cash only (default)

**Note**: This system generates signals but does NOT execute real trades. Use at your own risk.

## Adding New Strategies

1. Create a new strategy file in `strategies/`:

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

2. Register in `strategies/__init__.py`
3. Add to `config.yaml` under `signals.strategies`

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
python manage_output.py list      # List all files
python manage_output.py summary  # Show statistics
python manage_output.py cleanup  # Clean old files

# Advanced usage
python -m utils.file_manager --help
```

See [FILE_MANAGEMENT.md](FILE_MANAGEMENT.md) for detailed file management documentation.

## Configuration Options

See the Configuration section above for detailed examples. Key options include:

- **Portfolio Initialization**: Sync from exchange or manual positions (cost basis auto-set)
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
  3. RiskManagementNode calculates position sizing
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
- Generates signals with confidence scores (0-100%)
- Signals are aggregated and used by PortfolioManagementNode for final decisions

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
- Verify `base_url` in `config.yaml` matches your provider

### Strategy Loading Errors
- Ensure strategy names in `config.yaml` match class names exactly (case-sensitive)
- Strategy files should be in `strategies/` directory with matching class names

### Configuration Errors
- Ensure `primary_interval` is listed in `signals.intervals`
- Both `config.yaml` and `.env` files must exist and be properly configured

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
