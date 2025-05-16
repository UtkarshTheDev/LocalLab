"""
LocalLab - A lightweight AI inference server for running LLMs locally
"""

# Import early configuration first to set up logging and environment variables
# This ensures Hugging Face's progress bars are displayed correctly
from .utils.early_config import enable_hf_progress_bars

__version__ = "0.6.4"  # Updated to improve model downloading experience and fix CLI settings

# Only import what's necessary initially, lazy-load the rest
from .logger import get_logger

# Explicitly expose start_server for direct import
from .server import start_server, cli

# Enable Hugging Face progress bars with native display
enable_hf_progress_bars()

# Other imports will be lazy-loaded when needed
# from .config import MODEL_REGISTRY, DEFAULT_MODEL
# from .model_manager import ModelManager
# from .core.app import app

__all__ = ["start_server", "cli", "__version__"]
