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
from .cli.interactive import prompt_for_config, is_in_colab
from .cli.config import save_config, set_config_value, get_config_value, load_config, get_all_config

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
    in_colab = is_in_colab()
    
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


class NoopLifespan:
    """A no-op lifespan implementation for when all lifespan initialization attempts fail."""
    
    def __init__(self, app):
        """Initialize with the app."""
        self.app = app
    
    async def startup(self):
        """No-op startup method."""
        logger.warning("Using NoopLifespan - server may not handle startup/shutdown events properly")
        pass
    
    async def shutdown(self):
        """No-op shutdown method."""
        pass


class SimpleTCPServer:
    """A simple TCP server implementation for when TCPServer import fails."""
    
    def __init__(self, config):
        """Initialize with the config."""
        self.config = config
        self.server = None
        self.started = False
        self._serve_task = None
        self._socket = None
        self._running = False
    
    async def start(self):
        """Start the server."""
        self.started = True
        logger.info("Started SimpleTCPServer as fallback")
        
        # Create a task to run the server
        if not self._serve_task:
            self._serve_task = asyncio.create_task(self._run_server())
    
    async def _run_server(self):
        """Run the server in a separate task."""
        try:
            self._running = True
            
            # Try to create a socket
            import socket
            host = self.config.host
            port = self.config.port
            
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            try:
                self._socket.bind((host, port))
                self._socket.listen(100)  # Backlog
                self._socket.setblocking(False)
                
                logger.info(f"SimpleTCPServer listening on {host}:{port}")
                
                # Create a simple HTTP server
                loop = asyncio.get_event_loop()
                
                while self._running:
                    try:
                        client_socket, addr = await loop.sock_accept(self._socket)
                        logger.debug(f"Connection from {addr}")
                        
                        # Handle the connection in a separate task
                        asyncio.create_task(self._handle_connection(client_socket))
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Error accepting connection: {str(e)}")
            finally:
                if self._socket:
                    self._socket.close()
                    self._socket = None
        except Exception as e:
            logger.error(f"Error in SimpleTCPServer._run_server: {str(e)}")
            logger.debug(f"SimpleTCPServer._run_server error details: {traceback.format_exc()}")
        finally:
            self._running = False
    
    async def _handle_connection(self, client_socket):
        """Handle a client connection."""
        try:
            loop = asyncio.get_event_loop()
            
            # Set non-blocking mode
            client_socket.setblocking(False)
            
            # Read the request
            request_data = b""
            while True:
                try:
                    chunk = await loop.sock_recv(client_socket, 4096)
                    if not chunk:
                        break
                    request_data += chunk
                    
                    # Check if we've received the end of the HTTP request
                    if b"\r\n\r\n" in request_data:
                        break
                except Exception:
                    break
            
            # Prepare a simple HTTP response
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/plain\r\n"
                b"Connection: close\r\n"
                b"\r\n"
                b"LocalLab server is running (fallback mode)"
            )
            
            # Send the response
            await loop.sock_sendall(client_socket, response)
        except Exception as e:
            logger.error(f"Error handling connection: {str(e)}")
        finally:
            try:
                client_socket.close()
            except Exception:
                pass
    
    async def shutdown(self):
        """Shutdown the server."""
        self.started = False
        self._running = False
        
        # Cancel the serve task
        if self._serve_task:
            self._serve_task.cancel()
            try:
                await self._serve_task
            except asyncio.CancelledError:
                pass
            self._serve_task = None
        
        # Close the socket
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        
        logger.info("Shutdown SimpleTCPServer")
    
    async def serve(self, sock=None):
        """Serve the application."""
        self.started = True
        try:
            # Keep the server running until shutdown is called
            while self.started:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in SimpleTCPServer.serve: {str(e)}")
            logger.debug(f"SimpleTCPServer.serve error details: {traceback.format_exc()}")
        finally:
            self.started = False


