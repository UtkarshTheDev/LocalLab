"""
Integration tests for the LocalLab CLI chat command
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner
from locallab.cli.chat import chat_command, ChatInterface, GenerationMode


@pytest.fixture
def cli_runner():
    """Create Click CLI runner for testing"""
    return CliRunner()


@pytest.fixture
def mock_server_running():
    """Mock a running LocalLab server"""
    with patch('locallab.cli.connection.detect_local_server', return_value="http://localhost:8000"), \
         patch('locallab.cli.connection.test_connection', return_value=(True, {
             "server_info": {"version": "0.9.0", "status": "running"},
             "model_info": {"model_id": "test-model", "loaded": True}
         })):
        yield


@pytest.fixture
def mock_server_not_running():
    """Mock no LocalLab server running"""
    with patch('locallab.cli.connection.detect_local_server', return_value=None), \
         patch('locallab.cli.connection.test_connection', return_value=(False, None)):
        yield


class TestChatCommandCLI:
    """Test cases for the chat CLI command"""

    def test_chat_command_help(self, cli_runner):
        """Test chat command help display"""
        result = cli_runner.invoke(chat_command, ['--help'])
        
        assert result.exit_code == 0
        assert "Connect to and interact with a LocalLab server" in result.output
        assert "--url" in result.output
        assert "--generate" in result.output
        assert "--max-tokens" in result.output

    def test_chat_command_default_parameters(self, cli_runner, mock_server_not_running):
        """Test chat command with default parameters"""
        with patch('asyncio.run') as mock_run:
            result = cli_runner.invoke(chat_command)
            
            # Should attempt to run the chat interface
            mock_run.assert_called_once()

    def test_chat_command_custom_url(self, cli_runner, mock_server_not_running):
        """Test chat command with custom URL"""
        with patch('asyncio.run') as mock_run:
            result = cli_runner.invoke(chat_command, ['--url', 'http://custom.com'])
            
            mock_run.assert_called_once()

    def test_chat_command_generation_modes(self, cli_runner, mock_server_not_running):
        """Test chat command with different generation modes"""
        modes = ['stream', 'simple', 'chat', 'batch']
        
        for mode in modes:
            with patch('asyncio.run') as mock_run:
                result = cli_runner.invoke(chat_command, ['--generate', mode])
                
                mock_run.assert_called_once()

    def test_chat_command_custom_parameters(self, cli_runner, mock_server_not_running):
        """Test chat command with custom parameters"""
        with patch('asyncio.run') as mock_run:
            result = cli_runner.invoke(chat_command, [
                '--max-tokens', '200',
                '--temperature', '0.8',
                '--top-p', '0.95',
                '--verbose'
            ])
            
            mock_run.assert_called_once()

    def test_chat_command_keyboard_interrupt(self, cli_runner):
        """Test chat command handling keyboard interrupt"""
        with patch('asyncio.run', side_effect=KeyboardInterrupt):
            result = cli_runner.invoke(chat_command)
            
            assert result.exit_code == 0
            assert "Interrupted by user" in result.output or "Goodbye!" in result.output

    def test_chat_command_connection_error(self, cli_runner):
        """Test chat command handling connection error"""
        with patch('asyncio.run', side_effect=ConnectionError("Connection failed")):
            result = cli_runner.invoke(chat_command)
            
            assert result.exit_code == 1
            assert "Connection Error" in result.output

    def test_chat_command_timeout_error(self, cli_runner):
        """Test chat command handling timeout error"""
        with patch('asyncio.run', side_effect=asyncio.TimeoutError):
            result = cli_runner.invoke(chat_command)
            
            assert result.exit_code == 1
            assert "Timeout Error" in result.output

    def test_chat_command_unexpected_error(self, cli_runner):
        """Test chat command handling unexpected error"""
        with patch('asyncio.run', side_effect=Exception("Unexpected error")):
            result = cli_runner.invoke(chat_command)
            
            assert result.exit_code == 1
            assert "Unexpected Error" in result.output


class TestChatInterfaceIntegration:
    """Integration test cases for ChatInterface"""

    @pytest.mark.asyncio
    async def test_full_chat_flow_stream_mode(self):
        """Test complete chat flow in stream mode"""
        # Mock dependencies
        mock_connection = AsyncMock()
        mock_connection.connect.return_value = True
        mock_connection.health_check.return_value = True
        mock_connection.get_server_info.return_value = {"version": "0.9.0"}
        mock_connection.get_model_info.return_value = {"model_id": "test-model"}
        mock_connection.generate_stream.return_value = iter(["Hello", " world", "!"])
        
        mock_ui = MagicMock()
        mock_ui.get_user_input.side_effect = ["Hello", "/exit"]
        mock_ui.get_yes_no_input.return_value = False
        
        # Create interface
        interface = ChatInterface(
            url="http://localhost:8000",
            mode=GenerationMode.STREAM,
            max_tokens=100
        )
        interface.ui = mock_ui
        
        # Mock connection creation
        with patch('locallab.cli.chat.detect_local_server', return_value="http://localhost:8000"), \
             patch('locallab.cli.chat.test_connection', return_value=(True, {
                 "server_info": {"version": "0.9.0"},
                 "model_info": {"model_id": "test-model"}
             })), \
             patch('locallab.cli.chat.ServerConnection', return_value=mock_connection):
            
            # Run chat interface
            await interface.start_chat()
            
            # Verify interactions
            mock_ui.display_welcome.assert_called_once()
            mock_ui.display_connection_info.assert_called_once()
            assert mock_ui.get_user_input.call_count == 2  # "Hello" + "/exit"

    @pytest.mark.asyncio
    async def test_full_chat_flow_chat_mode(self):
        """Test complete chat flow in chat mode"""
        # Mock dependencies
        mock_connection = AsyncMock()
        mock_connection.connect.return_value = True
        mock_connection.health_check.return_value = True
        mock_connection.get_server_info.return_value = {"version": "0.9.0"}
        mock_connection.get_model_info.return_value = {"model_id": "test-model"}
        mock_connection.chat_completion.return_value = {
            "choices": [{"message": {"content": "Hello there!"}}]
        }
        
        mock_ui = MagicMock()
        mock_ui.get_user_input.side_effect = ["Hello", "/exit"]
        mock_ui.get_yes_no_input.return_value = False
        
        # Create interface
        interface = ChatInterface(
            url="http://localhost:8000",
            mode=GenerationMode.CHAT,
            max_tokens=100
        )
        interface.ui = mock_ui
        
        # Mock connection creation
        with patch('locallab.cli.chat.detect_local_server', return_value="http://localhost:8000"), \
             patch('locallab.cli.chat.test_connection', return_value=(True, {
                 "server_info": {"version": "0.9.0"},
                 "model_info": {"model_id": "test-model"}
             })), \
             patch('locallab.cli.chat.ServerConnection', return_value=mock_connection):
            
            # Run chat interface
            await interface.start_chat()
            
            # Verify chat completion was called
            mock_connection.chat_completion.assert_called_once()
            mock_ui.display_ai_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_chat_flow_batch_mode(self):
        """Test complete chat flow in batch mode"""
        # Mock dependencies
        mock_connection = AsyncMock()
        mock_connection.connect.return_value = True
        mock_connection.health_check.return_value = True
        mock_connection.get_server_info.return_value = {"version": "0.9.0"}
        mock_connection.get_model_info.return_value = {"model_id": "test-model"}
        mock_connection.batch_generate.return_value = {
            "responses": ["Response 1", "Response 2"]
        }
        
        mock_ui = MagicMock()
        mock_ui.get_user_input.side_effect = ["/batch", "/exit"]
        mock_ui.get_batch_prompts.return_value = ["Prompt 1", "Prompt 2"]
        mock_ui.get_yes_no_input.return_value = False
        
        # Create interface
        interface = ChatInterface(
            url="http://localhost:8000",
            mode=GenerationMode.BATCH,
            max_tokens=100
        )
        interface.ui = mock_ui
        
        # Mock connection creation
        with patch('locallab.cli.chat.detect_local_server', return_value="http://localhost:8000"), \
             patch('locallab.cli.chat.test_connection', return_value=(True, {
                 "server_info": {"version": "0.9.0"},
                 "model_info": {"model_id": "test-model"}
             })), \
             patch('locallab.cli.chat.ServerConnection', return_value=mock_connection):
            
            # Run chat interface
            await interface.start_chat()
            
            # Verify batch processing was triggered
            assert mock_ui.get_user_input.call_count == 2

    @pytest.mark.asyncio
    async def test_connection_failure_handling(self):
        """Test handling of connection failures"""
        mock_ui = MagicMock()
        
        # Create interface
        interface = ChatInterface(
            url="http://localhost:8000",
            mode=GenerationMode.STREAM
        )
        interface.ui = mock_ui
        
        # Mock connection failure
        with patch('locallab.cli.chat.detect_local_server', return_value=None), \
             patch('locallab.cli.chat.test_connection', return_value=(False, None)):
            
            # Run chat interface
            await interface.start_chat()
            
            # Verify error handling
            mock_ui.display_error.assert_called()

    @pytest.mark.asyncio
    async def test_reconnection_handling(self):
        """Test automatic reconnection handling"""
        # Mock dependencies
        mock_connection = AsyncMock()
        mock_connection.connect.side_effect = [True, False, True]  # Fail once, then succeed
        mock_connection.health_check.side_effect = [True, False, True]  # Fail once, then succeed
        mock_connection.get_server_info.return_value = {"version": "0.9.0"}
        mock_connection.get_model_info.return_value = {"model_id": "test-model"}
        
        mock_ui = MagicMock()
        mock_ui.get_user_input.side_effect = ["Hello", "/exit"]
        mock_ui.get_yes_no_input.return_value = False
        
        # Create interface with auto-reconnect
        interface = ChatInterface(
            url="http://localhost:8000",
            mode=GenerationMode.STREAM,
            max_tokens=100
        )
        interface.ui = mock_ui
        interface.auto_reconnect = True
        interface.max_retries = 2
        
        # Mock connection creation
        with patch('locallab.cli.chat.detect_local_server', return_value="http://localhost:8000"), \
             patch('locallab.cli.chat.test_connection', return_value=(True, {
                 "server_info": {"version": "0.9.0"},
                 "model_info": {"model_id": "test-model"}
             })), \
             patch('locallab.cli.chat.ServerConnection', return_value=mock_connection):
            
            # Run chat interface
            await interface.start_chat()
            
            # Verify reconnection attempts
            assert mock_connection.connect.call_count >= 1


if __name__ == "__main__":
    pytest.main([__file__])
