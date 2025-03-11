# Changelog

All notable changes to LocalLab will be documented in this file.

## 0.4.21 - 2025-03-12

### Fixed

- Fixed critical issue with server not shutting down properly when Ctrl+C is pressed
- Improved signal handling in ServerWithCallback class to ensure clean shutdown
- Enhanced main_loop method to respond faster to shutdown signals
- Implemented more robust server shutdown process with proper resource cleanup
- Added additional logging during shutdown to help diagnose issues
- Increased shutdown timeout to allow proper cleanup of all resources
- Fixed multiple shutdown attempts when Ctrl+C is pressed repeatedly
- Ensured all server components are properly closed during shutdown

## 0.4.20 - 2025-03-12

### Fixed

- Enhanced server compatibility with different versions of uvicorn
- Improved lifespan initialization with comprehensive fallback mechanisms
- Fixed server startup issues with newer versions of uvicorn (0.34.0+)
- Added robust error handling for lifespan initialization
- Implemented multiple initialization strategies for different uvicorn versions
- Improved logging during server startup to better diagnose initialization issues
- Enhanced server stability with proper error recovery during startup
- Fixed "Using NoopLifespan" warning by properly initializing lifespan components
- Ensured compatibility with both older and newer versions of uvicorn
- Improved server reliability in various Python environments

## 0.4.19 - 2025-03-11

### Fixed

- Fixed critical issue with SimpleTCPServer not properly handling API requests
- Implemented proper ASGI server in SimpleTCPServer for handling API requests
- Added support for uvicorn's H11Protocol for better request handling
- Improved fallback server implementation with proper HTTP request parsing
- Enhanced API documentation to show correct URLs based on environment
- Fixed API examples to show local URL or ngrok URL based on configuration
- Ensured server works correctly in both local and Google Colab environments

## 0.4.18 - 2025-03-11

### Fixed

- Fixed import error: "cannot import name 'get_system_info' from 'locallab.utils.system'"
- Added backward compatibility function for system information retrieval
- Ensured proper display of system resources during server startup
- Enhanced compatibility between UI components and system utilities
- Improved error handling during server startup display
- Added graceful error recovery for UI component failures
- Ensured server continues to run even if display components fail
- Enhanced robustness of startup process with comprehensive error handling
- Added fallback mechanisms for all UI components to handle import errors
- Improved system resource display with multiple fallback options
- Enhanced model information display with graceful degradation
- Ensured server can start even with missing or incompatible dependencies

### Added

- Added minimal mode fallback server for critical initialization failures
- Implemented comprehensive error handling for configuration loading
- Created fallback endpoints for basic server functionality
- Added detailed error reporting in minimal mode
- Enhanced server resilience with multi-level fallback mechanisms

## 0.4.17 - 2025-03-11

### Fixed

- Fixed critical error: "'Server' object has no attribute 'start'"
- Implemented robust SimpleTCPServer as a fallback when TCPServer import fails
- Added direct socket handling for maximum compatibility across environments
- Enhanced server startup process to handle different server implementations
- Improved error handling in server shutdown process
- Added graceful fallback for servers without start/shutdown methods
- Enhanced compatibility with different versions of uvicorn
- Improved server stability with better error recovery mechanisms
- Added comprehensive error handling for socket operations
- Implemented non-blocking socket I/O for better performance
- Added direct fallback to SimpleTCPServer when server.start() fails
- Improved Google Colab integration with better error handling
- Enhanced event loop handling for different Python environments

## 0.4.16 - 2025-03-11

### Fixed

- Fixed critical error: "'Config' object has no attribute 'server_class'"
- Implemented custom startup method that doesn't rely on config.server_class
- Fixed import issues in Google Colab by properly exposing start_server in **init**.py
- Enhanced compatibility with different versions of uvicorn
- Improved server initialization for more reliable startup
- Added direct TCPServer initialization for better compatibility
- Implemented fallback mechanisms for TCPServer import to handle different uvicorn versions
- Added multiple import paths for TCPServer to ensure compatibility across all environments
- Enhanced error handling during server initialization
- Improved Google Colab integration with better import structure
- Added custom main_loop implementation with robust error handling
- Implemented graceful shutdown mechanism for all server components
- Enhanced server stability with improved error recovery

## 0.4.15 - 2025-03-11

### Fixed

- Fixed critical error: "'NoneType' object has no attribute 'startup'"
- Implemented NoopLifespan class as a fallback when all lifespan initialization attempts fail
- Ensured server can start even when lifespan initialization fails
- Added proper error handling for startup and shutdown events
- Enhanced server stability across different environments and uvicorn versions
- Added robust error recovery during server startup process
- Overrode uvicorn's startup and shutdown methods to add additional error handling
- Improved logging for lifespan-related errors to aid in troubleshooting
- Added graceful fallback mechanisms for all critical server operations
- Ensured clean server shutdown even when lifespan shutdown fails

## 0.4.14 - 2025-03-11

### Fixed

- Fixed critical error: "LifespanOn.**init**() takes 2 positional arguments but 3 were given"
- Enhanced lifespan initialization to handle different uvicorn versions with varying parameter requirements
- Implemented comprehensive parameter testing for all lifespan classes to ensure compatibility
- Added detailed logging for lifespan initialization to aid in troubleshooting
- Improved error handling for all lifespan-related operations

