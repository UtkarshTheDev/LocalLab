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
        os._exit(0)
        
    threading.Thread(target=delayed_exit, daemon=True).start()


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
    
    async def start(self):
        self.started = True
        logger.info("Started SimpleTCPServer as fallback")
        
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
        self.started = False
        self._running = False
        
        if self._serve_task:
            self._serve_task.cancel()
            try:
                await self._serve_task
            except asyncio.CancelledError:
                pass
            self._serve_task = None
        
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        
        logger.info("Shutdown SimpleTCPServer")
    
    async def serve(self, sock=None):
        self.started = True
        try:
            while self.started:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in SimpleTCPServer.serve: {str(e)}")
            logger.debug(f"SimpleTCPServer.serve error details: {traceback.format_exc()}")
        finally:
            self.started = False


class ServerWithCallback(uvicorn.Server):
    def install_signal_handlers(self):
        def handle_exit(signum, frame):
            self.should_exit = True
            logger.debug(f"Signal {signum} received in ServerWithCallback, setting should_exit=True")
        
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
    
    async def startup(self, sockets=None):
        if self.should_exit:
            return
        
        if sockets is not None:
            try:
                await super().startup(sockets=sockets)
                logger.info("Using uvicorn's built-in Server implementation")
            except Exception as e:
                logger.error(f"Error during server startup: {str(e)}")
                logger.debug(f"Server startup error details: {traceback.format_exc()}")
                self.servers = []
                for socket in sockets:
                    server = SimpleTCPServer(config=self.config)
                    server.server = self
                    await server.start()
                    self.servers.append(server)
        else:
            try:
                await super().startup(sockets=None)
                logger.info("Using uvicorn's built-in Server implementation")
            except Exception as e:
                logger.error(f"Error during server startup: {str(e)}")
                logger.debug(f"Server startup error details: {traceback.format_exc()}")
                server = SimpleTCPServer(config=self.config)
                server.server = self
                await server.start()
                self.servers = [server]
        
        if self.lifespan is not None:
            try:
                await self.lifespan.startup()
            except Exception as e:
                logger.error(f"Error during lifespan startup: {str(e)}")
                logger.debug(f"Lifespan startup error details: {traceback.format_exc()}")
                self.lifespan = NoopLifespan(self.config.app)
                logger.warning("Replaced failed lifespan with NoopLifespan")
    
    async def main_loop(self):
        try:
            while not self.should_exit:
                await asyncio.sleep(0.05)
                
                if self.should_exit:
                    logger.debug("Shutdown signal detected in main_loop")
                    break
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            logger.debug(f"Main loop error details: {traceback.format_exc()}")
            self.should_exit = True
        
        logger.debug("Exiting main_loop")
    
    async def shutdown(self, sockets=None):
        logger.debug("Starting server shutdown process")
        
        if self.servers:
            for server in self.servers:
                try:
                    server.close()
                    await server.wait_closed()
                    logger.debug("Server closed successfully")
                except Exception as e:
                    logger.error(f"Error closing server: {str(e)}")
                    logger.debug(f"Server close error details: {traceback.format_exc()}")
        
        if self.lifespan is not None:
            try:
                await self.lifespan.shutdown()
                logger.debug("Lifespan shutdown completed")
            except Exception as e:
                logger.error(f"Error during lifespan shutdown: {str(e)}")
                logger.debug(f"Lifespan shutdown error details: {traceback.format_exc()}")
        
        self.servers = []
        self.lifespan = None
        
        logger.debug("Server shutdown process completed")
    
    async def serve(self, sockets=None):
        self.config.setup_event_loop()
        
        self.lifespan = None
        
        self._initialize_lifespan()
        
        try:
            await self.startup(sockets=sockets)
            
            if hasattr(self, 'on_startup_callback') and callable(self.on_startup_callback):
                self.on_startup_callback()
            
            await self.main_loop()
            await self.shutdown()
        except Exception as e:
            logger.error(f"Error during server operation: {str(e)}")
            logger.debug(f"Server error details: {traceback.format_exc()}")
            raise
            
    def _initialize_lifespan(self):
        try:
            from uvicorn.lifespan.on import LifespanOn
            
            try:
                self.lifespan = LifespanOn(config=self.config)
                logger.info("Using LifespanOn from uvicorn.lifespan.on with config parameter")
                return
            except TypeError:
                pass
                
            try:
                self.lifespan = LifespanOn(self.config.app)
                logger.info("Using LifespanOn from uvicorn.lifespan.on with app parameter")
                return
            except TypeError:
                pass
                
            try:
                lifespan_on = self.config.lifespan_on if hasattr(self.config, "lifespan_on") else "auto"
                self.lifespan = LifespanOn(self.config.app, lifespan_on)
                logger.info("Using LifespanOn from uvicorn.lifespan.on with app and lifespan_on parameters")
                return
            except TypeError:
                pass
                
        except (ImportError, AttributeError):
            logger.debug("Could not import LifespanOn from uvicorn.lifespan.on")
            
        try:
            from uvicorn.lifespan.lifespan import Lifespan
            
            try:
                self.lifespan = Lifespan(self.config.app)
                logger.info("Using Lifespan from uvicorn.lifespan.lifespan with app parameter")
                return
            except TypeError:
                pass
                
            try:
                self.lifespan = Lifespan(self.config.app, "auto")
                logger.info("Using Lifespan from uvicorn.lifespan.lifespan with app and lifespan_on parameters")
                return
            except TypeError:
                pass
                
            try:
                self.lifespan = Lifespan(self.config.app, "auto", logger)
                logger.info("Using Lifespan from uvicorn.lifespan.lifespan with app, lifespan_on, and logger parameters")
                return
            except TypeError:
                pass
                
        except (ImportError, AttributeError):
            logger.debug("Could not import Lifespan from uvicorn.lifespan.lifespan")
            
        try:
            from uvicorn.lifespan import Lifespan
            
            try:
                self.lifespan = Lifespan(self.config.app)
                logger.info("Using Lifespan from uvicorn.lifespan with app parameter")
                return
            except TypeError:
                pass
                
            try:
                self.lifespan = Lifespan(self.config.app, "auto")
                logger.info("Using Lifespan from uvicorn.lifespan with app and lifespan_on parameters")
                return
            except TypeError:
                pass
                
            try:
                self.lifespan = Lifespan(self.config.app, "auto", logger)
                logger.info("Using Lifespan from uvicorn.lifespan with app, lifespan_on, and logger parameters")
                return
            except TypeError:
                pass
                
        except (ImportError, AttributeError):
            logger.debug("Could not import Lifespan from uvicorn.lifespan")
            
        try:
            from uvicorn.lifespan.state import LifespanState
            
            try:
                self.lifespan = LifespanState(self.config.app)
                logger.info("Using LifespanState from uvicorn.lifespan.state with app parameter")
                return
            except TypeError:
                pass
                
            try:
                self.lifespan = LifespanState(self.config.app, logger=logger)
                logger.info("Using LifespanState from uvicorn.lifespan.state with app and logger parameters")
                return
            except TypeError:
                pass
                
        except (ImportError, AttributeError):
            logger.debug("Could not import LifespanState from uvicorn.lifespan.state")
            
        self.lifespan = NoopLifespan(self.config.app)
        logger.warning("Using NoopLifespan - server may not handle startup/shutdown events properly")


