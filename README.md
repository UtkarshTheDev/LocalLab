# 🚀 LocalLab: Your Personal AI Lab

[![LocalLab Server](https://img.shields.io/pypi/v/locallab.svg?label=locallab&color=blue)](https://pypi.org/project/locallab/) [![LocalLab Client](https://img.shields.io/pypi/v/locallab-client.svg?label=locallab-client&color=green)](https://pypi.org/project/locallab-client/) [![License](https://img.shields.io/badge/license-Apache%202.0-green)](./LICENSE) [![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)

**Run ChatGPT-like AI on your own computer!** LocalLab is a server that runs AI models locally and makes them accessible from anywhere.

## 🤔 What is LocalLab?

LocalLab is like having your own personal ChatGPT that runs on your computer. Here's how it works:

1. **LocalLab Server**: Runs on your computer and loads AI models
2. **Python Client**: A separate package that connects to the server
3. **Access From Anywhere**: Use your AI from any device with the ngrok feature

No complicated setup, no monthly fees, and your data stays private. Perfect for developers, students, researchers, or anyone who wants to experiment with AI.

## 🧠 How LocalLab Works (In Simple Terms)

Think of LocalLab as having two parts:

1. **The Server** (what you install with `pip install locallab`)

   - This is like a mini-ChatGPT that runs on your computer
   - It loads AI models and makes them available through a web server
   - You start it with a simple command: `locallab start`

2. **The Client** (what you install with `pip install locallab-client`)
   - This is how your Python code talks to the server
   - It's a separate package that connects to the server
   - You use it in your code with: `client = SyncLocalLabClient("http://localhost:8000")`

```mermaid
graph TD
    A[Your Python Code] -->|Uses| B[LocalLab Client Package]
    B -->|Connects to| C[LocalLab Server]
    C -->|Runs| D[AI Models]
    C -->|Optional| E[Ngrok for Remote Access]
    style C fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
```

**The Magic Part**: With the `--use-ngrok` option, you can access your AI from anywhere - your phone, another computer, or share with friends!

### 🎯 Key Features

```
📦 Easy Setup         🔒 Privacy First       🎮 Free GPU Access
🤖 Multiple Models    💾 Memory Efficient    🔄 Auto-Optimization
🌐 Local or Colab    ⚡ Fast Response       🔧 Simple Server
🌍 Access Anywhere   🔌 Client Package      🛡️ Secure Tunneling
```

**Two-Part System**:

- **LocalLab Server**: Runs the AI models and exposes API endpoints
- **LocalLab Client**: A separate Python package (`pip install locallab-client`) that connects to the server

**Access From Anywhere**: With built-in ngrok integration, you can securely access your LocalLab server from any device, anywhere in the world - perfect for teams, remote work, or accessing your models on the go.

### 🌟 Two Ways to Run

1. **On Your Computer (Local Mode)**

   ```
   💻 Your Computer
   └── 🚀 LocalLab Server
       └── 🤖 AI Model
           └── 🔧 Auto-optimization
   ```

2. **On Google Colab (Free GPU Mode)**
   ```
   ☁️ Google Colab
   └── 🎮 Free GPU
       └── 🚀 LocalLab Server
           └── 🤖 AI Model
               └── ⚡ GPU Acceleration
   ```

## 📦 Installation & Setup

> **Latest Package Versions:**
>
> - **LocalLab Server**: [![LocalLab Server](https://img.shields.io/pypi/v/locallab.svg?label=locallab&color=blue)](https://pypi.org/project/locallab/)
> - **LocalLab Client**: [![LocalLab Client](https://img.shields.io/pypi/v/locallab-client.svg?label=locallab-client&color=green)](https://pypi.org/project/locallab-client/)

### Windows Setup

1. **Install Required Build Tools**

   - Install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
     - Select "Desktop development with C++"
   - Install [CMake](https://cmake.org/download/)
     - Add to PATH during installation

2. **Install Packages**

   ```powershell
   pip install locallab locallab-client
   ```

3. **Verify PATH**

   - If `locallab` command isn't found, add Python Scripts to PATH:
     ```powershell
     # Find Python location
     where python
     # This will show something like: C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe
     ```

   **Adding to PATH in Windows:**

   1. Press `Win + X` and select "System"
   2. Click "Advanced system settings" on the right
   3. Click "Environment Variables" button
   4. Under "System variables", find and select "Path", then click "Edit"
   5. Click "New" and add your Python Scripts path (e.g., `C:\Users\YourName\AppData\Local\Programs\Python\Python311\Scripts\`)
   6. Click "OK" on all dialogs
   7. Restart your command prompt

   - Alternatively, use: `python -m locallab start`

> 🔍 Having issues? See our [Windows Troubleshooting Guide](./docs/guides/troubleshooting.md#windows-specific-issues)

### Linux/Mac Setup

```bash
# Install both server and client packages
pip install locallab locallab-client
```

### 2. Configure the Server (Recommended)

```bash
# Run interactive configuration
locallab config

# This will help you set up:
# - Model selection
# - Memory optimizations
# - GPU settings
# - System resources
```

### 3. Start the Server

```bash
# Start with saved configuration
locallab start

# Or start with specific options
locallab start --model microsoft/phi-2 --quantize --quantize-type int8
```

## 💬 CLI Chat Interface

LocalLab includes a powerful terminal-based chat interface that lets you interact with your AI models directly from the command line. Perfect for quick conversations, testing, and interactive AI sessions.

### Quick Start

```bash
# Connect to local server
locallab chat

# Connect to remote server
locallab chat --url https://your-ngrok-url.app

# Use different generation modes
locallab chat --generate chat    # Conversational mode with context
locallab chat --generate batch   # Batch processing mode
locallab chat --generate stream  # Real-time streaming (default)
```

### Features

- **🚀 Multiple Generation Modes**: Stream, Simple, Chat, and Batch processing
- **💬 Rich Terminal UI**: Enhanced markdown rendering and syntax highlighting
- **🔄 Real-time Streaming**: Live response streaming with Server-Sent Events
- **📚 Conversation Management**: History tracking, persistence, and context retention
- **🛠️ Error Handling**: Automatic reconnection and graceful error recovery
- **⚡ Batch Processing**: Process multiple prompts efficiently

### Interactive Commands

```bash
/help     - Show available commands
/history  - Display conversation history
/batch    - Enter batch processing mode
/save     - Save conversation to file
/clear    - Clear the screen
/exit     - Exit gracefully
```

### Example Session

```bash
$ locallab chat
🚀 LocalLab Chat Interface
✅ Connected to: http://localhost:8000
📊 Server: LocalLab v0.9.0 | Model: qwen-0.5b

You: Hello! Can you help me with Python?

AI: Hello! I'd be happy to help you with Python programming.
What specific topic would you like to explore?

You: Show me how to create a class

AI: Here's how to create a simple class in Python:

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def introduce(self):
        return f"Hi, I'm {self.name} and I'm {self.age} years old."

# Usage
person = Person("Alice", 25)
print(person.introduce())
```

You: /exit
👋 Goodbye!
```

> 📖 **Learn More**: See the [CLI Chat Documentation](./docs/cli/chat.md) for complete usage guide and examples.

## 💡 Client Connection & Usage

After starting your LocalLab server (either locally or on Google Colab), you can connect to it in two ways:

1. **CLI Chat Interface** (above) - For interactive terminal conversations
2. **Python Client Package** (below) - For programmatic access in your code

### Synchronous Client Usage (Easier for Beginners)

```python
from locallab_client import SyncLocalLabClient

# Connect to server - choose ONE of these options:
# 1. For local server (default)
client = SyncLocalLabClient("http://localhost:8000")

# 2. For remote server via ngrok (when using Google Colab or --use-ngrok)
# client = SyncLocalLabClient("https://abc123.ngrok.app")  # Replace with your ngrok URL

try:
    print("Generating text...")
    # Generate text
    response = client.generate("Write a story")
    print(response)

    print("Streaming responses...")
    # Stream responses
    for token in client.stream_generate("Tell me a story"):
       print(token, end="", flush=True)

    print("Chat responses...")
    # Chat with AI
    response = client.chat([
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello!"}
    ])
    print(response.choices[0]["message"]["content"])

finally:
    # Always close the client
    client.close()
```

> 💡 **Important**: When connecting to a server running on Google Colab or with ngrok enabled, always use the ngrok URL (https://abc123.ngrok.app) that was displayed when you started the server.

### Asynchronous Client Usage (For Advanced Users)

```python
import asyncio
from locallab_client import LocalLabClient

async def main():
    # Connect to server - choose ONE of these options:
    # 1. For local server (default)
    client = LocalLabClient("http://localhost:8000")

    # 2. For remote server via ngrok (when using Google Colab or --use-ngrok)
    # client = LocalLabClient("https://abc123.ngrok.app")  # Replace with your ngrok URL

    try:
        print("Generating text...")
        # Generate text
        response = await client.generate("Write a story")
        print(response)

        print("Streaming responses...")
        # Stream responses
        async for token in client.stream_generate("Tell me a story"):
            print(token, end="", flush=True)

        print("\nChatting with AI...")
        # Chat with AI
        response = await client.chat([
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello!"}
        ])
        # Extracting Content
        content = response['choices'][0]['message']['content']
        print(content)
    finally:
        # Always close the client
        await client.close()

# Run the async function
asyncio.run(main())
```

## 🌐 Google Colab Usage with Remote Access

### Step 1: Set Up the Server on Google Colab

First, you'll set up the LocalLab server on Google Colab to use their free GPU:

```python
# In your Colab notebook:

# 1. Install the server package
!pip install locallab

# 2. Configure with CLI (notice the ! prefix)
!locallab config

# 3. Start server with ngrok for remote access
!locallab start --use-ngrok

# The server will display a public URL like:
# 🚀 Ngrok Public URL: https://abc123.ngrok.app
# COPY THIS URL - you'll need it to connect!
```

### Step 2: Connect to Your Server

After setting up your server on Google Colab, you'll need to connect to it using the LocalLab client package. The server will display a ngrok URL that you'll use for the connection.

#### Using the Client Connection Examples

**You can now use the client connection examples from the [Client Connection & Usage](#-client-connection--usage) section above.**

Just make sure to:

1. Use your ngrok URL instead of localhost
2. Install the client package if needed

For example:

```python
# In another cell in the same Colab notebook:

# 1. Install the client package
!pip install locallab-client

# 2. Import the client
from locallab_client import SyncLocalLabClient

# 3. Connect to your ngrok URL (replace with your actual URL from Step 1)
client = SyncLocalLabClient("https://abc123.ngrok.app")  # ← REPLACE THIS with your URL!

# 4. Now you can use any of the client methods
response = client.generate("Write a poem about AI")
print(response)

# 5. Always close when done
client.close()
```

#### Access From Any Device

The power of using ngrok is that you can connect to your Colab server from anywhere:

```python
# On your local computer, phone, or any device with Python:
pip install locallab-client

from locallab_client import SyncLocalLabClient
client = SyncLocalLabClient("https://abc123.ngrok.app")  # ← REPLACE THIS with your URL!
response = client.generate("Hello from my device!")
print(response)
client.close()
```

> 💡 **Remote Access Tip**: The ngrok URL lets you access your LocalLab server from any device - your phone, tablet, another computer, or share with teammates. See the [Client Connection & Usage](#-client-connection--usage) section above for more examples of what you can do with the client.

## 💻 Requirements

### Local Computer

- Python 3.8+
- 4GB RAM minimum (8GB+ recommended)
- GPU optional but recommended
- Internet connection for downloading models

### Google Colab

- Just a Google account!
- Free tier works fine

## 🌟 Features

- **Easy Setup**: Just pip install and run
- **Multiple Models**: Use any Hugging Face model
- **Resource Efficient**: Automatic optimization
- **Privacy First**: All local, no data sent to cloud
- **Free GPU**: Google Colab integration
- **Flexible Client API**: Both async and sync clients available
- **Automatic Resource Management**: Sessions close automatically
- **Remote Access**: Access your models from anywhere with ngrok integration
- **Secure Tunneling**: Share your models securely with teammates or access from mobile devices
- **Client Libraries**: Python libraries for both synchronous and asynchronous usage

### 🌍 Client-Server Architecture

```mermaid
graph LR
    A[Your Application] -->|Uses| B[LocalLab Client]
    B -->|API Requests| C[LocalLab Server]
    C -->|Runs| D[AI Models]
    C -->|Optional| E[Ngrok Tunnel]
    E -->|Remote Access| F[Any Device, Anywhere]
    style E fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#bbf,stroke:#333,stroke-width:2px
```

[➡️ See All Features](./docs/features/README.md)

## 📚 Documentation

### Getting Started

1. [Installation Guide](./docs/guides/getting-started.md)
2. [Basic Examples](./docs/guides/examples.md)
3. [CLI Chat Interface](./docs/cli/chat.md)
4. [CLI Usage](./docs/guides/cli.md)

### Advanced Topics

1. [API Reference](./docs/guides/API.md)
2. [Client Libraries](./docs/clients/README.md)
3. [Advanced Features](./docs/guides/advanced.md)
4. [Performance Guide](./docs/features/performance.md)

### Deployment

1. [Local Setup](./docs/deployment/local.md)
2. [Google Colab Guide](./docs/colab/README.md)

## 🔍 Need Help?

- Check [FAQ](./docs/guides/faq.md)
- Visit [Troubleshooting](./docs/guides/troubleshooting.md)
- Ask in [Discussions](https://github.com/UtkarshTheDev/LocalLab/discussions)

## 📖 Additional Resources

- [Contributing Guide](./docs/guides/contributing.md)
- [Changelog](./CHANGELOG.md)
- [License](./LICENSE)

## 🌟 Star Us!

If you find LocalLab helpful, please star our repository! It helps others discover the project.

---

Made with ❤️ by Utkarsh Tiwari
[GitHub](https://github.com/UtkarshTheDev) • [Twitter](https://twitter.com/UtkarshTheDev) • [LinkedIn](https://linkedin.com/in/utkarshthedev)
