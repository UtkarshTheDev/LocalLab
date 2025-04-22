# Troubleshooting Guide

## 🔍 Common Issues for Beginners

### Installation Issues

**Problem:** `pip install` fails
```
ERROR: Could not find a version that satisfies the requirement locallab
```
**Solution:**
1. Make sure you have Python 3.8 or higher:
   ```bash
   python --version
   ```
2. Update pip:
   ```bash
   python -m pip install --upgrade pip
   ```
3. Try installing with specific Python version:
   ```bash
   python3.8 -m pip install locallab locallab-client
   ```

### Import Issues

**Problem:** Import error with locallab_client
```python
ImportError: No module named locallab_client
```
**Solution:**
Remember that while you install using `pip install locallab-client`, you import using underscore:
```python
# Correct imports:
from locallab_client import LocalLabClient  # For async
from locallab_client import SyncLocalLabClient  # For sync
```

### Connection Issues

**Problem:** Cannot connect to server
```
ConnectionError: Failed to connect to http://localhost:8000
```
**Solution:**
1. Make sure the server is running:
   ```bash
   locallab start
   ```
2. Wait for the "Server is running" message
3. Check if the URL is correct
4. Try with explicit localhost:
   ```python
   client = SyncLocalLabClient("http://127.0.0.1:8000")
   ```

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

### Authentication Issues

**Issue:** HuggingFace Authentication Error
```
ERROR: Failed to load model: Invalid credentials in Authorization header
```
**Solution:**
1. Get a HuggingFace token from [HuggingFace tokens page](https://huggingface.co/settings/tokens)
2. Set the token in one of these ways:
   ```python
   # Option 1: Environment variable
   os.environ["HUGGINGFACE_TOKEN"] = "your_token_here"
   
   # Option 2: Configuration file
   from locallab.cli.config import set_config_value
   set_config_value("huggingface_token", "your_token_here")
   ```
3. Restart the LocalLab server

Note: Some models like microsoft/phi-2 require authentication to download.

## Related Documentation
- [Getting Started](./getting-started.md)
- [Performance Guide](./features/performance.md)
- [FAQ](./FAQ.md)
