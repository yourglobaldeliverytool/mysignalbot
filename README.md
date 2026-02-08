# Multi-Strategy Trading Bot

A production-ready, modular trading bot supporting multiple strategies, data providers, and notification systems. Built with Python 3.11+ and designed for deployment on Railway or similar platforms.

## Features

- **Multiple Trading Modes**: Dry-run, backtest, and live trading
- **Modular Architecture**: Easy to extend with custom strategies, connectors, and notifiers
- **Multiple Data Providers**: Built-in mock connector for testing, extensible to real APIs
- **Notification System**: Telegram and email notifications with graceful failure handling
- **Configuration Management**: YAML-based configuration with Pydantic validation
- **State Management**: Persistent state with automatic backups
- **Backtesting Engine**: Full-featured backtesting with detailed metrics
- **Risk Management**: Built-in position sizing and risk controls

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

### Configuration

The bot comes with a default `config.yaml` pre-configured with:

- Mock data connector (works without external APIs)
- Telegram credentials pre-configured
- Dry-run mode enabled (safe testing)
- Default trading strategies

### Running the Bot

#### Dry-Run Mode (Recommended for testing)

```bash
PYTHONPATH=/workspace/src:$PYTHONPATH python -m bot.main --mode dry-run --config config.yaml
```

#### Backtest Mode

```bash
PYTHONPATH=/workspace/src:$PYTHONPATH python -m bot.main --mode backtest --config config.yaml
```

#### Live Mode (Requires confirmation)

To enable live trading, first update `config.yaml`:

```yaml
mode: live
confirm_live: true
```

Then run:

```bash
PYTHONPATH=/workspace/src:$PYTHONPATH python -m bot.main --mode live --config config.yaml
```

### Verification Script

Run the verification script to test all components:

```bash
PYTHONPATH=/workspace/src:$PYTHONPATH python tests/verify_runtime.py
```

This will test:
- Configuration loading
- Logging setup
- Connector functionality
- Telegram notifier (with provided credentials)
- Email notifier (graceful failure)
- Trading engine initialization

## Configuration

### Trading Modes

- **dry-run**: Simulates trading without real money. Use this to test strategies.
- **backtest**: Runs backtests on historical data to evaluate strategy performance.
- **live**: Executes real trades. Requires `confirm_live: true` for safety.

### Execution Parameters

```yaml
execution:
  initial_capital: 10000.0      # Starting capital
  order_type: market            # Order type (market/limit)
  order_timeout: 60             # Order timeout in seconds
  slippage_percent: 0.1         # Expected slippage
  fees:
    maker: 0.001                # Maker fee
    taker: 0.001                # Taker fee
  max_orders_per_minute: 10     # Rate limiting
  min_confidence_threshold: 0.6 # Minimum signal confidence
  allow_partial_fills: true     # Allow partial order fills
```

### Notifications

The bot supports Telegram and email notifications. Both are optional and will gracefully fail if credentials are missing.

#### Telegram

```yaml
notifications:
  telegram:
    enable_notifications: true
    bot_token: "your_bot_token"
    chat_id: "your_chat_id"
```

The provided `config.yaml` includes pre-configured Telegram credentials.

#### Email

```yaml
notifications:
  email:
    enable_notifications: true
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    username: "your_email@gmail.com"
    password: "your_password"
    from_email: "your_email@gmail.com"
    to_email: "alerts@example.com"
```

## Project Structure

```
trading-bot/
├── src/
│   └── bot/
│       ├── main.py              # Main entry point
│       ├── core/                # Core components
│       │   ├── config.py        # Configuration management
│       │   ├── engine.py        # Trading engine
│       │   ├── models.py        # Data models
│       │   ├── logger.py        # Logging setup
│       │   ├── exceptions.py    # Custom exceptions
│       │   └── registry.py      # Plugin registry
│       ├── connectors/          # Data connectors
│       │   ├── base.py          # Base connector class
│       │   ├── mock.py          # Mock connector
│       │   └── manager.py       # Connector manager
│       ├── strategies/          # Trading strategies
│       │   └── base.py          # Base strategy class
│       ├── indicators/          # Technical indicators
│       │   └── base.py          # Base indicator class
│       ├── notifiers/           # Notification services
│       │   ├── base.py          # Base notifier class
│       │   ├── telegram.py      # Telegram notifier
│       │   └── email.py         # Email notifier
│       └── backtest/            # Backtesting
│           └── engine.py        # Backtest engine
├── tests/
│   └── verify_runtime.py        # Runtime verification script
├── config.yaml                  # Main configuration file
├── config.yaml.example          # Example configuration
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker configuration
├── Procfile                     # Railway Procfile
└── README.md                    # This file
```

## Deployment

### Docker

Build and run with Docker:

```bash
docker build -t trading-bot .
docker run trading-bot
```

### Railway

The bot is ready for Railway deployment:

1. Push this repository to GitHub
2. Connect your GitHub account to Railway
3. Select this repository
4. Railway will automatically detect the settings from `Procfile` and `Dockerfile`
5. Deploy!

The bot will start in dry-run mode by default with the mock connector, so it will work immediately without requiring any API keys.

### Environment Variables

You can override configuration using environment variables:

```bash
export LOG_LEVEL=DEBUG
PYTHONPATH=/workspace/src:$PYTHONPATH python -m bot.main --mode dry-run --config config.yaml
```

## Safety Features

1. **Graceful Degradation**: The bot continues running even if optional services fail (e.g., Telegram, email)
2. **Configuration Validation**: Pydantic validates all configuration values
3. **Live Mode Confirmation**: Requires explicit confirmation before live trading
4. **Default Safe Mode**: Starts in dry-run mode
5. **No External Dependencies Required**: Mock connector works without API keys

## Extending the Bot

### Adding a Custom Strategy

1. Create a new file in `src/bot/strategies/`:
```python
from bot.strategies.base import StrategyBase

class MyStrategy(StrategyBase):
    async def generate_signal(self, data, current_price):
        # Your strategy logic here
        pass
```

2. Add configuration to `config.yaml`:
```yaml
strategies:
  - name: MyStrategy
    enabled: true
    parameters: {}
```

### Adding a Custom Connector

1. Create a new file in `src/bot/connectors/`:
```python
from bot.connectors.base import ConnectorBase

class MyConnector(ConnectorBase):
    async def connect(self):
        pass
    
    async def get_price(self, symbol):
        pass
    
    async def get_market_data(self, symbol, timeframe, limit):
        pass
```

## Troubleshooting

### Import Errors

Ensure you're running with the correct PYTHONPATH:
```bash
cd trading-bot
PYTHONPATH=/workspace/src:$PYTHONPATH python -m bot.main --mode dry-run --config config.yaml
```

### Telegram Notifier Disabled

Check that both `bot_token` and `chat_id` are provided in `config.yaml`. The notifier will automatically disable if credentials are missing.

### Configuration Errors

Run the verification script to diagnose configuration issues:
```bash
PYTHONPATH=/workspace/src:$PYTHONPATH python tests/verify_runtime.py
```

## License

MIT License

## Support

For issues and questions, please refer to the verification script and logs for detailed error messages.