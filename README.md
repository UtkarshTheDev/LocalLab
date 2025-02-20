# 🚀 LocalLab

LocalLab is a powerful, lightweight AI inference server designed to run language models locally or in Google Colab. It provides an easy way to run and interact with various AI models while efficiently managing system resources.

## 📚 How to Use These Docs

### For New Users
1. Start here with the [Quick Start](#quick-start) guide below
2. Then check the [Getting Started](docs/README.md) guide for detailed setup
3. Follow the [Colab Deployment](docs/colab/README.md) guide if you want to use Google Colab

### For Developers
- [API Reference](docs/API.md) - REST API documentation
- [Python Client](docs/python/README.md) - Python SDK guide
- [Node.js Client](docs/nodejs/README.md) - Node.js SDK guide

## ⚡ Quick Start

### 1. Installation
```bash
pip install locallab
```

### 2. Local Deployment
```python
from locallab import start_server

# Start the server locally
start_server()
```

### 3. Google Colab Deployment
```python
!pip install locallab
from locallab import start_server

# Set your ngrok token (get one from ngrok.com)
import os
os.environ["NGROK_AUTH_TOKEN"] = "your_token_here"

# Start server with public access
start_server(use_ngrok=True)
```

## 🌟 Key Features

- 🤖 **Multiple Model Support**
  - Pre-configured models for different resource constraints
  - Dynamic loading of any Hugging Face model
  - Automatic fallback to lighter models

- 🔧 **Advanced Optimizations**
  - Multiple quantization options (FP16, INT8, INT4)
  - Attention slicing for memory efficiency
  - Flash Attention support

- 📊 **Resource Management**
  - Automatic RAM and VRAM monitoring
  - Dynamic model unloading
  - Resource-based model fallback

- 🚄 **Performance Features**
  - Response streaming
  - Request batching
  - Caching system

## 💡 Basic Usage Example

```python
from locallab.client import LocalLabClient

# Connect to the server
client = LocalLabClient("http://localhost:8000")

# Generate text
response = client.generate(
    prompt="Write a story about a robot learning to paint",
    temperature=0.8
)
print(response)
```

## 📚 Available Models

| Model ID            | Size | RAM Required | Description                          |
| ------------------- | ---- | ------------ | ------------------------------------ |
| tinyllama-1.1b      | 1.1B | 3GB          | Ultra lightweight model for testing  |
| qwen-0.5b           | 0.5B | 4GB          | Efficient general-purpose model      |
| phi-2               | 2.7B | 6GB          | Good performance for size            |
| stable-code-3b      | 3B   | 8GB          | Specialized for code generation      |
| mistral-7b-instruct | 7B   | 14GB         | Powerful instruction-following model |

## 🔍 Need Help?

- Check our [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- Visit our [GitHub Issues](https://github.com/Developer-Utkarsh/LocalLab/issues)
- Read the [FAQ](docs/colab/faq.md)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
