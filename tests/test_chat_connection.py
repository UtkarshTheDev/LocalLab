"""
Tests for the LocalLab CLI chat connection module
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from locallab.cli.connection import ServerConnection, detect_local_server, test_connection


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for testing"""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def server_connection():
    """Create ServerConnection instance for testing"""
    return ServerConnection("http://localhost:8000", timeout=5.0)


class TestServerConnection:
    """Test cases for ServerConnection class"""

    def test_initialization(self):
        """Test ServerConnection initialization"""
        connection = ServerConnection("http://test.com", timeout=10.0)
        
        assert connection.base_url == "http://test.com"
        assert connection.timeout == 10.0
        assert connection.client is None

    @pytest.mark.asyncio
    async def test_connect_success(self, server_connection, mock_httpx_client):
        """Test successful connection"""
        with patch('httpx.AsyncClient', return_value=mock_httpx_client):
            result = await server_connection.connect()
            
            assert result is True
            assert server_connection.client is not None

    @pytest.mark.asyncio
    async def test_connect_failure(self, server_connection):
        """Test connection failure"""
        with patch('httpx.AsyncClient', side_effect=Exception("Connection failed")):
            result = await server_connection.connect()
            
            assert result is False
            assert server_connection.client is None

    @pytest.mark.asyncio
    async def test_disconnect(self, server_connection, mock_httpx_client):
        """Test disconnection"""
        server_connection.client = mock_httpx_client
        
        await server_connection.disconnect()
        
        mock_httpx_client.aclose.assert_called_once()
        assert server_connection.client is None

    @pytest.mark.asyncio
    async def test_health_check_success(self, server_connection, mock_httpx_client):
        """Test successful health check"""
        server_connection.client = mock_httpx_client
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_httpx_client.get.return_value = mock_response
        
        result = await server_connection.health_check()
        
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure_no_client(self, server_connection):
        """Test health check failure when no client"""
        result = await server_connection.health_check()
        
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_failure_bad_status(self, server_connection, mock_httpx_client):
        """Test health check failure with bad status code"""
        server_connection.client = mock_httpx_client
        
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_httpx_client.get.return_value = mock_response
        
        result = await server_connection.health_check()
        
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, server_connection, mock_httpx_client):
        """Test health check timeout"""
        server_connection.client = mock_httpx_client
        mock_httpx_client.get.side_effect = httpx.TimeoutException("Timeout")
        
        result = await server_connection.health_check()
        
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, server_connection, mock_httpx_client):
        """Test health check connection error"""
        server_connection.client = mock_httpx_client
        mock_httpx_client.get.side_effect = httpx.ConnectError("Connection failed")
        
        result = await server_connection.health_check()
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_server_info_success(self, server_connection, mock_httpx_client):
        """Test successful server info retrieval"""
        server_connection.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "0.9.0", "status": "running"}
        mock_httpx_client.get.return_value = mock_response
        
        result = await server_connection.get_server_info()
        
        assert result == {"version": "0.9.0", "status": "running"}

    @pytest.mark.asyncio
    async def test_get_server_info_failure(self, server_connection, mock_httpx_client):
        """Test server info retrieval failure"""
        server_connection.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_httpx_client.get.return_value = mock_response
        
        result = await server_connection.get_server_info()
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_model_info_success(self, server_connection, mock_httpx_client):
        """Test successful model info retrieval"""
        server_connection.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"model_id": "test-model", "loaded": True}
        mock_httpx_client.get.return_value = mock_response
        
        result = await server_connection.get_model_info()
        
        assert result == {"model_id": "test-model", "loaded": True}

    @pytest.mark.asyncio
    async def test_generate_success(self, server_connection, mock_httpx_client):
        """Test successful text generation"""
        server_connection.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Generated text"}
        mock_httpx_client.post.return_value = mock_response
        
        result = await server_connection.generate("Test prompt", max_tokens=100)
        
        assert result == {"text": "Generated text"}

    @pytest.mark.asyncio
    async def test_generate_failure(self, server_connection, mock_httpx_client):
        """Test text generation failure"""
        server_connection.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_httpx_client.post.return_value = mock_response
        
        result = await server_connection.generate("Test prompt")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_stream_success(self, server_connection, mock_httpx_client):
        """Test successful streaming generation"""
        server_connection.client = mock_httpx_client
        
        # Mock streaming response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.aiter_lines.return_value = [
            "data: chunk1",
            "data: chunk2",
            "data: [DONE]"
        ]
        mock_httpx_client.stream.return_value.__aenter__.return_value = mock_response
        
        chunks = []
        async for chunk in server_connection.generate_stream("Test prompt"):
            chunks.append(chunk)
        
        assert chunks == ["chunk1", "chunk2"]

    @pytest.mark.asyncio
    async def test_chat_completion_success(self, server_connection, mock_httpx_client):
        """Test successful chat completion"""
        server_connection.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Chat response"}}]
        }
        mock_httpx_client.post.return_value = mock_response
        
        messages = [{"role": "user", "content": "Hello"}]
        result = await server_connection.chat_completion(messages)
        
        assert result == {"choices": [{"message": {"content": "Chat response"}}]}

    @pytest.mark.asyncio
    async def test_batch_generate_success(self, server_connection, mock_httpx_client):
        """Test successful batch generation"""
        server_connection.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "responses": ["Response 1", "Response 2", "Response 3"]
        }
        mock_httpx_client.post.return_value = mock_response
        
        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
        result = await server_connection.batch_generate(prompts)
        
        assert result == {"responses": ["Response 1", "Response 2", "Response 3"]}

    @pytest.mark.asyncio
    async def test_batch_generate_failure(self, server_connection, mock_httpx_client):
        """Test batch generation failure"""
        server_connection.client = mock_httpx_client
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_httpx_client.post.return_value = mock_response
        
        prompts = ["Prompt 1", "Prompt 2"]
        result = await server_connection.batch_generate(prompts)
        
        assert result is None


