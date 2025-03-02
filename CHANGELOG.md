# Changelog

All notable changes to LocalLab will be documented in this file.

## [0.2.8] - 2025-03-02

### Fixed

- Fixed parameter mismatch in text generation endpoints by properly handling `max_new_tokens` parameter
- Resolved coroutine awaiting issues in streaming generation endpoints
- Fixed async generator handling in `stream_chat` and `generate_stream` functions
- Enhanced error handling in streaming responses to provide better error messages
- Improved compatibility between route parameters and model manager methods

## [0.2.7] - 2025-03-02

### Added

- Added missing dependencies in `setup.py`: huggingface_hub, pynvml, and typing_extensions
- Improved dependency management with dev extras for testing packages
- Enhanced error handling for GPU memory detection

### Fixed

- Fixed circular import issues between modules
- Improved error handling in system utilities
- Enhanced compatibility with Google Colab environments

## [0.2.6] - 2025-03-02

### Added

- New model loading endpoint that accepts model_id in the request body at `/models/load`
- `format_chat_messages` function to properly format chat messages for the model
- CLI function to support command-line usage with click interface

### Fixed

- Properly awaiting async `generate_text` in chat completion endpoint
- Fixed async generator handling in `generate_stream` function
- Fixed streaming in the `stream_chat` function to correctly send server-sent events
- Properly escaped newline characters in the streaming response
- Added missing dependencies in `setup.py`: colorama, python-multipart, websockets, psutil, and nest-asyncio

## [0.2.5] - 2025-03-02

### Added

- `get_network_interfaces` function to retrieve information about available network interfaces
- `get_public_ip` async function to retrieve the public IP address of the machine
- Adapter methods in `ModelManager` (`generate_text` and `generate_stream`) to maintain API compatibility with route handlers

### Fixed

- Import error for `get_public_ip` and `get_network_interfaces` functions
- Naming mismatch between route handlers and `ModelManager` methods
- New dependencies in `setup.py`: `netifaces` and `httpx`

## [0.2.4] - 2025-03-02

### Fixed

- Fixed API endpoint errors for `/models/available` and other model endpoints
- Resolved parameter error in `get_model_generation_params()` function
- Improved error handling for model optimization settings through environment variables
- Fixed circular import issues between routes and core modules
- Enhanced Flash Attention warning message to be more informative

### Added

- Added new `get_gpu_info()` function for detailed GPU monitoring
- Added improved system resource endpoint with detailed GPU metrics
- Added robust environment variable handling for optimization settings

### Changed

- Made optimization flags more robust by checking for empty string values
- Improved fallback handling for missing torch packages
- Enhanced server startup logs with better optimization information

## [0.2.3] - 2025-03-02

### Fixed

- Fixed critical server startup error in Google Colab environment with uvicorn callback configuration
- Resolved "'list' object is not callable" error by properly implementing the callback_notify as an async function
- Enhanced server startup sequence for better compatibility with both local and Colab environments
- Improved custom server implementation to handle callbacks more robustly

## [0.2.2] - 2025-03-02

### Fixed

- Fixed circular import issue between core/app.py and routes/system.py by updating system.py to use get_request_count from logger module directly
- Made Flash Attention warning less alarming by changing it from a warning to an info message with better explanation
- Enhanced get_system_info endpoint with cleaner code and better organization
- Fixed potential issues with GPU info retrieval through better error handling

## [0.2.0] - 2025-03-02

### Added

- Comprehensive environment check system that validates:
  - Python version compatibility
  - CUDA/GPU availability and configuration
  - Ngrok token presence when running in Google Colab
- Improved error handling with detailed error messages and suggestions
- Clear instructions for setting up ngrok authentication token

### Changed

- Complete removal of the deprecated monolithic `main.py` file
- Enhanced ngrok setup process with better authentication handling:
  - Automatic detection of auth token from environment variables
  - Clear error messages when auth token is missing
  - Improved token validation and connection process
