# Changelog

All notable changes will be documented in this file.

## [0.4.1] - 2024-02-23
### Enhanced
- Added detailed step-by-step instructions for ngrok token setup
- Improved ngrok error handling with clear visual guidance
- Added links to ngrok dashboard and registration

## [0.4.0] - 2024-02-23
### Enhanced
- Major version update with comprehensive UI improvements.
- Added beautiful ASCII art banners and refined logging sections.
- Added explicit ngrok tunnel handling for Google Colab (with a warning if an auth token is missing or invalid).
- Added a new method (get_model_generation_params) to allow overriding model generation parameters (max_length, temperature, top_p) via OS environment variables.
- Improved error and status messages with clear formatting and output flushes to ensure visibility in Colab.
- Updated active model details section to display generation parameters.

## [0.3.9] - 2024-02-23
- Previously enhanced logging and model configuration display.

## [0.3.8] - 2024-02-23
- Added default model generation settings and fixed missing imports.

## [0.3.7] - 2024-02-23
### Fixed
- Restored comprehensive logging sections with ASCII art banners, API overview, system and server details, creator footer, and error logs.
- Fixed the issue where the Hugging Face model defaults to "phi-2" by allowing override via the HUGGINGFACE_MODEL environment variable.
- Updated MODEL_REGISTRY import to resolve "name 'MODEL_REGISTRY' is not defined" error.

## [0.3.6] - 2024-02-23
### Fixed
- Fixed MODEL_REGISTRY import in __init__.py for Google Colab compatibility
- Added explicit exports in __init__.py

## [0.3.5] - 2024-02-23
### Fixed
- Fixed indentation error in main.py middleware declaration
- Improved error handling in server cleanup routine

## [0.3.4] - 2024-02-23
### Added
- Enhanced server startup logs with clearer model information
- Improved model loading feedback in logs
- Fixed Colab signal handling
- Added better version display in logs

## [0.3.3] - 2024-10-01
### Fixed
- Updated logging to include the active model in request logs.
- Enhanced model loading logs to explicitly mention Hugging Face model downloads.
- Updated API documentation to include a footer with creator details.
- Updated version numbers across the project.

## [0.3.2] - 2024-02-22
### Fixed
- Fixed text generation error by properly converting system instructions to string

## [0.3.1] - 2024-02-22
### Fixed
- Fixed system instructions import in model manager
- Fixed text generation error handling
- Improved error messages and logging

## [0.3.0] - 2024-02-22
### Fixed
- Fixed system instructions import in model manager
- Restored detailed ASCII art banners, API overview and server URL logs
- Improved error handling for ngrok
- Added better logging in startup and shutdown routines
- Improved text generation error handling

## [0.2.9] - 2024-02-22
### Fixed
- Fixed CPU usage monitoring in system resources
- Added safer resource checking with fallback values
- Improved system metrics collection

## [0.2.8] - 2024-02-22
### Fixed
- Fixed Phi-2 model loading by making attention slicing optional
- Restored ASCII art and logging structure
- Improved model optimization handling

## [Unreleased]
- Package creation for PyPI distribution
- Colab-optimized server implementation
- Automatic ngrok tunnel management
- Built-in Python client SDK
- Model caching and resource management

## [0.1.0] - 2023
- Initial release as Python package
- Google Colab integration
- Basic API functionality
