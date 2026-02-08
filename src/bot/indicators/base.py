"""Base indicator class."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
import pandas as pd

from bot.core.models import MarketData


class IndicatorBase(ABC):
    """Base class for technical indicators."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize indicator.
        
        Args:
            config: Indicator configuration
        """
        self.config = config
        self.name = config.get('name', self.__class__.__name__)
        self.parameters = config.get('parameters', {})
        self._initialized = False
    
    @abstractmethod
    def calculate(self, data: List[MarketData]) -> List[float]:
        """Calculate indicator values.
        
        Args:
            data: Market data
            
        Returns:
            List of indicator values
        """
        pass
    
    def get_min_periods(self) -> int:
        """Get minimum periods required for calculation.
        
        Returns:
            Minimum number of periods
        """
        return 1
    
    def validate_parameters(self) -> bool:
        """Validate indicator parameters.
        
        Returns:
            True if valid, False otherwise
        """
        return True
    
    def to_dataframe(self, data: List[MarketData]) -> pd.DataFrame:
        """Convert market data to pandas DataFrame.
        
        Args:
            data: Market data
            
        Returns:
            DataFrame
        """
        if not data:
            return pd.DataFrame()
        
        records = []
        for md in data:
            records.append({
                'timestamp': md.timestamp,
                'open': md.open,
                'high': md.high,
                'low': md.low,
                'close': md.close,
                'volume': md.volume
            })
        
        df = pd.DataFrame(records)
        df.set_index('timestamp', inplace=True)
        return df