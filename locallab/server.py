"""
Server startup and management functionality for LocalLab
"""

import asyncio
import signal
import sys
import time
import threading
import traceback
import socket
import uvicorn
import os
from colorama import Fore, Style, init
init(autoreset=True)

from typing import Optional, Dict, List, Tuple
from . import __version__
from .utils.networking import is_port_in_use, setup_ngrok
from .ui.banners import (
    print_initializing_banner, 
    print_running_banner, 
    print_system_resources,
    print_model_info,
    print_api_docs,
    print_system_instructions
)
from .logger import get_logger
from .logger.logger import set_server_status, log_request
from .utils.system import get_gpu_memory
from .config import (
    DEFAULT_MODEL,
    system_instructions,
    ENABLE_QUANTIZATION, 
    QUANTIZATION_TYPE,
    ENABLE_ATTENTION_SLICING,
    ENABLE_BETTERTRANSFORMER, 
    ENABLE_FLASH_ATTENTION
)

# Import torch - handle import error gracefully
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# Get the logger instance
logger = get_logger("locallab.server")


def check_environment() -> List[Tuple[str, str, bool]]:
    """
    Check the environment for potential issues
    
    Returns:
        List of (issue, suggestion, is_critical) tuples
    """
    issues = []
    
    # Check Python version
    py_version = sys.version_info
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 8):
        issues.append((
            f"Python version {py_version.major}.{py_version.minor} is below recommended 3.8+",
            "Consider upgrading to Python 3.8 or newer for better compatibility",
            False
        ))
    
    # Check for Colab environment
    try:
        import google.colab
        in_colab = True
    except ImportError:
        in_colab = False
    
    # Check for ngrok token if in Colab
    if in_colab:
        if not os.environ.get("NGROK_AUTH_TOKEN"):
            issues.append((
                "Running in Google Colab without NGROK_AUTH_TOKEN set",
                "Set os.environ['NGROK_AUTH_TOKEN'] = 'your_token' for public URL access. Get your token from https://dashboard.ngrok.com/get-started/your-authtoken",
                True
            ))
        
        # Check Colab runtime type for GPU
        if TORCH_AVAILABLE and not torch.cuda.is_available():
            issues.append((
                "Running in Colab without GPU acceleration",
                "Change runtime type to GPU: Runtime > Change runtime type > Hardware accelerator > GPU",
                True
            ))
        elif not TORCH_AVAILABLE:
            issues.append((
                "PyTorch is not installed",
                "Install PyTorch with: pip install torch",
                True
            ))
    
    # Check for CUDA and GPU availability
    if TORCH_AVAILABLE:
        if not torch.cuda.is_available():
            issues.append((
                "CUDA is not available - using CPU for inference",
                "This will be significantly slower. Consider using a GPU for better performance",
                False
            ))
        else:
            # Check GPU memory
            try:
                gpu_info = get_gpu_memory()
                if gpu_info:
                    total_mem, free_mem = gpu_info
                    if free_mem < 2000:  # Less than 2GB free
                        issues.append((
                            f"Low GPU memory: Only {free_mem}MB available",
                            "Models may require 2-6GB of GPU memory. Consider closing other applications or using a smaller model",
                            True if free_mem < 1000 else False
                        ))
            except Exception as e:
                logger.warning(f"Failed to check GPU memory: {str(e)}")
    else:
        issues.append((
            "PyTorch is not installed",
            "Install PyTorch with: pip install torch",
            True
        ))
    
    # Check system memory
    try:
        import psutil
        memory = psutil.virtual_memory()
        total_gb = memory.total / (1024 * 1024 * 1024)
        available_gb = memory.available / (1024 * 1024 * 1024)
        
        if available_gb < 2.0:  # Less than 2GB available
            issues.append((
                f"Low system memory: Only {available_gb:.1f}GB available",
                "Models may require 2-8GB of system memory. Consider closing other applications",
                True
            ))
    except Exception as e:
        pass  # Skip if psutil isn't available
    
    # Check for required dependencies
    try:
        import transformers
    except ImportError:
        issues.append((
            "Transformers library is not installed",
            "Install with: pip install transformers",
            True
        ))
    
    # Check disk space for model downloads
    try:
        import shutil
        _, _, free = shutil.disk_usage("/")
        free_gb = free / (1024 * 1024 * 1024)
        
        if free_gb < 5.0:  # Less than 5GB free
            issues.append((
                f"Low disk space: Only {free_gb:.1f}GB available",
                "Models may require 2-5GB of disk space for downloading and caching",
                True if free_gb < 2.0 else False
            ))
    except Exception as e:
        pass  # Skip if disk check fails
    
    return issues


