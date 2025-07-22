"""
LocalLab - A lightweight AI inference server for running LLMs locally
"""

# Import early configuration first to set up logging and environment variables
# This ensures Hugging Face's progress bars are displayed correctly
from .utils.early_config import configure_hf_logging

__version__ = "0.11.2"  # Enhanced CLI chat interface with modern design and improved reliability

# Only import what's necessary initially, lazy-load the rest
from .logger import get_logger

# Explicitly expose start_server for direct import
from .server import start_server, cli

# Configure Hugging Face logging early
configure_hf_logging()

# Other imports will be lazy-loaded when needed
# from .config import MODEL_REGISTRY, DEFAULT_MODEL
# from .model_manager import ModelManager
# from .core.app import app

__all__ = ["start_server", "cli", "__version__"]
