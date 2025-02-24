# LocalLab Client Usage Comparison: Python vs Node.js

This guide provides a clear, side-by-side comparison of how to use the LocalLab client libraries in Python and Node.js.

## Table of Contents

1. [Installation](#installation)
2. [Basic Setup & Usage](#basic-setup--usage)
3. [Advanced Features](#advanced-features)
4. [Error Handling](#error-handling)
5. [API Reference](#api-reference)

## Installation

### Python
Install the Python client using pip:
```bash
pip install locallab
```
or via poetry:
```bash
poetry add locallab
```

### Node.js
Install the Node.js client using npm or yarn:
```bash
npm install locallab-client
```
or
```bash
yarn add locallab-client
```

## Basic Setup & Usage

### Python
**Local Setup:**
```python
from locallab.client import LocalLabClient

# Connect to local server
client = LocalLabClient("http://localhost:8000")

# Generate text
response = await client.generate("Write a story about a robot", temperature=0.7)
print(response)
```

**Google Colab Setup:**
```python
from locallab.client import LocalLabClient

# Connect using the ngrok URL shown in server logs
client = LocalLabClient("https://xxxx-xx-xx-xxx-xx.ngrok-free.app")

# Generate text
response = await client.generate("Write a story about a robot", temperature=0.7)
print(response)
```

### Node.js
**Local Setup:**
```javascript
const LocalLabClient = require('locallab-client');

// Connect to local server
const client = new LocalLabClient('http://localhost:8000');

// Generate text
const response = await client.generate('Write a story about a robot', {
    temperature: 0.7
});
console.log(response);
```

**Google Colab Setup (Node.js):**
```javascript
const LocalLabClient = require('locallab-client');

// Connect using the ngrok URL shown in server logs
const client = new LocalLabClient('https://xxxx-xx-xx-xxx-xx.ngrok-free.app');

// Generate text
const response = await client.generate('Write a story about a robot', {
    temperature: 0.7
});
console.log(response);
```

## Advanced Features

### Python
- **Streaming Responses:**
  ```python
  async for token in client.stream_generate("Tell me a story"):
      print(token, end="", flush=True)
  ```
- **Chat Completion:**
  ```python
  response = await client.chat([
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is Python?"}
  ])
  print(response.choices[0].message.content)
  ```
- **Batch Processing:**
  ```python
  prompts = ["Write a haiku", "Tell a joke", "Give a fact"]
  responses = await client.batch_generate(prompts)
  ```
- **Model Management:**
  ```python
  models = await client.list_models()
  print(models)
  await client.load_model("mistral-7b")
  current_model = await client.get_current_model()
  print(current_model)
  ```

### Node.js
- **Streaming Responses:**
  ```javascript
  for await (const token of client.streamGenerate('Tell me a story')) {
      process.stdout.write(token);
  }
  ```
- **Chat Completion:**
  ```javascript
  const response = await client.chat([
      { role: 'system', content: 'You are a helpful assistant.' },
      { role: 'user', content: 'What is JavaScript?' }
  ]);
  console.log(response.choices[0].message.content);
  ```
- **Batch Processing:**
  ```javascript
  const prompts = ['Write a haiku', 'Tell a joke', 'Give a fact'];
  const responses = await client.batchGenerate(prompts);
  console.log(responses);
  ```
- **Model Management:**
  ```javascript
  const models = await client.listModels();
  console.log(models);
  await client.loadModel('mistral-7b');
  const currentModel = await client.getCurrentModel();
  console.log(currentModel);
  ```

## Advanced Examples

### System Resource Monitoring

#### Python
```python
# Get detailed system info
system_info = await client.get_system_info()
print(f"CPU Usage: {system_info.cpu_usage}%")
print(f"Memory Usage: {system_info.memory_usage}%")
if system_info.gpu_info:
    print(f"GPU Memory: {system_info.gpu_info.used_memory}MB")

# Health check
is_healthy = await client.health_check()
print(f"Server Status: {'Healthy' if is_healthy else 'Unhealthy'}")
```

#### Node.js
```javascript
// Get detailed system info
const systemInfo = await client.getSystemInfo();
console.log(`CPU Usage: ${systemInfo.cpuUsage}%`);
console.log(`Memory Usage: ${systemInfo.memoryUsage}%`);
if (systemInfo.gpuInfo) {
    console.log(`GPU Memory: ${systemInfo.gpuInfo.usedMemory}MB`);
}

// Health check
const isHealthy = await client.healthCheck();
console.log(`Server Status: ${isHealthy ? 'Healthy' : 'Unhealthy'}`);
```

### WebSocket Connections

#### Python
```python
# Connect to WebSocket
await client.connect_ws()

# Subscribe to messages
async def message_handler(data):
    print("Received:", data)

await client.on_message(message_handler)

# Disconnect when done
await client.disconnect_ws()
```

#### Node.js
```javascript
// Connect to WebSocket
await client.connect();

// Subscribe to messages
client.onMessage((data) => {
    console.log('Received:', data);
});

// Disconnect when done
await client.disconnect();
```

### Custom Model Configuration

#### Python
```python
# Configure model settings
await client.load_model("mistral-7b", {
    "temperature": 0.8,
    "max_length": 4096,
    "top_p": 0.95,
    "quantization": "int8"
})

# Get model configuration
config = await client.get_model_config()
print(f"Current settings: {config}")
```

#### Node.js
```javascript
// Configure model settings
await client.loadModel('mistral-7b', {
    temperature: 0.8,
    maxLength: 4096,
    topP: 0.95,
    quantization: 'int8'
});

// Get model configuration
const config = await client.getModelConfig();
console.log('Current settings:', config);
```

## Error Handling

### Python
```python
try:
    response = await client.generate("Hello")
except Exception as e:
    if "rate limit" in str(e):
        print("Rate limit exceeded")
    elif "model not found" in str(e):
        print("Model not available")
    else:
        print(f"Error: {str(e)}")
```

### Node.js
```javascript
try {
    const response = await client.generate('Hello');
} catch (error) {
    if (error.message.includes('rate limit')) {
        console.log('Rate limit exceeded');
    } else if (error.message.includes('model not found')) {
        console.log('Model not available');
    } else {
        console.error('Error:', error);
    }
}
```

## Prerequisites

### Python
- Python 3.8+
- Understanding of async/await
- Basic pip/poetry knowledge
- Virtual environment basics

### Node.js
- Node.js 14+
- Understanding of async/await
- npm/yarn basics
- ES6+ JavaScript knowledge

## Troubleshooting Guide

### Python Common Issues

1. **Connection Issues**
   ```python
   try:
       client = LocalLabClient("http://localhost:8000")
       await client.health_check()
   except ConnectionError:
       print("Server not running or wrong URL")
   except Exception as e:
       print(f"Unknown error: {str(e)}")
   ```

2. **Memory Management**
   ```python
   # Enable memory optimizations
   import os
   os.environ["LOCALLAB_ENABLE_QUANTIZATION"] = "true"
   os.environ["LOCALLAB_QUANTIZATION_TYPE"] = "int8"
   ```

3. **Async Context Management**
   ```python
   async with LocalLabClient("http://localhost:8000") as client:
       response = await client.generate("Hello")
   # Client automatically closes
   ```

### Node.js Common Issues

1. **Connection Issues**
   ```javascript
   try {
       const client = new LocalLabClient('http://localhost:8000');
       await client.healthCheck();
   } catch (error) {
       if (error.code === 'ECONNREFUSED') {
           console.log('Server not running or wrong URL');
       } else {
           console.error('Unknown error:', error);
       }
   }
   ```

2. **Memory Management**
   ```javascript
   // Enable memory optimizations
   process.env.LOCALLAB_ENABLE_QUANTIZATION = 'true';
   process.env.LOCALLAB_QUANTIZATION_TYPE = 'int8';
   ```

3. **Promise Handling**
   ```javascript
   // Using async/await with proper cleanup
   let client;
   try {
       client = new LocalLabClient('http://localhost:8000');
       const response = await client.generate('Hello');
   } finally {
       if (client) await client.close();
   }
   ```

## API Reference

For detailed API documentation, please refer to:
- [Python API Reference](./python.md#api-reference) in the Python Client Guide.
- [Node.js API Reference](./nodejs.md#api-reference) in the Node.js Client Guide.
