"""
ASCII art banners and UI elements for LocalLab
"""

from colorama import Fore, Style, init
init(autoreset=True)
from typing import Optional, Dict, Any, List
import os


def print_initializing_banner(version: str = "0.4.25"):
    """
    Print the initializing banner with clear visual indication
    that the server is starting up and not ready for requests
    """
    # Calculate banner width
    banner_width = 80

    # Create horizontal lines with modern styling
    h_line = f"{Fore.CYAN}{'═' * banner_width}{Style.RESET_ALL}"

    # Create the LocalLab ASCII art with improved spacing and color
    locallab_ascii = f"""{Fore.BLUE}
  ██╗      ██████╗  ██████╗ █████╗ ██╗     ██╗      █████╗ ██████╗
  ██║     ██╔═══██╗██╔════╝██╔══██╗██║     ██║     ██╔══██╗██╔══██╗
  ██║     ██║   ██║██║     ███████║██║     ██║     ███████║██████╔╝
  ██║     ██║   ██║██║     ██╔══██║██║     ██║     ██╔══██║██╔══██╗
  ███████╗╚██████╔╝╚██████╗██║  ██║███████╗███████╗██║  ██║██████╔╝
  ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝╚═════╝ {Style.RESET_ALL}"""

    # Create status box with modern styling (only top and bottom borders)
    status_box_top = f"{Fore.YELLOW}{'━' * banner_width}{Style.RESET_ALL}"
    status_title = f"{Fore.YELLOW}{' ' * ((banner_width - 20) // 2)}⚠️  INITIALIZING  ⚠️{Style.RESET_ALL}"
    status_empty = f""
    status_bullet1 = f"{Fore.YELLOW}  • {Fore.WHITE}Server is starting up - please wait{Style.RESET_ALL}"
    status_bullet2 = f"{Fore.YELLOW}  • {Fore.WHITE}Do not make API requests yet{Style.RESET_ALL}"
    status_bullet3 = f"{Fore.YELLOW}  • {Fore.WHITE}Wait for the \"RUNNING\" banner to appear{Style.RESET_ALL}"
    status_box_bottom = f"{Fore.YELLOW}{'━' * banner_width}{Style.RESET_ALL}"

    # Create status indicator with modern styling
    status_indicator = f"⏳ Status: {Fore.YELLOW}INITIALIZING{Style.RESET_ALL}"
    loading_indicator = f"🔄 Loading components and checking environment..."

    # Assemble the complete banner
    startup_banner = f"""
{h_line}

{Fore.GREEN}LocalLab Server v{version}{Style.RESET_ALL}
{Fore.CYAN}Your lightweight AI inference server for running LLMs locally{Style.RESET_ALL}

{locallab_ascii}

{status_box_top}
{status_title}
{status_empty}
{status_bullet1}
{status_bullet2}
{status_bullet3}
{status_empty}
{status_box_bottom}

{h_line}

{status_indicator}
{loading_indicator}

"""
    print(startup_banner, flush=True)


def print_running_banner(version: str):
    """
    Print the running banner with clear visual indication
    that the server is now ready to accept API requests
    """
    try:
        # Calculate banner width
        banner_width = 80

        # Create horizontal lines with modern styling
        h_line = f"{Fore.CYAN}{'═' * banner_width}{Style.RESET_ALL}"

        # Create the LocalLab ASCII art with improved spacing and color
        locallab_ascii = f"""{Fore.GREEN}
  ██╗      ██████╗  ██████╗ █████╗ ██╗     ██╗      █████╗ ██████╗
  ██║     ██╔═══██╗██╔════╝██╔══██╗██║     ██║     ██╔══██╗██╔══██╗
  ██║     ██║   ██║██║     ███████║██║     ██║     ███████║██████╔╝
  ██║     ██║   ██║██║     ██╔══██║██║     ██║     ██╔══██║██╔══██╗
  ███████╗╚██████╔╝╚██████╗██║  ██║███████╗███████╗██║  ██║██████╔╝
  ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝╚═════╝ {Style.RESET_ALL}"""

        # Create status box with modern styling (only top and bottom borders)
        status_box_top = f"{Fore.GREEN}{'━' * banner_width}{Style.RESET_ALL}"
        status_title = f"{Fore.GREEN}{' ' * ((banner_width - 16) // 2)}✅  RUNNING  ✅{Style.RESET_ALL}"
        status_empty = f""
        status_bullet1 = f"{Fore.GREEN}  • {Fore.WHITE}Server is ready - you can now make API requests{Style.RESET_ALL}"
        status_bullet2 = f"{Fore.GREEN}  • {Fore.WHITE}Prefer to use the client packages for easier interaction{Style.RESET_ALL}"
        status_bullet3 = f"{Fore.GREEN}  • {Fore.WHITE}Model loading will continue in the background{Style.RESET_ALL}"
        status_bullet4 = f"{Fore.GREEN}  • {Fore.WHITE}API documentation is available below{Style.RESET_ALL}"
        status_box_bottom = f"{Fore.GREEN}{'━' * banner_width}{Style.RESET_ALL}"

        # Create status indicator with modern styling
        status_indicator = f"🚀 Status: {Fore.GREEN}RUNNING{Style.RESET_ALL}"
        ready_indicator = f"✨ Your AI model is now running and ready to process requests"

        # Assemble the complete banner
        running_banner = f"""
{h_line}

{Fore.GREEN}LocalLab Server v{version}{Style.RESET_ALL} - {Fore.YELLOW}READY FOR REQUESTS{Style.RESET_ALL}
{Fore.CYAN}Your AI model is now running and ready to process requests{Style.RESET_ALL}

{locallab_ascii}

{status_box_top}
{status_title}
{status_empty}
{status_bullet1}
{status_bullet2}
{status_bullet3}
{status_bullet4}
{status_empty}
{status_box_bottom}

{h_line}

{status_indicator}
{ready_indicator}

"""
        # Make sure we flush the output to ensure it appears
        print(running_banner, flush=True)

        # Return the banner in case it needs to be logged
        return running_banner
    except Exception as e:
        # In case of any exception, log it and display a simpler message
        print(f"\n⚠️ Error displaying running banner: {str(e)}\n")
        print(f"\n{Fore.GREEN}✅ SERVER READY! YOU CAN NOW MAKE API REQUESTS{Style.RESET_ALL}\n", flush=True)
        return None