class ServerWithCallback(uvicorn.Server):
    def install_signal_handlers(self):
        # Override to prevent uvicorn from installing its own handlers
        pass
    
    async def startup(self, sockets=None):
        """Override the startup method to add error handling for lifespan startup."""
        if self.should_exit:
            return
        
        # Custom implementation that doesn't rely on config.server_class
        if sockets is not None:
            self.servers = []
            for socket in sockets:
                # Use TCPServer directly instead of relying on config.server_class
                try:
                    # Try the newer location first
                    from uvicorn.server import TCPServer
                    server = TCPServer(config=self.config)
                except (ImportError, AttributeError):
                    try:
                        # Try the older location
                        from uvicorn.protocols.http.h11_impl import TCPServer
                        server = TCPServer(config=self.config)
                    except (ImportError, AttributeError):
                        # Last resort - use a simple server implementation
                        logger.warning("Could not import TCPServer - using simple server implementation")
                        # Use our custom SimpleTCPServer instead of uvicorn.Server
                        server = SimpleTCPServer(config=self.config)
                
                server.server = self  # Set the server reference
                # Check if the server has a start method, otherwise use serve
                if hasattr(server, 'start'):
                    await server.start()
                elif hasattr(server, 'serve'):
                    # Create a task for serve but don't await it directly
                    # as it would block indefinitely
                    asyncio.create_task(server.serve())
                else:
                    logger.error(f"Server object {type(server)} has neither start() nor serve() method")
                    raise RuntimeError("Incompatible server implementation")
                self.servers.append(server)
        else:
            # Use TCPServer directly instead of relying on config.server_class
            try:
                # Try the newer location first
                from uvicorn.server import TCPServer
                server = TCPServer(config=self.config)
            except (ImportError, AttributeError):
                try:
                    # Try the older location
                    from uvicorn.protocols.http.h11_impl import TCPServer
                    server = TCPServer(config=self.config)
                except (ImportError, AttributeError):
                    # Last resort - use a simple server implementation
                    logger.warning("Could not import TCPServer - using simple server implementation")
                    # Use our custom SimpleTCPServer instead of uvicorn.Server
                    server = SimpleTCPServer(config=self.config)
            
            server.server = self  # Set the server reference
            # Check if the server has a start method, otherwise use serve
            if hasattr(server, 'start'):
                await server.start()
            elif hasattr(server, 'serve'):
                # Create a task for serve but don't await it directly
                # as it would block indefinitely
                asyncio.create_task(server.serve())
            else:
                logger.error(f"Server object {type(server)} has neither start() nor serve() method")
                raise RuntimeError("Incompatible server implementation")
            self.servers = [server]
        
        if self.lifespan is not None:
            try:
                await self.lifespan.startup()
            except Exception as e:
                logger.error(f"Error during lifespan startup: {str(e)}")
                logger.debug(f"Lifespan startup error details: {traceback.format_exc()}")
                # Replace with NoopLifespan if startup fails
                self.lifespan = NoopLifespan(self.config.app)
                logger.warning("Replaced failed lifespan with NoopLifespan")
    
    async def main_loop(self):
        """Custom main loop implementation with error handling."""
        try:
            # Use asyncio.sleep to keep the server running
            while not self.should_exit:
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            logger.debug(f"Main loop error details: {traceback.format_exc()}")
            # Set should_exit to True to initiate shutdown
            self.should_exit = True
    
    async def shutdown(self, sockets=None):
        """Override the shutdown method to add error handling for lifespan shutdown."""
        if self.servers:
            for server in self.servers:
                try:
                    # Check if the server has a shutdown method
                    if hasattr(server, 'shutdown'):
                        await server.shutdown()
                    else:
                        logger.warning(f"Server object {type(server)} has no shutdown method, skipping")
                except Exception as e:
                    logger.error(f"Error shutting down server: {str(e)}")
                    logger.debug(f"Server shutdown error details: {traceback.format_exc()}")
        
        if self.lifespan is not None:
            try:
                await self.lifespan.shutdown()
            except Exception as e:
                logger.error(f"Error during lifespan shutdown: {str(e)}")
                logger.debug(f"Lifespan shutdown error details: {traceback.format_exc()}")
                logger.warning("Continuing shutdown despite lifespan error")
    
    async def serve(self, sockets=None):
        self.config.setup_event_loop()
        
        # Initialize lifespan attribute before startup
        # Handle different versions of uvicorn
        self.lifespan = None
        
        try:
            # Try the newer location first (uvicorn >= 0.18.0)
            from uvicorn.lifespan.on import LifespanOn
            # LifespanOn may only accept app parameter in some versions
            try:
                # Try with just the app parameter
                self.lifespan = LifespanOn(self.config.app)
                logger.info("Using LifespanOn from uvicorn.lifespan.on (single parameter)")
            except TypeError:
                # If that fails, try with both parameters
                try:
                    self.lifespan = LifespanOn(
                        self.config.app,
                        self.config.lifespan_on if hasattr(self.config, "lifespan_on") else "auto"
                    )
                    logger.info("Using LifespanOn from uvicorn.lifespan.on (two parameters)")
                except TypeError:
                    logger.debug("LifespanOn initialization failed with both one and two parameters")
                    raise
        except (ImportError, AttributeError, TypeError) as e:
            logger.debug(f"Failed to import or initialize LifespanOn: {str(e)}")
            try:
                # Try the older location (uvicorn < 0.18.0)
                from uvicorn.lifespan.lifespan import Lifespan
                try:
                    # Try with just the app parameter
                    self.lifespan = Lifespan(self.config.app)
                    logger.info("Using Lifespan from uvicorn.lifespan.lifespan (single parameter)")
                except TypeError:
                    try:
                        # Try with two parameters
                        self.lifespan = Lifespan(
                            self.config.app,
                            "auto"
                        )
                        logger.info("Using Lifespan from uvicorn.lifespan.lifespan (two parameters)")
                    except TypeError:
                        # Try with three parameters
                        self.lifespan = Lifespan(
                            self.config.app,
                            "auto",
                            logger
                        )
                        logger.info("Using Lifespan from uvicorn.lifespan.lifespan (three parameters)")
                logger.info("Using Lifespan from uvicorn.lifespan.lifespan")
            except (ImportError, AttributeError, TypeError) as e:
                logger.debug(f"Failed to import or initialize Lifespan from lifespan.lifespan: {str(e)}")
                try:
                    # Try the oldest location
                    from uvicorn.lifespan import Lifespan
                    try:
                        # Try with just the app parameter
                        self.lifespan = Lifespan(self.config.app)
                        logger.info("Using Lifespan from uvicorn.lifespan (single parameter)")
                    except TypeError:
                        try:
                            # Try with two parameters
                            self.lifespan = Lifespan(
                                self.config.app,
                                "auto"
                            )
                            logger.info("Using Lifespan from uvicorn.lifespan (two parameters)")
                        except TypeError:
                            # Try with three parameters
                            self.lifespan = Lifespan(
                                self.config.app,
                                "auto",
                                logger
                            )
                            logger.info("Using Lifespan from uvicorn.lifespan (three parameters)")
                    logger.info("Using Lifespan from uvicorn.lifespan")
                except (ImportError, AttributeError, TypeError) as e:
                    logger.debug(f"Failed to import or initialize Lifespan from uvicorn.lifespan: {str(e)}")
                    try:
                        # Try the newest location (uvicorn >= 0.21.0)
                        from uvicorn.lifespan.state import LifespanState
                        try:
                            # Try with just the app parameter
                            self.lifespan = LifespanState(self.config.app)
                            logger.info("Using LifespanState from uvicorn.lifespan.state (single parameter)")
                        except TypeError:
                            # Try with logger parameter
                            self.lifespan = LifespanState(
                                self.config.app,
                                logger=logger
                            )
                            logger.info("Using LifespanState from uvicorn.lifespan.state (with logger)")
                        logger.info("Using LifespanState from uvicorn.lifespan.state")
                    except (ImportError, AttributeError, TypeError) as e:
                        logger.debug(f"Failed to import or initialize LifespanState: {str(e)}")
                        # Fallback to NoopLifespan
                        self.lifespan = NoopLifespan(self.config.app)
                        logger.warning("Using NoopLifespan - server may not handle startup/shutdown events properly")
        
        try:
            await self.startup(sockets=sockets)
            
            # Call our callback before processing requests
            # We need to access the on_startup function from the outer scope
            if hasattr(self, 'on_startup_callback') and callable(self.on_startup_callback):
                self.on_startup_callback()
            
            await self.main_loop()
            await self.shutdown()
        except Exception as e:
            logger.error(f"Error during server operation: {str(e)}")
            logger.debug(f"Server error details: {traceback.format_exc()}")
            # Re-raise to allow proper error handling
            raise


