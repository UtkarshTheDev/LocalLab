"""
Terminal UI utilities for LocalLab CLI chat interface
"""

import sys
import os
from typing import Optional, List, Dict, Any
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.rule import Rule
from rich.live import Live
from rich.spinner import Spinner
import re

from ..logger import get_logger

logger = get_logger("locallab.cli.ui")


class ChatUI:
    """Terminal UI for chat interface"""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.message_count = 0
        
    def display_welcome(self, server_url: str, mode: str, model_info: Optional[Dict[str, Any]] = None):
        """Display enhanced welcome with ASCII banner and usage guide"""
        # Clear any previous content and start fresh
        self.console.clear()

        # ASCII Art Banner with complete "LOCALLAB" text - no border, just bottom line
        banner_lines = [
            "",
            "  ██╗      ██████╗  ██████╗ █████╗ ██╗     ██╗      █████╗ ██████╗",
            "  ██║     ██╔═══██╗██╔════╝██╔══██╗██║     ██║     ██╔══██╗██╔══██╗",
            "  ██║     ██║   ██║██║     ███████║██║     ██║     ███████║██████╔╝",
            "  ██║     ██║   ██║██║     ██╔══██║██║     ██║     ██╔══██║██╔══██╗",
            "  ███████╗╚██████╔╝╚██████╗██║  ██║███████╗███████╗██║  ██║██████╔╝",
            "  ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝╚═════╝",
            "",
            "                           Chat Interface",
            "",
            "─────────────────────────────────────────────────────────────────"
        ]

        # Display banner with balanced color - lighter but not too dark
        for line in banner_lines:
            banner_text = Text()
            banner_text.append(line, style="bright_blue")
            self.console.print(banner_text)

        # Connection status with modern styling and horizontal padding
        status_text = Text()
        status_text.append("    ●", style="bright_green")  # Added horizontal padding
        status_text.append(" Connected", style="dim bright_white")

        # Model info if available
        if model_info and (model_info.get('model_id') or model_info.get('id')):
            model_name = model_info.get('model_id') or model_info.get('id') or model_info.get('name')
            display_name = model_name.split('/')[-1] if '/' in model_name else model_name
            display_name = display_name.replace('-Instruct', '').replace('-Chat', '')
            status_text.append(f" • {display_name}", style="dim bright_cyan")

        self.console.print(status_text)

        # Concise usage guide with horizontal padding
        usage_text = Text()
        usage_text.append("    Usage: ", style="dim bright_white")  # Added horizontal padding
        usage_text.append("Type your message or use ", style="dim white")
        usage_text.append("--stream", style="bright_cyan")
        usage_text.append(", ", style="dim white")
        usage_text.append("--chat", style="bright_cyan")
        usage_text.append(", ", style="dim white")
        usage_text.append("--batch", style="bright_cyan")
        usage_text.append(", ", style="dim white")
        usage_text.append("--simple", style="bright_cyan")
        usage_text.append(" to override modes", style="dim white")

        self.console.print(usage_text)
        self.console.print()  # Single line break before chat starts
        
    def display_help(self):
        """Display help information"""
        help_text = Text()
        help_text.append("Available commands:\n", style="bold")
        help_text.append("\n📋 Basic Commands:\n", style="bold yellow")
        help_text.append("  /help     - Show this help message\n", style="cyan")
        help_text.append("  /clear    - Clear the screen\n", style="cyan")
        help_text.append("  /exit     - Exit the chat gracefully\n", style="cyan")
        help_text.append("  /quit     - Same as /exit\n", style="cyan")
        help_text.append("  /bye      - Same as /exit\n", style="cyan")
        help_text.append("  /goodbye  - Same as /exit\n", style="cyan")
        help_text.append("\n💬 Conversation Management:\n", style="bold yellow")
        help_text.append("  /history  - Show conversation history\n", style="cyan")
        help_text.append("  /reset    - Reset conversation history\n", style="cyan")
        help_text.append("  /stats    - Show conversation statistics\n", style="cyan")
        help_text.append("\n💾 Save/Load:\n", style="bold yellow")
        help_text.append("  /save     - Save conversation to file\n", style="cyan")
        help_text.append("  /load     - Load conversation from file\n", style="cyan")
        help_text.append("\n🔄 Batch Processing:\n", style="bold yellow")
        help_text.append("  /batch    - Enter batch processing mode\n", style="cyan")
        help_text.append("\n🎯 Inline Mode Switching:\n", style="bold yellow")
        help_text.append("  Add mode switches to any message:\n", style="white")
        help_text.append("  • --stream  - Stream response in real-time\n", style="cyan")
        help_text.append("  • --chat    - Use conversational mode\n", style="cyan")
        help_text.append("  • --batch   - Process as single batch item\n", style="cyan")
        help_text.append("  • --simple  - Simple text generation\n", style="cyan")
        help_text.append("\n  Examples:\n", style="white")
        help_text.append("  'Hello world --stream'\n", style="dim")
        help_text.append("  'Explain Python --chat'\n", style="dim")
        help_text.append("  'Write a story --simple'\n", style="dim")
        help_text.append("\n✨ Or just type your message and press Enter!", style="green")

        panel = Panel(help_text, title="🤖 LocalLab Chat Help", border_style="blue")
        self.console.print(panel)
        
    def get_user_input(self) -> Optional[str]:
        """Get user input with enhanced chat-style prompt"""
        try:
            # Enhanced chat-style prompt with better visual distinction
            prompt_text = "[bold bright_white]You[/bold bright_white][dim white]:[/dim white]"
            user_input = Prompt.ask(prompt_text, console=self.console)

            if user_input.strip():
                self.message_count += 1
                return user_input.strip()
            return None

        except (KeyboardInterrupt, EOFError):
            return None
            
    def display_user_message(self, message: str):
        """Display user message with enhanced chat-style formatting and horizontal padding"""
        # Create a more chat-like user message display with padding
        user_text = Text()
        user_text.append("    You", style="bold bright_white")  # Added horizontal padding
        user_text.append(": ", style="dim white")
        user_text.append(message, style="bright_white")

        self.console.print(user_text)
        # No extra spacing after user message for tighter conversation flow
        
    def display_ai_response(self, response: str, model_name: Optional[str] = None):
        """Display AI response with enhanced chat-style formatting and horizontal padding"""
        # Enhanced AI response header with better visual distinction and padding
        ai_label = model_name.split('/')[-1] if model_name and '/' in model_name else (model_name or "AI")
        ai_label = ai_label.replace('-Instruct', '').replace('-Chat', '')  # Clean up model name

        header = Text()
        header.append("    " + ai_label, style="bold bright_cyan")  # Added horizontal padding
        header.append(": ", style="dim white")

        self.console.print(header, end="")

        # Enhanced markdown rendering with subdued styling for better hierarchy
        try:
            rendered_content = self._render_enhanced_markdown(response)
            self.console.print(rendered_content)
        except Exception as e:
            # Fallback to plain text with subdued styling (lighter than user text)
            self.console.print(response, style="white")

        # Add spacing after AI response for better conversation flow
        self.console.print()
        
    def display_streaming_response(self, model_name: Optional[str] = None):
        """Start displaying a streaming response with enhanced chat-style formatting and horizontal padding"""
        ai_label = model_name.split('/')[-1] if model_name and '/' in model_name else (model_name or "AI")
        ai_label = ai_label.replace('-Instruct', '').replace('-Chat', '')  # Clean up model name

        header = Text()
        header.append("    " + ai_label, style="bold bright_cyan")  # Added horizontal padding
        header.append(": ", style="dim white")
        self.console.print(header, end="")

        # Return a context manager for streaming with UI instance for markdown processing
        return StreamingDisplay(self.console, ui_instance=self)
        
    def display_error(self, error_message: str, silent: bool = False):
        """Display error message with professional chat-style formatting and horizontal padding"""
        if silent:
            # In silent mode, only log the error
            logger.debug(f"Silent error: {error_message}")
            return

        error_text = Text()
        error_text.append("    System", style="bold red")  # Added horizontal padding
        error_text.append(": ", style="dim white")
        error_text.append(error_message, style="bright_white")

        self.console.print(error_text)
        self.console.print()  # Add spacing after error

    def display_connection_error(self, error_message: str, silent: bool = True):
        """Display connection error with modern minimal handling"""
        if silent:
            # For connection errors, show a very subtle indicator
            self.display_subtle_status("Connection issue", "dim yellow")
            logger.debug(f"Connection error: {error_message}")
        else:
            self.display_error(error_message)

    def display_subtle_status(self, message: str, style: str = "dim white"):
        """Display a subtle status message with modern minimal styling"""
        status_text = Text()
        status_text.append(f"{message}", style=style)
        self.console.print(status_text)
        
    def display_info(self, info_message: str):
        """Display info message with modern minimal styling and horizontal padding"""
        info_text = Text()
        info_text.append("    " + info_message, style="dim white")  # Added horizontal padding

        self.console.print(info_text)
        
    def display_separator(self):
        """Display a minimal separator"""
        # Modern minimal separator - just a blank line
        self.console.print()
        
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def display_goodbye(self):
        """Display minimal goodbye message with horizontal padding"""
        goodbye_text = Text()
        goodbye_text.append("    Goodbye", style="dim white")  # Added horizontal padding

        self.console.print(goodbye_text)
        
    def _contains_markdown(self, text: str) -> bool:
        """Check if text contains markdown syntax"""
        markdown_patterns = [
            r'```[\s\S]*?```',      # Code blocks
            r'`[^`\n]+`',           # Inline code (no newlines)
            r'\*\*[^*\n]+\*\*',     # Bold
            r'\*[^*\n]+\*',         # Italic
            r'__[^_\n]+__',         # Bold (underscore)
            r'_[^_\n]+_',           # Italic (underscore)
            r'#{1,6}\s+.+',         # Headers
            r'^\s*[-*+]\s+.+',      # Unordered lists
            r'^\s*\d+\.\s+.+',      # Numbered lists
            r'\[.+\]\(.+\)',        # Links
            r'!\[.*\]\(.+\)',       # Images
            r'^\s*>\s+.+',          # Blockquotes
            r'^\s*\|.+\|',          # Tables
            r'---+',                # Horizontal rules
        ]

        for pattern in markdown_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return True
        return False

    def _render_enhanced_markdown(self, text: str):
        """Enhanced markdown rendering with syntax highlighting for code blocks"""
        # Check if text contains code blocks that need special handling
        if self._contains_code_blocks(text):
            return self._render_with_syntax_highlighting(text)
        elif self._contains_markdown(text):
            # Use Rich's built-in markdown renderer for standard markdown
            return Markdown(text)
        else:
            # Plain text with subdued styling for better hierarchy
            return Text(text, style="white")

    def _contains_code_blocks(self, text: str) -> bool:
        """Check if text contains code blocks with language specifications"""
        code_block_pattern = r'```(\w+)?\s*\n[\s\S]*?\n```'
        return bool(re.search(code_block_pattern, text, re.MULTILINE))

    def _render_with_syntax_highlighting(self, text: str):
        """Render text with enhanced syntax highlighting for code blocks"""
        # Split text into parts: before code, code blocks, after code
        parts = []
        last_end = 0

        # Find all code blocks
        code_block_pattern = r'```(\w+)?\s*\n([\s\S]*?)\n```'

        for match in re.finditer(code_block_pattern, text, re.MULTILINE):
            start, end = match.span()
            language = match.group(1) or "text"
            code_content = match.group(2)

            # Add text before code block
            if start > last_end:
                before_text = text[last_end:start]
                if before_text.strip():
                    if self._contains_markdown(before_text):
                        parts.append(Markdown(before_text))
                    else:
                        parts.append(Text(before_text, style="white"))

            # Add syntax-highlighted code block
            try:
                # Normalize language name for better syntax highlighting
                normalized_language = self._normalize_language(language)

                syntax = Syntax(
                    code_content,
                    normalized_language,
                    theme="github-dark",  # Better theme for terminals
                    line_numbers=True,
                    word_wrap=True,
                    background_color="default",
                    indent_guides=True
                )
                parts.append(syntax)
            except Exception:
                # Fallback to plain code block if syntax highlighting fails
                code_text = Text(f"```{language}\n{code_content}\n```", style="cyan")
                parts.append(code_text)

            last_end = end

        # Add remaining text after last code block
        if last_end < len(text):
            remaining_text = text[last_end:]
            if remaining_text.strip():
                if self._contains_markdown(remaining_text):
                    parts.append(Markdown(remaining_text))
                else:
                    parts.append(Text(remaining_text, style="white"))

        # If no code blocks found, fall back to regular markdown
        if not parts:
            return Markdown(text) if self._contains_markdown(text) else Text(text, style="white")

        # Combine all parts
        from rich.console import Group
        return Group(*parts)

    def _normalize_language(self, language: str) -> str:
        """Normalize language names for better syntax highlighting"""
        if not language:
            return "text"

        # Common language aliases and normalizations
        language_map = {
            "js": "javascript",
            "ts": "typescript",
            "py": "python",
            "rb": "ruby",
            "sh": "bash",
            "shell": "bash",
            "zsh": "bash",
            "fish": "bash",
            "ps1": "powershell",
            "pwsh": "powershell",
            "cmd": "batch",
            "bat": "batch",
            "yml": "yaml",
            "json5": "json",
            "jsonc": "json",
            "md": "markdown",
            "rst": "restructuredtext",
            "tex": "latex",
            "dockerfile": "docker",
            "makefile": "make",
            "cmake": "cmake",
            "sql": "sql",
            "plsql": "sql",
            "mysql": "sql",
            "postgresql": "sql",
            "sqlite": "sql",
            "c++": "cpp",
            "cxx": "cpp",
            "cc": "cpp",
            "c#": "csharp",
            "cs": "csharp",
            "fs": "fsharp",
            "vb": "vb.net",
            "kt": "kotlin",
            "scala": "scala",
            "clj": "clojure",
            "cljs": "clojure",
            "hs": "haskell",
            "elm": "elm",
            "erl": "erlang",
            "ex": "elixir",
            "exs": "elixir",
            "nim": "nim",
            "zig": "zig",
            "v": "v",
            "dart": "dart",
            "swift": "swift",
            "objc": "objective-c",
            "m": "objective-c",
        }

        normalized = language.lower().strip()
        return language_map.get(normalized, normalized)

    def get_batch_input(self, prompt_number: int) -> Optional[str]:
        """Get input for batch processing with special prompt"""
        try:
            prompt_text = f"[bold magenta]Prompt {prompt_number}[/bold magenta] [dim](/done to finish, /cancel to abort, /list to view, /clear to reset)[/dim]"
            user_input = Prompt.ask(prompt_text, console=self.console)
            return user_input.strip() if user_input else None
        except (KeyboardInterrupt, EOFError):
            return None

    def display_batch_result(self, index: int, prompt: str, response: str):
        """Display a single batch result with formatting"""
        # Create a panel for each result
        result_content = Text()

        # Add prompt
        result_content.append("📝 Prompt:\n", style="bold cyan")
        result_content.append(f"{prompt}\n\n", style="white")

        # Add response with markdown rendering
        result_content.append("🤖 Response:\n", style="bold green")

        # Use enhanced markdown rendering for the response
        try:
            rendered_response = self._render_enhanced_markdown(response)
            panel_content = Group(result_content, rendered_response)
        except Exception:
            # Fallback to plain text
            result_content.append(response, style="white")
            panel_content = result_content

        panel = Panel(
            panel_content,
            title=f"Result {index}",
            border_style="blue",
            padding=(1, 2)
        )

        self.console.print(panel)
        self.console.print()

    def display_batch_progress(self):
        """Return a context manager for batch progress display"""
        return BatchProgressDisplay(self.console)


