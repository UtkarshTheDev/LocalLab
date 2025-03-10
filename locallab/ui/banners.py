"""
ASCII art banners and UI elements for LocalLab
"""

from colorama import Fore, Style, init
init(autoreset=True)
from typing import Optional, Dict, Any, List


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
    from ..utils.system import get_system_info
    
    resources = get_system_info()
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
    from ..config import (
        DEFAULT_MODEL,
        ENABLE_QUANTIZATION,
        QUANTIZATION_TYPE,
        ENABLE_ATTENTION_SLICING,
        ENABLE_FLASH_ATTENTION,
        ENABLE_BETTERTRANSFORMER
    )
    from ..cli.config import get_config_value
    import os
    
    try:
        import torch
        torch_available = True
    except ImportError:
        torch_available = False
    
    # Get model settings from config system
    model_id = os.environ.get("HUGGINGFACE_MODEL", DEFAULT_MODEL)
    
    # Get optimization settings from config system
    enable_quantization = get_config_value('enable_quantization', ENABLE_QUANTIZATION)
    if isinstance(enable_quantization, str):
        enable_quantization = enable_quantization.lower() not in ('false', '0', 'none', '')
    
    quantization_type = get_config_value('quantization_type', QUANTIZATION_TYPE)
    
    enable_attention_slicing = get_config_value('enable_attention_slicing', ENABLE_ATTENTION_SLICING)
    if isinstance(enable_attention_slicing, str):
        enable_attention_slicing = enable_attention_slicing.lower() not in ('false', '0', 'none', '')
    
    enable_flash_attention = get_config_value('enable_flash_attention', ENABLE_FLASH_ATTENTION)
    if isinstance(enable_flash_attention, str):
        enable_flash_attention = enable_flash_attention.lower() not in ('false', '0', 'none', '')
    
    enable_better_transformer = get_config_value('enable_better_transformer', ENABLE_BETTERTRANSFORMER)
    if isinstance(enable_better_transformer, str):
        enable_better_transformer = enable_better_transformer.lower() not in ('false', '0', 'none', '')
    
    # Print model settings
    device = "cpu"
    if torch_available and torch.cuda.is_available():
        device = f"cuda:{torch.cuda.current_device()}"
    
    model_info = {
        "model_id": model_id,
        "model_name": model_id.split("/")[-1],
        "parameters": "Unknown (not loaded yet)",
        "device": device,
        "quantization": quantization_type if enable_quantization else "None",
        "optimizations": {
            "attention_slicing": enable_attention_slicing,
            "flash_attention": enable_flash_attention,
            "better_transformer": enable_better_transformer
        }
    }
    
    # Print model info
    model_info_text = f"""
{Fore.CYAN}════════════════════════════════════ Model Configuration ═══════════════════════════════════{Style.RESET_ALL}

🤖 Model: {Fore.GREEN}{model_info['model_id']}{Style.RESET_ALL}
📊 Parameters: {Fore.GREEN}{model_info['parameters']}{Style.RESET_ALL}
💾 Device: {Fore.GREEN}{model_info['device']}{Style.RESET_ALL}
⚙️ Quantization: {Fore.GREEN}{model_info['quantization']}{Style.RESET_ALL}

🔧 Optimizations:
   ├─ Attention Slicing: {Fore.GREEN if model_info['optimizations']['attention_slicing'] else Fore.RED}{model_info['optimizations']['attention_slicing']}{Style.RESET_ALL}
   ├─ Flash Attention: {Fore.GREEN if model_info['optimizations']['flash_attention'] else Fore.RED}{model_info['optimizations']['flash_attention']}{Style.RESET_ALL}
   └─ BetterTransformer: {Fore.GREEN if model_info['optimizations']['better_transformer'] else Fore.RED}{model_info['optimizations']['better_transformer']}{Style.RESET_ALL}

{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
    print(model_info_text, flush=True)
    return model_info_text


def print_system_instructions():
    """Print system instructions in a formatted box"""
    # Import here to avoid circular imports
    from ..config import system_instructions
    
    instructions_text = system_instructions.get_instructions()
    
    system_instructions_text = f"""
{Fore.CYAN}════════════════════════════════════ System Instructions ═══════════════════════════════════{Style.RESET_ALL}

{Fore.YELLOW}{instructions_text}{Style.RESET_ALL}

{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
    print(system_instructions_text, flush=True)
    return system_instructions_text


def print_api_docs():
    """Print API documentation with examples"""
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
    curl -X POST "<server-ngrok-public-url>/generate" \\
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
    curl -X POST "<server-ngrok-public-url>/chat" \\
    -H "Content-Type: application/json" \\
    -d '{{"messages": [{{"role": "user", "content": "Hello, who are you?"}}]}}'

📦 Model Management Endpoints:

1️⃣ /models - List available models
  • GET
  • Example: curl "<server-ngrok-public-url>/models"

2️⃣ /models/load - Load a specific model
  • POST with JSON body: {{ "model_id": "microsoft/phi-2" }}
  • Example:
    curl -X POST "<server-ngrok-public-url>/models/load" \\
    -H "Content-Type: application/json" \\
    -d '{{"model_id": "microsoft/phi-2"}}'

ℹ️ System Endpoints:

1️⃣ /system/info - Get system information
  • GET
  • Example: curl "<server-ngrok-public-url>/system/info"

2️⃣ /system/resources - Get detailed system resources
  • GET
  • Example: curl "<server-ngrok-public-url>/system/resources"

3️⃣ /docs - Interactive API documentation (Swagger UI)
  • Open in browser: <server-ngrok-public-url>/docs

{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
    print(api_docs, flush=True)
    return api_docs


def format_multiline_text(text: str, prefix: str = "") -> str:
    """Format multiline text for display in a banner"""
    lines = text.strip().split('\n')
    return '\n'.join([f"{prefix}{line}" for line in lines]) 