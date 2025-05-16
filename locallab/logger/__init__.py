"""
Logging utilities for LocalLab
"""

import logging
import sys
import os
import re
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

# Define subdued colors for less important logs
class Colors:
    # Bright colors for important messages
    BRIGHT_CYAN = Fore.CYAN
    BRIGHT_GREEN = Fore.GREEN
    BRIGHT_YELLOW = Fore.YELLOW
    BRIGHT_RED = Fore.RED

    # Subdued colors for regular logs - using lighter shades
    SUBDUED_DEBUG = Fore.CYAN + Style.DIM  # Dimmed cyan for debug
    SUBDUED_INFO = Fore.WHITE  # White for info (not dimmed)
    SUBDUED_WARNING = Fore.YELLOW + Style.DIM  # Dimmed yellow for warnings
    SUBDUED_ERROR = Fore.RED + Style.DIM  # Dimmed red for errors

    # Special colors for very unimportant logs
    VERY_SUBDUED = Fore.LIGHTBLACK_EX  # Light gray for very unimportant logs

    # Reset
    RESET = Style.RESET_ALL

# Patterns for important log messages that should stand out
IMPORTANT_PATTERNS = [
    # Server status messages
    r'Server status changed to',
    r'SERVER (READY|STARTING)',
    r'Starting server on port',
    r'Server startup',
    r'Application startup complete',

    # Model-related messages
    r'Model loaded',
    r'Loading model',
    r'Model configuration',

    # Error and warning messages
    r'Error',
    r'Exception',
    r'Failed',
    r'CRITICAL',
    r'WARNING',

    # Ngrok-related messages
    r'NGROK TUNNEL ACTIVE',
    r'Ngrok tunnel established',

    # Other important messages
    r'FastAPI application startup',
    r'HuggingFace token',
    r'SERVER READY',
    r'INITIALIZING'
]

# Compiled regex patterns for performance
IMPORTANT_REGEX = [re.compile(pattern, re.IGNORECASE) for pattern in IMPORTANT_PATTERNS]

# Define formatters
class SubduedColoredFormatter(logging.Formatter):
    """Formatter that adds subdued colors to regular logs and bright colors to important logs"""

    def format(self, record):
        # Check if this is a HuggingFace Hub progress bar log
        # HuggingFace progress bars use tqdm which writes directly to stdout/stderr
        # We need to completely bypass our logger for these messages

        # First, check if this is a HuggingFace-related log
        is_hf_log = False
        if hasattr(record, 'name') and isinstance(record.name, str):
            # HuggingFace Hub logs typically come from these modules
            hf_modules = ['huggingface_hub', 'filelock', 'transformers', 'tqdm', 'accelerate', 'bitsandbytes']
            is_hf_log = any(module in record.name for module in hf_modules)

        # Also check if the message contains download-related content
        is_download_log = False
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            download_patterns = ['download', 'fetch', 'safetensors', '.bin', '.json', 'model-', 'pytorch_model',
                               'Fetching', 'files:', 'it/s', 'B/s', '%', 'MB/s', 'GB/s']
            is_download_log = any(pattern in str(record.msg).lower() for pattern in download_patterns)

        # If this is a HuggingFace download log or tqdm progress bar, skip it completely
        # This ensures HuggingFace's native progress bars are displayed correctly
        if is_hf_log or is_download_log or (hasattr(record, 'msg') and '%' in str(record.msg) and ('/' in str(record.msg))):
            return ""

        # Check if we're currently downloading a model
        try:
            from ..utils.progress import is_model_downloading

            # During model downloads, only show critical logs and important model-related logs
            if is_model_downloading() and record.levelno < logging.ERROR:
                # Check if this is a model-related log that should be shown
                is_model_log = False
                if hasattr(record, 'msg') and isinstance(record.msg, str):
                    model_patterns = ['model loaded', 'tokenizer loaded', 'loading complete']
                    is_model_log = any(pattern in str(record.msg).lower() for pattern in model_patterns)

                # Skip non-critical and non-model logs during model download
                if not is_model_log:
                    return ""
        except (ImportError, AttributeError):
            # If we can't import the function, continue as normal
            pass

        # Check if this is an important message that should stand out
        is_important = False

        # Check message content against important patterns
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for pattern in IMPORTANT_REGEX:
                if pattern.search(record.msg):
                    is_important = True
                    break

        # Special case for certain types of logs - make them very subdued
        is_ngrok_log = hasattr(record, 'name') and record.name.startswith('pyngrok')
        is_uvicorn_log = hasattr(record, 'name') and record.name.startswith('uvicorn')

        # Determine the appropriate color based on log level and importance
        if is_ngrok_log or is_uvicorn_log:
            # Make ngrok and uvicorn logs subdued but still readable (light gray)
            color = Colors.VERY_SUBDUED
        elif record.levelno == logging.DEBUG:
            color = Colors.BRIGHT_CYAN if is_important else Colors.SUBDUED_DEBUG
        elif record.levelno == logging.INFO:
            color = Colors.BRIGHT_GREEN if is_important else Colors.SUBDUED_INFO
        elif record.levelno == logging.WARNING:
            color = Colors.BRIGHT_YELLOW if is_important else Colors.SUBDUED_WARNING
        elif record.levelno >= logging.ERROR:  # ERROR and CRITICAL
            color = Colors.BRIGHT_RED  # Always use bright red for errors
        else:
            color = Colors.SUBDUED_INFO  # Default

        # Format with the appropriate color
        formatted_message = f'{color}%(asctime)s - %(name)s - %(levelname)s - %(message)s{Colors.RESET}'
        formatter = logging.Formatter(formatted_message)
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
        handler.setFormatter(SubduedColoredFormatter())
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