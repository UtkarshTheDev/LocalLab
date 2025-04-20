# Async/Sync Client Guide

## Table of Contents

- [Overview](#overview)
- [Choosing the Right Client](#choosing-the-right-client)
- [Installation](#installation)
- [Asynchronous Client Example](#asynchronous-client-example)
- [Synchronous Client Example](#synchronous-client-example)
- [Context Manager Support](#context-manager-support)
- [How the Synchronous Client Works](#how-the-synchronous-client-works)
- [Performance Considerations](#performance-considerations)
- [Best Practices](#best-practices)
- [Migrating Between Clients](#migrating-between-clients)
- [Conclusion](#conclusion)

## Overview

The LocalLab Python client (`locallab-client` package) provides two different client classes to interact with the LocalLab server:

1. `LocalLabClient` - An asynchronous client that uses `async`/`await` syntax
2. `SyncLocalLabClient` - A synchronous client that doesn't require `async`/`await`

This guide explains when and how to use each client, with practical examples and best practices.

## Choosing the Right Client

### Use `LocalLabClient` (Async) When:

- You're already using async/await in your application
- You need to handle many concurrent operations efficiently
- You're building a high-performance web application
- You want to avoid blocking the main thread during long operations

### Use `SyncLocalLabClient` (Sync) When:

- You're writing a script or application that doesn't use async/await elsewhere
- You want simpler code without async/await boilerplate
- You're integrating with synchronous frameworks or libraries
- You're new to Python and not familiar with async programming

## Installation

First, install the client package:

```bash
pip install locallab-client
```

## Asynchronous Client Example

```python
import asyncio
from locallab_client import LocalLabClient

async def main():
    # Initialize client
    client = LocalLabClient("http://localhost:8000")

    try:
        # Basic text generation
        response = await client.generate("Write a story about a robot")
        print(response)

        # Streaming text generation
        print("Streaming response: ", end="")
        async for chunk in client.stream_generate("Write a haiku about nature"):
            print(chunk, end="", flush=True)
        print()

        # Chat completion
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
        response = await client.chat(messages)
        print(response["choices"][0]["message"]["content"])

    finally:
        # Always close the client
        await client.close()

# Run the async function
asyncio.run(main())
```

## Synchronous Client Example

```python
from locallab_client import SyncLocalLabClient

# Initialize client
client = SyncLocalLabClient("http://localhost:8000")

try:
    # Basic text generation
    response = client.generate("Write a story about a robot")
    print(response)

    # Streaming text generation
    print("Streaming response: ", end="")
    for chunk in client.stream_generate("Write a haiku about nature"):
        print(chunk, end="", flush=True)
    print()

    # Chat completion
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
    response = client.chat(messages)
    print(response["choices"][0]["message"]["content"])

finally:
    # Always close the client
    client.close()
```

## Context Manager Support

Both clients support context managers for automatic resource cleanup:

### Asynchronous Context Manager

```python
import asyncio
from locallab_client import LocalLabClient

async def main():
    # Use the client as an async context manager
    async with LocalLabClient("http://localhost:8000") as client:
        response = await client.generate("Write a story about a robot")
        print(response)
    # Client is automatically closed when exiting the context

asyncio.run(main())
```

### Synchronous Context Manager

```python
from locallab_client import SyncLocalLabClient

# Use the client as a sync context manager
with SyncLocalLabClient("http://localhost:8000") as client:
    response = client.generate("Write a story about a robot")
    print(response)
# Client is automatically closed when exiting the context
```

## How the Synchronous Client Works

The `SyncLocalLabClient` is a wrapper around the asynchronous `LocalLabClient`. It handles all the async/await details internally by:

1. Running a dedicated event loop in a background thread
2. Converting async calls to synchronous calls by running them in the background thread
3. Providing a synchronous API that matches the asynchronous API

This allows you to use the same functionality without having to deal with async/await syntax.

## Performance Considerations

- **Asynchronous Client**: More efficient for concurrent operations, as it doesn't block the main thread
- **Synchronous Client**: Slightly higher overhead due to thread management, but simpler to use

## Best Practices

1. **Be Consistent**: Choose one client type and stick with it in a single module or application
2. **Close Explicitly**: Always close the client when you're done with it, or use a context manager
3. **Error Handling**: Always use try/except blocks to handle errors properly
4. **Resource Management**: Be mindful of resource usage, especially when creating multiple clients

## Migrating Between Clients

If you need to migrate from one client to the other:

### From Async to Sync:

1. Remove `async`/`await` keywords
2. Replace `LocalLabClient` with `SyncLocalLabClient`
3. Replace `async for` with `for` in streaming operations
4. Remove `asyncio.run()` calls

### From Sync to Async:

1. Add `async`/`await` keywords
2. Replace `SyncLocalLabClient` with `LocalLabClient`
3. Replace `for` with `async for` in streaming operations
4. Wrap your code in an async function and use `asyncio.run()`

## Conclusion

Both clients provide the same functionality with different programming styles. Choose the one that best fits your application's needs and your programming preferences.
