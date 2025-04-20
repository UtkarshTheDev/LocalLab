import aiohttp
import asyncio
import atexit
import weakref
import warnings
import threading
import time
from typing import Optional, AsyncGenerator, Dict, Any, List, Set, ClassVar
import json

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

class LocalLabClient:
    """Asynchronous Python client for the LocalLab API with automatic session management

    This client requires async/await syntax. For synchronous usage, use SyncLocalLabClient.

    Async usage:
    ```python
    client = LocalLabClient("http://localhost:8000")
    response = await client.generate("Hello, world!")
    await client.close()
    ```

    # Context manager usage has been removed to simplify the client implementation
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

    # Context manager methods have been removed to simplify the client implementation

    def __del__(self):
        """Attempt to close the session when the client is garbage collected"""
        if not self._closed and self._session is not None:
            # We can't await in __del__, so just issue a warning
            warnings.warn(
                "LocalLabClient was garbage collected with an open session. "
                "Please use 'await client.close()' to properly close the session."
            )

    async def connect(self):
        """Ensure the client has an active session with retry logic"""
        # Update activity timestamp
        self._update_activity()

        # Maximum number of connection attempts
        max_attempts = 3
        attempt = 0
        last_error = None

        while attempt < max_attempts:
            try:
                if self._session is None or self._session.closed:
                    self._session = aiohttp.ClientSession(timeout=self.timeout)
                    self._closed = False
                return
            except Exception as e:
                last_error = e
                attempt += 1
                if attempt < max_attempts:
                    # Wait before retrying (exponential backoff)
                    await asyncio.sleep(0.5 * (2 ** attempt))

        # If we've exhausted all attempts, raise the last error
        if last_error:
            raise Exception(f"Failed to create session after {max_attempts} attempts: {str(last_error)}")

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
        top_p: float = 0.9,
        timeout: float = 60.0  # Add timeout parameter with a default of 60 seconds
    ) -> str:
        """Generate text using the model with improved error handling"""
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
            return self.stream_generate(prompt, model_id, max_length, temperature, top_p, timeout)

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
                    raise Exception(f"Generation failed: {error_text}")

                try:
                    data = await response.json()
                    # Handle both response formats for backward compatibility
                    if "response" in data:
                        return data["response"]
                    elif "text" in data:
                        return data["text"]
                    else:
                        raise Exception(f"Unexpected response format: {data}")
                except Exception as e:
                    # Handle JSON parsing errors
                    raise Exception(f"Failed to parse response: {str(e)}")
        except asyncio.TimeoutError:
            raise Exception("Request timed out. The server took too long to respond.")
        except aiohttp.ClientError as e:
            raise Exception(f"Connection error: {str(e)}")
        except Exception as e:
            raise Exception(f"Generation failed: {str(e)}")

    async def stream_generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: float = 120.0,  # Increased timeout for low-resource CPUs
        retry_count: int = 2     # Add retry count for reliability
    ) -> AsyncGenerator[str, None]:
        """Stream text generation with token-level streaming and robust error handling"""
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

        # Track retries
        retries = 0
        last_error = None

        while retries <= retry_count:
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
                    # Buffer for accumulating partial responses if needed

                    try:
                        # Process the streaming response
                        async for line in response.content:
                            if line:
                                received_data = True
                                text = line.decode("utf-8").strip()

                                # Skip empty lines
                                if not text:
                                    continue

                                # Handle SSE format (data: prefix)
                                if text.startswith("data: "):
                                    text = text[6:]  # Remove "data: " prefix

                                # Check for end of stream marker
                                if text == "[DONE]":
                                    break

                                # Check for error messages
                                if text.startswith("\nError:") or text.startswith("Error:"):
                                    error_msg = text.replace("\nError: ", "").replace("Error: ", "")
                                    raise Exception(error_msg)

                                yield text

                        # If we didn't receive any data, the stream might have ended unexpectedly
                        if not received_data:
                            yield "\nError: Stream ended unexpectedly without returning any data"

                        # Successful completion, break the retry loop
                        break

                    except asyncio.TimeoutError:
                        # For timeout during streaming, we'll retry
                        last_error = "Stream timed out. The server took too long to respond."
                        retries += 1
                        if retries > retry_count:
                            yield f"\nError: {last_error}"
                        continue

                    except Exception as stream_error:
                        # For other streaming errors, yield the error and break
                        error_msg = str(stream_error)
                        if "timeout" in error_msg.lower():
                            last_error = "Stream timed out. The server took too long to respond."
                            retries += 1
                            if retries > retry_count:
                                yield f"\nError: {last_error}"
                            continue
                        else:
                            yield f"\nError: {error_msg}"
                            break

            except asyncio.TimeoutError:
                # For connection timeout, we'll retry
                last_error = "Connection timed out. The server took too long to respond."
                retries += 1
                if retries > retry_count:
                    yield f"\nError: {last_error}"
                continue

            except aiohttp.ClientError as e:
                # For connection errors, we'll retry
                last_error = f"Connection error: {str(e)}"
                retries += 1
                if retries > retry_count:
                    yield f"\nError: {last_error}"
                continue

            except Exception as e:
                # For other errors, yield the error and break
                yield f"\nError: {str(e)}"
                break

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model_id: Optional[str] = None,
        stream: bool = False,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: float = 60.0  # Add timeout parameter with a default of 60 seconds
    ) -> Dict[str, Any]:
        """Chat completion endpoint with improved error handling"""
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
            return self.stream_chat(messages, model_id, max_length, temperature, top_p, timeout)

        # Create a timeout for this specific request
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            await self.connect()
            async with self._session.post(
                f"{self.base_url}/chat",
                json=payload,
                timeout=request_timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Chat completion failed: {error_text}")

                try:
                    return await response.json()
                except Exception as e:
                    # Handle JSON parsing errors
                    raise Exception(f"Failed to parse response: {str(e)}")
        except asyncio.TimeoutError:
            raise Exception("Request timed out. The server took too long to respond.")
        except aiohttp.ClientError as e:
            raise Exception(f"Connection error: {str(e)}")
        except Exception as e:
            raise Exception(f"Chat completion failed: {str(e)}")

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model_id: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: float = 120.0,  # Increased timeout for low-resource CPUs
        retry_count: int = 2     # Add retry count for reliability
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion with robust error handling"""
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

        # Create a timeout for this specific request
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        # Track retries
        retries = 0
        last_error = None

        while retries <= retry_count:
            try:
                await self.connect()
                async with self._session.post(
                    f"{self.base_url}/chat",
                    json=payload,
                    timeout=request_timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Chat streaming failed: {error_text}")

                    # Track if we've seen any data to detect early disconnections
                    received_data = False

                    try:
                        # Process the streaming response
                        async for line in response.content:
                            if line:
                                received_data = True
                                text = line.decode("utf-8").strip()

                                # Skip empty lines
                                if not text:
                                    continue

                                try:
                                    data = json.loads(text)

                                    # Check for end of stream marker
                                    if data == "[DONE]":
                                        break

                                    yield data
                                except json.JSONDecodeError:
                                    # Handle non-JSON responses
                                    if text.startswith("\nError:") or text.startswith("Error:"):
                                        error_msg = text.replace("\nError: ", "").replace("Error: ", "")
                                        raise Exception(error_msg)
                                    continue

                        # If we didn't receive any data, the stream might have ended unexpectedly
                        if not received_data:
                            yield {"error": "Stream ended unexpectedly without returning any data"}

                        # Successful completion, break the retry loop
                        break

                    except asyncio.TimeoutError:
                        # For timeout during streaming, we'll retry
                        last_error = "Stream timed out. The server took too long to respond."
                        retries += 1
                        if retries > retry_count:
                            yield {"error": last_error}
                        continue

                    except Exception as stream_error:
                        # For other streaming errors, yield the error and break
                        error_msg = str(stream_error)
                        if "timeout" in error_msg.lower():
                            last_error = "Stream timed out. The server took too long to respond."
                            retries += 1
                            if retries > retry_count:
                                yield {"error": last_error}
                            continue
                        else:
                            yield {"error": error_msg}
                            break

            except asyncio.TimeoutError:
                # For connection timeout, we'll retry
                last_error = "Connection timed out. The server took too long to respond."
                retries += 1
                if retries > retry_count:
                    yield {"error": last_error}
                continue

            except aiohttp.ClientError as e:
                # For connection errors, we'll retry
                last_error = f"Connection error: {str(e)}"
                retries += 1
                if retries > retry_count:
                    yield {"error": last_error}
                continue

            except Exception as e:
                # For other errors, yield the error and break
                yield {"error": str(e)}
                break

    async def batch_generate(
        self,
        prompts: List[str],
        model_id: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: float = 120.0  # Add timeout parameter with a default of 120 seconds for batch operations
    ) -> Dict[str, List[str]]:
        """Generate text for multiple prompts in parallel with improved error handling"""
        # Update activity timestamp
        self._update_activity()

        payload = {
            "prompts": prompts,
            "model_id": model_id,
            "max_length": max_length,
            "temperature": temperature,
            "top_p": top_p
        }

        # Create a timeout for this specific request
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            await self.connect()
            async with self._session.post(
                f"{self.base_url}/generate/batch",
                json=payload,
                timeout=request_timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Batch generation failed: {error_text}")

                try:
                    return await response.json()
                except Exception as e:
                    # Handle JSON parsing errors
                    raise Exception(f"Failed to parse response: {str(e)}")
        except asyncio.TimeoutError:
            raise Exception("Request timed out. The server took too long to respond.")
        except aiohttp.ClientError as e:
            raise Exception(f"Connection error: {str(e)}")
        except Exception as e:
            raise Exception(f"Batch generation failed: {str(e)}")

    async def load_model(self, model_id: str, timeout: float = 60.0) -> bool:
        """Load a specific model with improved error handling"""
        # Update activity timestamp
        self._update_activity()

        # Create a timeout for this specific request
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            await self.connect()
            async with self._session.post(
                f"{self.base_url}/models/load",
                json={"model_id": model_id},
                timeout=request_timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Model loading failed: {error_text}")

                try:
                    data = await response.json()
                    return data["status"] == "success"
                except Exception as e:
                    # Handle JSON parsing errors
                    raise Exception(f"Failed to parse response: {str(e)}")
        except asyncio.TimeoutError:
            raise Exception("Request timed out. The server took too long to respond.")
        except aiohttp.ClientError as e:
            raise Exception(f"Connection error: {str(e)}")
        except Exception as e:
            raise Exception(f"Model loading failed: {str(e)}")

    async def get_current_model(self, timeout: float = 30.0) -> Dict[str, Any]:
        """Get information about the currently loaded model with improved error handling"""
        # Update activity timestamp
        self._update_activity()

        # Create a timeout for this specific request
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            await self.connect()
            async with self._session.get(
                f"{self.base_url}/models/current",
                timeout=request_timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to get current model: {error_text}")

                try:
                    return await response.json()
                except Exception as e:
                    # Handle JSON parsing errors
                    raise Exception(f"Failed to parse response: {str(e)}")
        except asyncio.TimeoutError:
            raise Exception("Request timed out. The server took too long to respond.")
        except aiohttp.ClientError as e:
            raise Exception(f"Connection error: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to get current model: {str(e)}")

    async def list_models(self, timeout: float = 30.0) -> Dict[str, Any]:
        """List all available models with improved error handling"""
        # Update activity timestamp
        self._update_activity()

        # Create a timeout for this specific request
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            await self.connect()
            async with self._session.get(
                f"{self.base_url}/models/available",
                timeout=request_timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to list models: {error_text}")

                try:
                    data = await response.json()
                    return data["models"]
                except Exception as e:
                    # Handle JSON parsing errors
                    raise Exception(f"Failed to parse response: {str(e)}")
        except asyncio.TimeoutError:
            raise Exception("Request timed out. The server took too long to respond.")
        except aiohttp.ClientError as e:
            raise Exception(f"Connection error: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to list models: {str(e)}")

    async def health_check(self, timeout: float = 10.0) -> bool:
        """Check if the server is healthy with a short timeout"""
        # Update activity timestamp
        self._update_activity()

        # Create a timeout for this specific request
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            await self.connect()
            async with self._session.get(
                f"{self.base_url}/health",
                timeout=request_timeout
            ) as response:
                return response.status == 200
        except (asyncio.TimeoutError, aiohttp.ClientError, Exception):
            # Any error means the server is not healthy
            return False

    async def get_system_info(self, timeout: float = 30.0) -> Dict[str, Any]:
        """Get detailed system information with improved error handling"""
        # Update activity timestamp
        self._update_activity()

        # Create a timeout for this specific request
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            await self.connect()
            async with self._session.get(
                f"{self.base_url}/system/info",
                timeout=request_timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to get system info: {error_text}")

                try:
                    return await response.json()
                except Exception as e:
                    # Handle JSON parsing errors
                    raise Exception(f"Failed to parse response: {str(e)}")
        except asyncio.TimeoutError:
            raise Exception("Request timed out. The server took too long to respond.")
        except aiohttp.ClientError as e:
            raise Exception(f"Connection error: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to get system info: {str(e)}")

    async def unload_model(self, timeout: float = 30.0) -> bool:
        """Unload the current model to free up resources with improved error handling"""
        # Update activity timestamp
        self._update_activity()

        # Create a timeout for this specific request
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            await self.connect()
            async with self._session.post(
                f"{self.base_url}/models/unload",
                timeout=request_timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to unload model: {error_text}")

                try:
                    data = await response.json()
                    return data["status"] == "Model unloaded successfully"
                except Exception as e:
                    # Handle JSON parsing errors
                    raise Exception(f"Failed to parse response: {str(e)}")
        except asyncio.TimeoutError:
            raise Exception("Request timed out. The server took too long to respond.")
        except aiohttp.ClientError as e:
            raise Exception(f"Connection error: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to unload model: {str(e)}")