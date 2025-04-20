# Unified Client API Guide

The LocalLab Python client now features a unified API that works seamlessly in both synchronous and asynchronous code. This guide explains how to use this powerful new feature.

## Overview

The unified client API allows you to:

1. Use the same client with or without `async`/`await` syntax
2. Switch between sync and async code without changing your client code
3. Automatically manage resources in both modes
4. Use context managers for cleaner code

## How It Works

Under the hood, the client uses a sophisticated dual-mode system that:

1. Detects whether a method is being awaited
2. Runs async code in a background thread when used synchronously
3. Maintains proper error propagation in both modes
4. Ensures resources are properly cleaned up

## Synchronous vs. Asynchronous Usage

### Basic Text Generation

```python
# Initialize the client (same for both modes)
from locallab_client import LocalLabClient
client = LocalLabClient("http://localhost:8000")

# Synchronous usage
response = client.generate("Write a story about a robot")
print(response)
client.close()

# Asynchronous usage
response = await client.generate("Write a story about a robot")
print(response)
await client.close()
```

### Streaming Generation

```python
# Synchronous streaming
for token in client.stream_generate("Write a story about a robot"):
    print(token, end="", flush=True)

# Asynchronous streaming
async for token in client.stream_generate("Write a story about a robot"):
    print(token, end="", flush=True)
```

### Context Managers

```python
# Synchronous context manager
with LocalLabClient("http://localhost:8000") as client:
    response = client.generate("Write a story about a robot")
    print(response)
# Client is automatically closed

# Asynchronous context manager
async with LocalLabClient("http://localhost:8000") as client:
    response = await client.generate("Write a story about a robot")
    print(response)
# Client is automatically closed
```

## Automatic Resource Management

The client now features advanced resource management:

1. **Automatic Session Closing**: Sessions are automatically closed when the client is garbage collected or when the program exits
2. **Activity Tracking**: The client tracks when it was last used and can close inactive sessions
3. **Context Manager Support**: Use `with` or `async with` for automatic resource cleanup

```python
# Sessions are automatically closed when the client is garbage collected
client = LocalLabClient("http://localhost:8000")
response = client.generate("Hello")
# No need to explicitly close the client, though it's still recommended

# Sessions are automatically closed when the program exits
# This prevents resource leaks and warning messages
```

## When to Use Each Mode

### Use Synchronous Mode When:

- You're writing a script or application that doesn't use async/await elsewhere
- You want simpler code without async/await boilerplate
- You're integrating with synchronous frameworks or libraries
- You're new to Python and not familiar with async programming

```python
# Simple synchronous example
from locallab_client import LocalLabClient

client = LocalLabClient("http://localhost:8000")
response = client.generate("Write a story about a robot")
print(response)
client.close()
```

### Use Asynchronous Mode When:

- You're already using async/await in your application
- You need to handle many concurrent operations efficiently
- You're building a high-performance web application
- You want to avoid blocking the main thread during long operations

```python
# Asynchronous example in a web application
async def handle_request(request):
    client = LocalLabClient("http://localhost:8000")
    try:
        response = await client.generate(request.query.get("prompt"))
        return web.Response(text=response)
    finally:
        await client.close()
```

## Performance Considerations

- **Synchronous Mode**: Slightly higher overhead due to thread management
- **Asynchronous Mode**: More efficient for concurrent operations
- **Resource Usage**: Both modes efficiently manage resources
- **Memory Management**: Both modes handle memory similarly

## Best Practices

1. **Use Context Managers**: Prefer `with` or `async with` for automatic resource cleanup
2. **Be Consistent**: Try to use either sync or async mode consistently in a single module
3. **Close Explicitly**: While automatic closing is available, explicitly closing is still good practice
4. **Error Handling**: Always use try/except blocks to handle errors properly

```python
# Best practice with context manager
with LocalLabClient("http://localhost:8000") as client:
    try:
        response = client.generate("Write a story about a robot")
        print(response)
    except Exception as e:
        print(f"Error: {str(e)}")
```

## Migrating from Previous Versions

If you're upgrading from a previous version:

1. You can continue using async/await as before
2. You can gradually migrate to synchronous code where it makes sense
3. You can start using context managers for cleaner resource management

```python
# Old code (still works)
client = LocalLabClient("http://localhost:8000")
try:
    response = await client.generate("Hello")
    print(response)
finally:
    await client.close()

# New code (simpler)
with LocalLabClient("http://localhost:8000") as client:
    response = client.generate("Hello")
    print(response)
```

## Advanced Usage

### Mixing Sync and Async

You can mix synchronous and asynchronous calls in the same application, but it's generally cleaner to be consistent within a single module or function.

```python
# Not recommended but possible
client = LocalLabClient("http://localhost:8000")

# Synchronous call
sync_response = client.generate("Hello")

# Asynchronous call in an async function
async def get_async_response():
    return await client.generate("World")

# Close the client
client.close()  # or await client.close() in an async context
```

### Custom Thread Management

For advanced users, you can control how the client manages its background threads:

```python
from locallab.dual_mode import ThreadManager

# Get the thread manager
thread_manager = ThreadManager.get_instance()

# Manually shut down all background threads
thread_manager.shutdown()
```

## Troubleshooting

### Common Issues

1. **"Event loop is closed" errors**: This can happen if you mix sync and async code incorrectly. Stick to one mode within a function.

2. **Warnings about unclosed clients**: While the client will be closed automatically, it's still best practice to close it explicitly or use a context manager.

3. **Performance issues**: If you're making many rapid requests in synchronous mode, consider switching to asynchronous mode for better performance.

### Solutions

```python
# Fix for "Event loop is closed" errors
import asyncio

# Ensure you have an event loop
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Then use the client normally
client = LocalLabClient("http://localhost:8000")
```

## Conclusion

The unified client API makes LocalLab more accessible and flexible than ever before. Whether you prefer synchronous or asynchronous code, you can now use the same client with the style that works best for your application.
