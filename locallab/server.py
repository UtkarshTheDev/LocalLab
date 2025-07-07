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
    # Display a clean shutdown banner
    shutdown_banner = f"""
{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}

{Fore.YELLOW}⚠️  SERVER SHUTDOWN IN PROGRESS                                      ⚠️{Style.RESET_ALL}
{Fore.YELLOW}⚠️  Please wait while resources are cleaned up...                    ⚠️{Style.RESET_ALL}

{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
    print(shutdown_banner)

    # Check if we're already shutting down to avoid duplication
    if hasattr(signal_handler, 'shutting_down') and signal_handler.shutting_down:
        print(f"{Fore.YELLOW}Already shutting down, please wait...{Style.RESET_ALL}")
        return

    # Set flag to avoid duplicate shutdown
    signal_handler.shutting_down = True

    # Update server status
    set_server_status("shutting_down")

    try:
        from .core.app import shutdown_event

        # Mark that this is a real shutdown that needs a force exit
        shutdown_event.force_exit_required = True

        # Get the event loop and schedule the shutdown event
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.create_task(shutdown_event())
                logger.debug("Scheduled shutdown_event in current event loop")
        except RuntimeError:
            # If we can't get the current event loop, create a new one
            logger.debug("Creating new event loop for shutdown")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(shutdown_event())
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

    def delayed_exit():
        # Give the server some time to shut down gracefully
        time.sleep(5)

        try:
            # Check if the server is still running
            from .core.app import app
            if hasattr(app, "state") and hasattr(app.state, "server") and app.state.server:
                logger.debug("Server still running after timeout, forcing exit")
            else:
                logger.debug("Server shutdown completed successfully")
        except Exception:
            pass

        # Display a clean exit banner
        exit_banner = f"""
{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}

{Fore.GREEN}✅  SERVER SHUTDOWN COMPLETE                                         ✅{Style.RESET_ALL}
{Fore.GREEN}✅  Thank you for using LocalLab!                                    ✅{Style.RESET_ALL}

{Fore.CYAN}════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
        print(exit_banner)

        # Force exit to ensure clean termination
        logger.info("Forcing process termination to ensure clean shutdown")
        # Use os._exit to guarantee termination even if other threads are running
        os._exit(0)

    # Start a daemonic thread to force exit after a timeout
    force_exit_thread = threading.Thread(target=delayed_exit, daemon=True)
    force_exit_thread.start()

# Initialize the shutting down flag
signal_handler.shutting_down = False


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

        # Disable uvicorn's default logging setup to prevent duplication
        self.config.log_config = None
        self.config.access_log = False

    def install_signal_handlers(self):
        def handle_exit(signum, frame):
            if hasattr(handle_exit, 'called') and handle_exit.called:
                return

            handle_exit.called = True
            self.should_exit = True
            logger.debug(f"Signal {signum} received in ServerWithCallback, setting should_exit=True")

            # Don't propagate signals back to avoid loops
            # The main signal_handler will handle process termination

        # Initialize the flag
        handle_exit.called = False

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
                # Handle different server types appropriately
                if isinstance(server, SimpleTCPServer):
                    # Our custom TCP server
                    await server.shutdown()
                    logger.debug("SimpleTCPServer shutdown completed")
                elif hasattr(server, 'shutdown') and callable(server.shutdown):
                    # Server with shutdown method
                    if asyncio.iscoroutinefunction(server.shutdown):
                        await server.shutdown()
                    else:
                        server.shutdown()
                    logger.debug("Server shutdown completed")
                elif hasattr(server, 'stop') and callable(server.stop):
                    # Server with stop method
                    if asyncio.iscoroutinefunction(server.stop):
                        await server.stop()
                    else:
                        server.stop()
                    logger.debug("Server stop method called")
                elif hasattr(server, 'close') and callable(server.close):
                    # Server with close method
                    if asyncio.iscoroutinefunction(server.close):
                        await server.close()
                    else:
                        server.close()
                    logger.debug("Server close method called")
                elif str(type(server).__name__) == "Server" and hasattr(server, "_server"):
                    # Handle asyncio.Server objects which don't have shutdown but have close
                    if hasattr(server._server, "close") and callable(server._server.close):
                        server._server.close()
                        logger.debug("Asyncio server closed")
                else:
                    # No recognized shutdown method, but don't log a warning to avoid noise
                    logger.debug(f"No recognized shutdown method for server of type {type(server).__name__}")
            except asyncio.CancelledError:
                # This is expected during shutdown, don't treat as an error
                logger.debug(f"Server shutdown task was cancelled for {type(server).__name__}")
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
            except asyncio.CancelledError:
                # This is expected during shutdown, don't treat as an error
                logger.debug("Lifespan shutdown task was cancelled")
            except Exception as e:
                logger.error(f"Error during lifespan shutdown: {str(e)}")

        self.lifespan = None

        logger.debug("Server shutdown process completed")

        # Force exit after a short delay if the server is still running
        def force_exit():
            time.sleep(2)
            # Only force exit if we're still running
            if not hasattr(self, "_exit_event") or not self._exit_event.is_set():
                logger.info("Forcing process termination after shutdown")
                os._exit(0)

        # Create an event to track clean exit
        self._exit_event = threading.Event()
        exit_thread = threading.Thread(target=force_exit, daemon=True)
        exit_thread.start()

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

                ngrok_section = f"""
{Fore.CYAN}═══════════════════════════════════════════════════════════════════════════════ Ngrok Tunnel Details ════════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}

  🚀 Ngrok Public URL: {Fore.GREEN}{public_url}{Style.RESET_ALL}

{Fore.CYAN}═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
                print(ngrok_section)
            else:
                logger.error(f"Failed to set up ngrok tunnel. Server will run locally on port {port}.")
                raise RuntimeError("Failed to set up ngrok tunnel")
        else:
            os.environ["LOCALLAB_USE_NGROK"] = "false"

        # Set environment variable with the port
        os.environ["LOCALLAB_PORT"] = str(port)

        # Server info section
        server_section = f"""
{Fore.CYAN}════════════════════════════════════ Server Details ════════════════════════════════════{Style.RESET_ALL}

  🖥️ Local URL: {Fore.GREEN}http://localhost:{port}{Style.RESET_ALL}
  ⚙️ Status: {Fore.YELLOW}Starting{Style.RESET_ALL}
  🔄 Model Loading: {Fore.YELLOW}In Progress{Style.RESET_ALL}

