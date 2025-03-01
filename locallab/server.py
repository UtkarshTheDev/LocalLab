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

from typing import Optional
from . import __version__
from .utils.networking import is_port_in_use, setup_ngrok
from .ui.banners import print_initializing_banner, print_running_banner
from .logger import get_logger
from .logger.logger import set_server_status, log_request

# Get the logger instance
logger = get_logger("locallab.server")

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

def start_server(use_ngrok: bool = False, port=8000):
    """Start the LocalLab server directly in the main process"""
    
    # Set initial server status
    set_server_status("initializing")
    
    # Display startup banner with INITIALIZING status
    print_initializing_banner(__version__)
    
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
        public_url = setup_ngrok(port=port)
        if public_url:
            ngrok_section = f"\n{Fore.CYAN}┌────────────────────────── Ngrok Tunnel Details ─────────────────────────────┐{Style.RESET_ALL}\n│\n│  🚀 Ngrok Public URL: {Fore.GREEN}{public_url}{Style.RESET_ALL}\n│\n{Fore.CYAN}└──────────────────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n"
            logger.info(ngrok_section)
            print(ngrok_section)
        else:
            logger.warning(f"{Fore.YELLOW}Failed to set up ngrok tunnel. Server will run locally on port {port}.{Style.RESET_ALL}")
    
    # Server info section
    server_section = f"\n{Fore.CYAN}┌────────────────────────── Server Details ─────────────────────────────┐{Style.RESET_ALL}\n│\n│  🖥️ Local URL: {Fore.GREEN}http://localhost:{port}{Style.RESET_ALL}\n│  ⚙️ Status: {Fore.GREEN}Starting{Style.RESET_ALL}\n│  🔄 Model Loading: {Fore.YELLOW}In Progress{Style.RESET_ALL}\n│\n{Fore.CYAN}└──────────────────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n"
    print(server_section, flush=True)
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Import app here to avoid circular imports
    from .core.app import app
    
    # Create a function to display the Running banner when the server is ready
    def on_startup():
        # Update server status to running
        set_server_status("running")
        print_running_banner(port, public_url)
    
    # Start uvicorn server directly in the main process
    try:
        if use_ngrok:
            # Colab environment setup
            import nest_asyncio
            nest_asyncio.apply()
            logger.info(f"Starting server on port {port} (Colab mode)")
            config = uvicorn.Config(
                app, 
                host="0.0.0.0", 
                port=port, 
                reload=False, 
                log_level="info",
                # Add callback to print the RUNNING banner when server starts
                callback_notify=[on_startup]
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
                    for callback in self.config.callback_notify:
                        callback()
                    await self.main_loop()
                    await self.shutdown()
            
            config = uvicorn.Config(
                app, 
                host="127.0.0.1", 
                port=port, 
                reload=False, 
                workers=1, 
                log_level="info",
                callback_notify=[on_startup]
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
            except:
                pass
        logger.error(f"Server startup failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise 