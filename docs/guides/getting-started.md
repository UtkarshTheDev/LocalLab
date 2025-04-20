# Getting Started with LocalLab

This guide will help you start using LocalLab, whether you're running it locally or on Google Colab.

## Choose Your Environment

### Local Setup

1. **Install LocalLab**

   ```bash
   pip install locallab
   ```

2. **Start the Server**

   **Using Command Line (Improved in v0.4.8!)**

   ```bash
   # Interactive setup wizard - now with faster startup and better error handling
   locallab start

   # Or with specific options
   locallab start --model microsoft/phi-2 --quantize --quantize-type int8 --attention-slicing

   # Run the configuration wizard without starting the server
   locallab config

   # Check your system resources
   locallab info
   ```

   **Using Python**

   ```python
   from locallab import start_server
   start_server()
   ```

3. **Connect Client**

   First, install the client package:

   ```bash
   pip install locallab-client
   ```

   Then, use the client in your code:

   ```python
   # For async usage
   from locallab_client import LocalLabClient
   client = LocalLabClient("http://localhost:8000")

   # Or for sync usage (no async/await needed)
   from locallab_client import SyncLocalLabClient
   client = SyncLocalLabClient("http://localhost:8000")
   ```

### Google Colab Setup

1. **Install LocalLab**

   ```python
   !pip install locallab
   ```

2. **Set Up Ngrok**

   ```python
   import os
   os.environ["NGROK_AUTH_TOKEN"] = "your_token_here"
   ```

3. **Start Server**

   **Using Interactive Setup (Enhanced in v0.4.8!)**

   ```python
   from locallab import start_server
   # This will prompt for any missing settings, including ngrok token
   # Now with improved error handling and faster startup
   start_server(use_ngrok=True)
   ```

   **Using Manual Configuration**

   ```python
   from locallab import start_server
   start_server(use_ngrok=True)  # Will show public URL in logs
   ```

4. **Connect Client**

   First, install the client package:

   ```bash
   pip install locallab-client
   ```

   Then, use the client in your code:

   ```python
   # For async usage
   from locallab_client import LocalLabClient
   client = LocalLabClient("https://xxxx-xx-xx-xxx-xx.ngrok-free.app")  # Use URL from logs

   # Or for sync usage (no async/await needed)
   from locallab_client import SyncLocalLabClient
   client = SyncLocalLabClient("https://xxxx-xx-xx-xxx-xx.ngrok-free.app")  # Use URL from logs
   ```

## CLI Features (New & Improved in v0.4.8)

LocalLab's command-line interface has been significantly enhanced with:

- **Lightning-Fast Startup**: Optimized for quick response time
- **Robust Error Handling**: Better diagnostics and recovery from common issues
- **Unified Configuration System**: Seamlessly integrates CLI options with environment variables
- **Persistent Settings**: Your configuration is saved in `~/.locallab/config.json`
- **System Information Command**: Get detailed insights about your hardware with `locallab info`

```bash
# Examples of CLI usage

# Start with interactive configuration
locallab start

# Start with specific model and optimizations
locallab start --model microsoft/phi-2 --quantize --quantize-type int8

# Configure without starting
locallab config

# Check system resources
locallab info
```

## First Steps

### 1. Generate Text

```python
# Async usage
from locallab_client import LocalLabClient

async def main():
    client = LocalLabClient("http://localhost:8000")
    try:
        # Simple text generation
        response = await client.generate(
            "Write a story about a robot",
            temperature=0.7
        )
        print(response)
    finally:
        await client.close()

# Sync usage (no async/await needed)
from locallab_client import SyncLocalLabClient

client = SyncLocalLabClient("http://localhost:8000")
try:
    # Simple text generation
    response = client.generate(
        "Write a story about a robot",
        temperature=0.7
    )
    print(response)
finally:
    client.close()
```

### 2. Chat with AI

```python
# Async usage
from locallab_client import LocalLabClient

async def chat_example():
    client = LocalLabClient("http://localhost:8000")
    try:
        # Chat completion
        response = await client.chat([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ])
        print(response["choices"][0]["message"]["content"])
    finally:
        await client.close()

# Sync usage
from locallab_client import SyncLocalLabClient

def sync_chat_example():
    client = SyncLocalLabClient("http://localhost:8000")
    try:
        # Chat completion
        response = client.chat([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ])
        print(response["choices"][0]["message"]["content"])
    finally:
        client.close()
```

### 3. Process Multiple Prompts

```python
# Async usage
from locallab_client import LocalLabClient

async def batch_example():
    client = LocalLabClient("http://localhost:8000")
    try:
        # Batch processing
        responses = await client.batch_generate([
            "Write a haiku",
            "Tell a joke"
        ])
        print(responses)
    finally:
        await client.close()

# Sync usage
from locallab_client import SyncLocalLabClient

def sync_batch_example():
    client = SyncLocalLabClient("http://localhost:8000")
    try:
        # Batch processing
        responses = client.batch_generate([
            "Write a haiku",
            "Tell a joke"
        ])
        print(responses)
    finally:
        client.close()
```

## Next Steps

1. Explore the [CLI Guide](./cli.md) for interactive configuration
2. Check [Advanced Features](./advanced.md) for optimization options
3. Read the [API Reference](./api.md) for detailed endpoint documentation
4. See the [Performance Guide](../features/performance.md) for optimization tips

## Need Help?

- See [FAQ](./faq.md)
- Visit [Troubleshooting](./troubleshooting.md)
- Join our [Community](https://github.com/UtkarshTheDev/LocalLab/discussions)
