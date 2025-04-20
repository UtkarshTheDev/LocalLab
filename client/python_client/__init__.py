"""
LocalLab Python Client

A Python client for interacting with LocalLab, a local LLM server.

This client provides both asynchronous and synchronous interfaces:

Async usage:
```python
from locallab import LocalLabClient

client = LocalLabClient("http://localhost:8000")
response = await client.generate("Hello, world!")
await client.close()
```

Sync usage:
```python
from locallab import SyncLocalLabClient

client = SyncLocalLabClient("http://localhost:8000")
response = client.generate("Hello, world!")
client.close()
```
"""

from .client import LocalLabClient
from .sync_wrapper import SyncLocalLabClient

__version__ = "0.2.1"
__author__ = "Utkarsh"
__email__ = "utkarshweb2023@gmail.com"

__all__ = [
    "LocalLabClient",
    "SyncLocalLabClient",
]