def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    print(f"\n{Fore.YELLOW}Received signal {signum}, shutting down server...{Style.RESET_ALL}")
    
    # Update server status
    set_server_status("shutting_down")
    
    # Attempt to run shutdown tasks
    try:
        # Import here to avoid circular imports
        from .core.app import shutdown_event
        
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            loop.create_task(shutdown_event())
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
    
    # Exit after a short delay to allow cleanup
    def delayed_exit():
        time.sleep(2)  # Give some time for cleanup
        sys.exit(0)
        
    threading.Thread(target=delayed_exit, daemon=True).start()


def start_server(use_ngrok: bool = False, port=8000, ngrok_auth_token: Optional[str] = None):
    """Start the LocalLab server directly in the main process"""
    
    # Set initial server status
    set_server_status("initializing")
    
    # Display startup banner with INITIALIZING status
    print_initializing_banner(__version__)
    
    # Check environment for issues
    issues = check_environment()
    if issues:
        print(f"\n{Fore.YELLOW}⚠️ Environment Check Results:{Style.RESET_ALL}")
        for issue, suggestion, is_critical in issues:
            prefix = f"{Fore.RED}CRITICAL:" if is_critical else f"{Fore.YELLOW}WARNING:"
            print(f"{prefix} {issue}{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}Suggestion: {suggestion}{Style.RESET_ALL}\n")
    
    # Check if port is already in use
    if is_port_in_use(port):
        logger.warning(f"Port {port} is already in use. Trying to find another port...")
        for p in range(port+1, port+100):
            if not is_port_in_use(p):
                port = p
                logger.info(f"Using alternative port: {port}")
                break
        else:
            raise RuntimeError(f"Could not find an available port in range {port}-{port+100}")
    
    # Set up ngrok before starting server if requested
    public_url = None
    if use_ngrok:
        logger.info(f"{Fore.CYAN}Setting up ngrok tunnel to port {port}...{Style.RESET_ALL}")
        public_url = setup_ngrok(port=port, auth_token=ngrok_auth_token)
        if public_url:
            ngrok_section = f"\n{Fore.CYAN}┌────────────────────────── Ngrok Tunnel Details ─────────────────────────────┐{Style.RESET_ALL}\n│\n│  🚀 Ngrok Public URL: {Fore.GREEN}{public_url}{Style.RESET_ALL}\n│\n{Fore.CYAN}└──────────────────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n"
            logger.info(ngrok_section)
            print(ngrok_section)
        else:
            logger.warning(f"{Fore.YELLOW}Failed to set up ngrok tunnel. Server will run locally on port {port}.{Style.RESET_ALL}")
            logger.warning(f"{Fore.YELLOW}Note: In Google Colab, this means you'll only be able to access the server from within Colab.{Style.RESET_ALL}")
            logger.warning(f"{Fore.YELLOW}If you need public access, please set up ngrok with an auth token.{Style.RESET_ALL}")
    
    # Server info section
    server_section = f"\n{Fore.CYAN}┌────────────────────────── Server Details ─────────────────────────────┐{Style.RESET_ALL}\n│\n│  🖥️ Local URL: {Fore.GREEN}http://localhost:{port}{Style.RESET_ALL}\n│  ⚙️ Status: {Fore.GREEN}Starting{Style.RESET_ALL}\n│  🔄 Model Loading: {Fore.YELLOW}In Progress{Style.RESET_ALL}\n│\n{Fore.CYAN}└──────────────────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n"
    print(server_section, flush=True)
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Import app here to avoid circular imports
    try:
        from .core.app import app
    except ImportError as e:
        logger.error(f"{Fore.RED}Failed to import app: {str(e)}{Style.RESET_ALL}")
        logger.error(f"{Fore.RED}This could be due to circular imports or missing dependencies.{Style.RESET_ALL}")
        logger.error(f"{Fore.YELLOW}Please ensure all dependencies are installed: pip install -e .{Style.RESET_ALL}")
        raise
    
    # Create a function to display the Running banner when the server is ready
    def on_startup():
        # Update server status to running
        set_server_status("running")
        print_running_banner(port, public_url)
        
        # Print current system instructions
        instructions_text = system_instructions.get_instructions()
        print_system_instructions(instructions_text)
        
        # Import here to avoid circular imports
        from .core.app import model_manager
        
        # Print model info if a model is loaded
        if model_manager.current_model:
            model_info = model_manager.get_model_info()
            print_model_info(model_info)
        else:
            # Print model settings from environment variables
            env_model_info = {
                "model_id": os.environ.get("HUGGINGFACE_MODEL", DEFAULT_MODEL),
                "model_name": os.environ.get("HUGGINGFACE_MODEL", DEFAULT_MODEL).split("/")[-1],
                "parameters": "Unknown (not loaded yet)",
                "device": "cpu" if not torch.cuda.is_available() else f"cuda:{torch.cuda.current_device()}",
                "quantization": QUANTIZATION_TYPE if ENABLE_QUANTIZATION else "None",
                "optimizations": {
                    "attention_slicing": ENABLE_ATTENTION_SLICING,
                    "flash_attention": ENABLE_FLASH_ATTENTION,
                    "better_transformer": ENABLE_BETTERTRANSFORMER
                }
            }
            print_model_info(env_model_info)
        
        # Print API documentation
        print_api_docs()
    
    # Start uvicorn server directly in the main process
    try:
        if use_ngrok:
            # Colab environment setup
            import nest_asyncio
            nest_asyncio.apply()
            logger.info(f"Starting server on port {port} (Colab mode)")
            
            # Define the callback for Colab
            async def on_startup_async():
                on_startup()
            
            config = uvicorn.Config(
                app, 
                host="0.0.0.0", 
                port=port, 
                reload=False, 
                log_level="info",
                # Use an async callback function, not a list
                callback_notify=on_startup_async
            )
            server = uvicorn.Server(config)
            asyncio.get_event_loop().run_until_complete(server.serve())
        else:
            # Local environment
            logger.info(f"Starting server on port {port} (local mode)")
            # For local environment, we'll need a custom callback
            # We'll use a custom Server subclass for this
            class ServerWithCallback(uvicorn.Server):
                def install_signal_handlers(self):
                    # Override to prevent uvicorn from installing its own handlers
                    pass
                
                async def serve(self, sockets=None):
                    self.config.setup_event_loop()
                    await self.startup(sockets=sockets)
                    # Call our callback before processing requests
                    if callable(self.config.callback_notify):
                        await self.config.callback_notify()
                    elif isinstance(self.config.callback_notify, list):
                        for callback in self.config.callback_notify:
                            if callable(callback):
                                callback()
                    on_startup()  # Always ensure our startup function is called
                    await self.main_loop()
                    await self.shutdown()
            
            config = uvicorn.Config(
                app, 
                host="127.0.0.1", 
                port=port, 
                reload=False, 
                workers=1, 
                log_level="info",
                # This won't be used directly, as we call on_startup in the ServerWithCallback class
                callback_notify=None
            )
            server = ServerWithCallback(config)
            asyncio.run(server.serve())
    except Exception as e:
        # Update server status on error
        set_server_status("error")
        
        # Clean up ngrok if server fails to start
        if use_ngrok and public_url:
            try:
                from pyngrok import ngrok
                ngrok.disconnect(public_url)
            except Exception as ngrok_e:
                logger.error(f"Failed to disconnect ngrok: {str(ngrok_e)}")
                
        logger.error(f"Server startup failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise 

def cli():
    """Command line interface entry point for the package"""
    import click
    
    @click.command()
    @click.option('--use-ngrok', is_flag=True, help='Enable ngrok for public access')
    @click.option('--port', default=8000, help='Port to run the server on')
    @click.option('--ngrok-auth-token', help='Ngrok authentication token')
    def run(use_ngrok, port, ngrok_auth_token):
        """Run the LocalLab server"""
        start_server(use_ngrok=use_ngrok, port=port, ngrok_auth_token=ngrok_auth_token)
    
    run()

if __name__ == "__main__":
    cli() 