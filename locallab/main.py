import os
import logging
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from pydantic import BaseModel
import nest_asyncio
from pyngrok import ngrok
from typing import Optional, Dict, Any, List, Tuple
import time
import psutil
import torch

from .model_manager import ModelManager
from .config import (
    SERVER_HOST,
    SERVER_PORT,
    ENABLE_CORS,
    CORS_ORIGINS,
    DEFAULT_MODEL,
    NGROK_AUTH_TOKEN,
    ENABLE_COMPRESSION,
    QUANTIZATION_TYPE,
    ENABLE_FLASH_ATTENTION,
    ENABLE_ATTENTION_SLICING,
    ENABLE_CPU_OFFLOADING,
    ENABLE_BETTERTRANSFORMER
)

# Track server start time
start_time = time.time()

# Initialize FastAPI app
app = FastAPI(
    title="LocalLab",
    description="A lightweight AI inference server for running models locally or in Google Colab",
    version="0.1.9"
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("locallab")

# Initialize FastAPI cache
FastAPICache.init(InMemoryBackend())

# Initialize model manager
model_manager = ModelManager()

# Configure CORS
if ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Request counter
request_count = 0

# Pydantic models for request validation
class GenerateRequest(BaseModel):
    prompt: str
    model_id: Optional[str] = None
    stream: bool = False
    max_length: Optional[int] = None
    temperature: float = 0.7
    top_p: float = 0.9

class ModelLoadRequest(BaseModel):
    model_id: str

# Additional Pydantic models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model_id: Optional[str] = None
    stream: bool = False
    max_length: Optional[int] = None
    temperature: float = 0.7
    top_p: float = 0.9

class BatchGenerateRequest(BaseModel):
    prompts: list[str]
    model_id: Optional[str] = None
    max_length: Optional[int] = None
    temperature: float = 0.7
    top_p: float = 0.9

class SystemInfoResponse(BaseModel):
    cpu_usage: float
    memory_usage: float
    gpu_info: Optional[Dict[str, Any]]
    active_model: Optional[str]
    uptime: float
    request_count: int

# API endpoints
@app.post("/generate")
async def generate_text(request: GenerateRequest) -> Dict[str, Any]:
    """Generate text using the loaded model"""
    try:
        if request.model_id and request.model_id != model_manager.current_model:
            await model_manager.load_model(request.model_id)
        
        if request.stream:
            return StreamingResponse(
                model_manager.generate(
                    request.prompt,
                    stream=True,
                    max_length=request.max_length,
                    temperature=request.temperature,
                    top_p=request.top_p
                ),
                media_type="text/event-stream"
            )
        
        response = await model_manager.generate(
            request.prompt,
            max_length=request.max_length,
            temperature=request.temperature,
            top_p=request.top_p
        )
        return {"response": response}
    
    except Exception as e:
        logger.error(f"Generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/models/load")
async def load_model(request: ModelLoadRequest) -> Dict[str, Any]:
    """Load a specific model"""
    try:
        success = await model_manager.load_model(request.model_id)
        return {"status": "success" if success else "failed"}
    except Exception as e:
        logger.error(f"Model loading failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/current")
async def get_current_model() -> Dict[str, Any]:
    """Get information about the currently loaded model"""
    return model_manager.get_model_info()

@app.get("/models/available")
async def list_available_models() -> Dict[str, Any]:
    """List all available models in the registry"""
    from .config import MODEL_REGISTRY
    return {"models": MODEL_REGISTRY}

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Check the health status of the server"""
    return {"status": "healthy"}

# Additional endpoints
@app.post("/chat")
async def chat_completion(request: ChatRequest) -> Dict[str, Any]:
    """Chat completion endpoint similar to OpenAI's API"""
    try:
        if request.model_id and request.model_id != model_manager.current_model:
            await model_manager.load_model(request.model_id)
        
        # Format messages into a prompt
        formatted_prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages])
        
        if request.stream:
            return StreamingResponse(
                model_manager.generate(
                    formatted_prompt,
                    stream=True,
                    max_length=request.max_length,
                    temperature=request.temperature,
                    top_p=request.top_p
                ),
                media_type="text/event-stream"
            )
        
        response = await model_manager.generate(
            formatted_prompt,
            max_length=request.max_length,
            temperature=request.temperature,
            top_p=request.top_p
        )
        
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": response
                }
            }]
        }
    except Exception as e:
        logger.error(f"Chat completion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate/batch")
