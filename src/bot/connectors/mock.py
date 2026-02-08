"""Mock connector for testing and demo."""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from bot.connectors.base import ConnectorBase
from bot.core.models import MarketData
from bot.core.logger import get_logger


class MockConnector(ConnectorBase):
    """Mock connector that generates synthetic data."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize mock connector."""
        super().__init__(config)
        self.logger = get_logger("connectors.mock")
        self._prices: Dict[str, float] = {
            "BTC/USD": 45000.0,
            "ETH/USD": 2500.0,
            "GOLD": 2000.0
        }
        self._initialized = False
    
    async def connect(self) -> None:
        """Connect to mock data source."""
        if not self.enabled:
            self.logger.warning("Mock connector is disabled")
            return
        
        self.logger.info("Connecting to mock data source...")
        await asyncio.sleep(0.1)  # Simulate connection
        self._is_connected = True
        self._initialized = True
        self.logger.info("Connected to mock data source")
    
    async def disconnect(self) -> None:
        """Disconnect from mock data source."""
        self.logger.info("Disconnecting from mock data source...")
        self._is_connected = False
        self.logger.info("Disconnected from mock data source")
    
    async def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol."""
        if not self._is_connected:
            self.logger.warning("Connector not connected")
            return None
        
        # Simulate slight price movement
        if symbol in self._prices:
            import random
            variation = random.uniform(-0.001, 0.001)
            price = self._prices[symbol] * (1 + variation)
            self._prices[symbol] = price  # Update for next call
            self._update_last_update()
            self._reset_failure_count()
            return round(price, 2)
        
        self.logger.warning(f"Unknown symbol: {symbol}")
        self._increment_failure()
        return None
    
    async def get_market_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> Optional[List[MarketData]]:
        """Get historical market data."""
        if not self._is_connected:
            self.logger.warning("Connector not connected")
            return None
        
        # Generate synthetic OHLCV data
        import random
        
        base_price = self._prices.get(symbol, 1000.0)
        data = []
        now = datetime.utcnow()
        
        for i in range(limit):
            timestamp = now - timedelta(hours=limit - i)
            
            # Generate realistic price movement
            noise = random.uniform(-0.02, 0.02)
            price = base_price * (1 + noise * (i / limit))
            
            high = price * random.uniform(1.0, 1.01)
            low = price * random.uniform(0.99, 1.0)
            open_price = random.uniform(low, high)
            close_price = random.uniform(low, high)
            volume = random.uniform(100, 10000)
            
            md = MarketData(
                symbol=symbol,
                timestamp=timestamp,
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close_price, 2),
                volume=round(volume, 2),
                timeframe=timeframe,
                source="mock"
            )
            
            data.append(md)
        
        self._update_last_update()
        self._reset_failure_count()
        return data