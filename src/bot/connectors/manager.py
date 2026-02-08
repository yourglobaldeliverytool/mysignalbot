"""Connector manager for failover and aggregation."""

import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import statistics

from bot.connectors.base import ConnectorBase
from bot.core.models import MarketData
from bot.core.logger import get_logger
from bot.core.exceptions import ConnectorError


class ConnectorManager:
    """Manager for multiple connectors with failover."""
    
    def __init__(self, connectors: List[ConnectorBase], config: Dict[str, Any]):
        """Initialize connector manager.
        
        Args:
            connectors: List of connectors to manage
            config: Manager configuration
        """
        self.connectors = connectors
        self.config = config
        self.logger = get_logger("connectors.manager")
        self.primary_connector = self._find_primary()
        self.secondary_connector = self._find_secondary()
        self.fallback_connector = self._find_fallback()
        self.failover_enabled = config.get('failover_enabled', True)
        self.aggregation_method = config.get('aggregation_method', 'median')
        self._current_connector: Optional[ConnectorBase] = None
    
    def _find_primary(self) -> Optional[ConnectorBase]:
        """Find primary connector."""
        primary_name = self.config.get('primary')
        for connector in self.connectors:
            if connector.enabled and connector.__class__.__name__.lower().replace('connector', '') == primary_name.lower():
                return connector
        return None
    
    def _find_secondary(self) -> Optional[ConnectorBase]:
        """Find secondary connector."""
        secondary_name = self.config.get('secondary')
        if not secondary_name:
            return None
        for connector in self.connectors:
            if connector.enabled and connector.__class__.__name__.lower().replace('connector', '') == secondary_name.lower():
                return connector
        return None
    
    def _find_fallback(self) -> Optional[ConnectorBase]:
        """Find fallback connector."""
        fallback_name = self.config.get('fallback')
        if not fallback_name:
            return None
        for connector in self.connectors:
            if connector.enabled and connector.__class__.__name__.lower().replace('connector', '') == fallback_name.lower():
                return connector
        return None
    
    async def connect_all(self) -> None:
        """Connect all enabled connectors."""
        self.logger.info("Connecting all connectors...")
        for connector in self.connectors:
            if connector.enabled:
                try:
                    await connector.connect()
                    self.logger.info(f"Connected to {connector.__class__.__name__}")
                except Exception as e:
                    self.logger.error(f"Failed to connect to {connector.__class__.__name__}: {e}")
                    connector.enabled = False
        
        # Set current connector
        if self.primary_connector and self.primary_connector.is_connected:
            self._current_connector = self.primary_connector
        elif self.secondary_connector and self.secondary_connector.is_connected:
            self._current_connector = self.secondary_connector
        elif self.fallback_connector and self.fallback_connector.is_connected:
            self._current_connector = self.fallback_connector
        else:
            self.logger.warning("No connectors available")
    
    async def disconnect_all(self) -> None:
        """Disconnect all connectors."""
        self.logger.info("Disconnecting all connectors...")
        for connector in self.connectors:
            try:
                await connector.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting {connector.__class__.__name__}: {e}")
        self._current_connector = None
    
    async def get_price(self, symbol: str) -> Optional[float]:
        """Get price with failover.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Price or None if unavailable
        """
        # Try to get price from all available connectors
        prices = []
        
        for connector in self.connectors:
            if not connector.enabled or not connector.is_connected:
                continue
            
            try:
                price = await connector.get_price(symbol)
                if price is not None and price > 0:
                    prices.append(price)
                    self.logger.debug(f"Price from {connector.__class__.__name__}: {price}")
            except Exception as e:
                self.logger.warning(f"Error getting price from {connector.__class__.__name__}: {e}")
                connector._increment_failure()
        
        if not prices:
            self.logger.error("No price data available from any connector")
            return None
        
        # Aggregate prices
        if self.aggregation_method == 'median':
            return statistics.median(prices)
        elif self.aggregation_method == 'mean':
            return statistics.mean(prices)
        elif self.aggregation_method == 'last':
            return prices[-1]
        else:
            return prices[0]
    
    async def get_market_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> Optional[List[MarketData]]:
        """Get market data with failover.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            limit: Number of candles
            
        Returns:
            List of market data or None
        """
        # Try primary connector first
        connectors_to_try = []
        if self.primary_connector:
            connectors_to_try.append(self.primary_connector)
        if self.secondary_connector:
            connectors_to_try.append(self.secondary_connector)
        if self.fallback_connector:
            connectors_to_try.append(self.fallback_connector)
        
        for connector in connectors_to_try:
            if not connector.enabled or not connector.is_connected:
                continue
            
            try:
                data = await connector.get_market_data(symbol, timeframe, limit)
                if data:
                    # Validate data
                    valid_data = [md for md in data if connector.validate_market_data(md)]
                    if valid_data:
                        self.logger.info(f"Got {len(valid_data)} candles from {connector.__class__.__name__}")
                        return valid_data
            except Exception as e:
                self.logger.warning(f"Error getting market data from {connector.__class__.__name__}: {e}")
                connector._increment_failure()
        
        self.logger.error("No market data available from any connector")
        return None
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all connectors.
        
        Returns:
            Dictionary mapping connector names to health status
        """
        results = {}
        for connector in self.connectors:
            if connector.enabled:
                try:
                    healthy = await connector.health_check()
                    results[connector.__class__.__name__] = healthy
                except Exception as e:
                    self.logger.error(f"Health check failed for {connector.__class__.__name__}: {e}")
                    results[connector.__class__.__name__] = False
            else:
                results[connector.__class__.__name__] = False
        return results
    
    def get_connected_connectors(self) -> List[ConnectorBase]:
        """Get list of connected connectors.
        
        Returns:
            List of connected connectors
        """
        return [c for c in self.connectors if c.enabled and c.is_connected]