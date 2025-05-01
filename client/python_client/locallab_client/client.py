"""
Asynchronous client for LocalLab API.
"""

import aiohttp
import asyncio
import atexit
import weakref
import warnings
import threading
import time
import logging
from typing import Optional, AsyncGenerator, Dict, Any, List, Set, ClassVar, Union
import json
import websockets
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Define response models
class GenerateOptions(BaseModel):
    """Options for text generation"""
    max_length: Optional[int] = None
    temperature: float = 0.7
    top_p: float = 0.9
    stream: bool = False

class ChatMessage(BaseModel):
    """Chat message format"""
    role: str
    content: str

class GenerateResponse(BaseModel):
    """Response from text generation"""
    text: str
    model: str

class ChatResponse(BaseModel):
    """Response from chat completion"""
    choices: List[Dict[str, Any]]

class BatchResponse(BaseModel):
    """Response from batch generation"""
    responses: List[str]

class ModelInfo(BaseModel):
    """Model information"""
    name: str
    type: str
    parameters: Optional[Dict[str, Any]] = None

class SystemInfo(BaseModel):
    """System information"""
    cpu_usage: float
    memory_usage: float
    gpu_info: Optional[Dict[str, Any]] = None
    active_model: Optional[str] = None
    uptime: float
    request_count: int

# Define custom exceptions
class LocalLabError(Exception):
    """Base exception for LocalLab errors"""
    pass

class ValidationError(LocalLabError):
    """Validation error"""
    pass

class RateLimitError(LocalLabError):
    """Rate limit error"""
    pass

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

