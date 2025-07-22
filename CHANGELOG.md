# Changelog

All notable changes to LocalLab will be documented in this file.

## [0.11.2] - 2025-07-23

### Enhanced
- **CLI chat interface redesign** - Modern minimal aesthetic with ASCII banner, professional color scheme, and enhanced visual hierarchy
- **Response generation reliability** - 3-retry logic with auto-reconnection, comprehensive format support, and special token cleaning
- **Chat interface improvements** - Removed verbose startup info, optimized spacing, minimal shutdown messages, and horizontal padding
- **ASCII art banner** - Complete "LOCALLAB" display with clean bottom-line design and balanced color brightness
- **Visual distinction** - Enhanced user/AI message contrast with subdued AI response colors for better readability

### Fixed
- **Response parsing failures** - Robust handling of 120+ second generation times, Chinese text, and conversation end markers
- **Connection recovery** - Automatic reconnection between retry attempts with exponential backoff delays
- **Import error** - Added missing `Group` import in `locallab/cli/ui.py` for proper Rich component rendering

### Technical Changes
- Updated `locallab/cli/ui.py`, `locallab/cli/chat.py`, `locallab/cli/connection.py`
- Enhanced error handling with comprehensive debug logging and response validation

## [0.11.1] - 2025-07-08

### Fixed
- **HuggingFace Hub progress bar error** - Fixed `'enable_progress_bars'` attribute error with version-agnostic fallback methods
- **BetterTransformer compatibility** - Updated for transformers>=4.49.0 with intelligent version detection and native PyTorch fallbacks
- **CUDA warnings** - Changed alarming "CUDA not available" to informative "GPU not detected - running in CPU mode"
- **Flash Attention messages** - Improved warnings with installation guidance
- **Optimization fallbacks** - Added comprehensive error handling with result tracking and summary logging
- **Download process reliability** - Continues smoothly even when optimizations fail with clear user feedback

### Technical Changes
- Updated `locallab/utils/progress.py`, `locallab/utils/early_config.py`, `locallab/model_manager.py`
- Improved logging levels from warnings to informative messages

## [0.11.0] - 2025-07-08

### Added
- **New `locallab models` command group** - Complete model management system with HuggingFace Hub integration
- **Model discovery** - Search LocalLab registry and HuggingFace Hub with filtering, sorting, and popularity metrics
- **Local model management** - Download, list, remove, and get info on cached models with progress indicators
- **Cache management** - Intelligent cache with metadata tracking and cleanup functionality
- **Rich UI components** - Beautiful tables and progress bars with multiple output formats (table/JSON)
- **Offline capability** - Registry models available without internet, downloaded models work offline
- **System compatibility checks** - Hardware requirements validation before downloads

### Commands Added
```bash
locallab models list              # List locally cached models
locallab models download <id>    # Download a model locally
locallab models remove <id>      # Remove a cached model
locallab models discover         # Discover available models
locallab models info <id>        # Show detailed model information
locallab models clean            # Clean up orphaned cache files
```

### Enhanced
- **Model loading integration** - Better integration with existing model loading system
- **Documentation** - Comprehensive model management guide with CLI reference updates
- **Error handling** - Robust network resilience and graceful fallbacks
- **Performance** - Faster server startup with pre-downloaded models and better resource utilization

### Technical Changes
- Added `locallab/utils/model_cache.py` for centralized cache management
- Added `locallab/utils/huggingface_search.py` for Hub integration
- Enhanced architecture with modular design and proper API integration

## [0.10.0] - 2025-07-06

### Added
- **Dynamic generation mode switching** - Inline syntax (`--stream`, `--chat`, `--simple`, `--batch`) to override modes per message
- **Enhanced chat interface** - Visual feedback for mode changes, better error messages, seamless mode switching
- **Documentation overhaul** - New CLI documentation hub, restructured README with chat interface prominence
- **Improved getting started** - 3-step quick start process with better visual hierarchy and formatting

### Enhanced
- **Chat interface** - Better command documentation, clear benefits for each mode, comprehensive examples
- **Documentation quality** - Consistent formatting, logical organization, proper cross-references, fixed markdown issues
- **User experience** - Chat interface as primary interaction method, simplified onboarding, better feature discovery

