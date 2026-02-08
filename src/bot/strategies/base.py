"""Base strategy class."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime

from bot.core.models import Signal, MarketData, Side


class StrategyBase(ABC):
    """Base class for trading strategies."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize strategy.
        
        Args:
            config: Strategy configuration
        """
        self.config = config
        self.name = config.get('name', self.__class__.__name__)
        self.enabled = config.get('enabled', True)
        self.parameters = config.get('parameters', {})
        self._initialized = False
    
    @abstractmethod
    async def generate_signal(self, data: List[MarketData], current_price: float) -> Optional[Signal]:
        """Generate trading signal.
        
        Args:
            data: Historical market data
            current_price: Current price
            
        Returns:
            Signal or None
        """
        pass
    
    def validate_parameters(self) -> bool:
        """Validate strategy parameters.
        
        Returns:
            True if valid, False otherwise
        """
        return True
    
    async def initialize(self) -> None:
        """Initialize strategy."""
        if not self.validate_parameters():
            raise ValueError("Invalid strategy parameters")
        self._initialized = True
    
    async def cleanup(self) -> None:
        """Cleanup strategy resources."""
        pass
    
    def is_enabled(self) -> bool:
        """Check if strategy is enabled."""
        return self.enabled and self._initialized