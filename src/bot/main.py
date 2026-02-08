"""Main entrypoint for the trading bot."""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.core.config import load_config, TradingBotConfig
from bot.core.engine import TradingEngine
from bot.core.logger import setup_logger, get_logger


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Multi-Strategy Trading Bot")
    parser.add_argument(
        '--config', 
        type=str, 
        default='config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--mode',
        type=str,
        choices=['dry-run', 'backtest', 'live'],
        help='Trading mode (overrides config)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Log level (overrides config)'
    )
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Override mode if specified
        if args.mode:
            config.mode = args.mode
        
        # Override log level if specified
        if args.log_level:
            config.logging.level = args.log_level
        
        # Setup logging
        setup_logger(
            level=config.logging.level,
            log_format=config.logging.format,
            log_file=config.logging.file,
            rotation=config.logging.rotation
        )
        
        logger = get_logger()
        logger.info("Configuration loaded successfully")
        logger.info(f"Trading mode: {config.mode}")
        logger.info(f"Initial capital: ${config.execution.initial_capital:,.2f}")
        
        # Create and start trading engine
        engine = TradingEngine(config)
        await engine.start()
        
    except FileNotFoundError as e:
        print(f"Error: Configuration file not found: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())