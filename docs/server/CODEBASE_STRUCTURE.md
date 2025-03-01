# LocalLab Codebase Structure (After Refactoring)

## Directory Structure

```
locallab/
├── __init__.py               # Package initialization, version info
├── server.py                 # Main entry point for the server
├── config.py                 # Configuration management
├── model_manager.py          # Handles model loading/unloading
├── core/                     # Core functionality
│   ├── __init__.py
│   ├── app.py                # FastAPI application setup
│   └── security.py           # Security-related utilities
├── routes/                   # API routes
│   ├── __init__.py
│   ├── api.py                # Main API endpoints
│   ├── management.py         # Server management endpoints
│   └── ui.py                 # UI-related endpoints
├── ui/                       # User interface components
│   ├── __init__.py
│   ├── components/           # UI components (HTML, JS)
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── header.py
│   │   └── settings.py
│   ├── pages/                # Complete UI pages
│   │   ├── __init__.py
│   │   ├── index.py
│   │   └── admin.py
│   └── templates/            # Jinja2 templates
│       ├── base.html
│       └── ...
├── utils/                    # Utility functions
│   ├── __init__.py
│   ├── network.py            # Networking utilities
│   └── system.py             # System utilities
└── logger/                   # Logging module
    ├── __init__.py
    └── logger.py             # Logger implementation
```

## Core Components

- **server.py**: The main entry point for the LocalLab server. Handles startup, shutdown, and model management.
- **core/app.py**: Sets up the FastAPI application, including middleware, routes, and event handlers.
- **routes/**: Contains API endpoints organized by functionality.
- **ui/**: Manages the user interface, including HTML components and templates.
- **utils/**: Provides utility functions for networking, system resources, etc.
- **logger/**: Comprehensive logging system with colorized output and metrics tracking.

## Major Improvements

1. **Better Code Organization**: Code is now organized into modules based on functionality, making it easier to navigate and maintain.
2. **Reduced Circular Dependencies**: The new structure minimizes circular imports, improving stability.
3. **Enhanced User Experience**: UI components are better organized and more maintainable.
4. **Simplified Server Startup**: The server startup process is now more straightforward and robust.
5. **Comprehensive Logging**: The new logger module provides detailed logging with various features like colorized output, server status tracking, and performance metrics.

## How It Works

1. **Server Startup**:

   - `server.py` is the entry point
   - It creates the FastAPI application using `core/app.py`
   - Middleware, routes, and event handlers are set up
   - The server starts listening for requests

2. **API Requests**:

   - Requests come into the FastAPI application
   - They are routed to the appropriate endpoint in `routes/`
   - The endpoints process the request and return a response
   - The logger tracks request metrics and performance

3. **Model Management**:
   - `model_manager.py` handles loading and unloading models
   - It manages system resources and optimizes memory usage
   - The logger tracks model loading times and resource usage
