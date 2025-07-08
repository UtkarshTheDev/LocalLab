# Changelog

All notable changes to LocalLab will be documented in this file.

## [0.11.1] - 2025-07-08

### 🔧 Bug Fixes - Download Command Improvements

This patch release fixes several warnings and errors that appeared during model downloads, providing a cleaner and more user-friendly experience.

### Fixed

#### 🚀 Download Command Improvements
- **Fixed HuggingFace Hub progress bar configuration error** - Resolved `'module 'huggingface_hub.utils.logging' has no attribute 'enable_progress_bars''` error with multiple fallback methods for different huggingface_hub versions
- **Fixed BetterTransformer version compatibility warning** - Updated optimization code to handle transformers>=4.49.0 requirement with intelligent version detection and graceful fallback to native PyTorch optimizations
- **Improved CUDA availability warnings** - Changed alarming "CUDA not available" warning to informative "GPU not detected - running in CPU mode" with helpful tips
- **Enhanced Flash Attention messages** - Improved warning messages to be more informative with installation guidance for faster inference
- **Added graceful optimization fallbacks** - Implemented comprehensive error handling for all optimization attempts with result tracking and summary logging

#### 🛠️ Enhanced Error Handling
- **Robust optimization system** - Download process continues smoothly even if some optimizations fail
- **Clear user feedback** - Users now get a summary of which optimizations were applied successfully
- **Version compatibility** - Works correctly with current transformers and huggingface_hub versions
- **Graceful degradation** - Falls back to safe defaults when advanced features aren't available

### Technical Changes
- Updated `locallab/utils/progress.py` with improved HuggingFace Hub progress bar configuration
- Updated `locallab/utils/early_config.py` with better version compatibility handling
- Enhanced `locallab/model_manager.py` with comprehensive optimization tracking and fallback mechanisms
- Improved logging levels from warnings to informative messages for better user experience

## [0.11.0] - 2025-07-08

### 🎉 Major Release - Comprehensive Model Management CLI

This release introduces a powerful model management system that allows users to discover, download, organize, and manage AI models locally. The new `locallab models` command group provides comprehensive model management capabilities with HuggingFace Hub integration.

### Added

#### 🤖 Complete Model Management CLI
- **New `locallab models` command group** - Comprehensive model management functionality
- **Model discovery** - Search and discover models from LocalLab registry and HuggingFace Hub
- **Local model download** - Download models locally for faster startup and offline usage
- **Model listing** - List all locally cached models with detailed information
- **Model removal** - Remove cached models to free up disk space
- **Model information** - Get detailed information about any model including system compatibility
- **Cache cleanup** - Clean up orphaned cache files and free disk space

#### 🔍 Advanced Model Discovery
- **HuggingFace Hub integration** - Real-time search of HuggingFace Hub models
- **Smart filtering** - Automatic filtering for text-generation models suitable for LocalLab
- **Search functionality** - Search models by keywords, tags, or descriptions
- **Tag filtering** - Filter models by categories (e.g., "conversational", "chat")
- **Popularity metrics** - Display download counts and popularity information
- **Sort options** - Sort by downloads, likes, or recent updates

#### 🛠️ Model Management Features
- **Offline capability** - Registry models always available without internet
- **Cache management** - Intelligent model cache with metadata tracking
- **System compatibility** - Check if models work on your hardware before downloading
- **Progress indicators** - Beautiful progress bars for download operations
- **Error handling** - Robust error handling with graceful fallbacks
- **Multiple output formats** - Table and JSON output for both human and programmatic use

#### 📊 Enhanced User Experience
- **Rich UI components** - Beautiful tables and progress indicators using Rich library
- **Clear feedback** - Informative messages and status indicators
- **Graceful degradation** - Works perfectly with or without internet connection
- **Rate limiting** - Respectful API usage with built-in rate limiting
- **Network timeouts** - Proper timeout handling for network operations

### Enhanced

#### 🚀 Model Management Infrastructure
- **New cache manager** - `locallab/utils/model_cache.py` for centralized cache management
- **HuggingFace searcher** - `locallab/utils/huggingface_search.py` for Hub integration
- **Model metadata tracking** - Track download dates, access counts, and model information
- **Improved model loading** - Better integration with existing model loading system