{Fore.CYAN}═══════════════════════════════════════════════════════════════════════════════════════════{Style.RESET_ALL}
"""
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
        should_force_exit = [False]  # To prevent premature shutdown

        # Create a custom logging handler to detect when the application is ready
        class StartupDetectionHandler(logging.Handler):
            def __init__(self, server_ref):
                super().__init__()
                self.server_ref = server_ref

            def emit(self, record):
                if not startup_complete[0] and "Application startup complete" in record.getMessage():
                    logger.info("Detected application startup complete message")
                    try:
                        if hasattr(self.server_ref[0], "handle_app_startup_complete"):
                            self.server_ref[0].handle_app_startup_complete()
                        else:
                            logger.warning("Server reference doesn't have handle_app_startup_complete method")
                            # Call on_startup directly as a fallback
                            on_startup()
                    except Exception as e:
                        logger.error(f"Error in startup detection handler: {e}")
                        # Still try to display banners as a last resort
                        on_startup()

        def on_startup():
            # Use the mutable reference to track startup
            if startup_complete[0]:
                return

            try:
                logger.info("Server startup callback triggered")

                # Mark startup as complete to prevent repeated calls
                startup_complete[0] = True

                # Check if a model is configured to load on startup
                try:
                    from .cli.config import get_config_value
                    from .config import DEFAULT_MODEL
                    import os

                    # Get the model that should be loaded
                    model_to_load = (
                        os.environ.get("HUGGINGFACE_MODEL") or
                        get_config_value("model") or
                        DEFAULT_MODEL
                    )

                    if model_to_load:
                        # Set server status to loading while model loads
                        set_server_status("loading")
                        logger.info("Server status changed to: loading (waiting for model)")
                        # Don't display running banner yet - wait for model to load
                        return
                    else:
                        # No model to load, set to running immediately
                        set_server_status("running")
                        logger.info("Server status changed to: running")
                except Exception as e:
                    # Fallback if anything fails
                    logger.warning(f"Could not determine model loading status: {e}")
                    set_server_status("running")
                    logger.info("Server status changed to: running")

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
                # Check if a model is configured to load before setting to running
                try:
                    from .cli.config import get_config_value
                    from .config import DEFAULT_MODEL
                    import os

                    # Get the model that should be loaded
                    model_to_load = (
                        os.environ.get("HUGGINGFACE_MODEL") or
                        get_config_value("model") or
                        DEFAULT_MODEL
                    )

                    if model_to_load:
                        set_server_status("loading")
                        logger.info("Server status changed to: loading (waiting for model)")
                    else:
                        set_server_status("running")
                        logger.info("Server status changed to: running")
                except Exception as e:
                    # Fallback if anything fails
                    logger.warning(f"Could not determine model loading status: {e}")
                    set_server_status("running")
                    logger.info("Server status changed to: running")

        # Define async callback that uvicorn can call
        async def on_startup_async():
            # This is an async callback that uvicorn might call
            if not startup_complete[0]:
                on_startup()

        # Define this as a function to be called by uvicorn
        def callback_notify_function():
            # If needed, create and return an awaitable
            loop = asyncio.get_event_loop()
            return loop.create_task(on_startup_async())

        try:
            # Detect if we're in Google Colab
            in_colab = is_in_colab()

            # Create server reference holder
            server_ref = [None]

            # Set up the log handler for startup detection
            # We'll use a custom handler that doesn't duplicate logs
            startup_handler = StartupDetectionHandler(server_ref)

            # Only add the handler if it's not already present
            uvicorn_logger = logging.getLogger("uvicorn")
            if not any(isinstance(h, StartupDetectionHandler) for h in uvicorn_logger.handlers):
                uvicorn_logger.addHandler(startup_handler)

            # Only add to error logger if needed
            uvicorn_error_logger = logging.getLogger("uvicorn.error")
            if not any(isinstance(h, StartupDetectionHandler) for h in uvicorn_error_logger.handlers):
                uvicorn_error_logger.addHandler(startup_handler)

            if in_colab or use_ngrok:
                # Colab environment setup
                try:
                    import nest_asyncio
                    nest_asyncio.apply()
                except ImportError:
                    logger.warning("nest_asyncio not available. This may cause issues in Google Colab.")

                logger.info(f"Starting server on port {port} (Colab/ngrok mode)")

                config = uvicorn.Config(
                    app,
                    host="0.0.0.0",  # Bind to all interfaces in Colab
                    port=port,
                    reload=False,
                    log_level="info",
                    log_config=None,  # Disable uvicorn's default logging config
                    access_log=False,  # Disable access logs to prevent duplication
                    callback_notify=callback_notify_function  # Use a function, not a list
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
                    log_config=None,  # Disable uvicorn's default logging config
                    access_log=False,  # Disable access logs to prevent duplication
                    callback_notify=callback_notify_function  # Use a function, not a lambda or list
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
            # Don't handle TypeError about 'list' object not being callable - that's exactly what we're fixing
            if "'list' object is not callable" in str(e):
                logger.error("Server error: callback_notify was passed a list instead of a callable function.")
                logger.error("This is a known issue that will be fixed in the next version.")
                raise

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
                    log_level="info",
                    log_config=None,  # Disable uvicorn's default logging config
                    access_log=False,  # Disable access logs to prevent duplication
                    callback_notify=None  # Don't use callbacks in the minimal server
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
    @click.option('--max-length', type=int, help='Maximum generation length in tokens')
    @click.option('--temperature', type=float, help='Temperature for generation (0.1-1.0)')
    @click.option('--top-p', type=float, help='Top-p for nucleus sampling (0.1-1.0)')
    @click.option('--top-k', type=int, help='Top-k for sampling (1-100)')
    @click.option('--repetition-penalty', type=float, help='Repetition penalty (1.0-2.0)')
    def start(use_ngrok, port, ngrok_auth_token, model, quantize, quantize_type,
              attention_slicing, flash_attention, better_transformer,
              max_length, temperature, top_p, top_k, repetition_penalty):
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

        # Set generation parameters if provided
        if max_length:
            set_config_value('max_length', str(max_length))
            os.environ["DEFAULT_MAX_LENGTH"] = str(max_length)

        if temperature:
            set_config_value('temperature', str(temperature))
            os.environ["DEFAULT_TEMPERATURE"] = str(temperature)

        if top_p:
            set_config_value('top_p', str(top_p))
            os.environ["DEFAULT_TOP_P"] = str(top_p)

        if top_k:
            set_config_value('top_k', str(top_k))
            os.environ["DEFAULT_TOP_K"] = str(top_k)

        if repetition_penalty:
            set_config_value('repetition_penalty', str(repetition_penalty))
            os.environ["DEFAULT_REPETITION_PENALTY"] = str(repetition_penalty)

        # Start the server
        start_server(use_ngrok=use_ngrok, port=port, ngrok_auth_token=ngrok_auth_token)

    @locallab_cli.command()
    def config():
        """Configure LocalLab settings"""
        from .cli.interactive import prompt_for_config
        from .cli.config import save_config, load_config, get_all_config

        # Check if this is a fresh installation
        current_config = load_config()

        # Check if this is truly a fresh install (no meaningful config exists)
        is_fresh_install = not current_config or len(current_config) == 0 or not any(
            key in current_config for key in [
                'model_id', 'enable_quantization', 'enable_cpu_offloading',
                'enable_attention_slicing', 'enable_flash_attention', 'enable_bettertransformer'
            ]
        )

        if is_fresh_install:
            # Fresh installation - show welcome screen
            click.echo("\n" + "🌟" * 25)
            click.echo("🎉 Welcome to LocalLab!")
            click.echo("🌟" * 25)
            click.echo("\n💡 This appears to be your first time using LocalLab.")
            click.echo("   Let's get you set up with a quick configuration!")
            click.echo("\n🚀 We'll guide you through:")
            click.echo("   • Choosing an AI model")
            click.echo("   • Optimizing performance for your hardware")
            click.echo("   • Setting up authentication tokens")
            click.echo("   • Configuring public access (optional)")
            click.echo("\n✨ This will only take a few minutes!")

            if not click.confirm("\n🎯 Ready to start the setup?", default=True):
                click.echo("\n👋 Setup cancelled. You can run 'locallab config' anytime to configure.")
                return
        else:
            # Existing installation - show current config and ask to reconfigure
            click.echo("\n" + "⚙️" * 25)
            click.echo("📋 LocalLab Configuration")
            click.echo("⚙️" * 25)

            # Show current configuration in a nice format
            click.echo("\n🔍 Current Configuration:")
            click.echo("   ─────────────────────")

            # Group settings logically
            model_id = current_config.get('model_id', 'Not set')
            port = current_config.get('port', 8000)
            click.echo(f"   🤖 Model: {model_id}")
            click.echo(f"   🌐 Port: {port}")

            # Optimization settings
            click.echo(f"\n   ⚡ Optimization:")
            quantization = current_config.get('enable_quantization', False)
            click.echo(f"      • Quantization: {'✅ Enabled' if quantization else '❌ Disabled'}")
            if quantization:
                quant_type = current_config.get('quantization_type', 'fp16')
                click.echo(f"        Type: {quant_type}")

            cpu_offload = current_config.get('enable_cpu_offloading', False)
            attention_slice = current_config.get('enable_attention_slicing', False)
            flash_attn = current_config.get('enable_flash_attention', False)
            better_trans = current_config.get('enable_bettertransformer', False)

            click.echo(f"      • CPU Offloading: {'✅ Enabled' if cpu_offload else '❌ Disabled'}")
            click.echo(f"      • Attention Slicing: {'✅ Enabled' if attention_slice else '❌ Disabled'}")
            click.echo(f"      • Flash Attention: {'✅ Enabled' if flash_attn else '❌ Disabled'}")
            click.echo(f"      • Better Transformer: {'✅ Enabled' if better_trans else '❌ Disabled'}")

            # Access settings
            click.echo(f"\n   🔐 Access:")
            hf_token = current_config.get('huggingface_token')
            ngrok_enabled = current_config.get('use_ngrok', False)
            click.echo(f"      • HuggingFace Token: {'✅ Set' if hf_token else '❌ Not set'}")
            click.echo(f"      • Public Access (Ngrok): {'✅ Enabled' if ngrok_enabled else '❌ Disabled'}")

            # Ask if user wants to reconfigure
            click.echo("\n" + "─" * 50)
            if not click.confirm("🔧 Would you like to reconfigure these settings?", default=True):
                click.echo("\n✅ Configuration unchanged.")
                click.echo("💡 You can run 'locallab start' to use your current settings.")
                return

        # Run the interactive configuration
        config = prompt_for_config(force_reconfigure=True)
        save_config(config)

        # Show success message
        click.echo("\n" + "🎉" * 25)
        click.echo("✅ Configuration Complete!")
        click.echo("🎉" * 25)
        click.echo("\n💡 Your settings have been saved successfully!")
        click.echo("🚀 You can now run 'locallab start' to launch your AI server.")

        if config.get('use_ngrok', False):
            click.echo("🌐 Ngrok is enabled - your server will be accessible publicly!")
        else:
            click.echo("🏠 Your server will be accessible locally only.")

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

    # Import and add the chat command
    from .cli.chat import chat
    locallab_cli.add_command(chat)

    # Import and add the models command group
    from .cli.models import models
    locallab_cli.add_command(models)

    # Use sys.argv to check if we're just showing help
    if len(sys.argv) <= 1 or sys.argv[1] == '--help' or sys.argv[1] == '-h':
        return locallab_cli()

    # For specific commands, we can optimize further
    if sys.argv[1] == 'info':
        return locallab_cli(['info'])
    elif sys.argv[1] == 'models':
        return locallab_cli()

    return locallab_cli()

if __name__ == "__main__":
    cli()