"""
ASCII art banners and UI elements for LocalLab
"""

from colorama import Fore, Style, init
init(autoreset=True)
from typing import Optional, Dict, Any, List
import os


def print_initializing_banner(version: str):
    """
    Print the initializing banner with clear visual indication
    that the server is starting up and not ready for requests
    """
    startup_banner = f"""
{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}

{Fore.GREEN}LocalLab Server v{version}{Style.RESET_ALL}
{Fore.CYAN}Your lightweight AI inference server for running LLMs locally{Style.RESET_ALL}

{Fore.BLUE}
 ██       ██████   ██████  █████  ██      ██       █████  ██████  
 ██      ██    ██ ██      ██   ██ ██      ██      ██   ██ ██   ██ 
 ██      ██    ██ ██      ███████ ██      ██      ███████ ██████  
 ██      ██    ██ ██      ██   ██ ██      ██      ██   ██ ██   ██ 
 ███████  ██████   ██████ ██   ██ ███████ ███████ ██   ██ ██████  
{Style.RESET_ALL}

{Fore.RED}⚠️  SERVER STARTING - DO NOT MAKE API REQUESTS YET                ⚠️{Style.RESET_ALL}
{Fore.RED}⚠️  PLEASE WAIT FOR THE "RUNNING" BANNER TO APPEAR                ⚠️{Style.RESET_ALL}

{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}

⏳ Status: {Fore.YELLOW}INITIALIZING{Style.RESET_ALL}
🔄 Loading components and checking environment...

"""
    print(startup_banner, flush=True)


def print_running_banner(version: str):
    """
    Print the running banner with clear visual indication
    that the server is now ready to accept API requests
    """
    running_banner = f"""
{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}

{Fore.GREEN}LocalLab Server v{version}{Style.RESET_ALL} - {Fore.YELLOW}READY FOR REQUESTS{Style.RESET_ALL}
{Fore.CYAN}Your AI model is now running and ready to process requests{Style.RESET_ALL}

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

{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
    
    print(running_banner, flush=True)


def print_system_resources():
    """Print system resources in a formatted box"""
    # Import here to avoid circular imports
    try:
        from ..utils.system import get_system_info
        
        resources = get_system_info()
    except ImportError:
        # Fallback if get_system_info is not available
        try:
            from ..utils.system import get_system_resources
            resources = get_system_resources()
        except ImportError:
            # Ultimate fallback if neither function is available
            import psutil
            resources = {
                'cpu_count': psutil.cpu_count(),
                'cpu_usage': psutil.cpu_percent(),
                'ram_gb': psutil.virtual_memory().total / (1024 * 1024 * 1024),
                'gpu_available': False,
                'gpu_info': []
            }
    
    ram_gb = resources.get('ram_gb', 0)
    cpu_count = resources.get('cpu_count', 0)
    gpu_available = resources.get('gpu_available', False)
    gpu_info = resources.get('gpu_info', [])
    
    system_info = f"""
{Fore.CYAN}════════════════════════════════════ System Resources ════════════════════════════════════{Style.RESET_ALL}

💻 CPU: {Fore.GREEN}{cpu_count} cores{Style.RESET_ALL}
🧠 RAM: {Fore.GREEN}{ram_gb:.1f} GB{Style.RESET_ALL}
"""
    
    if gpu_available and gpu_info:
        for i, gpu in enumerate(gpu_info):
            system_info += f"🎮 GPU {i}: {Fore.GREEN}{gpu.get('name', 'Unknown')} ({gpu.get('total_memory', 0)} MB){Style.RESET_ALL}\n"
    else:
        system_info += f"🎮 GPU: {Fore.YELLOW}Not available{Style.RESET_ALL}\n"
        
    system_info += f"\n{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}\n"
    
    print(system_info, flush=True)
    return system_info


def print_model_info():
    """Print model information in a formatted box"""
    # Import here to avoid circular imports
    try:
        from ..config import get_env_var
        from ..model_manager import ModelManager
        
        # Get model information
        model_id = get_env_var("HUGGINGFACE_MODEL", default="microsoft/phi-2")
        
        # Get optimization settings
        enable_quantization = get_env_var("LOCALLAB_ENABLE_QUANTIZATION", default="false").lower() == "true"
        quantization_type = get_env_var("LOCALLAB_QUANTIZATION_TYPE", default="int8")
        enable_attention_slicing = get_env_var("LOCALLAB_ENABLE_ATTENTION_SLICING", default="false").lower() == "true"
        enable_flash_attention = get_env_var("LOCALLAB_ENABLE_FLASH_ATTENTION", default="false").lower() == "true"
        enable_better_transformer = get_env_var("LOCALLAB_ENABLE_BETTERTRANSFORMER", default="false").lower() == "true"
        enable_cpu_offloading = get_env_var("LOCALLAB_ENABLE_CPU_OFFLOADING", default="false").lower() == "true"
        
        # Format model information
        model_info = f"""
{Fore.CYAN}════════════════════════════════════ Model Configuration ════════════════════════════════════{Style.RESET_ALL}

🤖 Model: {Fore.GREEN}{model_id}{Style.RESET_ALL}

