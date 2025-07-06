"""
Terminal UI utilities for LocalLab CLI chat interface
"""

import sys
import os
from typing import Optional, List, Dict, Any
from rich.console import Console
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
        """Display welcome message and connection info"""
        # Create welcome panel
        welcome_text = Text()
        welcome_text.append("🎉 Welcome to LocalLab Chat Interface!\n", style="bold green")
        welcome_text.append(f"📡 Connected to: {server_url}\n", style="cyan")
        welcome_text.append(f"⚙️  Generation mode: {mode}\n", style="yellow")
        
        if model_info and model_info.get('model_id'):
            welcome_text.append(f"🤖 Active model: {model_info['model_id']}\n", style="magenta")
        else:
            welcome_text.append("⚠️  No model currently loaded\n", style="red")
            
        welcome_text.append("\n💬 Start typing your messages below!", style="bold blue")
        
        panel = Panel(
            welcome_text,
            title="LocalLab Chat",
            border_style="green",
            padding=(1, 2)
        )
        
        self.console.print(panel)
        self.console.print()
        
    def display_help(self):
        """Display help information"""
        help_text = Text()
        help_text.append("Available commands:\n", style="bold")
        help_text.append("  /help    - Show this help message\n", style="cyan")
        help_text.append("  /clear   - Clear the screen\n", style="cyan")
        help_text.append("  /exit    - Exit the chat\n", style="cyan")
        help_text.append("  /quit    - Exit the chat\n", style="cyan")
        help_text.append("\nOr just type your message and press Enter!", style="green")
        
        panel = Panel(help_text, title="Help", border_style="blue")
        self.console.print(panel)
        
    def get_user_input(self) -> Optional[str]:
        """Get user input with a nice prompt"""
        try:
            # Use rich prompt for better formatting
            prompt_text = f"[bold cyan]You[/bold cyan] [dim]({self.message_count + 1})[/dim]"
            user_input = Prompt.ask(prompt_text, console=self.console)
            
            if user_input.strip():
                self.message_count += 1
                return user_input.strip()
            return None
            
        except (KeyboardInterrupt, EOFError):
            return None
            
    def display_user_message(self, message: str):
        """Display user message"""
        user_text = Text()
        user_text.append("You: ", style="bold cyan")
        user_text.append(message, style="white")
        
        self.console.print(user_text)
        self.console.print()
        
    def display_ai_response(self, response: str, model_name: Optional[str] = None):
        """Display AI response with markdown formatting"""
        # Create header
        ai_label = model_name or "AI"
        header = Text()
        header.append(f"{ai_label}: ", style="bold green")
        
        self.console.print(header, end="")
        
        # Try to render as markdown if it contains markdown syntax
        if self._contains_markdown(response):
            try:
                markdown = Markdown(response)
                self.console.print(markdown)
            except Exception:
                # Fallback to plain text if markdown parsing fails
                self.console.print(response, style="white")
        else:
            self.console.print(response, style="white")
            
        self.console.print()
        
    def display_streaming_response(self, model_name: Optional[str] = None):
        """Start displaying a streaming response"""
        ai_label = model_name or "AI"
        header = Text()
        header.append(f"{ai_label}: ", style="bold green")
        self.console.print(header, end="")
        
        # Return a context manager for streaming
        return StreamingDisplay(self.console)
        
    def display_error(self, error_message: str):
        """Display error message"""
        error_text = Text()
        error_text.append("❌ Error: ", style="bold red")
        error_text.append(error_message, style="red")
        
        panel = Panel(error_text, border_style="red")
        self.console.print(panel)
        
    def display_info(self, info_message: str):
        """Display info message"""
        info_text = Text()
        info_text.append("ℹ️  ", style="blue")
        info_text.append(info_message, style="blue")
        
        self.console.print(info_text)
        
    def display_separator(self):
        """Display a visual separator"""
        self.console.print(Rule(style="dim"))
        
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def display_goodbye(self):
        """Display goodbye message"""
        goodbye_text = Text()
        goodbye_text.append("👋 Thanks for using LocalLab Chat!", style="bold green")
        goodbye_text.append("\n   Have a great day!", style="green")
        
        panel = Panel(
            goodbye_text,
            title="Goodbye",
            border_style="green",
            padding=(1, 2)
        )
        
        self.console.print(panel)
        
    def _contains_markdown(self, text: str) -> bool:
        """Check if text contains markdown syntax"""
        markdown_patterns = [
            r'```[\s\S]*?```',  # Code blocks
            r'`[^`]+`',         # Inline code
            r'\*\*[^*]+\*\*',   # Bold
            r'\*[^*]+\*',       # Italic
            r'#{1,6}\s',        # Headers
            r'^\s*[-*+]\s',     # Lists
            r'^\s*\d+\.\s',     # Numbered lists
        ]
        
        for pattern in markdown_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return True
        return False


class StreamingDisplay:
    """Context manager for streaming text display"""
    
    def __init__(self, console: Console):
        self.console = console
        self.buffer = ""
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
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


def create_loading_spinner(message: str = "Generating response...") -> Live:
    """Create a loading spinner"""
    spinner = Spinner("dots", text=message, style="cyan")
    return Live(spinner, console=Console(), refresh_per_second=10)
