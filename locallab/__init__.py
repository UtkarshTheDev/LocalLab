"""
LocalLab - A lightweight AI inference server for running models locally or in Google Colab
"""

__version__ = "0.1.9.5"
__author__ = "Utkarsh"
__email__ = "utkarshweb2023@gmail.com"

from .main import start_server
from .config import MODEL_REGISTRY, get_env_var, can_run_model, estimate_model_requirements

__all__ = [
    "start_server",
    "MODEL_REGISTRY",
    "get_env_var",
    "can_run_model",
    "estimate_model_requirements",
]
