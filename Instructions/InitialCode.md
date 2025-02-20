# Step 1: Install required packages
!pip install fastapi uvicorn python-multipart transformers accelerate pyngrok nest_asyncio psutil nvidia-ml-py3 fastapi-cache2 colorama

# Step 2: Import necessary modules
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
from pyngrok import ngrok
import torch
import asyncio
import psutil
import subprocess
from typing import Dict, List, Optional
import time
import numpy as np
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache

# Step 3: Configure application
app = FastAPI(title="AI Model Server", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Model Configuration ==========
MODEL_REGISTRY = {
    "qwen-0.5b": {
        "name": "Qwen/Qwen1.5-0.5B-Chat",
        "vram": 2000,
        "parameters": "0.5B",
        "max_length": 1024,
        "fallback": None
    },
    "llama2-7b": {
        "name": "meta-llama/Llama-2-7B-Chat",
        "vram": 8000,
        "parameters": "7B",
        "max_length": 512,
        "fallback": "qwen-0.5b"
    }
}

DEFAULT_MODEL = "qwen-0.5b"
SYSTEM_PROMPT = "You are a helpful AI assistant. Respond concisely and clearly."

# ========== Model Manager Class ==========
class ModelManager:
    def __init__(self):
        self.current_model = None
        self.tokenizer = None
        self.pipeline = None
        self.model_config = MODEL_REGISTRY[DEFAULT_MODEL]

    async def get_gpu_memory(self):
        try:
            output = subprocess.check_output(
                ['nvidia-smi', '--query-gpu=memory.free', '--format=csv,nounits,noheader']
            )
            return int(output.decode().strip())
        except:
            return 0

    async def load_model(self, model_id: str):
        if model_id not in MODEL_REGISTRY:
            raise HTTPException(status_code=400, detail="Model not found in registry")

        config = MODEL_REGISTRY[model_id]
        free_mem = await self.get_gpu_memory()

        if free_mem < config["vram"]:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient VRAM. Required: {config['vram']}MB, Available: {free_mem}MB"
            )

        try:
            # Unload previous model
            if self.pipeline:
                del self.pipeline
                torch.cuda.empty_cache()

            # Load new model
            self.tokenizer = AutoTokenizer.from_pretrained(config["name"])
            model = AutoModelForCausalLM.from_pretrained(
                config["name"],
                torch_dtype=torch.float16,
                device_map="auto"
            )

            self.pipeline = model
            self.model_config = config
            return True
        except Exception as e:
            if config["fallback"]:
                return await self.load_model(config["fallback"])
            raise HTTPException(status_code=500, detail=f"Model loading failed: {str(e)}")

    async def generate(self, prompt: str, stream: bool = False):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        try:
            inputs = self.tokenizer.apply_chat_template(
                messages,
                return_tensors="pt"
            ).to("cuda")

            if stream:
                return self._stream_generation(inputs)

            outputs = self.pipeline.generate(
                inputs,
                max_new_tokens=self.model_config["max_length"],
                temperature=0.7,
                top_p=0.9,
                do_sample=True
            )

            return self.tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)

        except Exception as e:
            if self.model_config["fallback"]:
                await self.load_model(self.model_config["fallback"])
                return await self.generate(prompt, stream)
            raise HTTPException(status_code=500, detail=str(e))

    def _stream_generation(self, inputs):
        for _ in range(self.model_config["max_length"]):
            with torch.no_grad():
                outputs = self.pipeline.generate(
                    inputs,
                    max_new_tokens=1,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True
                )

            new_token = self.tokenizer.decode(outputs[0][-1:], skip_special_tokens=True)
            inputs = outputs
            yield new_token

# Initialize model manager
model_manager = ModelManager()

# ========== API Endpoints ==========
class GenerationRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    stream: Optional[bool] = False

@app.post("/generate")
@cache(expire=300)
async def generate_text(request: GenerationRequest):
    try:
        if request.model and request.model != model_manager.model_config["name"]:
            await model_manager.load_model(request.model)

        if request.stream:
            return StreamingResponse(
                model_manager.generate(request.prompt, stream=True),
                media_type="text/event-stream"
            )

        response = await model_manager.generate(request.prompt)
        return {"response": response}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/models")
async def list_models():
    return {
        "available_models": list(MODEL_REGISTRY.keys()),
        "current_model": model_manager.model_config,
        "system_resources": {
            "vram": await model_manager.get_gpu_memory(),
            "ram": psutil.virtual_memory().available
        }
    }

@app.post("/set_model")
async def set_model(model_id: str):
    try:
        success = await model_manager.load_model(model_id)
        return {"status": "success", "current_model": model_manager.model_config}
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )

@app.get("/system_health")
async def system_health():
    return {
        "gpu_memory": await model_manager.get_gpu_memory(),
        "ram_usage": psutil.virtual_memory().percent,
        "cpu_usage": psutil.cpu_percent(),
        "active_model": model_manager.model_config
    }

@app.get("/suggest_model")
async def suggest_model(task: str = "general"):
    suggestions = {
        "general": "qwen-0.5b",
        "creative": "llama2-7b",
        "technical": "qwen-0.5b"
    }
    return {
        "suggestion": suggestions.get(task, "qwen-0.5b"),
        "reason": "Best performance for task type with available resources"
    }

# ========== Server Setup ==========
@app.on_event("startup")
async def startup():
    FastAPICache.init(InMemoryBackend())
    await model_manager.load_model(DEFAULT_MODEL)

if __name__ == "__main__":
    # Start ngrok tunnel
    ngrok.set_auth_token("YOUR_NGROK_TOKEN")
    public_url = ngrok.connect(8000).public_url
    print(f" * Public URL: {public_url}")

    # Start server
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)

    import nest_asyncio
    nest_asyncio.apply()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.serve())
