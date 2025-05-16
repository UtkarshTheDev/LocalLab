"""
Early configuration module for LocalLab.
This module is imported before any other modules to configure logging and environment variables.
"""

import os
import sys
import logging
import warnings

# Configure environment variables for Hugging Face
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"  # Enable HF Transfer for better downloads
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
    
    # Configure huggingface_hub
    try:
        import huggingface_hub
        huggingface_hub.enable_progress_bars()
    except ImportError:
        pass
    
    # Configure transformers
    try:
        import transformers
        transformers.utils.logging.enable_progress_bar()
        transformers.logging.set_verbosity_warning()
    except ImportError:
        pass
