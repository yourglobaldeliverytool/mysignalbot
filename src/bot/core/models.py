"""Data models for trading bot."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from decimal import Decimal


class Side(str, Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"


class SignalType(str, Enum):
    """Signal type."""
    ENTRY = "entry"
    EXIT = "exit"
    HOLD = "hold"


@dataclass
class Signal:
    """Trading signal."""
    symbol: str
    side: Side
    signal_type: SignalType
    confidence: float
    price: float
    timestamp: datetime
    strategy_name: str
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    size: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Order:
    """Order."""
    id: str
    symbol: str
    side: Side
    order_type: OrderType
    quantity: float
    price: float
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    filled_price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    strategy_name: Optional[str] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """Position."""
    symbol: str
    side: Side
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def value(self) -> float:
        """Position value."""
        return self.quantity * self.current_price
    
    @property
    def is_open(self) -> bool:
        """Check if position is open."""
        return abs(self.quantity) > 0.0001


@dataclass
class Trade:
    """Trade (filled order)."""
    id: str
    order_id: str
    symbol: str
    side: Side
    quantity: float
    price: float
    timestamp: datetime
    commission: float = 0.0
    strategy_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def value(self) -> float:
        """Trade value."""
        return self.quantity * self.price


@dataclass
class MarketData:
    """Market data."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str = "1h"
    source: str = "unknown"
    
    @property
    def mid_price(self) -> float:
        """Mid price."""
        return (self.high + self.low) / 2


@dataclass
class BacktestResult:
    """Backtest result."""
    initial_capital: float
    final_capital: float
    total_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    start_date: datetime
    end_date: datetime
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    drawdown_curve: List[float] = field(default_factory=list)