### Technical Changes
- **Regex-based parsing** - Robust pattern matching for inline mode detection with comprehensive error handling
- **Documentation infrastructure** - Markdown validation, link verification, unified formatting guidelines

## [0.9.0] - 2025-07-06

### Fixed
- **Fresh installation configuration bug** - Fixed confusing "enable_quantization: True" display with intelligent detection
- **Configuration interface issues** - Fixed quantization descriptions, model selection limitations, spacing, and boolean handling
- **User experience problems** - Proper welcome screen instead of raw config dump for new users

### Added
- **Fresh installation welcome** - Attractive welcome screen with step-by-step guidance and visual indicators
- **Enhanced configuration flow** - Improved model selection (registry + custom HuggingFace IDs), better optimization settings
- **Visual design improvements** - Modern emoji-rich interface with consistent hierarchy and better formatting
- **Organized configuration summary** - Logical grouping (Model, Optimization, Access) with enhanced completion screens

### Changed
- **Configuration UX** - Redesigned welcome flow, enhanced reconfigure experience, better error handling
- **Interface organization** - Reorganized settings into logical groups with improved information hierarchy

### Technical Changes
- Updated `locallab/server.py` and `locallab/cli/interactive.py` with fresh install detection and visual improvements

## [0.8.0] - 2025-07-04

### Fixed
- **Critical disk offloading error** - Fixed "You are trying to offload the whole model to the disk" preventing LLM loading
- **Qwen2.5-VL model loading** - Added comprehensive fallback logic and proper model class detection
- **Server stability** - Fixed repeated startup callbacks spamming logs every 30 seconds
- **Device mapping strategy** - Intelligent GPU memory detection with safe device assignments (`cuda:0`/`cpu`) instead of `device_map: "auto"`
- **Error recovery** - CPU retry logic when GPU loading fails, comprehensive error detection with appropriate fallbacks

### Added
- **Smart device management** - New `_get_safe_device_map()` method with GPU memory inspection and adaptive configuration
- **Enhanced model support** - Universal text generation and vision-language model support with cross-platform compatibility
- **Multi-level fallbacks** - Multiple fallback strategies ensure successful model loading

### Changed
- **Model loading process** - Updated quantization configuration, enhanced model class detection, optimized memory usage
- **Dependencies** - Updated transformers requirement to `>=4.49.0` for Qwen2.5-VL support

### Technical Changes
- Updated `locallab/model_manager.py`, `locallab/server.py`, `requirements.txt`, `setup.py`

## [0.7.2] - 2025-05-19

### Fixed
- Fixed Hugging Face model download issues with ModelManager and loading processes
- Improved model downloading and loading reliability and performance

## [0.7.1] - 2025-05-18

### Fixed
- **Critical `max_time` parameter error** - Fixed "unexpected keyword argument 'max_time'" in ModelManager.generate()
- Added `max_time` parameter to all generation endpoints and request models
- Set default max_time to 180 seconds with improved timeout error handling

## Client Package [1.1.0] - 2025-05-17

### Added
- **`max_time` parameter** - Added to both async and sync clients for server-side generation time limits
- Enhanced error handling for timeout-related issues with optional parameter (default: 180s)

### Fixed
- Fixed `max_time` parameter handling between client and server with proper timeout support

## [0.7.0] - 2025-05-16

### Improved
- **Stream generation quality** - Enhanced token generation parameters, stop sequence detection, repetition prevention, optimized buffering
- **Non-streaming generation** - Improved all endpoints with repetition detection, special token handling, conversation markers
- **Memory management** - Reduced memory check frequency, smarter cache clearing thresholds, better OOM recovery

### Changed
- Increased default max_length (2048→4096), token batch size (4→8), max_time (180s)
- Adjusted parameters: top_k (80), top_p (0.92), repetition_penalty (1.15) for better quality

## [0.6.6] - 2025-05-16

### Fixed
- **HuggingFace progress bars** - Fixed critical display error with version-agnostic approach and multiple fallback methods
- Enhanced error handling during downloads with improved early configuration system

## [0.6.5] - 2025-05-16

