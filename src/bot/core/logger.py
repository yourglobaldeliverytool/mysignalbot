"""Logging configuration."""

import logging
import sys
from typing import Optional
from pathlib import Path


def setup_logger(
    name: str = "trading-bot",
    level: str = "INFO",
    log_format: Optional[str] = None,
    log_file: Optional[str] = None,
    rotation: bool = True
) -> logging.Logger:
    """Setup logger with console and optional file handlers."""
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Default format
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    formatter = logging.Formatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        if rotation:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5
            )
        else:
            file_handler = logging.FileHandler(log_file)
        
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Global logger instance
_logger: Optional[logging.Logger] = None


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get global logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_logger()
    
    if name:
        return logging.getLogger(f"{_logger.name}.{name}")
    return _logger