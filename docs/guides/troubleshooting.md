# Troubleshooting Guide

This document provides solutions to common issues encountered while running LocalLab.

## Common Issues

### Model Loading and Inference

**Issue:** Insufficient VRAM  
- Make sure your machine meets the minimum VRAM requirements for the selected model.
- Consider switching to a model with a lower VRAM footprint if necessary.

**Issue:** Errors during model download or loading  
- Verify internet connectivity.
- Check that the model name in the registry is correct.
- Ensure sufficient system memory is available.

### Google Colab Specific Issues

**Issue:** Ngrok authentication error
```
ERROR: Failed to create ngrok tunnel: authentication failed
```
**Solution:**
1. Get a valid ngrok auth token from [ngrok dashboard](https://dashboard.ngrok.com)
2. Set the token correctly:
```python
import os
os.environ["NGROK_AUTH_TOKEN"] = "your_token_here"
```

**Issue:** Out of Memory (OOM) errors
```
RuntimeError: CUDA out of memory
```
**Solution:**
1. Enable memory optimizations:
```python
os.environ["LOCALLAB_ENABLE_QUANTIZATION"] = "true"
os.environ["LOCALLAB_QUANTIZATION_TYPE"] = "int8"
```
2. Use a smaller model:
```python
os.environ["HUGGINGFACE_MODEL"] = "microsoft/phi-2"  # Smaller model
```

## Related Documentation
- [Getting Started](./getting-started.md)
- [Performance Guide](./features/performance.md)
- [FAQ](./FAQ.md)
