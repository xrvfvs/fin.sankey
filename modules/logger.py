# -*- coding: utf-8 -*-
"""
Logging configuration for the Financial Sankey application.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(
    name: str = "fin_sankey",
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_dir: str = "logs"
) -> logging.Logger:
    """
    Set up and configure a logger instance.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to also log to a file
        log_dir: Directory for log files

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_to_file:
        try:
            log_path = Path(log_dir)
            log_path.mkdir(exist_ok=True)

            log_file = log_path / f"fin_sankey_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not set up file logging: {e}")

    return logger


# Create default logger instance
logger = setup_logger()


def log_error(error: Exception, context: str = "", extra_data: dict = None):
    """
    Log an error with context and optional extra data.

    Args:
        error: The exception to log
        context: Description of what was happening when error occurred
        extra_data: Additional data to include in the log
    """
    msg = f"{context}: {type(error).__name__}: {str(error)}"
    if extra_data:
        msg += f" | Data: {extra_data}"
    logger.error(msg, exc_info=True)


def log_warning(message: str, extra_data: dict = None):
    """Log a warning message with optional extra data."""
    if extra_data:
        message += f" | Data: {extra_data}"
    logger.warning(message)


def log_info(message: str):
    """Log an info message."""
    logger.info(message)


def log_debug(message: str, extra_data: dict = None):
    """Log a debug message with optional extra data."""
    if extra_data:
        message += f" | Data: {extra_data}"
    logger.debug(message)


def log_api_call(api_name: str, ticker: str = None, success: bool = True, duration_ms: float = None):
    """
    Log an API call for monitoring.

    Args:
        api_name: Name of the API being called
        ticker: Stock ticker if applicable
        success: Whether the call succeeded
        duration_ms: Duration in milliseconds
    """
    status = "SUCCESS" if success else "FAILED"
    msg = f"API Call | {api_name} | {status}"
    if ticker:
        msg += f" | Ticker: {ticker}"
    if duration_ms is not None:
        msg += f" | Duration: {duration_ms:.2f}ms"

    if success:
        logger.info(msg)
    else:
        logger.warning(msg)


def log_user_action(action: str, user_id: str = None, details: dict = None):
    """
    Log user actions for analytics.

    Args:
        action: Description of the action
        user_id: User identifier (optional, for logged-in users)
        details: Additional details about the action
    """
    msg = f"User Action | {action}"
    if user_id:
        msg += f" | User: {user_id}"
    if details:
        msg += f" | Details: {details}"
    logger.info(msg)
