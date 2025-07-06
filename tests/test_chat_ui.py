"""
Tests for the LocalLab CLI chat UI module
"""

import pytest
from unittest.mock import MagicMock, patch
from rich.console import Console
from rich.text import Text
from locallab.cli.ui import ChatUI, StreamingDisplay, BatchProgressDisplay


@pytest.fixture
def mock_console():
    """Mock Rich Console for testing"""
    console = MagicMock(spec=Console)
    return console


@pytest.fixture
def chat_ui(mock_console):
    """Create ChatUI instance for testing"""
    with patch('locallab.cli.ui.Console', return_value=mock_console):
        ui = ChatUI()
        ui.console = mock_console
        return ui


class TestChatUI:
    """Test cases for ChatUI class"""

    def test_initialization(self, chat_ui, mock_console):
        """Test ChatUI initialization"""
        assert chat_ui.console == mock_console
        assert chat_ui.status_text == ""

    def test_display_welcome(self, chat_ui, mock_console):
        """Test welcome message display"""
        chat_ui.display_welcome()
        
        # Verify console.print was called
        assert mock_console.print.called

    def test_display_connection_info(self, chat_ui, mock_console):
        """Test connection info display"""
        server_info = {"version": "0.9.0", "status": "running"}
        model_info = {"model_id": "test-model", "loaded": True}
        
        chat_ui.display_connection_info("http://localhost:8000", server_info, model_info)
        
        # Verify console.print was called multiple times
        assert mock_console.print.call_count >= 1

    def test_display_help(self, chat_ui, mock_console):
        """Test help display"""
        chat_ui.display_help()
        
        # Verify console.print was called
        assert mock_console.print.called

    def test_display_error(self, chat_ui, mock_console):
        """Test error display"""
        chat_ui.display_error("Test error message")
        
        # Verify console.print was called with error styling
        mock_console.print.assert_called()

    def test_display_warning(self, chat_ui, mock_console):
        """Test warning display"""
        chat_ui.display_warning("Test warning message")
        
        # Verify console.print was called with warning styling
        mock_console.print.assert_called()

    def test_display_info(self, chat_ui, mock_console):
        """Test info display"""
        chat_ui.display_info("Test info message")
        
        # Verify console.print was called with info styling
        mock_console.print.assert_called()

    def test_display_success(self, chat_ui, mock_console):
        """Test success display"""
        chat_ui.display_success("Test success message")
        
        # Verify console.print was called with success styling
        mock_console.print.assert_called()

    def test_display_user_prompt(self, chat_ui, mock_console):
        """Test user prompt display"""
        chat_ui.display_user_prompt("Test user message")
        
        # Verify console.print was called
        assert mock_console.print.called

    def test_display_ai_response(self, chat_ui, mock_console):
        """Test AI response display"""
        chat_ui.display_ai_response("Test AI response")
        
        # Verify console.print was called
        assert mock_console.print.called

    def test_display_ai_response_with_markdown(self, chat_ui, mock_console):
        """Test AI response display with markdown"""
        markdown_text = "# Header\n\n```python\nprint('hello')\n```"
        chat_ui.display_ai_response(markdown_text)
        
        # Verify console.print was called
        assert mock_console.print.called

    def test_clear_screen(self, chat_ui, mock_console):
        """Test screen clearing"""
        chat_ui.clear_screen()
        
        # Verify console.clear was called
        mock_console.clear.assert_called_once()

    def test_get_user_input(self, chat_ui):
        """Test user input retrieval"""
        with patch('locallab.cli.ui.Prompt.ask', return_value="test input"):
            result = chat_ui.get_user_input()
            
            assert result == "test input"

    def test_get_user_input_keyboard_interrupt(self, chat_ui):
        """Test user input with keyboard interrupt"""
        with patch('locallab.cli.ui.Prompt.ask', side_effect=KeyboardInterrupt):
            result = chat_ui.get_user_input()
            
            assert result is None

    def test_get_user_input_eof_error(self, chat_ui):
        """Test user input with EOF error"""
        with patch('locallab.cli.ui.Prompt.ask', side_effect=EOFError):
            result = chat_ui.get_user_input()
            
            assert result is None

    def test_get_yes_no_input_yes(self, chat_ui):
        """Test yes/no input with yes response"""
        with patch('locallab.cli.ui.Prompt.ask', return_value="y"):
            result = chat_ui.get_yes_no_input("Test question?")
            
            assert result is True

    def test_get_yes_no_input_no(self, chat_ui):
        """Test yes/no input with no response"""
        with patch('locallab.cli.ui.Prompt.ask', return_value="n"):
            result = chat_ui.get_yes_no_input("Test question?")
            
            assert result is False

    def test_get_yes_no_input_default_true(self, chat_ui):
        """Test yes/no input with default true"""
        with patch('locallab.cli.ui.Prompt.ask', return_value=""):
            result = chat_ui.get_yes_no_input("Test question?", default=True)
            
            assert result is True

    def test_get_yes_no_input_default_false(self, chat_ui):
        """Test yes/no input with default false"""
        with patch('locallab.cli.ui.Prompt.ask', return_value=""):
            result = chat_ui.get_yes_no_input("Test question?", default=False)
            
            assert result is False

    def test_get_yes_no_input_keyboard_interrupt(self, chat_ui):
        """Test yes/no input with keyboard interrupt"""
        with patch('locallab.cli.ui.Prompt.ask', side_effect=KeyboardInterrupt):
            result = chat_ui.get_yes_no_input("Test question?")
            
            assert result is False

    def test_update_status(self, chat_ui, mock_console):
        """Test status update"""
        chat_ui.update_status("Test status")
        
        assert chat_ui.status_text == "Test status"
        mock_console.print.assert_called()

    def test_display_streaming(self, chat_ui, mock_console):
        """Test streaming display context manager"""
        streaming_display = chat_ui.display_streaming()
        
        assert isinstance(streaming_display, StreamingDisplay)

    def test_display_batch_progress(self, chat_ui, mock_console):
        """Test batch progress display context manager"""
        batch_progress = chat_ui.display_batch_progress()
        
        assert isinstance(batch_progress, BatchProgressDisplay)

    def test_display_conversation_history_empty(self, chat_ui, mock_console):
        """Test conversation history display when empty"""
        chat_ui.display_conversation_history([])
        
        # Should display empty message
        mock_console.print.assert_called()

    def test_display_conversation_history_with_messages(self, chat_ui, mock_console):
        """Test conversation history display with messages"""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        chat_ui.display_conversation_history(history)
        
        # Should display messages
        assert mock_console.print.call_count >= len(history)

    def test_display_conversation_stats(self, chat_ui, mock_console):
        """Test conversation statistics display"""
        stats = {
            "total_messages": 10,
            "user_messages": 5,
            "assistant_messages": 5,
            "total_tokens": 1000
        }
        
        chat_ui.display_conversation_stats(stats)
        
        # Should display stats
        mock_console.print.assert_called()


