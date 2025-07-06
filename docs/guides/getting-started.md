# Getting Started with LocalLab

Welcome to LocalLab! This guide will get you up and running with your own personal AI assistant in just a few minutes.

## 🎯 What You'll Get

After following this guide, you'll have:

- ✅ **Your own ChatGPT** running locally on your computer
- ✅ **Terminal chat interface** for easy AI interactions
- ✅ **Python client** for building AI-powered applications
- ✅ **Remote access** capability to use your AI from anywhere

## 🚀 Quick Start (3 Steps)

```bash
# 1. Install LocalLab
pip install locallab locallab-client

# 2. Start your AI server
locallab start

# 3. Chat with your AI
locallab chat
```

That's it! You now have your own AI assistant running locally.

## 🌟 System Requirements

### For Local Setup

- **Python 3.8+** installed
- **4GB RAM** minimum (8GB+ recommended)
- **GPU** optional but recommended for faster responses
- **Internet** connection for downloading models

### For Google Colab (Free GPU!)

- Just a **Google account**
- **Internet** connection

### Additional Windows Requirements

- **Microsoft C++ Build Tools** (for some dependencies)
- **CMake** (for model compilation)
- **Python added to PATH**

## 🚀 Installation Guide

### Option 1: Windows Setup

1. **Install Build Tools** (Required for Windows)

   ```powershell
   # Download and install Microsoft C++ Build Tools
   # From: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   # Select "Desktop development with C++"

   # Download and install CMake
   # From: https://cmake.org/download/
   # ✅ Check "Add to PATH" during installation
   ```

2. **Install LocalLab**

   ```powershell
   # Install both packages
   pip install locallab locallab-client
   ```

3. **Verify Installation**

   ```powershell
   # Test the CLI
   locallab --help

   # If command not found, add Python Scripts to PATH
   # Usually: C:\Users\YourName\AppData\Local\Programs\Python\Python311\Scripts\
   ```

### Option 2: Linux/Mac Setup

```bash
# Simple one-line installation
pip install locallab locallab-client

# Verify installation
locallab --help
```

## 🎉 First Time Setup

After installation, follow these steps to get your AI assistant running:

### Step 1: Configure LocalLab

```bash
# Run the interactive configuration wizard
locallab config
```

This wizard will help you:
- **Choose a model** (e.g., microsoft/phi-2 for beginners)
- **Set memory optimizations** (quantization, etc.)
- **Configure system resources** (CPU/GPU usage)
- **Set up remote access** (optional ngrok)

### Step 2: Start Your AI Server

```bash
# Start with your saved configuration
locallab start
```

You'll see output like:
```
🚀 LocalLab Server Starting...
📦 Loading model: microsoft/phi-2
✅ Server running at: http://localhost:8000
🎯 Ready for connections!
```

### Step 3: Chat with Your AI

Open a new terminal and start chatting:

```bash
# Open the chat interface
locallab chat
```

You'll see:
```
🚀 LocalLab Chat Interface
✅ Connected to: http://localhost:8000
📊 Server: LocalLab v0.9.0 | Model: microsoft/phi-2

You: Hello! Can you help me with Python?

AI: Hello! I'd be happy to help you with Python programming.
What specific topic would you like to explore?
```

### 🎯 You're Ready!

Congratulations! You now have:
- ✅ Your own AI assistant running locally
- ✅ A ChatGPT-like chat interface
- ✅ Complete privacy (everything runs on your computer)
- ✅ Zero ongoing costs

## 💡 What's Next?

### Try Different Features

```bash
# Use different generation modes
You: Write a story --stream        # Real-time streaming
You: Remember my name is Alice --chat  # Conversational mode

# Use interactive commands
/help      # Show all commands
/history   # View conversation history
/save      # Save your conversation
/batch     # Process multiple prompts
```

### Connect from Other Devices

```bash
# Start server with remote access
locallab start --use-ngrok

# Connect from any device
locallab chat --url https://abc123.ngrok.app
```
- GPU settings
- System resources

#### Option B: Using Python Code

```python
from locallab.cli.config import set_config_value, save_config
from locallab.cli.interactive import prompt_for_config

# Method 1: Interactive Configuration
config = prompt_for_config()
save_config(config)

# Method 2: Direct Configuration
set_config_value("model_id", "microsoft/phi-2")
set_config_value("enable_quantization", True)
set_config_value("quantization_type", "int8")
set_config_value("enable_attention_slicing", True)
```

### Start the Server

After configuring, you can start the server:

#### Option A: Using Command Line

```bash
# Start with saved configuration
locallab start

# Or start with specific options
locallab start --model microsoft/phi-2 --quantize --quantize-type int8
```

#### Option B: Using Python Code

```python
from locallab import start_server

# Start with saved configuration
start_server()

# Or start with specific options
start_server(
    model_id="microsoft/phi-2",
    enable_quantization=True,
    quantization_type="int8"
)
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
3. Read the [API Reference](./API.md) for detailed endpoint documentation
4. See the [Performance Guide](../features/performance.md) for optimization tips

## Need Help?

- See [FAQ](./faq.md)
- Visit [Troubleshooting](./troubleshooting.md)
- Join our [Community](https://github.com/UtkarshTheDev/LocalLab/discussions)
