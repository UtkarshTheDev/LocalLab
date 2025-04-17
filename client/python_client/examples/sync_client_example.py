"""
Example usage of the synchronous LocalLab client.

This example demonstrates how to use the SyncLocalLabClient to interact with
the LocalLab server without using async/await syntax.
"""

from client.python_client import SyncLocalLabClient


def main():
    # Initialize client - no async/await needed!
    client = SyncLocalLabClient("http://localhost:8000")
    
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
        
        # List available models
        print("\nAvailable models:")
        models = client.list_models()
        for model in models:
            print(f"- {model}")
        
        # Get system information
        print("\nSystem information:")
        system_info = client.get_system_info()
        print(f"CPU: {system_info['cpu']}")
        print(f"RAM: {system_info['memory']}")
        print(f"GPU: {system_info.get('gpu', 'None')}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # No need to explicitly close the client, it will be closed automatically
        # But you can close it explicitly if you want
        client.close()


if __name__ == "__main__":
    main()
