# Getting Started with LocalLab

This guide will help you start using LocalLab, whether you're new to AI or an experienced developer.

## 🌟 What You'll Need

### For Local Setup
- Python 3.8 or higher installed
- 4GB RAM minimum (8GB+ recommended)
- GPU optional but recommended
- Internet connection for downloading models

### For Google Colab
- Just a Google account!
- Internet connection

## 🚀 Step-by-Step Setup

### Step 1: Install Required Packages

First, you need to install both the server and client packages:

```bash
# Install the server package
pip install locallab

# Install the client package
pip install locallab-client
```

### Step 2: Start the Server

You have two options:

#### Option A: Using Command Line (Recommended for Beginners)
```bash
# Start with interactive setup
locallab start
```
This will:
- Guide you through setup
- Help choose a model
- Configure optimizations
- Start the server

#### Option B: Using Python Code
```python
from locallab import start_server
start_server()
```

### Step 3: Connect with a Client

Choose between async or sync client based on your needs:

#### Synchronous Client (Easier for Beginners)
```python
from locallab_client import SyncLocalLabClient

# Connect to the server
client = SyncLocalLabClient("http://localhost:8000")

try:
    # Generate text
    response = client.generate("Write a story about a robot")
    print(response)
finally:
    # Always close the client when done
    client.close()
```

#### Asynchronous Client (For Advanced Users)
```python
import asyncio
from locallab_client import LocalLabClient

async def main():
    # Connect to the server
    client = LocalLabClient("http://localhost:8000")
    
    try:
        # Generate text
        response = await client.generate("Write a story about a robot")
        print(response)
    finally:
        # Always close the client when done
        await client.close()

# Run the async function
asyncio.run(main())
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
