# Migration Guide: Monolithic to Modular Architecture

This guide explains the transition from the earlier monolithic structure of LocalLab to the new modular architecture introduced in version 0.1.9.

## Overview of Changes

In version 0.1.9, LocalLab underwent a significant architectural transformation, moving from a single large `main.py` file to a modular structure with specialized components:

| Before (< 0.1.9)               | After (>= 0.1.9)                                     |
| ------------------------------ | ---------------------------------------------------- |
| Single `main.py` file          | Multiple modules in dedicated directories            |
| Basic logging with `logger.py` | Comprehensive `logger` module with advanced features |
| Direct imports from `main`     | Properly structured imports from specific modules    |

## Directory Structure

The new structure organizes code into logical components:

```
locallab/
├── __init__.py           # Package exports
├── server.py             # Server startup and management
├── config.py             # Configuration and settings
├── model_manager.py      # Model loading and inference
├── core/                 # Core components
│   ├── __init__.py
│   └── app.py            # FastAPI application
├── routes/               # API routes
│   ├── __init__.py
│   ├── generate.py       # Text generation endpoints
│   ├── models.py         # Model management endpoints
│   └── system.py         # System information endpoints
├── ui/                   # User interface components
│   ├── __init__.py
│   └── banners.py        # ASCII art and UI elements
├── utils/                # Utilities
│   ├── __init__.py
│   └── networking.py     # Network-related utilities
└── logger/               # Logging system
    ├── __init__.py
    └── logger.py         # Logger implementation
```

## Import Changes

If you were directly importing from `locallab.main`, you'll need to update your imports:

### Before (< 0.1.9):

```python
from locallab.main import app, setup_ngrok, start_server
```

### After (>= 0.1.9):

```python
from locallab import start_server
from locallab.core.app import app
from locallab.utils.networking import setup_ngrok
```

## Logging Changes

The new logger module provides more features and better organization:

### Before (< 0.1.9):

```python
from locallab.logger import logger

logger.info("Starting server")
```

### After (>= 0.1.9):

```python
from locallab.logger import get_logger

logger = get_logger("my_module")
logger.info("Starting server")
```

## Server Status Tracking

The new version introduces explicit server status tracking:

```python
from locallab.logger.logger import set_server_status, get_server_status

# Update server status
set_server_status("initializing")  # Options: initializing, running, error, shutting_down

# Get current status
current_status = get_server_status()
```

## Request and Model Tracking

Track requests and model loading with the new APIs:

```python
from locallab.logger.logger import log_request, log_model_loaded, log_model_unloaded

# Log API requests
log_request("/generate", {"prompt": "Hello", "max_tokens": 100})

# Track model loading/unloading
log_model_loaded("gpt2", 3.5)  # Model loaded in 3.5 seconds
log_model_unloaded("gpt2")
```

## Ngrok Usage Changes

When using ngrok for public URL access in Google Colab, you now need to provide an authentication token:

### Before (< 0.1.9):

```python
from locallab.main import start_server
start_server(ngrok=True)
```

### After (>= 0.1.9):

```python
import os
# Set your ngrok auth token (REQUIRED)
os.environ["NGROK_AUTH_TOKEN"] = "your_token_here"  # Get from dashboard.ngrok.com

from locallab import start_server
start_server(use_ngrok=True)  # Parameter renamed from 'ngrok' to 'use_ngrok'
```

Note that the parameter has been renamed from `ngrok` to `use_ngrok` for clarity, and an auth token is now required for public URL access.

## Need Help?

If you encounter any issues during migration, please:

1. Check the full [Logger Documentation](../server/logger.md)
2. Review the [API Reference](api.md)
3. Open an issue on our [GitHub repository](https://github.com/Developer-Utkarsh/LocalLab/issues)
