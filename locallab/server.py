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
import logging
from colorama import Fore, Style, init
init(autoreset=True)

from typing import Optional, Dict, List, Tuple, Any
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

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

logger = get_logger("locallab.server")


def check_environment() -> List[Tuple[str, str, bool]]:
    issues = []
    
    py_version = sys.version_info
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 8):
        issues.append((
            f"Python version {py_version.major}.{py_version.minor} is below recommended 3.8+",
            "Consider upgrading to Python 3.8 or newer for better compatibility",
            False
        ))
    
    in_colab = is_in_colab()
    
    if in_colab:
        if not os.environ.get("NGROK_AUTH_TOKEN"):
            issues.append((
                "Running in Google Colab without NGROK_AUTH_TOKEN set",
                "Set os.environ['NGROK_AUTH_TOKEN'] = 'your_token' for public URL access. Get your token from https://dashboard.ngrok.com/get-started/your-authtoken",
                True
            ))
        
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
    
    if TORCH_AVAILABLE:
        if not torch.cuda.is_available():
            issues.append((
                "CUDA is not available - using CPU for inference",
                "This will be significantly slower. Consider using a GPU for better performance",
                False
            ))
        else:
            try:
                gpu_info = get_gpu_memory()
                if gpu_info:
                    total_mem, free_mem = gpu_info
                    if free_mem < 2000:
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
    
    try:
        import psutil
        memory = psutil.virtual_memory()
        total_gb = memory.total / (1024 * 1024 * 1024)
        available_gb = memory.available / (1024 * 1024 * 1024)
        
        if available_gb < 2.0:
            issues.append((
                f"Low system memory: Only {available_gb:.1f}GB available",
                "Models may require 2-8GB of system memory. Consider closing other applications",
                True
            ))
    except Exception as e:
        pass
    
    try:
        import transformers
    except ImportError:
        issues.append((
            "Transformers library is not installed",
            "Install with: pip install transformers",
            True
        ))
    
    try:
        import shutil
        _, _, free = shutil.disk_usage("/")
        free_gb = free / (1024 * 1024 * 1024)
        
        if free_gb < 5.0:
            issues.append((
                f"Low disk space: Only {free_gb:.1f}GB available",
                "Models may require 2-5GB of disk space for downloading and caching",
                True if free_gb < 2.0 else False
            ))
    except Exception as e:
        pass
    
    return issues


def signal_handler(signum, frame):
    print(f"\n{Fore.YELLOW}Received signal {signum}, shutting down server...{Style.RESET_ALL}")
    
    set_server_status("shutting_down")
    
    try:
        from .core.app import shutdown_event
        
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            loop.create_task(shutdown_event())
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
    
    def delayed_exit():
        time.sleep(5)
        
        try:
            from .core.app import app
            if hasattr(app, "state") and hasattr(app.state, "server") and app.state.server:
                logger.debug("Server still running after timeout, forcing exit")
            else:
                logger.debug("Server shutdown completed successfully")
        except Exception:
            pass
        
        logger.info("Forcing process termination to ensure clean shutdown")
        # Use os._exit to guarantee termination even if other threads are running
        os._exit(0)
        
    # Start a daemonic thread to force exit after a timeout
    force_exit_thread = threading.Thread(target=delayed_exit, daemon=True)
    force_exit_thread.start()
    
    # Signal the main thread to exit immediately
    # This is important to ensure that even if the server is stuck, the process will terminate
    logger.info("Sending SIGINT to the current process to ensure clean exit")
    time.sleep(1)  # Give some time for the delayed_exit thread to start
    
    # If we're still running after 1 second, try to force kill the process again
    os.kill(os.getpid(), signal.SIGTERM)


class NoopLifespan:
    
    def __init__(self, app):
        self.app = app
    
    async def startup(self):
        logger.warning("Using NoopLifespan - server may not handle startup/shutdown events properly")
        pass
    
    async def shutdown(self):
        pass


