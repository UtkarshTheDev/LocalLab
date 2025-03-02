"""
Networking utilities for LocalLab
"""

import socket
import logging
import os
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
        logger.error(f"{Fore.RED}ngrok is not installed. Please install it with: pip install pyngrok{Style.RESET_ALL}")
        return None
    
    # Check for auth token in environment variable if not provided directly
    if not auth_token:
        auth_token = os.environ.get("NGROK_AUTH_TOKEN")
    
    # If still no auth token, provide clear instructions
    if not auth_token:
        logger.error(f"\n{Fore.RED}⛔ Ngrok authentication token is required for public tunneling.{Style.RESET_ALL}")
        logger.error(f"\n{Fore.YELLOW}📝 Please get your auth token from: {Fore.CYAN}https://dashboard.ngrok.com/get-started/your-authtoken{Style.RESET_ALL}")
        logger.error(f"\n{Fore.YELLOW}Then set your ngrok auth token using one of these methods:{Style.RESET_ALL}")
        logger.error(f"\n{Fore.GREEN}Method 1: Set NGROK_AUTH_TOKEN environment variable before importing locallab:{Style.RESET_ALL}")
        logger.error(f"   import os")
        logger.error(f"   os.environ['NGROK_AUTH_TOKEN'] = 'your_token_here'")
        logger.error(f"   import locallab")
        logger.error(f"\n{Fore.GREEN}Method 2: Pass the auth_token parameter directly to start_server:{Style.RESET_ALL}")
        logger.error(f"   from locallab.server import start_server")
        logger.error(f"   start_server(use_ngrok=True, ngrok_auth_token='your_token_here')")
        logger.error(f"\n{Fore.YELLOW}⚠️ If you're using Google Colab, you need to add this before starting the server.{Style.RESET_ALL}")
        return None
        
    # Configure ngrok with the auth token
    try:
        conf.get_default().auth_token = auth_token
    except Exception as e:
        logger.error(f"{Fore.RED}Failed to configure ngrok with auth token: {str(e)}{Style.RESET_ALL}")
        logger.error(f"{Fore.YELLOW}Please check that your auth token is valid.{Style.RESET_ALL}")
        return None
    
    # Check if there are existing tunnels and close them
    try:
        tunnels = ngrok.get_tunnels()
        for tunnel in tunnels:
            public_url = tunnel.public_url
            ngrok.disconnect(public_url)
            logger.info(f"Closed existing ngrok tunnel: {public_url}")
    except Exception as e:
        logger.warning(f"Failed to close existing tunnels: {str(e)}")
    
    # Create new tunnel with improved error handling
    try:
        # Start the tunnel without health checks or validation
        # which was causing errors for some users
        public_url = ngrok.connect(port, bind_tls=True)
        logger.info(f"{Fore.GREEN}Ngrok tunnel established: {public_url}{Style.RESET_ALL}")
        return public_url
    except Exception as e:
        error_msg = str(e)
        logger.error(f"{Fore.RED}Failed to establish ngrok tunnel: {error_msg}{Style.RESET_ALL}")
        
        # Provide specific guidance based on common error types
        if "AuthTokenNotSet" in error_msg or "auth" in error_msg.lower():
            logger.error(f"{Fore.YELLOW}❌ Authentication error: Your ngrok token appears to be invalid or not set correctly.{Style.RESET_ALL}")
            logger.error(f"{Fore.YELLOW}Please verify your token at: https://dashboard.ngrok.com/get-started/your-authtoken{Style.RESET_ALL}")
        elif "bind" in error_msg.lower() or "address already in use" in error_msg.lower():
            logger.error(f"{Fore.YELLOW}❌ Port binding error: The ngrok client couldn't bind to a port.{Style.RESET_ALL}")
            logger.error(f"{Fore.YELLOW}Try restarting your runtime or notebook if in Colab.{Style.RESET_ALL}")
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            logger.error(f"{Fore.YELLOW}❌ Connection error: Couldn't connect to ngrok service.{Style.RESET_ALL}")
            logger.error(f"{Fore.YELLOW}Check your internet connection and firewall settings.{Style.RESET_ALL}")
        
        logger.error(f"{Fore.YELLOW}The server will continue to run locally on port {port}.{Style.RESET_ALL}")
        return None 

def get_network_interfaces() -> dict:
    """
    Get information about available network interfaces
    
    Returns:
        A dictionary with interface names as keys and their addresses as values
    """
    interfaces = {}
    try:
        import socket
        import netifaces
        
        for interface in netifaces.interfaces():
            addresses = netifaces.ifaddresses(interface)
            # Get IPv4 addresses if available
            if netifaces.AF_INET in addresses:
                ipv4_info = addresses[netifaces.AF_INET][0]
                interfaces[interface] = {
                    "ip": ipv4_info.get("addr", ""),
                    "netmask": ipv4_info.get("netmask", ""),
                    "broadcast": ipv4_info.get("broadcast", "")
                }
            # Get IPv6 addresses if available
            if netifaces.AF_INET6 in addresses:
                ipv6_info = addresses[netifaces.AF_INET6][0]
                if interface not in interfaces:
                    interfaces[interface] = {}
                interfaces[interface]["ipv6"] = ipv6_info.get("addr", "")
    except ImportError:
        logger.warning(f"{Fore.YELLOW}netifaces package not found. Limited network interface information available.{Style.RESET_ALL}")
        # Fallback to simple hostname information
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            interfaces["default"] = {"ip": ip, "hostname": hostname}
        except Exception as e:
            logger.warning(f"Failed to get network interface information: {str(e)}")
            interfaces["error"] = str(e)
    except Exception as e:
        logger.warning(f"Failed to get network interface information: {str(e)}")
        interfaces["error"] = str(e)
    
    return interfaces

async def get_public_ip() -> str:
    """
    Get the public IP address of this machine
    
    Returns:
        The public IP address as a string, or an empty string if it cannot be determined
    """
    services = [
        "https://api.ipify.org",
        "https://api.my-ip.io/ip",
        "https://checkip.amazonaws.com",
        "https://ipinfo.io/ip"
    ]
    
    try:
        # Try to use httpx for async requests
        import httpx
        for service in services:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(service, timeout=5.0)
                    if response.status_code == 200:
                        return response.text.strip()
            except Exception:
                continue
    except ImportError:
        # Fallback to requests (synchronous)
        try:
            import requests
            for service in services:
                try:
                    response = requests.get(service, timeout=5.0)
                    if response.status_code == 200:
                        return response.text.strip()
                except Exception:
                    continue
        except ImportError:
            logger.warning(f"{Fore.YELLOW}Neither httpx nor requests packages found. Cannot determine public IP.{Style.RESET_ALL}")
    
    # If we couldn't get the IP from any service, return empty string
    return "" 