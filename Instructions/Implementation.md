# LocalLab Implementation Guide

This guide details every step required to build the full LocalLab project—from creating the Python server package to developing client packages in Python and Node.js. Follow the checklists and detailed instructions to set up, code, test, and deploy the project.

---

## Table of Contents

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Project Setup](#project-setup)
- [Server Package Implementation](#server-package-implementation)
  - [Creating the Python Server Package](#creating-the-python-server-package)
  - [Server File Components](#server-file-components)
- [Python Client Package Implementation](#python-client-package-implementation)
- [Node.js Client Package Implementation](#nodejs-client-package-implementation)
- [Testing and Deployment](#testing-and-deployment)
- [Troubleshooting](#troubleshooting)
- [Conclusion](#conclusion)

---

## Introduction

LocalLab is a lightweight AI inference server built to run advanced AI models on low-spec hardware or in Google Colab. It leverages FastAPI, Uvicorn, and Hugging Face’s Transformers to manage model loading, inference, and resource monitoring. This project supports easy integration through client libraries in Python and Node.js.

---

## Prerequisites

Before starting, ensure you have installed:

- [ ] **Python 3.8+**
- [ ] **pip** (Python package installer)
- [ ] **Virtual Environment** support (venv or virtualenv)
- [ ] **Node.js and npm** (for Node.js client development)
- [ ] **ngrok account** (optional for exposing your server)
- [ ] **Git**

---

## Project Setup

Follow these steps to create the project repository:

- [ ] **Initialize a Git Repository:**

  ```bash
  git init
  ```

- [ ] **Create the Directory Structure:**

  ```
  locallab/
  ├── server/
  │   ├── __init__.py
  │   ├── main.py           # Entry point; FastAPI server and ngrok integration.
  │   ├── model_manager.py  # Handles loading, managing, and inference of AI models.
  │   ├── config.py         # Configuration variables (e.g., model registry, ngrok token).
  │   ├── logger.py         # Custom logging setup.
  │   └── utils.py          # Utility functions (e.g., GPU memory check).
  ├── client/
  │   ├── python_client/
  │   │   ├── __init__.py
  │   │   └── client.py     # Python SDK for API interactions.
  │   └── node_client/
  │       ├── package.json  # Node.js client configuration.
  │       └── index.js      # Node.js client for API interactions.
  ├── tests/                # Unit and integration tests.
  ├── docs/                 # Documentation files (API.md, DEPLOYMENT.md, etc.).
  ├── requirements.txt      # Python packages dependencies.
  ├── README.md             # Project overview.
  └── Implementation.md     # This implementation guide.
  ```

- [ ] **Create and Activate a Virtual Environment:**

  ```bash
  python -m venv env
  source env/bin/activate   # macOS/Linux
  env\Scripts\activate      # Windows
  ```

- [ ] **Install Dependencies and Create `requirements.txt`:**

  ```bash
  pip install fastapi uvicorn python-multipart transformers accelerate pyngrok nest_asyncio psutil nvidia-ml-py3 fastapi-cache2 colorama
  pip freeze > requirements.txt
  ```

---

## Server Package Implementation

The server package is the backbone of LocalLab. It is built using FastAPI and integrates key components for AI model management, logging, and deployment.

### Creating the Python Server Package

Follow these steps:

- [ ] **Set up the Server Directory:**  
      Create all files in the `server/` folder as part of your Python package.

- [ ] **Install Server Dependencies:**  
      Ensure dependencies are installed (see installation above).

### Server File Components

#### 1. `server/main.py`

This file initializes FastAPI, configures middleware, sets up the ngrok tunnel, and defines API endpoints.

python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
import uvicorn
import nest_asyncio
from pyngrok import ngrok
import asyncio
Import custom modules
from model_manager import ModelManager
from config import DEFAULT_MODEL, NGROK_AUTH_TOKEN
app = FastAPI(title="AI Model Server", version="2.0")
Set up CORS middleware
app.add_middleware(
CORSMiddleware,
allow_origins=[""],
allow_methods=[""],
allow_headers=[""],
)
Initialize the model manager
model_manager = ModelManager()
API Endpoints
@app.post("/generate")
async def generate_text(prompt: str, stream: bool = False):
try:
if stream:
return StreamingResponse(
model_manager.generate(prompt, stream=True),
media_type="text/event-stream"
)
response = await model_manager.generate(prompt)
return {"response": response}
except Exception as e:
raise HTTPException(status_code=500, detail=str(e))
@app.get("/models")
async def list_models():
return {
"available_models": list(model_manager.MODEL_REGISTRY.keys()),
"current_model": model_manager.model_config
}
@app.get("/system_health")
async def system_health():
return {"status": "running"}
@app.on_event("startup")
async def startup_event():
FastAPICache.init(InMemoryBackend())
await model_manager.load_model(DEFAULT_MODEL)
if name == "main":

# Set up ngrok if running in a development environment

ngrok.set_auth_token(NGROK_AUTH_TOKEN)
public_url = ngrok.connect(8000).public_url
print(f" Public URL: {public_url}")
nest_asyncio.apply()
uvicorn.run(app, host="0.0.0.0", port=8000)

#### 2. `server/model_manager.py`

Handles AI model loading, checking GPU memory, inference, and fallback logic.

python
import subprocess
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from fastapi import HTTPException
Define the model registry
MODEL_REGISTRY = {
"qwen-0.5b": {
"name": "Qwen/Qwen1.5-0.5B-Chat",
"vram": 2000,
"max_length": 1024,
"fallback": None
},
"llama2-7b": {
"name": "meta-llama/Llama-2-7B-Chat",
"vram": 8000,
"max_length": 512,
"fallback": "qwen-0.5b"
}
}
class ModelManager:
def init(self):
self.MODEL_REGISTRY = MODEL_REGISTRY
self.current_model = None
self.tokenizer = None
self.pipeline = None
self.model_config = MODEL_REGISTRY["qwen-0.5b"]
async def get_gpu_memory(self):
try:
output = subprocess.check_output(
['nvidia-smi', '--query-gpu=memory.free', '--format=csv,nounits,noheader']
)
return int(output.decode().strip())
except Exception:
return 0
async def load_model(self, model_id: str):
if model_id not in self.MODEL_REGISTRY:
raise HTTPException(status_code=400, detail="Model not found in registry")
config = self.MODEL_REGISTRY[model_id]
free_mem = await self.get_gpu_memory()
if free_mem < config["vram"]:
raise HTTPException(
status_code=400,
detail=f"Insufficient VRAM. Required {config['vram']} MB, available {free_mem} MB."
)
try:
if self.pipeline:
del self.pipeline
torch.cuda.empty_cache()
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
{"role": "system", "content": "You are a helpful AI assistant."},
{"role": "user", "content": prompt}
]
try:
inputs = self.tokenizer(" ".join([m["content"] for m in messages]), return_tensors="pt").to("cuda")
if stream:
return self.stream_generation(inputs)
outputs = self.pipeline.generate(
inputs,
max_new_tokens=self.model_config["max_length"],
temperature=0.7,
top_p=0.9,
do_sample=True
)
return self.tokenizer.decode(outputs[0]len(inputs[0]):], skip_special_tokens=True)
except Exception as e:
if self.model_config["fallback"]:
await self.load_model(self.model_config["fallback"])
return await self.generate(prompt, stream)
raise HTTPException(status_code=500, detail=str(e))
def stream_generation(self, inputs):
for in range(self.model_config["max_length"]):
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

#### 3. Additional Server Files

- **`server/config.py`**  
  Define key configuration variables.

  ```python
  DEFAULT_MODEL = "qwen-0.5b"
  NGROK_AUTH_TOKEN = "YOUR_NGROK_TOKEN"  # Replace with your actual ngrok token
  ```

- **`server/logger.py`**  
  Set up custom logging with color output.

  ```python
  import logging
  from colorama import Fore, Style

  def setup_logger():
      logger = logging.getLogger("LocalLab")
      logger.setLevel(logging.INFO)
      ch = logging.StreamHandler()
      formatter = logging.Formatter(f'{Fore.GREEN}%(asctime)s{Style.RESET_ALL} - %(message)s')
      ch.setFormatter(formatter)
      logger.addHandler(ch)
      return logger

  logger = setup_logger()
  ```

- **`server/utils.py`**  
  Utility functions (for example, GPU memory check).

  ```python
  import subprocess

  def check_gpu_memory():
      try:
          output = subprocess.check_output(
              ['nvidia-smi', '--query-gpu=memory.free', '--format=csv,nounits,noheader']
          )
          return int(output.decode().strip())
      except Exception:
          return 0
  ```

---

## Python Client Package Implementation

The Python client simplifies API interactions with LocalLab.

- [ ] **Create `client/python_client/client.py`:**

  ```python
  import requests

  class LocalLabClient:
      def __init__(self, base_url: str):
          self.base_url = base_url

      def generate(self, prompt: str, model: str = None, stream: bool = False):
          payload = {
              "prompt": prompt,
              "model": model,
              "stream": stream
          }
          response = requests.post(f"{self.base_url}/generate", json=payload)
          return response.json()

      def get_models(self):
          response = requests.get(f"{self.base_url}/models")
          return response.json()

      def set_model(self, model_id: str):
          payload = {"model_id": model_id}
          response = requests.post(f"{self.base_url}/set_model", json=payload)
          return response.json()

      def system_health(self):
          response = requests.get(f"{self.base_url}/system_health")
          return response.json()

  # Example usage:
  if __name__ == "__main__":
      client = LocalLabClient("http://localhost:8000")
      print(client.get_models())
      print(client.generate("Hello, world!"))
  ```

- [ ] **Create `client/python_client/__init__.py`:**  
      This file can be empty or used for initialization.

---

## Node.js Client Package Implementation

The Node.js client offers a JavaScript-based interface to interact with the LocalLab API.

- [ ] **Initialize the Node.js Package:**

  ```bash
  cd client/node_client
  npm init -y
  ```

- [ ] **Create/Edit `client/node_client/package.json`:**

  ```json
  {
    "name": "locallab-node-client",
    "version": "1.0.0",
    "description": "Node.js client for LocalLab API",
    "main": "index.js",
    "scripts": {
      "start": "node index.js"
    },
    "dependencies": {
      "axios": "^0.27.2"
    }
  }
  ```

- [ ] **Create `client/node_client/index.js`:**

  ```javascript
  const axios = require("axios");

  class LocalLabClient {
    constructor(baseUrl) {
      this.baseUrl = baseUrl;
    }

    async generate(prompt, model = null, stream = false) {
      try {
        const response = await axios.post(`${this.baseUrl}/generate`, {
          prompt: prompt,
          model: model,
          stream: stream,
        });
        return response.data;
      } catch (error) {
        console.error("Error generating text:", error.response.data);
      }
    }

    async getModels() {
      try {
        const response = await axios.get(`${this.baseUrl}/models`);
        return response.data;
      } catch (error) {
        console.error("Error fetching models:", error.response.data);
      }
    }

    async setModel(model_id) {
      try {
        const response = await axios.post(`${this.baseUrl}/set_model`, {
          model_id,
        });
        return response.data;
      } catch (error) {
        console.error("Error setting model:", error.response.data);
      }
    }
  }

  module.exports = LocalLabClient;

  // Example usage:
  (async () => {
    const client = new LocalLabClient("http://localhost:8000");
    console.log(await client.getModels());
    console.log(await client.generate("Hello from Node.js!"));
  })();
  ```

---

## Testing and Deployment

- [ ] **API Testing:**
  - Use the interactive Swagger UI at `http://localhost:8000/docs`.
  - Test endpoints via Postman using the provided Python and Node.js client examples.
- [ ] **Running the Server Locally:**

  ```bash
  python -m server.main
  ```

- [ ] **Deploy on Google Colab:**

  - Copy the contents from `Instructions/InitialCode.md` into a Colab notebook cell.
  - Run the cell to install dependencies, start the FastAPI server, and automatically set up an ngrok tunnel.

- [ ] **Running Automated Tests:**
  - Write tests in the `tests/` folder using a framework such as pytest.
  - Run tests via:
    ```bash
    pytest --maxfail=1 --disable-warnings -q
    ```

---

## Troubleshooting

- [ ] **GPU Memory Issues:**  
      Verify available GPU memory using functions from `server/utils.py` if model loading fails.

- [ ] **ngrok Tunnel Problems:**  
      Ensure the correct ngrok token is set in `server/config.py` and that your account is active.

- [ ] **API Errors:**  
      Review server logs (configured in `server/logger.py`) and consult `docs/TROUBLESHOOTING.md` for common issues.

---

## Conclusion

By following this comprehensive guide, you will have:

- Created a robust Python server package using FastAPI.
- Developed easy-to-use client packages for both Python and Node.js.
- Documented and tested the entire system for smooth deployment and scaling.

Happy building with LocalLab—your lightweight AI inference platform!
