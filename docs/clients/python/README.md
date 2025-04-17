# LocalLab Python Client

The official Python client for LocalLab, providing a simple and powerful interface to interact with your LocalLab server.

## 📦 Installation

```bash
pip install locallab
```

## 🚀 Quick Start

### Synchronous Usage (New!)

```python
from locallab.client import LocalLabClient

# Initialize client
client = LocalLabClient("http://localhost:8000")

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

```python
import asyncio
from locallab.client import LocalLabClient

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

### Context Manager Support (New!)

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

## 📚 API Reference

### Client Initialization

```python
from locallab.client import LocalLabClient

client = LocalLabClient(
    base_url: str,
    timeout: float = 30.0,
    auto_close: bool = True  # New! Automatically close inactive sessions
)
```

> **New Feature**: The client now automatically closes inactive sessions and supports both synchronous and asynchronous usage patterns. You can use the same client with or without `async`/`await` keywords.

### Text Generation

#### Basic Generation

```python
# Async usage
response = await client.generate(
    prompt: str,
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = None,
    top_p: float = 0.9
) -> str

# Sync usage (New!)
response = client.generate(
    prompt: str,
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = None,
    top_p: float = 0.9
) -> str
```

#### Streaming Generation

```python
# Async usage
async for token in client.stream_generate(
    prompt: str,
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = None,
    top_p: float = 0.9,
    timeout: float = 60.0  # New! Control request timeout
):
    print(token, end="", flush=True)

# Sync usage (New!)
for token in client.stream_generate(
    prompt: str,
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = None,
    top_p: float = 0.9,
    timeout: float = 60.0
):
    print(token, end="", flush=True)
```

### Chat Completion

```python
# Async usage
response = await client.chat(
    messages: list[dict],
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = None,
    top_p: float = 0.9
) -> dict

# Sync usage (New!)
response = client.chat(
    messages: list[dict],
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = None,
    top_p: float = 0.9
) -> dict
```

Example:

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
]

# Async usage
response = await client.chat(messages)
print(response["choices"][0]["message"]["content"])

# Sync usage (New!)
response = client.chat(messages)
print(response["choices"][0]["message"]["content"])
```

### Batch Generation

```python
# Async usage
responses = await client.batch_generate(
    prompts: list[str],
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = None,
    top_p: float = 0.9
) -> dict

# Sync usage (New!)
responses = client.batch_generate(
    prompts: list[str],
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = None,
    top_p: float = 0.9
) -> dict
```

Example:

```python
prompts = [
    "Write a haiku",
    "Tell a joke",
    "Give a fun fact"
]

# Async usage
responses = await client.batch_generate(prompts)
for prompt, response in zip(prompts, responses["responses"]):
    print(f"\nPrompt: {prompt}")
    print(f"Response: {response}")

# Sync usage (New!)
responses = client.batch_generate(prompts)
for prompt, response in zip(prompts, responses["responses"]):
    print(f"\nPrompt: {prompt}")
    print(f"Response: {response}")
```

## 🛠️ Troubleshooting

Common issues and solutions:

1. **Connection Errors**

```python
# Async usage
try:
    await client.generate("Test")
except ConnectionError as e:
    print("Server not running:", str(e))

# Sync usage (New!)
try:
    client.generate("Test")
except ConnectionError as e:
    print("Server not running:", str(e))
```

2. **Timeout Handling**

```python
# For client initialization
client = LocalLabClient(
    "http://localhost:8000",
    timeout=60.0
)

# For streaming requests
for token in client.stream_generate("Hello", timeout=120.0):
    print(token, end="")
```

3. **Memory Management**

```python
# Async usage
async def memory_warning(usage: float):
    print(f"High memory usage: {usage}%")
    await client.unload_model()

client.on_memory_warning = memory_warning

# Sync usage (New!)
def memory_warning(usage: float):
    print(f"High memory usage: {usage}%")
    client.unload_model()

client.on_memory_warning = memory_warning
```

4. **Automatic Session Closing (New!)**

```python
# Sessions are automatically closed when the client is garbage collected
# or when the program exits, but you can still close them explicitly:

# Async usage
await client.close()

# Sync usage
client.close()

# Or use context managers for automatic closing:
with LocalLabClient("http://localhost:8000") as client:
    # Do something with the client
    pass  # Session is automatically closed when exiting the block
```

## 📚 Additional Resources

- [Type Hints](./type_hints.md)
- [Error Codes](./errors.md)
- [Best Practices](./best-practices.md)
- [Migration Guide](./migration.md)
- [Unified Client API Guide](./unified-client.md) (New!)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Run tests: `pytest`
4. Submit a pull request

## 📝 License

MIT License - see [LICENSE](../../LICENSE) for details.
