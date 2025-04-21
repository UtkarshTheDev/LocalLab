"""
Synchronous client for LocalLab API.
This module provides a synchronous wrapper around the async LocalLabClient.
"""

import asyncio
import threading
import sys
import os
from typing import List, Dict, Any, Optional, Generator, Union
from concurrent.futures import ThreadPoolExecutor

# Make sure we can import the client
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import the client directly
import client
LocalLabClient = client.LocalLabClient


class SyncLocalLabClient:
    """
    Synchronous client for the LocalLab API.

    This class provides a synchronous interface to the LocalLab API by wrapping
    the asynchronous LocalLabClient. It handles all the async/await details
    internally, allowing developers to use the client without async/await syntax.

    Example:
        ```python
        from sync_client import SyncLocalLabClient

        # Create a client
        client = SyncLocalLabClient("http://localhost:8000")

        # Generate text
        response = client.generate("Write a story about a robot")
        print(response)

        # No need to explicitly close the client, it will be closed automatically
        ```
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        Initialize the synchronous client.

        Args:
            base_url: The base URL of the LocalLab server
            timeout: Request timeout in seconds
        """
        self._async_client = LocalLabClient(base_url, timeout)
        self._loop = None
        self._thread = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._lock = threading.RLock()
        self._initialize_event_loop()

    def _initialize_event_loop(self):
        """Initialize a dedicated event loop in a separate thread."""
        with self._lock:
            if self._loop is None or self._thread is None:
                self._loop = asyncio.new_event_loop()

                def run_event_loop():
                    asyncio.set_event_loop(self._loop)
                    self._loop.run_forever()

                self._thread = threading.Thread(target=run_event_loop, daemon=True)
                self._thread.start()

    def _run_coroutine(self, coro):
        """Run a coroutine in the event loop thread and return the result."""
        if not self._loop or not self._thread or not self._thread.is_alive():
            self._initialize_event_loop()

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __del__(self):
        """Clean up resources when the object is garbage collected."""
        self.close()

    def close(self):
        """Close the client and clean up resources."""
        with self._lock:
            if self._loop and self._thread and self._thread.is_alive():
                # Run the close coroutine in the event loop
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        self._async_client.close(), self._loop
                    )
                    future.result(timeout=5)  # Wait up to 5 seconds for close to complete
                except Exception:
                    pass  # Ignore errors during cleanup

                # Stop the event loop
                self._loop.call_soon_threadsafe(self._loop.stop)

                # Wait for the thread to finish
                self._thread.join(timeout=1)

                # Clean up
                self._loop = None
                self._thread = None

            # Shutdown the executor
            self._executor.shutdown(wait=False)

    def generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        stream: bool = False,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Union[str, Generator[str, None, None]]:
        """
        Generate text using the model.

        Args:
            prompt: The prompt to generate text from
            model_id: Optional model ID to use
            stream: Whether to stream the response
            max_length: Maximum length of the generated text
            temperature: Temperature for sampling
            top_p: Top-p for nucleus sampling

        Returns:
            If stream=False, returns the generated text as a string.
            If stream=True, returns a generator that yields chunks of text.
        """
        if stream:
            return self.stream_generate(prompt, model_id, max_length, temperature, top_p)

        return self._run_coroutine(
            self._async_client.generate(
                prompt=prompt,
                model_id=model_id,
                stream=False,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p
            )
        )

    def stream_generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: float = 60.0
    ) -> Generator[str, None, None]:
        """
        Stream text generation.

        Args:
            prompt: The prompt to generate text from
            model_id: Optional model ID to use
            max_length: Maximum length of the generated text
            temperature: Temperature for sampling
            top_p: Top-p for nucleus sampling
            timeout: Request timeout in seconds

        Returns:
            A generator that yields chunks of text as they are generated.
        """
        # Create a queue to pass data between the async and sync worlds
        queue = asyncio.Queue()
        stop_event = threading.Event()

        # Define the async producer function
        async def producer():
            try:
                async for chunk in self._async_client.stream_generate(
                    prompt=prompt,
                    model_id=model_id,
                    max_length=max_length,
                    temperature=temperature,
                    top_p=top_p,
                    timeout=timeout
                ):
                    await queue.put(chunk)

                    # Check if consumer has stopped
                    if stop_event.is_set():
                        break

                # Signal end of stream
                await queue.put(None)
            except Exception as e:
                # Put the error in the queue
                await queue.put(f"\nError: {str(e)}")
                await queue.put(None)

        # Start the producer in the event loop
        asyncio.run_coroutine_threadsafe(producer(), self._loop)

        # Define the consumer generator
        def consumer():
            try:
                while True:
                    # Get the next chunk from the queue
                    chunk = self._run_coroutine(queue.get())

                    # None signals end of stream
                    if chunk is None:
                        break

                    yield chunk
            finally:
                # Signal producer to stop if consumer is stopped
                stop_event.set()

        # Return the consumer generator
        return consumer()

    def chat(
        self,
        messages: List[Dict[str, str]],
        model_id: Optional[str] = None,
        stream: bool = False,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Union[Dict[str, Any], Generator[Dict[str, Any], None, None]]:
        """
        Chat completion.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model_id: Optional model ID to use
            stream: Whether to stream the response
            max_length: Maximum length of the generated text
            temperature: Temperature for sampling
            top_p: Top-p for nucleus sampling

        Returns:
            If stream=False, returns the chat completion response.
            If stream=True, returns a generator that yields chunks of the response.
        """
        if stream:
            return self.stream_chat(messages, model_id, max_length, temperature, top_p)

        return self._run_coroutine(
            self._async_client.chat(
                messages=messages,
                model_id=model_id,
                stream=False,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p
            )
        )

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model_id: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream chat completion.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model_id: Optional model ID to use
            max_length: Maximum length of the generated text
            temperature: Temperature for sampling
            top_p: Top-p for nucleus sampling

        Returns:
            A generator that yields chunks of the chat completion response.
        """
        # Create a queue to pass data between the async and sync worlds
        queue = asyncio.Queue()
        stop_event = threading.Event()

        # Define the async producer function
        async def producer():
            try:
                async for chunk in self._async_client.stream_chat(
                    messages=messages,
                    model_id=model_id,
                    max_length=max_length,
                    temperature=temperature,
                    top_p=top_p
                ):
                    await queue.put(chunk)

                    # Check if consumer has stopped
                    if stop_event.is_set():
                        break

                # Signal end of stream
                await queue.put(None)
            except Exception as e:
                # Put the error in the queue
                await queue.put({"error": str(e)})
                await queue.put(None)

        # Start the producer in the event loop
        asyncio.run_coroutine_threadsafe(producer(), self._loop)

        # Define the consumer generator
        def consumer():
            try:
                while True:
                    # Get the next chunk from the queue
                    chunk = self._run_coroutine(queue.get())

                    # None signals end of stream
                    if chunk is None:
                        break

                    yield chunk
            finally:
                # Signal producer to stop if consumer is stopped
                stop_event.set()

        # Return the consumer generator
        return consumer()

    def batch_generate(
        self,
        prompts: List[str],
        model_id: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Dict[str, List[str]]:
        """
        Generate text for multiple prompts in parallel.

        Args:
            prompts: List of prompts to generate text from
            model_id: Optional model ID to use
            max_length: Maximum length of the generated text
            temperature: Temperature for sampling
            top_p: Top-p for nucleus sampling

        Returns:
            Dictionary with the generated responses.
        """
        return self._run_coroutine(
            self._async_client.batch_generate(
                prompts=prompts,
                model_id=model_id,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p
            )
        )

    def load_model(self, model_id: str) -> bool:
        """
        Load a specific model.

        Args:
            model_id: The ID of the model to load

        Returns:
            True if the model was loaded successfully.
        """
        return self._run_coroutine(self._async_client.load_model(model_id))

    def get_current_model(self) -> Dict[str, Any]:
        """
        Get information about the currently loaded model.

        Returns:
            Dictionary with information about the current model.
        """
        return self._run_coroutine(self._async_client.get_current_model())

    def list_models(self) -> Dict[str, Any]:
        """
        List all available models.

        Returns:
            Dictionary with information about available models.
        """
        return self._run_coroutine(self._async_client.list_models())

    def health_check(self) -> bool:
        """
        Check if the server is healthy.

        Returns:
            True if the server is healthy.
        """
        return self._run_coroutine(self._async_client.health_check())

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get detailed system information.

        Returns:
            Dictionary with system information.
        """
        return self._run_coroutine(self._async_client.get_system_info())

    def unload_model(self) -> bool:
        """
        Unload the current model to free up resources.

        Returns:
            True if the model was unloaded successfully.
        """
        return self._run_coroutine(self._async_client.unload_model())
