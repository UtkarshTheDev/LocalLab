# Changelog

All notable changes for version updates.

## [0.1.1] - 2024-02-25

### Fixed

- Fixed RuntimeError related to SemLock sharing in multiprocessing by clearing logger handlers in run_server_proc.
- Updated Mermaid diagrams in README.md and docs/colab/README.md to wrap node labels in double quotes, improving compatibility with GitHub rendering.
- Improved build status badge aesthetics in the README.

## [0.1.0] - 2024-02-23

### Added

- Upgraded package version from 0.0 to 0.1.0.
- Initial release as a Python package with full Google Colab integration.
- Basic API functionality including dynamic model loading and inference endpoints.
- Enhanced logging with ASCII art banners, detailed model and system resource information, and robust error handling.
- Ngrok tunnel management for public URL access in Colab.
- Comprehensive documentation with absolute URLs for smooth navigation.
- GitHub Actions workflow for automated PyPI publishing.
- MIT License introduced.
