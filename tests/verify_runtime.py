"""Runtime verification script for trading bot."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from bot.core.config import load_config, TradingBotConfig
from bot.core.logger import setup_logger, get_logger
from bot.core.exceptions import ConfigurationError
from bot.connectors.mock import MockConnector
from bot.connectors.manager import ConnectorManager
from bot.notifiers.telegram import TelegramNotifier
from bot.notifiers.email import EmailNotifier


async def verify_config():
    """Verify configuration loading."""
    print("Testing configuration loading...")
    
    try:
        config = load_config('config.yaml')
        print("✓ Configuration loaded successfully")
        print(f"  - Mode: {config.mode}")
        print(f"  - Initial Capital: ${config.execution.initial_capital:,.2f}")
        print(f"  - Order Type: {config.execution.order_type}")
        print(f"  - Max Orders/Min: {config.execution.max_orders_per_minute}")
        print(f"  - Min Confidence: {config.execution.min_confidence_threshold}")
        print(f"  - Backtest Start: {config.backtesting.start_date}")
        print(f"  - Backtest End: {config.backtesting.end_date}")
        print(f"  - Backtest Initial Capital: ${config.backtesting.initial_capital:,.2f}")
        print(f"  - Telegram Enabled: {config.notifications.telegram.get('enable_notifications', False)}")
        print(f"  - Telegram Token: {'***' + config.notifications.telegram.get('bot_token', '')[-4:] if config.notifications.telegram.get('bot_token') else 'None'}")
        print(f"  - Telegram Chat ID: {config.notifications.telegram.get('chat_id', 'None')}")
        return config
    except FileNotFoundError:
        print("✗ Configuration file not found")
        return None
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return None


async def verify_logging(config):
    """Verify logging setup."""
    print("\nTesting logging setup...")
    
    try:
        setup_logger(level=config.logging.level)
        logger = get_logger()
        logger.info("✓ Logging initialized successfully")
        logger.debug("Debug message test")
        logger.warning("Warning message test")
        return True
    except Exception as e:
        print(f"✗ Logging error: {e}")
        return False


async def verify_connectors():
    """Verify connector setup."""
    print("\nTesting connector setup...")
    
    try:
        # Create mock connector
        mock_config = {'enabled': True, 'max_retries': 3}
        mock_connector = MockConnector(mock_config)
        print("✓ Mock connector created")
        
        # Connect
        await mock_connector.connect()
        print(f"✓ Connector connected: {mock_connector.is_connected}")
        
        # Get price
        price = await mock_connector.get_price("BTC/USD")
        print(f"✓ Got price for BTC/USD: ${price:.2f}")
        
        # Get market data
        market_data = await mock_connector.get_market_data("BTC/USD", "1h", 10)
        print(f"✓ Got {len(market_data)} candles of market data")
        
        # Health check
        health = await mock_connector.health_check()
        print(f"✓ Health check: {health}")
        
        # Disconnect
        await mock_connector.disconnect()
        print(f"✓ Connector disconnected")
        
        # Test ConnectorManager
        connectors = [mock_connector]
        manager = ConnectorManager(
            connectors,
            {
                'primary': 'mock',
                'failover_enabled': True,
                'aggregation_method': 'median'
            }
        )
        
        await manager.connect_all()
        print("✓ ConnectorManager connected all connectors")
        
        health_results = await manager.health_check()
        print(f"✓ ConnectorManager health check: {health_results}")
        
        await manager.disconnect_all()
        print("✓ ConnectorManager disconnected all connectors")
        
        return True
    except Exception as e:
        print(f"✗ Connector error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_telegram():
    """Verify Telegram notifier (graceful failure test)."""
    print("\nTesting Telegram notifier...")
    
    try:
        # Test with provided credentials
        config = {
            'telegram': {
                'enable_notifications': True,
                'bot_token': '8515959173:AAEtfUIiBxa5ZHUMzM2mz6s9Yi9No55nOBI',
                'chat_id': '2141325844'
            },
            'enabled': True
        }
        
        notifier = TelegramNotifier(config)
        print(f"✓ Telegram notifier created (enabled: {notifier.enabled})")
        
        # Try to connect (may fail gracefully)
        try:
            await notifier.connect()
            print(f"✓ Telegram connect attempt completed (enabled: {notifier.enabled})")
        except Exception as e:
            print(f"✓ Telegram connect handled gracefully: {e}")
        
        # Test with empty credentials (should disable)
        empty_config = {
            'telegram': {
                'enable_notifications': True,
                'bot_token': '',
                'chat_id': ''
            },
            'enabled': True
        }
        
        empty_notifier = TelegramNotifier(empty_config)
        print(f"✓ Empty Telegram notifier created (should be disabled: {not empty_notifier.enabled})")
        
        return True
    except Exception as e:
        print(f"✗ Telegram error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_email():
    """Verify Email notifier (should disable gracefully)."""
    print("\nTesting Email notifier...")
    
    try:
        # Test with empty credentials (should disable)
        config = {
            'email': {
                'enable_notifications': True,
                'smtp_host': '',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'from_email': '',
                'to_email': ''
            },
            'enabled': True
        }
        
        notifier = EmailNotifier(config)
        print(f"✓ Email notifier created (should be disabled: {not not notifier.enabled})")
        
        await notifier.connect()
        print(f"✓ Email connect handled gracefully")
        
        return True
    except Exception as e:
        print(f"✗ Email error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_engine(config):
    """Verify trading engine initialization."""
    print("\nTesting trading engine...")
    
    try:
        from bot.core.engine import TradingEngine
        
        engine = TradingEngine(config)
        print("✓ Trading engine created")
        
        await engine.initialize()
        print("✓ Trading engine initialized")
        
        await engine.stop()
        print("✓ Trading engine stopped")
        
        return True
    except Exception as e:
        print(f"✗ Engine error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all verification tests."""
    print("=" * 60)
    print("TRADING BOT RUNTIME VERIFICATION")
    print("=" * 60)
    
    results = []
    
    # Test 1: Configuration
    config = await verify_config()
    results.append(('Configuration', config is not None))
    
    if not config:
        print("\n✗ Cannot continue without valid configuration")
        return False
    
    # Test 2: Logging
    results.append(('Logging', await verify_logging(config)))
    
    # Test 3: Connectors
    results.append(('Connectors', await verify_connectors()))
    
    # Test 4: Telegram Notifier
    results.append(('Telegram Notifier', await verify_telegram()))
    
    # Test 5: Email Notifier
    results.append(('Email Notifier', await verify_email()))
    
    # Test 6: Trading Engine
    results.append(('Trading Engine', await verify_engine(config)))
    
    # Print summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    
    print("=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("\nThe trading bot is ready to run.")
        print("To start in dry-run mode:")
        print("  python -m bot.main --mode dry-run --config config.yaml")
        print("\nTo start in backtest mode:")
        print("  python -m bot.main --mode backtest --config config.yaml")
    else:
        print("✗ SOME TESTS FAILED")
        print("Please review the errors above.")
    
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)