def start_server(use_ngrok: bool = None, port: int = None, ngrok_auth_token: Optional[str] = None):
    """Start the LocalLab server directly in the main process"""
    
    try:
        # Import here to avoid circular imports
        from .cli.config import load_config, set_config_value
        
        # Load existing configuration
        try:
            saved_config = load_config()
        except Exception as e:
            logger.warning(f"Error loading configuration: {str(e)}. Using defaults.")
            saved_config = {}
        
        # Apply saved configuration to environment variables
        for key, value in saved_config.items():
            if key == "model_id":
                os.environ["HUGGINGFACE_MODEL"] = str(value)
            elif key == "ngrok_auth_token":
                os.environ["NGROK_AUTH_TOKEN"] = str(value)
            elif key in ["enable_quantization", "enable_attention_slicing", "enable_flash_attention", 
                        "enable_better_transformer", "enable_cpu_offloading", "enable_cache", 
                        "enable_file_logging"]:
                env_key = f"LOCALLAB_{key.upper()}"
                os.environ[env_key] = str(value).lower()
            elif key in ["quantization_type", "model_timeout", "cache_ttl", "log_level", "log_file"]:
                env_key = f"LOCALLAB_{key.upper()}"
                os.environ[env_key] = str(value)
        
        # Interactive CLI configuration if needed
        config = prompt_for_config(use_ngrok, port, ngrok_auth_token)
        
        # Save configuration for future use
        save_config(config)
        
        # Extract values from config
        use_ngrok = config.get("use_ngrok", use_ngrok)
        port = config.get("port", port or 8000)
        ngrok_auth_token = config.get("ngrok_auth_token", ngrok_auth_token)
        
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
            # Check if we have an ngrok auth token
            if not ngrok_auth_token and not os.environ.get("NGROK_AUTH_TOKEN"):
                logger.error("Ngrok auth token is required for public access. Please set it in the configuration.")
                logger.info("You can get a free token from: https://dashboard.ngrok.com/get-started/your-authtoken")
                raise ValueError("Ngrok auth token is required for public access")
            
            logger.info(f"{Fore.CYAN}Setting up ngrok tunnel to port {port}...{Style.RESET_ALL}")
            public_url = setup_ngrok(port=port, auth_token=ngrok_auth_token or os.environ.get("NGROK_AUTH_TOKEN"))
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
        try:
            from .core.app import app
        except ImportError as e:
            logger.error(f"{Fore.RED}Failed to import app: {str(e)}{Style.RESET_ALL}")
            logger.error(f"{Fore.RED}This could be due to circular imports or missing dependencies.{Style.RESET_ALL}")
            logger.error(f"{Fore.YELLOW}Please ensure all dependencies are installed: pip install -e .{Style.RESET_ALL}")
            raise
        
        # Create a function to display the Running banner when the server is ready
        startup_complete = False  # Flag to track if startup has been completed
        
        def on_startup():
            # Use a flag to ensure this function only runs once
            nonlocal startup_complete
            if startup_complete:
                return
            
            try:
                # Set server status to running
                set_server_status("running")
                
                # Display the RUNNING banner
                print_running_banner(__version__)
                
                try:
                    # Display system resources
                    print_system_resources()
                except Exception as e:
                    logger.error(f"Error displaying system resources: {str(e)}")
                    logger.debug(f"System resources error details: {traceback.format_exc()}")
                
                try:
                    # Display model information
                    print_model_info()
                except Exception as e:
                    logger.error(f"Error displaying model information: {str(e)}")
                    logger.debug(f"Model information error details: {traceback.format_exc()}")
                
                try:
                    # Display system instructions
                    print_system_instructions()
                except Exception as e:
                    logger.error(f"Error displaying system instructions: {str(e)}")
                    logger.debug(f"System instructions error details: {traceback.format_exc()}")
                
                try:
                    # Display API documentation
                    print_api_docs()
                except Exception as e:
                    logger.error(f"Error displaying API documentation: {str(e)}")
                    logger.debug(f"API documentation error details: {traceback.format_exc()}")
                
                # Set flag to indicate startup is complete
                startup_complete = True
            except Exception as e:
                logger.error(f"Error during server startup display: {str(e)}")
                logger.debug(f"Startup display error details: {traceback.format_exc()}")
                # Still mark startup as complete to avoid repeated attempts
                startup_complete = True
                # Ensure server status is set to running even if display fails
                set_server_status("running")
        
        # Start uvicorn server directly in the main process
        try:
            # Detect if we're in Google Colab
            in_colab = is_in_colab()
            
            if in_colab or use_ngrok:
                # Colab environment setup
                try:
                    import nest_asyncio
                    nest_asyncio.apply()
                except ImportError:
                    logger.warning("nest_asyncio not available. This may cause issues in Google Colab.")
                    
                logger.info(f"Starting server on port {port} (Colab/ngrok mode)")
                
                # Define the callback for Colab
                async def on_startup_async():
                    # This will only run once due to the flag in on_startup
                    on_startup()
                
                config = uvicorn.Config(
                    app, 
                    host="0.0.0.0",  # Bind to all interfaces in Colab
                    port=port, 
                    reload=False, 
                    log_level="info",
                    # Use an async callback function, not a list
                    callback_notify=on_startup_async
                )
                server = ServerWithCallback(config)
                server.on_startup_callback = on_startup  # Set the callback
                
                # Use the appropriate event loop method based on Python version
                try:
                    # Wrap in try/except to handle server startup errors
                    try:
                        asyncio.run(server.serve())
                    except AttributeError as e:
                        if "'Server' object has no attribute 'start'" in str(e):
                            # If we get the 'start' attribute error, use our SimpleTCPServer directly
                            logger.warning("Falling back to direct SimpleTCPServer implementation")
                            direct_server = SimpleTCPServer(config)
                            asyncio.run(direct_server.serve())
                        else:
                            raise
                except RuntimeError as e:
                    # Handle "Event loop is already running" error
                    if "Event loop is already running" in str(e):
                        logger.warning("Event loop is already running. Using get_event_loop instead.")
                        loop = asyncio.get_event_loop()
                        try:
                            loop.run_until_complete(server.serve())
                        except AttributeError as e:
                            if "'Server' object has no attribute 'start'" in str(e):
                                # If we get the 'start' attribute error, use our SimpleTCPServer directly
                                logger.warning("Falling back to direct SimpleTCPServer implementation")
                                direct_server = SimpleTCPServer(config)
                                loop.run_until_complete(direct_server.serve())
                            else:
                                raise
                    else:
                        # Re-raise other errors
                        raise
            else:
                # Local environment
                logger.info(f"Starting server on port {port} (local mode)")
                # For local environment, we'll use a custom Server subclass
                config = uvicorn.Config(
                    app, 
                    host="127.0.0.1",  # Localhost only for local mode
                    port=port, 
                    reload=False, 
                    workers=1, 
                    log_level="info",
                    # This won't be used directly, as we call on_startup in the ServerWithCallback class
                    callback_notify=None
                )
                server = ServerWithCallback(config)
                server.on_startup_callback = on_startup  # Set the callback
                
                # Use asyncio.run which is more reliable
                try:
                    # Wrap in try/except to handle server startup errors
                    try:
                        asyncio.run(server.serve())
                    except AttributeError as e:
                        if "'Server' object has no attribute 'start'" in str(e):
                            # If we get the 'start' attribute error, use our SimpleTCPServer directly
                            logger.warning("Falling back to direct SimpleTCPServer implementation")
                            direct_server = SimpleTCPServer(config)
                            asyncio.run(direct_server.serve())
                        else:
                            raise
                except RuntimeError as e:
                    # Handle "Event loop is already running" error
                    if "Event loop is already running" in str(e):
                        logger.warning("Event loop is already running. Using get_event_loop instead.")
                        loop = asyncio.get_event_loop()
                        try:
                            loop.run_until_complete(server.serve())
                        except AttributeError as e:
                            if "'Server' object has no attribute 'start'" in str(e):
                                # If we get the 'start' attribute error, use our SimpleTCPServer directly
                                logger.warning("Falling back to direct SimpleTCPServer implementation")
                                direct_server = SimpleTCPServer(config)
                                loop.run_until_complete(direct_server.serve())
                            else:
                                raise
                    else:
                        # Re-raise other errors
                        raise
        except Exception as e:
            logger.error(f"Server startup failed: {str(e)}")
            logger.error(traceback.format_exc())
            set_server_status("error")
            
            # Try to start a minimal server as a last resort
            try:
                logger.warning("Attempting to start minimal server as fallback")
                # Create a minimal config
                minimal_config = uvicorn.Config(
                    app="locallab.core.minimal:app",  # Use a minimal app if available, or create one
                    host="127.0.0.1",
                    port=port or 8000,
                    log_level="info"
                )
                
                # Create a simple server
                direct_server = SimpleTCPServer(config=minimal_config)
                
                # Start the server
                logger.info("Starting minimal server")
                asyncio.run(direct_server.serve())
            except Exception as e2:
                logger.error(f"Minimal server startup also failed: {str(e2)}")
                logger.error(traceback.format_exc())
                raise RuntimeError(f"Server startup failed: {str(e)}. Minimal server also failed: {str(e2)}")
            
            raise
    except Exception as e:
        logger.error(f"Fatal error during server initialization: {str(e)}")
        logger.error(traceback.format_exc())
        set_server_status("error")
        raise