class BatchProgressDisplay:
    """Context manager for batch processing progress display"""

    def __init__(self, console: Console):
        self.console = console
        self.status_text = ""

    def __enter__(self):
        self.console.print("⏳ Starting batch processing...", style="yellow")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.console.print("✅ Batch processing completed!", style="green")
        else:
            self.console.print("❌ Batch processing failed!", style="red")
        self.console.print()

    def update_status(self, status: str):
        """Update the current status"""
        self.status_text = status
        self.console.print(f"  {status}", style="dim")

    def get_yes_no_input(self, prompt: str, default: bool = False) -> bool:
        """Get yes/no input from user with default value"""
        try:
            default_text = "Y/n" if default else "y/N"
            full_prompt = f"{prompt} [{default_text}]"

            response = Prompt.ask(full_prompt, console=self.console, default="")

            if not response:
                return default

            response = response.lower().strip()
            return response in ['y', 'yes', 'true', '1']

        except (KeyboardInterrupt, EOFError):
            return False


class StreamingDisplay:
    """Context manager for streaming text display with markdown post-processing"""

    def __init__(self, console: Console, ui_instance=None):
        self.console = console
        self.ui_instance = ui_instance
        self.buffer = ""
        self.enable_markdown_post_processing = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Post-process for markdown if enabled and we have content
        if (self.enable_markdown_post_processing and
            self.ui_instance and
            self.buffer.strip() and
            self._should_rerender_as_markdown()):

            # Clear the current line and re-render with markdown
            self.console.print("\r", end="")  # Return to start of line
            self.console.print(" " * 80, end="")  # Clear line
            self.console.print("\r", end="")  # Return to start again

            # Re-render with enhanced markdown
            try:
                rendered_content = self.ui_instance._render_enhanced_markdown(self.buffer)
                self.console.print(rendered_content)
            except Exception:
                # Fallback to what we already displayed
                pass
        else:
            # Ensure we end with a newline
            if self.buffer and not self.buffer.endswith('\n'):
                self.console.print()

        self.console.print()

    def write(self, text: str):
        """Write streaming text"""
        self.buffer += text
        self.console.print(text, end="", style="white")

    def write_chunk(self, chunk: str):
        """Write a chunk of streaming text"""
        self.write(chunk)

    def _should_rerender_as_markdown(self) -> bool:
        """Check if the complete buffer should be re-rendered as markdown"""
        if not self.ui_instance:
            return False

        # Only re-render if we have significant markdown content
        return (self.ui_instance._contains_code_blocks(self.buffer) or
                (self.ui_instance._contains_markdown(self.buffer) and
                 len(self.buffer.strip()) > 50))  # Only for substantial content


def create_loading_spinner(message: str = "Generating response...") -> Live:
    """Create a loading spinner"""
    spinner = Spinner("dots", text=message, style="cyan")
    return Live(spinner, console=Console(), refresh_per_second=10)
