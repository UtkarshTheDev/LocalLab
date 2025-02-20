# LocalLab Python Client

Official Python client for LocalLab - A local LLM server.

## Features

- 🚀 Async/await API
- 📊 Batch processing
- 🌊 Streaming support
- 💬 Chat completion
- 🔍 Model management
- 📈 System monitoring
- 🔒 Type-safe with Pydantic
- 🌐 WebSocket support

## Installation

```bash
pip install locallab-client
# or
poetry add locallab-client
```

## Quick Start

```python
import asyncio
from locallab.client import LocalLabClient

async def main():
    # Initialize client
    client = LocalLabClient({
        "base_url": "http://localhost:8000",
        "api_key": "your-api-key",  # Optional
    })

    try:
        # Basic generation
        response = await client.generate("Hello, how are you?")
        print(response.response)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Usage Examples

### Text Generation

```python
# Basic generation
response = await client.generate("Hello, how are you?")
print(response.response)

# Generation with options
response = await client.generate("Hello", {
    "temperature": 0.7,
    "max_length": 100,
})

# Streaming generation
async for token in client.stream_generate("Tell me a story"):
    print(token, end="", flush=True)
```

### Chat Completion

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"},
]

response = await client.chat(messages)
print(response.choices[0].message.content)
```

### Batch Processing

```python
prompts = [
    "What is 2+2?",
    "Who wrote Romeo and Juliet?",
    "What is the speed of light?",
]

response = await client.batch_generate(prompts)
for i, answer in enumerate(response.responses, 1):
    print(f"{i}. {answer}")
```

### Model Management

```python
# List available models
models = await client.list_models()
print(models)

# Load a specific model
await client.load_model("mistral-7b")

# Get current model info
current_model = await client.get_current_model()
print(current_model)
```

### System Monitoring

```python
# Get system information
system_info = await client.get_system_info()
print(f"CPU Usage: {system_info.cpu_usage}%")
print(f"Memory Usage: {system_info.memory_usage}%")
if system_info.gpu_info:
    print(f"GPU: {system_info.gpu_info.device}")

# Check system health
is_healthy = await client.health_check()
print(is_healthy)
```

### WebSocket Connection

```python
# Connect to WebSocket
await client.connect_ws()

# Subscribe to messages
async def message_handler(data):
    print("Received:", data)

await client.on_message(message_handler)

# Disconnect when done
await client.disconnect_ws()
```

## API Reference

### Client Configuration

```python
class LocalLabConfig(BaseModel):
    base_url: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    retries: int = 3
    headers: Dict[str, str] = Field(default_factory=dict)
```

### Generation Options

```python
class GenerateOptions(BaseModel):
    model_id: Optional[str] = None
    max_length: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stream: bool = False
```

### Response Types

```python
class GenerateResponse(BaseModel):
    response: str
    model_id: str
    usage: Usage

class ChatResponse(BaseModel):
    choices: List[ChatChoice]
    usage: Usage
```

## Error Handling

The client throws typed exceptions that you can catch and handle:

```python
try:
    await client.generate("Hello")
except ValidationError as e:
    print("Validation error:", e.field_errors)
except RateLimitError as e:
    print(f"Rate limit exceeded. Retry after {e.retry_after}s")
except LocalLabError as e:
    print(f"Error {e.code}: {e.message}")
```

## Development

### Installation

```bash
# Install dependencies
pip install -e ".[dev]"
```

### Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=locallab
```

### Linting

```bash
# Run linters
flake8 locallab
mypy locallab
```

### Formatting

```bash
# Format code
black locallab
isort locallab
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
