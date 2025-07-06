"""
Connection utilities for LocalLab CLI chat interface
"""

import asyncio
import httpx
import json
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urljoin
import time

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
            # Create client with timeout
            self.client = httpx.AsyncClient(timeout=self.timeout)

            # Test connection with health check
            health_ok = await self.health_check()
            if not health_ok:
                await self.disconnect()
                return False

            # Get server information
            await self.get_server_info()
            await self.get_model_info()

            logger.info(f"Successfully connected to LocalLab server at {self.base_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to server: {str(e)}")
            await self.disconnect()
            return False

    async def disconnect(self):
        """Close the connection"""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("Disconnected from server")
            
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
                else:
                    error_text = response.text
                    logger.error(f"Streaming generation failed: {response.status_code} - {error_text}")

        except Exception as e:
            logger.error(f"Failed to stream text: {str(e)}")

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
                    logger.info(f"Found LocalLab server at {url}")
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