#### 📖 Documentation Expansion
- **Comprehensive model management guide** - Complete documentation with examples and troubleshooting
- **Updated CLI documentation** - Enhanced CLI reference with model management commands
- **Getting started improvements** - Added model management to onboarding flow
- **Cross-references** - Proper linking between all model management documentation

### Commands Added

#### 🎯 New CLI Commands
```bash
locallab models list              # List locally cached models
locallab models download <id>    # Download a model locally
locallab models remove <id>      # Remove a cached model
locallab models discover         # Discover available models
locallab models info <id>        # Show detailed model information
locallab models clean            # Clean up orphaned cache files
```

#### 🔧 Command Options
- **Discovery options**: `--search`, `--tags`, `--sort`, `--registry-only`, `--hub-only`
- **Output formats**: `--format table|json` for all commands
- **Filtering options**: `--registry-only`, `--custom-only` for listing
- **Safety options**: `--force` for downloads and removals

### Technical Improvements

#### 🏗️ Architecture Enhancements
- **Modular design** - Clean separation of concerns with dedicated modules
- **API integration** - Proper HuggingFace Hub API integration with error handling
- **Cache optimization** - Efficient model cache management and cleanup
- **Memory management** - Proper cleanup of model resources after operations

#### 🛡️ Reliability Features
- **Network resilience** - Graceful handling of network issues and timeouts
- **Error recovery** - Comprehensive error handling with helpful user messages
- **Data validation** - Proper validation of model information and cache data
- **Backward compatibility** - Full compatibility with existing LocalLab functionality

### Benefits for Users

#### ⚡ Performance Improvements
- **Faster server startup** - Pre-downloaded models load instantly
- **Offline usage** - Use models without internet connection after download
- **Disk space management** - Easy cleanup and monitoring of model cache
- **Better resource utilization** - Smart model selection based on system capabilities

#### 🎯 User Experience
- **Model discovery** - Easily find new models from HuggingFace Hub
- **Informed decisions** - See popularity metrics and system requirements before downloading
- **Simple management** - Easy-to-use commands for all model operations
- **Clear feedback** - Always know what's happening with clear status messages

## [0.10.0] - 2025-07-06

### 🎉 Major Release - Enhanced Chat Interface & Documentation Overhaul

This release significantly enhances the LocalLab chat interface with dynamic mode switching capabilities and provides a comprehensive documentation overhaul that makes LocalLab more accessible and user-friendly.

### Added

#### 🚀 Dynamic Generation Mode Switching
- **New inline mode switching syntax** - Override generation mode per message using `--stream`, `--chat`, `--simple`, `--batch`
- **Visual feedback system** - Clear indicators when mode overrides are applied
- **Backward compatibility** - All existing CLI options continue to work seamlessly
- **Smart parsing** - Robust regex-based mode detection with comprehensive error handling

#### 🚀 Enhanced Chat Interface Features
- **Improved mode override handling** - Seamless switching between generation modes within conversations
- **Better error messages** - Clear feedback for invalid mode specifications
- **Enhanced user experience** - Visual confirmation of mode changes during chat sessions

#### 📚 Comprehensive Documentation Overhaul
- **New CLI documentation hub** - Created `docs/cli/README.md` with complete CLI overview and navigation
- **Restructured main README** - Chat interface now prominently featured as the star feature
- **Enhanced getting started guide** - 3-step quick start process for immediate success
- **Improved CLI reference** - Better organized with chat interface as primary section
- **Better visual hierarchy** - Tables, emojis, and clear formatting throughout all documentation

### Enhanced

#### 💬 Chat Interface Improvements
- **Better command documentation** - All interactive commands clearly explained with examples
- **Improved feature descriptions** - Clear benefits and use cases for each generation mode
- **Enhanced examples** - Comprehensive usage scenarios and practical demonstrations
- **Better error handling** - More graceful handling of invalid mode switches

#### 📖 Documentation Quality
- **Consistent formatting** - Unified style across all documentation files
- **Better organization** - Logical flow from installation to advanced usage
- **Cross-references** - Proper linking between all documentation sections
- **User-focused content** - Clear value propositions and practical examples
- **Fixed markdown issues** - Resolved formatting problems that affected rendering

