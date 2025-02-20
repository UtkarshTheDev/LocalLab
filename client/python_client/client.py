import requests
from typing import Optional, Generator, Dict, Any
import json

class LocalLabClient:
    """Python client for the LocalLab API"""
    
    def __init__(self, base_url: str):
        """Initialize the client with the server's base URL"""
        self.base_url = base_url.rstrip("/")
    
    def generate(
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
            return self._stream_generate(payload)
        
        response = requests.post(f"{self.base_url}/generate", json=payload)
        if response.status_code != 200:
            raise Exception(f"Generation failed: {response.text}")
        
        return response.json()["response"]
    
    def _stream_generate(self, payload: Dict[str, Any]) -> Generator[str, None, None]:
        """Stream text generation"""
        with requests.post(f"{self.base_url}/generate", json=payload, stream=True) as response:
            if response.status_code != 200:
                raise Exception(f"Streaming failed: {response.text}")
            
            for line in response.iter_lines():
                if line:
                    yield line.decode("utf-8")
    
    def load_model(self, model_id: str) -> bool:
        """Load a specific model"""
        response = requests.post(
            f"{self.base_url}/models/load",
            json={"model_id": model_id}
        )
        if response.status_code != 200:
            raise Exception(f"Model loading failed: {response.text}")
        
        return response.json()["status"] == "success"
    
    def get_current_model(self) -> Dict[str, Any]:
        """Get information about the currently loaded model"""
        response = requests.get(f"{self.base_url}/models/current")
        if response.status_code != 200:
            raise Exception(f"Failed to get current model: {response.text}")
        
        return response.json()
    
    def list_available_models(self) -> Dict[str, Any]:
        """List all available models"""
        response = requests.get(f"{self.base_url}/models/available")
        if response.status_code != 200:
            raise Exception(f"Failed to list models: {response.text}")
        
        return response.json()["models"]
    
    def health_check(self) -> bool:
        """Check if the server is healthy"""
        try:
            response = requests.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False
    
    def chat(
        self,
        messages: list[dict],
        model_id: Optional[str] = None,
        stream: bool = False,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> dict:
        """Chat completion endpoint similar to OpenAI's API"""
        payload = {
            "messages": messages,
            "model_id": model_id,
            "stream": stream,
            "max_length": max_length,
            "temperature": temperature,
            "top_p": top_p
        }
        
        if stream:
            return self._stream_chat(payload)
        
        response = requests.post(f"{self.base_url}/chat", json=payload)
        if response.status_code != 200:
            raise Exception(f"Chat completion failed: {response.text}")
        
        return response.json()
    
    def _stream_chat(self, payload: Dict[str, Any]) -> Generator[str, None, None]:
        """Stream chat completion"""
        with requests.post(f"{self.base_url}/chat", json=payload, stream=True) as response:
            if response.status_code != 200:
                raise Exception(f"Chat streaming failed: {response.text}")
            
            for line in response.iter_lines():
                if line:
                    yield line.decode("utf-8")
    
    def batch_generate(
        self,
        prompts: list[str],
        model_id: Optional[str] = None,
        max_length: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Dict[str, list]:
        """Generate text for multiple prompts in parallel"""
        payload = {
            "prompts": prompts,
            "model_id": model_id,
            "max_length": max_length,
            "temperature": temperature,
            "top_p": top_p
        }
        
        response = requests.post(f"{self.base_url}/generate/batch", json=payload)
        if response.status_code != 200:
            raise Exception(f"Batch generation failed: {response.text}")
        
        return response.json()
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get detailed system information"""
        response = requests.get(f"{self.base_url}/system/info")
        if response.status_code != 200:
            raise Exception(f"Failed to get system info: {response.text}")
        
        return response.json()
    
    def unload_model(self) -> bool:
        """Unload the current model to free up resources"""
        response = requests.post(f"{self.base_url}/models/unload")
        if response.status_code != 200:
            raise Exception(f"Failed to unload model: {response.text}")
        
        return response.json()["status"] == "Model unloaded successfully" 