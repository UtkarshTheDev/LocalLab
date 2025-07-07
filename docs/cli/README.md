# LocalLab CLI Documentation

Welcome to the LocalLab Command Line Interface documentation! The LocalLab CLI provides powerful tools for running AI models locally and interacting with them through various interfaces.

## 🚀 Quick Start

```bash
# Install LocalLab
pip install locallab locallab-client

# Configure your setup (recommended)
locallab config

# Start the server
locallab start

# Chat with your AI
locallab chat
```

## 📋 Available Commands

### Core Commands

| Command | Description | Documentation |
|---------|-------------|---------------|
| `locallab start` | Start the LocalLab server | [CLI Guide](../guides/cli.md#start-server) |
| `locallab config` | Interactive configuration wizard | [CLI Guide](../guides/cli.md#configure-settings) |
| `locallab chat` | Terminal-based chat interface | [Chat Documentation](./chat.md) |
| `locallab stop` | Stop the running server | [CLI Guide](../guides/cli.md#stop-server) |
| `locallab status` | Check server status | [CLI Guide](../guides/cli.md#check-status) |

### Management Commands

| Command | Description | Documentation |
|---------|-------------|---------------|
| `locallab models list` | List locally cached models | [Model Management](../guides/model-management.md#list-models) |
| `locallab models download <model_id>` | Download a model locally | [Model Management](../guides/model-management.md#download-models) |
| `locallab models remove <model_id>` | Remove a cached model | [Model Management](../guides/model-management.md#remove-models) |
| `locallab models discover` | Discover available models | [Model Management](../guides/model-management.md#discover-models) |
| `locallab models info <model_id>` | Show detailed model information | [Model Management](../guides/model-management.md#model-info) |
| `locallab models clean` | Clean up orphaned cache files | [Model Management](../guides/model-management.md#cache-cleanup) |
| `locallab logs` | View server logs | [CLI Guide](../guides/cli.md#view-logs) |
| `locallab version` | Show version information | [CLI Guide](../guides/cli.md#version) |

## 💬 Chat Interface - The Star Feature

The LocalLab chat interface is a powerful terminal-based tool that lets you interact with your AI models directly from the command line.

### Key Features

- **🎯 Multiple Generation Modes**: Stream, Chat, Simple, and Batch processing
- **🔄 Real-time Streaming**: Live response generation with Server-Sent Events
- **💬 Conversation Management**: History tracking, saving, and loading
- **🎨 Rich Terminal UI**: Markdown rendering with syntax highlighting
- **⚡ Dynamic Mode Switching**: Change modes per message with `--stream`, `--chat`, etc.
- **🛠️ Error Handling**: Automatic reconnection and graceful recovery
- **📦 Batch Processing**: Process multiple prompts efficiently

### Quick Chat Examples

```bash
# Basic chat session
locallab chat

# Connect to remote server
locallab chat --url https://your-ngrok-url.app

# Use specific generation mode
locallab chat --generate chat

# Custom parameters
locallab chat --max-tokens 200 --temperature 0.8
```

### Dynamic Mode Switching

Override the default mode for any message:

```bash
You: Explain quantum physics --stream
🔄 Using stream mode for this message

You: Remember my name is Alice --chat  
🔄 Using chat mode for this message

You: What's 2+2? --simple
🔄 Using simple mode for this message
```

**[📖 Complete Chat Documentation →](./chat.md)**

## 🔧 Server Management

### Starting Your Server

```bash
# Start with saved configuration
locallab start

# Start with specific options
locallab start --model microsoft/phi-2 --port 8000

# Start with ngrok for remote access
locallab start --use-ngrok

# Start with GPU acceleration
locallab start --device cuda --quantize
```

### Configuration Management

```bash
# Run interactive configuration
locallab config

# View current configuration
locallab config --show

# Reset to defaults
locallab config --reset
```

## 🌐 Remote Access with Ngrok

LocalLab supports secure remote access through ngrok tunneling:

```bash
# Start server with ngrok
locallab start --use-ngrok

# Chat with remote server
locallab chat --url https://abc123.ngrok.app
```

This allows you to:
- Access your AI from any device
- Share your models with teammates
- Run on Google Colab and connect from anywhere

## 📚 Documentation Structure

```
docs/
├── cli/
│   ├── README.md          ← You are here
│   └── chat.md           ← Complete chat interface guide
├── guides/
│   ├── getting-started.md ← Installation and setup
│   ├── cli.md            ← Detailed CLI reference
│   └── troubleshooting.md ← Common issues and solutions
└── api/
    └── README.md         ← API documentation
```

## 🎯 Common Use Cases

### 1. Quick AI Chat
```bash
locallab start
locallab chat
```

### 2. Development Testing
```bash
locallab start --model microsoft/phi-2
locallab chat --generate simple
```

### 3. Remote AI Access
```bash
# On your server/Colab
locallab start --use-ngrok

# From any device
locallab chat --url https://your-ngrok-url.app
```

### 4. Batch Processing
```bash
locallab chat --generate batch
# Then use /batch command for multiple prompts
```

## 🔍 Getting Help

### Command Help
```bash
# General help
locallab --help

# Command-specific help
locallab start --help
locallab chat --help
locallab config --help
```

### Interactive Help
```bash
# In chat interface
/help

# Show available commands and syntax
```

### Documentation Links

- **[Getting Started Guide](../guides/getting-started.md)** - Installation and first steps
- **[CLI Reference](../guides/cli.md)** - Complete command documentation  
- **[Chat Interface](./chat.md)** - Detailed chat features and examples
- **[Troubleshooting](../guides/troubleshooting.md)** - Common issues and solutions

## 🚀 Next Steps

1. **[Install LocalLab](../guides/getting-started.md)** - Get up and running
2. **[Try the Chat Interface](./chat.md)** - Experience interactive AI
3. **[Explore Advanced Features](../guides/cli.md)** - Dive deeper into CLI capabilities
4. **[Set Up Remote Access](../guides/getting-started.md#google-colab-usage)** - Access from anywhere

---

**Need help?** Check our [troubleshooting guide](../guides/troubleshooting.md) or open an issue on GitHub.
