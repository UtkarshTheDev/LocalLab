"""
Comprehensive tests for the LocalLab CLI chat interface
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from locallab.cli.chat import ChatInterface, GenerationMode, parse_inline_mode
from locallab.cli.connection import ServerConnection
from locallab.cli.ui import ChatUI


@pytest.fixture
def mock_connection():
    """Mock ServerConnection for testing"""
    connection = AsyncMock(spec=ServerConnection)
    connection.health_check.return_value = True
    connection.get_server_info.return_value = {"version": "0.9.0"}
    connection.get_model_info.return_value = {"model_id": "test-model"}
    connection.generate_stream.return_value = iter(["chunk1", "chunk2", "chunk3"])
    connection.generate.return_value = {"text": "Test response"}
    connection.chat_completion.return_value = {"choices": [{"message": {"content": "Test chat response"}}]}
    connection.batch_generate.return_value = {"responses": ["Response 1", "Response 2"]}
    return connection


@pytest.fixture
def mock_ui():
    """Mock ChatUI for testing"""
    ui = MagicMock(spec=ChatUI)
    ui.get_user_input.return_value = "test input"
    ui.get_yes_no_input.return_value = True
    return ui


@pytest.fixture
def chat_interface(mock_ui):
    """Create ChatInterface instance for testing"""
    interface = ChatInterface(
        url="http://localhost:8000",
        mode=GenerationMode.STREAM,
        max_tokens=100,
        temperature=0.7,
        top_p=0.9
    )
    interface.ui = mock_ui
    return interface


class TestChatInterface:
    """Test cases for ChatInterface class"""

    def test_initialization(self):
        """Test ChatInterface initialization"""
        interface = ChatInterface(
            url="http://test.com",
            mode=GenerationMode.CHAT,
            max_tokens=200,
            temperature=0.8,
            top_p=0.95
        )
        
        assert interface.url == "http://test.com"
        assert interface.mode == GenerationMode.CHAT
        assert interface.max_tokens == 200
        assert interface.temperature == 0.8
        assert interface.top_p == 0.95
        assert interface.session_history == []
        assert interface.connected is False
        assert interface.connection is None
        assert interface.max_retries == 3
        assert interface.retry_delay == 2.0
        assert interface.auto_reconnect is True
        assert interface.graceful_shutdown is False

    @pytest.mark.asyncio
    async def test_connect_success(self, chat_interface, mock_connection):
        """Test successful connection"""
        with patch('locallab.cli.chat.detect_local_server', return_value="http://localhost:8000"), \
             patch('locallab.cli.chat.test_connection', return_value=(True, {"server_info": {}, "model_info": {}})), \
             patch('locallab.cli.chat.ServerConnection', return_value=mock_connection):
            
            result = await chat_interface.connect()
            
            assert result is True
            assert chat_interface.connected is True
            assert chat_interface.connection is not None

    @pytest.mark.asyncio
    async def test_connect_failure(self, chat_interface):
        """Test connection failure"""
        with patch('locallab.cli.chat.detect_local_server', return_value=None), \
             patch('locallab.cli.chat.test_connection', return_value=(False, None)):
            
            result = await chat_interface.connect()
            
            assert result is False
            assert chat_interface.connected is False
            assert chat_interface.connection is None

    @pytest.mark.asyncio
    async def test_disconnect(self, chat_interface, mock_connection):
        """Test disconnection"""
        chat_interface.connection = mock_connection
        chat_interface.connected = True
        
        await chat_interface.disconnect()
        
        mock_connection.disconnect.assert_called_once()
        assert chat_interface.connection is None
        assert chat_interface.connected is False

    @pytest.mark.asyncio
    async def test_check_connection_healthy(self, chat_interface, mock_connection):
        """Test connection health check when healthy"""
        chat_interface.connection = mock_connection
        chat_interface.connected = True
        mock_connection.health_check.return_value = True
        
        result = await chat_interface._check_connection()
        
        assert result is True
        assert chat_interface.connected is True

    @pytest.mark.asyncio
    async def test_check_connection_unhealthy(self, chat_interface, mock_connection):
        """Test connection health check when unhealthy"""
        chat_interface.connection = mock_connection
        chat_interface.connected = True
        mock_connection.health_check.return_value = False
        
        result = await chat_interface._check_connection()
        
        assert result is False
        assert chat_interface.connected is False

    @pytest.mark.asyncio
    async def test_attempt_reconnection_success(self, chat_interface, mock_connection):
        """Test successful reconnection"""
        chat_interface.url = "http://localhost:8000"
        chat_interface.auto_reconnect = True
        chat_interface.graceful_shutdown = False
        
        with patch('locallab.cli.chat.ServerConnection', return_value=mock_connection):
            mock_connection.connect.return_value = True
            
            result = await chat_interface._attempt_reconnection()
            
            assert result is True
            assert chat_interface.connected is True

    @pytest.mark.asyncio
    async def test_attempt_reconnection_failure(self, chat_interface, mock_connection):
        """Test failed reconnection"""
        chat_interface.url = "http://localhost:8000"
        chat_interface.auto_reconnect = True
        chat_interface.graceful_shutdown = False
        chat_interface.max_retries = 1  # Reduce for faster testing
        
        with patch('locallab.cli.chat.ServerConnection', return_value=mock_connection):
            mock_connection.connect.return_value = False
            
            result = await chat_interface._attempt_reconnection()
            
            assert result is False
            assert chat_interface.connected is False

    @pytest.mark.asyncio
    async def test_handle_command_exit(self, chat_interface):
        """Test exit command handling"""
        result = await chat_interface._handle_command('/exit')
        
        assert result is True
        assert chat_interface.graceful_shutdown is True

    @pytest.mark.asyncio
    async def test_handle_command_help(self, chat_interface, mock_ui):
        """Test help command handling"""
        result = await chat_interface._handle_command('/help')
        
        assert result is False
        mock_ui.display_help.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_command_clear(self, chat_interface, mock_ui):
        """Test clear command handling"""
        result = await chat_interface._handle_command('/clear')
        
        assert result is False
        mock_ui.clear_screen.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_command_reset(self, chat_interface):
        """Test reset command handling"""
        chat_interface.session_history = ["message1", "message2"]
        
        result = await chat_interface._handle_command('/reset')
        
        assert result is False
        assert len(chat_interface.session_history) == 0

    @pytest.mark.asyncio
    async def test_process_message_stream_mode(self, chat_interface, mock_connection):
        """Test message processing in stream mode"""
        chat_interface.mode = GenerationMode.STREAM
        chat_interface.connection = mock_connection
        chat_interface.connected = True
        
        with patch.object(chat_interface, '_check_connection', return_value=True), \
             patch.object(chat_interface, '_generate_stream_with_recovery') as mock_stream:
            
            await chat_interface._process_message("test message")
            
            mock_stream.assert_called_once_with("test message")

    @pytest.mark.asyncio
    async def test_process_message_chat_mode(self, chat_interface, mock_connection):
        """Test message processing in chat mode"""
        chat_interface.mode = GenerationMode.CHAT
        chat_interface.connection = mock_connection
        chat_interface.connected = True
        chat_interface.model_info = {"model_id": "test-model"}
        
        with patch.object(chat_interface, '_check_connection', return_value=True), \
             patch.object(chat_interface, '_chat_completion_with_recovery', return_value={"text": "response"}), \
             patch.object(chat_interface, '_extract_response_text', return_value="response"):
            
            await chat_interface._process_message("test message")
            
            chat_interface.ui.display_ai_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_batch_mode(self, chat_interface, mock_connection):
        """Test message processing in batch mode"""
        chat_interface.mode = GenerationMode.BATCH
        chat_interface.connection = mock_connection
        chat_interface.connected = True
        
        with patch.object(chat_interface, '_check_connection', return_value=True), \
             patch.object(chat_interface, '_process_batch_with_recovery') as mock_batch:
            
            await chat_interface._process_message("test message")
            
            mock_batch.assert_called_once_with(["test message"])

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, chat_interface, mock_ui):
        """Test graceful shutdown process"""
        chat_interface.session_history = ["message1", "message2"]
        mock_ui.get_yes_no_input.return_value = False  # Don't save conversation
        
        with patch.object(chat_interface, 'disconnect') as mock_disconnect:
            await chat_interface._graceful_shutdown()
            
            mock_disconnect.assert_called_once()
            mock_ui.display_info.assert_called()

    @pytest.mark.asyncio
    async def test_cleanup(self, chat_interface, mock_connection):
        """Test cleanup operations"""
        chat_interface.connection = mock_connection
        chat_interface.connected = True
        chat_interface.session_history = ["message1", "message2"]
        chat_interface.server_info = {"version": "0.9.0"}
        chat_interface.model_info = {"model_id": "test-model"}
        
        with patch.object(chat_interface, 'disconnect') as mock_disconnect:
            await chat_interface._cleanup()
            
            mock_disconnect.assert_called_once()
            assert len(chat_interface.session_history) == 0
            assert chat_interface.server_info is None
            assert chat_interface.model_info is None

    def test_extract_response_text_simple(self, chat_interface):
        """Test response text extraction from simple response"""
        response = {"text": "Simple response"}
        result = chat_interface._extract_response_text(response)
        assert result == "Simple response"

    def test_extract_response_text_choices(self, chat_interface):
        """Test response text extraction from choices format"""
        response = {"choices": [{"message": {"content": "Choice response"}}]}
        result = chat_interface._extract_response_text(response)
        assert result == "Choice response"

    def test_extract_response_text_generated_text(self, chat_interface):
        """Test response text extraction from generated_text format"""
        response = {"generated_text": "Generated response"}
        result = chat_interface._extract_response_text(response)
        assert result == "Generated response"

    def test_extract_response_text_fallback(self, chat_interface):
        """Test response text extraction fallback to string conversion"""
        response = "Direct string response"
        result = chat_interface._extract_response_text(response)
        assert result == "Direct string response"


class TestGenerationMode:
    """Test cases for GenerationMode enum"""

    def test_generation_mode_values(self):
        """Test GenerationMode enum values"""
        assert GenerationMode.STREAM == "stream"
        assert GenerationMode.SIMPLE == "simple"
        assert GenerationMode.CHAT == "chat"
        assert GenerationMode.BATCH == "batch"

    def test_generation_mode_creation(self):
        """Test GenerationMode creation from string"""
        assert GenerationMode("stream") == GenerationMode.STREAM
        assert GenerationMode("simple") == GenerationMode.SIMPLE
        assert GenerationMode("chat") == GenerationMode.CHAT
        assert GenerationMode("batch") == GenerationMode.BATCH


class TestInlineModeParsing:
    """Test cases for inline mode switching functionality"""

    def test_valid_mode_switches(self):
        """Test parsing of valid mode switches"""
        test_cases = [
            ("Hello world --stream", "Hello world", GenerationMode.STREAM, None),
            ("Explain Python --chat", "Explain Python", GenerationMode.CHAT, None),
            ("Write a story --simple", "Write a story", GenerationMode.SIMPLE, None),
            ("Process this --batch", "Process this", GenerationMode.BATCH, None),
        ]

        for input_msg, expected_msg, expected_mode, expected_error in test_cases:
            result_msg, result_mode, result_error = parse_inline_mode(input_msg)
            assert result_msg == expected_msg
            assert result_mode == expected_mode
            assert result_error == expected_error

    def test_case_insensitive_modes(self):
        """Test that mode switches are case insensitive"""
        test_cases = [
            ("Hello --STREAM", "Hello", GenerationMode.STREAM, None),
            ("Test --Chat", "Test", GenerationMode.CHAT, None),
            ("Message --SIMPLE", "Message", GenerationMode.SIMPLE, None),
            ("Process --BATCH", "Process", GenerationMode.BATCH, None),
        ]

        for input_msg, expected_msg, expected_mode, expected_error in test_cases:
            result_msg, result_mode, result_error = parse_inline_mode(input_msg)
            assert result_msg == expected_msg
            assert result_mode == expected_mode
            assert result_error == expected_error

    def test_mode_with_extra_spaces(self):
        """Test mode switches with extra whitespace"""
        test_cases = [
            ("Message --stream   ", "Message", GenerationMode.STREAM, None),
            ("  Another test   --batch  ", "Another test", GenerationMode.BATCH, None),
            ("   --chat   ", "", GenerationMode.CHAT, None),
        ]

        for input_msg, expected_msg, expected_mode, expected_error in test_cases:
            result_msg, result_mode, result_error = parse_inline_mode(input_msg)
            assert result_msg == expected_msg
            assert result_mode == expected_mode
            assert result_error == expected_error

    def test_no_mode_switch(self):
        """Test messages without mode switches"""
        test_cases = [
            ("Just a regular message", "Just a regular message", None, None),
            ("Message with --stream in middle", "Message with --stream in middle", None, None),
            ("", "", None, None),
            ("   ", "", None, None),
        ]

        for input_msg, expected_msg, expected_mode, expected_error in test_cases:
            result_msg, result_mode, result_error = parse_inline_mode(input_msg)
            assert result_msg == expected_msg
            assert result_mode == expected_mode
            assert result_error == expected_error

    def test_invalid_mode_switches(self):
        """Test handling of invalid mode switches"""
        test_cases = [
            ("Test --invalid", "Test --invalid", None, "Invalid mode: --invalid. Valid modes: --stream, --chat, --batch, --simple"),
            ("Hello --wrong", "Hello --wrong", None, "Invalid mode: --wrong. Valid modes: --stream, --chat, --batch, --simple"),
            ("--invalid", "--invalid", None, "Invalid mode: --invalid. Valid modes: --stream, --chat, --batch, --simple"),
        ]

        for input_msg, expected_msg, expected_mode, expected_error in test_cases:
            result_msg, result_mode, result_error = parse_inline_mode(input_msg)
            assert result_msg == expected_msg
            assert result_mode == expected_mode
            assert result_error == expected_error

    def test_mode_only_messages(self):
        """Test messages that are only mode switches"""
        test_cases = [
            ("--stream", "", GenerationMode.STREAM, None),
            ("--chat", "", GenerationMode.CHAT, None),
            ("--simple", "", GenerationMode.SIMPLE, None),
            ("--batch", "", GenerationMode.BATCH, None),
        ]

        for input_msg, expected_msg, expected_mode, expected_error in test_cases:
            result_msg, result_mode, result_error = parse_inline_mode(input_msg)
            assert result_msg == expected_msg
            assert result_mode == expected_mode
            assert result_error == expected_error


if __name__ == "__main__":
    pytest.main([__file__])
