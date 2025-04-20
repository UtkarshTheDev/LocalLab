# 🎯 LocalLab Examples Guide

This guide provides practical examples of using LocalLab in your projects. Each example includes code snippets and explanations.

## 📚 Table of Contents

- [Basic Usage](#basic-usage)
- [Text Generation](#text-generation)
- [Chat Completion](#chat-completion)
- [Streaming Responses](#streaming-responses)
- [Batch Processing](#batch-processing)
- [Model Management](#model-management)
- [Error Handling](#error-handling)

## Basic Usage

First, set up your LocalLab environment:

```python
import asyncio
from locallab_client import LocalLabClient

async def main():
    # Initialize client
    client = LocalLabClient("http://localhost:8000") # or "https://your-ngrok-url.ngrok.app"

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

Generate text with default settings:

```python
async def generate_text():
    client = LocalLabClient("http://localhost:8000") # or "https://your-ngrok-url.ngrok.app"
    try:
        response = await client.generate(
            "Write a short story about a robot"
        )
        print(response)
    finally:
        await client.close()
```

### Custom Parameters

Control the generation with parameters:

```python
response = await client.generate(
    prompt="Write a poem about coding",
    temperature=0.7,  # Control creativity (0.0 to 1.0)
    max_length=100,   # Maximum length of response
    top_p=0.9        # Nucleus sampling parameter
)
```

## Chat Completion

### Basic Chat

Have a simple conversation:

```python
async def chat_example():
    client = LocalLabClient("http://localhost:8000") # or "https://your-ngrok-url.ngrok.app"
    try:
        response = await client.chat([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is Python?"}
        ])
        print(response.choices[0].message.content)
    finally:
        await client.close()
```

### Multi-turn Conversation

Maintain a conversation thread:

```python
messages = [
    {"role": "system", "content": "You are a math tutor."},
    {"role": "user", "content": "Can you help me with algebra?"},
    {"role": "assistant", "content": "Of course! What would you like to know?"},
    {"role": "user", "content": "Explain quadratic equations."}
]
response = await client.chat(messages)
```

## Streaming Responses

### Stream Text Generation

Get responses token by token:

```python
async def stream_example():
    client = LocalLabClient("http://localhost:8000") # or "https://your-ngrok-url.ngrok.app"
    try:
        print("Generating story: ", end="", flush=True)
        async for token in client.stream_generate("Once upon a time"):
            print(token, end="", flush=True)
        print()  # New line at end
    finally:
        await client.close()
```

### Stream Chat

Stream chat responses:

```python
async def stream_chat():
    async for token in client.stream_chat([
        {"role": "user", "content": "Tell me a story"}
    ]):
        print(token, end="", flush=True)
```

### Stream Text Generation with Context

The streaming generation now maintains context of the conversation for more coherent responses:

```python
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
```

The client maintains a context of recent exchanges, allowing for more coherent follow-up responses. The context is automatically managed and includes up to 5 previous exchanges.

## Batch Processing

### Process Multiple Prompts

Generate responses for multiple prompts efficiently:

```python
async def batch_example():
    prompts = [
        "Write a haiku",
        "Tell a joke",
        "Give a fun fact"
    ]

    responses = await client.batch_generate(prompts)

    for prompt, response in zip(prompts, responses["responses"]):
        print(f"\nPrompt: {prompt}")
        print(f"Response: {response}")
```

## Model Management

### Load Different Models

Switch between different models:

```python
async def model_management():
    client = LocalLabClient("http://localhost:8000") # or "https://your-ngrok-url.ngrok.app"
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
```

## Error Handling

### Handle Common Errors

Properly handle potential errors:

```python
async def error_handling():
    try:
        # Try to connect
        client = LocalLabClient("http://localhost:8000") # or "https://your-ngrok-url.ngrok.app"

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
        await client.close()
```

## Best Practices

1. **Always Close the Client**

   ```python
   try:
       # Your code here
   finally:
       await client.close()
   ```

2. **Check Server Health**

   ```python
   if not await client.health_check():
       print("Server not ready")
       return
   ```

3. **Use Proper Error Handling**

   ```python
   try:
       response = await client.generate(prompt)
   except Exception as e:
       print(f"Error: {str(e)}")
   ```

4. **Monitor System Resources**
   ```python
   info = await client.get_system_info()
   print(f"Memory usage: {info.memory_usage}%")
   ```

## Next Steps

- Check the [API Reference](./api.md) for detailed parameter information
- Learn about [Advanced Features](./advanced.md)
- See [Performance Guide](../features/performance.md) for optimization tips
- Visit [Troubleshooting](./troubleshooting.md) if you encounter issues

---

Need more examples? Check our [Community Examples](https://github.com/UtkarshTheDev/LocalLab/discussions/categories/show-and-tell) or ask in our [Discussion Forum](https://github.com/UtkarshTheDev/LocalLab/discussions).
