# LocalLab Advanced Guide

## 📚 Table of Contents

1. [Advanced Features](#advanced-features)
2. [Performance Optimization](#performance-optimization)
3. [Model Management](#model-management)
4. [System Configuration](#system-configuration)
5. [CLI Configuration](#cli-configuration)
6. [Best Practices](#best-practices)

## Advanced Features

### Custom Model Loading

**Using CLI (New!)**

```bash
# Load a custom model with the CLI
locallab start --model meta-llama/Llama-2-7b-chat-hf
```

**Using Environment Variables**

```python
import os
from locallab import start_server

# Load any HuggingFace model
os.environ["HUGGINGFACE_MODEL"] = "meta-llama/Llama-2-7b-chat-hf"

# Configure model settings
os.environ["LOCALLAB_MODEL_TEMPERATURE"] = "0.8"
os.environ["LOCALLAB_MODEL_MAX_LENGTH"] = "4096"
os.environ["LOCALLAB_MODEL_TOP_P"] = "0.95"

start_server()
```

### Batch Processing

```python
from locallab.client import LocalLabClient

client = LocalLabClient("http://localhost:8000")

# Process multiple prompts in parallel
prompts = [
    "Write a poem about spring",
    "Explain quantum computing",
    "Tell me a joke"
]

responses = await client.batch_generate(prompts)
```

## Performance Optimization

### 1. Memory Optimization

**Using CLI (New!)**

```bash
# Enable memory optimizations via CLI
locallab start --quantize --quantize-type int8 --attention-slicing
```

**Using Environment Variables**

```python
# Enable memory optimizations
os.environ["LOCALLAB_ENABLE_QUANTIZATION"] = "true"
os.environ["LOCALLAB_QUANTIZATION_TYPE"] = "int8"  # or "int4" for more savings
os.environ["LOCALLAB_ENABLE_CPU_OFFLOADING"] = "true"
```

### 2. Speed Optimization

**Using CLI (New!)**

```bash
# Enable speed optimizations via CLI
locallab start --flash-attention --better-transformer
```

**Using Environment Variables**

```python
# Enable speed optimizations
os.environ["LOCALLAB_ENABLE_FLASH_ATTENTION"] = "true"
os.environ["LOCALLAB_ENABLE_ATTENTION_SLICING"] = "true"
os.environ["LOCALLAB_ENABLE_BETTERTRANSFORMER"] = "true"
```

### 3. Resource Management

```python
# Set resource limits
os.environ["LOCALLAB_MIN_FREE_MEMORY"] = "2000"  # MB
os.environ["LOCALLAB_MAX_BATCH_SIZE"] = "4"
os.environ["LOCALLAB_REQUEST_TIMEOUT"] = "30"
```

## Model Management

### Model Registry Configuration

```python
from locallab import MODEL_REGISTRY

# Check available models
print(MODEL_REGISTRY.keys())

# Load specific model
client.load_model("microsoft/phi-2")

# Get current model info
model_info = await client.get_current_model()
```

### Custom Model Configuration

```python
# Define custom model settings
os.environ["LOCALLAB_CUSTOM_MODEL"] = "your-org/your-model"
os.environ["LOCALLAB_MODEL_INSTRUCTIONS"] = """You are a helpful AI assistant.
Please provide clear and concise responses."""
```

## System Configuration

### Server Configuration

```python
# Configure server settings
os.environ["LOCALLAB_HOST"] = "0.0.0.0"
os.environ["LOCALLAB_PORT"] = "8000"
os.environ["LOCALLAB_WORKERS"] = "4"
os.environ["LOCALLAB_ENABLE_CORS"] = "true"
```

### Logging Configuration

```python
# Configure logging
os.environ["LOCALLAB_LOG_LEVEL"] = "INFO"
os.environ["LOCALLAB_ENABLE_FILE_LOGGING"] = "true"
os.environ["LOCALLAB_LOG_FILE"] = "locallab.log"
```

## CLI Configuration

The LocalLab CLI provides a powerful way to configure and manage your server. Here are some advanced CLI features:

### Interactive Configuration Wizard

```bash
# Run the configuration wizard
locallab config
```

### System Information

```bash
# Get detailed system information
locallab info
```

### Advanced CLI Options

```bash
# Start with advanced configuration
locallab start \
  --model microsoft/phi-2 \
  --port 8080 \
  --quantize \
  --quantize-type int4 \
  --attention-slicing \
  --flash-attention \
  --better-transformer
```

### Persistent Configuration

The CLI stores your configuration in `~/.locallab/config.json`. You can edit this file directly for advanced configuration:

```json
{
  "model_id": "microsoft/phi-2",
  "port": 8080,
  "enable_quantization": true,
  "quantization_type": "int8",
  "enable_attention_slicing": true,
  "enable_flash_attention": true,
  "enable_better_transformer": true
}
```

For more details, see the [CLI Guide](./cli.md).

## Best Practices

1. **Resource Management**

   - Monitor system resources
   - Use appropriate quantization
   - Enable optimizations based on hardware

2. **Error Handling**

   ```python
   try:
       response = await client.generate("Hello")
   except Exception as e:
       if "out of memory" in str(e):
           # Fall back to smaller model
           await client.load_model("microsoft/phi-2")
   ```

3. **Performance Monitoring**
   ```python
   # Get system information
   system_info = await client.get_system_info()
   print(f"CPU Usage: {system_info.cpu_usage}%")
   print(f"Memory Usage: {system_info.memory_usage}%")
   print(f"GPU Info: {system_info.gpu_info}")
   ```

## Related Resources

- [CLI Guide](./cli.md)
- [API Reference](./api.md)
- [Configuration Guide](../features/configuration.md)
- [Troubleshooting](./troubleshooting.md)