### Fixed
- Fixed critical HuggingFace progress bars display error
- Improved early configuration system for proper logging setup

## [0.6.4] - 2025-05-16

### Improved
- **Model downloading redesign** - Native HuggingFace progress bars with early configuration system
- **Visual improvements** - StdoutRedirector, clear separation between LocalLab logs and HF progress bars
- **Download experience** - Informative messages, consistent display across model types

## [0.6.3] - 2025-05-16

### Improved
- **Native progress bars** - Used HuggingFace's original progress bars instead of custom logger
- Fixed download log interception with proper visual formatting

## [0.6.2] - 2025-05-04

### Improved
- Native HuggingFace progress bars with fixed interleaved display and clear success messages

### Fixed
- **CLI configuration** - Fixed optimization settings not being saved properly, updated defaults to enabled

## [0.6.1] - 2025-05-02

### Fixed
- Fixed CLI config environment variable issue

## [0.6.0] - 2025-05-02

### Added
- **`do_sample` parameter** - Added to all generation endpoints with API documentation and examples
- Clear messages before/after model downloads for better UX

### Fixed
- **Model download logs** - Fixed interleaving with custom progress bar system and suppressed regular logs
- **Client `do_sample` error** - Added parameter to all client methods (client v1.0.9)

## [0.5.9] - 2025-05-01

### Fixed
- **Client parameter errors** - Fixed repetition_penalty, missing top_k, sync/async mismatch (client v1.0.8)
- Consistent parameter handling with accurate docstrings

### Improved
- **UI banner redesign** - Removed side borders, cleaner layout, better spacing and readability
- Enhanced visual consistency across INITIALIZING, RUNNING, and ngrok banners

## [0.5.8] - 2025-05-01

### Added
- **Response Quality Settings** - Optional CLI section with detailed parameter descriptions
- **Enhanced parameters** - max_length (4096→8192), top_k (50→80), max_time (120s), repetition_penalty (1.1→1.15)
- **Improved streaming** - Larger token batches (4 tokens), better stop sequence and repetition detection
- **Better error recovery** - Enhanced OOM handling and memory management

### Changed
- **Client improvements** - Timeouts (180→300s), max_length (1024→8192), added top_k and repetition_penalty
- **Client Package (v1.0.7)** - Increased timeouts, better streaming buffering, improved error handling

## [0.5.7] - 2025-05-01

### Improved

- Redesigned all UI banners with modern, aesthetic styling
- Enhanced INITIALIZING and RUNNING banners with box-style borders and improved spacing
- Redesigned ngrok tunnel banner with a modern box layout and better visual hierarchy
- Added informative notes to the ngrok banner for better user guidance
- Improved overall visual consistency and readability across all UI elements
- Enhanced color scheme for better visual appeal and readability

## [0.5.6] - 2025-05-01

### Fixed

- Fixed model download progress bars to display sequentially instead of interleaved
- Implemented custom progress bar handler for HuggingFace Hub downloads
- Added proper synchronization for multiple concurrent download progress bars
- Enhanced logging during model downloads for better readability
- Improved visual clarity of download progress information

## [0.5.5] - 2025-04-30

### Fixed

- Fixed extra spacing in the boundary of status banners
- Improved alignment of INITIALIZING and RUNNING status boxes
- Enhanced visual consistency across all UI elements

## [0.5.4] - 2025-04-30

### Improved

- Enhanced log coloring with lighter shades for better readability
- Redesigned ngrok tunnel banner with dynamic width to accommodate long URLs
- Improved visual aesthetics of the ngrok tunnel banner with modern styling
- Added automatic width adjustment for banners based on content length
- Fine-tuned color scheme to ensure all logs remain visible while not competing with important banners

## [0.5.3] - 2025-04-30

### Improved

