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


def print_running_banner(port: int, public_url: Optional[str] = None):
    """
    Print the running banner with clear visual indication
    that the server is now ready to accept API requests
    """
    running_banner = f"""
{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}

{Fore.GREEN}LocalLab Server{Style.RESET_ALL} - {Fore.YELLOW}READY FOR REQUESTS{Style.RESET_ALL}
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

🖥️ Local URL: {Fore.GREEN}http://localhost:{port}{Style.RESET_ALL}
"""
    if public_url:
        running_banner += f"🌐 Public URL: {Fore.GREEN}{public_url}{Style.RESET_ALL}\n"
    
    print(running_banner, flush=True)


def print_system_resources(resources: dict):
    """Print system resources in a formatted box"""
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


def print_model_info(model_info: Dict[str, Any], optimization_settings: Dict[str, Any] = None):
    """
    Print model information and optimization settings
    
    Args:
        model_info: Dictionary containing model information
        optimization_settings: Dictionary containing optimization settings
    """
    # Get model information
    model_id = model_info.get('model_id', 'Unknown')
    model_name = model_info.get('model_name', model_id)
    parameters = model_info.get('parameters', 'Unknown')
    device = model_info.get('device', 'cpu')
    architecture = model_info.get('architecture', 'Unknown')
    max_length = model_info.get('max_length', 'Unknown')
    memory_used = model_info.get('memory_used', 'Unknown')
    
    # Get optimization settings
    if not optimization_settings and 'optimizations' in model_info:
        optimization_settings = model_info.get('optimizations', {})
    
    quantization = model_info.get('quantization', 'None')
    attention_slicing = optimization_settings.get('attention_slicing', False) if optimization_settings else False
    flash_attention = optimization_settings.get('flash_attention', False) if optimization_settings else False
    better_transformer = optimization_settings.get('better_transformer', False) if optimization_settings else False
    
    model_info_banner = f"""
{Fore.CYAN}════════════════════════════════════ Model Configuration ════════════════════════════════════{Style.RESET_ALL}

🤖 Model: {Fore.GREEN}{model_name} ({model_id}){Style.RESET_ALL}
📊 Parameters: {Fore.GREEN}{parameters}{Style.RESET_ALL}
🧠 Architecture: {Fore.GREEN}{architecture}{Style.RESET_ALL}
💽 Device: {Fore.GREEN}{device}{Style.RESET_ALL}
📏 Max Length: {Fore.GREEN}{max_length}{Style.RESET_ALL}
💾 Memory Used: {Fore.GREEN}{memory_used}{Style.RESET_ALL}

⚙️ Optimizations:
  • Quantization: {Fore.GREEN if quantization != "None" else Fore.YELLOW}{quantization}{Style.RESET_ALL}
  • Attention Slicing: {Fore.GREEN if attention_slicing else Fore.YELLOW}{str(attention_slicing)}{Style.RESET_ALL}
  • Flash Attention: {Fore.GREEN if flash_attention else Fore.YELLOW}{str(flash_attention)}{Style.RESET_ALL}
  • Better Transformer: {Fore.GREEN if better_transformer else Fore.YELLOW}{str(better_transformer)}{Style.RESET_ALL}

{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
    print(model_info_banner, flush=True)
    return model_info_banner


def print_system_instructions(instructions: str):
    """
    Print the current system instructions
    
    Args:
        instructions: The system instructions text
    """
    # Truncate instructions if they're too long
    max_length = 400
    displayed_instructions = instructions
    if len(instructions) > max_length:
        displayed_instructions = instructions[:max_length] + "..."
    
    instructions_banner = f"""
{Fore.CYAN}════════════════════════════════════ System Instructions ════════════════════════════════════{Style.RESET_ALL}

{format_multiline_text(displayed_instructions, prefix="")}

{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
    print(instructions_banner, flush=True)
    return instructions_banner


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