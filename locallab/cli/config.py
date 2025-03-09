"""
Configuration management for LocalLab CLI
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Default config path
CONFIG_DIR = Path.home() / ".locallab"
CONFIG_FILE = CONFIG_DIR / "config.json"

def ensure_config_dir():
    """Ensure the config directory exists"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def load_config() -> Dict[str, Any]:
    """Load configuration from file"""
    ensure_config_dir()
    
    if not CONFIG_FILE.exists():
        return {}
    
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def save_config(config: Dict[str, Any]):
    """Save configuration to file"""
    ensure_config_dir()
    
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")

def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a configuration value, checking environment variables first,
    then the config file, then the default
    """
    # Check environment variables first
    env_key = f"LOCALLAB_{key.upper()}"
    if env_key in os.environ:
        return os.environ[env_key]
    
    # Then check config file
    config = load_config()
    if key in config:
        return config[key]
    
    # Finally return default
    return default

def set_config_value(key: str, value: Any):
    """Set a configuration value in both environment and config file"""
    # Set environment variable
    env_key = f"LOCALLAB_{key.upper()}"
    os.environ[env_key] = str(value)
    
    # Update config file
    config = load_config()
    config[key] = value
    save_config(config)

def get_all_config() -> Dict[str, Any]:
    """Get all configuration values, merging environment variables and config file"""
    config = load_config()
    
    # Add environment variables
    for key, value in os.environ.items():
        if key.startswith("LOCALLAB_"):
            config_key = key[9:].lower()  # Remove LOCALLAB_ prefix and lowercase
            config[config_key] = value
    
    return config 