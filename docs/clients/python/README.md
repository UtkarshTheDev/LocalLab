# LocalLab Python Client

The official Python client for LocalLab, providing a simple and powerful interface to interact with your LocalLab server.

## Table of Contents

- [Installation](#-installation)
- [Quick Start](#-quick-start)
  - [Synchronous Usage](#synchronous-usage)
  - [Asynchronous Usage](#asynchronous-usage)
  - [Context Manager Support](#context-manager-support)
- [API Reference](#-api-reference)
  - [Client Initialization](#client-initialization)
  - [Text Generation](#text-generation)
  - [Chat Completion](#chat-completion)
  - [Batch Generation](#batch-generation)
- [Troubleshooting](#-troubleshooting)
- [Additional Resources](#-additional-resources)

## 📦 Installation

Install the client package:

```bash
pip install locallab-client
```

> **Note**: The package name is `locallab-client` but the import is `locallab_client` (with an underscore)

## 🚀 Quick Start

The LocalLab client provides two different client classes:

1. `LocalLabClient` - An asynchronous client that uses `async`/`await` syntax
2. `SyncLocalLabClient` - A synchronous client that doesn't require `async`/`await`

Choose the one that best fits your needs.

### Synchronous Usage

Use `SyncLocalLabClient` when you don't want to use async/await:

```python
from locallab_client import SyncLocalLabClient

# Initialize client
client = SyncLocalLabClient("http://localhost:8000")

try:
    # Basic text generation - no async/await needed!
    response = client.generate("Write a story about a robot")
    print(response)
except Exception as e:
    print(f"Generation failed: {str(e)}")
finally:
    # Close the client - no async/await needed!
    client.close()
```

### Asynchronous Usage

Use `LocalLabClient` when you're working with async code:

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
    except Exception as e:
        print(f"Generation failed: {str(e)}")
    finally:
        await client.close()

# Run the async function
asyncio.run(main())
```

### Context Manager Support

Both clients support context managers for automatic resource cleanup:

```python
# Import the clients
from locallab_client import SyncLocalLabClient, LocalLabClient

# Synchronous context manager
with SyncLocalLabClient("http://localhost:8000") as client:
    response = client.generate("Write a story about a robot")
    print(response)
# Client is automatically closed

# Asynchronous context manager
async with LocalLabClient("http://localhost:8000") as client:
    response = await client.generate("Write a story about a robot")
    print(response)
# Client is automatically closed
```

> **See Also**: For more details, check the [Async/Sync Client Guide](./async-sync-guide.md)

## 📚 API Reference

### Client Initialization

#### Asynchronous Client

```python
from locallab_client import LocalLabClient

client = LocalLabClient(
    base_url: str,
    timeout: float = 30.0,
    auto_close: bool = True  # Automatically close inactive sessions
)

# Note: The package name is 'locallab-client' but the import is 'locallab_client'
# pip install locallab-client
```

#### Synchronous Client

```python
from locallab_client import SyncLocalLabClient

client = SyncLocalLabClient(
    base_url: str,
    timeout: float = 30.0
)

# Note: The package name is 'locallab-client' but the import is 'locallab_client'
# pip install locallab-client
```

> **Feature**: Both clients automatically close inactive sessions and provide proper resource management. The synchronous client handles all the async/await details internally.

### Text Generation

#### Basic Generation

```python
# Async usage with LocalLabClient
response = await client.generate(
    prompt: str,
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = 8192,  # Default is 8192 tokens for complete responses
    top_p: float = 0.9,
    top_k: int = 80,  # Limits vocabulary to top K tokens
    repetition_penalty: float = 1.15,  # Reduces repetition
    timeout: float = 180.0  # 3 minutes timeout for complete responses
) -> str

# Sync usage with SyncLocalLabClient
response = client.generate(
    prompt: str,
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = 8192,  # Default is 8192 tokens for complete responses
    top_p: float = 0.9,
    top_k: int = 80,  # Limits vocabulary to top K tokens
    repetition_penalty: float = 1.15,  # Reduces repetition
    timeout: float = 180.0  # 3 minutes timeout for complete responses
) -> str
```

#### Response Quality Parameters

The client now supports advanced response quality parameters:

| Parameter            | Default | Description                                                          |
| -------------------- | ------- | -------------------------------------------------------------------- |
| `max_length`         | 8192    | Maximum number of tokens in the generated response                   |
| `temperature`        | 0.7     | Controls randomness (higher = more creative, lower = more focused)   |
| `top_p`              | 0.9     | Nucleus sampling parameter (higher = more diverse responses)         |
| `top_k`              | 80      | Limits vocabulary to top K tokens (higher = more diverse vocabulary) |
| `repetition_penalty` | 1.15    | Penalizes repetition (higher = less repetition)                      |
| `timeout`            | 180.0   | Maximum time in seconds allowed for generation                       |

These parameters work together to produce high-quality, complete responses that are both relevant and diverse, with minimal repetition.

#### Streaming Generation

```python
# Async usage with LocalLabClient
async for token in client.stream_generate(
    prompt: str,
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = 8192,  # Default is 8192 tokens for complete responses
    top_p: float = 0.9,
    top_k: int = 80,  # Limits vocabulary to top K tokens
    repetition_penalty: float = 1.15,  # Reduces repetition
    timeout: float = 300.0  # 5 minutes timeout for streaming
):
    print(token, end="", flush=True)

# Sync usage with SyncLocalLabClient
for token in client.stream_generate(
    prompt: str,
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = 8192,  # Default is 8192 tokens for complete responses
    top_p: float = 0.9,
    top_k: int = 80,  # Limits vocabulary to top K tokens
    repetition_penalty: float = 1.15,  # Reduces repetition
    timeout: float = 300.0  # 5 minutes timeout for streaming
):
    print(token, end="", flush=True)
```

### Chat Completion

```python
# Async usage with LocalLabClient
response = await client.chat(
    messages: list[dict],
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = 8192,  # Default is 8192 tokens for complete responses
    top_p: float = 0.9,
    top_k: int = 80,  # Limits vocabulary to top K tokens
    repetition_penalty: float = 1.15,  # Reduces repetition
    timeout: float = 180.0  # 3 minutes timeout for complete responses
) -> dict

# Sync usage with SyncLocalLabClient
response = client.chat(
    messages: list[dict],
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = 8192,  # Default is 8192 tokens for complete responses
    top_p: float = 0.9,
    top_k: int = 80,  # Limits vocabulary to top K tokens
    repetition_penalty: float = 1.15,  # Reduces repetition
    timeout: float = 180.0  # 3 minutes timeout for complete responses
) -> dict
```

#### Streaming Chat

```python
# Async usage with LocalLabClient
async for chunk in client.stream_chat(
    messages: list[dict],
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = 8192,  # Default is 8192 tokens for complete responses
    top_p: float = 0.9,
    top_k: int = 80,  # Limits vocabulary to top K tokens
    repetition_penalty: float = 1.15,  # Reduces repetition
    timeout: float = 300.0  # 5 minutes timeout for streaming
):
    if "content" in chunk:
        print(chunk["content"], end="", flush=True)

# Sync usage with SyncLocalLabClient
for chunk in client.stream_chat(
    messages: list[dict],
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = 8192,  # Default is 8192 tokens for complete responses
    top_p: float = 0.9,
    top_k: int = 80,  # Limits vocabulary to top K tokens
    repetition_penalty: float = 1.15,  # Reduces repetition
    timeout: float = 300.0  # 5 minutes timeout for streaming
):
    if "content" in chunk:
        print(chunk["content"], end="", flush=True)
```

#### Example

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
]

# Async usage with LocalLabClient
response = await client.chat(messages)
print(response["choices"][0]["message"]["content"])

# Sync usage with SyncLocalLabClient
response = client.chat(messages)
print(response["choices"][0]["message"]["content"])
```

### Batch Generation

```python
# Async usage with LocalLabClient
responses = await client.batch_generate(
    prompts: list[str],
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = 8192,  # Default is 8192 tokens for complete responses
    top_p: float = 0.9,
    top_k: int = 80,  # Limits vocabulary to top K tokens
    repetition_penalty: float = 1.15,  # Reduces repetition
    timeout: float = 300.0  # 5 minutes timeout for batch operations
) -> dict

# Sync usage with SyncLocalLabClient
responses = client.batch_generate(
    prompts: list[str],
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = 8192,  # Default is 8192 tokens for complete responses
    top_p: float = 0.9,
    top_k: int = 80,  # Limits vocabulary to top K tokens
    repetition_penalty: float = 1.15,  # Reduces repetition
    timeout: float = 300.0  # 5 minutes timeout for batch operations
) -> dict
```

#### Example

```python
prompts = [
    "Write a haiku",
    "Tell a joke",
    "Give a fun fact"
]

# Async usage with LocalLabClient
responses = await client.batch_generate(prompts)
for prompt, response in zip(prompts, responses["responses"]):
    print(f"\nPrompt: {prompt}")
    print(f"Response: {response}")

# Sync usage with SyncLocalLabClient
responses = client.batch_generate(prompts)
for prompt, response in zip(prompts, responses["responses"]):
    print(f"\nPrompt: {prompt}")
    print(f"Response: {response}")
```

#### Using Default Parameters

All generation methods work with sensible defaults, so you can use them without specifying any parameters:

```python
# Simple generation with all default parameters
response = client.generate("Explain quantum computing")

# Simple chat with all default parameters
messages = [{"role": "user", "content": "Hello, how are you?"}]
response = client.chat(messages)

# Simple batch generation with all default parameters
responses = client.batch_generate(["Write a poem", "Tell a story"])
```

The client will automatically use the optimal parameters for high-quality responses.

## 🛠️ Troubleshooting

### Common Issues and Solutions

#### 1. Connection Errors

If you can't connect to the server, make sure it's running and accessible:

```python
# Async usage with LocalLabClient
try:
    await client.generate("Test")
except ConnectionError as e:
    print("Server not running:", str(e))

# Sync usage with SyncLocalLabClient
try:
    client.generate("Test")
except ConnectionError as e:
    print("Server not running:", str(e))
```

#### 2. Timeout Handling

For slow responses or large generations, increase the timeout:

```python
# For async client initialization
client = LocalLabClient(
    "http://localhost:8000",
    timeout=60.0  # 60 seconds timeout for connection
)

# For sync client initialization
client = SyncLocalLabClient(
    "http://localhost:8000",
    timeout=60.0  # 60 seconds timeout for connection
)

# For individual requests (recommended approach)
response = client.generate(
    "Write a detailed essay on quantum computing",
    max_length=8192,
    timeout=300.0  # 5 minutes timeout for this specific request
)

# For streaming requests
for token in client.stream_generate(
    "Write a detailed essay on quantum computing",
    max_length=8192,
    timeout=300.0  # 5 minutes timeout for streaming
):
    print(token, end="")
```

> **Note**: The `timeout` parameter in the client initialization controls the connection timeout, while the `timeout` parameter in the generation methods controls the request timeout. For long generations, it's recommended to use a higher timeout in the generation methods.

#### 3. Memory Management

For low-resource environments, unload models when not in use:

```python
# Async usage with LocalLabClient
async def memory_warning(usage: float):
    print(f"High memory usage: {usage}%")
    await client.unload_model()

client.on_memory_warning = memory_warning

# Sync usage with SyncLocalLabClient
def memory_warning(usage: float):
    print(f"High memory usage: {usage}%")
    client.unload_model()

client.on_memory_warning = memory_warning
```

#### 4. Resource Management

Always close clients when done to prevent resource leaks:

```python
# Sessions are automatically closed when the client is garbage collected
# or when the program exits, but you should still close them explicitly:

# Async usage with LocalLabClient
await client.close()

# Sync usage with SyncLocalLabClient
client.close()

# Or better yet, use context managers for automatic closing:

# Async context manager
async with LocalLabClient("http://localhost:8000") as client:
    # Do something with the client
    pass  # Session is automatically closed when exiting the block

# Sync context manager
with SyncLocalLabClient("http://localhost:8000") as client:
    # Do something with the client
    pass  # Session is automatically closed when exiting the block
```

#### 5. Package Installation Issues

If you encounter import errors, make sure you've installed the correct package:

```bash
pip install locallab-client
```

And import it correctly:

```python
# The package name is 'locallab-client' but the import is 'locallab_client'
from locallab_client import LocalLabClient
from locallab_client import SyncLocalLabClient
```

## 📚 Additional Resources

- [Type Hints](./type_hints.md)
- [Error Codes](./errors.md)
- [Best Practices](./best-practices.md)
- [Migration Guide](./migration.md)
- [Async/Sync Client Guide](./async-sync-guide.md)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Run tests: `pytest`
4. Submit a pull request

## 📝 License

MIT License - see [LICENSE](../../LICENSE) for details.