def start_server(use_ngrok: bool = None, port: int = None, ngrok_auth_token: Optional[str] = None):
    
    try:
        set_server_status("initializing")
        
        print_initializing_banner(__version__)
        
        from .cli.config import load_config, set_config_value
        
        try:
            saved_config = load_config()
        except Exception as e:
            logger.warning(f"Error loading configuration: {str(e)}. Using defaults.")
            saved_config = {}
        
        for key, value in saved_config.items():
            if key == "model_id":
                os.environ["HUGGINGFACE_MODEL"] = str(value)
            elif key == "ngrok_auth_token":
                os.environ["NGROK_AUTH_TOKEN"] = str(value)
            elif key == "huggingface_token":
                os.environ["HUGGINGFACE_TOKEN"] = str(value)
            elif key in ["enable_quantization", "enable_attention_slicing", "enable_flash_attention", 
                        "enable_better_transformer", "enable_cpu_offloading", "enable_cache", 
                        "enable_file_logging"]:
                env_key = f"LOCALLAB_{key.upper()}"
                os.environ[env_key] = str(value).lower()
            elif key in ["quantization_type", "model_timeout", "cache_ttl", "log_level", "log_file"]:
                env_key = f"LOCALLAB_{key.upper()}"
                os.environ[env_key] = str(value)
        
        config = prompt_for_config(use_ngrok, port, ngrok_auth_token)
        
        save_config(config)
        
        use_ngrok = config.get("use_ngrok", use_ngrok)
        port = config.get("port", port or 8000)
        ngrok_auth_token = config.get("ngrok_auth_token", ngrok_auth_token)
        
        if is_port_in_use(port):
            logger.warning(f"Port {port} is already in use. Trying to find another port...")
            for p in range(port+1, port+100):
                if not is_port_in_use(p):
                    port = p
                    logger.info(f"Using alternative port: {port}")
                    break
            else:
                raise RuntimeError(f"Could not find an available port in range {port}-{port+100}")
        
        public_url = None
        if use_ngrok:
            os.environ["LOCALLAB_USE_NGROK"] = "true"
            
            if not ngrok_auth_token and not os.environ.get("NGROK_AUTH_TOKEN"):
                logger.error("Ngrok auth token is required for public access. Please set it in the configuration.")
                logger.info("You can get a free token from: https://dashboard.ngrok.com/get-started/your-authtoken")
                raise ValueError("Ngrok auth token is required for public access")
                
            logger.info(f"{Fore.CYAN}Setting up ngrok tunnel to port {port}...{Style.RESET_ALL}")
            public_url = setup_ngrok(port=port, auth_token=ngrok_auth_token or os.environ.get("NGROK_AUTH_TOKEN"))
            if public_url:
                os.environ["LOCALLAB_NGROK_URL"] = public_url
                
                ngrok_section = f"\n{Fore.CYAN}┌────────────────────────── Ngrok Tunnel Details ─────────────────────────────┐{Style.RESET_ALL}\n│\n│  🚀 Ngrok Public URL: {Fore.GREEN}{public_url}{Style.RESET_ALL}\n│\n{Fore.CYAN}└──────────────────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n"
                print(ngrok_section)
            
        # Start the server logic goes here...
        
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        raise
