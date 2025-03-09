# LocalLab CLI Guide

LocalLab provides a powerful command-line interface (CLI) that makes it easy to configure and run your AI inference server. This guide covers all the CLI features and how to use them effectively.

## 📚 Table of Contents

1. [Installation](#installation)
2. [Basic Commands](#basic-commands)
3. [Interactive Configuration](#interactive-configuration)
4. [Command Reference](#command-reference)
5. [Environment Variables](#environment-variables)
6. [Configuration Storage](#configuration-storage)
7. [Google Colab Integration](#google-colab-integration)

## Installation

The LocalLab CLI is automatically installed when you install the LocalLab package:

```bash
pip install locallab
```

After installation, you can access the CLI using the `locallab` command:

```bash
locallab --help
```

## Basic Commands

LocalLab CLI provides several commands for different operations:

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

✅ Configuration complete! Starting server...
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

Run the configuration wizard without starting the server.

Example:

```bash
locallab config
```

### `locallab info`

Display system information.

Example:

```bash
locallab info
```

## Environment Variables

The CLI respects environment variables that you've already set. If an environment variable is set, the CLI won't prompt for that setting unless you explicitly run the configuration wizard.

Key environment variables:

- `HUGGINGFACE_MODEL`: Model to load
- `NGROK_AUTH_TOKEN`: Ngrok authentication token
- `LOCALLAB_ENABLE_QUANTIZATION`: Enable/disable quantization
- `LOCALLAB_QUANTIZATION_TYPE`: Type of quantization (int8/int4)
- `LOCALLAB_ENABLE_ATTENTION_SLICING`: Enable/disable attention slicing
- `LOCALLAB_ENABLE_FLASH_ATTENTION`: Enable/disable Flash Attention
- `LOCALLAB_ENABLE_BETTERTRANSFORMER`: Enable/disable BetterTransformer
- `LOCALLAB_ENABLE_CPU_OFFLOADING`: Enable/disable CPU offloading

## Configuration Storage

The CLI stores your configuration in `~/.locallab/config.json` for future use. This means you don't have to re-enter your settings each time you run LocalLab.

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