class LocalLabConfig:
    def __init__(self, base_url: str, timeout: float = 30.0, headers: Dict[str, str] = {}, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = headers
        self.api_key = api_key

class LocalLabClient:
    """Asynchronous client for the LocalLab API with improved error handling."""

    # Class-level attribute for activity tracking
    _last_activity_times = {}

    def __init__(self, config: Union[str, LocalLabConfig, Dict[str, Any]]):
        if isinstance(config, str):
            config = LocalLabConfig(base_url=config)
        elif isinstance(config, dict):
            config = LocalLabConfig(**config)

        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._stream_context = []
        self._closed = False
        self._connection_lock = asyncio.Lock()
        self._last_activity = time.time()
        self._retry_count = 0
        self._max_retries = 3

    async def connect(self):
        """Initialize HTTP session with improved error handling."""
        if self._closed:
            raise RuntimeError("Client is closed")

        if not self._session:
            try:
                headers = {
                    "Content-Type": "application/json",
                    **self.config.headers,
                }
                if self.config.api_key:
                    headers["Authorization"] = f"Bearer {self.config.api_key}"

                self._session = aiohttp.ClientSession(
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                )
            except Exception as e:
                logger.error(f"Failed to create session: {str(e)}")
                raise ConnectionError(f"Failed to create session: {str(e)}")

    async def close(self):
        """Close all connections with proper cleanup."""
        if not self._closed:
            try:
                if self._session:
                    await self._session.close()
                    self._session = None
                if self.ws:
                    await self.ws.close()
                    self.ws = None
            except Exception as e:
                logger.error(f"Error during close: {str(e)}")
            finally:
                self._closed = True

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

    def __del__(self):
        """Attempt to close the session when the client is garbage collected"""
        if not self._closed and self._session is not None:
            # We can't await in __del__, so just issue a warning
            warnings.warn(
                "LocalLabClient was garbage collected with an open session. "
                "Please use 'await client.close()' to properly close the session."
            )

    async def generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        stream: bool = False,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: float = 180.0,  # Increased timeout for more complete responses (3 minutes)
        repetition_penalty: float = 1.15,  # Added repetition penalty for better quality
        top_k: int = 80  # Added top_k parameter for better quality
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
            "top_p": top_p,
            "repetition_penalty": repetition_penalty,
            "top_k": top_k
        }

        if stream:
            return self.stream_generate(
                prompt=prompt,
                model_id=model_id,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                timeout=timeout,
                repetition_penalty=repetition_penalty,
                top_k=top_k
            )

        # Create a timeout for this specific request
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            await self.connect()
            async with self._session.post(
                f"{self.config.base_url}/generate",
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
        timeout: float = 300.0,  # Increased timeout for more complete responses (5 minutes)
        retry_count: int = 3,    # Increased retry count for better reliability
        repetition_penalty: float = 1.15,  # Increased repetition penalty for better quality
        top_k: int = 80  # Added top_k parameter for better quality
    ) -> AsyncGenerator[str, None]:
        """
        Stream text generation with token-level streaming and robust error handling.

        Args:
            prompt: The prompt to generate text from
            model_id: Optional model ID to use
            max_length: Maximum length of the generated text (defaults to 8192 if None)
            temperature: Temperature for sampling
            top_p: Top-p for nucleus sampling
            timeout: Request timeout in seconds
            retry_count: Number of retries for network errors
            repetition_penalty: Penalty for repetition (higher values = less repetition)
            top_k: Top-k for sampling (higher values = more diverse vocabulary)

        Returns:
            A generator that yields chunks of text as they are generated.
        """
        # Update activity timestamp
        self._update_activity()

        # Use a higher max_length by default to ensure complete responses
        if max_length is None:
            max_length = 8192  # Default to 8192 tokens to match server's default

        payload = {
            "prompt": prompt,
            "model_id": model_id,
            "stream": True,
            "max_length": max_length,
            "temperature": temperature,
            "top_p": top_p,
            "repetition_penalty": repetition_penalty,
            "top_k": top_k
        }

        # Create a timeout for this specific request
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        # Track retries
        retries = 0
        last_error = None
        accumulated_text = ""  # Track accumulated text for error recovery

        while retries <= retry_count:
            try:
                await self.connect()
                async with self._session.post(
                    f"{self.config.base_url}/generate",
                    json=payload,
                    timeout=request_timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Streaming failed: {error_text}")

                    # Track if we've seen any data to detect early disconnections
                    received_data = False
                    # Buffer for accumulating partial responses if needed
                    token_buffer = ""
                    last_token_time = time.time()

                    try:
                        # Process the streaming response
                        async for line in response.content:
                            if line:
                                received_data = True
                                current_time = time.time()
                                text = line.decode("utf-8").strip()

                                # Skip empty lines
                                if not text:
                                    continue

                                # Handle SSE format (data: prefix)
                                if text.startswith("data: "):
                                    text = text[6:]  # Remove "data: " prefix

                                # Check for end of stream marker
                                if text == "[DONE]":
                                    # If we have any buffered text, yield it before ending
                                    if token_buffer:
                                        yield token_buffer
                                    break

                                # Check for error messages
                                if text.startswith("\nError:") or text.startswith("Error:"):
                                    error_msg = text.replace("\nError: ", "").replace("Error: ", "")
                                    raise Exception(error_msg)

                                # Add to accumulated text for error recovery
                                accumulated_text += text

                                # Reset the last token time
                                last_token_time = current_time

                                # Yield the token directly for immediate feedback
                                yield text

                        # If we didn't receive any data, the stream might have ended unexpectedly
                        if not received_data:
                            # If we have accumulated text from previous attempts, don't report an error
                            if not accumulated_text:
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
        timeout: float = 180.0,  # Increased timeout for more complete responses (3 minutes)
        repetition_penalty: float = 1.15,  # Added repetition penalty for better quality
        top_k: int = 80  # Added top_k parameter for better quality
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
            "top_p": top_p,
            "repetition_penalty": repetition_penalty,
            "top_k": top_k
        }

        if stream:
            return self.stream_chat(
                messages=messages,
                model_id=model_id,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p,
                timeout=timeout,
                repetition_penalty=repetition_penalty,
                top_k=top_k
            )

        # Create a timeout for this specific request
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            await self.connect()
            async with self._session.post(
                f"{self.config.base_url}/chat",
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
        timeout: float = 300.0,  # Increased timeout for more complete responses (5 minutes)
        retry_count: int = 3,    # Increased retry count for better reliability
        repetition_penalty: float = 1.15,  # Added repetition penalty for better quality
        top_k: int = 80  # Added top_k parameter for better quality
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
            "top_p": top_p,
            "repetition_penalty": repetition_penalty,
            "top_k": top_k
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
                    f"{self.config.base_url}/chat",
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
        timeout: float = 300.0,  # Increased timeout for more complete responses (5 minutes)
        repetition_penalty: float = 1.15,  # Added repetition penalty for better quality
        top_k: int = 80  # Added top_k parameter for better quality
    ) -> Dict[str, List[str]]:
        """Generate text for multiple prompts in parallel with improved error handling"""
        # Update activity timestamp
        self._update_activity()

        payload = {
            "prompts": prompts,
            "model_id": model_id,
            "max_length": max_length,
            "temperature": temperature,
            "top_p": top_p,
            "repetition_penalty": repetition_penalty,
            "top_k": top_k
        }

        # Create a timeout for this specific request
        request_timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            await self.connect()
            async with self._session.post(
                f"{self.config.base_url}/generate/batch",
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
                f"{self.config.base_url}/models/load",
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
                f"{self.config.base_url}/models/current",
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
                f"{self.config.base_url}/models/available",
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
                f"{self.config.base_url}/health",
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
                f"{self.config.base_url}/system/info",
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
                f"{self.config.base_url}/models/unload",
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