# LocalLab Deployment Guide

This document provides step-by-step instructions to deploy LocalLab.

> **Note**: For Google Colab-specific deployment details, see [Google Colab Deployment Guide](./COLAB_DEPLOYMENT.md).

## Google Colab Deployment (Recommended)

1. Install the LocalLab package:
   ```python
   !pip install locallab
   ```

2. Import and initialize LocalLab:
   ```python
   from locallab import ModelServer

   # Initialize the server with default settings
   server = ModelServer()
   
   # Or customize the configuration
   server = ModelServer(
       model_name="qwen-0.5b",  # Default model
       ngrok_token="your_token", # Optional: Your ngrok token
       cache_dir="/content/model_cache"  # Where to store downloaded models
   )
   ```

3. Start the server:
   ```python
   # This will automatically:
   # - Set up ngrok tunnel
   # - Download and load the AI model
   # - Start the FastAPI server
   public_url = server.start()
   print(f"Server is running at: {public_url}")
   ```

4. Use the API:
   ```python
   # Built-in client for easy testing
   from locallab import Client
   
   client = Client(public_url)
   response = client.generate("Hello, world!")
   print(response)
   ```

## Local Deployment (Alternative)

1. Install the package:
   ```bash
   pip install locallab
   ```

2. Start the server from command line:
   ```bash
   python -m locallab.server
   ```

3. Access the API:
   http://localhost:8000

## Environment Variables

- `LOCALLAB_MODEL`: Default model to load (e.g., "qwen-0.5b")
- `NGROK_TOKEN`: Your ngrok authentication token
- `LOCALLAB_CACHE_DIR`: Directory for storing downloaded models

## Related Documentation
- [API Documentation](./API.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)
