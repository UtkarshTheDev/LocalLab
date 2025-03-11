"""
LocalLab - A lightweight AI inference server for running LLMs locally
"""

__version__ = "0.4.22"

# Only import what's necessary initially, lazy-load the rest
from .logger import get_logger

# Explicitly expose start_server for direct import
from .server import start_server, cli

# Other imports will be lazy-loaded when needed

# Don't import these by default to speed up CLI startup
# They will be imported when needed
# from .config import MODEL_REGISTRY, DEFAULT_MODEL
# from .model_manager import ModelManager
# from .core.app import app

__all__ = ["start_server", "cli", "__version__"]
