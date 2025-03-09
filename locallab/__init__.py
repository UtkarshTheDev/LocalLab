"""
LocalLab - A lightweight AI inference server for running LLMs locally
"""

__version__ = "0.4.7"

from typing import Dict, Any, Optional

# Export commonly used components
from .config import MODEL_REGISTRY, can_run_model
from .server import start_server, cli

__all__ = ["start_server", "MODEL_REGISTRY", "can_run_model", "cli"]