def print_system_resources():
    """Print system resources in a formatted box"""
    try:
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

        system_info += f"\n{Fore.CYAN}═══════════════════════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}\n"

        print(system_info, flush=True)
        return system_info
    except Exception as e:
        # In case of any exception, log it and display a simpler message
        print(f"\n⚠️ Error displaying system resources: {str(e)}\n", flush=True)
        return None


def print_model_info():
    """Print model information in a formatted box"""
    try:
        # Import here to avoid circular imports
        try:
            from ..config import get_env_var
            from ..model_manager import ModelManager

            # Get model information from model manager first
            model_manager = ModelManager()
            model_id = model_manager.current_model if model_manager.current_model else None

            # If no model loaded, check environment/config
            if not model_id:
                model_id = get_env_var("HUGGINGFACE_MODEL") or get_env_var("LOCALLAB_MODEL_ID") or "microsoft/phi-2"

            # Get optimization settings
            enable_quantization = get_env_var("LOCALLAB_ENABLE_QUANTIZATION", default="true").lower() == "true"
            quantization_type = get_env_var("LOCALLAB_QUANTIZATION_TYPE", default="int8")
            enable_attention_slicing = get_env_var("LOCALLAB_ENABLE_ATTENTION_SLICING", default="true").lower() == "true"
            enable_flash_attention = get_env_var("LOCALLAB_ENABLE_FLASH_ATTENTION", default="true").lower() == "true"
            enable_better_transformer = get_env_var("LOCALLAB_ENABLE_BETTERTRANSFORMER", default="true").lower() == "true"
            enable_cpu_offloading = get_env_var("LOCALLAB_ENABLE_CPU_OFFLOADING", default="true").lower() == "true"

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
        return model_info
    except Exception as e:
        # In case of any exception, log it and display a simpler message
        print(f"\n⚠️ Error displaying model information: {str(e)}\n", flush=True)
        return None


def print_system_instructions():
    """Print system instructions in a formatted box"""
    try:
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
    except Exception as e:
        # In case of any exception, log it and display a simpler message
        print(f"\n⚠️ Error displaying system instructions: {str(e)}\n", flush=True)
        return None


def print_api_docs():
    """Print API documentation with examples"""
    try:
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
            # URL description available for future use if needed
        else:
            server_url = f"http://localhost:{port}"
            # Local URL description available for future use if needed

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
    except Exception as e:
        # In case of any exception, log it and display a simpler message
        print(f"\n⚠️ Error displaying API documentation: {str(e)}\n", flush=True)
        return None


def format_multiline_text(text: str, prefix: str = "") -> str:
    """Format multiline text for display in a banner"""
    lines = text.strip().split('\n')
    return '\n'.join([f"{prefix}{line}" for line in lines])


def print_footer():
    """Print a footer with author information and social media links."""
    try:
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
        return footer
    except Exception as e:
        # In case of any exception, log it and display a simpler message
        print(f"\n⚠️ Error displaying footer: {str(e)}\n", flush=True)
        return None