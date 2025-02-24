# Getting Started with LocalLab

This guide will help you start using LocalLab, whether you're running it locally or on Google Colab.

## Choose Your Environment

### Local Setup

1. **Install LocalLab**
   ```bash
   pip install locallab
   ```

2. **Start the Server**
   ```python
   from locallab import start_server
   start_server()
   ```

3. **Connect Client**
   ```python
   from locallab.client import LocalLabClient
   client = LocalLabClient("http://localhost:8000")
   ```

### Google Colab Setup

1. **Install LocalLab**
   ```python
   !pip install locallab
   ```

2. **Set Up Ngrok**
   ```python
   import os
   os.environ["NGROK_AUTH_TOKEN"] = "your_token_here"
   ```

3. **Start Server**
   ```python
   from locallab import start_server
   start_server(ngrok=True)  # Will show public URL in logs
   ```

4. **Connect Client**
   ```python
   from locallab.client import LocalLabClient
   client = LocalLabClient("https://xxxx-xx-xx-xxx-xx.ngrok-free.app")  # Use URL from logs
   ```

## First Steps

### 1. Generate Text
```python
# Simple text generation
response = await client.generate(
    "Write a story about a robot",
    temperature=0.7
)
print(response)
```

### 2. Chat with AI
```python
# Chat completion
response = await client.chat([
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
])
print(response.choices[0].message.content)
```

### 3. Process Multiple Prompts
```python
# Batch processing
responses = await client.batch_generate([
    "Write a haiku",
    "Tell a joke"
])
```

## Next Steps

1. Explore [Advanced Features](./guides/advanced.md)
2. Check [API Reference](./API.md)
3. Read [Performance Guide](./features/performance.md)

## Need Help?

- See [FAQ](./FAQ.md)
- Visit [Troubleshooting](./TROUBLESHOOTING.md)
- Join our [Community](https://github.com/Developer-Utkarsh/LocalLab/discussions)
