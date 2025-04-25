# 🎯 LocalLab Examples Guide

This guide provides practical examples of using LocalLab in your projects. Each example includes code snippets and explanations.

## 📚 Table of Contents

- [Client Types](#client-types)
- [Basic Usage](#basic-usage)
- [Text Generation](#text-generation)
- [Chat Completion](#chat-completion)
- [Streaming Responses](#streaming-responses)
- [Batch Processing](#batch-processing)
- [Model Management](#model-management)
- [Error Handling](#error-handling)

## Client Types

LocalLab provides two client types to fit different programming styles:

### SyncLocalLabClient (Synchronous)

- **Easier for beginners** - No need to use `async`/`await`
- **Works in regular Python code** - No special syntax required
- **Simpler to understand** - Traditional function calls

### LocalLabClient (Asynchronous)

- **Better for advanced users** - Uses `async`/`await` syntax
- **More efficient for concurrent operations** - Non-blocking I/O
- **Requires asyncio** - Must be used with `async`/`await` and `asyncio.run()`

Choose the client type that best fits your needs and coding style.

## Basic Usage

### Synchronous Client (Easier for Beginners)

```python
from locallab_client import SyncLocalLabClient

# Initialize client
client = SyncLocalLabClient("http://localhost:8000")  # or "https://your-ngrok-url.ngrok.app"

try:
    # Check if server is healthy
    is_healthy = client.health_check()
    print(f"Server status: {'Ready' if is_healthy else 'Not Ready'}")

    # Your code here...

finally:
    # Always close the client when done
    client.close()
```

### Asynchronous Client (For Advanced Users)

```python
import asyncio
from locallab_client import LocalLabClient

async def main():
    # Initialize client
    client = LocalLabClient("http://localhost:8000")  # or "https://your-ngrok-url.ngrok.app"

    try:
        # Check if server is healthy
        is_healthy = await client.health_check()
        print(f"Server status: {'Ready' if is_healthy else 'Not Ready'}")

        # Your code here...

    finally:
        # Always close the client when done
        await client.close()

# Run your async code
asyncio.run(main())
```

## Text Generation

### Simple Generation

#### Synchronous (Easier for Beginners)

```python
from locallab_client import SyncLocalLabClient

def generate_text():
    client = SyncLocalLabClient("http://localhost:8000")  # or "https://your-ngrok-url.ngrok.app"
    try:
        response = client.generate(
            "Write a short story about a robot"
        )
        print(response)
    finally:
        client.close()

# Call the function directly
generate_text()
```

#### Asynchronous (For Advanced Users)

```python
import asyncio
from locallab_client import LocalLabClient

async def generate_text():
    client = LocalLabClient("http://localhost:8000")  # or "https://your-ngrok-url.ngrok.app"
    try:
        response = await client.generate(
            "Write a short story about a robot"
        )
        print(response)
    finally:
        await client.close()

# Run the async function
asyncio.run(generate_text())
```

### Custom Parameters

#### Synchronous (Easier for Beginners)

```python
from locallab_client import SyncLocalLabClient

client = SyncLocalLabClient("http://localhost:8000")
try:
    response = client.generate(
        prompt="Write a poem about coding",
        temperature=0.7,  # Control creativity (0.0 to 1.0)
        max_length=100,   # Maximum length of response
        top_p=0.9         # Nucleus sampling parameter
    )
    print(response)
finally:
    client.close()
```

#### Asynchronous (For Advanced Users)

```python
import asyncio
from locallab_client import LocalLabClient

async def main():
    client = LocalLabClient("http://localhost:8000")
    try:
        response = await client.generate(
            prompt="Write a poem about coding",
            temperature=0.7,  # Control creativity (0.0 to 1.0)
            max_length=100,   # Maximum length of response
            top_p=0.9         # Nucleus sampling parameter
        )
        print(response)
    finally:
        await client.close()

asyncio.run(main())
```

## Chat Completion

### Basic Chat

#### Synchronous (Easier for Beginners)

```python
from locallab_client import SyncLocalLabClient

def chat_example():
    client = SyncLocalLabClient("http://localhost:8000")  # or "https://your-ngrok-url.ngrok.app"
    try:
        response = client.chat([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is Python?"}
        ])
        print(response.choices[0].message.content)
    finally:
        client.close()

# Call the function directly
chat_example()
```

#### Asynchronous (For Advanced Users)

```python
import asyncio
from locallab_client import LocalLabClient

async def chat_example():
    client = LocalLabClient("http://localhost:8000")  # or "https://your-ngrok-url.ngrok.app"
    try:
        response = await client.chat([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is Python?"}
        ])
        print(response.choices[0].message.content)
    finally:
        await client.close()

# Run the async function
asyncio.run(chat_example())
```

### Multi-turn Conversation

#### Synchronous (Easier for Beginners)

```python
from locallab_client import SyncLocalLabClient

client = SyncLocalLabClient("http://localhost:8000")
try:
    messages = [
        {"role": "system", "content": "You are a math tutor."},
        {"role": "user", "content": "Can you help me with algebra?"},
        {"role": "assistant", "content": "Of course! What would you like to know?"},
        {"role": "user", "content": "Explain quadratic equations."}
    ]
    response = client.chat(messages)
    print(response.choices[0].message.content)
finally:
    client.close()
```

#### Asynchronous (For Advanced Users)

```python
import asyncio
from locallab_client import LocalLabClient

async def main():
    client = LocalLabClient("http://localhost:8000")
    try:
        messages = [
            {"role": "system", "content": "You are a math tutor."},
            {"role": "user", "content": "Can you help me with algebra?"},
            {"role": "assistant", "content": "Of course! What would you like to know?"},
            {"role": "user", "content": "Explain quadratic equations."}
        ]
        response = await client.chat(messages)
        print(response.choices[0].message.content)
    finally:
        await client.close()

asyncio.run(main())
```

## Streaming Responses

### Stream Text Generation

#### Synchronous (Easier for Beginners)

```python
from locallab_client import SyncLocalLabClient

def stream_example():
    client = SyncLocalLabClient("http://localhost:8000")  # or "https://your-ngrok-url.ngrok.app"
    try:
        print("Generating story: ", end="", flush=True)
        for token in client.stream_generate("Once upon a time"):
            print(token, end="", flush=True)
        print()  # New line at end
    finally:
        client.close()

# Call the function directly
stream_example()
```

#### Asynchronous (For Advanced Users)

```python
import asyncio
from locallab_client import LocalLabClient

async def stream_example():
    client = LocalLabClient("http://localhost:8000")  # or "https://your-ngrok-url.ngrok.app"
    try:
        print("Generating story: ", end="", flush=True)
        async for token in client.stream_generate("Once upon a time"):
            print(token, end="", flush=True)
        print()  # New line at end
    finally:
        await client.close()

# Run the async function
asyncio.run(stream_example())
```

### Stream Chat

#### Synchronous (Easier for Beginners)

```python
from locallab_client import SyncLocalLabClient

client = SyncLocalLabClient("http://localhost:8000")
try:
    print("Chat response: ", end="", flush=True)
    for token in client.stream_chat([
        {"role": "user", "content": "Tell me a story"}
    ]):
        print(token, end="", flush=True)
    print()  # New line at end
finally:
    client.close()
```

#### Asynchronous (For Advanced Users)

```python
import asyncio
from locallab_client import LocalLabClient

async def stream_chat():
    client = LocalLabClient("http://localhost:8000")
    try:
        print("Chat response: ", end="", flush=True)
        async for token in client.stream_chat([
            {"role": "user", "content": "Tell me a story"}
        ]):
            print(token, end="", flush=True)
        print()  # New line at end
    finally:
        await client.close()

# Run the async function
asyncio.run(stream_chat())
```

### Stream Text Generation with Context

#### Synchronous (Easier for Beginners)

```python
from locallab_client import SyncLocalLabClient

def stream_with_context():
    client = SyncLocalLabClient("http://localhost:8000")
    try:
        # First response
        print("Q: Tell me a story about a robot")
        for token in client.stream_generate("Tell me a story about a robot"):
            print(token, end="", flush=True)
        print("\n")

        # Follow-up question (will have context from previous response)
        print("Q: What happens next in the story?")
        for token in client.stream_generate("What happens next in the story?"):
            print(token, end="", flush=True)
        print("\n")
    finally:
        client.close()

# Call the function directly
stream_with_context()
```

#### Asynchronous (For Advanced Users)

```python
import asyncio
from locallab_client import LocalLabClient

async def stream_with_context():
    client = LocalLabClient("http://localhost:8000")
    try:
        # First response
        print("Q: Tell me a story about a robot")
        async for token in client.stream_generate("Tell me a story about a robot"):
            print(token, end="", flush=True)
        print("\n")

        # Follow-up question (will have context from previous response)
        print("Q: What happens next in the story?")
        async for token in client.stream_generate("What happens next in the story?"):
            print(token, end="", flush=True)
        print("\n")
    finally:
        await client.close()

# Run the async function
asyncio.run(stream_with_context())
```

The client maintains a context of recent exchanges, allowing for more coherent follow-up responses. The context is automatically managed and includes up to 5 previous exchanges.

## Batch Processing

### Process Multiple Prompts

#### Synchronous (Easier for Beginners)

```python
from locallab_client import SyncLocalLabClient

def batch_example():
    client = SyncLocalLabClient("http://localhost:8000")
    try:
        prompts = [
            "Write a haiku",
            "Tell a joke",
            "Give a fun fact"
        ]

        responses = client.batch_generate(prompts)

        for prompt, response in zip(prompts, responses["responses"]):
            print(f"\nPrompt: {prompt}")
            print(f"Response: {response}")
    finally:
        client.close()

# Call the function directly
batch_example()
```

#### Asynchronous (For Advanced Users)

```python
import asyncio
from locallab_client import LocalLabClient

async def batch_example():
    client = LocalLabClient("http://localhost:8000")
    try:
        prompts = [
            "Write a haiku",
            "Tell a joke",
            "Give a fun fact"
        ]

        responses = await client.batch_generate(prompts)

        for prompt, response in zip(prompts, responses["responses"]):
            print(f"\nPrompt: {prompt}")
            print(f"Response: {response}")
    finally:
        await client.close()

# Run the async function
asyncio.run(batch_example())
```

## Model Management

### Load Different Models

#### Synchronous (Easier for Beginners)

```python
from locallab_client import SyncLocalLabClient

def model_management():
    client = SyncLocalLabClient("http://localhost:8000")  # or "https://your-ngrok-url.ngrok.app"
    try:
        # List available models
        models = client.list_models()
        print("Available models:", models)

        # Load a specific model
        client.load_model("microsoft/phi-2")

        # Get current model info
        model_info = client.get_current_model()
        print("Current model:", model_info)

        # Generate with loaded model
        response = client.generate("Hello!")
        print(response)

    finally:
        client.close()

# Call the function directly
model_management()
```

#### Asynchronous (For Advanced Users)

```python
import asyncio
from locallab_client import LocalLabClient

async def model_management():
    client = LocalLabClient("http://localhost:8000")  # or "https://your-ngrok-url.ngrok.app"
    try:
        # List available models
        models = await client.list_models()
        print("Available models:", models)

        # Load a specific model
        await client.load_model("microsoft/phi-2")

        # Get current model info
        model_info = await client.get_current_model()
        print("Current model:", model_info)

        # Generate with loaded model
        response = await client.generate("Hello!")
        print(response)

    finally:
        await client.close()

# Run the async function
asyncio.run(model_management())
```

## Error Handling

### Handle Common Errors

#### Synchronous (Easier for Beginners)

```python
from locallab_client import SyncLocalLabClient

def error_handling():
    try:
        # Try to connect
        client = SyncLocalLabClient("http://localhost:8000")  # or "https://your-ngrok-url.ngrok.app"

        # Check server health
        if not client.health_check():
            print("Server is not responding")
            return

        # Try generation
        try:
            response = client.generate("Hello!")
            print(response)
        except Exception as e:
            print(f"Generation failed: {str(e)}")

    except ConnectionError:
        print("Could not connect to server")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()

# Call the function directly
error_handling()
```

#### Asynchronous (For Advanced Users)

```python
import asyncio
from locallab_client import LocalLabClient

async def error_handling():
    try:
        # Try to connect
        client = LocalLabClient("http://localhost:8000")  # or "https://your-ngrok-url.ngrok.app"

        # Check server health
        if not await client.health_check():
            print("Server is not responding")
            return

        # Try generation
        try:
            response = await client.generate("Hello!")
            print(response)
        except Exception as e:
            print(f"Generation failed: {str(e)}")

    except ConnectionError:
        print("Could not connect to server")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
    finally:
        if 'client' in locals():
            await client.close()

# Run the async function
asyncio.run(error_handling())
```

## Best Practices

### For Both Client Types

1. **Always Close the Client**

   ```python
   # For synchronous client
   try:
       # Your code here
   finally:
       client.close()

   # For asynchronous client
   try:
       # Your code here
   finally:
       await client.close()
   ```

2. **Check Server Health**

   ```python
   # For synchronous client
   if not client.health_check():
       print("Server not ready")
       return

   # For asynchronous client
   if not await client.health_check():
       print("Server not ready")
       return
   ```

3. **Use Proper Error Handling**

   ```python
   # For synchronous client
   try:
       response = client.generate(prompt)
   except Exception as e:
       print(f"Error: {str(e)}")

   # For asynchronous client
   try:
       response = await client.generate(prompt)
   except Exception as e:
       print(f"Error: {str(e)}")
   ```

4. **Monitor System Resources**

   ```python
   # For synchronous client
   info = client.get_system_info()
   print(f"Memory usage: {info.memory_usage}%")

   # For asynchronous client
   info = await client.get_system_info()
   print(f"Memory usage: {info.memory_usage}%")
   ```

### Choosing Between Sync and Async

- **Use SyncLocalLabClient when:**

  - You're new to Python
  - You don't need concurrent operations
  - You want simpler code without async/await
  - You're using a regular Python script

- **Use LocalLabClient when:**
  - You're familiar with async/await
  - You need to perform concurrent operations
  - You're building an async application
  - You're using frameworks like FastAPI or asyncio

## Next Steps

- Check the [API Reference](./API.md) for detailed parameter information
- Learn about [Advanced Features](./advanced.md)
- See [Performance Guide](../features/performance.md) for optimization tips
- Visit [Troubleshooting](./troubleshooting.md) if you encounter issues

---

Need more examples? Check our [Community Examples](https://github.com/UtkarshTheDev/LocalLab/discussions/categories/show-and-tell) or ask in our [Discussion Forum](https://github.com/UtkarshTheDev/LocalLab/discussions).
