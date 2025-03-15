"""
Networking utilities for LocalLab
"""

import os
import socket
import logging
import requests
from typing import Optional, Dict, List, Tuple
from ..config import NGROK_TOKEN_ENV, get_ngrok_token, set_env_var

logger = logging.getLogger(__name__)

def is_port_in_use(port: int) -> bool:
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def setup_ngrok(port: int) -> Optional[str]:
    """Setup ngrok tunnel for the given port"""
    try:
        from pyngrok import ngrok, conf
        
        # Get ngrok token using the standardized function
        auth_token = get_ngrok_token()
        
        if not auth_token:
            logger.error("Ngrok auth token not found. Please configure it using 'locallab config'")
            return None
            
        # Ensure token is properly set in environment
        set_env_var(NGROK_TOKEN_ENV, auth_token)
        
        # Configure ngrok
        ngrok.set_auth_token(auth_token)
        conf.get_default().auth_token = auth_token
        
        # Start tunnel with improved configuration
        tunnel = ngrok.connect(
            port,
            "http",
            options={
                "bind_tls": True,  # Enable HTTPS
                "inspect": False,  # Disable inspection for better performance
            }
        )
        
        public_url = tunnel.public_url
        
        # Store the URL in environment for clients
        os.environ["LOCALLAB_NGROK_URL"] = public_url
        
        logger.info(f"Ngrok tunnel established at: {public_url}")
        return public_url
        
    except Exception as e:
        logger.error(f"Failed to setup ngrok: {str(e)}")
        logger.info("Please check your ngrok token using 'locallab config'")
        return None

def get_network_interfaces() -> List[Dict[str, str]]:
    """Get list of network interfaces"""
    interfaces = []
    try:
        import netifaces
        for iface in netifaces.interfaces():
            try:
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        interfaces.append({
                            "name": iface,
                            "ip": addr['addr']
                        })
            except Exception:
                continue
    except ImportError:
        # Fallback to socket if netifaces not available
        hostname = socket.gethostname()
        try:
            ip = socket.gethostbyname(hostname)
            interfaces.append({
                "name": hostname,
                "ip": ip
            })
        except Exception:
            pass
            
    return interfaces

def get_public_ip() -> Optional[str]:
    """Get public IP address"""
    try:
        response = requests.get('https://api.ipify.org')
        return response.text
    except Exception:
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