"""
Logging utilities for LocalLab
"""

import logging
import sys
import os
from colorama import Fore, Style, init as colorama_init

# Initialize colorama with autoreset
colorama_init(autoreset=True)

# Cache for loggers to avoid creating multiple instances
_loggers = {}
_root_logger_configured = False

# Detect if terminal supports colors
def supports_color():
    """
    Check if the terminal supports color output.
    Returns True if color is supported, False otherwise.
    """
    # Check if NO_COLOR environment variable is set (standard for disabling color)
    if os.environ.get('NO_COLOR') is not None:
        return False

    # Check if FORCE_COLOR environment variable is set (force color even if not detected)
    if os.environ.get('FORCE_COLOR') is not None:
        return True

    # Check if output is a TTY
    if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        return True

    # Check common environment variables that indicate color support
    if os.environ.get('TERM') == 'dumb':
        return False

    if os.environ.get('COLORTERM') is not None:
        return True

    if os.environ.get('TERM_PROGRAM') in ['iTerm.app', 'Apple_Terminal', 'vscode']:
        return True

    # Default to no color if we can't determine
    return False

# Use color only if supported
USE_COLOR = supports_color()

# Define formatters
class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors to log messages"""
    FORMATS = {
        logging.DEBUG: f'{Fore.CYAN}%(asctime)s - %(name)s - %(levelname)s - %(message)s{Style.RESET_ALL}',
        logging.INFO: f'{Fore.GREEN}%(asctime)s - %(name)s - %(levelname)s - %(message)s{Style.RESET_ALL}',
        logging.WARNING: f'{Fore.YELLOW}%(asctime)s - %(name)s - %(levelname)s - %(message)s{Style.RESET_ALL}',
        logging.ERROR: f'{Fore.RED}%(asctime)s - %(name)s - %(levelname)s - %(message)s{Style.RESET_ALL}',
        logging.CRITICAL: f'{Fore.RED}{Style.BRIGHT}%(asctime)s - %(name)s - %(levelname)s - %(message)s{Style.RESET_ALL}'
    }

    def format(self, record):
        log_format = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_format)
        return formatter.format(record)

# Plain formatter without colors
PLAIN_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
plain_formatter = logging.Formatter(PLAIN_FORMAT)

def configure_root_logger():
    """Configure the root logger to prevent duplicate handlers"""
    global _root_logger_configured

    if _root_logger_configured:
        return

    # Get the root logger
    root_logger = logging.getLogger()

    # Remove any existing handlers to prevent duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add a single handler with appropriate formatter
    handler = logging.StreamHandler(sys.stdout)

    if USE_COLOR:
        handler.setFormatter(ColoredFormatter())
    else:
        handler.setFormatter(plain_formatter)

    root_logger.addHandler(handler)

    # Set the level
    root_logger.setLevel(logging.INFO)

    _root_logger_configured = True

# Configure the root logger on import
configure_root_logger()

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name

    Args:
        name: Logger name, typically using dot notation (e.g., "locallab.server")

    Returns:
        Configured logger instance
    """
    # Ensure root logger is configured
    configure_root_logger()

    # Return cached logger if available
    if name in _loggers:
        return _loggers[name]

    # Get or create the logger
    logger = logging.getLogger(name)

    # Remove any existing handlers to prevent duplication
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Don't add handlers to non-root loggers - they will inherit from root
    # This prevents duplicate log messages

    # Cache the logger
    _loggers[name] = logger

    return logger