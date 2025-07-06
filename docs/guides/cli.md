# LocalLab CLI Guide

LocalLab provides a comprehensive command-line interface (CLI) that makes it easy to run AI models locally and interact with them. This guide covers all CLI features from basic server management to the powerful chat interface.

## 🚀 Quick Start

```bash
# Install LocalLab
pip install locallab locallab-client

# Configure your setup
locallab config

# Start the server
locallab start

# Chat with your AI
locallab chat
```

## 📚 Table of Contents

1. [Installation](#installation)
2. [Chat Interface](#chat-interface) ⭐ **Most Popular**
3. [Server Management](#server-management)
4. [Interactive Configuration](#interactive-configuration)
5. [Command Reference](#command-reference)
6. [Environment Variables](#environment-variables)
7. [Configuration Storage](#configuration-storage)
8. [Google Colab Integration](#google-colab-integration)
9. [Recent Updates](#recent-updates)

## Installation

The LocalLab CLI is automatically installed when you install the LocalLab package:

```bash
pip install locallab locallab-client
```

After installation, you can access the CLI using the `locallab` command:

```bash
locallab --help
```

## Chat Interface ⭐

The **LocalLab Chat Interface** is the easiest way to interact with your AI models. It provides a ChatGPT-like experience right in your terminal.

### Quick Start

```bash
# Start your server
locallab start

# Open chat interface
locallab chat
```

### Key Features

- **🎯 Dynamic Mode Switching** - Change generation mode per message with `--stream`, `--chat`, etc.
- **🔄 Real-time Streaming** - See responses as they're generated
- **💬 Rich Terminal UI** - Markdown rendering with syntax highlighting
- **📚 Conversation Management** - History, saving, and loading
- **🌐 Remote Access** - Connect to any LocalLab server
- **🛠️ Error Recovery** - Automatic reconnection and graceful handling

### Basic Usage

```bash
# Connect to local server
locallab chat

# Connect to remote server
locallab chat --url https://your-ngrok-url.app

# Use specific generation mode
locallab chat --generate chat

# Custom parameters
locallab chat --max-tokens 200 --temperature 0.8
```

### Interactive Commands

```bash
/help      # Show all available commands
/history   # View conversation history
/save      # Save current conversation
/batch     # Enter batch processing mode
/reset     # Clear conversation history
/exit      # Exit gracefully
```

### Dynamic Mode Switching

Override the default generation mode for any message:

```bash
You: Write a story --stream          # Use streaming mode
You: Remember my name --chat         # Use chat mode with context
You: What's 2+2? --simple           # Use simple mode
You: Process these --batch          # Use batch mode
```

> 📖 **Complete Guide**: See the [Chat Interface Documentation](../cli/chat.md) for detailed features and examples.

## Server Management

### Start Server

```bash
# Start with interactive prompts for missing settings
locallab start

# Start with specific settings
locallab start --use-ngrok --port 8080 --model microsoft/phi-2
```

### Configure Settings

```bash
# Run the configuration wizard
locallab config
```

### System Information

```bash
# Display system information
locallab info
```

## Interactive Configuration

When you run `locallab start` without all required settings, the CLI will prompt you for the missing information:

1. **Model Selection**: Choose which model to load
2. **Port Selection**: Specify which port to run on
3. **Ngrok Configuration**: Enable public access via ngrok (if desired)
4. **Optimization Settings**: Configure performance optimizations

Example interactive session:

```
🎮 GPU detected with 8192MB free of 16384MB total
💾 System memory: 12288MB free of 16384MB total

🚀 Welcome to LocalLab! Let's set up your server.

📦 Which model would you like to use? [microsoft/phi-2]:
🔌 Which port would you like to run on? [8000]:
🌐 Do you want to enable public access via ngrok? [y/N]: y
🔑 Please enter your ngrok auth token: ******************

⚡ Would you like to configure optimizations for better performance? [Y/n]:
📊 Enable quantization for reduced memory usage? [Y/n]:
📊 Quantization type [int8/int4]: int8
🔪 Enable attention slicing for reduced memory usage? [Y/n]:
⚡ Enable flash attention for faster inference? [Y/n]:
🔄 Enable BetterTransformer for optimized inference? [Y/n]:

🔧 Would you like to configure advanced options? [y/N]:

✅ Configuration complete!
```

## Command Reference

### `locallab start`

Start the LocalLab server.

Options:

- `--use-ngrok`: Enable ngrok for public access
- `--port`: Port to run the server on
- `--ngrok-auth-token`: Ngrok authentication token
- `--model`: Model to load (e.g., microsoft/phi-2)
- `--quantize`: Enable quantization
- `--quantize-type`: Quantization type (int8 or int4)
- `--attention-slicing`: Enable attention slicing
- `--flash-attention`: Enable flash attention
- `--better-transformer`: Enable BetterTransformer

Example:

```bash
locallab start --model microsoft/phi-2 --quantize --quantize-type int8
```

### `locallab config`

Run the configuration wizard without starting the server. This command now shows your current configuration and allows you to modify it.

Example:

```bash
locallab config
```

Output:

```
📋 Current Configuration:
  port: 8000
  model_id: microsoft/phi-2
  enable_quantization: true
  quantization_type: int8
  enable_attention_slicing: true
  enable_flash_attention: false
  enable_better_transformer: false

Would you like to reconfigure these settings? [Y/n]:
```

### `locallab info`

Display system information.

Example:

```bash
locallab info
```

## Environment Variables

Key environment variables:

- `HUGGINGFACE_TOKEN`: HuggingFace API token for accessing models (optional)
- `HUGGINGFACE_MODEL`: Model to load
- `NGROK_AUTH_TOKEN`: Ngrok authentication token
- `LOCALLAB_ENABLE_QUANTIZATION`: Enable/disable quantization
- `LOCALLAB_QUANTIZATION_TYPE`: Type of quantization (int8/int4)
- `LOCALLAB_ENABLE_ATTENTION_SLICING`: Enable/disable attention slicing
- `LOCALLAB_ENABLE_FLASH_ATTENTION`: Enable/disable Flash Attention
- `LOCALLAB_ENABLE_BETTERTRANSFORMER`: Enable/disable BetterTransformer
- `LOCALLAB_ENABLE_CPU_OFFLOADING`: Enable/disable CPU offloading

## Configuration Storage

The CLI stores your configuration in `~/.locallab/config.json` for future use. This includes:
- HuggingFace token (if provided)
- Model settings
- Server configuration
- Optimization settings

To view your stored configuration:

```bash
cat ~/.locallab/config.json
```

To reset your configuration, simply delete this file:

```bash
rm ~/.locallab/config.json
```

## Google Colab Integration

The CLI works seamlessly in Google Colab. When running in Colab, the CLI automatically detects the environment and provides appropriate defaults:

```python
from locallab import start_server

# This will prompt for any missing required settings
start_server()

# Or with some settings provided
start_server(use_ngrok=True, port=8080)
```

The CLI will detect that it's running in Colab and prompt for any missing required settings, such as the ngrok authentication token if `use_ngrok=True` is specified.

## New in v0.4.9

Version 0.4.9 brings significant improvements to the configuration system:

### 🔄 Persistent Configuration That Works

- **Fixed Configuration Persistence**: The `locallab config` command now properly saves settings that are respected when running `locallab start`
- **Configuration Display**: The `config` command now shows your current configuration before prompting for changes
- **Skip Unnecessary Prompts**: The CLI now only prompts for settings that aren't already configured
- **Clear Feedback**: After saving configuration, the CLI shows what was saved and how to use it

### 🛠️ Improved Configuration Workflow

```bash
# Step 1: Configure your settings once
locallab config

# Step 2: Start the server using your saved configuration
locallab start
```

With this improved workflow, you only need to configure your settings once, and they'll be remembered for future sessions.

### Example Configuration Session

```
$ locallab config

📋 Current Configuration:
  port: 8000
  model_id: microsoft/phi-2
  enable_quantization: true
  quantization_type: int8
  enable_attention_slicing: true

Would you like to reconfigure these settings? [Y/n]: n
Configuration unchanged.

$ locallab start
🎮 GPU detected with 8192MB free of 16384MB total
💾 System memory: 12288MB free of 16384MB total

✅ Using saved configuration!
```

## New in v0.4.8

Version 0.4.8 brings significant improvements to the CLI:

### ⚡ Lightning-Fast Startup

- **Lazy Loading**: The CLI now uses lazy loading for imports, resulting in much faster startup times
- **Optimized Initialization**: Reduced unnecessary operations during CLI startup
- **Faster Response**: Commands like `locallab info` now respond almost instantly

### 🛡️ Improved Error Handling

- **Robust Error Recovery**: Better handling of common errors like missing dependencies
- **Informative Messages**: More helpful error messages that guide you to solutions
- **Graceful Fallbacks**: The CLI now gracefully handles missing or invalid configuration values

### 🔄 Unified Configuration System

- **Seamless Integration**: CLI options, environment variables, and configuration files now work together harmoniously
- **Consistent Behavior**: No more conflicts between different ways of setting configuration values
- **Clear Precedence**: Environment variables take precedence over saved configuration, which takes precedence over defaults

### 📊 Enhanced System Information

- **Detailed Hardware Info**: The `locallab info` command now provides more detailed information about your system
- **Better Memory Reporting**: Improved memory usage reporting with proper unit conversion (GB instead of MB)
- **GPU Details**: More comprehensive GPU information when available

### Example Usage

```bash
# Start with interactive configuration - now much faster!
locallab start

# Use the improved system information command
locallab info

# Configure with specific options - now with better error handling
locallab start --model microsoft/phi-2 --quantize --quantize-type int8 --attention-slicing
```

## Using the CLI in Python Code

You can also use the CLI functionality directly in your Python code:

```python
from locallab.cli.interactive import prompt_for_config
from locallab.cli.config import save_config

# Run the interactive configuration
config = prompt_for_config()

# Save the configuration
save_config(config)

# Use the configuration
print(config)
```

This is useful if you want to build your own custom configuration flow on top of LocalLab's CLI.
