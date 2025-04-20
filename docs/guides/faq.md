# Frequently Asked Questions (FAQ)

## General Questions

### Q: What is LocalLab?

LocalLab is a lightweight AI inference server that lets you run language models locally or in Google Colab. It's designed to make it easy to use powerful AI models without requiring extensive setup or cloud resources.

### Q: Which models can I use?

You can use:

- Any model from HuggingFace
- Pre-configured models like phi-2, qwen-0.5b
- Custom models (with proper configuration)

### Q: What are the minimum requirements?

- Local: 4GB RAM, Python 3.8+
- Colab: Free tier is sufficient for most models
- GPU: Optional but recommended for larger models

## Setup & Installation

### Q: How do I get started?

```python
# Install package
pip install locallab

# Start server
from locallab import start_server
start_server()  # For local use
# OR
start_server(ngrok=True)  # For Google Colab
```

### Q: How do I use it in Google Colab?

1. Install LocalLab
2. Set up ngrok token
3. Start server with ngrok=True
4. Use the public URL for client connections

Example:

```python
import os
os.environ["NGROK_AUTH_TOKEN"] = "your_token_here"

from locallab import start_server
start_server(ngrok=True)  # Will show public URL in logs

# Connect using the ngrok URL
from locallab_client import LocalLabClient
client = LocalLabClient("https://xxxx-xx-xx-xxx-xx.ngrok-free.app")
```

## Common Issues

### Q: Getting "Out of Memory" errors?

Try these solutions:

1. Enable quantization:
   ```python
   os.environ["LOCALLAB_ENABLE_QUANTIZATION"] = "true"
   ```
2. Use a smaller model:
   ```python
   os.environ["HUGGINGFACE_MODEL"] = "microsoft/phi-2"
   ```
3. Enable memory optimizations:
   ```python
   os.environ["LOCALLAB_ENABLE_ATTENTION_SLICING"] = "true"
   ```

### Q: Server connection issues?

Check:

1. For local: Use "http://localhost:8000"
2. For Colab: Use the ngrok URL from server logs
3. Verify server is running
4. Check for firewall issues

## Model Management

### Q: How do I change models?

```python
# Via environment variable
os.environ["HUGGINGFACE_MODEL"] = "microsoft/phi-2"

# Or via client
await client.load_model("microsoft/phi-2")
```

### Q: How do I adjust model parameters?

```python
os.environ["LOCALLAB_MODEL_TEMPERATURE"] = "0.7"
os.environ["LOCALLAB_MODEL_MAX_LENGTH"] = "2048"
os.environ["LOCALLAB_MODEL_TOP_P"] = "0.9"
```

## Performance

### Q: How can I improve performance?

1. Enable optimizations:
   ```python
   os.environ["LOCALLAB_ENABLE_QUANTIZATION"] = "true"
   os.environ["LOCALLAB_ENABLE_FLASH_ATTENTION"] = "true"
   ```
2. Use appropriate batch sizes
3. Monitor system resources

### Q: How do I monitor resource usage?

```python
info = await client.get_system_info()
print(f"CPU Usage: {info.cpu_usage}%")
print(f"Memory: {info.memory_usage}%")
```

## More Help

- Check our [Getting Started Guide](./getting-started.md)
- Visit [Troubleshooting](./TROUBLESHOOTING.md)
- Read [API Documentation](./API.md)