- Implemented intelligent log coloring that uses subdued colors for routine logs
- Added smart detection of important log messages to highlight critical information
- Enhanced visual focus on banners and important messages by de-emphasizing routine logs
- Added special handling for ngrok and uvicorn logs to make them even more subdued
- Created a comprehensive pattern matching system to identify and highlight important logs
- Improved overall readability by reducing visual noise from routine log messages
- Completely redesigned the LocalLab ASCII art logo with a modern, aesthetically pleasing look
- Created beautiful boxed status indicators for both INITIALIZING and RUNNING states
- Enhanced visual hierarchy with prominent logo and clear status indicators
- Added detailed bullet points in status boxes for better user guidance
- Standardized the formatting of server details and ngrok tunnel information boxes
- Improved overall visual consistency across all UI elements
- Made server status much easier to distinguish at a glance

## [0.5.2] - 2025-04-30

### Fixed

- Fixed duplicate logging issue where the same log message appeared multiple times
- Improved color detection for terminal output - now only uses colors when supported
- Prevented multiple handlers from being added to the same logger
- Disabled uvicorn's default logging configuration to prevent duplication
- Enhanced logger initialization to ensure consistent formatting
- Added proper cleanup of existing handlers before adding new ones
- Improved compatibility with different terminal environments

## [0.5.1] - 2025-04-21

### Added

- Enhanced error handling and reliability in both clients
- Added timeout handling to sync client streaming methods
- Improved event loop cleanup and resource management
- Added connection state validation
- Added retry mechanism for streaming operations
- Added comprehensive logging throughout both clients
- Added proper cleanup of resources on client closure

### Fixed

- Fixed potential memory leaks in event loop handling
- Fixed thread cleanup in synchronous client
- Improved error propagation between async and sync clients
- Added proper timeout handling in streaming operations
- Enhanced connection state management

## [0.5.0] - 2025-04-21

### Fixed

- Fixed package structure to avoid duplicate exports
- Updated version numbers to be consistent across all files
- Fixed imports in sync_client.py to use correct package name
- Improved package import reliability
- Ensured both LocalLabClient and SyncLocalLabClient are properly exported

## [0.5.01] - 2025-04-21

### Fixed

- Fixed SyncLocalLabClient not being exported from locallab_client package
- Added proper exports for both LocalLabClient and SyncLocalLabClient in package **init**.py
- Ensured both sync and async clients are available through the main package import

## [0.4.50] - 2025-04-21

### Changed

- Renamed Python client package from `locallab-client` to `locallab_client` for better import compatibility
- Updated client package version to 0.3.0
- Changed client package structure to use direct imports instead of nested packages
- Improved client package documentation with correct import examples

## [0.4.49] - 2025-04-21

### Fixed

- Fixed server shutdown issues when pressing Ctrl+C
- Improved error handling during server shutdown process
- Enhanced handling of asyncio.CancelledError during shutdown
- Added proper handling for asyncio.Server objects during shutdown
- Reduced duplicate log messages during shutdown
- Added clean shutdown banner for better user experience
- Improved task cancellation with proper timeout handling
- Enhanced force exit mechanism to ensure clean termination

## [0.4.48] - 2025-03-15

### Client Library Changes (v0.2.1)

#### Added

- Added a dedicated synchronous client (`SyncLocalLabClient`) that doesn't require async/await
- Added automatic session closing to prevent resource leaks
- Added proper resource management with context managers

#### Changed

- Simplified client API with separate async and sync clients
- Updated documentation to clearly explain both client options

#### Fixed

- Fixed issue with unclosed client sessions causing warnings
- Improved error handling in streaming responses

### Client Library Changes

#### Added

- Added unified client API that works both with and without async/await
- Implemented automatic session closing to the Python client
- Added proper resource management with atexit handlers and finalizers
- Improved error handling in the Python client
- Added synchronous context manager support (`with` statement)

#### Changed

- Simplified client API - same methods work in both sync and async contexts
- Updated Python client to track activity and close inactive sessions
- Enhanced client session management to prevent resource leaks
- Improved client package version to 0.2.0

#### Fixed

- Fixed issue with unclosed client sessions causing warnings
- Improved error propagation in streaming responses

### Changed

- Removed all response formatting from streaming generation
- Simplified token streaming to provide raw, unformatted tokens
- Removed text cleaning and formatting from all generation endpoints
- Improved error handling in streaming responses

## [0.4.47] - 2025-03-15

### Added