class TestUtilityFunctions:
    """Test cases for utility functions"""

    @pytest.mark.asyncio
    async def test_detect_local_server_found(self):
        """Test local server detection when server is found"""
        with patch('locallab.cli.connection.is_port_in_use', return_value=True):
            result = await detect_local_server()
            
            assert result == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_detect_local_server_not_found(self):
        """Test local server detection when no server is found"""
        with patch('locallab.cli.connection.is_port_in_use', return_value=False):
            result = await detect_local_server()
            
            assert result is None

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test"""
        mock_connection = AsyncMock()
        mock_connection.connect.return_value = True
        mock_connection.health_check.return_value = True
        mock_connection.get_server_info.return_value = {"version": "0.9.0"}
        mock_connection.get_model_info.return_value = {"model_id": "test-model"}
        
        with patch('locallab.cli.connection.ServerConnection', return_value=mock_connection):
            success, info = await test_connection("http://localhost:8000")
            
            assert success is True
            assert info["server_info"] == {"version": "0.9.0"}
            assert info["model_info"] == {"model_id": "test-model"}

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test connection test failure"""
        mock_connection = AsyncMock()
        mock_connection.connect.return_value = False
        
        with patch('locallab.cli.connection.ServerConnection', return_value=mock_connection):
            success, info = await test_connection("http://localhost:8000")
            
            assert success is False
            assert info is None

    @pytest.mark.asyncio
    async def test_test_connection_health_check_failure(self):
        """Test connection test with health check failure"""
        mock_connection = AsyncMock()
        mock_connection.connect.return_value = True
        mock_connection.health_check.return_value = False
        
        with patch('locallab.cli.connection.ServerConnection', return_value=mock_connection):
            success, info = await test_connection("http://localhost:8000")
            
            assert success is False
            assert info is None


if __name__ == "__main__":
    pytest.main([__file__])
