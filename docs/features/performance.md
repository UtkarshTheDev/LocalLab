# Performance Guide

## Quick Optimization Guide

### 1. Memory Optimizations

```python
# Enable all memory optimizations
os.environ["LOCALLAB_ENABLE_QUANTIZATION"] = "true"
os.environ["LOCALLAB_QUANTIZATION_TYPE"] = "int8"
os.environ["LOCALLAB_ENABLE_ATTENTION_SLICING"] = "true"
os.environ["LOCALLAB_ENABLE_CPU_OFFLOADING"] = "true"
```

### 2. Speed Optimizations

```python
# Enable speed optimizations
os.environ["LOCALLAB_ENABLE_FLASH_ATTENTION"] = "true"
os.environ["LOCALLAB_ENABLE_BETTERTRANSFORMER"] = "true"
```

### 3. Resource Limits

```python
# Set resource limits
os.environ["LOCALLAB_MIN_FREE_MEMORY"] = "2000"  # MB
os.environ["LOCALLAB_MAX_BATCH_SIZE"] = "4"
os.environ["LOCALLAB_REQUEST_TIMEOUT"] = "30"
```

## Model Selection Guide

| Model Size | RAM Required | Best For             | Trade-offs     |
| ---------- | ------------ | -------------------- | -------------- |
| 0.5B - 3B  | 4-6GB        | Testing, Development | Lower quality  |
| 3B - 7B    | 8-12GB       | Production           | Good balance   |
| 7B+        | 14GB+        | High-quality         | Resource heavy |

## Configuration Options

### Server Configuration

```python
# Set server host and port
os.environ["LOCALLAB_HOST"] = "0.0.0.0"
os.environ["LOCALLAB_PORT"] = "8000"

# Enable CORS
os.environ["LOCALLAB_ENABLE_CORS"] = "true"
os.environ["LOCALLAB_CORS_ORIGINS"] = "*"
```

### Model Generation Parameters

```python
os.environ["LOCALLAB_MODEL_MAX_LENGTH"] = "2048"    # Maximum length of generated text
os.environ["LOCALLAB_MODEL_TEMPERATURE"] = "0.7"    # Controls creativity (0.0 to 1.0)
os.environ["LOCALLAB_MODEL_TOP_P"] = "0.9"         # Nucleus sampling probability
```

### Ngrok Setup for Google Colab

```python
import os
os.environ["NGROK_AUTH_TOKEN"] = "your_valid_ngrok_token_here"

from locallab import start_server
start_server(ngrok=True)  # Will show public URL in logs
```

## Optimization Techniques

### 1. Quantization

- INT8: Good balance of quality/memory
- INT4: Maximum memory savings
- FP16: GPU optimization

### 2. Attention Mechanisms

- Flash Attention: Faster processing
- Attention Slicing: Lower memory usage
- CPU Offloading: Handle larger models

### 3. Batch Processing

- Group similar requests
- Process in parallel
- Balance batch size

## Performance Monitoring

### System Metrics

```python
# Monitor system health
async def monitor_health():
    while True:
        info = await client.get_system_info()
        print(f"CPU: {info.cpu_usage}%")
        print(f"Memory: {info.memory_usage}%")
        print(f"GPU: {info.gpu_info}")
        await asyncio.sleep(60)
```

### Error Recovery

```python
try:
    response = await client.generate("prompt")
except Exception as e:
    if "out of memory" in str(e):
        # Switch to smaller model
        await client.load_model("microsoft/phi-2")
        response = await client.generate("prompt")
```

## Best Practices

### Local Deployment

1. Start with smaller models
2. Enable appropriate optimizations
3. Monitor resource usage

### Google Colab

1. Use GPU runtime
2. Enable quantization
3. Monitor memory usage

## Troubleshooting

### Common Issues

1. Out of Memory

   - Enable quantization
   - Use smaller model
   - Reduce batch size

2. Slow Response

   - Enable Flash Attention
   - Use appropriate batch size
   - Check system resources

3. GPU Issues
   - Verify CUDA availability
   - Check GPU memory
   - Consider CPU fallback

## Related Resources

- [Model Management](./models.md)
- [API Reference](../guides/API.md)
- [Troubleshooting Guide](../TROUBLESHOOTING.md)
