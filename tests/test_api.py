import pytest
from fastapi import HTTPException
from unittest.mock import patch

def test_generate_endpoint(test_client, mock_model, mock_tokenizer):
    """Test the text generation endpoint"""
    response = test_client.post("/generate", json={
        "prompt": "Test prompt",
        "temperature": 0.7,
        "max_length": 100
    })
    assert response.status_code == 200
    assert "response" in response.json()

def test_chat_endpoint(test_client):
    """Test the chat completion endpoint"""
    response = test_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": "Hello!"}
        ],
        "temperature": 0.7
    })
    assert response.status_code == 200
    assert "choices" in response.json()

def test_batch_generate_endpoint(test_client):
    """Test batch generation endpoint"""
    response = test_client.post("/generate/batch", json={
        "prompts": ["Test 1", "Test 2"],
        "temperature": 0.7
    })
    assert response.status_code == 200
    assert "responses" in response.json()
    assert len(response.json()["responses"]) == 2

def test_models_endpoints(test_client):
    """Test model management endpoints"""
    # Test loading model
    response = test_client.post("/models/load", json={
        "model_id": "qwen-0.5b"
    })
    assert response.status_code == 200
    
    # Test getting current model
    response = test_client.get("/models/current")
    assert response.status_code == 200
    assert "model_id" in response.json()
    
    # Test listing available models
    response = test_client.get("/models/available")
    assert response.status_code == 200
    assert "models" in response.json()
    
    # Test unloading model
    response = test_client.post("/models/unload")
    assert response.status_code == 200

def test_system_endpoints(test_client):
    """Test system information endpoints"""
    # Test system info
    response = test_client.get("/system/info")
    assert response.status_code == 200
    assert all(key in response.json() for key in [
        "cpu_usage", "memory_usage", "gpu_info", 
        "active_model", "uptime", "request_count"
    ])
    
    # Test health check
    response = test_client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()

def test_error_handling(test_client):
    """Test API error handling"""
    # Test invalid model
    response = test_client.post("/models/load", json={
        "model_id": "invalid-model"
    })
    assert response.status_code == 404
    
    # Test invalid parameters
    response = test_client.post("/generate", json={
        "prompt": "Test",
        "temperature": 2.0  # Invalid temperature
    })
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_streaming_response(test_client):
    """Test streaming response"""
    with test_client.stream("POST", "/generate", json={
        "prompt": "Test",
        "stream": True
    }) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            assert line  # Check that we're getting data 