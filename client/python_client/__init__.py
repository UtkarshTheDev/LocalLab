"""
LocalLab Python Client

A Python client for interacting with LocalLab, a local LLM server.

This client can be used both synchronously and asynchronously:

Async usage:
```python
client = LocalLabClient("http://localhost:8000")
response = await client.generate("Hello, world!")
await client.close()
```

Sync usage:
```python
client = LocalLabClient("http://localhost:8000")
response = client.generate("Hello, world!")
client.close()
```
"""

from .client import LocalLabClient

__version__ = "0.2.0"
__author__ = "Utkarsh"
__email__ = "utkarshweb2023@gmail.com"

__all__ = [
    "LocalLabClient",
]
