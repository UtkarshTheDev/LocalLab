"""
Networking utilities for LocalLab
"""

import socket
import logging
from typing import Optional
from colorama import Fore, Style

from ..logger import get_logger

# Get the logger instance
logger = get_logger("locallab.networking")

# Try to import ngrok, but don't fail if not available
try:
    from pyngrok import ngrok, conf
    NGROK_AVAILABLE = True
except ImportError:
    NGROK_AVAILABLE = False


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use on localhost"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def setup_ngrok(port: int = 8000, auth_token: Optional[str] = None) -> Optional[str]:
    """
    Set up an ngrok tunnel to the given port
    
    Args:
        port: The local port to tunnel to
        auth_token: Optional ngrok auth token
        
    Returns:
        The public ngrok URL or None if setup failed
    """
    if not NGROK_AVAILABLE:
        logger.error("ngrok is not installed. Please install it with: pip install pyngrok")
        return None
        
    # Configure ngrok
    if auth_token:
        conf.get_default().auth_token = auth_token
    
    # Check if there are existing tunnels and close them
    try:
        tunnels = ngrok.get_tunnels()
        for tunnel in tunnels:
            public_url = tunnel.public_url
            ngrok.disconnect(public_url)
            logger.info(f"Closed existing ngrok tunnel: {public_url}")
    except Exception as e:
        logger.warning(f"Failed to close existing tunnels: {str(e)}")
    
    # Create new tunnel - we've removed validation and health checks as requested
    try:
        # We're starting the tunnel without health checks or validation
        # which was causing errors for some users
        public_url = ngrok.connect(port, bind_tls=True)
        logger.info(f"ngrok tunnel established: {public_url}")
        return public_url
    except Exception as e:
        logger.error(f"Failed to establish ngrok tunnel: {str(e)}")
        return None 