async def batch_generate(request: BatchGenerateRequest) -> Dict[str, Any]:
    """Generate text for multiple prompts in parallel"""
    try:
        if request.model_id and request.model_id != model_manager.current_model:
            await model_manager.load_model(request.model_id)
        
        responses = []
        for prompt in request.prompts:
            response = await model_manager.generate(
                prompt,
                max_length=request.max_length,
                temperature=request.temperature,
                top_p=request.top_p
            )
            responses.append(response)
        
        return {"responses": responses}
    except Exception as e:
        logger.error(f"Batch generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def get_gpu_memory() -> Optional[Tuple[int, int]]:
    """Get GPU memory info in MB"""
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return (info.total // 1024 // 1024, info.free // 1024 // 1024)
    except Exception as e:
        logger.debug(f"Failed to get GPU memory: {str(e)}")
        return None

@app.get("/system/info")
async def system_info() -> SystemInfoResponse:
    """Get detailed system information"""
    try:
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        gpu_info = None
        
        if torch.cuda.is_available():
            gpu_mem = get_gpu_memory()
            if gpu_mem:
                total_gpu, free_gpu = gpu_mem
                gpu_info = {
                    "total_memory": total_gpu,
                    "free_memory": free_gpu,
                    "used_memory": total_gpu - free_gpu,
                    "device": torch.cuda.get_device_name(0)
                }
        
        return SystemInfoResponse(
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            gpu_info=gpu_info,
            active_model=model_manager.current_model,
            uptime=time.time() - start_time,
            request_count=request_count
        )
    except Exception as e:
        logger.error(f"Failed to get system info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/models/unload")
async def unload_model() -> Dict[str, str]:
    """Unload the current model to free up resources"""
    try:
        if model_manager.model:
            del model_manager.model
            model_manager.model = None
            model_manager.current_model = None
            torch.cuda.empty_cache()
            return {"status": "Model unloaded successfully"}
        return {"status": "No model was loaded"}
    except Exception as e:
        logger.error(f"Failed to unload model: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.middleware("http")
async def count_requests(request: Request, call_next):
    """Middleware to count requests"""
    global request_count
    request_count += 1
    response = await call_next(request)
    return response

@app.on_event("startup")
async def startup_event():
    """Initialize the server on startup"""
    try:
        logger.info("Starting LocalLab server...")
        logger.info(f"Default model: {DEFAULT_MODEL}")
        
        # Load default model
        await model_manager.load_model(DEFAULT_MODEL)
        
        model_info = model_manager.get_model_info()
        logger.info(f"Model loaded successfully: {model_info['model_name']}")
        logger.info(f"Device: {model_info['device']}")
        logger.info(f"Memory used: {model_info['memory_used']}")
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

def get_system_resources() -> Dict[str, Any]:
    """Get system resource information"""
    resources = {
        'cpu_count': psutil.cpu_count(),
        'ram_total': psutil.virtual_memory().total / (1024 * 1024),
        'ram_available': psutil.virtual_memory().available / (1024 * 1024),
        'gpu_available': torch.cuda.is_available(),
        'gpu_info': []
    }
    
    if resources['gpu_available']:
        gpu_count = torch.cuda.device_count()
        for i in range(gpu_count):
            gpu_mem = get_gpu_memory()
            if gpu_mem:
                total_mem, _ = gpu_mem
                resources['gpu_info'].append({
                    'name': torch.cuda.get_device_name(i),
                    'total_memory': total_mem
                })
    
    return resources

def start_server(use_ngrok: bool = False):
    """Start the FastAPI server"""
    try:
        # Log system information
        resources = get_system_resources()
        logger.info("System Information:")
        logger.info(f"CPU Cores: {resources['cpu_count']}")
        logger.info(f"Total RAM: {resources['ram_total']:.2f} MB")
        logger.info(f"Available RAM: {resources['ram_available']:.2f} MB")
        
        if resources['gpu_available']:
            logger.info("GPU Information:")
            for i, gpu in enumerate(resources['gpu_info']):
                logger.info(f"GPU {i}: {gpu['name']}")
                logger.info(f"GPU Memory: {gpu['total_memory']:.2f} MB")
        else:
            logger.warning("No GPU detected, running in CPU mode")

        # Log configuration
        logger.info("\nConfiguration:")
        logger.info(f"Default Model: {DEFAULT_MODEL}")
        logger.info(f"Quantization: {QUANTIZATION_TYPE}")
        logger.info(f"Flash Attention: {ENABLE_FLASH_ATTENTION}")
        logger.info(f"Attention Slicing: {ENABLE_ATTENTION_SLICING}")
        logger.info(f"CPU Offloading: {ENABLE_CPU_OFFLOADING}")
        logger.info(f"BetterTransformer: {ENABLE_BETTERTRANSFORMER}")
        
        if use_ngrok:
            # Configure ngrok
            if not NGROK_AUTH_TOKEN:
                error_msg = (
                    "NGROK_AUTH_TOKEN not set. Please set it using:\n"
                    "import os\n"
                    "os.environ['NGROK_AUTH_TOKEN'] = 'your_token_here'\n"
                    "before calling start_server()"
                )
                logger.error(error_msg)
                raise ValueError("NGROK_AUTH_TOKEN is required when use_ngrok=True")
            
            logger.info("\nConfiguring ngrok...")
            ngrok.set_auth_token(NGROK_AUTH_TOKEN)
            public_url = ngrok.connect(SERVER_PORT).public_url
            logger.info(f"Public URL: {public_url}")
        
        # Enable asyncio event loop in Jupyter/Colab
        nest_asyncio.apply()
        
        # Log server settings
        logger.info("\nServer Settings:")
        logger.info(f"Host: {SERVER_HOST}")
        logger.info(f"Port: {SERVER_PORT}")
        logger.info(f"CORS Enabled: {ENABLE_CORS}")
        if ENABLE_CORS:
            logger.info(f"CORS Origins: {CORS_ORIGINS}")
        
        # Start the server
        logger.info("\nStarting server...")
        uvicorn.run(
            app,
            host=SERVER_HOST,
            port=SERVER_PORT,
            log_level="info"
        )
    
    except Exception as e:
        error_msg = f"Server startup failed: {str(e)}"
        logger.error(error_msg)
        logger.exception("Full traceback:")
        raise RuntimeError(error_msg) from e

if __name__ == "__main__":
    start_server()
