import asyncio
import os
from locallab.client import LocalLabClient

# Get the server URL from environment or user input
SERVER_URL = os.getenv("LOCALLAB_SERVER_URL") or input("Enter the ngrok URL from your Colab notebook: ").strip()
if not SERVER_URL:
    raise ValueError("Server URL is required. Get it from your Colab notebook after starting the server.")

async def main():
    # Initialize client with ngrok URL
    client = LocalLabClient({
        "base_url": SERVER_URL,  # Use the ngrok URL from Colab
        "api_key": os.getenv("LOCALLAB_API_KEY"),
        "timeout": 30.0  # Increased timeout for Colab
    })

    try:
        # Check health
        is_healthy = await client.health_check()
        print("Server health:", is_healthy)

        # List available models
        models = await client.list_models()
        print("Available models:", list(models.keys()))

        # Load a model
        await client.load_model("mistral-7b")
        print("Loaded model: mistral-7b")

        # Basic generation
        response = await client.generate("Hello, how are you?")
        print("Generated response:", response.response)

        # Chat completion
        chat_response = await client.chat([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"},
        ])
        print("Chat response:", chat_response.choices[0].message.content)

        # Streaming generation
        print("\nStreaming response:")
        async for token in client.stream_generate("Tell me a story"):
            print(token, end="", flush=True)
        print("\n")

        # Batch processing
        batch_response = await client.batch_generate([
            "What is 2+2?",
            "Who wrote Romeo and Juliet?",
            "What is the speed of light?",
        ])
        print("Batch responses:")
        for i, response in enumerate(batch_response.responses, 1):
            print(f"{i}. {response}")

        # System information
        system_info = await client.get_system_info()
        print("\nSystem Information:")
        print(f"CPU Usage: {system_info.cpu_usage}%")
        print(f"Memory Usage: {system_info.memory_usage}%")
        if system_info.gpu_info:
            print(f"GPU: {system_info.gpu_info.device}")
            print(f"GPU Memory: {system_info.gpu_info.used_memory}/{system_info.gpu_info.total_memory} MB")
            print(f"GPU Utilization: {system_info.gpu_info.utilization}%")
        print(f"Active Model: {system_info.active_model}")
        print(f"Uptime: {system_info.uptime/3600:.2f} hours")
        print(f"Total Requests: {system_info.request_count}")

        # WebSocket example
        print("\nConnecting to WebSocket...")
        await client.connect_ws()

        async def message_handler(data):
            print("Received message:", data)

        print("Listening for messages (press Ctrl+C to stop)...")
        try:
            await client.on_message(message_handler)
        except KeyboardInterrupt:
            print("\nStopping WebSocket connection...")

    except Exception as e:
        print("Error:", e)
    finally:
        # Clean up
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())