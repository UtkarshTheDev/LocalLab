import aiohttp
import asyncio
import atexit
import weakref
import warnings
import threading
import time
from typing import Optional, AsyncGenerator, Dict, Any, List, Set, ClassVar, Generator, Union
import json

from .dual_mode import dual_mode

# Global registry to track all active client sessions
_active_clients: Set[weakref.ReferenceType] = set()
_registry_lock = threading.RLock()
_cleanup_task = None
_event_loop = None

# Function to close all active sessions at program exit
async def _close_all_sessions():
    """Close all active client sessions"""
    with _registry_lock:
        # Make a copy of the set to avoid modification during iteration
        clients = set(_active_clients)

    for client_ref in clients:
        client = client_ref()
        if client is not None and client._session is not None:
            try:
                await client.close()
            except Exception as e:
                warnings.warn(f"Error closing client session: {e}")

# Register the atexit handler
def _atexit_handler():
    """Handle cleanup when the program exits"""
    # Create a new event loop for the cleanup
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_close_all_sessions())
    except Exception as e:
        warnings.warn(f"Error during session cleanup: {e}")
    finally:
        loop.close()

# Register the atexit handler
atexit.register(_atexit_handler)

# Start a background task to periodically check for unused sessions
def _start_cleanup_task():
    """Start a background task to clean up unused sessions"""
    global _cleanup_task, _event_loop

    if _cleanup_task is None or _cleanup_task.done():
        # Create a new event loop for the background task
        if _event_loop is None or _event_loop.is_closed():
            _event_loop = asyncio.new_event_loop()

        async def cleanup_loop():
            while True:
                await asyncio.sleep(60)  # Check every minute
                await _close_all_sessions()

        # Run the cleanup loop in a separate thread
        def run_cleanup_loop():
            asyncio.set_event_loop(_event_loop)
            _event_loop.run_until_complete(cleanup_loop())

        cleanup_thread = threading.Thread(target=run_cleanup_loop, daemon=True)
        cleanup_thread.start()
        _cleanup_task = asyncio.Future()

# Initialize the cleanup task
_start_cleanup_task()

