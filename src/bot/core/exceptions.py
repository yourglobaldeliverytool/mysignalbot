"""Custom exceptions for trading bot."""


class TradingBotError(Exception):
    """Base exception for trading bot errors."""
    pass


class ConfigurationError(TradingBotError):
    """Configuration error."""
    pass


class StrategyError(TradingBotError):
    """Strategy error."""
    pass


class ConnectorError(TradingBotError):
    """Connector error."""
    pass


class OrderError(TradingBotError):
    """Order error."""
    pass


class RiskManagementError(TradingBotError):
    """Risk management error."""
    pass


class StateManagementError(TradingBotError):
    """State management error."""
    pass


class NotificationError(TradingBotError):
    """Notification error."""
    pass


class BacktestError(TradingBotError):
    """Backtest error."""
    pass


class DataValidationError(TradingBotError):
    """Data validation error."""
    pass