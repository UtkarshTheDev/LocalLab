"""
LocalLab - A lightweight AI inference server for running LLMs locally
"""

__version__ = "0.4.11"

# Only import what's needed for basic functionality
# Other imports will be lazy-loaded when needed
from .server import start_server, cli

# Don't import these by default to speed up CLI startup
# They will be imported when needed
# from .config import MODEL_REGISTRY, DEFAULT_MODEL
# from .model_manager import ModelManager
# from .core.app import app

__all__ = ["start_server", "cli", "__version__"]
