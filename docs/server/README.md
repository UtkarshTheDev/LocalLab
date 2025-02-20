# LocalLab Server Setup Guide

A comprehensive guide for setting up and deploying the LocalLab server in various environments.

## 📚 Table of Contents

1. [Local Deployment](#local-deployment)
2. [Google Colab Deployment](#google-colab-deployment)
3. [Configuration Options](#configuration-options)
4. [Security Considerations](#security-considerations)
5. [Performance Tuning](#performance-tuning)

## Local Deployment

### Prerequisites

- Python 3.8+
- CUDA-compatible GPU (optional)
- 8GB+ RAM (16GB+ recommended)
- 50GB+ free disk space

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install LocalLab
pip install locallab torch transformers accelerate
```

### Basic Server Start

```python
from locallab import start_server

# Start with default settings
start_server()
```

### Advanced Server Start

```python
from locallab import start_server

# Start with custom configuration
start_server(
    host="0.0.0.0",
    port=8000,
    workers=4,
    enable_cache=True,
    enable_compression=True,
    log_level="INFO"
)
```

## Google Colab Deployment

### Setup

1. **Install Dependencies**

   ```python
   !pip install locallab torch transformers accelerate
   ```

2. **Configure Ngrok**

   ```python
   import os
   os.environ["NGROK_AUTH_TOKEN"] = "your_token_here"
   ```

3. **Start Server**

   ```python
   from locallab import start_server
   import threading

   def run_server():
       start_server(use_ngrok=True)

   server_thread = threading.Thread(target=run_server)
   server_thread.daemon = True
   server_thread.start()
   ```

### Persistent Sessions

```python
# Add to your notebook to prevent disconnects
from IPython.display import Javascript
display(Javascript('''
function ClickConnect(){
    console.log("Auto-connecting...");
    document.querySelector("colab-connect-button").click()
}
setInterval(ClickConnect, 60000)
'''))
```

## Configuration Options

### Environment Variables

```bash
# Server Configuration
export LOCALLAB_HOST="0.0.0.0"
export LOCALLAB_PORT="8000"
export LOCALLAB_WORKERS="4"
export LOCALLAB_LOG_LEVEL="INFO"

# Model Configuration
export LOCALLAB_DEFAULT_MODEL="qwen-0.5b"
export LOCALLAB_PRELOAD_MODELS="false"
export LOCALLAB_UNLOAD_TIMEOUT="1800"

# Resource Management
export LOCALLAB_MIN_FREE_MEMORY="2000"
export LOCALLAB_MAX_BATCH_SIZE="4"
export LOCALLAB_REQUEST_TIMEOUT="30"

# Performance
export LOCALLAB_ENABLE_CACHE="true"
export LOCALLAB_CACHE_TTL="3600"
export LOCALLAB_ENABLE_COMPRESSION="true"

# Security
export LOCALLAB_ENABLE_CORS="true"
export LOCALLAB_CORS_ORIGINS="*"
export LOCALLAB_RATE_LIMIT="60"
```

### Configuration File

Create `config.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  log_level: "INFO"

model:
  default: "qwen-0.5b"
  preload: false
  unload_timeout: 1800

resources:
  min_free_memory: 2000
  max_batch_size: 4
  request_timeout: 30

performance:
  enable_cache: true
  cache_ttl: 3600
  enable_compression: true

security:
  enable_cors: true
  cors_origins: ["*"]
  rate_limit: 60
```

## Security Considerations

### 1. Access Control

```python
from locallab import start_server
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

def api_key_auth(api_key: str = Security(api_key_header)):
    if api_key != os.getenv("LOCALLAB_API_KEY"):
        raise HTTPException(status_code=403)
    return api_key

start_server(
    auth_handler=api_key_auth,
    enable_cors=True,
    cors_origins=["https://yourdomain.com"]
)
```

### 2. Rate Limiting

```python
from locallab import start_server
from fastapi import Request
from fastapi.middleware.throttling import ThrottlingMiddleware

start_server(
    rate_limit=60,  # requests per minute
    burst_size=10,
    enable_request_validation=True
)
```

### 3. Input Validation

```python
from pydantic import BaseModel, Field

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    max_length: int = Field(100, ge=1, le=2048)
```

## Performance Tuning

### 1. Resource Optimization

```python
start_server(
    enable_attention_slicing=True,
    enable_cpu_offloading=True,
    enable_flash_attention=True,
    enable_bettertransformer=True
)
```

### 2. Caching

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

redis = aioredis.from_url("redis://localhost")
FastAPICache.init(RedisBackend(redis), prefix="locallab-cache")
```

### 3. Load Balancing

```python
# Using Nginx configuration
http {
    upstream locallab {
        server 127.0.0.1:8000;
        server 127.0.0.1:8001;
        server 127.0.0.1:8002;
    }

    server {
        listen 80;
        location / {
            proxy_pass http://locallab;
        }
    }
}
```

## Monitoring

### 1. System Metrics

```python
from locallab.monitoring import setup_monitoring

setup_monitoring(
    enable_prometheus=True,
    enable_logging=True,
    log_file="server.log"
)
```

### 2. Health Checks

```python
from locallab.health import HealthCheck

health = HealthCheck()
health.add_check(check_database_connection)
health.add_check(check_gpu_availability)

start_server(health_check=health)
```

### 3. Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler()
    ]
)
```

## Deployment Examples

### 1. Docker

```dockerfile
FROM python:3.8-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "-m", "locallab"]
```

### 2. Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: locallab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: locallab
  template:
    metadata:
      labels:
        app: locallab
    spec:
      containers:
        - name: locallab
          image: locallab:latest
          ports:
            - containerPort: 8000
          resources:
            limits:
              nvidia.com/gpu: 1
```

## Troubleshooting

### Common Issues

1. **Memory Issues**

   ```python
   import torch
   torch.cuda.empty_cache()
   ```

2. **GPU Problems**

   ```python
   import torch
   if not torch.cuda.is_available():
       print("CUDA not available")
   else:
       print(f"Using GPU: {torch.cuda.get_device_name(0)}")
   ```

3. **Connection Issues**
   ```python
   import requests
   try:
       requests.get("http://localhost:8000/health")
   except requests.exceptions.ConnectionError:
       print("Server not running")
   ```

## 📚 Additional Resources

- [Advanced Configuration](./advanced-config.md)
- [Deployment Guide](./deployment.md)
- [Security Best Practices](./security.md)
- [Performance Optimization](./performance.md)
