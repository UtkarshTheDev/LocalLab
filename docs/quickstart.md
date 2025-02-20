# Quick Start Guide to LocalLab

Welcome to LocalLab – a lightweight AI inference server that lets you run powerful language models both locally and in Google Colab. This guide will get you up and running in just a few minutes, whether you're using the Python or Node.js client.

---

## 1. LocalLab Server Setup

### Installation

Install LocalLab using pip:

```bash
pip install locallab
```

### Local Deployment

Start the server locally with the following Python snippet:

```python
from locallab import start_server

# Start the server on http://localhost:8000
start_server()
```

After starting the server, you can access the API at:
[http://localhost:8000](http://localhost:8000)

### Google Colab Deployment

If you prefer running LocalLab on Google Colab, follow these steps:

1. **Install LocalLab in Colab:**

   ```python
   !pip install locallab
   ```

2. **Set Up ngrok:**

   Replace `"your_token_here"` with your actual ngrok token.

   ```python
   import os
   os.environ["NGROK_AUTH_TOKEN"] = "your_token_here"
   ```

3. **Start the Server with Public Access:**

   ```python
   from locallab import start_server
   start_server(use_ngrok=True)
   ```

Your public URL will be displayed in the output. For more details, see the [Google Colab Integration Guide](./colab/README.md).

---

## 2. Python Client Quick Start

### Installation

Install the Python client (bundled within LocalLab):

```bash
pip install locallab
```

### Usage Example

```python
from locallab.client import LocalLabClient

# Connect to the LocalLab server
client = LocalLabClient("http://localhost:8000")

# Basic text generation example
response = client.generate("Write a story about a robot")
print("Generated Text:", response)

# Chat completion example
chat_response = client.chat([
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Tell me a joke."}
])
print("Chat Response:", chat_response["choices"][0]["message"]["content"])
```

For additional details, refer to the [Python Client Documentation](./python/README.md).

---

## 3. Node.js Client Quick Start

### Installation

Install the Node.js client via npm or yarn:

```bash
npm install locallab-client
# or
yarn add locallab-client
```

### Usage Example

```javascript
const LocalLabClient = require("locallab-client");

// Initialize the client with the server URL
const client = new LocalLabClient("http://localhost:8000");

// Example: Basic text generation
async function generateText() {
  try {
    const response = await client.generate("Write a story about a robot");
    console.log("Generated Text:", response);
  } catch (error) {
    console.error("Error generating text:", error);
  }
}

generateText();
```

For further examples and advanced configurations, see the [Node.js Client Documentation](./nodejs/README.md).

---

## 4. Further References

- **API Reference:**  
  [LocalLab API Documentation](./API.md) – Detailed descriptions of all REST API endpoints.

- **Deployment Guide:**  
  [Deployment Instructions](./DEPLOYMENT.md) – Learn how to deploy locally or on Google Colab.

- **Troubleshooting:**  
  [Troubleshooting Guide](./TROUBLESHOOTING.md) – Find solutions to common issues.

- **Features Overview:**  
  [Features Guide](./features/README.md) – Explore advanced functionalities and optimizations.

---

Congratulations! You are now ready to explore and utilize LocalLab for your AI inference needs.