class SimpleTCPServer:
    
    def __init__(self, config):
        self.config = config
        self.server = None
        self.started = False
        self._serve_task = None
        self._socket = None
        self.app = config.app
        self.callback_triggered = False
    
    async def start(self):
        self.started = True
        logger.info("Started SimpleTCPServer as fallback")
        
        # Trigger callback if server has one and it hasn't been triggered yet
        if (hasattr(self, 'server') and self.server and 
            hasattr(self.server, 'on_startup_callback') and 
            not self.callback_triggered and
            not (hasattr(self.server, 'callback_triggered') and self.server.callback_triggered)):
            logger.info("Executing startup callback from SimpleTCPServer.start")
            self.server.on_startup_callback()
            self.callback_triggered = True
            if hasattr(self.server, 'callback_triggered'):
                self.server.callback_triggered = True
        
        if not self._serve_task:
            self._serve_task = asyncio.create_task(self._run_server())
    
    async def _run_server(self):
        try:
            self._running = True
            
            import socket
            host = self.config.host
            port = self.config.port
            
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            try:
                self._socket.bind((host, port))
                self._socket.listen(100)
                self._socket.setblocking(False)
                
                logger.info(f"SimpleTCPServer listening on {host}:{port}")
                
                loop = asyncio.get_event_loop()
                
                try:
                    from uvicorn.protocols.http.h11_impl import H11Protocol
                    from uvicorn.protocols.utils import get_remote_addr, get_local_addr
                    from uvicorn.config import Config
                    
                    protocol_config = Config(app=self.app, host=host, port=port)
                    
                    use_uvicorn_protocol = True
                    logger.info("Using uvicorn's H11Protocol for request handling")
                except ImportError:
                    use_uvicorn_protocol = False
                    logger.warning("Could not import uvicorn's H11Protocol, using basic request handling")
                
                while self._running:
                    try:
                        client_socket, addr = await loop.sock_accept(self._socket)
                        logger.debug(f"Connection from {addr}")
                        
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
        try:
            loop = asyncio.get_event_loop()
            
            client_socket.setblocking(False)
            
            request_data = b""
            while True:
                try:
                    chunk = await loop.sock_recv(client_socket, 4096)
                    if not chunk:
                        break
                    request_data += chunk
                    
                    if b"\r\n\r\n" in request_data:
                        break
                except Exception:
                    break
            
            if not request_data:
                return
            
            try:
                request_line, *headers_data = request_data.split(b"\r\n")
                method, path, _ = request_line.decode('utf-8').split(' ', 2)
                
                headers = {}
                for header in headers_data:
                    if b":" in header:
                        key, value = header.split(b":", 1)
                        headers[key.decode('utf-8').strip()] = value.decode('utf-8').strip()
                
                path_parts = path.split('?', 1)
                path_without_query = path_parts[0]
                query_string = path_parts[1].encode('utf-8') if len(path_parts) > 1 else b""
                
                body = b""
                if b"\r\n\r\n" in request_data:
                    body = request_data.split(b"\r\n\r\n", 1)[1]
                
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
                
                async def send(message):
                    if message["type"] == "http.response.start":
                        status = message["status"]
                        headers = message.get("headers", [])
                        
                        response_line = f"HTTP/1.1 {status} OK\r\n"
                        
                        header_lines = []
                        for name, value in headers:
                            header_lines.append(f"{name.decode('utf-8')}: {value.decode('utf-8')}")
                        
                        if not any(name.lower() == b"content-type" for name, _ in headers):
                            header_lines.append("Content-Type: text/plain")
                        
                        header_lines.append("Connection: close")
                        
                        header_block = "\r\n".join(header_lines) + "\r\n\r\n"
                        
                        await loop.sock_sendall(client_socket, (response_line + header_block).encode('utf-8'))
                    
                    elif message["type"] == "http.response.body":
                        body = message.get("body", b"")
                        await loop.sock_sendall(client_socket, body)
                        
                        if not message.get("more_body", False):
                            client_socket.close()
                
                async def receive():
                    return {
                        "type": "http.request",
                        "body": body,
                        "more_body": False,
                    }
                
                await self.app(scope, receive, send)
                
            except Exception as e:
                logger.error(f"Error parsing request or running ASGI app: {str(e)}")
                logger.debug(f"Request parsing error details: {traceback.format_exc()}")
                
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
        """Shutdown the TCP server gracefully"""
        logger.info("Shutting down SimpleTCPServer")
        
        # First mark server as stopping to prevent new connections
        self.started = False
        if hasattr(self, '_running'):
            self._running = False
        
        # Cancel any running tasks
        if self._serve_task and not self._serve_task.done():
            try:
                logger.debug("Cancelling serve task")
                self._serve_task.cancel()
                try:
                    await asyncio.wait_for(self._serve_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    logger.debug("Serve task cancelled or timed out")
            except Exception as e:
                logger.warning(f"Error cancelling serve task: {str(e)}")
            finally:
                self._serve_task = None
        
        # Close socket connections
        if self._socket:
            try:
                logger.debug("Closing server socket")
                self._socket.close()
            except Exception as e:
                logger.warning(f"Error closing socket: {str(e)}")
            finally:
                self._socket = None
        
        # Try to clean up event loop tasks
        try:
            # Clean up any pending tasks
            tasks = [t for t in asyncio.all_tasks() 
                    if t is not asyncio.current_task() and not t.done()]
            if tasks:
                logger.debug(f"Cancelling {len(tasks)} remaining tasks")
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.warning(f"Error cleaning up tasks: {str(e)}")
        
        logger.info("SimpleTCPServer shutdown completed")
    
    async def serve(self, sock=None):
        """Main server method, keeps running until shutdown"""
        self.started = True
        try:
            while self.started:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("SimpleTCPServer.serve task cancelled")
        except Exception as e:
            logger.error(f"Error in SimpleTCPServer.serve: {str(e)}")
            logger.debug(f"SimpleTCPServer.serve error details: {traceback.format_exc()}")
        finally:
            self.started = False
            logger.info("SimpleTCPServer.serve exited")

    def handle_app_startup_complete(self):
        """Handle application startup complete event"""
        if self.callback_triggered:
            return
            
        if hasattr(self, 'server') and self.server and hasattr(self.server, 'on_startup_callback'):
            logger.info("Executing startup callback from SimpleTCPServer.handle_app_startup_complete")
            self.server.on_startup_callback()
            self.callback_triggered = True
            if hasattr(self.server, 'callback_triggered'):
                self.server.callback_triggered = True


class ServerWithCallback(uvicorn.Server):
    def __init__(self, config):
        super().__init__(config)
        self.servers = []  # Initialize servers list
        self.should_exit = False
        self.callback_triggered = False  # Flag to track if callback has been triggered
        
    def install_signal_handlers(self):
        def handle_exit(signum, frame):
            self.should_exit = True
            logger.debug(f"Signal {signum} received in ServerWithCallback, setting should_exit=True")
            
            # Try to propagate the signal to parent process
            # This helps ensure the process exits properly
            try:
                os.kill(os.getpid(), signal.SIGTERM)
            except Exception:
                pass
        
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
    
    async def startup(self, sockets=None):
        if self.should_exit:
            return
        
        try:
            await super().startup(sockets=sockets)
            logger.info("Using uvicorn's built-in Server implementation")
            
            # Execute callback after successful startup
            # This is critical to show the running banner
            if hasattr(self, 'on_startup_callback') and not self.callback_triggered:
                logger.info("Executing server startup callback")
                self.on_startup_callback()
                self.callback_triggered = True
                
        except Exception as e:
            logger.error(f"Error during server startup: {str(e)}")
            logger.debug(f"Server startup error details: {traceback.format_exc()}")
            self.servers = []
            
            # Create SimpleTCPServer as fallback
            if sockets:
                for socket in sockets:
                    server = SimpleTCPServer(config=self.config)
                    server.server = self
                    await server.start()
                    self.servers.append(server)
                    
                    # Make sure callback is executed for the fallback server too
                    if hasattr(self, 'on_startup_callback') and not self.callback_triggered:
                        logger.info("Executing server startup callback (fallback server)")
                        self.on_startup_callback()
                        self.callback_triggered = True
            else:
                server = SimpleTCPServer(config=self.config)
                server.server = self
                await server.start()
                self.servers.append(server)
                
                # Make sure callback is executed for the fallback server too
                if hasattr(self, 'on_startup_callback') and not self.callback_triggered:
                    logger.info("Executing server startup callback (fallback server)")
                    self.on_startup_callback()
                    self.callback_triggered = True

    # Add a method to explicitly handle the application startup complete event
    def handle_app_startup_complete(self):
        if hasattr(self, 'on_startup_callback') and not self.callback_triggered:
            logger.info("Executing server startup callback from app startup complete event")
            self.on_startup_callback()
            self.callback_triggered = True

    async def shutdown(self, sockets=None):
        logger.debug("Starting server shutdown process")
        
        # First shutdown any SimpleTCPServer instances
        for server in self.servers:
            try:
                # Check if the server has a shutdown method before calling it
                if hasattr(server, 'shutdown') and callable(server.shutdown):
                    await server.shutdown()
                    logger.debug("SimpleTCPServer shutdown completed")
                else:
                    logger.warning(f"Server object of type {type(server)} does not have a shutdown method")
                    # Try other shutdown methods that might be available
                    if hasattr(server, 'stop') and callable(server.stop):
                        if asyncio.iscoroutinefunction(server.stop):
                            await server.stop()
                        else:
                            server.stop()
                        logger.debug("Server stop method called instead of shutdown")
                    elif hasattr(server, 'close') and callable(server.close):
                        if asyncio.iscoroutinefunction(server.close):
                            await server.close()
                        else:
                            server.close()
                        logger.debug("Server close method called instead of shutdown")
            except Exception as e:
                logger.error(f"Error shutting down server: {str(e)}")
                logger.debug(f"Server shutdown error details: {traceback.format_exc()}")
        
        # Clear servers list
        self.servers = []
        
        # Shutdown lifespan
        if self.lifespan is not None:
            try:
                await self.lifespan.shutdown()
                logger.debug("Lifespan shutdown completed")
            except Exception as e:
                logger.error(f"Error during lifespan shutdown: {str(e)}")
        
        self.lifespan = None
        
        logger.debug("Server shutdown process completed")
        
        # Force exit after a short delay if the server is still running
        def force_exit():
            time.sleep(2)
            logger.info("Forcing process termination after shutdown")
            os._exit(0)
        
        threading.Thread(target=force_exit, daemon=True).start()

def start_server(use_ngrok: bool = None, port: int = None, ngrok_auth_token: Optional[str] = None):
    try:
        set_server_status("initializing")
        
        # Print initializing banner immediately
        print_initializing_banner(__version__)
        
        # Load configuration
        from .cli.config import load_config, set_config_value
        
        try:
            saved_config = load_config()
        except Exception as e:
            logger.warning(f"Error loading configuration: {str(e)}. Using defaults.")
            saved_config = {}
            
        # Set up ngrok configuration
        use_ngrok = (
            use_ngrok if use_ngrok is not None 
            else saved_config.get("use_ngrok", False) 
            or os.environ.get("LOCALLAB_USE_NGROK", "").lower() == "true"
        )
        
        # Get port configuration
        port = port or saved_config.get("port", None) or int(os.environ.get("LOCALLAB_PORT", "8000"))
        
        # Handle ngrok auth token
        if ngrok_auth_token:
            os.environ["NGROK_AUTHTOKEN"] = ngrok_auth_token
        elif saved_config.get("ngrok_auth_token"):
            os.environ["NGROK_AUTHTOKEN"] = saved_config["ngrok_auth_token"]
            
        # Set up ngrok if enabled
        public_url = None
        if use_ngrok:
            os.environ["LOCALLAB_USE_NGROK"] = "true"
            
            if not os.environ.get("NGROK_AUTHTOKEN"):
                logger.error("Ngrok auth token is required for public access. Please set it in the configuration.")
                logger.info("You can get a free token from: https://dashboard.ngrok.com/get-started/your-authtoken")
                raise ValueError("Ngrok auth token is required for public access")
                
            logger.info(f"Setting up ngrok tunnel to port {port}...")
            public_url = setup_ngrok(port)
            
            if public_url:
                os.environ["LOCALLAB_NGROK_URL"] = public_url
                
                ngrok_section = f"\n{Fore.CYAN}┌────────────────────────── Ngrok Tunnel Details ─────────────────────────────┐{Style.RESET_ALL}\n│\n│  🚀 Ngrok Public URL: {Fore.GREEN}{public_url}{Style.RESET_ALL}\n│\n{Fore.CYAN}└──────────────────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n"
                print(ngrok_section)
            else:
                logger.error(f"Failed to set up ngrok tunnel. Server will run locally on port {port}.")
                raise RuntimeError("Failed to set up ngrok tunnel")
        else:
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

        # Flag to track if startup has been completed
        startup_complete = [False]  # Using a list as a mutable reference

        # Create a custom logging handler to detect when the application is ready
        class StartupDetectionHandler(logging.Handler):
            def __init__(self, server_ref):
                super().__init__()
                self.server_ref = server_ref
                
            def emit(self, record):
                if not startup_complete[0] and "Application startup complete" in record.getMessage():
                    logger.info("Detected application startup complete message")
                    if hasattr(self.server_ref, "handle_app_startup_complete"):
                        self.server_ref.handle_app_startup_complete()
                    else:
                        logger.warning("Server reference doesn't have handle_app_startup_complete method")
                        # Call on_startup directly as a fallback
                        on_startup()

        def on_startup():
            # Use the mutable reference to track startup
            if startup_complete[0]:
                return

            try:
                logger.info("Server startup callback triggered")
                
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
                startup_complete[0] = True
                logger.info("Server startup display completed successfully")
                
            except Exception as e:
                logger.error(f"Error during server startup display: {str(e)}")
                logger.debug(f"Startup display error details: {traceback.format_exc()}")
                # Still mark startup as complete to avoid repeated attempts
                startup_complete[0] = True
                # Ensure server status is set to running even if display fails
                set_server_status("running")

        try:
            # Detect if we're in Google Colab
            in_colab = is_in_colab()
            
            # Create server reference holder
            server_ref = [None]
            
            # Set up the log handler for startup detection
            startup_handler = StartupDetectionHandler(server_ref)
            logging.getLogger("uvicorn").addHandler(startup_handler)
            logging.getLogger("uvicorn.error").addHandler(startup_handler)
            
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
                    # This is an async callback that uvicorn might call
                    if not startup_complete[0]:
                        on_startup()
                
                config = uvicorn.Config(
                    app, 
                    host="0.0.0.0",  # Bind to all interfaces in Colab
                    port=port, 
                    reload=False, 
                    log_level="info",
                    callback_notify=[on_startup_async]  # Use a list for the callback
                )
                
                server = ServerWithCallback(config)
                server.on_startup_callback = on_startup  # Also set the direct callback
                server_ref[0] = server  # Store reference for log handler
                
                # Use the appropriate event loop method based on Python version
                try:
                    # Wrap in try/except to handle server startup errors
                    try:
                        asyncio.run(server.serve())
                    except AttributeError as e:
                        if "'Server' object has no attribute 'start'" in str(e):
                            # If we get the 'start' attribute error, use our SimpleTCPServer directly
                            logger.warning("Falling back to direct SimpleTCPServer implementation")
                            direct_server = SimpleTCPServer(config=config)  # Pass the config directly
                            direct_server.server = server  # Set reference to the server for callbacks
                            server_ref[0] = direct_server  # Update reference
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
                                direct_server = SimpleTCPServer(config=config)  # Pass the config directly
                                direct_server.server = server  # Set reference to the server for callbacks
                                server_ref[0] = direct_server  # Update reference
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
                    callback_notify=[lambda: on_startup()]  # Use a lambda to prevent immediate execution
                )
                
                server = ServerWithCallback(config)
                server.on_startup_callback = on_startup  # Set the callback directly
                server_ref[0] = server  # Store reference for log handler
                
                # Use asyncio.run which is more reliable
                try:
                    # Wrap in try/except to handle server startup errors
                    try:
                        asyncio.run(server.serve())
                    except AttributeError as e:
                        if "'Server' object has no attribute 'start'" in str(e):
                            # If we get the 'start' attribute error, use our SimpleTCPServer directly
                            logger.warning("Falling back to direct SimpleTCPServer implementation")
                            direct_server = SimpleTCPServer(config=config)  # Pass the config directly
                            direct_server.server = server  # Set reference to the server for callbacks
                            server_ref[0] = direct_server  # Update reference
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
                                direct_server = SimpleTCPServer(config=config)  # Pass the config directly
                                direct_server.server = server  # Set reference to the server for callbacks
                                server_ref[0] = direct_server  # Update reference
                                loop.run_until_complete(direct_server.serve())
                            else:
                                raise
                    else:
                        # Re-raise other errors
                        raise
                        
            # If we reach here and startup hasn't completed yet, call it manually as a fallback
            if not startup_complete[0]:
                logger.warning("Server started but startup callback wasn't triggered. Calling manually...")
                on_startup()
                
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

def cli():
    """Command line interface entry point for the package"""
    import click
    import sys
    
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
        
        # Run the interactive configuration
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
        from .utils.system import get_system_resources
        
        try:
            resources = get_system_resources()
            
            click.echo("\n🖥️ System Information:")
            click.echo(f"  CPU: {resources.get('cpu_count', 'Unknown')} cores")
            
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
    if len(sys.argv) <= 1 or sys.argv[1] == '--help' or sys.argv[1] == '-h':
        return locallab_cli()
    
    # For specific commands, we can optimize further
    if sys.argv[1] == 'info':
        return locallab_cli(['info'])
    
    return locallab_cli()

if __name__ == "__main__":
    cli()