### Changed

#### 🎯 User Experience Focus
- **Chat interface prominence** - Now positioned as the primary way to interact with LocalLab
- **Simplified onboarding** - Clear 3-step process gets users to success immediately
- **Better feature discovery** - Enhanced documentation helps users find and use advanced features
- **Improved accessibility** - Documentation is now easier to read and navigate for all skill levels

#### 📚 Documentation Structure
- **Reorganized navigation** - Better hierarchy and cross-referencing between docs
- **Enhanced examples** - More practical, real-world usage scenarios
- **Clearer instructions** - Step-by-step guidance for all major features
- **Better visual design** - Tables, code blocks, and formatting improvements

### Technical Details

#### 🔧 Implementation
- **Regex-based parsing** - Robust pattern matching for inline mode detection
- **Comprehensive testing** - Full test coverage for dynamic mode switching functionality
- **Error handling** - Graceful degradation and clear error messages
- **Performance optimization** - Efficient parsing with minimal overhead

#### 📝 Documentation Infrastructure
- **Markdown validation** - Ensured all documentation renders correctly
- **Link verification** - All cross-references properly validated
- **Content organization** - Logical structure with clear navigation paths
- **Visual consistency** - Unified formatting and style guidelines

This release makes LocalLab significantly more user-friendly while adding powerful new features that enhance the chat experience. The comprehensive documentation overhaul ensures that users can easily discover and utilize all of LocalLab's capabilities.

## [0.9.0] - 2025-07-06

### 🎉 Major Release - CLI Configuration Interface Redesign

This release completely transforms the LocalLab configuration experience with a comprehensive redesign of the CLI interface, fixing critical bugs and dramatically improving user experience for both new and existing users.

### Fixed

#### 🔧 Critical Fresh Installation Configuration Bug
- **Fixed "enable_quantization: True" display bug** that was confusing new users on fresh installations
- Implemented intelligent fresh installation detection that checks for meaningful configuration keys
- Added proper differentiation between fresh installations and existing configurations
- Fixed configuration display to show appropriate welcome screen instead of raw config dump for new users

#### 🔧 Configuration Interface Issues
- **Fixed quantization type descriptions appearing after user selection** instead of before decision-making
- **Fixed model selection limitation** that only allowed MODEL_REGISTRY models instead of custom HuggingFace IDs
- **Fixed poor spacing and layout** in authentication token sections
- **Fixed boolean setting handling** that was causing KeyError exceptions in CLI prompts

### Added

#### 🚀 Fresh Installation Welcome Experience
- **New attractive welcome screen** for first-time users with clear guidance and expectations
- **Step-by-step setup guidance** that explains what each configuration step accomplishes
- **Visual indicators and emojis** throughout the interface for better user engagement
- **Context-aware messaging** that adapts based on whether it's a fresh or existing installation

#### 🚀 Enhanced Configuration Flow
- **Improved model selection** that allows both registry models and custom HuggingFace model IDs
- **Better optimization settings display** with clear descriptions and recommendations for low-spec hardware
- **Organized configuration summary** with logical grouping (Model, Optimization, Access)
- **Enhanced completion screens** with different messaging for fresh vs. existing installations

#### 🚀 Visual Design Improvements
- **Modern emoji-rich interface** with consistent visual hierarchy
- **Better spacing and formatting** throughout all configuration sections
- **Clear section separators** and organized information display
- **Attractive banners and visual elements** for improved user experience

### Changed

#### ⚡ Configuration User Experience
- **Redesigned welcome flow** to be more intuitive and informative for new users
- **Enhanced reconfigure experience** for existing users with clear current settings display
- **Improved error handling** and user guidance throughout the configuration process
- **Better default value presentation** with clear recommendations

#### ⚡ Interface Organization
- **Reorganized settings into logical groups**: Model selection, Optimization, Advanced settings, Authentication
- **Improved information hierarchy** with better visual organization
- **Enhanced completion summary** with comprehensive configuration overview
- **Better next-step guidance** after configuration completion

### Technical Details

#### Files Modified
- `locallab/server.py`: Added fresh installation detection and improved config command flow
- `locallab/cli/interactive.py`: Complete redesign of interactive configuration interface
- Enhanced fresh install detection logic and removed duplicate code
- Improved visual design and user experience throughout

