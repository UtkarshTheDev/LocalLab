# Logger Module

The Logger module provides comprehensive logging functionality for the LocalLab server. It offers colorized console output, server status tracking, request monitoring, and performance metrics.

## Features

- **Colorized Console Output**: Different log levels (INFO, WARNING, ERROR, etc.) are displayed in distinct colors for better readability.
- **Server Status Tracking**: Monitors and logs server state transitions (initializing, running, error, shutting_down).
- **Request Monitoring**: Tracks API requests with detailed metrics.
- **Performance Tracking**: Identifies and logs slow requests for performance optimization.
- **Model Loading Metrics**: Records model loading/unloading times and resource usage.

## Usage

### Basic Logging

```python
from locallab.logger import get_logger

# Create a logger with namespace
logger = get_logger("locallab.my_module")

# Use the logger
logger.info("Server started")
logger.warning("Low memory available")
logger.error("Failed to load model")
```

### Server Status Management

```python
from locallab.logger.logger import set_server_status, get_server_status

# Update server status
set_server_status("initializing")  # Options: initializing, running, error, shutting_down

# Get current status
current_status = get_server_status()
```

### Request Tracking

```python
from locallab.logger.logger import log_request, get_request_count

# Log an API request
log_request("/generate", {"prompt": "Hello", "max_tokens": 100})

# Get total request count
count = get_request_count()
```

### Model Tracking

```python
from locallab.logger.logger import log_model_loaded, log_model_unloaded

# Log model loading with time taken
log_model_loaded("gpt2", 3.5)  # Model loaded in 3.5 seconds

# Log model unloading
log_model_unloaded("gpt2")
```

## API Reference

### `get_logger(name: str) -> logging.Logger`

Creates and returns a logger with the given name.

### `set_server_status(status: str) -> None`

Updates the server status.

### `get_server_status() -> str`

Returns the current server status.

### `log_request(endpoint: str, params: Optional[Dict[str, Any]] = None) -> None`

Logs an API request.

### `log_model_loaded(model_id: str, load_time_seconds: float) -> None`

Logs when a model is loaded and records the time taken.

### `log_model_unloaded(model_id: str) -> None`

Logs when a model is unloaded.

### `get_uptime_seconds() -> float`

Returns the server's uptime in seconds.

### `get_request_count() -> int`

Returns the total number of requests processed.

### `get_active_model() -> Optional[str]`

Returns the currently active model ID, or None if no model is loaded.

### `configure_file_logging(log_dir: str = "logs") -> None`

Configures additional file-based logging alongside console logging.
