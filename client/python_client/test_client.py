import asyncio
from locallab_client import LocalLabClient

async def test_client(server_url: str):
    """Test the client package functionality"""
    print("Starting client tests...")
    
    # Initialize client
    client = LocalLabClient({
        "base_url": server_url,
        "timeout": 30.0
    })
    
    try:
        # Test 1: Health Check
        print("\n1. Testing health check...")
        is_healthy = await client.health_check()
        print(f"Server health: {'OK' if is_healthy else 'Failed'}")
        
        # Test 2: List Models
        print("\n2. Testing model listing...")
        models = await client.list_models()
        print("Available models:", list(models.keys()))
        
        # Test 3: Basic Generation
        print("\n3. Testing text generation...")
        response = await client.generate(
            "Write a one-sentence story about a robot.",
            {"temperature": 0.7}
        )
        print("Generated text:", response.response)
        
        # Test 4: Chat Completion
        print("\n4. Testing chat completion...")
        chat_response = await client.chat([
            {"role": "user", "content": "What is 2+2?"}
        ])
        print("Chat response:", chat_response.choices[0].message.content)
        
        # Test 5: System Info
        print("\n5. Testing system info...")
        info = await client.get_system_info()
        print(f"CPU Usage: {info.cpu_usage}%")
        print(f"Memory Usage: {info.memory_usage}%")
        if info.gpu_info:
            print(f"GPU Memory: {info.gpu_info.used_memory}/{info.gpu_info.total_memory} MB")
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")
    finally:
        await client.close()
        print("\nTests completed!")

if __name__ == "__main__":
    # Get server URL from user
    server_url = input("Enter the server URL from Colab (e.g., https://xxxx-xx-xx-xxx-xx.ngrok.io): ").strip()
    
    # Run tests
    asyncio.run(test_client(server_url)) 