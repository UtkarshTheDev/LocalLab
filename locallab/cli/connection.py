"""
Connection utilities for LocalLab CLI chat interface
"""

import asyncio
import httpx
import json
from typing import Optional, Dict, Any, Tuple, AsyncGenerator, List
from urllib.parse import urljoin
import time
from collections import deque

from ..logger import get_logger

logger = get_logger("locallab.cli.connection")


class ServerConnection:
    """Handles connection to LocalLab server"""
    
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
        self.server_info: Optional[Dict[str, Any]] = None
        self.model_info: Optional[Dict[str, Any]] = None

        # Connection monitoring attributes
        self.connection_quality = 100  # 0-100 score
        self.last_ping_time = 0
        self.ping_interval = 30  # seconds during idle
        self.is_streaming = False
        self.is_idle = True
        self.background_monitor_task: Optional[asyncio.Task] = None

        # Health tracking
        self.ping_history: deque = deque(maxlen=10)  # Last 10 ping results
        self.consecutive_failures = 0
        self.last_successful_ping = time.time()

        # Silent operation flags
        self.silent_mode = True  # No user-visible connection messages
        self.auto_recovery = True
        self._reconnecting = False
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
        
    async def connect(self) -> bool:
        """Establish connection to the server"""
        try:
            # Create client with extended timeout for generation
            timeout_config = httpx.Timeout(
                connect=10.0,  # Connection timeout
                read=300.0,    # Read timeout (5 minutes for generation)
                write=10.0,    # Write timeout
                pool=10.0      # Pool timeout
            )
            self.client = httpx.AsyncClient(timeout=timeout_config)

            # Test connection with health check
            health_ok = await self.health_check()
            if not health_ok:
                await self.disconnect()
                return False

            # Get server information
            await self.get_server_info()
            await self.get_model_info()

            # Start background monitoring
            await self.start_background_monitor()

            # Reset connection quality and tracking
            self.connection_quality = 100
            self.consecutive_failures = 0
            self.last_successful_ping = time.time()
            self._reconnecting = False

            if not self.silent_mode:
                logger.info(f"Successfully connected to LocalLab server at {self.base_url}")
            else:
                logger.debug(f"Successfully connected to LocalLab server at {self.base_url}")
            return True

        except Exception as e:
            if not self.silent_mode:
                logger.error(f"Failed to connect to server: {str(e)}")
            else:
                logger.debug(f"Failed to connect to server: {str(e)}")
            await self.disconnect()
            return False

    async def disconnect(self):
        """Close the connection"""
        # Stop background monitoring
        await self.stop_background_monitor()

        if self.client:
            await self.client.aclose()
            self.client = None
            if not self.silent_mode:
                logger.info("Disconnected from server")
            else:
                logger.debug("Disconnected from server")
            
    async def health_check(self) -> bool:
        """Check if the server is healthy with enhanced error handling"""
        try:
            if not self.client:
                logger.debug("Health check failed: No client connection")
                return False

            url = urljoin(self.base_url, '/health')
            response = await self.client.get(url)

            if response.status_code == 200:
                try:
                    data = response.json()
                    is_healthy = data.get('status') == 'healthy'
                    logger.debug(f"Health check successful: {is_healthy}")
                    return is_healthy
                except Exception:
                    # Fallback: if we can't parse JSON, assume healthy if 200 OK
                    logger.debug("Health check successful (fallback)")
                    return True
            else:
                logger.debug(f"Health check failed: HTTP {response.status_code}")
                return False

        except httpx.TimeoutException:
            logger.debug("Health check failed: Request timeout")
            return False
        except httpx.ConnectError:
            logger.debug("Health check failed: Connection error")
            return False
        except httpx.NetworkError as e:
            logger.debug(f"Health check failed: Network error - {str(e)}")
            return False
        except Exception as e:
            logger.debug(f"Health check failed: Unexpected error - {str(e)}")
            return False

    async def get_server_info(self) -> Optional[Dict[str, Any]]:
        """Get server information"""
        try:
            if not self.client:
                return None

            url = urljoin(self.base_url, '/system/info')
            response = await self.client.get(url)
            if response.status_code == 200:
                self.server_info = response.json()
                return self.server_info
            return None

        except Exception as e:
            logger.debug(f"Failed to get server info: {str(e)}")
            return None

    async def get_model_info(self) -> Optional[Dict[str, Any]]:
        """Get current model information"""
        try:
            if not self.client:
                return None

            url = urljoin(self.base_url, '/models/current')
            response = await self.client.get(url)
            if response.status_code == 200:
                self.model_info = response.json()
                return self.model_info
            elif response.status_code == 404:
                # No model loaded
                self.model_info = {"model_id": None, "status": "no_model_loaded"}
                return self.model_info
            return None

        except Exception as e:
            logger.debug(f"Failed to get model info: {str(e)}")
            return None

    # Background monitoring methods
    async def start_background_monitor(self):
        """Start continuous connection monitoring"""
        if self.background_monitor_task and not self.background_monitor_task.done():
            return  # Already running

        self.background_monitor_task = asyncio.create_task(
            self._background_monitor_loop()
        )
        logger.debug("Background connection monitor started")

    async def stop_background_monitor(self):
        """Stop background monitoring"""
        if self.background_monitor_task and not self.background_monitor_task.done():
            self.background_monitor_task.cancel()
            try:
                await self.background_monitor_task
            except asyncio.CancelledError:
                pass
            logger.debug("Background connection monitor stopped")

    async def _background_monitor_loop(self):
        """Continuous monitoring loop"""
        while self.client:
            try:
                # Only ping during idle periods
                if self.is_idle and not self.is_streaming:
                    await self._perform_health_ping()

                # Wait for next check interval
                await asyncio.sleep(self.ping_interval)

            except asyncio.CancelledError:
                logger.debug("Background monitor cancelled")
                break
            except Exception as e:
                logger.debug(f"Background monitor error: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def _perform_health_ping(self):
        """Perform health check and update connection quality"""
        start_time = time.time()

        try:
            if not self.client:
                return

            response = await self.client.get(
                f"{self.base_url}/health",
                timeout=5.0
            )

            if response.status_code == 200:
                # Successful ping
                ping_time = (time.time() - start_time) * 1000  # ms
                self._update_connection_quality(True, ping_time)
                self.consecutive_failures = 0
                self.last_successful_ping = time.time()
                logger.debug(f"Health ping successful: {ping_time:.1f}ms")
            else:
                self._update_connection_quality(False, None)
                logger.debug(f"Health ping failed: HTTP {response.status_code}")

        except Exception as e:
            self._update_connection_quality(False, None)
            logger.debug(f"Health ping failed: {e}")

    def _update_connection_quality(self, success: bool, ping_time: Optional[float]):
        """Update connection quality score based on ping results"""

        # Add to history (keep last 10 results)
        result = {
            'success': success,
            'ping_time': ping_time,
            'timestamp': time.time()
        }
        self.ping_history.append(result)

        if success:
            # Good ping - improve quality
            if ping_time and ping_time < 50:  # Excellent response
                self.connection_quality = min(100, self.connection_quality + 5)
            elif ping_time and ping_time < 100:  # Good response
                self.connection_quality = min(100, self.connection_quality + 2)
            elif ping_time and ping_time < 200:  # Fair response
                self.connection_quality = min(100, self.connection_quality + 1)
            # Slow response doesn't improve quality

        else:
            # Failed ping - degrade quality
            self.consecutive_failures += 1
            degradation = min(20, self.consecutive_failures * 5)
            self.connection_quality = max(0, self.connection_quality - degradation)

        logger.debug(f"Connection quality: {self.connection_quality}% (failures: {self.consecutive_failures})")

        # Trigger reconnection if quality is too low
        if self.connection_quality < 30 and self.auto_recovery and not self._reconnecting:
            logger.debug("Connection quality degraded, triggering silent reconnection")
            asyncio.create_task(self._silent_reconnect())

    def set_streaming_state(self, is_streaming: bool):
        """Update streaming state for monitoring"""
        self.is_streaming = is_streaming
        self.is_idle = not is_streaming

        if is_streaming:
            # Pause aggressive monitoring during streaming
            self.ping_interval = 60  # Check less frequently
            logger.debug("Streaming started - reduced monitoring frequency")
        else:
            # Resume normal monitoring
            self.ping_interval = 30
            logger.debug("Streaming ended - resumed normal monitoring")
            # Immediate health check after streaming
            if self.background_monitor_task and not self.background_monitor_task.done():
                asyncio.create_task(self._perform_health_ping())

    async def _silent_reconnect(self):
        """Perform silent reconnection without user notification"""
        if self._reconnecting:
            return  # Already reconnecting

        self._reconnecting = True
        logger.debug("Starting silent reconnection...")

        try:
            # Stop background monitoring during reconnection
            await self.stop_background_monitor()

            # Close current connection
            if self.client:
                await self.client.aclose()
                self.client = None

            # Attempt reconnection with exponential backoff
            for attempt in range(3):
                if attempt > 0:
                    await asyncio.sleep(2 ** attempt)  # 2s, 4s, 8s

                logger.debug(f"Silent reconnection attempt {attempt + 1}/3")

                if await self.connect():
                    logger.debug("Silent reconnection successful")
                    self.connection_quality = 70  # Reset to good quality
                    self.consecutive_failures = 0
                    return True
                else:
                    logger.debug(f"Silent reconnection attempt {attempt + 1} failed")

            logger.warning("Silent reconnection failed after 3 attempts")
            return False

        except Exception as e:
            logger.debug(f"Silent reconnection error: {e}")
            return False
        finally:
            self._reconnecting = False

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status and quality metrics"""
        return {
            'connected': self.client is not None,
            'quality': self.connection_quality,
            'consecutive_failures': self.consecutive_failures,
            'last_successful_ping': self.last_successful_ping,
            'is_streaming': self.is_streaming,
            'is_idle': self.is_idle,
            'ping_history_count': len(self.ping_history),
            'reconnecting': self._reconnecting
        }

    async def generate_text(self, prompt: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate text using the /generate endpoint"""
        try:
            if not self.client:
                return None

            url = urljoin(self.base_url, '/generate')
            payload = {
                "prompt": prompt,
                "stream": False,
                **kwargs
            }

            response = await self.client.post(url, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                error_text = response.text
                logger.error(f"Generation failed: {response.status_code} - {error_text}")
                return None

        except Exception as e:
            logger.error(f"Failed to generate text: {str(e)}")
            return None
            
    async def generate_stream(self, prompt: str, **kwargs):
        """Generate text with streaming using the /generate endpoint"""
        try:
            if not self.client:
                return

            # Set streaming state
            self.set_streaming_state(True)

            url = urljoin(self.base_url, '/generate')
            payload = {
                "prompt": prompt,
                "stream": True,
                **kwargs
            }

            async with self.client.stream('POST', url, json=payload) as response:
                if response.status_code == 200:
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            if data == '[DONE]':
                                break
                            yield data
                        elif line:  # Non-empty line that doesn't start with 'data: '
                            logger.debug(f"Unexpected line format: {line}")
                else:
                    error_text = await response.aread()
                    logger.error(f"Streaming generation failed: {response.status_code} - {error_text.decode()}")

        except Exception as e:
            logger.error(f"Failed to stream text: {str(e)}")
            import traceback
            logger.debug(f"Streaming error traceback: {traceback.format_exc()}")
        finally:
            # Reset streaming state
            self.set_streaming_state(False)

    async def chat_completion(self, messages: list, **kwargs) -> Optional[Dict[str, Any]]:
        """Chat completion using the /chat endpoint"""
        try:
            if not self.client:
                return None

            url = urljoin(self.base_url, '/chat')
            payload = {
                "messages": messages,
                "stream": False,
                **kwargs
            }

            response = await self.client.post(url, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                error_text = response.text
                logger.error(f"Chat completion failed: {response.status_code} - {error_text}")
                return None

        except Exception as e:
            logger.error(f"Failed to complete chat: {str(e)}")
            return None

    async def chat_completion_stream(self, messages: list, **kwargs):
        """Chat completion with streaming using the /chat endpoint"""
        try:
            if not self.client:
                return

            # Set streaming state
            self.set_streaming_state(True)

            url = urljoin(self.base_url, '/chat')
            payload = {
                "messages": messages,
                "stream": True,
                **kwargs
            }

            async with self.client.stream('POST', url, json=payload) as response:
                if response.status_code == 200:
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            if data == '[DONE]':
                                break
                            yield data
                else:
                    error_text = response.text
                    logger.error(f"Streaming chat completion failed: {response.status_code} - {error_text}")

        except Exception as e:
            logger.error(f"Failed to stream chat completion: {str(e)}")
        finally:
            # Reset streaming state
            self.set_streaming_state(False)

    async def batch_generate(self, prompts: list, **kwargs) -> Optional[dict]:
        """Generate text for multiple prompts using the /generate/batch endpoint"""
        try:
            if not self.client:
                return None

            url = urljoin(self.base_url, '/generate/batch')

            # Prepare the batch request payload
            payload = {
                "prompts": prompts,
                **kwargs  # Include max_tokens, temperature, top_p, etc.
            }

            response = await self.client.post(url, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                error_text = response.text
                logger.error(f"Batch generation failed: {response.status_code} - {error_text}")
                return None

        except Exception as e:
            logger.error(f"Failed to perform batch generation: {str(e)}")
            return None

    async def batch_generate(self, prompts: list, **kwargs) -> Optional[dict]:
        """Generate text for multiple prompts using the /generate/batch endpoint"""
        try:
            if not self.client:
                return None

            url = urljoin(self.base_url, '/generate/batch')

            # Prepare the batch request payload
            payload = {
                "prompts": prompts,
                **kwargs  # Include max_tokens, temperature, top_p, etc.
            }

            response = await self.client.post(url, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                error_text = response.text
                logger.error(f"Batch generation failed: {response.status_code} - {error_text}")
                return None

        except Exception as e:
            logger.error(f"Failed to perform batch generation: {str(e)}")
            return None


async def detect_local_server(ports: list = [8000, 8080, 3000]) -> Optional[str]:
    """Detect if a LocalLab server is running locally"""
    for port in ports:
        url = f"http://localhost:{port}"
        try:
            async with ServerConnection(url, timeout=3) as conn:
                if await conn.health_check():
                    logger.debug(f"Found LocalLab server at {url}")  # Changed to debug
                    return url
        except Exception:
            continue
    return None


async def test_connection(url: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Test connection to a server and return status and info"""
    try:
        async with ServerConnection(url, timeout=5) as conn:
            if await conn.health_check():
                server_info = await conn.get_server_info()
                model_info = await conn.get_model_info()
                return True, {
                    "server_info": server_info,
                    "model_info": model_info,
                    "url": url
                }
            return False, None
    except Exception as e:
        logger.debug(f"Connection test failed for {url}: {str(e)}")
        return False, None
