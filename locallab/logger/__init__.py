"""
Logging utilities for LocalLab
"""

import logging
import sys
from colorama import Fore, Style

# Configure default logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Cache for loggers to avoid creating multiple instances
_loggers = {}


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name
    
    Args:
        name: Logger name, typically using dot notation (e.g., "locallab.server")
        
    Returns:
        Configured logger instance
    """
    if name in _loggers:
        return _loggers[name]
    
    logger = logging.getLogger(name)
    
    # Add a stream handler with colorized output if not already present
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        # Define a formatter that adds colors
        class ColoredFormatter(logging.Formatter):
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
        
        handler.setFormatter(ColoredFormatter())
        logger.addHandler(handler)
    
    # Cache the logger
    _loggers[name] = logger
    
    return logger 