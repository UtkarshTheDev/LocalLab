"""
Synchronous client for LocalLab API.
This module provides a synchronous wrapper around the async LocalLabClient.
"""

import asyncio
import threading
from typing import List, Dict, Any, Optional, Generator, Union
from concurrent.futures import ThreadPoolExecutor

from .client import LocalLabClient


class SyncLocalLabClient:
    """
    Synchronous client for the LocalLab API.
    
    This class provides a synchronous interface to the LocalLab API by wrapping
    the asynchronous LocalLabClient. It handles all the async/await details
    internally, allowing developers to use the client without async/await syntax.
    
    Example:
        ```python
        from locallab_client import SyncLocalLabClient
        
        # Create a client
        client = SyncLocalLabClient("http://localhost:8000")
        
        # Generate text
        response = client.generate("Write a story about a robot")
        print(response)
        
        # Close the client when done
        client.close()
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
        self._run_coroutine(self._async_client.connect())
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
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
    ) -> str:
        """Generate text using the model."""
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
        """Stream text generation with token-level streaming."""
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
                await queue.put(f"Error: {str(e)}")
                await queue.put(None)
        
        # Start the producer in the background
        asyncio.run_coroutine_threadsafe(producer(), self._loop)
        
        # Yield items from the queue
        try:
            while True:
                # Get the next item from the queue
                item = self._run_coroutine(queue.get())
                
                # None signals the end of the stream
                if item is None:
                    break
                
                yield item
        finally:
            # Signal the producer to stop
            stop_event.set()
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model_id: Optional[str] = None,
        stream: bool = False,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Dict[str, Any]:
        """Chat completion endpoint."""
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
        """Stream chat completion."""
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
        
        # Start the producer in the background
        asyncio.run_coroutine_threadsafe(producer(), self._loop)
        
        # Yield items from the queue
        try:
            while True:
                # Get the next item from the queue
                item = self._run_coroutine(queue.get())
                
                # None signals the end of the stream
                if item is None:
                    break
                
                yield item
        finally:
            # Signal the producer to stop
            stop_event.set()
    
    def batch_generate(
        self,
        prompts: List[str],
        model_id: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Dict[str, List[str]]:
        """Generate text for multiple prompts in parallel."""
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
        """Load a specific model."""
        return self._run_coroutine(
            self._async_client.load_model(model_id)
        )
    
    def get_current_model(self) -> Dict[str, Any]:
        """Get information about the currently loaded model."""
        return self._run_coroutine(
            self._async_client.get_current_model()
        )
    
    def list_models(self) -> Dict[str, Any]:
        """List all available models."""
        return self._run_coroutine(
            self._async_client.list_models()
        )
    
    def health_check(self) -> bool:
        """Check if the server is healthy."""
        return self._run_coroutine(
            self._async_client.health_check()
        )
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get detailed system information."""
        return self._run_coroutine(
            self._async_client.get_system_info()
        )
    
    def unload_model(self) -> bool:
        """Unload the current model to free up resources."""
        return self._run_coroutine(
            self._async_client.unload_model()
        )
