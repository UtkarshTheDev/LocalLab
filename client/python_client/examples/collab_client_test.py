import asyncio
from locallab_client import LocalLabClient


async def main():
    # Initialize client with URL string
    client = LocalLabClient("LOCALLAB_SERVER_NGROK_URL")

    try:
        # Test health check
        healthy = await client.health_check()
        print(f"Server health: {healthy}\n")

        # Test basic generation
        response = await client.generate("Tell me about React Native?")
        print("Generation response:")
        print(response.text)
        print()

        # Test streaming with proper spacing and error handling
        print("Streaming response:")
        try:
            async for token in client.stream_generate("What are you working on? Tell me about your current project."):
                if token.startswith("Error:"):
                    print(f"\n{token}")
                    break
                print(token, end="", flush=True)
            print("\n")
        except Exception as e:
            print(f"\nStreaming error: {str(e)}")

        # Test chat with context
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Tell me about Paris"},
            {"role": "assistant", "content": "Paris is the capital of France."},
            {"role": "user", "content": "What's the most famous landmark there?"}
        ]
        chat_response = await client.chat(messages)
        print("\nChat response:")
        print(chat_response.choices[0].message.content)

    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
