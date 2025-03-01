"""
ASCII art banners and UI elements for LocalLab
"""

from colorama import Fore, Style, init
init(autoreset=True)
from typing import Optional


def print_initializing_banner(version: str):
    """
    Print the initializing banner with clear visual indication
    that the server is starting up and not ready for requests
    """
    startup_banner = f"""
{Fore.CYAN}
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  {Fore.GREEN}LocalLab Server v{version}{Fore.CYAN}                                      ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.YELLOW}
   _____ _______    _      _____ _______ _____ _   _  _____
  / ____|__   __|  / \    |  __ \|__   __|_   _| \ | |/ ____|
 | (___    | |    /   \   | |__) |  | |    | | |  \| | |  __ 
  \___ \   | |   / ___ \  |  _  /   | |    | | | . ` | | |_ |
  ____) |  | |  / /   \ \ | | \ \   | |   _| |_| |\  | |__| |
 |_____/   |_| /_/     \_\|_|  \_\  |_|  |_____|_| \_|\_____|
{Style.RESET_ALL}

{Fore.RED}⚠️  SERVER STARTING - DO NOT MAKE API REQUESTS YET                ⚠️{Style.RESET_ALL}
{Fore.RED}⚠️  PLEASE WAIT FOR THE "RUNNING" BANNER TO APPEAR                ⚠️{Style.RESET_ALL}

{Fore.CYAN}┌────────────────────────── Server Status ───────────────────────────┐{Style.RESET_ALL}
│
│  ⏳ Status: {Fore.YELLOW}INITIALIZING{Style.RESET_ALL}
│  🔄 Loading components and checking environment...
│
{Fore.CYAN}└─────────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}
"""
    print(startup_banner, flush=True)


def print_running_banner(port: int, public_url: Optional[str] = None):
    """
    Print the running banner with clear visual indication
    that the server is now ready to accept API requests
    """
    running_banner = f"""
{Fore.GREEN}
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  {Fore.CYAN}LocalLab Server{Fore.GREEN} - {Fore.YELLOW}READY FOR REQUESTS{Fore.GREEN}                          ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.GREEN}
  _____  _    _ _   _ _   _ _____ _   _  _____ 
 |  __ \| |  | | \ | | \ | |_   _| \ | |/ ____|
 | |__) | |  | |  \| |  \| | | | |  \| | |  __ 
 |  _  /| |  | | . ` | . ` | | | | . ` | | |_ |
 | | \ \| |__| | |\  | |\  |_| |_| |\  | |__| |
 |_|  \_\\____/|_| \_|_| \_|_____|_| \_|\_____|
{Style.RESET_ALL}

{Fore.GREEN}✅ SERVER READY! YOU CAN NOW MAKE API REQUESTS                      ✅{Style.RESET_ALL}
{Fore.GREEN}✅ MODEL LOADING WILL CONTINUE IN BACKGROUND IF NOT FINISHED        ✅{Style.RESET_ALL}

"""
    print(running_banner, flush=True)
    
    # Show connection details again for convenience
    endpoint_info = f"""
{Fore.CYAN}┌────────────────────────── Connection Details ────────────────────────┐{Style.RESET_ALL}
│
│  🖥️ Local URL: {Fore.GREEN}http://localhost:{port}{Style.RESET_ALL}
"""
    if public_url:
        endpoint_info += f"│  🌐 Public URL: {Fore.GREEN}{public_url}{Style.RESET_ALL}\n"
    endpoint_info += f"│\n{Fore.CYAN}└─────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n"
    print(endpoint_info, flush=True)


def print_system_resources(resources: dict):
    """Print system resources in a formatted box"""
    ram_gb = resources.get('ram_gb', 0)
    cpu_count = resources.get('cpu_count', 0)
    gpu_available = resources.get('gpu_available', False)
    gpu_info = resources.get('gpu_info', [])
    
    system_info = f"""
{Fore.CYAN}┌────────────────────────── System Resources ────────────────────────┐{Style.RESET_ALL}
│
│  💻 CPU: {Fore.GREEN}{cpu_count} cores{Style.RESET_ALL}
│  🧠 RAM: {Fore.GREEN}{ram_gb:.1f} GB{Style.RESET_ALL}
"""
    
    if gpu_available and gpu_info:
        for i, gpu in enumerate(gpu_info):
            system_info += f"│  🎮 GPU {i}: {Fore.GREEN}{gpu.get('name', 'Unknown')} ({gpu.get('total_memory', 0)} MB){Style.RESET_ALL}\n"
    else:
        system_info += f"│  🎮 GPU: {Fore.YELLOW}Not available{Style.RESET_ALL}\n"
        
    system_info += f"│\n{Fore.CYAN}└─────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n"
    
    print(system_info, flush=True)
    return system_info 