#### Key Improvements
- **Fresh Installation Detection**: Intelligent detection based on meaningful configuration keys
- **Contextual UI Flow**: Different experiences for fresh vs. existing installations
- **Visual Appeal**: Consistent emoji usage, better spacing, and clear section organization
- **User Guidance**: Clear explanations and recommendations throughout the process
- **Error Prevention**: Better handling of edge cases and user input validation

### Impact

This release ensures that **ALL users have an excellent configuration experience**:
- ✅ New users get a proper welcome and guided setup experience
- ✅ Existing users see their current settings clearly organized and easy to understand
- ✅ No more confusing "enable_quantization: True" on fresh installations
- ✅ Beautiful, modern interface that's easy to navigate and understand
- ✅ Clear guidance and recommendations for optimal configuration
- ✅ Consistent visual design throughout the entire configuration flow

## [0.8.0] - 2025-07-04

### 🎉 Major Release - Comprehensive Model Loading Fixes

This release addresses critical issues that were preventing text generation LLMs from working properly with LocalLab, particularly the Qwen2.5-VL model and disk offloading errors.

### Fixed

#### 🔧 Critical Disk Offloading Issue
- **Fixed "You are trying to offload the whole model to the disk" error** that was preventing all text generation LLMs from loading
- Implemented intelligent device mapping strategy that prevents disk offloading:
  - **GPU Memory Detection**: Automatically checks available GPU memory before device placement
  - **Safe Device Selection**: Uses specific device assignments (`cuda:0` or `cpu`) instead of problematic `device_map: "auto"`
  - **CPU Fallback Logic**: Automatically uses CPU when GPU memory is insufficient (<4GB)
  - **Error Recovery**: Detects disk offloading errors and automatically retries with CPU-only configuration

#### 🔧 Qwen2.5-VL Model Loading
- **Fixed Qwen2.5-VL model loading errors** with proper model class detection
- Added comprehensive fallback logic for different model types:
  - `AutoModelForCausalLM` → `AutoModel` → `Qwen2_5_VLForConditionalGeneration` → `AutoModelForVision2Seq`
- Enhanced processor/tokenizer loading with smart detection:
  - **Vision-Language Models**: Use `AutoProcessor` for models with "vl", "vision", or "qwen2.5-vl" in name
  - **Text-Only Models**: Use `AutoTokenizer` for all other models

#### 🔧 Server Stability Issues
- **Fixed repeated startup callbacks** that were spamming logs every 30 seconds
- Added completion flag to prevent callback loops during server initialization
- Enhanced server startup process for cleaner, one-time initialization

#### 🔧 Enhanced Error Recovery
- **CPU Retry Logic**: When GPU loading fails with disk offloading errors, automatically retry with CPU-only configuration
- **Comprehensive Error Detection**: Intelligently detects various error patterns and triggers appropriate fallbacks
- **Memory-Aware Loading**: Considers available system resources when selecting device mapping strategy

### Added

#### 🚀 Smart Device Management
- **New `_get_safe_device_map()` method** for intelligent device selection
- **GPU Memory Inspection**: Checks GPU memory capacity before attempting GPU loading
- **Adaptive Configuration**: Automatically adjusts quantization settings based on available hardware
- **Multi-Level Fallbacks**: Multiple fallback strategies ensure models load successfully

#### 🚀 Enhanced Model Support
- **Universal Text Generation Support**: All text generation LLMs now work properly with the package
- **Vision-Language Model Support**: Proper handling of multimodal models like Qwen2.5-VL
- **Cross-Platform Compatibility**: Works reliably across different hardware configurations

### Changed

#### ⚡ Improved Model Loading Process
- **Updated quantization configuration** to use safe device mapping across all scenarios
- **Enhanced model class detection** with comprehensive fallback chains
- **Optimized memory usage** with intelligent device selection
- **Better error messages** with clear guidance for troubleshooting

#### ⚡ Dependencies
- **Updated transformers requirement** to `>=4.49.0` (minimum version for Qwen2.5-VL support)
- Ensured compatibility with latest Hugging Face ecosystem

### Technical Details

