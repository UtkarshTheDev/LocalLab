# Changelog

All notable changes for version updates.

## [0.1.3] - 2024-02-27

### Changed

- Updated GitHub Actions workflow to use the --no-cache-dir flag in pip install commands, which prevents disk space issues during dependency installation (e.g., for large packages like torch).

## [0.1.2] - 2024-02-25

### Changed

- Updated GitHub Actions workflow to install the Locallab package along with its runtime dependencies in CI, ensuring that all required packages are available for proper testing.

### Fixed

- Refactored `run_server_proc` in the spawned process to initialize a dedicated logger ("locallab.spawn") to avoid inheriting SemLock objects from a fork context.
- Ensured that the log queue is created using the multiprocessing spawn context, preventing runtime errors in Google Colab.
- Updated Mermaid diagrams in `README.md` and `docs/colab/README.md` to enclose node labels in double quotes, resolving parse errors in GitHub rendering.
- Removed duplicate architecture diagrams from the root `README.md` to streamline documentation.
- Minor improvements to logging and error handling.

## [0.1.1] - 2024-02-25

### Fixed

- Fixed RuntimeError related to SemLock sharing in multiprocessing by clearing logger handlers in `run_server_proc`.
- Updated Mermaid diagrams in `README.md` and `docs/colab/README.md` to wrap node labels in double quotes, improving compatibility with GitHub rendering.
- Improved build status badge aesthetics in the README.

## [0.1.0] - 2024-02-24

### Added

- Upgraded package version from 0.0 to 0.1.0.
- Initial release as a Python package with full Google Colab integration.
- Basic API functionality including dynamic model loading and inference endpoints.
- Enhanced logging with ASCII art banners, detailed model and system resource information, and robust error handling.
- Ngrok tunnel management for public URL access in Colab.
- Comprehensive documentation with absolute URLs for smooth navigation.
- GitHub Actions workflow for automated PyPI publishing.
- MIT License introduced.
