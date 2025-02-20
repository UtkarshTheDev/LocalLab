import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from server.locallab.main import app
from server.locallab.model_manager import ModelManager
from server.locallab.client import LocalLabClient

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def model_manager():
    return ModelManager()

@pytest.fixture
def mock_tokenizer():
    tokenizer = Mock()
    tokenizer.return_value = {"input_ids": [1, 2, 3], "attention_mask": [1, 1, 1]}
    return tokenizer

@pytest.fixture
def mock_model():
    model = Mock()
    model.generate.return_value = [[1, 2, 3, 4]]
    return model

@pytest.fixture
def locallab_client():
    with patch('locallab.client.requests') as mock_requests:
        client = LocalLabClient("http://localhost:8000")
        mock_requests.get.return_value.json.return_value = {"status": "ok"}
        mock_requests.post.return_value.json.return_value = {"response": "test response"}
        yield client 