# LocalLab Python Client

The official Python client for LocalLab, providing a simple and powerful interface to interact with your LocalLab server.

## 📦 Installation

```bash
pip install locallab
```

## 🚀 Quick Start

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

## 📚 API Reference

### Client Initialization

```python
from locallab.client import LocalLabClient

client = LocalLabClient(
    base_url: str,
    timeout: float = 30.0
)
```

### Text Generation

#### Basic Generation

```python
response = await client.generate(
    prompt: str,
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = None,
    top_p: float = 0.9
) -> str
```

#### Streaming Generation

```python
async for token in client.stream_generate(
    prompt: str,
    model_id: str = None,
    temperature: float = 0.7,
    max_length: int = None,
    top_p: float = 0.9
):
    print(token, end="", flush=True)
```

### Chat Completion

```python
response = await client.chat(
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
response = await client.chat(messages)
print(response["choices"][0]["message"]["content"])
```

### Batch Generation

```python
responses = await client.batch_generate(
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
responses = await client.batch_generate(prompts)
for prompt, response in zip(prompts, responses["responses"]):
    print(f"\nPrompt: {prompt}")
    print(f"Response: {response}")
```

## 🛠️ Troubleshooting

Common issues and solutions:

1. **Connection Errors**

```python
try:
    await client.generate("Test")
except ConnectionError as e:
    print("Server not running:", str(e))
```

2. **Timeout Handling**

```python
client = LocalLabClient(
    "http://localhost:8000",
    timeout=60.0
)
```

3. **Memory Management**

```python
async def memory_warning(usage: float):
    print(f"High memory usage: {usage}%")
    await client.unload_model()

client.on_memory_warning = memory_warning
```

## 📚 Additional Resources

- [Type Hints](./type_hints.md)
- [Error Codes](./errors.md)
- [Best Practices](./best-practices.md)
- [Migration Guide](./migration.md)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Run tests: `pytest`
4. Submit a pull request

## 📝 License

MIT License - see [LICENSE](../../LICENSE) for details.
