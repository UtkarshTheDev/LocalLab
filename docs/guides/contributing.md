# Contributing to LocalLab

## 📚 Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Code Style](#code-style)
4. [Making Changes](#making-changes)
5. [Testing](#testing)
6. [Documentation](#documentation)
7. [Submitting Changes](#submitting-changes)

## Getting Started

1. **Fork the Repository**
   - Visit [LocalLab on GitHub](https://github.com/Developer-Utkarsh/LocalLab)
   - Click the "Fork" button

2. **Clone Your Fork**
   ```bash
   git clone https://github.com/your-username/LocalLab.git
   cd LocalLab
   ```

3. **Set Up Development Environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows

   # Install dependencies
   pip install -e ".[dev]"
   ```

## Development Setup

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Pre-commit Hooks

```bash
pre-commit install
```

## Code Style

We follow these guidelines:
- PEP 8 for Python code style
- Type hints for function arguments and returns
- Docstrings for all public functions
- Comments for complex logic
- Maximum line length of 100 characters

Example:
```python
from typing import List, Optional

def process_text(
    text: str,
    max_length: Optional[int] = None,
    *,
    temperature: float = 0.7
) -> List[str]:
    """Process input text with given parameters.

    Args:
        text: Input text to process
        max_length: Maximum length of output (optional)
        temperature: Sampling temperature (default: 0.7)

    Returns:
        List of processed text segments
    """
    # Implementation
```

## Making Changes

1. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Follow code style guidelines
   - Add tests for new features
   - Update documentation

3. **Run Tests**
   ```bash
   # Run all tests
   pytest

   # Run with coverage
   pytest --cov=locallab
   ```

## Testing

### Writing Tests

```python
# tests/test_feature.py
import pytest
from locallab import YourFeature

def test_your_feature():
    feature = YourFeature()
    result = feature.process("test")
    assert result == expected_result

@pytest.mark.asyncio
async def test_async_feature():
    # Test async functionality
    pass
```

### Running Tests

```bash
# Run specific test file
pytest tests/test_feature.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=locallab --cov-report=html
```

## Documentation

### Writing Documentation

- Use clear, concise language
- Include code examples
- Add type hints and docstrings
- Update relevant documentation files

Example:
```python
class ModelManager:
    """Manages AI model loading and inference.

    Attributes:
        current_model: Currently loaded model name
        model_config: Model configuration dictionary
    """

    def __init__(self):
        """Initialize the model manager."""
        self.current_model = None
        self.model_config = {}
```

### Building Documentation

```bash
# Install documentation dependencies
pip install -r docs/requirements.txt

# Build documentation
cd docs
make html
```

## Submitting Changes

1. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

2. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create Pull Request**
   - Go to the [LocalLab repository](https://github.com/Developer-Utkarsh/LocalLab)
   - Click "New Pull Request"
   - Select your branch
   - Fill in the PR template

## Need Help?

- Check our [Troubleshooting Guide](https://github.com/Developer-Utkarsh/LocalLab/blob/main/docs/troubleshooting.md)
- Join our [Discord Community](https://discord.gg/locallab)
- Open an [Issue](https://github.com/Developer-Utkarsh/LocalLab/issues)
