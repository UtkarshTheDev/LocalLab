"""
CLI module for LocalLab
"""

from .interactive import prompt_for_config, is_in_colab
from .config import load_config, save_config, get_config_value

__all__ = [
    'prompt_for_config',
    'is_in_colab',
    'load_config',
    'save_config',
    'get_config_value'
] 