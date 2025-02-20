import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from server.locallab.model_manager import ModelManager
from server.locallab.config import MODEL_REGISTRY

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

def test_init(model_manager):
    """Test ModelManager initialization"""
    assert model_manager.current_model is None
    assert model_manager.model is None
    assert model_manager.tokenizer is None

@patch("server.locallab.model_manager.check_resource_availability")
@patch("server.locallab.model_manager.AutoTokenizer")
@patch("server.locallab.model_manager.AutoModelForCausalLM")
async def test_load_model(mock_auto_model, mock_auto_tokenizer, mock_check_resources, model_manager):
    """Test model loading"""
    # Mock resource check
    mock_check_resources.return_value = True
    
    # Mock tokenizer and model
    mock_auto_tokenizer.from_pretrained.return_value = Mock()
    mock_auto_model.from_pretrained.return_value = Mock()
    
    # Test loading a valid model
    success = await model_manager.load_model("qwen-0.5b")
    assert success
    assert model_manager.current_model == "qwen-0.5b"
    
    # Test loading invalid model
    with pytest.raises(HTTPException):
        await model_manager.load_model("invalid-model")

@patch("server.locallab.model_manager.check_resource_availability")
async def test_model_fallback(mock_check_resources, model_manager):
    """Test model fallback when resources are insufficient"""
    # Mock resource check to fail for larger model
    mock_check_resources.side_effect = lambda x: x < 5000
    
    # Load model with fallback
    success = await model_manager.load_model("llama2-7b")
    assert success
    assert model_manager.current_model == "qwen-0.5b"  # Fallback model

@pytest.mark.asyncio
async def test_generate(model_manager, mock_tokenizer, mock_model):
    """Test text generation"""
    model_manager.tokenizer = mock_tokenizer
    model_manager.model = mock_model
    model_manager.model_config = MODEL_REGISTRY["qwen-0.5b"]
    
    # Test basic generation
    response = await model_manager.generate("Test prompt")
    assert isinstance(response, str)
    
    # Test streaming generation
    stream = model_manager.generate("Test prompt", stream=True)
    assert hasattr(stream, "__iter__") 