"""Base notifier class."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from bot.core.models import Signal, Order, Trade


class NotifierBase(ABC):
    """Base class for notification systems."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize notifier.
        
        Args:
            config: Notifier configuration
        """
        self.config = config
        self.enabled = config.get('enabled', True)
        self._initialized = False
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to notification service."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from notification service."""
        pass
    
    @abstractmethod
    async def send_message(self, message: str, **kwargs) -> bool:
        """Send a message.
        
        Args:
            message: Message to send
            **kwargs: Additional parameters
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    async def notify_signal(self, signal: Signal) -> bool:
        """Notify about a signal.
        
        Args:
            signal: Trading signal
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        message = self._format_signal(signal)
        return await self.send_message(message)
    
    async def notify_order(self, order: Order) -> bool:
        """Notify about an order.
        
        Args:
            order: Order
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        message = self._format_order(order)
        return await self.send_message(message)
    
    async def notify_trade(self, trade: Trade) -> bool:
        """Notify about a trade.
        
        Args:
            trade: Trade
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        message = self._format_trade(trade)
        return await self.send_message(message)
    
    def _format_signal(self, signal: Signal) -> str:
        """Format signal as message.
        
        Args:
            signal: Signal
            
        Returns:
            Formatted message
        """
        return (
            f"📊 Signal: {signal.strategy_name}\n"
            f"Symbol: {signal.symbol}\n"
            f"Side: {signal.side.value.upper()}\n"
            f"Price: {signal.price:.2f}\n"
            f"Confidence: {signal.confidence:.2%}\n"
            f"Type: {signal.signal_type.value}"
        )
    
    def _format_order(self, order: Order) -> str:
        """Format order as message.
        
        Args:
            order: Order
            
        Returns:
            Formatted message
        """
        return (
            f"📝 Order: {order.id}\n"
            f"Symbol: {order.symbol}\n"
            f"Side: {order.side.value.upper()}\n"
            f"Type: {order.order_type.value}\n"
            f"Quantity: {order.quantity:.4f}\n"
            f"Price: {order.price:.2f}\n"
            f"Status: {order.status.value}"
        )
    
    def _format_trade(self, trade: Trade) -> str:
        """Format trade as message.
        
        Args:
            trade: Trade
            
        Returns:
            Formatted message
        """
        return (
            f"✅ Trade: {trade.id}\n"
            f"Symbol: {trade.symbol}\n"
            f"Side: {trade.side.value.upper()}\n"
            f"Quantity: {trade.quantity:.4f}\n"
            f"Price: {trade.price:.2f}\n"
            f"Value: ${trade.value:.2f}"
        )