#### Files Modified
- `locallab/model_manager.py`: Core model loading logic with device mapping and error recovery
- `locallab/server.py`: Fixed startup callback loop
- `requirements.txt` & `setup.py`: Updated transformers version

#### Key Improvements
- **Device Mapping Strategy**: Prevents disk offloading by using specific device assignments
- **Error Recovery Mechanisms**: Multiple fallback strategies ensure successful model loading
- **Memory Management**: Intelligent resource allocation based on available hardware
- **Cross-Model Compatibility**: Universal support for text generation and vision-language models

### Impact

This release ensures that **ALL text generation LLMs work properly** with LocalLab:
- ✅ Qwen2.5-VL models load successfully
- ✅ Large models don't fail with disk offloading errors
- ✅ GPU models use GPU when memory is sufficient
- ✅ CPU fallback works seamlessly when needed
- ✅ Server startup is clean and stable
- ✅ Universal compatibility across different model types

## [0.7.2] - 2025-05-19

### Fixed

- Fixed Hugging Face Model Download Issues with ModelManager and ModelLoading Processes
- Improved Model Downloading and Loading Processes for better reliability and performance

## [0.7.1] - 2025-05-18

### Fixed

- Fixed critical error: "ModelManager.generate() got an unexpected keyword argument 'max_time'"
- Added proper handling of the `max_time` parameter in all generation endpoints
- Updated `ModelManager.generate()` method to accept the `max_time` parameter
- Added `max_time` parameter to all request models (GenerationRequest, BatchGenerationRequest, ChatRequest)
- Ensured consistent parameter passing between client and server
- Set default max_time to 180 seconds (3 minutes) when not specified
- Improved error handling for generation timeouts

## Client Package [1.1.0] - 2025-05-17

### Added

- Added `max_time` parameter to both async and sync clients to limit generation time on the server side
- Implemented proper handling of the `max_time` parameter in all generation methods
- Updated documentation for all client methods to include the new parameter
- Enhanced error handling for timeout-related issues
- Made `max_time` parameter optional with a default server-side value of 180 seconds

### Fixed

- Fixed error with `max_time` parameter not being properly handled by the server
- Improved parameter passing between client and server for better compatibility
- Updated client to properly handle server-side timeouts
- Added proper handling for when the `max_time` parameter is not provided

## [0.7.0] - 2025-05-16

### Improved

- Significantly enhanced stream generation quality with comprehensive improvements:

  - Improved token generation parameters for higher quality responses
  - Enhanced stop sequence detection with better conversation markers handling
  - Implemented more intelligent repetition detection to prevent loops
  - Optimized token buffering and yielding logic for smoother streaming
  - Added better error handling and recovery in streaming responses

- Improved non-streaming generation quality across all endpoints:

  - Enhanced generate, chat, and batch generation methods with optimized parameters
  - Implemented repetition detection to prevent the model from getting stuck
  - Added comprehensive special token handling and cleanup
  - Improved conversation marker detection for better response termination
  - Balanced parameters between quality and speed for optimal performance

- Optimized memory management:
  - Reduced frequency of memory checks to avoid interrupting generation
  - Implemented smarter memory threshold for cache clearing
  - Added better error recovery for out-of-memory situations

### Changed

- Increased default max_length from 2048 to 4096 for non-streaming generation
- Increased token generation batch size from 4 to 8 for better efficiency
- Adjusted top_k (80), top_p (0.92), and repetition_penalty (1.15) for better quality
- Increased max_time parameter to 180 seconds for more complete responses
- Enhanced all generation endpoints with consistent high-quality parameters

## [0.6.6] - 2025-05-16

### Fixed

- Fixed critical error with Hugging Face progress bars display
- Added robust version-agnostic approach to enable progress bars
- Implemented multiple fallback methods for different huggingface_hub versions
- Fixed AttributeError with huggingface_hub.utils.logging module
- Added direct environment variable configuration for maximum compatibility
- Enhanced error handling during model downloads
- Improved early configuration system to properly set up logging

### Changed

- Corrected function naming and imports for better compatibility

## [0.6.5] - 2025-05-16

### Fixed

- Fixed critical error with Hugging Face progress bars display
- Improved early configuration system to properly set up logging

## [0.6.4] - 2025-05-16

### Improved

