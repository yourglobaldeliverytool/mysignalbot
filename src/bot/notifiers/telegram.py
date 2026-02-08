"""Telegram notifier."""

import asyncio
from typing import Dict, Any, Optional

from telegram import Bot
from telegram.error import TelegramError

from bot.notifiers.base import NotifierBase
from bot.core.logger import get_logger


class TelegramNotifier(NotifierBase):
    """Telegram notification service."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Telegram notifier."""
        super().__init__(config)
        self.logger = get_logger("notifiers.telegram")
        self.bot: Optional[Bot] = None
        
        telegram_config = config.get('telegram', {})
        self.bot_token = telegram_config.get('bot_token', '')
        self.chat_id = telegram_config.get('chat_id', '')
        
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
        if not self.enabled:
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
        if self.bot:
            try:
                await self.bot.shutdown()
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
        if not self.enabled or self.bot is None:
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=kwargs.get('parse_mode', 'Markdown')
            )
            self.logger.debug("Telegram message sent successfully")
            return True
        except TelegramError as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending Telegram message: {e}")
            return False