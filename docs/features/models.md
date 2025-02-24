# Model Management Guide

## Available Models

### Core Models
| Model ID | Size | RAM | Best For |
|----------|------|-----|----------|
| phi-2 | 2.7B | 6GB | General use |
| qwen-0.5b | 0.5B | 4GB | Testing |
| mistral-7b | 7B | 14GB | Advanced tasks |

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

## Related Documentation
- [Performance Guide](./performance.md)
- [API Reference](../API.md)
