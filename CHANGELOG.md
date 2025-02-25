# Changelog

All notable changes for version updates.

## [0.1.5] - 2024-03-01

### Changed

- Extended the initial wait time in start_server from 5 to 15 seconds to allow the server ample time to initialize, especially in Google Colab environments.
- Increased health check timeout to 120 seconds for ngrok mode and 60 seconds for local mode to accommodate slower startups.
- Added detailed logging during health checks to aid in debugging startup issues.

## [0.1.4] - 2024-02-25

### Changed

- Improved logging across startup: the banner, model details, configuration, system resources, API documentation, quick start guide, and footer are now fully logged and printed.
- Updated the start_server function to extend the health check timeout to 60 seconds in Google Colab (when using ngrok) and to set an environment variable to trigger the Colab branch in run_server_proc.
- Modified startup_event to load the model in the background, ensuring that the server's /health endpoint becomes available in time and that logging output is complete.

## [0.1.3] - 2024-02-25

### Changed

- Updated GitHub Actions workflow to install the Locallab package along with its runtime dependencies in CI, ensuring that all required packages are available for proper testing.

### Fixed

- Refactored `run_server_proc` in the spawned process to initialize a dedicated logger ("locallab.spawn") to avoid inheriting SemLock objects from a fork context.
- Ensured that the log queue is created using the multiprocessing spawn context, preventing runtime errors in Google Colab.
- Updated Mermaid diagrams in `README.md` and `docs/colab/README.md` to enclose node labels in double quotes, resolving parse errors in GitHub rendering.
- Removed duplicate architecture diagrams from the root `README.md` to streamline documentation.
- Minor improvements to logging and error handling.

## [0.1.2] - 2024-02-25

### Changed

- Updated GitHub Actions workflow to install the Locallab package along with its runtime dependencies in CI.

### Fixed

- Fixed RuntimeError related to SemLock sharing in multiprocessing by clearing logger handlers in `run_server_proc`.
- Updated Mermaid diagrams to wrap node labels in double quotes, improving compatibility with GitHub rendering.
- Improved build status badge aesthetics in the README.

## [0.1.1] - 2024-02-25

### Fixed

- Fixed RuntimeError related to SemLock sharing in multiprocessing by clearing logger handlers in `run_server_proc`.
- Updated Mermaid diagrams to wrap node labels in double quotes, improving compatibility with GitHub rendering.
- Improved build status badge aesthetics in the README.

## [0.1.0] - 2024-02-24

### Added

- Initial release as a Python package with full Google Colab integration, dynamic model loading, robust logging (with ASCII art banners), API endpoints for text generation and system monitoring, Ngrok tunnel management, and comprehensive documentation.
