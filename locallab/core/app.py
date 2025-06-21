"""
Core FastAPI application setup for LocalLab
"""

import time
import logging
import asyncio
import gc
import torch
import os
from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import contextmanager
from colorama import Fore, Style
from typing import Optional, Dict, Any, List

# Try to import FastAPICache, but don't fail if not available
try:
    from fastapi_cache import FastAPICache
    from fastapi_cache.backends.inmemory import InMemoryBackend
    FASTAPI_CACHE_AVAILABLE = True
except ImportError:
    FASTAPI_CACHE_AVAILABLE = False
    # Create dummy FastAPICache to avoid errors
    class DummyFastAPICache:
        @staticmethod
        def init(backend, **kwargs):
            pass
    FastAPICache = DummyFastAPICache

from .. import __version__
from ..logger import get_logger
from ..logger.logger import log_request, log_model_loaded, log_model_unloaded, get_request_count, set_server_status
from ..model_manager import ModelManager
from ..config import (
    ENABLE_CORS,
    CORS_ORIGINS,
    DEFAULT_MODEL,
    ENABLE_COMPRESSION,
    QUANTIZATION_TYPE,
    SERVER_PORT,
    DEFAULT_MAX_LENGTH,
    get_env_var,
)
from ..cli.config import get_config_value
from ..utils.system import get_system_resources

# Get the logger
logger = get_logger("locallab.app")

# Track server start time
start_time = time.time()

# Initialize FastAPI app
app = FastAPI(
    title="LocalLab",
    description="A lightweight AI inference server for running models locally or in Google Colab",
    version=__version__
)

# Configure CORS
if ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Initialize model manager (imported by routes)
model_manager = ModelManager()

# Import all routes (after app initialization to avoid circular imports)
from ..routes.models import router as models_router
from ..routes.generate import router as generate_router
from ..routes.system import router as system_router

# Include all routers
app.include_router(models_router)
app.include_router(generate_router)
app.include_router(system_router)

# Startup event triggered flag
startup_event_triggered = False

# Model loading status flag
model_loading_in_progress = False

# Application startup event to ensure banners are displayed
@app.on_event("startup")
async def startup_event():
    """Event that is triggered when the application starts up"""
    global startup_event_triggered

    # Only log once
    if startup_event_triggered:
        return

    logger.info("FastAPI application startup event triggered")
    startup_event_triggered = True

    # Wait a short time to ensure logs are processed
    await asyncio.sleep(0.5)

    # Log a special message that our callback handler will detect
    root_logger = logging.getLogger()
    root_logger.info("Application startup complete - banner display trigger")

    logger.info(f"{Fore.CYAN}Starting LocalLab server...{Style.RESET_ALL}")

    # Get HuggingFace token and set it in environment if available
    from ..config import get_hf_token
    hf_token = get_hf_token(interactive=False)
    if hf_token:
        os.environ["HUGGINGFACE_TOKEN"] = hf_token
        logger.info(f"{Fore.GREEN}HuggingFace token loaded from configuration{Style.RESET_ALL}")
    else:
        logger.warning(f"{Fore.YELLOW}No HuggingFace token found. Some models may not be accessible.{Style.RESET_ALL}")

    # Check if ngrok should be enabled
    from ..cli.config import get_config_value
    use_ngrok = get_config_value("use_ngrok", False)
    if use_ngrok:
        from ..utils.networking import setup_ngrok
        port = int(os.environ.get("LOCALLAB_PORT", SERVER_PORT))  # Use SERVER_PORT as fallback

        # Handle ngrok setup synchronously since it's not async
        ngrok_url = setup_ngrok(port)
        if ngrok_url:
            logger.info(f"{Fore.GREEN}Ngrok tunnel established successfully{Style.RESET_ALL}")
        else:
            logger.warning("Failed to establish ngrok tunnel. Server will run locally only.")

    # Initialize cache if available
    if FASTAPI_CACHE_AVAILABLE:
        FastAPICache.init(InMemoryBackend(), prefix="locallab-cache")
        logger.info("FastAPICache initialized")
    else:
        logger.warning("FastAPICache not available, caching disabled")

    # Check for model specified in environment variables or CLI config
    model_to_load = (
        os.environ.get("HUGGINGFACE_MODEL") or
        get_config_value("model_id") or
        DEFAULT_MODEL
    )

    # Log model configuration
    logger.info(f"{Fore.CYAN}Model configuration:{Style.RESET_ALL}")
    logger.info(f" - Model to load: {model_to_load}")
    logger.info(f" - Quantization: {'Enabled - ' + os.environ.get('LOCALLAB_QUANTIZATION_TYPE', QUANTIZATION_TYPE) if os.environ.get('LOCALLAB_ENABLE_QUANTIZATION', '').lower() == 'true' else 'Disabled'}")
    logger.info(f" - Attention slicing: {'Enabled' if os.environ.get('LOCALLAB_ENABLE_ATTENTION_SLICING', '').lower() == 'true' else 'Disabled'}")
    logger.info(f" - Flash attention: {'Enabled' if os.environ.get('LOCALLAB_ENABLE_FLASH_ATTENTION', '').lower() == 'true' else 'Disabled'}")
    logger.info(f" - Better transformer: {'Enabled' if os.environ.get('LOCALLAB_ENABLE_BETTERTRANSFORMER', '').lower() == 'true' else 'Disabled'}")

    # Start loading the model in background if specified
    if model_to_load:
        try:
            # This will run asynchronously without blocking server startup
            # But we'll set a flag to indicate model loading is in progress
            asyncio.create_task(load_model_in_background(model_to_load))
            # Set a global flag to indicate model is loading
            global model_loading_in_progress
            model_loading_in_progress = True
        except Exception as e:
            logger.error(f"Error starting model loading task: {str(e)}")
    else:
        logger.warning("No model specified to load on startup. Use the /models/load endpoint to load a model.")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup tasks when the server shuts down"""
    logger.info(f"{Fore.YELLOW}Shutting down server...{Style.RESET_ALL}")

    # Unload model to free GPU memory
    try:
        # Get current model ID before unloading
        current_model = model_manager.current_model

        # Unload the model
        if hasattr(model_manager, 'unload_model'):
            model_manager.unload_model()
        else:
            # Fallback if unload_model method doesn't exist
            model_manager.model = None
            model_manager.current_model = None

        # Clean up memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()

        # Log model unloading
        if current_model:
            log_model_unloaded(current_model)

        logger.info("Model unloaded and memory freed")
    except Exception as e:
        logger.error(f"Error during shutdown cleanup: {str(e)}")

    # Clean up any pending tasks
    try:
        # Get all tasks except the current one
        current_task = asyncio.current_task()
        tasks = [t for t in asyncio.all_tasks()
                if t is not current_task and not t.done()]

        if tasks:
            logger.debug(f"Cancelling {len(tasks)} remaining tasks")

            # Cancel all tasks
            for task in tasks:
                task.cancel()

            # Wait for tasks to complete with a timeout
            try:
                # Use wait_for with a timeout to avoid hanging
                await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=3.0)
                logger.debug("All tasks cancelled successfully")
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for tasks to cancel")
            except asyncio.CancelledError:
                # This is expected during shutdown
                logger.debug("Task cancellation was itself cancelled - this is normal during shutdown")
            except Exception as e:
                logger.warning(f"Error during task cancellation: {str(e)}")
    except Exception as e:
        logger.warning(f"Error cleaning up tasks: {str(e)}")

    # Set server status to stopped
    set_server_status("stopped")

    logger.info(f"{Fore.GREEN}Server shutdown complete{Style.RESET_ALL}")

    # Only force exit if this is a true shutdown initiated by SIGINT/SIGTERM
    # Check if this was triggered by an actual signal
    if hasattr(shutdown_event, 'force_exit_required') and shutdown_event.force_exit_required:
        import threading
        def force_exit():
            import time
            import os
            time.sleep(3)  # Give a little time for clean shutdown

            # Check if we need to force exit
            if hasattr(shutdown_event, 'force_exit_required') and shutdown_event.force_exit_required:
                logger.info("Forcing exit after shutdown to ensure clean termination")
                try:
                    # Reset the flag to avoid multiple exit attempts
                    shutdown_event.force_exit_required = False
                    os._exit(0)  # Direct exit instead of sending another signal
                except:
                    pass

        # Start a daemon thread that will force exit if needed
        exit_thread = threading.Thread(target=force_exit, daemon=True)
        exit_thread.start()

# Initialize the flag (default to not forcing exit)
shutdown_event.force_exit_required = False

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Middleware to track request processing time"""
    start_time = time.time()

    # Extract path and some basic params for logging
    path = request.url.path
    method = request.method
    client = request.client.host if request.client else "unknown"

    # Skip detailed logging for health check endpoints to reduce noise
    is_health_check = path.endswith("/health") or path.endswith("/startup-status")

    if not is_health_check:
        log_request(f"{method} {path}", {"client": client})

    # Process the request
    response = await call_next(request)

    # Calculate processing time
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"

    # Add request stats to response headers
    response.headers["X-Request-Count"] = str(get_request_count())

    # Log slow requests for performance monitoring (if not a health check)
    if process_time > 1.0 and not is_health_check:
        logger.warning(f"Slow request: {method} {path} took {process_time:.2f}s")

    return response


