# Model Management Guide

## Available Models

### Core Models

| Model ID   | Size | RAM  | Best For       |
| ---------- | ---- | ---- | -------------- |
| phi-2      | 2.7B | 6GB  | General use    |
| qwen-0.5b  | 0.5B | 4GB  | Testing        |
| mistral-7b | 7B   | 14GB | Advanced tasks |

### Loading Models

```python
# Via environment
os.environ["HUGGINGFACE_MODEL"] = "microsoft/phi-2"

# Via client
await client.load_model("microsoft/phi-2")
```

## Model Configuration

### Generation Parameters

```python
os.environ["LOCALLAB_MODEL_TEMPERATURE"] = "0.7"
os.environ["LOCALLAB_MODEL_MAX_LENGTH"] = "2048"
os.environ["LOCALLAB_MODEL_TOP_P"] = "0.9"
```

## Resource Management

### Memory Optimization

```python
os.environ["LOCALLAB_ENABLE_QUANTIZATION"] = "true"
os.environ["LOCALLAB_QUANTIZATION_TYPE"] = "int8"
```

## Remote Access with Ngrok

LocalLab includes built-in ngrok integration, allowing you to access your models from anywhere in the world. This is especially useful for:

- Accessing your models from mobile devices
- Sharing your models with teammates
- Using your models while away from your computer
- Accessing models running on Google Colab from anywhere

### Enabling Remote Access

```bash
# Start server with ngrok enabled
locallab start --use-ngrok

# You'll see output like:
# 🚀 Ngrok Public URL: https://abc123.ngrok.app
```

### Connecting from Anywhere

```python
from locallab_client import SyncLocalLabClient

# Connect to your ngrok URL from any device
client = SyncLocalLabClient("https://abc123.ngrok.app")

# Use the client as normal
response = client.generate("Hello from my phone!")
print(response)

# Always close when done
client.close()
```

### Ngrok Authentication

For longer sessions, set up an ngrok auth token:

```bash
# Configure ngrok auth token
locallab config

# Or set directly when starting
locallab start --use-ngrok --ngrok-auth-token YOUR_TOKEN
```

Get your free ngrok token at [ngrok.com/signup](https://ngrok.com/signup)

## Related Documentation

- [Performance Guide](./performance.md)
- [API Reference](../guides/API.md)
- [Google Colab Guide](../colab/README.md)
