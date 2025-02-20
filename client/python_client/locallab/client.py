from typing import Any, AsyncGenerator, Dict, List, Optional, Union
import json
import asyncio
import aiohttp
import websockets
from pydantic import BaseModel, Field

class LocalLabConfig(BaseModel):
    base_url: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    retries: int = 3
    headers: Dict[str, str] = Field(default_factory=dict)

class GenerateOptions(BaseModel):
    model_id: Optional[str] = None
    max_length: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stream: bool = False

class ChatMessage(BaseModel):
    role: str
    content: str

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class GenerateResponse(BaseModel):
    response: str
    model_id: str
    usage: Usage

class ChatChoice(BaseModel):
    message: ChatMessage
    finish_reason: str

class ChatResponse(BaseModel):
    choices: List[ChatChoice]
    usage: Usage

class BatchResponse(BaseModel):
    responses: List[str]
    model_id: str
    usage: Usage

class ModelInfo(BaseModel):
    name: str
    vram: int
    ram: int
    max_length: int
    fallback: Optional[str]
    description: str
    quantization: Optional[str]
    tags: List[str]

class GpuInfo(BaseModel):
    device: str
    total_memory: int
    used_memory: int
    free_memory: int
    utilization: float

class SystemInfo(BaseModel):
    cpu_usage: float
    memory_usage: float
    gpu_info: Optional[GpuInfo]
    active_model: Optional[str]
    uptime: float
    request_count: int

class LocalLabError(Exception):
    def __init__(self, message: str, code: str, status: Optional[int] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.details = details or {}

class ValidationError(LocalLabError):
    def __init__(self, message: str, field_errors: Dict[str, List[str]]):
        super().__init__(message, "VALIDATION_ERROR", 400)
        self.field_errors = field_errors

class RateLimitError(LocalLabError):
    def __init__(self, message: str, retry_after: int):
        super().__init__(message, "RATE_LIMIT_ERROR", 429)
        self.retry_after = retry_after

class LocalLabClient:
    def __init__(self, config: Union[LocalLabConfig, Dict[str, Any]]):
        if isinstance(config, dict):
            config = LocalLabConfig(**config)
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Initialize HTTP session"""
        if not self.session:
            headers = {
                "Content-Type": "application/json",
                **self.config.headers,
            }
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            self.session = aiohttp.ClientSession(
                base_url=self.config.base_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            )

    async def close(self):
        """Close all connections"""
        if self.session:
            await self.session.close()
            self.session = None
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        """Make HTTP request with retries"""
        if not self.session:
            await self.connect()

        for attempt in range(self.config.retries):
            try:
                async with self.session.request(method, path, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 400:
                        data = await response.json()
                        raise ValidationError(data["message"], data["field_errors"])
                    elif response.status == 429:
                        data = await response.json()
                        raise RateLimitError(data["message"], data["retry_after"])
                    else:
                        data = await response.json()
                        raise LocalLabError(
                            data.get("message", "Unknown error"),
                            data.get("code", "UNKNOWN_ERROR"),
                            response.status,
                            data.get("details"),
                        )
            except aiohttp.ClientError as e:
                if attempt == self.config.retries - 1:
                    raise LocalLabError(str(e), "CONNECTION_ERROR")
                await asyncio.sleep(2 ** attempt)

    async def generate(self, prompt: str, options: Optional[Union[GenerateOptions, Dict]] = None) -> GenerateResponse:
        """Generate text from prompt"""
        if isinstance(options, dict):
            options = GenerateOptions(**options)
        data = {"prompt": prompt, **(options.model_dump() if options else {})}
        response = await self._request("POST", "/generate", json=data)
        return GenerateResponse(**response)

    async def stream_generate(self, prompt: str, options: Optional[Union[GenerateOptions, Dict]] = None) -> AsyncGenerator[str, None]:
        """Stream generated text"""
        if isinstance(options, dict):
            options = GenerateOptions(**options)
        if options:
            options.stream = True
        else:
            options = GenerateOptions(stream=True)
        
        data = {"prompt": prompt, **options.model_dump()}
        async with self.session.post("/generate/stream", json=data) as response:
            async for line in response.content:
                if line:
                    try:
                        data = json.loads(line)
                        yield data["response"]
                    except json.JSONDecodeError:
                        yield line.decode().strip()

    async def chat(self, messages: List[Union[ChatMessage, Dict]], options: Optional[Union[GenerateOptions, Dict]] = None) -> ChatResponse:
        """Chat completion"""
        messages = [m if isinstance(m, ChatMessage) else ChatMessage(**m) for m in messages]
        if isinstance(options, dict):
            options = GenerateOptions(**options)
        data = {
            "messages": [m.model_dump() for m in messages],
            **(options.model_dump() if options else {})
        }
        response = await self._request("POST", "/chat", json=data)
        return ChatResponse(**response)

    async def stream_chat(self, messages: List[Union[ChatMessage, Dict]], options: Optional[Union[GenerateOptions, Dict]] = None) -> AsyncGenerator[ChatMessage, None]:
        """Stream chat completion"""
        messages = [m if isinstance(m, ChatMessage) else ChatMessage(**m) for m in messages]
        if isinstance(options, dict):
            options = GenerateOptions(**options)
        if options:
            options.stream = True
        else:
            options = GenerateOptions(stream=True)
        
        data = {
            "messages": [m.model_dump() for m in messages],
            **options.model_dump()
        }
        async with self.session.post("/chat/stream", json=data) as response:
            async for line in response.content:
                if line:
                    try:
                        data = json.loads(line)
                        yield ChatMessage(**data)
                    except json.JSONDecodeError:
                        continue

    async def batch_generate(self, prompts: List[str], options: Optional[Union[GenerateOptions, Dict]] = None) -> BatchResponse:
        """Batch generate text"""
        if isinstance(options, dict):
            options = GenerateOptions(**options)
        data = {
            "prompts": prompts,
            **(options.model_dump() if options else {})
        }
        response = await self._request("POST", "/generate/batch", json=data)
        return BatchResponse(**response)

    async def load_model(self, model_id: str, options: Optional[Dict] = None) -> bool:
        """Load a specific model"""
        data = {"model_id": model_id, **(options or {})}
        response = await self._request("POST", "/models/load", json=data)
        return response.get("status") == "success"

    async def get_current_model(self) -> ModelInfo:
        """Get current model information"""
        response = await self._request("GET", "/models/current")
        return ModelInfo(**response)

    async def list_models(self) -> Dict[str, ModelInfo]:
        """List all available models"""
        response = await self._request("GET", "/models")
        return {k: ModelInfo(**v) for k, v in response.items()}

    async def get_system_info(self) -> SystemInfo:
        """Get system information"""
        response = await self._request("GET", "/system/info")
        return SystemInfo(**response)

    async def health_check(self) -> bool:
        """Check system health"""
        try:
            await self._request("GET", "/health")
            return True
        except Exception:
            return False

    async def connect_ws(self) -> None:
        """Connect to WebSocket for real-time updates"""
        if not self.ws:
            url = f"ws://{self.config.base_url.replace('http://', '')}/ws"
            self.ws = await websockets.connect(url)

    async def disconnect_ws(self) -> None:
        """Disconnect WebSocket"""
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def on_message(self, callback: callable) -> None:
        """Subscribe to WebSocket messages"""
        if not self.ws:
            await self.connect_ws()
        
        async for message in self.ws:
            try:
                data = json.loads(message)
                await callback(data)
            except json.JSONDecodeError:
                await callback(message) 