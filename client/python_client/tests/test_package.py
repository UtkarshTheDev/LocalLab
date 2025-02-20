"""Test package structure and imports."""

def test_package_imports():
    """Test that all package components can be imported."""
    from locallab import (
        LocalLabClient,
        LocalLabConfig,
        GenerateOptions,
        ChatMessage,
        GenerateResponse,
        ChatResponse,
        BatchResponse,
        ModelInfo,
        SystemInfo,
        LocalLabError,
        ValidationError,
        RateLimitError,
    )
    
    assert LocalLabClient is not None
    assert LocalLabConfig is not None
    assert GenerateOptions is not None
    assert ChatMessage is not None
    assert GenerateResponse is not None
    assert ChatResponse is not None
    assert BatchResponse is not None
    assert ModelInfo is not None
    assert SystemInfo is not None
    assert LocalLabError is not None
    assert ValidationError is not None
    assert RateLimitError is not None

def test_client_initialization():
    """Test that client can be initialized with config."""
    from locallab import LocalLabClient, LocalLabConfig
    
    config = LocalLabConfig(base_url="http://localhost:8000")
    client = LocalLabClient(config)
    
    assert client.config.base_url == "http://localhost:8000"
    assert client.config.timeout == 30.0
    assert client.config.retries == 3 