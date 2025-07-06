"""
CLI chat interface for LocalLab
"""

import click
import asyncio
import sys
from typing import Optional, Dict, Any
from enum import Enum

from ..logger import get_logger
from .connection import ServerConnection, detect_local_server, test_connection
from .ui import ChatUI

logger = get_logger("locallab.cli.chat")


class GenerationMode(str, Enum):
    """Generation modes for the chat interface"""
    STREAM = "stream"
    SIMPLE = "simple"
    CHAT = "chat"
    BATCH = "batch"


class ChatInterface:
    """Main chat interface class"""

    def __init__(self, url: Optional[str] = None, mode: GenerationMode = GenerationMode.STREAM,
                 max_tokens: int = 8192, temperature: float = 0.7, top_p: float = 0.9):
        self.url = url
        self.mode = mode
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.session_history = []
        self.connected = False
        self.connection: Optional[ServerConnection] = None
        self.server_info: Optional[Dict[str, Any]] = None
        self.model_info: Optional[Dict[str, Any]] = None
        self.ui = ChatUI()

    async def connect(self) -> bool:
        """Connect to the LocalLab server"""
        try:
            # If no URL provided, try to detect local server
            if not self.url:
                click.echo("🔍 Detecting local LocalLab server...")
                detected_url = await detect_local_server()
                if detected_url:
                    self.url = detected_url
                    click.echo(f"✅ Found server at {self.url}")
                else:
                    click.echo("❌ No local server detected. Please specify a URL with --url")
                    return False

            # Test connection
            click.echo(f"🔗 Connecting to {self.url}...")
            success, info = await test_connection(self.url)

            if not success:
                click.echo(f"❌ Failed to connect to {self.url}")
                click.echo("   Make sure the LocalLab server is running and accessible.")
                return False

            # Store connection info
            self.server_info = info.get("server_info")
            self.model_info = info.get("model_info")

            # Create persistent connection
            self.connection = ServerConnection(self.url)
            await self.connection.connect()
            self.connected = True

            # Display connection success
            self._display_connection_info()
            return True

        except Exception as e:
            click.echo(f"❌ Connection error: {str(e)}")
            return False

    async def disconnect(self):
        """Disconnect from the server"""
        if self.connection:
            await self.connection.disconnect()
            self.connection = None
        self.connected = False

    def _display_connection_info(self):
        """Display server and model information using the UI framework"""
        self.ui.display_welcome(
            server_url=self.url,
            mode=self.mode.value,
            model_info=self.model_info
        )

    async def start_chat(self):
        """Start the interactive chat session"""
        if not await self.connect():
            return

        try:
            # Display help information
            self.ui.display_info("Type your message and press Enter to send.")
            self.ui.display_info("Type '/help' for commands, '/exit' or '/quit' to end the session.")
            self.ui.display_separator()

            # Start the chat loop
            await self._chat_loop()

        except KeyboardInterrupt:
            self.ui.display_goodbye()
        finally:
            await self.disconnect()

    async def _chat_loop(self):
        """Main chat interaction loop"""
        while True:
            try:
                # Get user input
                user_input = self.ui.get_user_input()

                if user_input is None:
                    # User pressed Ctrl+C or EOF
                    break

                # Handle commands
                if user_input.startswith('/'):
                    if await self._handle_command(user_input):
                        break  # Exit command was used
                    continue

                # Display user message
                self.ui.display_user_message(user_input)

                # Process the message
                await self._process_message(user_input)
                self.ui.display_separator()

            except KeyboardInterrupt:
                break

        self.ui.display_goodbye()

    async def _handle_command(self, command: str) -> bool:
        """Handle chat commands. Returns True if should exit."""
        command = command.lower().strip()

        if command in ['/exit', '/quit']:
            return True
        elif command == '/help':
            self.ui.display_help()
        elif command == '/clear':
            self.ui.clear_screen()
            self._display_connection_info()
        else:
            self.ui.display_error(f"Unknown command: {command}")

        return False

    async def _process_message(self, message: str):
        """Process user message and get AI response"""
        try:
            if not self.connection:
                self.ui.display_error("Not connected to server")
                return

            # Show loading indicator
            self.ui.display_info("🤔 Thinking...")

            # Choose generation method based on mode
            if self.mode == GenerationMode.STREAM:
                await self._generate_stream(message)
            elif self.mode == GenerationMode.CHAT:
                response = await self._chat_completion(message)
                if response:
                    response_text = self._extract_response_text(response)
                    if response_text:
                        model_name = self.model_info.get('model_id', 'AI') if self.model_info else 'AI'
                        self.ui.display_ai_response(response_text, model_name)
                    else:
                        self.ui.display_error("Received empty response from server")
                else:
                    self.ui.display_error("Failed to get response from server")
            else:
                # Simple generation mode
                response = await self._generate_text(message)
                if response:
                    response_text = self._extract_response_text(response)
                    if response_text:
                        model_name = self.model_info.get('model_id', 'AI') if self.model_info else 'AI'
                        self.ui.display_ai_response(response_text, model_name)
                    else:
                        self.ui.display_error("Received empty response from server")
                else:
                    self.ui.display_error("Failed to get response from server")

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            self.ui.display_error(f"Error processing message: {str(e)}")

    async def _generate_text(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Generate text using the /generate endpoint"""
        try:
            # Prepare generation parameters
            params = {
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
            }

            return await self.connection.generate_text(prompt, **params)

        except Exception as e:
            logger.error(f"Text generation failed: {str(e)}")
            return None

    async def _generate_stream(self, prompt: str):
        """Generate text with streaming using the /generate endpoint"""
        try:
            if not self.connection:
                self.ui.display_error("Not connected to server")
                return

            # Prepare generation parameters
            params = {
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
            }

            model_name = self.model_info.get('model_id', 'AI') if self.model_info else 'AI'

            # Start streaming display
            with self.ui.display_streaming_response(model_name) as stream_display:
                full_response = ""

                async for chunk in self.connection.generate_stream(prompt, **params):
                    try:
                        # Parse the streaming chunk
                        chunk_text = self._parse_stream_chunk(chunk)
                        if chunk_text:
                            full_response += chunk_text
                            stream_display.write_chunk(chunk_text)
                    except Exception as e:
                        logger.debug(f"Error parsing stream chunk: {str(e)}")
                        continue

                # Add to session history if we got a response
                if full_response.strip():
                    self.session_history.append({"role": "user", "content": prompt})
                    self.session_history.append({"role": "assistant", "content": full_response})

        except Exception as e:
            logger.error(f"Streaming generation failed: {str(e)}")
            self.ui.display_error(f"Streaming failed: {str(e)}")

    def _parse_stream_chunk(self, chunk: str) -> Optional[str]:
        """Parse a streaming chunk and extract text content"""
        try:
            if not chunk or chunk.strip() == "":
                return None

            # Try to parse as JSON
            import json
            try:
                data = json.loads(chunk)

                # Handle different streaming formats
                if "choices" in data and data["choices"]:
                    choice = data["choices"][0]
                    if "delta" in choice and "content" in choice["delta"]:
                        return choice["delta"]["content"]
                    elif "text" in choice:
                        return choice["text"]
                elif "token" in data:
                    return data["token"]
                elif "text" in data:
                    return data["text"]
                elif "content" in data:
                    return data["content"]

            except json.JSONDecodeError:
                # If not JSON, treat as plain text
                return chunk

            return None

        except Exception as e:
            logger.debug(f"Error parsing stream chunk: {str(e)}")
            return None

    async def _chat_completion(self, message: str) -> Optional[Dict[str, Any]]:
        """Chat completion using the /chat endpoint"""
        try:
            # Add message to session history
            self.session_history.append({"role": "user", "content": message})

            # Prepare generation parameters
            params = {
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
            }

            response = await self.connection.chat_completion(self.session_history, **params)

            # Add assistant response to history
            if response:
                assistant_message = self._extract_response_text(response)
                if assistant_message:
                    self.session_history.append({"role": "assistant", "content": assistant_message})

            return response

        except Exception as e:
            logger.error(f"Chat completion failed: {str(e)}")
            return None

    def _extract_response_text(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract response text from API response"""
        try:
            # Handle different response formats
            if "choices" in response and response["choices"]:
                choice = response["choices"][0]
                if "message" in choice:
                    return choice["message"].get("content", "")
                elif "text" in choice:
                    return choice["text"]
            elif "response" in response:
                return response["response"]
            elif "text" in response:
                return response["text"]
            elif "content" in response:
                return response["content"]

            return None

        except Exception as e:
            logger.error(f"Failed to extract response text: {str(e)}")
            return None

    async def _chat_completion_stream(self, message: str):
        """Chat completion with streaming using the /chat endpoint"""
        try:
            if not self.connection:
                self.ui.display_error("Not connected to server")
                return

            # Add message to session history
            self.session_history.append({"role": "user", "content": message})

            # Prepare generation parameters
            params = {
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
            }

            model_name = self.model_info.get('model_id', 'AI') if self.model_info else 'AI'

            # Start streaming display
            with self.ui.display_streaming_response(model_name) as stream_display:
                full_response = ""

                async for chunk in self.connection.chat_completion_stream(self.session_history, **params):
                    try:
                        # Parse the streaming chunk
                        chunk_text = self._parse_stream_chunk(chunk)
                        if chunk_text:
                            full_response += chunk_text
                            stream_display.write_chunk(chunk_text)
                    except Exception as e:
                        logger.debug(f"Error parsing stream chunk: {str(e)}")
                        continue

                # Add assistant response to history
                if full_response.strip():
                    self.session_history.append({"role": "assistant", "content": full_response})

        except Exception as e:
            logger.error(f"Streaming chat completion failed: {str(e)}")
            self.ui.display_error(f"Streaming chat failed: {str(e)}")
        

def validate_url(ctx, param, value):
    """Validate URL parameter"""
    if value is None:
        return None
        
    # Basic URL validation
    if not value.startswith(('http://', 'https://')):
        value = f"http://{value}"
        
    return value


@click.command()
@click.option(
    '--url', '-u',
    help='LocalLab server URL (default: http://localhost:8000)',
    callback=validate_url,
    metavar='URL'
)
@click.option(
    '--generate', '-g',
    type=click.Choice(['stream', 'simple', 'chat', 'batch']),
    default='stream',
    help='Generation mode (default: stream)'
)
@click.option(
    '--max-tokens', '-m',
    type=int,
    default=8192,
    help='Maximum tokens to generate (default: 8192)'
)
@click.option(
    '--temperature', '-t',
    type=float,
    default=0.7,
    help='Temperature for generation (default: 0.7)'
)
@click.option(
    '--top-p', '-p',
    type=float,
    default=0.9,
    help='Top-p for nucleus sampling (default: 0.9)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
def chat(url, generate, max_tokens, temperature, top_p, verbose):
    """
    Connect to and interact with a LocalLab server through a terminal chat interface.
    
    Examples:
    
    \b
    # Connect to local server
    locallab chat
    
    \b
    # Connect to remote server
    locallab chat --url https://abc123.ngrok.io
    
    \b
    # Use simple generation mode
    locallab chat --generate simple
    
    \b
    # Use chat mode with context retention
    locallab chat --generate chat
    """
    if verbose:
        logger.setLevel("DEBUG")
        
    # Create chat interface
    mode = GenerationMode(generate)
    interface = ChatInterface(
        url=url,
        mode=mode,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p
    )
    
    # Display connection info
    click.echo(f"\n🚀 LocalLab Chat Interface")
    click.echo(f"📡 Server: {interface.url}")
    click.echo(f"⚙️  Mode: {mode.value}")
    click.echo(f"🎛️  Max Tokens: {max_tokens}")
    click.echo(f"🌡️  Temperature: {temperature}")
    click.echo(f"🎯 Top-p: {top_p}")
    click.echo()
    
    # Start the chat interface
    try:
        asyncio.run(interface.start_chat())
    except KeyboardInterrupt:
        click.echo("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}")
        sys.exit(1)
