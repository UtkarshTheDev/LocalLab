# LocalLab Features Guide

A comprehensive guide to LocalLab's features and capabilities.

## 📚 Table of Contents
1. [Model Management](./models.md)
2. [Resource Optimization](./performance.md)
3. [Streaming Responses](#streaming-responses)
4. [Batch Processing](#batch-processing)
5. [Custom Model Loading](#custom-model-loading)
6. [System Monitoring](#system-monitoring)

## Model Management

### Available Models

LocalLab comes with several pre-configured models optimized for different use cases:

| Model ID       | Size | RAM Required | Best For                          |
| -------------- | ---- | ------------ | --------------------------------- |
| qwen-0.5b      | 0.5B | 4GB          | Testing, lightweight applications |
| phi-2          | 2.7B | 6GB          | General purpose, code generation  |
| stable-code-3b | 3B   | 8GB          | Code completion                   |
| mistral-7b     | 7B   | 14GB         | Chat, reasoning                   |

### Model Loading

```python
# Python
client.load_model("qwen-0.5b")

# Node.js
await client.loadModel("qwen-0.5b");
```

### Automatic Fallback

Models automatically fall back to lighter versions if resources are insufficient:

```python
# Will fall back to qwen-0.5b if resources are insufficient
client.load_model("mistral-7b")
```

## Resource Optimization

### Memory Management

1. **Quantization Options**

   ```python
   # INT8 Quantization
   client.load_custom_model(
       name="model_name",
       quantization="int8"
   )

   # INT4 Quantization
   client.load_custom_model(
       name="model_name",
       quantization="int4"
   )
   ```

2. **Attention Slicing**

   ```python
   os.environ["LOCALLAB_ENABLE_ATTENTION_SLICING"] = "true"
   ```

3. **CPU Offloading**
   ```python
   os.environ["LOCALLAB_ENABLE_CPU_OFFLOADING"] = "true"
   ```

## Streaming Responses

### Basic Streaming

```python
# Python
for token in client.generate("Hello", stream=True):
    print(token, end="", flush=True)

# Node.js
for await (const token of client.streamGenerate("Hello")) {
    process.stdout.write(token);
}
```

## Batch Processing

### Basic Batch Processing

```python
# Python
prompts = ["Write a haiku", "Tell a joke", "Give a fact"]
responses = client.batch_generate(prompts)

# Node.js
const prompts = ["Write a haiku", "Tell a joke", "Give a fact"];
const responses = await client.batchGenerate(prompts);
```

## Custom Model Loading

### Loading from Hugging Face

```python
# Load any model from Hugging Face
client.load_custom_model(
    name="facebook/opt-350m",
    fallback_model="qwen-0.5b",
    quantization="int8"
)
```

## System Monitoring

### Resource Monitoring

```python
# Get system information
info = client.get_system_info()
print(f"CPU Usage: {info['cpu_usage']}%")
print(f"Memory Usage: {info['memory_usage']}%")
print(f"GPU Memory: {info['gpu_info']['used_memory']} MB")
```

## Additional Features

### 1. Request Validation

```python
os.environ["LOCALLAB_ENABLE_REQUEST_VALIDATION"] = "true"
```

### 2. Rate Limiting

```python
os.environ["LOCALLAB_RATE_LIMIT"] = "60"  # requests per minute
os.environ["LOCALLAB_BURST_SIZE"] = "10"
```

### 3. Compression

```python
os.environ["LOCALLAB_ENABLE_COMPRESSION"] = "true"
```

## 📚 Additional Resources

- [Model Registry](./models.md)
- [Performance Guide](./performance.md)
- [Security Guide](./security.md)
- [Configuration Reference](./configuration.md)
