"""
Example usage of the unified LocalLab client.

This example demonstrates how the same client can be used both
synchronously and asynchronously.
"""

import asyncio
from client.python_client import LocalLabClient


# Synchronous usage example
def sync_example():
    print("\n=== Synchronous Usage Example ===")
    
    # Create client - no async/await needed!
    client = LocalLabClient("http://localhost:8000")
    
    try:
        # Check if the server is healthy
        if not client.health_check():
            print("Server is not healthy. Please check if it's running.")
            return
        
        # Get information about the current model
        model_info = client.get_current_model()
        print(f"Current model: {model_info['name']}")
        
        # Basic text generation
        print("\nGenerating text...")
        response = client.generate("Write a short story about a robot")
        print(f"Response: {response}")
        
        # Streaming text generation
        print("\nStreaming text generation...")
        print("Response: ", end="", flush=True)
        for chunk in client.stream_generate("Write a haiku about nature"):
            print(chunk, end="", flush=True)
        print()  # Add a newline at the end
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close the client
        client.close()


# Asynchronous usage example
async def async_example():
    print("\n=== Asynchronous Usage Example ===")
    
    # Create client
    client = LocalLabClient("http://localhost:8000")
    
    try:
        # Check if the server is healthy
        if not await client.health_check():
            print("Server is not healthy. Please check if it's running.")
            return
        
        # Get information about the current model
        model_info = await client.get_current_model()
        print(f"Current model: {model_info['name']}")
        
        # Basic text generation
        print("\nGenerating text...")
        response = await client.generate("Write a short story about a robot")
        print(f"Response: {response}")
        
        # Streaming text generation
        print("\nStreaming text generation...")
        print("Response: ", end="", flush=True)
        async for chunk in client.stream_generate("Write a haiku about nature"):
            print(chunk, end="", flush=True)
        print()  # Add a newline at the end
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close the client
        await client.close()


# Context manager examples
def sync_context_example():
    print("\n=== Synchronous Context Manager Example ===")
    
    # Use the client as a context manager
    with LocalLabClient("http://localhost:8000") as client:
        # Check if the server is healthy
        if not client.health_check():
            print("Server is not healthy. Please check if it's running.")
            return
        
        # Basic text generation
        print("\nGenerating text...")
        response = client.generate("Write a short story about a robot")
        print(f"Response: {response}")
    
    # Client is automatically closed when exiting the context


async def async_context_example():
    print("\n=== Asynchronous Context Manager Example ===")
    
    # Use the client as an async context manager
    async with LocalLabClient("http://localhost:8000") as client:
        # Check if the server is healthy
        if not await client.health_check():
            print("Server is not healthy. Please check if it's running.")
            return
        
        # Basic text generation
        print("\nGenerating text...")
        response = await client.generate("Write a short story about a robot")
        print(f"Response: {response}")
    
    # Client is automatically closed when exiting the context


# Run all examples
def main():
    # Run the synchronous example
    sync_example()
    
    # Run the synchronous context manager example
    sync_context_example()
    
    # Run the asynchronous examples
    asyncio.run(async_example())
    asyncio.run(async_context_example())


if __name__ == "__main__":
    main()
