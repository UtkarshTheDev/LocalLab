import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientSession, ClientResponse, WSMessage
from locallab.client import (
    LocalLabClient,
    LocalLabConfig,
    GenerateOptions,
    ChatMessage,
    GenerateResponse,
    ChatResponse,
    BatchResponse,
    ModelInfo,
    SystemInfo,
    ValidationError,
    RateLimitError,
)

@pytest.fixture
def client():
    return LocalLabClient({
        "base_url": "http://localhost:8000",
        "api_key": "test-key",
    })

@pytest.fixture
def mock_response():
    response = AsyncMock(spec=ClientResponse)
    response.status = 200
    return response

@pytest.mark.asyncio
async def test_generate(client, mock_response):
    mock_data = {
        "response": "Generated text",
        "model_id": "test-model",
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }
    mock_response.json.return_value = mock_data

    with patch.object(ClientSession, "request", return_value=mock_response):
        response = await client.generate("Hello")
        assert isinstance(response, GenerateResponse)
        assert response.response == "Generated text"
        assert response.model_id == "test-model"
        assert response.usage.total_tokens == 30

@pytest.mark.asyncio
async def test_generate_with_options(client, mock_response):
    mock_data = {
        "response": "Generated text",
        "model_id": "test-model",
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }
    mock_response.json.return_value = mock_data

    options = GenerateOptions(temperature=0.7, max_length=100)
    with patch.object(ClientSession, "request", return_value=mock_response):
        response = await client.generate("Hello", options)
        assert isinstance(response, GenerateResponse)
        assert response.response == "Generated text"

@pytest.mark.asyncio
async def test_stream_generate(client):
    mock_response = AsyncMock()
    mock_response.content.__aiter__.return_value = [
        b'{"response": "Hello"}',
        b'{"response": " World"}',
    ]

    with patch.object(ClientSession, "post", return_value=mock_response):
        responses = []
        async for token in client.stream_generate("Hello"):
            responses.append(token)
        
        assert responses == ["Hello", " World"]

@pytest.mark.asyncio
async def test_chat(client, mock_response):
    mock_data = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "Hello! How can I help you?",
            },
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }
    mock_response.json.return_value = mock_data

    messages = [{"role": "user", "content": "Hello"}]
    with patch.object(ClientSession, "request", return_value=mock_response):
        response = await client.chat(messages)
        assert isinstance(response, ChatResponse)
        assert response.choices[0].message.content == "Hello! How can I help you?"

@pytest.mark.asyncio
async def test_batch_generate(client, mock_response):
    mock_data = {
        "responses": ["Answer 1", "Answer 2", "Answer 3"],
        "model_id": "test-model",
        "usage": {
            "prompt_tokens": 30,
            "completion_tokens": 60,
            "total_tokens": 90,
        },
    }
    mock_response.json.return_value = mock_data

    prompts = ["Q1", "Q2", "Q3"]
    with patch.object(ClientSession, "request", return_value=mock_response):
        response = await client.batch_generate(prompts)
        assert isinstance(response, BatchResponse)
        assert len(response.responses) == 3
        assert response.responses[0] == "Answer 1"

@pytest.mark.asyncio
async def test_load_model(client, mock_response):
    mock_response.json.return_value = {"status": "success"}

    with patch.object(ClientSession, "request", return_value=mock_response):
        success = await client.load_model("test-model")
        assert success is True

@pytest.mark.asyncio
async def test_list_models(client, mock_response):
    mock_data = {
        "model-1": {
            "name": "Model 1",
            "vram": 4000,
            "ram": 8000,
            "max_length": 2048,
            "fallback": None,
            "description": "Test model",
            "quantization": "fp16",
            "tags": ["test"],
        },
    }
    mock_response.json.return_value = mock_data

    with patch.object(ClientSession, "request", return_value=mock_response):
        models = await client.list_models()
        assert isinstance(models, dict)
        assert "model-1" in models
        assert isinstance(models["model-1"], ModelInfo)

@pytest.mark.asyncio
async def test_get_system_info(client, mock_response):
    mock_data = {
        "cpu_usage": 50.0,
        "memory_usage": 60.0,
        "gpu_info": {
            "device": "nvidia",
            "total_memory": 8000,
            "used_memory": 4000,
            "free_memory": 4000,
            "utilization": 50.0,
        },
        "active_model": "test-model",
        "uptime": 3600.0,
        "request_count": 100,
    }
    mock_response.json.return_value = mock_data

    with patch.object(ClientSession, "request", return_value=mock_response):
        info = await client.get_system_info()
        assert isinstance(info, SystemInfo)
        assert info.cpu_usage == 50.0
        assert info.gpu_info.device == "nvidia"

@pytest.mark.asyncio
async def test_validation_error(client):
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.status = 400
    mock_response.json.return_value = {
        "message": "Validation failed",
        "field_errors": {"prompt": ["Required field"]},
    }

    with patch.object(ClientSession, "request", return_value=mock_response):
        with pytest.raises(ValidationError) as exc_info:
            await client.generate("")
        assert exc_info.value.field_errors["prompt"] == ["Required field"]

@pytest.mark.asyncio
async def test_rate_limit_error(client):
    mock_response = AsyncMock(spec=ClientResponse)
    mock_response.status = 429
    mock_response.json.return_value = {
        "message": "Rate limit exceeded",
        "retry_after": 60,
    }

    with patch.object(ClientSession, "request", return_value=mock_response):
        with pytest.raises(RateLimitError) as exc_info:
            await client.generate("Hello")
        assert exc_info.value.retry_after == 60

@pytest.mark.asyncio
async def test_websocket(client):
    mock_ws = AsyncMock()
    mock_ws.__aiter__.return_value = [
        WSMessage(type=1, data='{"event": "update"}', extra=None),
    ]

    with patch("websockets.connect", return_value=mock_ws):
        callback = AsyncMock()
        await client.connect_ws()
        await client.on_message(callback)
        callback.assert_called_once_with({"event": "update"}) 