async def load_model_in_background(model_id: str):
    """Load the model asynchronously in the background"""
    global model_loading_in_progress
    logger.info(f"Loading model {model_id} in background...")
    start_time = time.time()

    try:
        # Ensure HF token is set before loading model
        from ..config import get_hf_token
        hf_token = get_hf_token(interactive=False)
        if hf_token:
            os.environ["HUGGINGFACE_TOKEN"] = hf_token
            logger.debug("Using HuggingFace token from configuration")
        else:
            logger.warning("No HuggingFace token found. Some models may not be accessible.")

        # Wait for the model to load
        await model_manager.load_model(model_id)

        # Calculate load time
        load_time = time.time() - start_time

        # We don't need to call log_model_loaded here since it's already done in the model_manager
        logger.info(f"{Fore.GREEN}Model {model_id} loaded successfully in {load_time:.2f} seconds!{Style.RESET_ALL}")

        # Now that model is loaded, set server status to running
        from ..logger.logger import set_server_status
        set_server_status("running")
        logger.info("Server status changed to: running")

        # Mark model loading as complete
        model_loading_in_progress = False

        # Display the running banner now that model is loaded
        try:
            from ..ui.banners import print_running_banner
            from .. import __version__
            print_running_banner(__version__)
        except Exception as banner_e:
            logger.warning(f"Could not display running banner: {banner_e}")

    except Exception as e:
        logger.error(f"Failed to load model {model_id}: {str(e)}")
        if "401 Client Error: Unauthorized" in str(e):
            logger.error("This appears to be an authentication error. Please ensure your HuggingFace token is set correctly.")
            logger.info("You can set your token using: locallab config")

        # Even if model loading fails, mark it as complete and set server to running
        # so the server can still be used for other operations
        model_loading_in_progress = False
        from ..logger.logger import set_server_status
        set_server_status("running")
        logger.info("Server status changed to: running (model loading failed)")

        # Display the running banner even if model loading failed
        try:
            from ..ui.banners import print_running_banner
            from .. import __version__
            print_running_banner(__version__)
        except Exception as banner_e:
            logger.warning(f"Could not display running banner: {banner_e}")