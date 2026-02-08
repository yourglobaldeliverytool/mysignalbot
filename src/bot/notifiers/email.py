"""Email notifier."""

import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any

from bot.notifiers.base import NotifierBase
from bot.core.logger import get_logger


class EmailNotifier(NotifierBase):
    """Email notification service."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize email notifier."""
        super().__init__(config)
        self.logger = get_logger("notifiers.email")
        
        email_config = config.get('email', {})
        self.smtp_host = email_config.get('smtp_host', '')
        self.smtp_port = email_config.get('smtp_port', 587)
        self.username = email_config.get('username', '')
        self.password = email_config.get('password', '')
        self.from_email = email_config.get('from_email', '')
        self.to_email = email_config.get('to_email', '')
        
        # Disable if credentials missing
        if not all([self.smtp_host, self.username, self.password, self.from_email, self.to_email]):
            self.enabled = False
            self.logger.warning("Email notifier disabled: missing required credentials")
    
    async def connect(self) -> None:
        """Connect to SMTP server."""
        if not self.enabled:
            self.logger.warning("Email notifier is disabled")
            return
        
        self.logger.info("Email notifier ready (connection on send)")
        self._initialized = True
    
    async def disconnect(self) -> None:
        """Disconnect from SMTP server."""
        self.logger.info("Email notifier disconnected")
    
    async def send_message(self, message: str, **kwargs) -> bool:
        """Send email message.
        
        Args:
            message: Message body
            **kwargs: Additional parameters (subject, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_sync, message, **kwargs)
            self.logger.info("Email sent successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False
    
    def _send_sync(self, message: str, subject: str = "Trading Bot Notification", **kwargs) -> None:
        """Send email synchronously."""
        msg = MIMEMultipart()
        msg['From'] = self.from_email
        msg['To'] = self.to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain'))
        
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)