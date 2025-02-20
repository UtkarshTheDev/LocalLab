# LocalLab Documentation

Welcome to the LocalLab documentation! This guide will help you get started quickly and make the most of LocalLab's features.

## 📚 Quick Navigation

### For New Users
1. [Quick Start Guide](../README.md#quick-start) - Start here!
2. [Deployment Guide](./DEPLOYMENT.md) - Set up LocalLab
3. [Colab Guide](./colab/README.md) - Run in Google Colab

### For Developers
1. [API Reference](./API.md) - REST API documentation
2. [Python SDK](./python/README.md) - Python client guide
3. [Node.js SDK](./nodejs/README.md) - Node.js client guide

## 🚀 Getting Started

1. **Installation**
```bash
pip install locallab
```

2. **Basic Usage**
```python
from locallab import start_server
start_server()
```

3. **Using the Client**
```python
from locallab.client import LocalLabClient
client = LocalLabClient("http://localhost:8000")
response = client.generate("Hello, world!")
```

## 🔧 Core Features

- Model Management
- Text Generation
- Chat Completion
- Batch Processing
- Resource Optimization
- System Monitoring

## 🆘 Need Help?

- Check the [Troubleshooting Guide](./TROUBLESHOOTING.md)
- Read the [FAQ](./colab/faq.md)
- Visit our [GitHub Issues](https://github.com/Developer-Utkarsh/LocalLab/issues)

## 📖 Documentation Structure

```
docs/
├── README.md           # This file - Start here
├── API.md             # REST API documentation
├── DEPLOYMENT.md      # Deployment instructions
├── TROUBLESHOOTING.md # Common issues and solutions
├── colab/            # Google Colab integration
├── python/           # Python client documentation
└── nodejs/           # Node.js client documentation
```
