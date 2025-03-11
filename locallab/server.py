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
        # Give more time for cleanup - increased from 2 to 5 seconds
        # This allows the server to complete its shutdown process
        time.sleep(5)
        
        # Check if we need to force exit
        try:
            # Import here to avoid circular imports
            from .core.app import app
            if hasattr(app, "state") and hasattr(app.state, "server") and app.state.server:
                logger.debug("Server still running after timeout, forcing exit")
            else:
                logger.debug("Server shutdown completed successfully")
        except Exception:
            pass
        
        # Force exit the process completely - use os._exit instead of sys.exit
        # This ensures all threads are terminated
        logger.info("Forcing process termination to ensure clean shutdown")
        os._exit(0)
        
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
        self.app = config.app
    
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
                
                # Try to import uvicorn's HTTP protocol implementation
                try:
                    from uvicorn.protocols.http.h11_impl import H11Protocol
                    from uvicorn.protocols.utils import get_remote_addr, get_local_addr
                    from uvicorn.config import Config
                    
                    # Create a config for the protocol
                    protocol_config = Config(app=self.app, host=host, port=port)
                    
                    # Use uvicorn's protocol implementation if available
                    use_uvicorn_protocol = True
                    logger.info("Using uvicorn's H11Protocol for request handling")
                except ImportError:
                    use_uvicorn_protocol = False
                    logger.warning("Could not import uvicorn's H11Protocol, using basic request handling")
                
                while self._running:
                    try:
                        client_socket, addr = await loop.sock_accept(self._socket)
                        logger.debug(f"Connection from {addr}")
                        
                        # Handle the connection in a separate task
                        if use_uvicorn_protocol:
                            server = self.server if hasattr(self, 'server') else None
                            remote_addr = get_remote_addr(client_socket)
                            local_addr = get_local_addr(client_socket)
                            protocol = H11Protocol(
                                config=protocol_config,
                                server=server,
                                client=client_socket,
                                server_state={"total_requests": 0},
                                client_addr=remote_addr,
                                root_path="",
                            )
                            asyncio.create_task(protocol.run_asgi(self.app))
                        else:
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
        """Handle a client connection using a basic ASGI implementation."""
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
            
            if not request_data:
                return
            
            # Parse the HTTP request
            try:
                # Basic HTTP request parsing
                request_line, *headers_data = request_data.split(b"\r\n")
                method, path, _ = request_line.decode('utf-8').split(' ', 2)
                
                # Parse headers
                headers = {}
                for header in headers_data:
                    if b":" in header:
                        key, value = header.split(b":", 1)
                        headers[key.decode('utf-8').strip()] = value.decode('utf-8').strip()
                
                # Extract query string
                path_parts = path.split('?', 1)
                path_without_query = path_parts[0]
                query_string = path_parts[1].encode('utf-8') if len(path_parts) > 1 else b""
                
                # Extract body
                body = b""
                if b"\r\n\r\n" in request_data:
                    body = request_data.split(b"\r\n\r\n", 1)[1]
                
                # Create ASGI scope
                scope = {
                    "type": "http",
                    "asgi": {"version": "3.0", "spec_version": "2.0"},
                    "http_version": "1.1",
                    "method": method,
                    "scheme": "http",
                    "path": path_without_query,
                    "raw_path": path.encode('utf-8'),
                    "query_string": query_string,
                    "headers": [[k.lower().encode('utf-8'), v.encode('utf-8')] for k, v in headers.items()],
                    "client": ("127.0.0.1", 0),
                    "server": (self.config.host, self.config.port),
                }
                
                # Create response writer
                async def send(message):
                    if message["type"] == "http.response.start":
                        status = message["status"]
                        headers = message.get("headers", [])
                        
                        # Prepare response line
                        response_line = f"HTTP/1.1 {status} OK\r\n"
                        
                        # Prepare headers
                        header_lines = []
                        for name, value in headers:
                            header_lines.append(f"{name.decode('utf-8')}: {value.decode('utf-8')}")
                        
                        # Add default headers if not present
                        if not any(name.lower() == b"content-type" for name, _ in headers):
                            header_lines.append("Content-Type: text/plain")
                        
                        # Add connection close header
                        header_lines.append("Connection: close")
                        
                        # Combine headers
                        header_block = "\r\n".join(header_lines) + "\r\n\r\n"
                        
                        # Send response line and headers
                        await loop.sock_sendall(client_socket, (response_line + header_block).encode('utf-8'))
                    
                    elif message["type"] == "http.response.body":
                        body = message.get("body", b"")
                        await loop.sock_sendall(client_socket, body)
                        
                        # Close the connection if more_body is False or not specified
                        if not message.get("more_body", False):
                            client_socket.close()
                
                # Create request body iterator
                async def receive():
                    return {
                        "type": "http.request",
                        "body": body,
                        "more_body": False,
                    }
                
                # Run the ASGI application
                await self.app(scope, receive, send)
                
            except Exception as e:
                logger.error(f"Error parsing request or running ASGI app: {str(e)}")
                logger.debug(f"Request parsing error details: {traceback.format_exc()}")
                
                # Send a 500 error response
                error_response = (
                    b"HTTP/1.1 500 Internal Server Error\r\n"
                    b"Content-Type: text/plain\r\n"
                    b"Connection: close\r\n"
                    b"\r\n"
                    b"Internal Server Error: The server encountered an error processing your request."
                )
                await loop.sock_sendall(client_socket, error_response)
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
        # but still handle the should_exit flag for clean shutdown
        
        def handle_exit(signum, frame):
            self.should_exit = True
            logger.debug(f"Signal {signum} received in ServerWithCallback, setting should_exit=True")
        
        # Register our own minimal signal handlers that just set should_exit
        # This allows the main process signal handler to handle the actual shutdown
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
    
    async def startup(self, sockets=None):
        """Override the startup method to add error handling for lifespan startup."""
        if self.should_exit:
            return
        
        # In newer versions of uvicorn (0.34.0+), TCPServer is no longer available
        # Instead, we should use the Server class directly
        if sockets is not None:
            # For newer versions of uvicorn, we don't need to create separate servers
            # Just use the built-in functionality
            try:
                # Call the parent class's startup method
                await super().startup(sockets=sockets)
                logger.info("Using uvicorn's built-in Server implementation")
            except Exception as e:
                logger.error(f"Error during server startup: {str(e)}")
                logger.debug(f"Server startup error details: {traceback.format_exc()}")
                # If the parent class's startup method fails, fall back to our custom implementation
                self.servers = []
                for socket in sockets:
                    server = SimpleTCPServer(config=self.config)
                    server.server = self  # Set the server reference
                    await server.start()
                    self.servers.append(server)
        else:
            # For newer versions of uvicorn, we don't need to create separate servers
            # Just use the built-in functionality
            try:
                # Call the parent class's startup method
                await super().startup(sockets=None)
                logger.info("Using uvicorn's built-in Server implementation")
            except Exception as e:
                logger.error(f"Error during server startup: {str(e)}")
                logger.debug(f"Server startup error details: {traceback.format_exc()}")
                # If the parent class's startup method fails, fall back to our custom implementation
                server = SimpleTCPServer(config=self.config)
                server.server = self  # Set the server reference
                await server.start()
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
                # Check more frequently to respond to shutdown signals faster
                await asyncio.sleep(0.05)
                
                # Check if we've received a shutdown signal
                if self.should_exit:
                    logger.debug("Shutdown signal detected in main_loop")
                    break
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            logger.debug(f"Main loop error details: {traceback.format_exc()}")
            # Set should_exit to True to initiate shutdown
            self.should_exit = True
        
        logger.debug("Exiting main_loop")
    
    async def shutdown(self, sockets=None):
        """Override the shutdown method to add error handling for lifespan shutdown."""
        logger.debug("Starting server shutdown process")
        
        # First, shut down all servers
        if self.servers:
            for server in self.servers:
                try:
                    server.close()
                    await server.wait_closed()
                    logger.debug("Server closed successfully")
                except Exception as e:
                    logger.error(f"Error closing server: {str(e)}")
                    logger.debug(f"Server close error details: {traceback.format_exc()}")
        
        # Then, shut down the lifespan
        if self.lifespan is not None:
            try:
                await self.lifespan.shutdown()
                logger.debug("Lifespan shutdown completed")
            except Exception as e:
                logger.error(f"Error during lifespan shutdown: {str(e)}")
                logger.debug(f"Lifespan shutdown error details: {traceback.format_exc()}")
        
        # Clear all references to help with garbage collection
        self.servers = []
        self.lifespan = None
        
        logger.debug("Server shutdown process completed")
    
    async def serve(self, sockets=None):
        self.config.setup_event_loop()
        
        # Initialize lifespan attribute before startup
        # Handle different versions of uvicorn
        self.lifespan = None
        
        # Try different approaches to initialize the lifespan
        self._initialize_lifespan()
        
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
            
    def _initialize_lifespan(self):
        """Initialize the lifespan attribute with appropriate implementation based on uvicorn version."""
        # Try LifespanOn from uvicorn.lifespan.on (newer versions)
        try:
            from uvicorn.lifespan.on import LifespanOn
            
            # Try with config parameter (for newer versions like 0.34.0)
            try:
                self.lifespan = LifespanOn(config=self.config)
                logger.info("Using LifespanOn from uvicorn.lifespan.on with config parameter")
                return
            except TypeError:
                pass
                
            # Try with app parameter (for older versions)
            try:
                self.lifespan = LifespanOn(self.config.app)
                logger.info("Using LifespanOn from uvicorn.lifespan.on with app parameter")
                return
            except TypeError:
                pass
                
            # Try with both parameters
            try:
                lifespan_on = self.config.lifespan_on if hasattr(self.config, "lifespan_on") else "auto"
                self.lifespan = LifespanOn(self.config.app, lifespan_on)
                logger.info("Using LifespanOn from uvicorn.lifespan.on with app and lifespan_on parameters")
                return
            except TypeError:
                pass
                
        except (ImportError, AttributeError):
            logger.debug("Could not import LifespanOn from uvicorn.lifespan.on")
            
        # Try Lifespan from uvicorn.lifespan.lifespan (older versions)
        try:
            from uvicorn.lifespan.lifespan import Lifespan
            
            # Try with app parameter
            try:
                self.lifespan = Lifespan(self.config.app)
                logger.info("Using Lifespan from uvicorn.lifespan.lifespan with app parameter")
                return
            except TypeError:
                pass
                
            # Try with two parameters
            try:
                self.lifespan = Lifespan(self.config.app, "auto")
                logger.info("Using Lifespan from uvicorn.lifespan.lifespan with app and lifespan_on parameters")
                return
            except TypeError:
                pass
                
            # Try with three parameters
            try:
                self.lifespan = Lifespan(self.config.app, "auto", logger)
                logger.info("Using Lifespan from uvicorn.lifespan.lifespan with app, lifespan_on, and logger parameters")
                return
            except TypeError:
                pass
                
        except (ImportError, AttributeError):
            logger.debug("Could not import Lifespan from uvicorn.lifespan.lifespan")
            
        # Try Lifespan from uvicorn.lifespan (oldest versions)
        try:
            from uvicorn.lifespan import Lifespan
            
            # Try with app parameter
            try:
                self.lifespan = Lifespan(self.config.app)
                logger.info("Using Lifespan from uvicorn.lifespan with app parameter")
                return
            except TypeError:
                pass
                
            # Try with two parameters
            try:
                self.lifespan = Lifespan(self.config.app, "auto")
                logger.info("Using Lifespan from uvicorn.lifespan with app and lifespan_on parameters")
                return
            except TypeError:
                pass
                
            # Try with three parameters
            try:
                self.lifespan = Lifespan(self.config.app, "auto", logger)
                logger.info("Using Lifespan from uvicorn.lifespan with app, lifespan_on, and logger parameters")
                return
            except TypeError:
                pass
                
        except (ImportError, AttributeError):
            logger.debug("Could not import Lifespan from uvicorn.lifespan")
            
        # Try LifespanState from uvicorn.lifespan.state (newest versions)
        try:
            from uvicorn.lifespan.state import LifespanState
            
            # Try with app parameter
            try:
                self.lifespan = LifespanState(self.config.app)
                logger.info("Using LifespanState from uvicorn.lifespan.state with app parameter")
                return
            except TypeError:
                pass
                
            # Try with logger parameter
            try:
                self.lifespan = LifespanState(self.config.app, logger=logger)
                logger.info("Using LifespanState from uvicorn.lifespan.state with app and logger parameters")
                return
            except TypeError:
                pass
                
        except (ImportError, AttributeError):
            logger.debug("Could not import LifespanState from uvicorn.lifespan.state")
            
        # Fallback to NoopLifespan if all attempts fail
        self.lifespan = NoopLifespan(self.config.app)
        logger.warning("Using NoopLifespan - server may not handle startup/shutdown events properly")


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
            # Set environment variable to indicate ngrok is enabled
            os.environ["LOCALLAB_USE_NGROK"] = "true"
            
            # Check if we have an ngrok auth token
            if not ngrok_auth_token and not os.environ.get("NGROK_AUTH_TOKEN"):
                logger.error("Ngrok auth token is required for public access. Please set it in the configuration.")
                logger.info("You can get a free token from: https://dashboard.ngrok.com/get-started/your-authtoken")
                raise ValueError("Ngrok auth token is required for public access")
                
            logger.info(f"{Fore.CYAN}Setting up ngrok tunnel to port {port}...{Style.RESET_ALL}")
            public_url = setup_ngrok(port=port, auth_token=ngrok_auth_token or os.environ.get("NGROK_AUTH_TOKEN"))
            if public_url:
                # Set environment variable with the ngrok URL
                os.environ["LOCALLAB_NGROK_URL"] = public_url
                
                ngrok_section = f"\n{Fore.CYAN}┌────────────────────────── Ngrok Tunnel Details ─────────────────────────────┐{Style.RESET_ALL}\n│\n│  🚀 Ngrok Public URL: {Fore.GREEN}{public_url}{Style.RESET_ALL}\n│\n{Fore.CYAN}└──────────────────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n"
                logger.info(ngrok_section)
                print(ngrok_section)
            else:
                logger.warning(f"{Fore.YELLOW}Failed to set up ngrok tunnel. Server will run locally on port {port}.{Style.RESET_ALL}")
        else:
            # Set environment variable to indicate ngrok is not enabled
            os.environ["LOCALLAB_USE_NGROK"] = "false"
        
        # Set environment variable with the port
        os.environ["LOCALLAB_PORT"] = str(port)
        
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
                    
                try:
                    # Display footer with author information
                    from .ui.banners import print_footer
                    print_footer()
                except Exception as e:
                    logger.error(f"Error displaying footer: {str(e)}")
                    logger.debug(f"Footer display error details: {traceback.format_exc()}")
                
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