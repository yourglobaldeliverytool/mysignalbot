"""Main trading engine."""

import asyncio
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from bot.core.config import TradingBotConfig, load_config
from bot.core.models import (
    Signal, Order, OrderStatus, OrderType,
    Side, MarketData, Trade, Position, SignalType
)
from bot.core.logger import get_logger
from bot.core.exceptions import TradingBotError, ConnectorError
from bot.core.registry import registry_manager
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
        self.logger = get_logger("trading-bot.engine")

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

        # The ConnectorManager implementation in this repo expects a config dict
        # with a 'data_providers' key. Pass the full config as dict so manager
        # can read what it needs.
        try:
            cfg_dict = self.config.dict() if hasattr(self.config, "dict") else dict(self.config)
        except Exception:
            # As a fallback, attempt to load from yaml path
            cfg_dict = {}

        self.connector_manager = ConnectorManager(cfg_dict)

        # Connect all (will handle connector-specific connect logic)
        try:
            await self.connector_manager.connect_all()
        except Exception as e:
            self.logger.error(f"Error connecting connectors: {e}")
            # depending on severity, keep running (some connectors may be optional)

    async def _initialize_strategies(self) -> None:
        """Initialize trading strategies."""
        self.logger.info("Initializing strategies...")

        # Try to create strategies from registry if available, otherwise
        # fall back to a simple built-in placeholder strategy.
        from bot.strategies.base import StrategyBase as BaseStrategy

        class SimpleStrategy(BaseStrategy):
            """Simple placeholder strategy."""

            def __init__(self, cfg: Dict[str, Any]):
                super().__init__(cfg)
                self.name = cfg.get("name", "SimpleStrategy")

            async def initialize(self):
                # placeholder init if the base requires it
                return

            async def generate_signal(self, data: List[MarketData], current_price: float) -> Optional[Signal]:
                """Generate a simple signal (always 'hold' by default)."""
                asset = data[-1].symbol if data else "BTC/USD"
                return Signal(
                    asset=asset,
                    side=Side.BUY,
                    signal_type=SignalType.HOLD,
                    size=0.0,
                    entry_price=current_price,
                    take_profit=None,
                    stop_loss=None,
                    confidence_score=0.5,
                    strategy_source=self.name,
                )

            def get_min_periods(self) -> int:
                return 50

        # config.strategies is a Dict[str, StrategyConfig] (Pydantic)
        strategies_cfg = self.config.strategies or {}
        if isinstance(strategies_cfg, dict):
            for name, s_cfg in strategies_cfg.items():
                try:
                    # Prefer registry-created strategy if available
                    strategies_registry = registry_manager.get_registry("strategies")
                    if strategies_registry and strategies_registry.exists(name):
                        strategy = strategies_registry.create(name, s_cfg)
                        if strategy is None:
                            # fallback to simple strategy if factory failed
                            strategy = SimpleStrategy({"name": name})
                    else:
                        # fallback simple strategy
                        strategy = SimpleStrategy({"name": name})

                    # initialize if async initialize exists
                    if hasattr(strategy, "initialize"):
                        maybe = strategy.initialize()
                        if asyncio.iscoroutine(maybe):
                            await maybe

                    self.strategies.append(strategy)
                    self.logger.info(f"Initialized strategy: {getattr(strategy,'name',name)}")
                except Exception as e:
                    self.logger.error(f"Failed to initialize strategy {name}: {e}")
        else:
            self.logger.warning("No strategies configured (strategies must be a mapping)")

    async def _initialize_notifiers(self) -> None:
        """Initialize notification services."""
        self.logger.info("Initializing notifiers...")

        # Telegram notifier
        # config.notifications may contain a 'telegram' section or not depending on YAML
        try:
            telegram_section = {}
            if hasattr(self.config, "notifications") and getattr(self.config, "notifications", None):
                tconf = getattr(self.config, "notifications")
                # support both pydantic model and raw dict
                if hasattr(tconf, "dict"):
                    telegram_section = tconf.dict().get("daily_summary", {})  # avoid crash; default
                # More robust: read from raw config if available
            # Instead of assuming, attempt to get config dict safely
            raw_cfg = self.config.dict() if hasattr(self.config, "dict") else {}
            telegram_cfg = raw_cfg.get("notifications", {}).get("telegram", raw_cfg.get("api_credentials", {}).get("telegram", {}))
        except Exception:
            telegram_cfg = {}

        telegram_notifier = TelegramNotifier({"telegram": telegram_cfg})
        try:
            await telegram_notifier.connect()
            self.notifiers.append(telegram_notifier)
            if telegram_notifier.enabled:
                self.logger.info("Telegram notifier connected")
            else:
                self.logger.info("Telegram notifier initialized but disabled")
        except Exception as e:
            self.logger.warning(f"Failed to connect Telegram notifier: {e}")

        # Email notifier (best-effort)
        try:
            raw_cfg = self.config.dict() if hasattr(self.config, "dict") else {}
            email_cfg = raw_cfg.get("notifications", {}).get("email", {})
        except Exception:
            email_cfg = {}

        try:
            email_notifier = EmailNotifier({"email": email_cfg})
            await email_notifier.connect()
            self.notifiers.append(email_notifier)
            if getattr(email_notifier, "enabled", False):
                self.logger.info("Email notifier connected")
        except Exception as e:
            self.logger.warning(f"Failed to initialize/connect email notifier: {e}")

    async def start(self) -> None:
        """Start trading engine."""
        if not self._initialized:
            await self.initialize()

        self.logger.info("Starting trading engine...")
        self.logger.info(f"Mode: {self.config.mode}")

        if self.config.mode == "backtest":
            await self.run_backtest()
        elif self.config.mode in ["dry-run", "live"]:
            await self.run_trading_loop()
        else:
            raise ValueError(f"Unknown mode: {self.config.mode}")

    async def stop(self) -> None:
        """Stop trading engine."""
        self.logger.info("Stopping trading engine...")
        self._running = False

        # Disconnect connectors
        if self.connector_manager:
            try:
                await self.connector_manager.disconnect_all()
            except Exception as e:
                self.logger.error(f"Error disconnecting connectors: {e}")

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
                    if not getattr(asset, "enabled", True):
                        continue

                    try:
                        await self.process_asset(asset)
                    except Exception as e:
                        self.logger.error(f"Error processing asset {getattr(asset,'symbol',str(asset))}: {e}")

                # Wait for next iteration
                await asyncio.sleep(60)  # 1 minute interval

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Error in trading loop: {e}")
            raise
        finally:
            await self.stop()

    # Helper wrappers to cope with different connector manager method names
    async def _get_price(self, symbol: str) -> Optional[float]:
        """Attempt to get a price using available connector-manager methods."""
        if self.connector_manager is None:
            return None

        # try common method names with fallbacks
        if hasattr(self.connector_manager, "get_price"):
            try:
                return await self.connector_manager.get_price(symbol)
            except Exception as e:
                self.logger.debug(f"get_price failed: {e}")

        if hasattr(self.connector_manager, "get_price_with_failover"):
            try:
                price, _ = await self.connector_manager.get_price_with_failover(symbol)
                return price
            except Exception as e:
                self.logger.debug(f"get_price_with_failover failed: {e}")

        if hasattr(self.connector_manager, "get_aggregated_price"):
            try:
                price, meta = await self.connector_manager.get_aggregated_price(symbol)
                return price
            except Exception as e:
                self.logger.debug(f"get_aggregated_price failed: {e}")

        self.logger.error("No connector method available to get price")
        return None

    async def _get_market_data(self, symbol: str, timeframe: str = "1h", limit: int = 200) -> Optional[List[MarketData]]:
        """Attempt to get market data with available connector-manager methods."""
        if self.connector_manager is None:
            return None

        if hasattr(self.connector_manager, "get_market_data"):
            try:
                return await self.connector_manager.get_market_data(symbol, timeframe=timeframe, limit=limit)
            except Exception as e:
                self.logger.debug(f"get_market_data failed: {e}")

        if hasattr(self.connector_manager, "get_market_data_with_failover"):
            try:
                data, _ = await self.connector_manager.get_market_data_with_failover(symbol, timeframe=timeframe, limit=limit)
                return data
            except Exception as e:
                self.logger.debug(f"get_market_data_with_failover failed: {e}")

        self.logger.error("No connector method available to get market data")
        return None

    async def process_asset(self, asset) -> None:
        """Process a single asset.

        Args:
            asset: Asset configuration
        """
        # Get current price
        current_price = await self._get_price(getattr(asset, "symbol", asset))
        if current_price is None:
            self.logger.warning(f"Could not get price for {getattr(asset, 'symbol', asset)}")
            return

        # Get market data
        market_data = await self._get_market_data(getattr(asset, "symbol", asset), timeframe="1h", limit=200)
        if not market_data:
            self.logger.warning(f"Could not get market data for {getattr(asset, 'symbol', asset)}")
            return

        # Generate signals from strategies
        for strategy in self.strategies:
            # strategy may provide is_enabled or similar
            if hasattr(strategy, "is_enabled") and not strategy.is_enabled():
                continue

            try:
                maybe = strategy.generate_signal(market_data, current_price)
                if asyncio.iscoroutine(maybe):
                    signal = await maybe
                else:
                    signal = maybe

                if signal:
                    await self.process_signal(signal)
            except Exception as e:
                self.logger.error(f"Error generating signal from {getattr(strategy,'name','unknown')}: {e}")

    async def process_signal(self, signal: Signal) -> None:
        """Process trading signal.

        Args:
            signal: Trading signal
        """
        # Normalize names from Signal dataclass
        self.signals.append(signal)
        asset = getattr(signal, "asset", "UNKNOWN")
        confidence = getattr(signal, "confidence_score", getattr(signal, "confidence", 0.0))
        strategy_name = getattr(signal, "strategy_source", getattr(signal, "strategy_name", "unknown"))
        price = getattr(signal, "entry_price", getattr(signal, "price", None))

        self.logger.info(
            f"Received signal: {strategy_name} - {getattr(signal,'side').value.upper()} "
            f"{asset} @ {price if price is not None else 'N/A'} (confidence: {confidence:.2%})"
        )

        # ALWAYS notify so you see activity even when confidence is low
        notify_payload = {
            "asset": asset,
            "strategy": strategy_name,
            "side": getattr(signal, "side").value if getattr(signal, "side") else "N/A",
            "price": price,
            "confidence": confidence,
            "status": "below_threshold" if confidence < self.config.execution.min_confidence_threshold else "accepted"
        }

        for notifier in self.notifiers:
            try:
                # prefer high-level notify_signal if provided by notifier base
                if hasattr(notifier, "notify_signal"):
                    await notifier.notify_signal(signal)
                else:
                    # fallback: send a compact message
                    msg = (
                        f"Signal from {notify_payload['strategy']}\n"
                        f"{notify_payload['asset']} {notify_payload['side']}\n"
                        f"Price: {notify_payload['price']}\n"
                        f"Confidence: {notify_payload['confidence']:.2%}\n"
                        f"Status: {notify_payload['status']}"
                    )
                    await notifier.send_message(msg)
            except Exception as e:
                self.logger.error(f"Error notifying signal with {notifier}: {e}")

        # If below confidence threshold, do not execute orders but still log / notify as above
        if confidence < self.config.execution.min_confidence_threshold:
            self.logger.info("Signal confidence below threshold; not executing order (notification already sent).")
            return

        # Execute signal based on mode
        if self.config.mode == "live":
            await self.execute_order(signal)
        else:  # dry-run
            await self.simulate_order(signal)

    async def execute_order(self, signal: Signal) -> None:
        """Execute live order.

        Args:
            signal: Trading signal
        """
        # Minimal placeholder — real implementation should place orders via connectors
        self.logger.warning("Live trading not implemented in this version")

    async def simulate_order(self, signal: Signal) -> None:
        """Simulate order (dry-run).

        Args:
            signal: Trading signal
        """
        order_id = str(uuid.uuid4())
        price = getattr(signal, "entry_price", None)
        # Determine position sizing: prefer fixed_amount if present
        ps = getattr(self.config, "risk_management", None)
        fixed_amount = None
        try:
            if ps and hasattr(ps, "position_sizing") and hasattr(ps.position_sizing, "fixed_amount"):
                fixed_amount = ps.position_sizing.fixed_amount
        except Exception:
            fixed_amount = None

        if not fixed_amount:
            # fallback default
            fixed_amount = 100.0

        quantity = 0.0
        if price and price > 0:
            quantity = fixed_amount / price

        order = Order(
            order_id=order_id,
            asset=getattr(signal, "asset", "UNKNOWN"),
            side=getattr(signal, "side"),
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=price,
            status=OrderStatus.FILLED,
            filled_quantity=quantity,
            filled_price=price,
            timestamp=datetime.utcnow(),
            signal_id=None,
            exchange_order_id=None,
            fees=0.0,
            metadata={"simulated": True, "strategy": getattr(signal, "strategy_source", None)}
        )

        self.orders.append(order)
        self.logger.info(f"Simulated order: {order.side.value.upper()} {order.quantity:.6f} {order.asset} @ {order.price if order.price else 'N/A'}")

    async def run_backtest(self) -> None:
        """Run backtest."""
        self.logger.info("Running backtest...")

        backtest_config = {
            "initial_capital": getattr(self.config.backtesting, "initial_capital", 10000.0),
            "commission": getattr(self.config.backtesting, "commission", 0.0),
            "slippage": getattr(self.config.backtesting, "slippage", 0.0),
        }

        backtest_engine = BacktestEngine(backtest_config)

        # Get historical data
        asset = self.config.assets[0] if self.config.assets else None
        if not asset:
            self.logger.error("No assets configured for backtest")
            return

        market_data = await self._get_market_data(getattr(asset, "symbol", asset), timeframe="1h", limit=1000)

        if not market_data or len(market_data) < 100:
            self.logger.error("Not enough data for backtest")
            return

        # Run backtest with first strategy
        if not self.strategies:
            self.logger.error("No strategies configured for backtest")
            return

        # Backtest engine API may vary — attempt common signature
        try:
            result = await backtest_engine.run_backtest(self.strategies[0], market_data, getattr(asset, "symbol", "UNKNOWN"))
        except TypeError:
            # Try alternate signature
            result = await backtest_engine.run_backtest(market_data, self.strategies[0], getattr(asset, "symbol", "UNKNOWN"))

        # Print results (handle attribute access defensively)
        self.logger.info("=" * 60)
        self.logger.info("BACKTEST RESULTS")
        self.logger.info("=" * 60)
        try:
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
        except Exception:
            # If result is a dict-like
            try:
                r = result if isinstance(result, dict) else getattr(result, "to_dict", lambda: {})()
                self.logger.info(f"Initial Capital: ${r.get('initial_capital', 0):,.2f}")
                self.logger.info(f"Final Capital:   ${r.get('final_capital', 0):,.2f}")
            except Exception as e:
                self.logger.error(f"Unable to print backtest results: {e}")

        self.logger.info("=" * 60)

        # Notify results
        for notifier in self.notifiers:
            try:
                message = (
                    f"*Backtest Results*\n\n"
                    f"Initial Capital: ${getattr(result, 'initial_capital', 'N/A')}\n"
                    f"Final Capital: {getattr(result, 'final_capital', 'N/A')}\n"
                )
                if hasattr(notifier, "send_message"):
                    await notifier.send_message(message)
            except Exception as e:
                self.logger.error(f"Error notifying backtest results: {e}")
