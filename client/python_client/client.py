import aiohttp
import asyncio
from typing import Optional, AsyncGenerator, Dict, Any, List
import json

class LocalLabClient:
    """Python client for the LocalLab API"""
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        """Initialize the client with the server's base URL"""
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def connect(self):
        """Create aiohttp session"""
        if not self._session:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
    
    async def close(self):
        """Close aiohttp session"""
        if self._session:
            await self._session.close()
            self._session = None
    
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
        top_p: float = 0.9
    ) -> AsyncGenerator[str, None]:
        """Stream text generation"""
        payload = {
            "prompt": prompt,
            "model_id": model_id,
            "stream": True,
            "max_length": max_length,
            "temperature": temperature,
            "top_p": top_p
        }
        
        await self.connect()
        async with self._session.post(f"{self.base_url}/generate", json=payload) as response:
            if response.status != 200:
                raise Exception(f"Streaming failed: {await response.text()}")
            
            async for line in response.content:
                if line:
                    yield line.decode("utf-8").strip()
    
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
        await self.connect()
        async with self._session.get(f"{self.base_url}/models/current") as response:
            if response.status != 200:
                raise Exception(f"Failed to get current model: {await response.text()}")
            
            return await response.json()
    
    async def list_models(self) -> Dict[str, Any]:
        """List all available models"""
        await self.connect()
        async with self._session.get(f"{self.base_url}/models/available") as response:
            if response.status != 200:
                raise Exception(f"Failed to list models: {await response.text()}")
            
            data = await response.json()
            return data["models"]
    
    async def health_check(self) -> bool:
        """Check if the server is healthy"""
        try:
            await self.connect()
            async with self._session.get(f"{self.base_url}/health") as response:
                return response.status == 200
        except Exception:
            return False
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get detailed system information"""
        await self.connect()
        async with self._session.get(f"{self.base_url}/system/info") as response:
            if response.status != 200:
                raise Exception(f"Failed to get system info: {await response.text()}")
            
            return await response.json()
    
    async def unload_model(self) -> bool:
        """Unload the current model to free up resources"""
        await self.connect()
        async with self._session.post(f"{self.base_url}/models/unload") as response:
            if response.status != 200:
                raise Exception(f"Failed to unload model: {await response.text()}")
            
            data = await response.json()
            return data["status"] == "Model unloaded successfully"