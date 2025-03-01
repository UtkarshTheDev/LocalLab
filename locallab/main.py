import os
import logging
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Tuple, Generator
import nest_asyncio
from pyngrok import ngrok, conf
import time
import psutil
import torch
from colorama import Fore, Style, init
init(autoreset=True)
import asyncio
import gc
import signal
import sys
import threading
from contextlib import contextmanager
import requests
import traceback
import socket

from . import __version__  # Import version from package
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
    ENABLE_BETTERTRANSFORMER,
    system_instructions,
    DEFAULT_SYSTEM_INSTRUCTIONS,
    MODEL_REGISTRY,
    DEFAULT_MAX_LENGTH,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    get_model_generation_params
)

# Track server start time
start_time = time.time()

# Initialize FastAPI app
app = FastAPI(
    title="LocalLab",
    description="A lightweight AI inference server for running models locally or in Google Colab",
    version=__version__
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
# Global flag to indicate if model is loading
model_loading = False

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
class SystemInstructionsRequest(BaseModel):
    instructions: str
    model_id: Optional[str] = None

class GenerateRequest(BaseModel):
    prompt: str
    model_id: Optional[str] = None
    stream: bool = False
    max_length: Optional[int] = None
    temperature: float = 0.7
    top_p: float = 0.9
    system_instructions: Optional[str] = None

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
@app.post("/system/instructions")
async def update_system_instructions(request: SystemInstructionsRequest) -> Dict[str, str]:
    """Update system instructions"""
    try:
        if request.model_id:
            system_instructions.set_model_instructions(request.model_id, request.instructions)
            return {"message": f"Updated system instructions for model {request.model_id}"}
        else:
            system_instructions.set_global_instructions(request.instructions)
            return {"message": "Updated global system instructions"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/instructions")
async def get_system_instructions(model_id: Optional[str] = None) -> Dict[str, Any]:
    """Get current system instructions"""
    return {
        "instructions": system_instructions.get_instructions(model_id),
        "model_id": model_id if model_id else "global"
    }

@app.post("/system/instructions/reset")
async def reset_system_instructions(model_id: Optional[str] = None) -> Dict[str, str]:
    """Reset system instructions to default"""
    system_instructions.reset_instructions(model_id)
    return {
        "message": f"Reset system instructions for {'model ' + model_id if model_id else 'all models'}"
    }

@app.post("/generate")
async def generate_text(request: GenerateRequest) -> Dict[str, Any]:
    """Generate text using the loaded model"""
    try:
        if request.model_id and request.model_id != model_manager.current_model:
            await model_manager.load_model(request.model_id)
        
        if request.stream:
            async def stream_wrapper():
                # Call generate() with stream=True; do not await it directly.
                async_gen = await model_manager.generate(
                    request.prompt,
                    stream=True,
                    max_length=request.max_length,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    system_instructions=request.system_instructions
                )
                async for token in async_gen:
                    yield token
            
            return StreamingResponse(stream_wrapper(), media_type="text/event-stream")
        
        response = await model_manager.generate(
            request.prompt,
            max_length=request.max_length,
            temperature=request.temperature,
            top_p=request.top_p,
            system_instructions=request.system_instructions
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
    return {"models": MODEL_REGISTRY}

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Check the health status of the server"""
    global model_loading
    status = "initializing" if model_loading else "healthy"
    return {"status": status}

@app.get("/startup-status")
async def startup_status() -> Dict[str, Any]:
    """Get detailed startup status including model loading progress"""
    global model_loading
    return {
        "server_ready": True,
        "model_loading": model_loading,
        "current_model": model_manager.current_model,
        "uptime": time.time() - start_time
    }

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
            async def stream_wrapper_chat():
                async_gen = await model_manager.generate(
                    formatted_prompt,
                    stream=True,
                    max_length=request.max_length,
                    temperature=request.temperature,
                    top_p=request.top_p
                )
                async for token in async_gen:
                    yield token
            
            return StreamingResponse(stream_wrapper_chat(), media_type="text/event-stream")
        
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
    """Initialize server on startup"""
    try:
        import sys
        # ASCII Art Banner
        banner = f"""
        {Fore.CYAN}
            ██╗      ██████╗  ██████╗ █████╗ ██╗     ██╗      █████╗ ██████╗ 
            ██║     ██╔═══██╗██╔════╝██╔══██╗██║     ██║     ██╔══██╗██╔══██╗
            ██║     ██║   ██║██║     ███████║██║     ██║     ███████║██████╔╝
            ██║     ██║   ██║██║     ██╔══██║██║     ██║     ██╔══██║██╔══██╗
            ███████╗╚██████╔╝╚██████╗██║  ██║███████╗███████╗██║  ██║██████╔╝
            ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝╚═════╝ 
        {Style.RESET_ALL}"""

        print(banner)
        sys.stdout.flush()
        logger.info(banner)
        sys.stdout.flush()
        logger.info(f"{Fore.GREEN}Version: {__version__}{Style.RESET_ALL}")
        logger.info(f"{Fore.GREEN}Status: Starting server...{Style.RESET_ALL}")
        logger.info("\n" + "═" * 80)
        sys.stdout.flush()# Active Model Details
        hf_model = os.getenv("HUGGINGFACE_MODEL", DEFAULT_MODEL)
        gen_params = get_model_generation_params()
        model_details = f"""
        {Fore.CYAN}┌────────────────────── Active Model Details ───────────────────────┐{Style.RESET_ALL}
        │
        │  📚 Model Information:
        │  • Name: {Fore.YELLOW}{hf_model}{Style.RESET_ALL}
        │  • Type: {Fore.YELLOW}{'Custom HuggingFace Model' if hf_model != DEFAULT_MODEL else 'Default Model'}{Style.RESET_ALL}
        │  • Status: {Fore.GREEN}Loading in background...{Style.RESET_ALL}
        │
        │  ⚙️ Model Settings:
        │  • Max Length: {Fore.YELLOW}{gen_params['max_length']}{Style.RESET_ALL}
        │  • Temperature: {Fore.YELLOW}{gen_params['temperature']}{Style.RESET_ALL}
        │  • Top P: {Fore.YELLOW}{gen_params['top_p']}{Style.RESET_ALL}
        │
        {Fore.CYAN}└───────────────────────────────────────────────────────────────┘{Style.RESET_ALL}
        """
        print(model_details)
        sys.stdout.flush()
        logger.info(model_details)
        sys.stdout.flush()

        # Model Configuration with better formatting
        model_config = f"""
        {Fore.CYAN}┌──────────────────────── Model Configuration ────────────────────────┐{Style.RESET_ALL}
        │
        │  🤖 Available Models:
        │  • Default: {Fore.YELLOW}{DEFAULT_MODEL}{Style.RESET_ALL}
        │  • Registry: {Fore.YELLOW}{', '.join(MODEL_REGISTRY.keys())}{Style.RESET_ALL}
        │
        │  🔧 Optimizations:
        │  • Quantization: {Fore.GREEN if ENABLE_COMPRESSION else Fore.RED}{QUANTIZATION_TYPE if ENABLE_COMPRESSION else 'Disabled'}{Style.RESET_ALL}
        │  • Flash Attention: {Fore.GREEN if ENABLE_FLASH_ATTENTION else Fore.RED}{str(ENABLE_FLASH_ATTENTION)}{Style.RESET_ALL}
        │  • Attention Slicing: {Fore.GREEN if ENABLE_ATTENTION_SLICING else Fore.RED}{str(ENABLE_ATTENTION_SLICING)}{Style.RESET_ALL}
        │  • CPU Offloading: {Fore.GREEN if ENABLE_CPU_OFFLOADING else Fore.RED}{str(ENABLE_CPU_OFFLOADING)}{Style.RESET_ALL}
        │
        {Fore.CYAN}└────────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}
        """
        print(model_config)
        sys.stdout.flush()
        logger.info(model_config)
        sys.stdout.flush()

        # Load model with progress indicator (start in background to not block startup)
        # This ensures the health endpoint can respond immediately
        logger.info(f"\n{Fore.YELLOW}⚡ Loading model: {hf_model} in background...{Style.RESET_ALL}")
        asyncio.create_task(load_model_in_background(hf_model))
        logger.info(f"{Fore.GREEN}Server is ready! Model will continue loading in background.{Style.RESET_ALL}\n")
        sys.stdout.flush()

        # System Resources with box drawing
        resources = f"""
        {Fore.CYAN}┌──────────────────────── System Resources ──────────────────────────┐{Style.RESET_ALL}
        │
        │  💻 Hardware:
        │  • CPU Cores: {Fore.YELLOW}{psutil.cpu_count()}{Style.RESET_ALL}
        │  • CPU Usage: {Fore.YELLOW}{psutil.cpu_percent()}%{Style.RESET_ALL}
        │  • Memory: {Fore.YELLOW}{psutil.virtual_memory().percent}% used{Style.RESET_ALL}
        │  • GPU: {Fore.YELLOW}{torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Not Available'}{Style.RESET_ALL}
        │
        {Fore.CYAN}└────────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}
        """
        print(resources)
        sys.stdout.flush()
        logger.info(resources)
        sys.stdout.flush()

        # API Documentation with better formatting
        api_docs = f"""
        {Fore.CYAN}┌────────────────────────── API Overview ─────────────────────────────┐{Style.RESET_ALL}
        │
        │  🔤 Text Generation:
        │   • POST /generate     - Generate text from prompt
        │   • POST /chat        - Interactive chat completion
        │   • POST /batch       - Batch text generation
        │
        │  🔄 Model Management:
        │   • GET  /models      - List available models
        │   • GET  /model       - Get current model info
        │   • POST /model/load  - Load a specific model
        │
        │  📊 System:
        │   • GET  /health      - Check server health
        │   • GET  /system      - Get system statistics
        │
        {Fore.CYAN}└────────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}
        """
        print(api_docs)
        sys.stdout.flush()
        logger.info(api_docs)
        sys.stdout.flush()

        # Quick Start Guide
        quickstart = f"""
        {Fore.CYAN}┌─────────────────────── Quick Start Guide ───────────────────────────┐{Style.RESET_ALL}
        │
        │  🚀 Example Usage:
        │
        │  1. Generate Text:
        │     curl -X POST "https://<NGROK_PUBLIC_URL>/generate" \\
        │     -H "Content-Type: application/json" \\
        │     -d '{{"prompt": "Once upon a time"}}'
        │
        │  2. Chat Completion:
        │     curl -X POST "https://<NGROK_PUBLIC_URL>/chat" \\
        │     -H "Content-Type: application/json" \\
        │     -d '{{"messages": [{{"role": "user", "content": "Hello!"}}]}}'
        │
        │  🔗 Replace <NGROK_PUBLIC_URL> with the public URL shown in the Server URLs section
        │
        {Fore.CYAN}└────────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}
        """
        print(quickstart)
        sys.stdout.flush()
        logger.info(quickstart)
        sys.stdout.flush()

        # Footer with social links and ASCII art
        footer = f"""
        {Fore.CYAN}
            ╔════════════════════════════════════════════════════════════════════╗
            ║                                                                  ║
            ║  {Fore.GREEN}LocalLab - Your Local AI Inference Server{Fore.CYAN}                    ║
            ║  {Fore.GREEN}Made with ❤️  by Utkarsh{Fore.CYAN}                             ║
            ║                                                                  ║
            ╚══════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

        {Fore.YELLOW}🔗 Connect & Contribute:{Style.RESET_ALL}
        • GitHub:   {Fore.CYAN}https://github.com/Developer-Utkarsh{Style.RESET_ALL}
        • Twitter:  {Fore.CYAN}https://twitter.com/UtkarshTheDev{Style.RESET_ALL}
        • LinkedIn: {Fore.CYAN}https://linkedin.com/in/utkarshthedev{Style.RESET_ALL}

        {Fore.GREEN}✨ Server is ready! Happy generating! 🚀{Style.RESET_ALL}
        """
        print(footer)
        sys.stdout.flush()
        logger.info(footer)
        sys.stdout.flush()

    except Exception as e:
        error_msg = f"""
        {Fore.RED}╔══════════════════════════════════════════════════════════════════╗{Style.RESET_ALL}
        {Fore.RED}║                              ERROR                                   ║{Style.RESET_ALL}
        {Fore.RED}╚══════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
    
        {str(e)}
        
        {Fore.YELLOW}💡 Need help? Check the documentation or open an issue on GitHub.{Style.RESET_ALL}
        """
        print(error_msg)
        sys.stdout.flush()
        logger.error(error_msg)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on server shutdown"""
    try:
        # Display goodbye message
        print("\n" + "=" * 80)
        print("👋 Shutting down LocalLab server...")
        
        # Clean up ngrok tunnels with improved error handling
        if ngrok.get_tunnels():
            for tunnel in ngrok.get_tunnels():
                try:
                    ngrok.disconnect(tunnel.public_url)
                except Exception as e:
                    if "ERR_NGROK_4018" in str(e):
                        logger.warning("Ngrok auth token not set or invalid. Skipping ngrok cleanup.")
                    else:
                        logger.warning("Failed to disconnect ngrok tunnel: " + str(e))
        
        # Clean up model resources
        if model_manager.model is not None:
            try:
                del model_manager.model
                del model_manager.tokenizer
                model_manager.model = None
                model_manager.tokenizer = None
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                gc.collect()
            except Exception as e:
                logger.warning("Failed to clean up model resources: " + str(e))
        
        print("✅ Cleanup completed successfully")
        print("=" * 80 + "\n")
        
    except Exception as e:
        logger.error("Error during cleanup: " + str(e))
        print("\n" + "=" * 80)
        print("❌ Error during cleanup: " + str(e))
        print("=" * 80 + "\n")

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