@dual_mode
class LocalLabClient:
    """Python client for the LocalLab API with automatic session management

    This client can be used both synchronously and asynchronously:

    Async usage:
    ```python
    client = LocalLabClient("http://localhost:8000")
    response = await client.generate("Hello, world!")
    await client.close()
    ```

    Sync usage:
    ```python
    client = LocalLabClient("http://localhost:8000")
    response = client.generate("Hello, world!")
    client.close()
    ```
    """

    # Class variable to track the last activity time
    _last_activity_times: ClassVar[Dict[int, float]] = {}

    def __init__(self, base_url: str, timeout: float = 30.0, auto_close: bool = True):
        """Initialize the client with the server's base URL

        Args:
            base_url: The base URL of the LocalLab server
            timeout: Request timeout in seconds
            auto_close: Whether to automatically close the session when unused
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session = None
        self._auto_close = auto_close
        self._closed = False

        # Register this client in the global registry
        if self._auto_close:
            with _registry_lock:
                _active_clients.add(weakref.ref(self, self._cleanup_callback))

        # Update last activity time
        self._update_activity()

    def _update_activity(self):
        """Update the last activity time for this client"""
        LocalLabClient._last_activity_times[id(self)] = time.time()

    @classmethod
    def _cleanup_callback(cls, ref):
        """Callback when a client is garbage collected"""
        with _registry_lock:
            if ref in _active_clients:
                _active_clients.remove(ref)

        # Remove from activity times
        client_id = id(ref)
        if client_id in cls._last_activity_times:
            del cls._last_activity_times[client_id]

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    def __enter__(self):
        """Synchronous context manager entry"""
        # The dual_mode decorator will handle running connect() synchronously
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Synchronous context manager exit"""
        # The dual_mode decorator will handle running close() synchronously
        self.close()

    def __del__(self):
        """Attempt to close the session when the client is garbage collected"""
        if not self._closed and self._session is not None:
            # We can't await in __del__, but the dual_mode decorator will handle it
            try:
                self.close()
            except Exception:
                # If that fails, just issue a warning
                warnings.warn(
                    "LocalLabClient was garbage collected with an open session. "
                    "Please use 'client.close()' or 'with LocalLabClient(...) as client:' "
                    "to properly close the session."
                )

    async def connect(self):
        """Create aiohttp session if it doesn't exist"""
        self._update_activity()
        if not self._session:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
            self._closed = False

    async def close(self):
        """Close aiohttp session"""
        if self._session and not self._closed:
            await self._session.close()
            self._session = None
            self._closed = True

            # Remove from registry
            with _registry_lock:
                for ref in list(_active_clients):
                    if ref() is self:
                        _active_clients.remove(ref)
                        break

    async def generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        stream: bool = False,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """Generate text using the model"""
        # Update activity timestamp
        self._update_activity()

        payload = {
            "prompt": prompt,
            "model_id": model_id,
            "stream": stream,
            "max_length": max_length,
            "temperature": temperature,
            "top_p": top_p
        }

        if stream:
            return self.stream_generate(prompt, model_id, max_length, temperature, top_p)

        await self.connect()
        async with self._session.post(f"{self.base_url}/generate", json=payload) as response:
            if response.status != 200:
                raise Exception(f"Generation failed: {await response.text()}")

            data = await response.json()
            return data["response"]

    async def stream_generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: float = 60.0  # Add timeout parameter with a default of 60 seconds
    ) -> AsyncGenerator[str, None]:
        """Stream text generation with token-level streaming and improved error handling"""
        # Update activity timestamp
        self._update_activity()

        payload = {
            "prompt": prompt,
            "model_id": model_id,
            "stream": True,
            "max_length": max_length,
            "temperature": temperature,
            "top_p": top_p
        }

        # Create a timeout for this specific request
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            await self.connect()
            async with self._session.post(
                f"{self.base_url}/generate",
                json=payload,
                timeout=request_timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Streaming failed: {error_text}")

                # Track if we've seen any data to detect early disconnections
                received_data = False

                try:
                    # Process the streaming response
                    async for line in response.content:
                        if line:
                            received_data = True
                            text = line.decode("utf-8").strip()

                            # Check for error messages
                            if text.startswith("\nError:"):
                                raise Exception(text.replace("\nError: ", ""))

                            yield text

                    # If we didn't receive any data, the stream might have ended unexpectedly
                    if not received_data:
                        yield "\nError: Stream ended unexpectedly without returning any data"

                except Exception as stream_error:
                    # Handle errors during streaming
                    if "timeout" in str(stream_error).lower():
                        yield "\nError: Stream timed out. The server took too long to respond."
                    else:
                        yield f"\nError: {str(stream_error)}"
        except Exception as e:
            # Handle connection errors
            if "timeout" in str(e).lower():
                yield "\nError: Connection timed out. The server took too long to respond."
            else:
                yield f"\nError: {str(e)}"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model_id: Optional[str] = None,
        stream: bool = False,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Dict[str, Any]:
        """Chat completion endpoint"""
        # Update activity timestamp
        self._update_activity()

        payload = {
            "messages": messages,
            "model_id": model_id,
            "stream": stream,
            "max_length": max_length,
            "temperature": temperature,
            "top_p": top_p
        }

        if stream:
            return self.stream_chat(messages, model_id, max_length, temperature, top_p)

        await self.connect()
        async with self._session.post(f"{self.base_url}/chat", json=payload) as response:
            if response.status != 200:
                raise Exception(f"Chat completion failed: {await response.text()}")

            return await response.json()

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model_id: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion"""
        # Update activity timestamp
        self._update_activity()

        payload = {
            "messages": messages,
            "model_id": model_id,
            "stream": True,
            "max_length": max_length,
            "temperature": temperature,
            "top_p": top_p
        }

        await self.connect()
        async with self._session.post(f"{self.base_url}/chat", json=payload) as response:
            if response.status != 200:
                raise Exception(f"Chat streaming failed: {await response.text()}")

            async for line in response.content:
                if line:
                    data = json.loads(line.decode("utf-8"))
                    if data == "[DONE]":
                        break
                    yield data

    async def batch_generate(
        self,
        prompts: List[str],
        model_id: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Dict[str, List[str]]:
        """Generate text for multiple prompts in parallel"""
        # Update activity timestamp
        self._update_activity()

        payload = {
            "prompts": prompts,
            "model_id": model_id,
            "max_length": max_length,
            "temperature": temperature,
            "top_p": top_p
        }

        await self.connect()
        async with self._session.post(f"{self.base_url}/generate/batch", json=payload) as response:
            if response.status != 200:
                raise Exception(f"Batch generation failed: {await response.text()}")

            return await response.json()

    async def load_model(self, model_id: str) -> bool:
        """Load a specific model"""
        # Update activity timestamp
        self._update_activity()

        await self.connect()
        async with self._session.post(
            f"{self.base_url}/models/load",
            json={"model_id": model_id}
        ) as response:
            if response.status != 200:
                raise Exception(f"Model loading failed: {await response.text()}")

            data = await response.json()
            return data["status"] == "success"

    async def get_current_model(self) -> Dict[str, Any]:
        """Get information about the currently loaded model"""
        # Update activity timestamp
        self._update_activity()

        await self.connect()
        async with self._session.get(f"{self.base_url}/models/current") as response:
            if response.status != 200:
                raise Exception(f"Failed to get current model: {await response.text()}")

            return await response.json()

    async def list_models(self) -> Dict[str, Any]:
        """List all available models"""
        # Update activity timestamp
        self._update_activity()

        await self.connect()
        async with self._session.get(f"{self.base_url}/models/available") as response:
            if response.status != 200:
                raise Exception(f"Failed to list models: {await response.text()}")

            data = await response.json()
            return data["models"]

    async def health_check(self) -> bool:
        """Check if the server is healthy"""
        # Update activity timestamp
        self._update_activity()

        try:
            await self.connect()
            async with self._session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except Exception:
            return False

    async def get_system_info(self) -> Dict[str, Any]:
        """Get detailed system information"""
        # Update activity timestamp
        self._update_activity()

        await self.connect()
        async with self._session.get(f"{self.base_url}/system/info") as response:
            if response.status != 200:
                raise Exception(f"Failed to get system info: {await response.text()}")

            return await response.json()

    async def unload_model(self) -> bool:
        """Unload the current model to free up resources"""
        # Update activity timestamp
        self._update_activity()

        await self.connect()
        async with self._session.post(f"{self.base_url}/models/unload") as response:
            if response.status != 200:
                raise Exception(f"Failed to unload model: {await response.text()}")

            data = await response.json()
            return data["status"] == "Model unloaded successfully"