- Optimized streaming generation for low-resource computers
- Implemented token-level streaming with proper error handling
- Added memory monitoring and adaptive token generation
- Enhanced error recovery mechanisms for streaming generation
- Improved client-side error handling for streaming responses

### Fixed

- Fixed issue with streaming generation stopping unexpectedly
- Improved error reporting in streaming responses
- Added timeout handling to prevent hanging during streaming
- Enhanced memory management to prevent OOM errors
- Optimized token generation for better performance on low-resource computers

### Changed

- Reduced default max_length for streaming to conserve memory
- Improved token buffering for smoother streaming experience
- Enhanced Python client with better error handling for streaming
- Added proper error message propagation from server to client

## [0.4.46] - 2025-03-14

### Added

- Added context awareness to streaming generation
- Enhanced streaming response quality with context tracking
- Improved streaming response coherence by maintaining conversation history
- Updated documentation with streaming context examples

### Fixed

- Fixed streaming response formatting issues
- Improved error handling in streaming generation
- Enhanced token cleanup for better readability

## [0.4.45] - 2025-03-14

### Fixed

- Fixed Python client initialization error "'str' object has no attribute 'headers'"
- Updated client package to handle string URLs in constructor
- Bumped client package version to 1.0.2
- Updated documentation with correct client initialization examples

## [0.4.31] - 2025-03-14

### Fixed

- Fixed HuggingFace token handling and validation in model loading
- Fixed ngrok token environment variable usage to use official `NGROK_AUTHTOKEN` name
- Fixed token storage and retrieval in config and environment variables

### Improved

- Improved CLI UX for token input and management
  - Removed token masking for better visibility
  - Show current token values when available
  - Added proper token validation
- Enhanced token handling across the package
  - Standardized environment variable names
  - Better string handling for token values
  - Consistent token validation
- Better error messages for token-related issues
- Improved networking setup with proper token handling

### Changed

- Updated environment variable names to use official standards
  - `NGROK_AUTHTOKEN` for ngrok token
  - `HUGGINGFACE_TOKEN` for HuggingFace token
- Standardized token management functions in config.py

## 0.4.25 - 2025-03-13

### Fixed

- Fixed critical error with ngrok URL handling in Google Colab
- Fixed NgrokTunnel type error during server initialization
- Improved error messages for ngrok connection issues
- Updated footer design for better visibility
- Clarified URL usage in documentation (localhost vs ngrok)

### Changed

- Simplified footer design in server output
- Enhanced ngrok tunnel setup process with better error handling
- Updated documentation to clearly distinguish between local and ngrok URLs

## 0.4.24 - 2025-03-13

### Added

- Added support for HuggingFace token through CLI and environment variables
- Interactive prompt for HuggingFace token when required
- Secure token handling in configuration
- Improved error messages for model loading issues

### Changed

- Made HuggingFace token optional but with interactive prompt when needed
- Enhanced model loading process with better token handling
- Updated documentation with HuggingFace token configuration details

## 0.4.23 - 2025-03-13

### Fixed

- Fixed critical issue with BERT model loading by removing device_map for BERT models
- Added proper BERT model configuration for text generation
- Improved model loading process with better architecture detection
- Enhanced error handling for different model architectures
- Fixed memory management for CPU-only environments
- Added automatic model type detection and configuration
- Improved compatibility with various model architectures
- Enhanced error messages for better debugging

### Added

- Added support for BERT models in text generation mode
- Implemented automatic model architecture detection
- Added proper model-specific configurations
- Enhanced memory optimization for different model types

## 0.4.22 - 2025-03-12

### Fixed

- Fixed critical issue with server not terminating properly when Ctrl+C is pressed
- Improved process termination by using os.\_exit() instead of sys.exit() for clean shutdown
- Added CPU compatibility by disabling quantization when CUDA is not available
- Fixed bitsandbytes error for CPU-only systems with clear warning messages
- Enhanced user experience with better error handling for non-GPU environments

### Added

- Added beautiful footer section with author information and social media links
- Included GitHub, Twitter, and Instagram links in the footer
- Added project repository link with star request
- Enhanced server startup display with comprehensive information

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
- Fixed API documentation to show correct URLs based on environment
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
- Removed duplicate architecture diagrams from the root `README.md` file.
