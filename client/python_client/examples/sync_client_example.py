"""
Example usage of the synchronous LocalLab client.

This example demonstrates how to use the SyncLocalLabClient to interact with
the LocalLab server without using async/await syntax.
"""

import sys
import os

# Add the parent directory to the path so we can import the client
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Try different import approaches
try:
    # First try the installed package
    from locallab_client import SyncLocalLabClient
except ImportError:
    try:
        # Then try direct import
        from sync_wrapper import SyncLocalLabClient
    except ImportError:
        try:
            # Then try relative import
            import sys, os
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from sync_wrapper import SyncLocalLabClient
        except ImportError:
            print("LocalLab client not found. Please install it with:")
            print("pip install locallab-client")
            sys.exit(1)


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

        # Chat completion
        print("\nChat completion...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Tell me a joke about programming."}
        ]
        response = client.chat(messages)
        print(f"Response: {response['choices'][0]['message']['content']}")

        # Batch generation
        print("\nBatch generation...")
        prompts = [
            "Write a haiku",
            "Tell a joke",
            "Give a fun fact"
        ]
        responses = client.batch_generate(prompts)
        for prompt, response in zip(prompts, responses["responses"]):
            print(f"\nPrompt: {prompt}")
            print(f"Response: {response}")

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
        # Always close the client when done
        client.close()


# Example without context manager
def simple_example():
    """Example without using context manager."""
    print("\n=== Simple Example ===")

    # Create the client directly
    client = SyncLocalLabClient("http://localhost:8000")

    try:
        # Check if the server is healthy
        if not client.health_check():
            print("Server is not healthy. Please check if it's running.")
            return

        # Generate text
        response = client.generate("Write a short poem")
        print(f"Response: {response}")
    finally:
        # Always close the client when done
        client.close()
        print("Client closed.")


if __name__ == "__main__":
    # Run the examples
    main()
    simple_example()
