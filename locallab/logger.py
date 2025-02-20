import logging
from colorama import Fore, Style, init
from .config import LOG_LEVEL, LOG_FORMAT

# Initialize colorama
init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output"""
    
    COLORS = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        # Add color to the level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)

def setup_logger(name: str = "LocalLab") -> logging.Logger:
    """Set up and return a logger instance with colored output"""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Create console handler with colored formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter(LOG_FORMAT))
    
    # Remove any existing handlers and add our console handler
    logger.handlers = []
    logger.addHandler(console_handler)
    
    return logger

# Create the default logger instance
logger = setup_logger()
