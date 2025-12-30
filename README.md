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
1. Fetch historical data for the specified date range
2. Run the DAG workflow for each time period with progress tracking
3. Execute simulated trades based on generated signals
4. Calculate and display performance metrics (returns, Sharpe ratio, Sortino ratio, max drawdown)
5. Export results to CSV and JSON files automatically
6. Generate log files for detailed analysis

**Enhanced Features**:
- Progress bar showing backtest progress
- Configurable print frequency to reduce I/O overhead
- Automatic export of trade logs and performance data
- Log file generation for debugging

### Live Mode

Live mode will:
1. Fetch current market data
2. Run the DAG workflow
3. Generate trading signals
4. Display decisions with enhanced portfolio information:
   - Current cash balance and margin usage
   - Total portfolio value and return percentage
   - Current positions (long/short) with market prices
   - Trading decisions with confidence levels
   - Analyst signals from all strategies
5. Save decision history to JSON file

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

See [FILE_MANAGEMENT.md](FILE_MANAGEMENT.md) for detailed documentation.

## Configuration Options

New configuration options in `config.yaml`:

```yaml
# Performance and output options
print_frequency: 1        # Print every N iterations
use_progress_bar: true    # Show progress bar
enable_logging: true      # Generate log files
save_decision_history: true  # Save decision history

# File management
auto_cleanup_files: false     # Auto-cleanup old files
file_retention_days: 30      # Delete files older than N days
file_keep_latest: 10         # Keep at least N latest files
```

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