@contextmanager
def handle_shutdown():
    """Context manager for graceful shutdown"""
    try:
        yield
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Received keyboard interrupt, shutting down...{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
    finally:
        try:
            # Run shutdown cleanup
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.run_until_complete(shutdown_event())
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    print(f"\n{Fore.YELLOW}Received signal {signum}, shutting down server...{Style.RESET_ALL}")
    
    # Attempt to run shutdown tasks
    try:
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

def setup_ngrok(port: int = 8000) -> Optional[str]:
    """Simple ngrok tunnel setup without any validation or health checks"""
    ngrok_token = os.getenv("NGROK_AUTH_TOKEN")
    
    if not ngrok_token:
        logger.error("NGROK_AUTH_TOKEN environment variable not set")
        return None
        
    try:
        # Configure and start tunnel
        conf.get_default().auth_token = ngrok_token
        tunnel = ngrok.connect(port, "http")
        public_url = tunnel.public_url
        logger.info(f"Ngrok tunnel established: {public_url}")
        return public_url
    except Exception as e:
        logger.error(f"Failed to establish ngrok tunnel: {str(e)}")
        return None

# New utility functions added to fix undefined errors

def is_port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


async def load_model_in_background(model_id: str):
    global model_loading
    model_loading = True
    try:
        await model_manager.load_model(model_id)
    finally:
        model_loading = False


# Simplified start_server function that runs directly in the main process
def start_server(use_ngrok: bool = False, port=8000):
    """Start the LocalLab server directly in the main process"""
    
    # Display startup banner with INITIALIZING status
    startup_banner = f"""
{Fore.CYAN}
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  {Fore.GREEN}LocalLab Server v{__version__} - Starting Up{Fore.CYAN}                          ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.YELLOW}
 ██▓ ███▄    █  ██▓▄▄▄█████▓ ██▓ ▄▄▄       ██▓     ██▓▒███████▒ ██▓ ███▄    █   ▄████ 
▓██▒ ██ ▀█   █ ▓██▒▓  ██▒ ▓▒▓██▒▒████▄    ▓██▒    ▓██▒▒ ▒ ▒ ▄▀░▓██▒ ██ ▀█   █  ██▒ ▀█▒
▒██▒▓██  ▀█ ██▒▒██▒▒ ▓██░ ▒░▒██▒▒██  ▀█▄  ▒██░    ▒██▒░ ▒ ▄▀▒░ ▒██▒▓██  ▀█ ██▒▒██░▄▄▄░
░██░▓██▒  ▐▌██▒░██░░ ▓██▓ ░ ░██░░██▄▄▄▄██ ▒██░    ░██░  ▄▀▒   ░░██░▓██▒  ▐▌██▒░▓█  ██▓
░██░▒██░   ▓██░░██░  ▒██▒ ░ ░██░ ▓█   ▓██▒░██████▒░██░▒███████▒░██░▒██░   ▓██░░▒▓███▀▒
░▓  ░ ▒░   ▒ ▒ ░▓    ▒ ░░   ░▓   ▒▒   ▓▒█░░ ░░▓  ░░▓  ░▒▒ ▓░▒░▒░▓  ░ ▒░   ▒ ▒  ░▒   ▒ 
 ▒ ░░ ░░   ░ ▒░ ▒ ░    ░     ▒ ░  ▒   ▒▒ ░░ ░ ▒  ░ ▒ ░░░▒ ▒ ░ ▒ ▒ ░░ ░░   ░ ▒░  ░   ░ 
 ▒ ░   ░   ░ ░  ▒ ░  ░       ▒ ░  ░   ▒     ░ ░    ▒ ░░ ░ ░ ░ ░ ▒ ░   ░   ░ ░ ░ ░   ░ 
 ░           ░  ░            ░        ░  ░    ░  ░ ░    ░ ░     ░           ░       ░ 
                                                      ░                             
{Style.RESET_ALL}

{Fore.RED}⚠️  PLEASE WAIT! Server is initializing. DO NOT make API requests yet. ⚠️{Style.RESET_ALL}
{Fore.RED}⚠️  Wait for the RUNNING banner to appear before making requests.     ⚠️{Style.RESET_ALL}

{Fore.YELLOW}⏳ Initializing server components...{Style.RESET_ALL}
"""
    print(startup_banner, flush=True)
    
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
    
    # Create a function to display the Running banner when the server is ready
    def on_startup():
        running_banner = f"""
{Fore.GREEN}
██████╗ ██╗   ██╗███╗   ██╗███╗   ██╗██╗███╗   ██╗ ██████╗ 
██╔══██╗██║   ██║████╗  ██║████╗  ██║██║████╗  ██║██╔════╝ 
██████╔╝██║   ██║██╔██╗ ██║██╔██╗ ██║██║██╔██╗ ██║██║  ███╗
██╔══██╗██║   ██║██║╚██╗██║██║╚██╗██║██║██║╚██╗██║██║   ██║
██║  ██║╚██████╔╝██║ ╚████║██║ ╚████║██║██║ ╚████║╚██████╔╝
╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═══╝ ╚═════╝ 
{Style.RESET_ALL}

{Fore.GREEN}✅ SERVER IS READY! You can now make API requests.{Style.RESET_ALL}
{Fore.GREEN}✅ Model will continue loading in the background if not already loaded.{Style.RESET_ALL}

"""
        print(running_banner, flush=True)
        
        # Show connection details again for convenience
        endpoint_info = f"""
{Fore.CYAN}┌────────────────────────── Connection Details ────────────────────────┐{Style.RESET_ALL}
│
│  🖥️ Local URL: {Fore.GREEN}http://localhost:{port}{Style.RESET_ALL}
"""
        if public_url:
            endpoint_info += f"│  🌐 Public URL: {Fore.GREEN}{public_url}{Style.RESET_ALL}\n"
        endpoint_info += f"│\n{Fore.CYAN}└─────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n"
        print(endpoint_info, flush=True)
    
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
        # Clean up ngrok if server fails to start
        if use_ngrok and public_url:
            try:
                ngrok.disconnect(public_url)
            except:
                pass
        logger.error(f"Server startup failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    # Start the server with ngrok if requested via environment variable
    use_ngrok = os.getenv("ENABLE_NGROK", "false").lower() == "true"
    port = int(os.getenv("SERVER_PORT", "8000"))
    start_server(use_ngrok=use_ngrok, port=port)
