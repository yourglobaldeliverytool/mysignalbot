"""Configuration management using Pydantic."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime


class ExecutionConfig(BaseModel):
    """Execution configuration."""
    
    initial_capital: float = Field(default=10000.0, gt=0, description="Initial capital for trading")
    order_type: str = Field(default="market", description="Order type: market or limit")
    order_timeout: int = Field(default=60, gt=0, description="Order timeout in seconds")
    slippage_percent: float = Field(default=0.1, ge=0, description="Slippage percentage")
    fees: Dict[str, float] = Field(default_factory=lambda: {"maker": 0.001, "taker": 0.001}, description="Trading fees")
    max_orders_per_minute: int = Field(default=10, gt=0, description="Maximum orders per minute")
    min_confidence_threshold: float = Field(default=0.6, ge=0, le=1, description="Minimum confidence threshold")
    allow_partial_fills: bool = Field(default=True, description="Allow partial fills")
    
    @field_validator('order_type')
    @classmethod
    def validate_order_type(cls, v):
        if v not in ['market', 'limit']:
            raise ValueError('order_type must be either "market" or "limit"')
        return v
    
    @field_validator('slippage_percent')
    @classmethod
    def validate_slippage(cls, v):
        if v > 5:
            raise ValueError('slippage_percent must be less than 5%')
        return v / 100.0 if v >= 1 else v


class BacktestingConfig(BaseModel):
    """Backtesting configuration."""
    
    start_date: str = Field(default="2024-01-01", description="Backtest start date (YYYY-MM-DD)")
    end_date: str = Field(default="2024-12-31", description="Backtest end date (YYYY-MM-DD)")
    initial_capital: float = Field(default=10000.0, gt=0, description="Initial capital for backtesting")
    commission: float = Field(default=0.001, ge=0, description="Commission per trade")
    slippage: float = Field(default=0.001, ge=0, description="Slippage per trade")
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_dates(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')
        return v


class APICredentialsConfig(BaseModel):
    """API credentials configuration."""
    
    ccxt: Dict[str, Any] = Field(default_factory=dict, description="CCXT exchange credentials")
    alpha_vantage: Dict[str, str] = Field(default_factory=dict, description="Alpha Vantage API key")
    telegram: Dict[str, str] = Field(default_factory=dict, description="Telegram credentials")
    email: Dict[str, Any] = Field(default_factory=dict, description="Email SMTP settings")


class AssetConfig(BaseModel):
    """Asset configuration."""
    
    symbol: str
    type: str = Field(default="crypto", description="Asset type: crypto, stock, commodity")
    exchange: str = Field(default="binance", description="Exchange name")
    enabled: bool = Field(default=True, description="Whether this asset is enabled")
    min_trade_size: float = Field(default=0.001, gt=0, description="Minimum trade size")
    max_position_size: float = Field(default=1.0, gt=0, description="Maximum position size")


class StrategyConfig(BaseModel):
    """Strategy configuration."""
    
    name: str
    enabled: bool = Field(default=True, description="Whether this strategy is enabled")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")


class DataProviderConfig(BaseModel):
    """Data provider configuration."""
    
    primary: str = Field(default="mock", description="Primary data provider")
    secondary: Optional[str] = Field(default=None, description="Secondary data provider")
    fallback: Optional[str] = Field(default=None, description="Fallback data provider")
    failover_enabled: bool = Field(default=True, description="Enable automatic failover")
    aggregation_method: str = Field(default="median", description="Price aggregation method")


class NotificationConfig(BaseModel):
    """Notification configuration."""
    
    telegram: Dict[str, Any] = Field(default_factory=lambda: {
        "enable_notifications": False,
        "bot_token": "",
        "chat_id": ""
    })
    email: Dict[str, Any] = Field(default_factory=lambda: {
        "enable_notifications": False,
        "smtp_host": "",
        "smtp_port": 587,
        "username": "",
        "password": "",
        "from_email": ""
    })
    rate_limit: int = Field(default=10, gt=0, description="Max notifications per minute")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file: Optional[str] = Field(default=None, description="Log file path")
    rotation: bool = Field(default=True, description="Enable log rotation")


class StateManagementConfig(BaseModel):
    """State management configuration."""
    
    enabled: bool = Field(default=True, description="Enable state persistence")
    save_interval: int = Field(default=60, gt=0, description="Save interval in seconds")
    storage_path: str = Field(default="./state", description="State storage path")
    max_backups: int = Field(default=10, gt=0, description="Maximum number of state backups")


class AIMLConfig(BaseModel):
    """AI/ML configuration."""
    
    enabled: bool = Field(default=False, description="Enable AI/ML features")
    model_type: str = Field(default="random_forest", description="ML model type")
    retrain_interval: int = Field(default=86400, gt=0, description="Retrain interval in seconds")
    feature_window: int = Field(default=100, gt=0, description="Feature calculation window")
    
    model_config = {"protected_namespaces": ()}


class NewsSentimentConfig(BaseModel):
    """News sentiment configuration."""
    
    enabled: bool = Field(default=False, description="Enable news sentiment analysis")
    rss_feeds: List[str] = Field(default_factory=list, description="RSS feed URLs")
    update_interval: int = Field(default=3600, gt=0, description="Update interval in seconds")


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    
    enabled: bool = Field(default=True, description="Enable monitoring")
    health_check_interval: int = Field(default=60, gt=0, description="Health check interval in seconds")
    metrics_retention: int = Field(default=86400, gt=0, description="Metrics retention in seconds")


class AdvancedConfig(BaseModel):
    """Advanced configuration."""
    
    max_concurrent_orders: int = Field(default=5, gt=0, description="Maximum concurrent orders")
    position_sizing_method: str = Field(default="fixed", description="Position sizing method")
    risk_per_trade: float = Field(default=0.02, ge=0, le=1, description="Risk per trade (2% = 0.02)")
    max_drawdown: float = Field(default=0.2, ge=0, le=1, description="Maximum drawdown (20% = 0.2)")
    use_trailing_stop: bool = Field(default=False, description="Use trailing stop loss")


class TradingBotConfig(BaseModel):
    """Main trading bot configuration."""
    
    mode: str = Field(default="dry-run", description="Trading mode: dry-run, backtest, live")
    confirm_live: bool = Field(default=False, description="Confirmation required for live mode")
    api_credentials: APICredentialsConfig = Field(default_factory=APICredentialsConfig)
    assets: List[AssetConfig] = Field(default_factory=list, description="List of assets to trade")
    strategies: List[StrategyConfig] = Field(default_factory=list, description="List of strategies")
    data_providers: DataProviderConfig = Field(default_factory=DataProviderConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    backtesting: BacktestingConfig = Field(default_factory=BacktestingConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    state_management: StateManagementConfig = Field(default_factory=StateManagementConfig)
    ai_ml: AIMLConfig = Field(default_factory=AIMLConfig)
    news_sentiment: NewsSentimentConfig = Field(default_factory=NewsSentimentConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)
    
    @model_validator(mode='after')
    def validate_config(self) -> 'TradingBotConfig':
        """Validate configuration consistency."""
        if self.mode == 'live' and not self.confirm_live:
            raise ValueError(
                'Live mode requires confirm_live=true. '
                'Set confirm_live: true in config.yaml to enable live trading.'
            )
        if self.mode not in ['dry-run', 'backtest', 'live']:
            raise ValueError('mode must be one of: dry-run, backtest, live')
        return self


def load_config(config_path: str) -> TradingBotConfig:
    """Load configuration from YAML file."""
    import yaml
    from pathlib import Path
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_file, 'r') as f:
        config_data = yaml.safe_load(f)
    
    return TradingBotConfig(**config_data)