⚙️ Optimizations:
  • Quantization: {Fore.GREEN if enable_quantization else Fore.RED}{enable_quantization}{Style.RESET_ALL} {f"({quantization_type})" if enable_quantization else ""}
  • Attention Slicing: {Fore.GREEN if enable_attention_slicing else Fore.RED}{enable_attention_slicing}{Style.RESET_ALL}
  • Flash Attention: {Fore.GREEN if enable_flash_attention else Fore.RED}{enable_flash_attention}{Style.RESET_ALL}
  • BetterTransformer: {Fore.GREEN if enable_better_transformer else Fore.RED}{enable_better_transformer}{Style.RESET_ALL}
  • CPU Offloading: {Fore.GREEN if enable_cpu_offloading else Fore.RED}{enable_cpu_offloading}{Style.RESET_ALL}

{Fore.CYAN}═══════════════════════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
    except ImportError as e:
        # Fallback if imports fail
        model_info = f"""
{Fore.CYAN}════════════════════════════════════ Model Configuration ════════════════════════════════════{Style.RESET_ALL}

🤖 Model: {Fore.YELLOW}Default model will be used{Style.RESET_ALL}

⚙️ Optimizations: {Fore.YELLOW}Using default settings{Style.RESET_ALL}

{Fore.CYAN}═══════════════════════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
    
    print(model_info, flush=True)


def print_system_instructions():
    """Print system instructions in a formatted box"""
    # Import here to avoid circular imports
    from ..config import system_instructions
    
    instructions_text = system_instructions.get_instructions()
    
    system_instructions_text = f"""
{Fore.CYAN}════════════════════════════════════ System Instructions ═══════════════════════════════════{Style.RESET_ALL}

{Fore.YELLOW}{instructions_text}{Style.RESET_ALL}

{Fore.CYAN}═══════════════════════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
    print(system_instructions_text, flush=True)
    return system_instructions_text


def print_api_docs():
    """Print API documentation with examples"""
    # Check if ngrok is enabled and get the public URL
    # Get the port from environment or use default
    port = os.environ.get("LOCALLAB_PORT", "8000")
    
    # Check if ngrok is enabled
    use_ngrok = os.environ.get("LOCALLAB_USE_NGROK", "").lower() in ("true", "1", "yes")
    
    # Get the ngrok URL if available
    ngrok_url = os.environ.get("LOCALLAB_NGROK_URL", "")
    
    # Determine the server URL to display in examples
    if use_ngrok and ngrok_url:
        server_url = ngrok_url
        url_description = "ngrok public URL"
    else:
        server_url = f"http://localhost:{port}"
        url_description = "local URL"
    
    api_docs = f"""
{Fore.CYAN}════════════════════════════════════ API Documentation ════════════════════════════════════{Style.RESET_ALL}

📚 Text Generation Endpoints:

1️⃣ /generate - Generate text from a prompt
  • POST with JSON body: {{
      "prompt": "Write a story about a dragon",
      "max_tokens": 100,
      "temperature": 0.7,
      "top_p": 0.9,
      "system_prompt": "You are a creative storyteller",
      "stream": false
    }}

  • Example:
    curl -X POST "{server_url}/generate" \\
    -H "Content-Type: application/json" \\
    -d '{{"prompt": "Write a story about a dragon", "max_tokens": 100}}'

2️⃣ /chat - Chat completion API
  • POST with JSON body: {{
      "messages": [
        {{"role": "system", "content": "You are a helpful assistant"}},
        {{"role": "user", "content": "Hello, who are you?"}}
      ],
      "max_tokens": 100,
      "temperature": 0.7,
      "top_p": 0.9,
      "stream": false
    }}

  • Example:
    curl -X POST "{server_url}/chat" \\
    -H "Content-Type: application/json" \\
    -d '{{"messages": [{{"role": "user", "content": "Hello, who are you?"}}]}}'

📦 Model Management Endpoints:

1️⃣ /models - List available models
  • GET
  • Example: curl "{server_url}/models"

2️⃣ /models/load - Load a specific model
  • POST with JSON body: {{ "model_id": "microsoft/phi-2" }}
  • Example:
    curl -X POST "{server_url}/models/load" \\
    -H "Content-Type: application/json" \\
    -d '{{"model_id": "microsoft/phi-2"}}'

ℹ️ System Endpoints:

1️⃣ /system/info - Get system information
  • GET
  • Example: curl "{server_url}/system/info"

2️⃣ /system/resources - Get detailed system resources
  • GET
  • Example: curl "{server_url}/system/resources"

3️⃣ /docs - Interactive API documentation (Swagger UI)
  • Open in browser: {server_url}/docs

{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
    print(api_docs, flush=True)
    return api_docs


def format_multiline_text(text: str, prefix: str = "") -> str:
    """Format multiline text for display in a banner"""
    lines = text.strip().split('\n')
    return '\n'.join([f"{prefix}{line}" for line in lines])


def print_footer():
    """Print a footer with author information and social media links."""
    footer = f"""
{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
  Created by: Utkarsh Tiwari                                    
  GitHub: https://github.com/UtkarshTheDev                   
  Twitter: https://twitter.com/UtkarshTheDev                   
  Instagram: https://instagram.com/UtkarshTheDev                 
                                                                    
  ⭐ Star this project: https://github.com/UtkarshTheDev/LocalLab  
                                                                    
  Thank you for using LocalLab! Feedback and contributions welcome!  
{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
    print(footer, flush=True)