class TestStreamingDisplay:
    """Test cases for StreamingDisplay class"""

    def test_initialization(self, mock_console):
        """Test StreamingDisplay initialization"""
        display = StreamingDisplay(mock_console)
        
        assert display.console == mock_console
        assert display.current_text == ""

    def test_context_manager(self, mock_console):
        """Test StreamingDisplay as context manager"""
        with StreamingDisplay(mock_console) as display:
            assert isinstance(display, StreamingDisplay)

    def test_add_chunk(self, mock_console):
        """Test adding text chunk"""
        display = StreamingDisplay(mock_console)
        
        display.add_chunk("Hello ")
        display.add_chunk("world!")
        
        assert display.current_text == "Hello world!"

    def test_finalize(self, mock_console):
        """Test finalizing display"""
        display = StreamingDisplay(mock_console)
        display.current_text = "Test text"
        
        display.finalize()
        
        # Should call console.print
        mock_console.print.assert_called()


class TestBatchProgressDisplay:
    """Test cases for BatchProgressDisplay class"""

    def test_initialization(self, mock_console):
        """Test BatchProgressDisplay initialization"""
        display = BatchProgressDisplay(mock_console)
        
        assert display.console == mock_console

    def test_context_manager(self, mock_console):
        """Test BatchProgressDisplay as context manager"""
        with BatchProgressDisplay(mock_console) as display:
            assert isinstance(display, BatchProgressDisplay)

    def test_start_batch(self, mock_console):
        """Test starting batch processing"""
        display = BatchProgressDisplay(mock_console)
        
        display.start_batch(5)
        
        # Should initialize progress tracking
        assert hasattr(display, 'total_items')

    def test_update_progress(self, mock_console):
        """Test updating progress"""
        display = BatchProgressDisplay(mock_console)
        display.start_batch(5)
        
        display.update_progress(2)
        
        # Should update progress display
        mock_console.print.assert_called()

    def test_finish_batch(self, mock_console):
        """Test finishing batch processing"""
        display = BatchProgressDisplay(mock_console)
        display.start_batch(5)
        
        display.finish_batch()
        
        # Should finalize progress display
        mock_console.print.assert_called()


class TestLanguageDetection:
    """Test cases for language detection and syntax highlighting"""

    def test_detect_language_python(self, chat_ui):
        """Test Python language detection"""
        code = "def hello():\n    print('world')"
        language = chat_ui._detect_language(code)
        assert language == "python"

    def test_detect_language_javascript(self, chat_ui):
        """Test JavaScript language detection"""
        code = "function hello() {\n    console.log('world');\n}"
        language = chat_ui._detect_language(code)
        assert language == "javascript"

    def test_detect_language_unknown(self, chat_ui):
        """Test unknown language detection"""
        code = "some random text without clear language indicators"
        language = chat_ui._detect_language(code)
        assert language == "text"

    def test_normalize_language_alias(self, chat_ui):
        """Test language alias normalization"""
        assert chat_ui._normalize_language("js") == "javascript"
        assert chat_ui._normalize_language("py") == "python"
        assert chat_ui._normalize_language("sh") == "bash"
        assert chat_ui._normalize_language("unknown") == "unknown"


if __name__ == "__main__":
    pytest.main([__file__])
