# LocalLab

A lightweight AI inference server for local deployment on low-spec machines, enabling developers to run advanced AI models without high-end hardware or cloud services.

## 📋 Table of Contents

- [Overview](#overview)
- [Key Components](#key-components)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Server Implementation](#server-implementation)
- [Deployment](#deployment)
- [Final Goal](#final-goal)

## 🔍 Overview

LocalLab provides RESTful API endpoints to manage and interact with AI models, supporting:

- Model loading and switching
- Text generation (with streaming support)
- System health monitoring
- Performance optimization through caching
- Easy deployment on Google Colab using ngrok

## 🛠 Key Components

### Server Framework

- **FastAPI**: Core API endpoints and web framework
- **Uvicorn**: ASGI server for running the FastAPI application

### AI Model Management

- **Transformers (Hugging Face)**: Loading and running pre-trained AI models
- **ModelManager Class**: Custom module for:
  - Model registry management
  - GPU memory monitoring
  - Error handling and fallbacks
  - Text generation and streaming

### Logging & Monitoring

- **Python logging & Colorama**: Enhanced visual logging
- **System Health Endpoints**: Real-time resource monitoring

### Caching & Performance

- **fastapi-cache2**: Response caching for improved performance

### Deployment Tools

- **pyngrok**: Internet accessibility for local servers
- **nest_asyncio**: Async operation compatibility

## 📥 Installation

### Server Dependencies

```bash
pip install fastapi uvicorn python-multipart transformers accelerate pyngrok nest_asyncio psutil nvidia-ml-py3 fastapi-cache2 colorama
```

## 📁 Project Structure

### Directory Tree

```
locallab/
├── server/
│   ├── __init__.py
│   ├── main.py           # Entry point; sets up FastAPI, API endpoints, and ngrok integration.
│   ├── model_manager.py  # Contains the ModelManager class for loading and managing AI models.
│   ├── config.py         # Holds configuration variables like the model registry and system prompt.
│   ├── logger.py         # Configures custom logging with aesthetic formatting.
│   └── utils.py          # Contains utility functions (e.g., GPU memory check).
├── client/
│   ├── python_client/
│   │   ├── __init__.py
│   │   └── client.py     # Python client wrapper for interacting with LocalLab API.
│   └── node_client/
│       ├── package.json
│       └── index.js      # Node.js client for API interactions.
├── tests/                # Unit and integration tests for server and clients.
├── docs/                 # Documentation and example usage.
├── requirements.txt      # List of dependencies.
└── README.md             # Project overview and instructions.
```

### Detailed Component Description

| Component          | Path                             | Description                                          |
| ------------------ | -------------------------------- | ---------------------------------------------------- |
| Server Entry Point | `server/main.py`                 | FastAPI setup, API endpoints, ngrok integration      |
| Model Manager      | `server/model_manager.py`        | AI model loading, inference, and resource management |
| Configuration      | `server/config.py`               | System settings, model registry, prompts             |
| Logger             | `server/logger.py`               | Custom logging with color formatting                 |
| Python Client      | `client/python_client/client.py` | Python SDK for API interaction                       |
| Node.js Client     | `client/node_client/index.js`    | Node.js SDK for API interaction                      |

## 🚀 Server Implementation

### API Endpoints

- `/generate`: Text generation endpoint
- `/models`: Model listing and resource info
- `/set_model`: Model switching
- `/system_health`: Resource monitoring
- `/suggest_model`: Model recommendations

### Features

- GPU memory validation
- Hugging Face model integration
- System prompt processing
- Response caching
- Colored logging

## 📦 Deployment

### Local Deployment

```bash
python -m server.main
```

### Google Colab Deployment

- Automatic ngrok tunnel creation
- Public URL generation

## 🎯 Final Goal

LocalLab aims to be a self-contained, modular AI inference platform that:

- Runs on low-spec machines
- Deploys easily on Google Colab
- Provides simple client libraries
- Requires minimal setup
- Offers comprehensive documentation

## Project Components and Technologies

### Server Framework

- FastAPI: Provides the core API endpoints and serves as the main web framework
- Uvicorn: Acts as the ASGI server to run the FastAPI application

### AI Model Management

- Transformers (Hugging Face): Used to load and run pre-trained AI models for inference
- ModelManager Class: A custom module responsible for:
  - Loading models based on a predefined registry.
  - Checking GPU memory (using nvidia-ml-py3 and psutil).
  - Managing model fallbacks in case of errors.
  - Handling text generation, including streaming responses.

### Logging & Monitoring

- Python logging module & Colorama: For creating visually appealing and informative logs that emphasize errors and key status updates.
- System Health Endpoints: Provide real-time insights into GPU memory, CPU usage, and active models.

### Caching

- fastapi-cache2: Integrated to cache responses from computationally expensive operations (like inference) for improved performance.

### Deployment and Accessibility

- pyngrok: Facilitates exposing the local server to the internet, making it accessible when running on platforms like Google Colab.
- nest_asyncio: Ensures compatibility with asynchronous operations in environments (like Jupyter Notebooks or Colab) that use nested event loops.

### Project Modularity & Packaging

- Modular Code Structure: The code is divided into distinct modules for configuration, model management, logging, API endpoints, and utilities.
- Python Package & Client Libraries: Designed to be distributed as a Python package with potential client libraries (Python and Node.js) that allow developers to easily interact with the server using simple, high-level API calls.
