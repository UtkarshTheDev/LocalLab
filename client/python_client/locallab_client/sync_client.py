"""
Synchronous client for LocalLab API.
This module provides a synchronous wrapper around the async LocalLabClient.
"""

import asyncio
import threading
import sys
import os
import time
from typing import List, Dict, Any, Optional, Generator, Union
from concurrent.futures import ThreadPoolExecutor
import logging

# Import from the package root
from .client import LocalLabClient, LocalLabConfig

logger = logging.getLogger(__name__)

class SyncLocalLabClient:
    """
    Synchronous client for the LocalLab API.
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        """Initialize the synchronous client."""
        self._async_client = LocalLabClient(LocalLabConfig(base_url=base_url, timeout=timeout))
        self._loop = None
        self._thread = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._lock = threading.RLock()
        self._is_closed = False
        self._initialize_event_loop()

    def _initialize_event_loop(self):
        """Initialize a dedicated event loop in a separate thread with error handling."""
        with self._lock:
            if self._loop is None or self._thread is None:
                try:
                    self._loop = asyncio.new_event_loop()

                    def run_event_loop():
                        try:
                            asyncio.set_event_loop(self._loop)
                            self._loop.run_forever()
                        except Exception as e:
                            logger.error(f"Event loop error: {str(e)}")
                        finally:
                            try:
                                # Cancel all running tasks
                                pending = asyncio.all_tasks(self._loop)
                                for task in pending:
                                    task.cancel()
                                # Run loop until tasks are cancelled
                                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                                self._loop.close()
                            except Exception as e:
                                logger.error(f"Error during event loop cleanup: {str(e)}")

                    self._thread = threading.Thread(target=run_event_loop, daemon=True)
                    self._thread.start()
                except Exception as e:
                    logger.error(f"Failed to initialize event loop: {str(e)}")
                    raise RuntimeError(f"Failed to initialize client: {str(e)}")

    def _ensure_connection(self):
        """Ensure the client is connected and ready."""
        if self._is_closed:
            raise RuntimeError("Client is closed")
        if not self._loop or not self._thread or not self._thread.is_alive():
            self._initialize_event_loop()

    def _run_coroutine(self, coro, timeout: Optional[float] = None):
        """Run a coroutine in the event loop thread with timeout and error handling."""
        self._ensure_connection()

        try:
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return future.result(timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError("Operation timed out")
        except Exception as e:
            logger.error(f"Error running coroutine: {str(e)}")
            raise

    def __enter__(self):
        """Context manager entry with connection validation."""
        self._ensure_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with proper cleanup."""
        self.close()

    def __del__(self):
        """Cleanup on garbage collection."""
        if not self._is_closed:
            self.close()

    def close(self):
        """Close the client with proper cleanup of all resources."""
        with self._lock:
            if not self._is_closed:
                try:
                    # Close async client first
                    if self._loop and self._thread and self._thread.is_alive():
                        try:
                            future = asyncio.run_coroutine_threadsafe(
                                self._async_client.close(), self._loop
                            )
                            future.result(timeout=5)
                        except Exception as e:
                            logger.error(f"Error closing async client: {str(e)}")

                    # Stop event loop
                    if self._loop and not self._loop.is_closed():
                        self._loop.call_soon_threadsafe(self._loop.stop)

                    # Wait for thread to finish
                    if self._thread and self._thread.is_alive():
                        self._thread.join(timeout=1)

                    # Clean up
                    self._loop = None
                    self._thread = None

                    # Shutdown executor
                    self._executor.shutdown(wait=False)

                except Exception as e:
                    logger.error(f"Error during client cleanup: {str(e)}")
                finally:
                    self._is_closed = True

    def generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        stream: bool = False,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        repetition_penalty: float = 1.15,  # Increased repetition penalty for better quality
        top_k: int = 80  # Added top_k parameter for better quality
    ) -> Union[str, Generator[str, None, None]]:
        """
        Generate text using the model with improved quality settings.

        Args:
            prompt: The prompt to generate text from
            model_id: Optional model ID to use
            stream: Whether to stream the response
            max_length: Maximum length of the generated text (defaults to 1024 if None)
            temperature: Temperature for sampling
            top_p: Top-p for nucleus sampling
            repetition_penalty: Penalty for repetition (higher values = less repetition)

        Returns:
            If stream=False, returns the generated text as a string.
            If stream=True, returns a generator that yields chunks of text.
        """
        # Use a higher max_length by default to ensure complete responses
        if max_length is None:
            max_length = 4096  # Default to 4096 tokens for more complete responses

        if stream:
            return self.stream_generate(
                prompt=prompt,
                model_id=model_id,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                repetition_penalty=repetition_penalty,
                top_k=top_k
            )

        return self._run_coroutine(
            self._async_client.generate(
                prompt=prompt,
                model_id=model_id,
                stream=False,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                repetition_penalty=repetition_penalty,
                top_k=top_k,
                timeout=180.0  # Increased timeout for more complete responses (3 minutes)
            )
        )

    def stream_generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: float = 300.0,  # Increased timeout for more complete responses (5 minutes)
        repetition_penalty: float = 1.15,  # Increased repetition penalty for better quality
        top_k: int = 80  # Added top_k parameter for better quality
    ) -> Generator[str, None, None]:
        """
        Stream text generation with improved quality and reliability.

        Args:
            prompt: The prompt to generate text from
            model_id: Optional model ID to use
            max_length: Maximum length of the generated text (defaults to 1024 if None)
            temperature: Temperature for sampling
            top_p: Top-p for nucleus sampling
            timeout: Request timeout in seconds
            repetition_penalty: Penalty for repetition (higher values = less repetition)

        Returns:
            A generator that yields chunks of text as they are generated.
        """
        # Use a higher max_length by default to ensure complete responses
        if max_length is None:
            max_length = 4096  # Default to 4096 tokens for more complete responses

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
                    timeout=timeout,
                    retry_count=3,  # Increased retry count for better reliability
                    repetition_penalty=repetition_penalty,  # Pass the repetition penalty parameter
                    top_k=top_k  # Pass the top_k parameter
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
        top_p: float = 0.9,
        repetition_penalty: float = 1.15,  # Increased repetition penalty for better quality
        top_k: int = 80  # Added top_k parameter for better quality
    ) -> Union[Dict[str, Any], Generator[Dict[str, Any], None, None]]:
        """
        Chat completion with improved quality settings.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model_id: Optional model ID to use
            stream: Whether to stream the response
            max_length: Maximum length of the generated text (defaults to 1024 if None)
            temperature: Temperature for sampling
            top_p: Top-p for nucleus sampling
            repetition_penalty: Penalty for repetition (higher values = less repetition)

        Returns:
            If stream=False, returns the chat completion response.
            If stream=True, returns a generator that yields chunks of the response.
        """
        # Use a higher max_length by default to ensure complete responses
        if max_length is None:
            max_length = 4096  # Default to 4096 tokens for more complete responses

        if stream:
            return self.stream_chat(
                messages=messages,
                model_id=model_id,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                timeout=300.0,  # Increased timeout for more complete responses (5 minutes)
                repetition_penalty=repetition_penalty,
                top_k=top_k
            )

        return self._run_coroutine(
            self._async_client.chat(
                messages=messages,
                model_id=model_id,
                stream=False,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                timeout=180.0,  # Increased timeout for more complete responses (3 minutes)
                repetition_penalty=repetition_penalty,
                top_k=top_k
            )
        )

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model_id: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: float = 300.0,  # Increased timeout for more complete responses (5 minutes)
        repetition_penalty: float = 1.15,  # Added repetition penalty for better quality
        top_k: int = 80  # Added top_k parameter for better quality
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream chat completion with improved quality and reliability.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model_id: Optional model ID to use
            max_length: Maximum length of the generated text (defaults to 1024 if None)
            temperature: Temperature for sampling
            top_p: Top-p for nucleus sampling
            timeout: Request timeout in seconds

        Returns:
            A generator that yields chunks of the chat completion response.
        """
        # Use a higher max_length by default to ensure complete responses
        if max_length is None:
            max_length = 4096  # Default to 4096 tokens for more complete responses

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
                    top_p=top_p,
                    timeout=timeout,
                    retry_count=3,  # Increased retry count for better reliability
                    repetition_penalty=repetition_penalty,
                    top_k=top_k
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
        top_p: float = 0.9,
        repetition_penalty: float = 1.15,  # Increased repetition penalty for better quality
        top_k: int = 80,  # Added top_k parameter for better quality
        timeout: float = 300.0  # Added timeout parameter (5 minutes)
    ) -> Dict[str, List[str]]:
        """
        Generate text for multiple prompts in parallel with improved quality settings.

        Args:
            prompts: List of prompts to generate text from
            model_id: Optional model ID to use
            max_length: Maximum length of the generated text (defaults to 1024 if None)
            temperature: Temperature for sampling
            top_p: Top-p for nucleus sampling
            repetition_penalty: Penalty for repetition (higher values = less repetition)

        Returns:
            Dictionary with the generated responses.
        """
        # Use a higher max_length by default to ensure complete responses
        if max_length is None:
            max_length = 4096  # Default to 4096 tokens for more complete responses

        return self._run_coroutine(
            self._async_client.batch_generate(
                prompts=prompts,
                model_id=model_id,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                repetition_penalty=repetition_penalty,
                top_k=top_k,
                timeout=timeout  # Use the provided timeout parameter
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