## 0.4.13 - 2025-03-11

### Fixed

- Fixed critical error with LifespanOn initialization: "LifespanOn.**init**() got an unexpected keyword argument 'logger'"
- Improved compatibility with different versions of uvicorn by properly handling lifespan initialization
- Enhanced error handling for different lifespan implementations
- Added graceful fallbacks when lifespan initialization fails

## 0.4.12 - 2025-03-11

### Fixed

- Fixed critical server startup error related to uvicorn lifespan initialization
- Fixed 'Config' object has no attribute 'logger' error during server startup
- Fixed 'Config' object has no attribute 'loaded_app' error
- Improved compatibility with different versions of uvicorn
- Enhanced error handling during server startup
- Fixed banner display functions to work with the latest server implementation

## 0.4.11 - 2025-03-11

### Fixed

- Fixed critical issue with `locallab start` failing due to uvicorn lifespan module errors
- Fixed `locallab config` command not properly prompting for new settings when reconfiguring
- Significantly improved CLI startup speed with optimized imports and conditional loading
- Enhanced configuration system to include all available options (cache, logging, etc.)
- Improved compatibility with different Python versions and environments
- Added better error handling for ngrok authentication token
- Fixed event loop handling for both local and Google Colab environments
- Removed "What's New" sections from documentation in favor of directing users to the changelog
- Restored option to skip advanced configuration settings for better user experience

## 0.4.10 - 2025-03-11

### Fixed

- Fixed critical issue with `locallab start` failing due to uvicorn lifespan module errors
- Fixed `locallab config` command not properly prompting for new settings when reconfiguring
- Significantly improved CLI startup speed with optimized imports and conditional loading
- Enhanced configuration system to include all available options (cache, logging, etc.)
- Improved compatibility with different Python versions and environments
- Added better error handling for ngrok authentication token
- Fixed event loop handling for both local and Google Colab environments
- Removed "What's New" sections from documentation in favor of directing users to the changelog

## 0.4.9 - 2025-03-11

### Fixed

- Fixed critical issue with `locallab config` command not being respected when running `locallab start`
- Enhanced configuration system to properly load and apply saved settings
- Improved user experience by showing current configuration before prompting for changes
- Added clear feedback when configuration is saved and how to use it

## 0.4.8 - 2025-03-10

### Fixed

- Fixed critical server startup error related to missing 'lifespan' attribute in ServerWithCallback class
- Fixed KeyError in 'locallab info' command by properly handling RAM information
- Significantly improved CLI startup speed through lazy loading of imports
- Enhanced error handling in system information display
- Fixed environment variable conflicts between CLI configuration and OS environment variables
- Improved configuration system to properly handle both CLI and environment variable settings
- Optimized server startup process for faster response time

### Changed

- Reduced unnecessary operations during CLI startup for better performance
- Improved memory usage reporting with proper unit conversion (GB instead of MB)
- Enhanced ServerWithCallback class with proper lifespan initialization
- Updated configuration system to use a unified approach for all settings

## 0.4.7 - 2025-03-08

### Added

- Enhanced CLI with interactive configuration wizard
- Added persistent configuration storage
- Implemented environment detection for smart defaults
- Added command groups: start, config, info
- Added support for configuring optimizations through CLI
- Improved Google Colab integration with context-aware prompts
- Added system information command

## 0.4.6 - 2025-03-08

### Fixed

- Improved streaming generation quality to match non-streaming responses
- Added proper stopping conditions for streaming to prevent endless generation
- Implemented repetition detection to stop low-quality streaming responses
- Reduced token chunk size for better quality control in streaming mode
- Ensured consistent generation parameters between streaming and non-streaming modes

## 0.4.5 - 2025-03-08

### Added

- Added memory monitoring to prevent CUDA out of memory errors
- Implemented adaptive token generation for streaming responses
- Added CUDA memory configuration with expandable segments

### Fixed

- Fixed torch.compile() errors by adding proper error handling and fallback to eager mode
- Fixed early stopping warning by correctly setting num_beams parameter
- Improved streaming generation with smaller token chunks for more responsive output
- Added memory-aware generation that adapts to available GPU resources
- Implemented error recovery for out-of-memory situations during generation

## 0.4.4 - 2025-03-08

### Fixed

- Fixed issue with banners (running banner, system instructions, model configuration, API documentation) repeating in the console at regular intervals
- Added flag to ensure startup information is only displayed once during server initialization
- Improved server callback handling to prevent duplicate banner displays

## 0.3.5 - 2023-03-05

### Fixed

- Fixed Env Configuration by removing the duplicated Env Configuration.

## [0.2.9] - 2025-03-04

### Added

- Added comprehensive API documentation display on server startup with curl examples
- Added model configuration section that displays current model and optimization settings
- Added system instructions section showing the current prompt template
- Improved environment variable handling for model configuration
- Enhanced server startup logging with detailed optimization settings
- Added support for reading HUGGINGFACE_MODEL environment variable to specify model
- Redesigned modern ASCII art banners for a more aesthetic interface
- Improved UI with cleaner banner separations and better readability

## [0.2.8] - 2025-03-03

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
