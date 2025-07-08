"""
Early configuration module for LocalLab.
This module is imported before any other modules to configure logging and environment variables.
"""

import os
import sys
import logging
import warnings

# Configure environment variables for Hugging Face
# Only enable HF Transfer if the package is available
try:
    import hf_transfer
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"  # Enable HF Transfer for better downloads
except ImportError:
    # hf_transfer not available, disable it to avoid errors
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

os.environ["TOKENIZERS_PARALLELISM"] = "true"  # Enable parallelism for tokenizers
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"  # Disable advisory warnings
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"  # Disable telemetry

# Configure tqdm to use the best available display method
os.environ["TQDM_DISABLE"] = "0"  # Ensure tqdm is not disabled
os.environ["TQDM_MININTERVAL"] = "0.1"  # Update progress bars more frequently

# Configure Hugging Face logging before importing any HF libraries
def configure_hf_logging():
    """
    Configure Hugging Face logging before any HF libraries are imported.
    This ensures that HF's progress bars are displayed correctly.
    """
    # Disable all warnings
    warnings.filterwarnings("ignore")

    # Configure logging for Hugging Face libraries
    for logger_name in ["transformers", "huggingface_hub", "accelerate", "tqdm", "filelock"]:
        hf_logger = logging.getLogger(logger_name)
        hf_logger.setLevel(logging.WARNING)  # Only show warnings and errors
        hf_logger.propagate = False  # Don't propagate to parent loggers

        # Remove any existing handlers
        for handler in hf_logger.handlers[:]:
            hf_logger.removeHandler(handler)

        # Add a null handler to prevent warnings about no handlers
        hf_logger.addHandler(logging.NullHandler())

# Run configuration immediately on import
configure_hf_logging()

# Function to temporarily redirect stdout/stderr during model downloads
class StdoutRedirector:
    """
    Context manager to temporarily redirect stdout/stderr during model downloads.
    This ensures that tqdm progress bars are displayed correctly.
    """
    def __init__(self, disable_logging=True):
        self.disable_logging = disable_logging
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.original_log_levels = {}

    def __enter__(self):
        # Store original log levels
        if self.disable_logging:
            for logger_name in ["transformers", "huggingface_hub", "accelerate", "tqdm", "filelock"]:
                logger = logging.getLogger(logger_name)
                self.original_log_levels[logger_name] = logger.level
                logger.setLevel(logging.WARNING)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original log levels
        if self.disable_logging:
            for logger_name, level in self.original_log_levels.items():
                logging.getLogger(logger_name).setLevel(level)

# Function to enable Hugging Face progress bars
def enable_hf_progress_bars():
    """
    Enable Hugging Face progress bars.
    Call this function before downloading models.
    """
    # Configure tqdm
    try:
        import tqdm
        tqdm.tqdm.monitor_interval = 0  # Disable monitor thread
    except ImportError:
        pass

    # Configure huggingface_hub progress bars
    try:
        import huggingface_hub
        import os

        # Different versions of huggingface_hub have different ways to enable progress bars
        # Try multiple approaches to ensure compatibility
        progress_enabled = False

        # Method 1: Try direct module function (newer versions)
        if hasattr(huggingface_hub, "enable_progress_bars"):
            try:
                huggingface_hub.enable_progress_bars()
                progress_enabled = True
            except Exception:
                pass

        # Method 2: Try through utils.logging (older versions)
        if not progress_enabled:
            try:
                from huggingface_hub.utils import logging as hf_logging
                if hasattr(hf_logging, "enable_progress_bars"):
                    hf_logging.enable_progress_bars()
                    progress_enabled = True
            except (ImportError, AttributeError):
                pass

        # Method 3: Use environment variable as fallback
        if not progress_enabled:
            os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"

        # Method 3: Set environment variable (works for all versions)
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"

        # Also enable HF Transfer for better download experience (only if available)
        if hasattr(huggingface_hub, "constants"):
            try:
                import hf_transfer
                huggingface_hub.constants.HF_HUB_ENABLE_HF_TRANSFER = True
            except ImportError:
                # hf_transfer not available, don't enable it
                huggingface_hub.constants.HF_HUB_ENABLE_HF_TRANSFER = False
    except ImportError:
        pass

    # Configure transformers
    try:
        import transformers

        # Different versions of transformers have different ways to enable progress bars
        # Try multiple approaches to ensure compatibility

        # Method 1: Try through utils.logging (newer versions)
        try:
            if hasattr(transformers.utils.logging, "enable_progress_bar"):
                transformers.utils.logging.enable_progress_bar()
        except (ImportError, AttributeError):
            pass

        # Method 2: Try direct module function (some versions)
        if hasattr(transformers, "enable_progress_bars"):
            transformers.enable_progress_bars()

        # Method 3: Set environment variable (works for all versions)
        os.environ["TRANSFORMERS_VERBOSITY"] = "warning"
        os.environ["TRANSFORMERS_NO_PROGRESS_BAR"] = "0"

        # Set verbosity level if available
        if hasattr(transformers, "logging") and hasattr(transformers.logging, "set_verbosity_warning"):
            transformers.logging.set_verbosity_warning()
    except ImportError:
        pass

# Alias for backward compatibility
configure_hf_progress_bars = enable_hf_progress_bars

# Function to configure Hugging Face logging
def configure_hf_logging():
    """
    Configure Hugging Face logging.
    This function is called from __init__.py to set up logging early.
    """
    # Configure logging for Hugging Face libraries
    for logger_name in ["transformers", "huggingface_hub", "accelerate", "tqdm", "filelock"]:
        hf_logger = logging.getLogger(logger_name)
        hf_logger.setLevel(logging.WARNING)  # Only show warnings and errors
        hf_logger.propagate = False  # Don't propagate to parent loggers

        # Remove any existing handlers
        for handler in hf_logger.handlers[:]:
            hf_logger.removeHandler(handler)

        # Add a null handler to prevent warnings about no handlers
        hf_logger.addHandler(logging.NullHandler())

    # Set environment variables for better compatibility
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"  # Enable progress bars
    os.environ["TRANSFORMERS_VERBOSITY"] = "warning"  # Set verbosity level
    os.environ["TRANSFORMERS_NO_PROGRESS_BAR"] = "0"  # Enable progress bars

# Export functions for use in other modules
__all__ = ["enable_hf_progress_bars", "configure_hf_progress_bars", "configure_hf_logging", "StdoutRedirector"]