def cli():
    """Command line interface entry point for the package"""
    # Only import click here to speed up initial import time
    import click
    import sys
    
    # Avoid importing other modules until they're needed
    # This significantly speeds up CLI startup
    
    @click.group()
    @click.version_option(__version__)
    def locallab_cli():
        """LocalLab - Your lightweight AI inference server for running LLMs locally"""
        pass
    
    @locallab_cli.command()
    @click.option('--use-ngrok', is_flag=True, help='Enable ngrok for public access')
    @click.option('--port', default=None, type=int, help='Port to run the server on')
    @click.option('--ngrok-auth-token', help='Ngrok authentication token')
    @click.option('--model', help='Model to load (e.g., microsoft/phi-2)')
    @click.option('--quantize', is_flag=True, help='Enable quantization')
    @click.option('--quantize-type', type=click.Choice(['int8', 'int4']), help='Quantization type')
    @click.option('--attention-slicing', is_flag=True, help='Enable attention slicing')
    @click.option('--flash-attention', is_flag=True, help='Enable flash attention')
    @click.option('--better-transformer', is_flag=True, help='Enable BetterTransformer')
    def start(use_ngrok, port, ngrok_auth_token, model, quantize, quantize_type, 
              attention_slicing, flash_attention, better_transformer):
        """Start the LocalLab server"""
        # Import the config system - lazy import to speed up CLI
        from .cli.config import set_config_value
        
        # Set configuration values from command line options
        if model:
            os.environ["HUGGINGFACE_MODEL"] = model
        
        if quantize:
            set_config_value('enable_quantization', 'true')
            if quantize_type:
                set_config_value('quantization_type', quantize_type)
        
        if attention_slicing:
            set_config_value('enable_attention_slicing', 'true')
        
        if flash_attention:
            set_config_value('enable_flash_attention', 'true')
        
        if better_transformer:
            set_config_value('enable_better_transformer', 'true')
        
        # Start the server
        start_server(use_ngrok=use_ngrok, port=port, ngrok_auth_token=ngrok_auth_token)
    
    @locallab_cli.command()
    def config():
        """Configure LocalLab settings"""
        # Lazy import to speed up CLI
        from .cli.interactive import prompt_for_config
        from .cli.config import save_config, load_config, get_all_config
        
        # Show current configuration if it exists
        current_config = load_config()
        if current_config:
            click.echo("\n📋 Current Configuration:")
            for key, value in current_config.items():
                click.echo(f"  {key}: {value}")
            click.echo("")
            
            # Ask if user wants to reconfigure
            if not click.confirm("Would you like to reconfigure these settings?", default=True):
                click.echo("Configuration unchanged.")
                return
        
        # This will run the interactive configuration without starting the server
        config = prompt_for_config(force_reconfigure=True)
        save_config(config)
        
        # Show the new configuration
        click.echo("\n📋 New Configuration:")
        for key, value in config.items():
            click.echo(f"  {key}: {value}")
        
        click.echo("\n✅ Configuration saved successfully!")
        click.echo("You can now run 'locallab start' to start the server with these settings.")
    
    @locallab_cli.command()
    def info():
        """Display system information"""
        # Lazy import to speed up CLI
        from .utils.system import get_system_resources
        
        try:
            resources = get_system_resources()
            
            click.echo("\n🖥️ System Information:")
            click.echo(f"  CPU: {resources.get('cpu_count', 'Unknown')} cores")
            
            # Handle RAM display with proper error checking
            ram_gb = resources.get('ram_total', 0) / (1024 * 1024 * 1024) if 'ram_total' in resources else 0
            click.echo(f"  RAM: {ram_gb:.1f} GB")
            
            if resources.get('gpu_available', False):
                click.echo("\n🎮 GPU Information:")
                for i, gpu in enumerate(resources.get('gpu_info', [])):
                    click.echo(f"  GPU {i}: {gpu.get('name', 'Unknown')}")
                    vram_gb = gpu.get('total_memory', 0) / (1024 * 1024 * 1024) if 'total_memory' in gpu else 0
                    click.echo(f"    VRAM: {vram_gb:.1f} GB")
            else:
                click.echo("\n⚠️ No GPU detected")
                
            # Display Python version
            import sys
            click.echo(f"\n🐍 Python: {sys.version.split()[0]}")
            
            # Display LocalLab version
            click.echo(f"📦 LocalLab: {__version__}")
            
            # Display configuration location
            from pathlib import Path
            config_path = Path.home() / ".locallab" / "config.json"
            if config_path.exists():
                click.echo(f"\n⚙️ Configuration: {config_path}")
            
        except Exception as e:
            click.echo(f"\n❌ Error retrieving system information: {str(e)}")
            click.echo("Please check that all required dependencies are installed.")
            return 1
    
    # Use sys.argv to check if we're just showing help
    # This avoids importing modules unnecessarily
    if len(sys.argv) <= 1 or sys.argv[1] == '--help' or sys.argv[1] == '-h':
        return locallab_cli()
    
    # For specific commands, we can optimize further
    if sys.argv[1] == 'info':
        # For info command, we can bypass some imports
        return locallab_cli(['info'])
    
    return locallab_cli()

if __name__ == "__main__":
    cli() 