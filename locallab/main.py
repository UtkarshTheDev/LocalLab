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
import asyncio
import gc
import signal
import sys
from contextlib import contextmanager
import requests
import multiprocessing

# New: Define a LogQueueWriter to redirect writes to a multiprocessing.Queue
class LogQueueWriter:
    def __init__(self, queue):
        self.queue = queue
    def write(self, msg):
        if msg.strip() != "":
            self.queue.put(msg)
    def flush(self):
        pass

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
    version="0.3.4"
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
        
        # In Google Colab, explicitly print the banner to ensure visibility
        print(banner)
        sys.stdout.flush()
        logger.info(banner)
        sys.stdout.flush()
        logger.info(f"{Fore.GREEN}Version: {__version__}{Style.RESET_ALL}")
        logger.info(f"{Fore.GREEN}Status: Starting server...{Style.RESET_ALL}")
        logger.info("\n" + "═" * 80)
        sys.stdout.flush()

        # Active Model Details
        hf_model = os.getenv("HUGGINGFACE_MODEL", DEFAULT_MODEL)
        gen_params = get_model_generation_params()
        model_details = f"""
{Fore.CYAN}┌────────────────────── Active Model Details ───────────────────────┐{Style.RESET_ALL}
│
│  📚 Model Information:
│  • Name: {Fore.YELLOW}{hf_model}{Style.RESET_ALL}
│  • Type: {Fore.YELLOW}{'Custom HuggingFace Model' if hf_model != DEFAULT_MODEL else 'Default Model'}{Style.RESET_ALL}
│  • Status: {Fore.GREEN}Loading...{Style.RESET_ALL}
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

        # Load model with progress indicator
        logger.info(f"\n{Fore.YELLOW}⚡ Loading model: {hf_model}{Style.RESET_ALL}")
        await model_manager.load_model(hf_model)
        logger.info(f"{Fore.GREEN}✓ Model loaded successfully!{Style.RESET_ALL}\n")
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
    ║  {Fore.GREEN}Made with ❤️  by Utkarsh Tiwari{Fore.CYAN}                             ║
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
    """Handle system signals"""
    print(f"\n{Fore.YELLOW}Received signal {signum}, shutting down...{Style.RESET_ALL}")
    # Don't call sys.exit directly in Colab
    if "COLAB_GPU" in os.environ:
        # Graceful shutdown for Colab
        asyncio.get_event_loop().stop()
    else:
        sys.exit(0)

def setup_ngrok(port: int = 8000, max_retries: int = 3) -> Optional[str]:
    """Setup ngrok tunnel with retry logic and validation"""
    ngrok_token = os.getenv("NGROK_AUTH_TOKEN")
    
    if not ngrok_token:
        logger.error("NGROK_AUTH_TOKEN environment variable not set")
        return None
        
    # Validate token format
    if not isinstance(ngrok_token, str) or len(ngrok_token) < 30:
        logger.error("Invalid NGROK_AUTH_TOKEN format")
        return None
    
    for attempt in range(max_retries):
        try:
            # Configure ngrok
            conf.get_default().auth_token = ngrok_token
            conf.get_default().region = "us"  # or other region as needed
            
            # Kill any existing ngrok processes
            ngrok.kill()
            time.sleep(2)  # Added delay to allow previous tunnels to close
            
            # Start new tunnel
            tunnel = ngrok.connect(port, "http")
            
            # Verify tunnel
            public_url = tunnel.public_url
            if not public_url.startswith("http"):
                raise ValueError("Invalid tunnel URL")
                
            # Test connection
            response = requests.get(f"{public_url}/health", timeout=5)
            if response.status_code != 200:
                raise ConnectionError("Tunnel health check failed")
                
            logger.info(f"Ngrok tunnel established: {public_url}")
            return public_url
            
        except Exception as e:
            logger.warning(f"Ngrok connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            logger.error("Failed to establish ngrok tunnel after all retries")
            raise

# Modify run_server_proc to accept a log_queue and redirect stdout/stderr

def run_server_proc(log_queue):
    import logging
    # Create a new logger for the spawned process to avoid inheriting fork-context locks
    logger = logging.getLogger("locallab.spawn")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # Redirect stdout and stderr to the log queue
    log_writer = LogQueueWriter(log_queue)
    sys.stdout = log_writer
    sys.stderr = log_writer

    # Attach a logging handler to send log messages to the queue
    handler = logging.StreamHandler(log_writer)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

    try:
        if "COLAB_GPU" in os.environ:
            import nest_asyncio
            nest_asyncio.apply()
            # Set reload to False in COLAB
            config = uvicorn.Config(app, host="0.0.0.0", port=8000, reload=False)
            server = uvicorn.Server(config)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(server.serve())
        else:
            # Disable reload and force single worker to avoid multiple processes
            uvicorn.run(app, host="127.0.0.1", port=8000, reload=False, workers=1)
    except Exception as e:
        logger.error(f"Server startup failed: {str(e)}")
        raise

# Modify start_server to accept a log_queue parameter and pass it to the child process

def start_server(use_ngrok: bool = False, log_queue=None):
    import time
    import requests
    
    # If no log_queue provided, create one (though normally parent supplies it)
    if log_queue is None:
        ctx = multiprocessing.get_context("spawn")
        log_queue = ctx.Queue()
    
    # Start the server in a separate process using spawn context with module-level run_server_proc
    ctx = multiprocessing.get_context("spawn")
    p = ctx.Process(target=run_server_proc, args=(log_queue,))
    p.start()
    
    # Wait until the /health endpoint returns 200 or timeout
    timeout = 30
    start_time_loop = time.time()
    health_url = "http://127.0.0.1:8000/health"
    server_ready = False
    while time.time() - start_time_loop < timeout:
        try:
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                server_ready = True
                break
        except Exception:
            pass
        time.sleep(1)
    
    if not server_ready:
        raise Exception("Server did not become healthy in time.")
    
    if use_ngrok:
        public_url = setup_ngrok(port=8000)
        ngrok_section = f"\n{Fore.CYAN}┌────────────────────────── Ngrok Tunnel Details ─────────────────────────────┐{Style.RESET_ALL}\n│\n│  🚀 Ngrok Public URL: {Fore.GREEN}{public_url}{Style.RESET_ALL}\n│\n{Fore.CYAN}└──────────────────────────────────────────────────────────────────────────────┘{Style.RESET_ALL}\n"
        logger.info(ngrok_section)
        print(ngrok_section)
    
    # Wait indefinitely until a KeyboardInterrupt is received
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down server...")
        p.terminate()
        p.join()

# Define a log listener function in the parent to print messages from the log queue

def log_listener(queue):
    while True:
        try:
            msg = queue.get()
            if msg is None:
                break
            print(msg, end='')
        except Exception as e:
            pass

if __name__ == "__main__":
    import multiprocessing
    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError as e:
        logger.warning("multiprocessing start method already set: " + str(e))
    
    import threading
    # Create a log queue using the spawn context and start the listener thread
    ctx = multiprocessing.get_context("spawn")
    log_queue = ctx.Queue()
    listener_thread = threading.Thread(target=log_listener, args=(log_queue,), daemon=True)
    listener_thread.start()
    
    start_server(use_ngrok=True, log_queue=log_queue)
