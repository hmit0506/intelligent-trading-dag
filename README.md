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
├── core/              # Core framework (state, nodes, workflow)
├── nodes/             # Workflow nodes
├── strategies/        # Trading strategies
├── backtest/          # Backtesting engine
├── data/              # Data providers (Binance)
├── indicators/        # Technical indicators
├── llm/               # LLM integration
├── utils/             # Utilities and configuration
├── main.py            # Live trading entry point
├── backtest.py        # Backtest entry point
└── config.yaml        # Configuration file
```

**Note**: This project is fully independent and does not require the original project directory.

## Installation

### Prerequisites

- Python 3.12 or higher
- Binance account (for market data access)

### Setup

1. Navigate to the project directory:
```bash
cd new_project
```

2. Set up using uv (recommended):
```bash
# Install uv if you don't have it
curl -fsSL https://install.lunarvim.org/uv.sh | sh

# Create virtual environment
uv venv --python 3.12

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Install dependencies
uv pip sync
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
- Get Binance API keys from: https://www.binance.com/en/my/settings/api-management
- Get LLM API keys from your chosen provider's website

4. Configure the system:
```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
```

## Configuration

**Configuration is a core component of this project!**

1. **Create config.yaml**:
```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
```

2. **Create .env file**:
```bash
cp env.example .env
# Edit .env with your API keys
```

**Note**: Both `config.yaml` and `.env` files are required for the system to function.

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

## Usage

### Quick Start

1. **Install dependencies** (if using pip instead of uv):
```bash
pip install -r requirements.txt
```

2. **Run backtest**:
```bash
uv run backtest.py
# or
python backtest.py
```

3. **Run live mode** (signal generation only, no actual trading):
```bash
uv run main.py
# or
python main.py
```

### Backtest Mode

Backtest mode will:
1. Fetch historical data for the specified date range
2. Run the DAG workflow for each time period
3. Execute simulated trades based on generated signals
4. Calculate and display performance metrics (returns, Sharpe ratio, Sortino ratio, max drawdown)

### Live Mode

Live mode will:
1. Fetch current market data
2. Run the DAG workflow
3. Generate trading signals
4. Display decisions (without executing actual trades)

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
- Trade-by-trade log
- Portfolio value over time

## Troubleshooting

### Import Errors
- Make sure virtual environment is activated
- Run `uv pip sync` or `pip install -r requirements.txt` to install all dependencies

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
Copyright (c) 2025 qashi (https://github.com/hmit0506)

This project is based on the original work:
Copyright (c) 2025 51bitquant (ai-hedge-fund-crypto)

See [LICENSE](LICENSE) file for full license text and attribution details.

## Contributors

- [qashi](https://github.com/hmit0506) - Project lead and initial implementation
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
