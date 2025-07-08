# 🤖 Model Management Guide

LocalLab provides comprehensive model management capabilities through the `locallab models` command group. This allows you to download, manage, and organize AI models locally before starting the server.

## 📋 Overview

The model management system helps you:
- **Download models locally** for offline use and faster startup
- **List cached models** with detailed information
- **Remove models** to free up disk space
- **Discover available models** from registries and HuggingFace Hub
- **Get detailed model information** including system compatibility
- **Clean up cache** to remove orphaned files

## 🚀 Quick Start

```bash
# Discover available models
locallab models discover

# Download a model
locallab models download microsoft/DialoGPT-medium

# List your cached models
locallab models list

# Get detailed information about a model
locallab models info microsoft/DialoGPT-medium

# Remove a model to free space
locallab models remove microsoft/DialoGPT-medium
```

## 📖 Command Reference

### List Models {#list-models}

List all locally cached models with detailed information.

```bash
locallab models list [OPTIONS]
```

**Options:**
- `--format [table|json]` - Output format (default: table)
- `--registry-only` - Show only registry models
- `--custom-only` - Show only custom models

**Examples:**
```bash
# List all cached models in table format
locallab models list

# List only registry models
locallab models list --registry-only

# Export model list as JSON
locallab models list --format json
```

**Output includes:**
- Model ID and name
- Size on disk
- Cache status and date
- Model type (Registry/Custom)
- Brief description

### Download Models {#download-models}

Download a model locally for offline use and faster server startup.

```bash
locallab models download <model_id> [OPTIONS]
```

**Options:**
- `--force` - Force re-download even if model exists
- `--no-cache-update` - Skip updating cache metadata

**Examples:**
```bash
# Download a registry model
locallab models download microsoft/DialoGPT-medium

# Download a custom HuggingFace model
locallab models download huggingface/CodeBERTa-small-v1

# Force re-download an existing model
locallab models download microsoft/DialoGPT-medium --force
```

**Features:**
- Progress bar with download speed and ETA
- Automatic validation of downloaded files
- Integration with HuggingFace Hub authentication
- Graceful error handling and retry logic
- Cache metadata tracking

### Remove Models {#remove-models}

Remove locally cached models to free up disk space.

```bash
locallab models remove <model_id> [OPTIONS]
```

**Options:**
- `--force` - Skip confirmation prompt

**Examples:**
```bash
# Remove a model with confirmation
locallab models remove microsoft/DialoGPT-medium

# Remove without confirmation
locallab models remove microsoft/DialoGPT-medium --force
```

**Safety features:**
- Confirmation prompt by default
- Shows model size before removal
- Cleans up all associated files
- Updates cache metadata

### Discover Models {#discover-models}

Discover available models from the LocalLab registry and HuggingFace Hub.

```bash
locallab models discover [OPTIONS]
```

**Options:**
- `--search <term>` - Search models by name or description
- `--limit <number>` - Maximum number of models to show (default: 20)
- `--format [table|json]` - Output format (default: table)

**Examples:**
```bash
# Discover all available models
locallab models discover

# Search for specific models
locallab models discover --search "dialog"

# Limit results and export as JSON
locallab models discover --limit 10 --format json
```

**Information shown:**
- Model ID and name
- Model size and type
- Cache status (cached/available)
- Brief description
- Download availability

### Model Information {#model-info}

Get detailed information about a specific model.

```bash
locallab models info <model_id>
```

**Examples:**
```bash
# Get detailed info about a model
locallab models info microsoft/DialoGPT-medium
```

**Information includes:**
- Model name and description
- Size and requirements
- Local cache status and location
- System compatibility check
- Available actions (download/remove)
- Fallback model information

### Cache Cleanup {#cache-cleanup}

Clean up orphaned cache files and free disk space.

```bash
locallab models clean
```

**Features:**
- Finds empty model directories
- Identifies temporary and lock files
- Shows what will be cleaned before removal
- Confirmation prompt for safety
- Reports space freed after cleanup

## 💾 Cache Management

### Cache Location

Models are cached in the standard HuggingFace Hub cache directory:
- **Windows**: `%USERPROFILE%\.cache\huggingface\hub`
- **macOS/Linux**: `~/.cache/huggingface/hub`

You can override this location by setting the `HF_HOME` environment variable.

### Cache Structure

```
~/.cache/huggingface/hub/
├── models--microsoft--DialoGPT-medium/
│   ├── refs/
│   ├── snapshots/
│   └── blobs/
└── models--huggingface--CodeBERTa-small-v1/
    ├── refs/
    ├── snapshots/
    └── blobs/
```

### Metadata Tracking

LocalLab maintains additional metadata in `~/.locallab/model_cache.json`:
- Download timestamps
- Access counts
- Download methods
- Custom model information

## 🔧 Advanced Usage

### Environment Variables

- `HF_HOME` - Override HuggingFace cache directory
- `HF_TOKEN` - HuggingFace authentication token for private models

### Integration with Server

Downloaded models are automatically available when starting the LocalLab server:

```bash
# Download model first
locallab models download microsoft/DialoGPT-medium

# Start server - model loads faster from cache
locallab start --model microsoft/DialoGPT-medium
```

### Batch Operations

Use shell scripting for batch operations:

```bash
# Download multiple models
for model in "microsoft/DialoGPT-medium" "microsoft/DialoGPT-large"; do
    locallab models download "$model"
done

# Clean up old models
locallab models list --format json | jq -r '.[] | select(.size > 1000000000) | .id' | \
    xargs -I {} locallab models remove {} --force
```

## 🚨 Troubleshooting

### Common Issues

**Download fails with authentication error:**
```bash
# Set HuggingFace token
export HF_TOKEN="your_token_here"
locallab models download private/model
```

**Model not found:**
```bash
# Check if model exists in registry
locallab models discover --search "model_name"

# Try with full HuggingFace model ID
locallab models download organization/model-name
```

**Cache corruption:**
```bash
# Clean up corrupted cache
locallab models clean

# Force re-download
locallab models download model_id --force
```

**Disk space issues:**
```bash
# Check cache size
locallab models list

# Remove large unused models
locallab models remove large_model_id

# Clean orphaned files
locallab models clean
```

### Getting Help

```bash
# Get help for any command
locallab models --help
locallab models download --help
locallab models list --help
```

## 📊 Best Practices

1. **Download models before first use** for faster server startup
2. **Regularly clean cache** to free up disk space
3. **Use registry models** when possible for better support
4. **Check system compatibility** before downloading large models
5. **Set HF_TOKEN** for accessing private models
6. **Monitor disk usage** with `locallab models list`

---

For more information, see the [CLI Reference](../cli/README.md) or [Configuration Guide](./configuration.md).