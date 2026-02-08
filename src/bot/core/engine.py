"""Main trading engine."""

import asyncio
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from bot.core.config import TradingBotConfig, load_config
from bot.core.models import (
    Signal, Order, OrderStatus, OrderType, 
    Side, MarketData, Trade, Position
)
from bot.core.logger import get_logger
from bot.core.exceptions import TradingBotError, OrderError
from bot.core.registry import get_registry_manager
from bot.connectors.base import ConnectorBase
from bot.connectors.manager import ConnectorManager
from bot.strategies.base import StrategyBase
from bot.notifiers.base import NotifierBase
from bot.notifiers.email import EmailNotifier
from bot.notifiers.telegram import TelegramNotifier
from bot.backtest.engine import BacktestEngine


class TradingEngine:
    """Main trading engine."""
    
    def __init__(self, config: TradingBotConfig):
        """Initialize trading engine.
        
        Args:
            config: Trading bot configuration
        """
        self.config = config
        self.logger = get_logger("engine")
        
        # Components
        self.connector_manager: Optional[ConnectorManager] = None
        self.strategies: List[StrategyBase] = []
        self.notifiers: List[NotifierBase] = []
        
        # State
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[Trade] = []
        self.signals: List[Signal] = []
        self._running = False
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all components."""
        self.logger.info("Initializing trading engine...")
        
        # Initialize connectors
        await self._initialize_connectors()
        
        # Initialize strategies
        await self._initialize_strategies()
        
        # Initialize notifiers
        await self._initialize_notifiers()
        
        self._initialized = True
        self.logger.info("Trading engine initialized successfully")
    
    async def _initialize_connectors(self) -> None:
        """Initialize data connectors."""
        self.logger.info("Initializing connectors...")
        
        # Create mock connector (always available)
        from bot.connectors.mock import MockConnector
        
        mock_config = {'enabled': True, 'max_retries': 3}
        mock_connector = MockConnector(mock_config)
        
        connectors = [mock_connector]
        self.connector_manager = ConnectorManager(
            connectors,
            {
                'primary': 'mock',
                'failover_enabled': self.config.data_providers.failover_enabled,
                'aggregation_method': self.config.data_providers.aggregation_method
            }
        )
        
        await self.connector_manager.connect_all()
    
    async def _initialize_strategies(self) -> None:
        """Initialize trading strategies."""
        self.logger.info("Initializing strategies...")
        
        # For now, we'll create a simple placeholder strategy
        # In production, this would load configured strategies
        from bot.strategies.base import StrategyBase
        
        class SimpleStrategy(StrategyBase):
            """Simple placeholder strategy."""
            
            async def generate_signal(self, data: List[MarketData], current_price: float) -> Optional[Signal]:
                """Generate a simple signal."""
                # Placeholder - returns hold signal
                return Signal(
                    symbol="BTC/USD",
                    side=Side.BUY,
                    signal_type="hold",
                    confidence=0.5,
                    price=current_price,
                    timestamp=datetime.utcnow(),
                    strategy_name="SimpleStrategy"
                )
            
            def get_min_periods(self) -> int:
                return 50
        
        for strategy_config in self.config.strategies:
            if strategy_config.enabled:
                try:
                    strategy = SimpleStrategy(strategy_config.dict())
                    await strategy.initialize()
                    self.strategies.append(strategy)
                    self.logger.info(f"Initialized strategy: {strategy.name}")
                except Exception as e:
                    self.logger.error(f"Failed to initialize strategy {strategy_config.name}: {e}")
    
    async def _initialize_notifiers(self) -> None:
        """Initialize notification services."""
        self.logger.info("Initializing notifiers...")
        
        # Telegram notifier
        telegram_config = {
            'telegram': self.config.notifications.telegram,
            'enabled': self.config.notifications.telegram.get('enable_notifications', False)
        }
        telegram_notifier = TelegramNotifier(telegram_config)
        
        try:
            await telegram_notifier.connect()
            self.notifiers.append(telegram_notifier)
            if telegram_notifier.enabled:
                self.logger.info("Telegram notifier connected")
        except Exception as e:
            self.logger.warning(f"Failed to connect Telegram notifier: {e}")
        
        # Email notifier
        email_config = {
            'email': self.config.notifications.email,
            'enabled': self.config.notifications.email.get('enable_notifications', False)
        }
        email_notifier = EmailNotifier(email_config)
        
        try:
            await email_notifier.connect()
            self.notifiers.append(email_notifier)
            if email_notifier.enabled:
                self.logger.info("Email notifier connected")
        except Exception as e:
            self.logger.warning(f"Failed to connect Email notifier: {e}")
    
    async def start(self) -> None:
        """Start trading engine."""
        if not self._initialized:
            await self.initialize()
        
        self.logger.info("Starting trading engine...")
        self.logger.info(f"Mode: {self.config.mode}")
        
        if self.config.mode == 'backtest':
            await self.run_backtest()
        elif self.config.mode in ['dry-run', 'live']:
            await self.run_trading_loop()
        else:
            raise ValueError(f"Unknown mode: {self.config.mode}")
    
    async def stop(self) -> None:
        """Stop trading engine."""
        self.logger.info("Stopping trading engine...")
        self._running = False
        
        # Disconnect connectors
        if self.connector_manager:
            await self.connector_manager.disconnect_all()
        
        # Disconnect notifiers
        for notifier in self.notifiers:
            try:
                await notifier.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting notifier: {e}")
        
        self.logger.info("Trading engine stopped")
    
    async def run_trading_loop(self) -> None:
        """Run main trading loop."""
        self._running = True
        self.logger.info("Starting trading loop...")
        
        try:
            while self._running:
                # Process each asset
                for asset in self.config.assets:
                    if not asset.enabled:
                        continue
                    
                    try:
                        await self.process_asset(asset)
                    except Exception as e:
                        self.logger.error(f"Error processing asset {asset.symbol}: {e}")
                
                # Wait for next iteration
                await asyncio.sleep(60)  # 1 minute interval
        
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Error in trading loop: {e}")
            raise
        finally:
            await self.stop()
    
    async def process_asset(self, asset) -> None:
        """Process a single asset.
        
        Args:
            asset: Asset configuration
        """
        # Get current price
        current_price = await self.connector_manager.get_price(asset.symbol)
        if current_price is None:
            self.logger.warning(f"Could not get price for {asset.symbol}")
            return
        
        # Get market data
        market_data = await self.connector_manager.get_market_data(
            asset.symbol,
            timeframe="1h",
            limit=200
        )
        if not market_data:
            self.logger.warning(f"Could not get market data for {asset.symbol}")
            return
        
        # Generate signals from strategies
        for strategy in self.strategies:
            if not strategy.is_enabled():
                continue
            
            try:
                signal = await strategy.generate_signal(market_data, current_price)
                if signal:
                    await self.process_signal(signal)
            except Exception as e:
                self.logger.error(f"Error generating signal from {strategy.name}: {e}")
    
    async def process_signal(self, signal: Signal) -> None:
        """Process trading signal.
        
        Args:
            signal: Trading signal
        """
        self.signals.append(signal)
        self.logger.info(
            f"Received signal: {signal.strategy_name} - {signal.side.value.upper()} "
            f"{signal.symbol} @ {signal.price:.2f} (confidence: {signal.confidence:.2%})"
        )
        
        # Check confidence threshold
        if signal.confidence < self.config.execution.min_confidence_threshold:
            self.logger.info("Signal confidence below threshold, ignoring")
            return
        
        # Notify about signal
        for notifier in self.notifiers:
            try:
                await notifier.notify_signal(signal)
            except Exception as e:
                self.logger.error(f"Error notifying signal: {e}")
        
        # Execute signal based on mode
        if self.config.mode == 'live':
            await self.execute_order(signal)
        else:  # dry-run
            await self.simulate_order(signal)
    
    async def execute_order(self, signal: Signal) -> None:
        """Execute live order.
        
        Args:
            signal: Trading signal
        """
        self.logger.warning("Live trading not implemented in this version")
    
    async def simulate_order(self, signal: Signal) -> None:
        """Simulate order (dry-run).
        
        Args:
            signal: Trading signal
        """
        order_id = str(uuid.uuid4())
        
        order = Order(
            id=order_id,
            symbol=signal.symbol,
            side=signal.side,
            order_type=OrderType.MARKET,
            quantity=self.config.advanced.risk_per_trade * self.config.execution.initial_capital / signal.price,
            price=signal.price,
            status=OrderStatus.FILLED,
            timestamp=datetime.utcnow(),
            strategy_name=signal.strategy_name
        )
        
        self.orders.append(order)
        self.logger.info(f"Simulated order: {order.side.value.upper()} {order.quantity:.4f} {order.symbol} @ {order.price:.2f}")
    
    async def run_backtest(self) -> None:
        """Run backtest."""
        self.logger.info("Running backtest...")
        
        backtest_config = {
            'initial_capital': self.config.backtesting.initial_capital,
            'commission': self.config.backtesting.commission,
            'slippage': self.config.backtesting.slippage
        }
        
        backtest_engine = BacktestEngine(backtest_config)
        
        # Get historical data
        asset = self.config.assets[0] if self.config.assets else None
        if not asset:
            self.logger.error("No assets configured for backtest")
            return
        
        market_data = await self.connector_manager.get_market_data(
            asset.symbol,
            timeframe="1h",
            limit=1000
        )
        
        if not market_data or len(market_data) < 100:
            self.logger.error("Not enough data for backtest")
            return
        
        # Run backtest with first strategy
        if not self.strategies:
            self.logger.error("No strategies configured for backtest")
            return
        
        result = await backtest_engine.run_backtest(
            self.strategies[0],
            market_data,
            asset.symbol
        )
        
        # Print results
        self.logger.info("=" * 60)
        self.logger.info("BACKTEST RESULTS")
        self.logger.info("=" * 60)
        self.logger.info(f"Initial Capital: ${result.initial_capital:,.2f}")
        self.logger.info(f"Final Capital:   ${result.final_capital:,.2f}")
        self.logger.info(f"Total Return:    {result.total_return:.2%}")
        self.logger.info(f"Total Trades:    {result.total_trades}")
        self.logger.info(f"Winning Trades:  {result.winning_trades}")
        self.logger.info(f"Losing Trades:   {result.losing_trades}")
        self.logger.info(f"Win Rate:        {result.win_rate:.2%}")
        self.logger.info(f"Max Drawdown:    {result.max_drawdown:.2%}")
        self.logger.info(f"Sharpe Ratio:    {result.sharpe_ratio:.2f}")
        self.logger.info(f"Sortino Ratio:   {result.sortino_ratio:.2f}")
        self.logger.info(f"Profit Factor:   {result.profit_factor:.2f}")
        self.logger.info("=" * 60)
        
        # Notify results
        for notifier in self.notifiers:
            try:
                message = (
                    f"*Backtest Results*\n\n"
                    f"Initial Capital: ${result.initial_capital:,.2f}\n"
                    f"Final Capital: ${result.final_capital:,.2f}\n"
                    f"Total Return: {result.total_return:.2%}\n"
                    f"Total Trades: {result.total_trades}\n"
                    f"Win Rate: {result.win_rate:.2%}\n"
                    f"Max Drawdown: {result.max_drawdown:.2%}\n"
                    f"Sharpe Ratio: {result.sharpe_ratio:.2f}"
                )
                await notifier.send_message(message)
            except Exception as e:
                self.logger.error(f"Error notifying backtest results: {e}")