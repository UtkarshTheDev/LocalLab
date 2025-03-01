"""
Core logger implementation for LocalLab
"""

import logging
import os
import time
from typing import Optional, Dict, Any
from . import get_logger

# Server start time for uptime calculation
SERVER_START_TIME = time.time()

# Global variables for tracking request counts and other metrics
_request_counter = 0
_model_load_times: Dict[str, float] = {}
_active_model: Optional[str] = None
_server_status = "initializing"

# Create main logger
logger = get_logger("locallab")


def log_request(endpoint: str, params: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an API request
    
    Args:
        endpoint: The API endpoint that was called
        params: Optional parameters to log
    """
    global _request_counter
    _request_counter += 1
    
    if params:
        logger.info(f"Request #{_request_counter} to {endpoint} with params: {params}")
    else:
        logger.info(f"Request #{_request_counter} to {endpoint}")


def log_model_loaded(model_id: str, load_time_seconds: float) -> None:
    """
    Log when a model is loaded and store metrics
    
    Args:
        model_id: The ID of the loaded model
        load_time_seconds: Time taken to load the model in seconds
    """
    global _active_model, _model_load_times
    _active_model = model_id
    _model_load_times[model_id] = load_time_seconds
    
    logger.info(f"Model {model_id} loaded in {load_time_seconds:.2f} seconds")


def log_model_unloaded(model_id: str) -> None:
    """
    Log when a model is unloaded
    
    Args:
        model_id: The ID of the unloaded model
    """
    global _active_model
    if _active_model == model_id:
        _active_model = None
    
    logger.info(f"Model {model_id} unloaded")


def set_server_status(status: str) -> None:
    """
    Update the server status
    
    Args:
        status: New server status (e.g., "initializing", "running")
    """
    global _server_status
    _server_status = status.lower()
    logger.info(f"Server status changed to: {status}")


def get_server_status() -> str:
    """
    Get the current server status
    
    Returns:
        Current server status
    """
    return _server_status


def get_uptime_seconds() -> float:
    """
    Get server uptime in seconds
    
    Returns:
        Uptime in seconds
    """
    return time.time() - SERVER_START_TIME


def get_request_count() -> int:
    """
    Get the total number of requests processed
    
    Returns:
        Total request count
    """
    return _request_counter


def get_active_model() -> Optional[str]:
    """
    Get the currently active model ID
    
    Returns:
        Active model ID or None if no model is loaded
    """
    return _active_model


def get_model_load_times() -> Dict[str, float]:
    """
    Get a dictionary of model load times
    
    Returns:
        Dictionary mapping model IDs to their load times in seconds
    """
    return _model_load_times.copy()


def configure_file_logging(log_dir: str = "logs") -> None:
    """
    Configure file-based logging in addition to console logging
    
    Args:
        log_dir: Directory to store log files
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    file_handler = logging.FileHandler(os.path.join(log_dir, "locallab.log"))
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    
    logger.info(f"File logging configured in directory: {log_dir}") 