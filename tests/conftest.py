import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
from locallab.main import app
from locallab.model_manager import ModelManager

@pytest.fixture
def test_client():
    """
    Fixture to create a TestClient for the FastAPI app.
    """
    return TestClient(app)

@pytest.fixture
def model_manager():
    """
    Fixture to create a new instance of the ModelManager.
    """
    return ModelManager()

@pytest.fixture
def mock_tokenizer():
    """
    Fixture for a mocked tokenizer.
    Returns a simple dictionary mimicking tokenizer output.
    """
    tokenizer = Mock()
    tokenizer.return_value = {"input_ids": [1, 2, 3], "attention_mask": [1, 1, 1]}
    return tokenizer

@pytest.fixture
def mock_model():
    """
    Fixture for a mocked model.
    Mocks the generate method.
    """
    model = Mock()
    model.generate.return_value = [[1, 2, 3, 4]]
    return model
