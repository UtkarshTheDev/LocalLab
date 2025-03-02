"""
Core FastAPI application setup for LocalLab
"""

import time
import logging
import asyncio
import gc
import torch
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import contextmanager
from colorama import Fore, Style

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
from ..logger.logger import log_request, log_model_loaded, log_model_unloaded, get_request_count
from ..model_manager import ModelManager
from ..config import (
    ENABLE_CORS,
    CORS_ORIGINS,
    DEFAULT_MODEL,
    ENABLE_COMPRESSION,
    QUANTIZATION_TYPE,
)

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


@app.on_event("startup")
async def startup_event():
    """Initialization tasks when the server starts"""
    logger.info("Starting LocalLab server...")
    
    # Initialize cache if available
    if FASTAPI_CACHE_AVAILABLE:
        FastAPICache.init(InMemoryBackend(), prefix="locallab-cache")
        logger.info("FastAPICache initialized")
    else:
        logger.warning("FastAPICache not available, caching disabled")
    
    # Check for model specified in environment variables (prioritize HUGGINGFACE_MODEL)
    model_to_load = os.environ.get("HUGGINGFACE_MODEL", DEFAULT_MODEL)
    
    # Log model configuration
    logger.info(f"Model configuration:")
    logger.info(f" - Model to load: {model_to_load}")
    logger.info(f" - Quantization: {'Enabled - ' + os.environ.get('LOCALLAB_QUANTIZATION_TYPE', QUANTIZATION_TYPE) if os.environ.get('LOCALLAB_ENABLE_QUANTIZATION', '').lower() == 'true' else 'Disabled'}")
    logger.info(f" - Attention slicing: {'Enabled' if os.environ.get('LOCALLAB_ENABLE_ATTENTION_SLICING', '').lower() == 'true' else 'Disabled'}")
    logger.info(f" - Flash attention: {'Enabled' if os.environ.get('LOCALLAB_ENABLE_FLASH_ATTENTION', '').lower() == 'true' else 'Disabled'}")
    logger.info(f" - Better transformer: {'Enabled' if os.environ.get('LOCALLAB_ENABLE_BETTERTRANSFORMER', '').lower() == 'true' else 'Disabled'}")
    
    # Start loading the model in background if specified
    if model_to_load:
        try:
            # This will run asynchronously without blocking server startup
            asyncio.create_task(load_model_in_background(model_to_load))
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
        torch.cuda.empty_cache()
        gc.collect()
        
        # Log model unloading
        if current_model:
            log_model_unloaded(current_model)
            
        logger.info("Model unloaded and memory freed")
    except Exception as e:
        logger.error(f"Error during shutdown cleanup: {str(e)}")
    
    logger.info(f"{Fore.GREEN}Server shutdown complete{Style.RESET_ALL}")


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
    logger.info(f"Loading model {model_id} in background...")
    start_time = time.time()
    
    try:
        # Wait for the model to load
        await model_manager.load_model(model_id)
        
        # Calculate load time
        load_time = time.time() - start_time
        
        # We don't need to call log_model_loaded here since it's already done in the model_manager
        logger.info(f"{Fore.GREEN}Model {model_id} loaded successfully in {load_time:.2f} seconds!{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"Failed to load model {model_id}: {str(e)}") 