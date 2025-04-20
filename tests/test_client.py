import pytest
from unittest.mock import patch, Mock
import requests

def test_generate(locallab_client):
    """Test text generation"""
    response = locallab_client.generate("Test prompt")
    assert isinstance(response, str)
    
    # Test with parameters
    response = locallab_client.generate(
        "Test prompt",
        model_id="qwen-0.5b",
        temperature=0.8,
        max_length=100
    )
    assert isinstance(response, str)

def test_chat(locallab_client):
    """Test chat completion"""
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello!"}
    ]
    response = locallab_client.chat(messages)
    assert isinstance(response, dict)
    assert "choices" in response

def test_batch_generate(locallab_client):
    """Test batch generation"""
    prompts = ["Test 1", "Test 2", "Test 3"]
    response = locallab_client.batch_generate(prompts)
    assert isinstance(response, dict)
    assert "responses" in response
    assert len(response["responses"]) == len(prompts)

def test_model_management(locallab_client):
    """Test model management methods"""
    # Test loading model
    assert locallab_client.load_model("qwen-0.5b")
    
    # Test getting current model
    model_info = locallab_client.get_current_model()
    assert isinstance(model_info, dict)
    assert "model_id" in model_info
    
    # Test listing models
    models = locallab_client.list_available_models()
    assert isinstance(models, dict)
    assert "models" in models
    
    # Test unloading model
    assert locallab_client.unload_model()

def test_system_info(locallab_client):
    """Test system information methods"""
    info = locallab_client.get_system_info()
    assert isinstance(info, dict)
    assert all(key in info for key in [
        "cpu_usage", "memory_usage", "gpu_info",
        "active_model", "uptime", "request_count"
    ])

def test_error_handling(locallab_client):
    """Test client error handling"""
    with patch('locallab_client.requests') as mock_requests:
        # Test connection error
        mock_requests.post.side_effect = requests.ConnectionError
        with pytest.raises(ConnectionError):
            locallab_client.generate("Test")
        
        # Test timeout error
        mock_requests.post.side_effect = requests.Timeout
        with pytest.raises(TimeoutError):
            locallab_client.generate("Test")
        
        # Test API error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Invalid parameters"}
        mock_requests.post.side_effect = None
        mock_requests.post.return_value = mock_response
        with pytest.raises(ValueError):
            locallab_client.generate("Test")

def test_streaming(locallab_client):
    """Test streaming functionality"""
    with patch('locallab_client.requests') as mock_requests:
        mock_response = Mock()
        mock_response.iter_lines.return_value = [b'data: token1', b'data: token2']
        mock_requests.post.return_value = mock_response
        
        tokens = list(locallab_client.generate("Test", stream=True))
        assert len(tokens) > 0
        assert all(isinstance(token, str) for token in tokens)

def test_custom_model_loading(locallab_client):
    """Test loading custom models"""
    assert locallab_client.load_custom_model(
        "facebook/opt-350m",
        fallback_model="qwen-0.5b"
    )
    
    # Test with invalid model
    with pytest.raises(ValueError):
        locallab_client.load_custom_model("invalid/model") 