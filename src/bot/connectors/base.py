"""Base connector class."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime

from bot.core.models import MarketData
from bot.core.exceptions import ConnectorError


class ConnectorBase(ABC):
    """Base class for data connectors."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize connector.
        
        Args:
            config: Connector configuration
        """
        self.config = config
        self.enabled: bool = config.get('enabled', True)
        self.max_retries: int = config.get('max_retries', 3)
        self._is_connected: bool = False
        self._failure_count: int = 0
        self._last_update: Optional[datetime] = None
    
    @property
    def is_connected(self) -> bool:
        """Check if connector is connected."""
        return self._is_connected
    
    @property
    def failure_count(self) -> int:
        """Get failure count."""
        return self._failure_count
    
    @property
    def last_update(self) -> Optional[datetime]:
        """Get last update timestamp."""
        return self._last_update
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to data source."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from data source."""
        pass
    
    @abstractmethod
    async def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Current price or None if unavailable
        """
        pass
    
    @abstractmethod
    async def get_market_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> Optional[List[MarketData]]:
        """Get historical market data.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (e.g., '1m', '1h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            List of market data or None if unavailable
        """
        pass
    
    async def health_check(self) -> bool:
        """Check connector health.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to fetch a price as a basic health check
            price = await self.get_price("BTC/USD")
            return price is not None and price > 0
        except Exception:
            return False
    
    def validate_market_data(self, md: MarketData) -> bool:
        """Validate market data.
        
        Args:
            md: Market data to validate
            
        Returns:
            True if valid, False otherwise
        """
        if md is None:
            return False
        
        if not md.symbol:
            return False
        
        if md.open <= 0 or md.high <= 0 or md.low <= 0 or md.close <= 0:
            return False
        
        if md.high < md.low:
            return False
        
        if md.close > md.high or md.close < md.low:
            return False
        
        if md.open > md.high or md.open < md.low:
            return False
        
        if md.volume < 0:
            return False
        
        return True
    
    def _increment_failure(self) -> None:
        """Increment failure count."""
        self._failure_count += 1
    
    def _reset_failure_count(self) -> None:
        """Reset failure count."""
        self._failure_count = 0
    
    def _update_last_update(self) -> None:
        """Update last update timestamp."""
        self._last_update = datetime.utcnow()