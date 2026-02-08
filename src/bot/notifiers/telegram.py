"""Telegram notifier."""

import asyncio
from typing import Dict, Any, Optional

from telegram import Bot
from telegram.error import TelegramError

from bot.notifiers.base import NotifierBase
from bot.core.logger import get_logger
from bot.core.models import Signal


class TelegramNotifier(NotifierBase):
    """Telegram notification service."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Telegram notifier."""
        # NotifierBase may expect a config dict - pass through
        super().__init__(config)
        self.logger = get_logger("trading-bot.notifiers.telegram")
        self.bot: Optional[Bot] = None

        telegram_config = {}
        if isinstance(config, dict):
            # support either {"telegram": {...}} or raw telegram dict
            telegram_config = config.get("telegram", config)

        self.bot_token = telegram_config.get("bot_token", "") if telegram_config else ""
        self.chat_id = telegram_config.get("chat_id", "") if telegram_config else ""

        # CRITICAL: Handle missing credentials gracefully
        # Log warning and disable if token or chat_id is missing
        if not self.bot_token or not self.chat_id:
            self.enabled = False
            self.logger.warning(
                "Telegram notifier disabled: missing required credentials. "
                "Please provide bot_token and chat_id in configuration."
            )
            return

        # Initialize bot but don't connect yet
        try:
            self.bot = Bot(token=self.bot_token)
        except Exception as e:
            self.enabled = False
            self.logger.warning(f"Telegram notifier disabled: failed to initialize bot: {e}")

    async def connect(self) -> None:
        """Connect to Telegram API."""
        if not getattr(self, "enabled", True):
            self.logger.info("Telegram notifier is disabled")
            return

        if self.bot is None:
            self.logger.warning("Telegram bot not initialized")
            self.enabled = False
            return

        try:
            # Verify bot by getting bot info
            await self.bot.get_me()
            self.logger.info("Connected to Telegram successfully")
            self._initialized = True
        except TelegramError as e:
            # CRITICAL: Do not crash, just log and disable
            self.logger.error(f"Failed to connect to Telegram: {e}")
            self.enabled = False
            self.logger.warning("Telegram notifier disabled due to connection error")
        except Exception as e:
            # CRITICAL: Do not crash, just log and disable
            self.logger.error(f"Unexpected error connecting to Telegram: {e}")
            self.enabled = False
            self.logger.warning("Telegram notifier disabled due to unexpected error")

    async def disconnect(self) -> None:
        """Disconnect from Telegram API."""
        # Bot doesn't have a strict disconnect method in some versions; best-effort
        if self.bot:
            try:
                # If the bot has a close/shutdown method, call it
                if hasattr(self.bot, "shutdown"):
                    await self.bot.shutdown()
                elif hasattr(self.bot, "session") and hasattr(self.bot.session, "close"):
                    await self.bot.session.close()
            except Exception as e:
                self.logger.error(f"Error disconnecting from Telegram: {e}")
        self.logger.info("Telegram notifier disconnected")

    async def send_message(self, message: str, **kwargs) -> bool:
        """Send Telegram message.

        Args:
            message: Message to send
            **kwargs: Additional parameters (parse_mode, etc.)

        Returns:
            True if successful, False otherwise
        """
        if not getattr(self, "enabled", False) or self.bot is None:
            self.logger.debug("Telegram notifier not enabled or bot not initialized - message skipped")
            return False

        try:
            parse_mode = kwargs.get("parse_mode", "Markdown")
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode=parse_mode)
            self.logger.debug("Telegram message sent successfully")
            return True
        except TelegramError as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending Telegram message: {e}")
            return False

    async def notify_signal(self, signal: Signal) -> bool:
        """High-level helper to format and send a signal notification."""
        try:
            asset = getattr(signal, "asset", "UNKNOWN")
            confidence = getattr(signal, "confidence_score", getattr(signal, "confidence", 0.0))
            strategy = getattr(signal, "strategy_source", getattr(signal, "strategy_name", "unknown"))
            entry = getattr(signal, "entry_price", getattr(signal, "price", None))

            emoji = "🟢" if getattr(signal, "side", None) and getattr(signal.side, "value", "") == "buy" else "🔴"
            status = "ACCEPTED" if confidence >= getattr(getattr(self, "config", {}), "get", lambda k, d=None: d)("min_confidence_threshold", 0.0) else "LOW_CONFIDENCE"

            message = (
                f"{emoji} *Trading Signal*\n\n"
                f"*Asset:* {asset}\n"
                f"*Side:* {getattr(signal.side, 'value', 'N/A').upper()}\n"
                f"*Strategy:* {strategy}\n"
                f"*Entry:* {entry if entry is not None else 'N/A'}\n"
                f"*Confidence:* {confidence:.2%}\n"
                f"*Status:* {status}"
            )

            return await self.send_message(message, parse_mode="Markdown")
        except Exception as e:
            self.logger.error(f"Error formatting/sending signal notification: {e}")
            return False