- Parameter renamed from `ngrok` to `use_ngrok` for clarity
- More readable ASCII art for initializing banner
- Improved documentation about ngrok requirements for Google Colab

### Fixed

- Fixed circular import issues between core/app.py and routes modules
- Fixed ngrok authentication flow to properly use auth token from environment variables
- Fixed error with missing torch import in the server.py file
- Added graceful handling of missing torch module to prevent startup failures
- Improved error messages when server fails to start
- Better exception handling throughout the codebase

## [0.1.9] - 2025-03-01

### Added

- Clear ASCII art status indicators ("INITIALIZING" and "RUNNING") showing server state
- Warning messages that prevent users from making API requests before the server is ready
- Callback mechanism to display the "RUNNING" banner only when the server is fully operational
- New dedicated logger module with comprehensive features:
  - Colorized console output for different log levels
  - Server status tracking (initializing, running, error, shutting_down)
  - Request tracking with detailed metrics
  - Model loading/unloading metrics
  - Performance monitoring for slow requests
- API documentation for logger module with usage examples

### Changed

- Completely refactored the codebase into a more modular structure:
  - Split main.py into smaller, focused modules
  - Created separate directories for routes, UI components, utilities, and core functionality
  - Improved import structure to prevent circular dependencies
  - Better organization of server startup and API functionality
- Enhanced model loading process with proper timing and status updates
- Improved error handling throughout the application
- Better request metrics in response headers
- Removed old logger.py in favor of the new dedicated logger module

### Fixed

- Complete removal of health checks and validation when setting up ngrok tunnels
- Fixed issue where logs did not appear correctly due to server starting in a separate process
- Simplified ngrok setup process to run without validation to prevent connection errors during startup
- Improved server startup flow to be more direct without background health checks or API validation
- Reorganized startup sequence to work properly with ngrok, enhancing compatibility with Colab

## [0.1.7] - 2025-03-01

### Changed

- Removed the background process workflow for server startup. The server now runs directly in the main process, ensuring that all logs (banner, model details, system resources, etc.) are displayed properly.
- Simplified the startup process by directly calling uvicorn.run(), with optional ngrok setup if the server is run in Google Colab.

## [0.1.6] - 2025-02-25

### Added

- Added utility function is_port_in_use(port: int) → bool to check if a port is already in use.
- Added async utility function load_model_in_background(model_id: str) to load the model asynchronously in the background while managing the global loading flag.
- Updated server startup functions to incorporate these utilities, ensuring proper port management and asynchronous model loading.

## [0.1.5] - 2025-02-25

### Changed

- Extended the initial wait time in start_server from 5 to 15 seconds to allow the server ample time to initialize, especially in Google Colab environments.
- Increased health check timeout to 120 seconds for ngrok mode and 60 seconds for local mode to accommodate slower startups.
- Added detailed logging during health checks to aid in debugging startup issues.

## [0.1.4] - 2025-02-25

### Changed

- Improved logging across startup: the banner, model details, configuration, system resources, API documentation, quick start guide, and footer are now fully logged and printed.
- Updated the start_server function to extend the health check timeout to 60 seconds in Google Colab (when using ngrok) and to set an environment variable to trigger the Colab branch in run_server_proc.
- Modified startup_event to load the model in the background, ensuring that the server's /health endpoint becomes available in time and that logging output is complete.

## [0.1.3] - 2025-02-25

### Changed

- Updated GitHub Actions workflow to install the Locallab package along with its runtime dependencies in CI, ensuring that all required packages are available for proper testing.

### Fixed

- Refactored `run_server_proc` in the spawned process to initialize a dedicated logger ("locallab.spawn") to avoid inheriting SemLock objects from a fork context.
- Ensured that the log queue is created using the multiprocessing spawn context, preventing runtime errors in Google Colab.
- Updated Mermaid diagrams in `README.md` and `docs/colab/README.md` to enclose node labels in double quotes, resolving parse errors in GitHub rendering.
- Removed duplicate architecture diagrams from the root `