- Completely redesigned model downloading experience with proper native Hugging Face progress bars
- Created new early configuration system to set up logging before any Hugging Face libraries are imported
- Implemented StdoutRedirector to ensure proper display of progress bars during model downloads
- Temporarily disabled all logging handlers during model downloads to prevent interference
- Added clear visual separation between LocalLab logs and Hugging Face progress bars
- Set environment variables to optimize Hugging Face download experience
- Configured transformers library to use native progress bars for model downloads
- Added informative messages before and after model downloads for better user experience
- Ensured consistent progress bar display across different model types and sizes

## [0.6.3] - 2025-05-16

### Improved

- Enhanced model downloading experience by using HuggingFace's native progress bars instead of custom logger
- Fixed issue with Hugging Face download logs being intercepted by custom logger
- Ensured Hugging Face progress bars display in their original, visually appealing format
- Improved configuration of Hugging Face Hub progress bars for better visual experience
- Completely bypassed custom logging for Hugging Face download-related logs
- Configured transformers library to use native progress bars for model downloads

## [0.6.2] - 2025-05-04

### Improved

- Improved model downloading experience by using HuggingFace's native progress bars
- Fixed interleaved progress bars issue during model downloads
- Added clear success messages after model downloads

### Fixed

- Fixed CLI configuration issue where optimization settings shown as enabled by default weren't being properly saved
- Updated default values for all optimization settings to be enabled by default
- Ensured consistency between displayed optimization settings and saved configuration

## [0.6.1] - 2025-05-02

### Fixed

- Fixed CLI config environment variable issue

## [0.6.0] - 2025-05-02

### Added

- Added `do_sample` parameter to all generation endpoints in the API
- Updated API documentation to include the `do_sample` parameter with description and examples
- Added clear messages before and after model downloads for better user experience

### Fixed

- Fixed model downloading logs to display properly without interleaving
- Implemented a custom progress bar system for Hugging Face downloads
- Suppressed regular logs during model downloads to avoid interference with progress bars
- Enhanced progress bar display with better formatting and descriptions
- Fixed client error with `do_sample` parameter by adding it to all client methods
- Updated client package version to 1.0.9 to reflect these fixes

## [0.5.9] - 2025-05-01

### Fixed

- Fixed error in client package when using repetition_penalty parameter
- Fixed missing top_k parameter in async client methods
- Fixed parameter mismatch between sync and async client implementations
- Updated client package version to 1.0.8 to reflect these fixes
- Ensured consistent parameter handling across all client methods
- Fixed docstrings to accurately reflect all available parameters

### Improved

- Redesigned UI banners to remove side borders for better alignment and aesthetics
- Improved INITIALIZING banner with cleaner layout and better spacing
- Enhanced RUNNING banner with more modern design and better readability
- Redesigned ngrok tunnel banner with improved layout for better URL display
- Maintained top and bottom borders for visual separation while removing side borders
- Enhanced overall visual consistency across all banners

## [0.5.8] - 2025-05-01

### Added

- Added optional Response Quality Settings section to the CLI configuration
- Added detailed parameter descriptions for all response quality settings
- Increased default max_length from 4096 to 8192 tokens for more complete responses
- Increased default top_k from 50 to 80 for better quality responses
- Added max_time parameter (default: 120 seconds) to control generation time
- Improved token-level streaming with larger token batches (4 tokens at a time)
- Enhanced stop sequence detection to only check for definitive end markers
- Improved repetition detection to only stop for extreme repetition
- Added better error recovery for out-of-memory situations

### Changed

- Made Response Quality Settings section optional in CLI (default: skip)
- Updated client timeouts from 180 to 300 seconds (5 minutes) for more complete responses
- Increased client default max_length from 1024 to 8192 tokens to match server's default
- Increased repetition_penalty from 1.1 to 1.15 for better quality
- Updated all API routes to include top_k and repetition_penalty parameters
- Enhanced memory management to prevent OOM errors
- Improved error handling in streaming responses

### Client Package Changes (v1.0.7)

- Increased default timeouts for all operations
- Added repetition_penalty parameter to all generation methods
- Improved error handling and recovery in streaming
- Added better buffering for token-level streaming
- Increased retry counts for better reliability
- Added top_k parameter to all generation methods

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
