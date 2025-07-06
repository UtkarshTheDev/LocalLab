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


def parse_inline_mode(message: str) -> tuple[str, Optional[GenerationMode], Optional[str]]:
    """
    Parse inline mode switches from user message.

    Args:
        message: User input message that may contain inline mode switches

    Returns:
        tuple: (cleaned_message, mode_override, error_message) where:
        - mode_override is None if no override or if invalid
        - error_message is None if no error, otherwise contains error description

    Examples:
        "Hello world --stream" -> ("Hello world", GenerationMode.STREAM, None)
        "Explain Python --chat" -> ("Explain Python", GenerationMode.CHAT, None)
        "Just a message" -> ("Just a message", None, None)
        "Test --invalid" -> ("Test --invalid", None, "Invalid mode: --invalid")
    """
    import re

    # Define valid mode patterns - match --mode at the end of the message
    # Allow optional whitespace before the mode switch
    valid_mode_patterns = {
        r'(^|\s+)--stream\s*$': GenerationMode.STREAM,
        r'(^|\s+)--simple\s*$': GenerationMode.SIMPLE,
        r'(^|\s+)--chat\s*$': GenerationMode.CHAT,
        r'(^|\s+)--batch\s*$': GenerationMode.BATCH,
    }

    # Check for valid mode switches first
    for pattern, mode in valid_mode_patterns.items():
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            # Remove the mode switch from the message
            cleaned_message = re.sub(pattern, '', message, flags=re.IGNORECASE).strip()
            return cleaned_message, mode, None

    # Check for invalid mode switches (--something that's not valid)
    invalid_mode_pattern = r'(^|\s+)(--\w+)\s*$'
    invalid_match = re.search(invalid_mode_pattern, message, re.IGNORECASE)
    if invalid_match:
        invalid_mode = invalid_match.group(2)  # group(2) because group(1) is the whitespace
        error_msg = f"Invalid mode: {invalid_mode}. Valid modes: --stream, --chat, --batch, --simple"
        return message.strip(), None, error_msg

    # No mode switch found
    return message.strip(), None, None


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
        self.max_history_length = 50  # Maximum number of messages to keep
        self.conversation_started = False
        self.connected = False
        self.connection: Optional[ServerConnection] = None
        self.server_info: Optional[Dict[str, Any]] = None
        self.model_info: Optional[Dict[str, Any]] = None
        self.ui = ChatUI()

        # Error handling and reconnection settings
        self.max_retries = 3
        self.retry_delay = 2.0  # seconds
        self.connection_timeout = 10.0  # seconds
        self.auto_reconnect = True
        self.graceful_shutdown = False

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
        try:
            if self.connection:
                await self.connection.disconnect()
                self.connection = None
            self.connected = False
            logger.info("Successfully disconnected from server")
        except Exception as e:
            logger.error(f"Error during disconnection: {str(e)}")
            # Force cleanup even if disconnect fails
            self.connection = None
            self.connected = False

    async def _check_connection(self) -> bool:
        """Check if connection is still alive"""
        if not self.connection or not self.connected:
            return False

        try:
            # Perform a quick health check
            health_ok = await self.connection.health_check()
            if not health_ok:
                logger.warning("Health check failed - connection may be lost")
                self.connected = False
                return False
            return True
        except Exception as e:
            logger.warning(f"Connection check failed: {str(e)}")
            self.connected = False
            return False

    async def _attempt_reconnection(self) -> bool:
        """Attempt to reconnect to the server with retries"""
        if not self.auto_reconnect or self.graceful_shutdown:
            return False

        self.ui.display_info("🔄 Connection lost. Attempting to reconnect...")

        for attempt in range(1, self.max_retries + 1):
            try:
                self.ui.display_info(f"   Attempt {attempt}/{self.max_retries}...")

                # Clean up old connection
                if self.connection:
                    try:
                        await self.connection.disconnect()
                    except:
                        pass
                    self.connection = None

                # Create new connection
                self.connection = ServerConnection(self.url, timeout=self.connection_timeout)
                success = await self.connection.connect()

                if success:
                    self.connected = True
                    self.ui.display_info("✅ Reconnection successful!")
                    return True
                else:
                    logger.warning(f"Reconnection attempt {attempt} failed")

            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt} failed: {str(e)}")

            if attempt < self.max_retries:
                self.ui.display_info(f"   Waiting {self.retry_delay} seconds before next attempt...")
                await asyncio.sleep(self.retry_delay)

        self.ui.display_error("❌ Failed to reconnect after all attempts")
        return False

    def _display_connection_info(self):
        """Display server and model information using the UI framework"""
        self.ui.display_welcome(
            server_url=self.url,
            mode=self.mode.value,
            model_info=self.model_info
        )

    async def start_chat(self):
        """Start the interactive chat session with comprehensive error handling"""
        try:
            if not await self.connect():
                return

            # Display help information
            self.ui.display_info("Type your message and press Enter to send.")
            self.ui.display_info("Type '/help' for commands, '/exit' or '/quit' to end the session.")
            self.ui.display_separator()

            # Start the chat loop
            await self._chat_loop()

        except KeyboardInterrupt:
            self.graceful_shutdown = True
            self.ui.display_info("\n🛑 Received interrupt signal. Shutting down gracefully...")
            await self._graceful_shutdown()
        except Exception as e:
            logger.error(f"Unexpected error in chat session: {str(e)}")
            self.ui.display_error(f"❌ Unexpected error: {str(e)}")
        finally:
            await self._cleanup()

    async def _chat_loop(self):
        """Main chat interaction loop with enhanced error handling"""
        consecutive_errors = 0
        max_consecutive_errors = 5

        while not self.graceful_shutdown:
            try:
                # Check connection periodically
                if not await self._check_connection():
                    if not await self._attempt_reconnection():
                        self.ui.display_error("❌ Unable to maintain connection. Exiting...")
                        break

                # Get user input
                user_input = self.ui.get_user_input()

                if user_input is None:
                    # User pressed Ctrl+C or EOF
                    break

                # Handle commands
                if user_input.startswith('/'):
                    try:
                        if await self._handle_command(user_input):
                            break  # Exit command was used
                        consecutive_errors = 0  # Reset error count on successful command
                        continue
                    except Exception as e:
                        logger.error(f"Error handling command '{user_input}': {str(e)}")
                        self.ui.display_error(f"❌ Command error: {str(e)}")
                        consecutive_errors += 1

                # Display user message
                self.ui.display_user_message(user_input)

                # Process the message
                try:
                    await self._process_message(user_input)
                    consecutive_errors = 0  # Reset error count on successful processing
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    self.ui.display_error(f"❌ Processing error: {str(e)}")
                    consecutive_errors += 1

                self.ui.display_separator()

            except KeyboardInterrupt:
                self.graceful_shutdown = True
                break
            except EOFError:
                # Handle EOF gracefully
                self.ui.display_info("\n📝 End of input detected. Exiting...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in chat loop: {str(e)}")
                self.ui.display_error(f"❌ Unexpected error: {str(e)}")
                consecutive_errors += 1

            # Check for too many consecutive errors
            if consecutive_errors >= max_consecutive_errors:
                self.ui.display_error(f"❌ Too many consecutive errors ({consecutive_errors}). Exiting for safety...")
                break

        if not self.graceful_shutdown:
            self.ui.display_goodbye()

    async def _handle_command(self, command: str) -> bool:
        """Handle chat commands. Returns True if should exit."""
        command = command.lower().strip()

        if command in ['/exit', '/quit', '/bye', '/goodbye']:
            self.graceful_shutdown = True
            self.ui.display_info("👋 Initiating graceful shutdown...")
            return True
        elif command == '/help':
            self.ui.display_help()
        elif command == '/clear':
            self.ui.clear_screen()
            self._display_connection_info()
        elif command == '/history':
            self._display_conversation_history()
        elif command == '/reset':
            self._reset_conversation()
        elif command == '/save':
            await self._save_conversation()
        elif command == '/load':
            await self._load_conversation()
        elif command == '/stats':
            self._display_conversation_stats()
        elif command == '/batch':
            await self._handle_batch_mode()
        else:
            self.ui.display_error(f"Unknown command: {command}")

        return False

    async def _process_message(self, message: str):
        """Process user message and get AI response with error handling and reconnection"""
        max_attempts = 2  # Allow one retry

        for attempt in range(max_attempts):
            try:
                # Check connection before processing
                if not await self._check_connection():
                    if attempt == 0 and await self._attempt_reconnection():
                        continue  # Retry with new connection
                    else:
                        self.ui.display_error("❌ Not connected to server and reconnection failed")
                        return

                # Parse inline mode switches
                cleaned_message, mode_override, parse_error = parse_inline_mode(message)

                # Handle parsing errors
                if parse_error:
                    self.ui.display_error(f"❌ {parse_error}")
                    return

                # Determine which mode to use (override or default)
                active_mode = mode_override if mode_override else self.mode

                # Display mode information if override is used
                if mode_override:
                    self.ui.display_info(f"🔄 Using {mode_override.value} mode for this message")

                # Show loading indicator
                self.ui.display_info("🤔 Thinking...")

                # Choose generation method based on active mode
                if active_mode == GenerationMode.STREAM:
                    await self._generate_stream_with_recovery(cleaned_message)
                elif active_mode == GenerationMode.CHAT:
                    response = await self._chat_completion_with_recovery(cleaned_message)
                    if response:
                        response_text = self._extract_response_text(response)
                        if response_text:
                            model_name = self.model_info.get('model_id', 'AI') if self.model_info else 'AI'
                            self.ui.display_ai_response(response_text, model_name)
                        else:
                            self.ui.display_error("Received empty response from server")
                    else:
                        self.ui.display_error("Failed to get response from server")
                elif active_mode == GenerationMode.BATCH:
                    # For batch mode, treat single messages as single-item batches
                    await self._process_batch_with_recovery([cleaned_message])
                else:
                    # Simple generation mode
                    response = await self._generate_text_with_recovery(cleaned_message)
                    if response:
                        response_text = self._extract_response_text(response)
                        if response_text:
                            model_name = self.model_info.get('model_id', 'AI') if self.model_info else 'AI'
                            self.ui.display_ai_response(response_text, model_name)
                        else:
                            self.ui.display_error("Received empty response from server")
                    else:
                        self.ui.display_error("Failed to get response from server")

                # If we reach here, processing was successful
                return

            except ConnectionError as e:
                logger.warning(f"Connection error on attempt {attempt + 1}: {str(e)}")
                if attempt == 0:
                    # Try to reconnect on first failure
                    if await self._attempt_reconnection():
                        continue
                self.ui.display_error(f"❌ Connection error: {str(e)}")
                return

            except Exception as e:
                logger.error(f"Error processing message on attempt {attempt + 1}: {str(e)}")
                if attempt == max_attempts - 1:  # Last attempt
                    self.ui.display_error(f"❌ Error processing message: {str(e)}")
                    return

    async def _generate_stream_with_recovery(self, prompt: str):
        """Generate streaming text with connection recovery"""
        try:
            await self._generate_stream(prompt)
        except Exception as e:
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                raise ConnectionError(f"Streaming connection failed: {str(e)}")
            raise

    async def _chat_completion_with_recovery(self, message: str):
        """Chat completion with connection recovery"""
        try:
            return await self._chat_completion(message)
        except Exception as e:
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                raise ConnectionError(f"Chat completion connection failed: {str(e)}")
            raise

    async def _generate_text_with_recovery(self, prompt: str):
        """Generate text with connection recovery"""
        try:
            return await self._generate_text(prompt)
        except Exception as e:
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                raise ConnectionError(f"Text generation connection failed: {str(e)}")
            raise

    async def _process_batch_with_recovery(self, prompts: list):
        """Process batch with connection recovery"""
        try:
            await self._process_batch(prompts)
        except Exception as e:
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                raise ConnectionError(f"Batch processing connection failed: {str(e)}")
            raise

    async def _graceful_shutdown(self):
        """Perform graceful shutdown operations"""
        try:
            self.ui.display_info("🔄 Performing graceful shutdown...")

            # Save conversation if it exists and user wants to
            if self.session_history:
                try:
                    save_choice = self.ui.get_yes_no_input("💾 Save current conversation before exiting?")
                    if save_choice:
                        await self._save_conversation()
                except Exception as e:
                    logger.warning(f"Failed to save conversation during shutdown: {str(e)}")

            # Disconnect from server
            await self.disconnect()

            self.ui.display_info("✅ Graceful shutdown completed")

        except Exception as e:
            logger.error(f"Error during graceful shutdown: {str(e)}")
            self.ui.display_error(f"❌ Shutdown error: {str(e)}")

    async def _cleanup(self):
        """Final cleanup operations"""
        try:
            # Ensure disconnection
            if self.connected or self.connection:
                await self.disconnect()

            # Clear sensitive data
            self.session_history.clear()
            self.server_info = None
            self.model_info = None

            logger.info("Cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
        finally:
            # Always display goodbye message
            if not self.graceful_shutdown:
                self.ui.display_goodbye()

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
                    self.conversation_started = True
                    self._manage_history_length()

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
                    self.conversation_started = True
                    self._manage_history_length()

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
                    self.conversation_started = True
                    self._manage_history_length()

        except Exception as e:
            logger.error(f"Streaming chat completion failed: {str(e)}")
            self.ui.display_error(f"Streaming chat failed: {str(e)}")

    def _display_conversation_history(self):
        """Display the current conversation history"""
        if not self.session_history:
            self.ui.display_info("No conversation history yet.")
            return

        self.ui.display_info(f"Conversation History ({len(self.session_history)} messages):")
        self.ui.display_separator()

        for i, message in enumerate(self.session_history, 1):
            role = message.get("role", "unknown")
            content = message.get("content", "")

            # Truncate long messages for history display
            if len(content) > 100:
                content = content[:97] + "..."

            if role == "user":
                self.ui.display_info(f"{i}. You: {content}")
            elif role == "assistant":
                model_name = self.model_info.get('model_id', 'AI') if self.model_info else 'AI'
                self.ui.display_info(f"{i}. {model_name}: {content}")
            else:
                self.ui.display_info(f"{i}. {role}: {content}")

        self.ui.display_separator()

    def _reset_conversation(self):
        """Reset the conversation history"""
        old_count = len(self.session_history)
        self.session_history.clear()
        self.conversation_started = False
        self.ui.display_info(f"Conversation reset. Cleared {old_count} messages.")

    async def _save_conversation(self):
        """Save conversation history to a file"""
        if not self.session_history:
            self.ui.display_info("No conversation to save.")
            return

        try:
            import json
            from datetime import datetime
            import os

            # Create conversations directory if it doesn't exist
            conversations_dir = "conversations"
            os.makedirs(conversations_dir, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_{timestamp}.json"
            filepath = os.path.join(conversations_dir, filename)

            # Prepare conversation data
            conversation_data = {
                "timestamp": datetime.now().isoformat(),
                "mode": self.mode.value,
                "model_info": self.model_info,
                "server_url": self.url,
                "messages": self.session_history,
                "stats": {
                    "total_messages": len(self.session_history),
                    "user_messages": len([m for m in self.session_history if m.get("role") == "user"]),
                    "assistant_messages": len([m for m in self.session_history if m.get("role") == "assistant"])
                }
            }

            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)

            self.ui.display_info(f"Conversation saved to: {filepath}")

        except Exception as e:
            logger.error(f"Failed to save conversation: {str(e)}")
            self.ui.display_error(f"Failed to save conversation: {str(e)}")

    async def _load_conversation(self):
        """Load conversation history from a file"""
        try:
            import json
            import os
            from pathlib import Path

            conversations_dir = "conversations"
            if not os.path.exists(conversations_dir):
                self.ui.display_info("No conversations directory found.")
                return

            # List available conversation files
            conversation_files = list(Path(conversations_dir).glob("conversation_*.json"))
            if not conversation_files:
                self.ui.display_info("No saved conversations found.")
                return

            # Display available conversations
            self.ui.display_info("Available conversations:")
            for i, file_path in enumerate(conversation_files, 1):
                # Extract timestamp from filename
                filename = file_path.stem
                timestamp_str = filename.replace("conversation_", "")
                try:
                    from datetime import datetime
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    self.ui.display_info(f"  {i}. {formatted_time} ({file_path.name})")
                except:
                    self.ui.display_info(f"  {i}. {file_path.name}")

            # For now, just load the most recent one
            # In a full implementation, you'd prompt the user to choose
            latest_file = max(conversation_files, key=lambda p: p.stat().st_mtime)

            with open(latest_file, 'r', encoding='utf-8') as f:
                conversation_data = json.load(f)

            # Load the conversation history
            old_count = len(self.session_history)
            self.session_history = conversation_data.get("messages", [])
            self.conversation_started = len(self.session_history) > 0

            self.ui.display_info(f"Loaded conversation from {latest_file.name}")
            self.ui.display_info(f"Replaced {old_count} messages with {len(self.session_history)} messages")

        except Exception as e:
            logger.error(f"Failed to load conversation: {str(e)}")
            self.ui.display_error(f"Failed to load conversation: {str(e)}")

    def _display_conversation_stats(self):
        """Display conversation statistics"""
        if not self.session_history:
            self.ui.display_info("No conversation data available.")
            return

        user_messages = [m for m in self.session_history if m.get("role") == "user"]
        assistant_messages = [m for m in self.session_history if m.get("role") == "assistant"]

        total_user_chars = sum(len(m.get("content", "")) for m in user_messages)
        total_assistant_chars = sum(len(m.get("content", "")) for m in assistant_messages)

        self.ui.display_info("📊 Conversation Statistics:")
        self.ui.display_info(f"  Total messages: {len(self.session_history)}")
        self.ui.display_info(f"  User messages: {len(user_messages)}")
        self.ui.display_info(f"  Assistant messages: {len(assistant_messages)}")
        self.ui.display_info(f"  User characters: {total_user_chars:,}")
        self.ui.display_info(f"  Assistant characters: {total_assistant_chars:,}")
        self.ui.display_info(f"  Average user message length: {total_user_chars // max(len(user_messages), 1):,}")
        self.ui.display_info(f"  Average assistant message length: {total_assistant_chars // max(len(assistant_messages), 1):,}")

        if self.model_info:
            model_name = self.model_info.get('model_id', 'Unknown')
            self.ui.display_info(f"  Model: {model_name}")

        self.ui.display_info(f"  Mode: {self.mode.value}")
        self.ui.display_info(f"  Max history length: {self.max_history_length}")

    def _manage_history_length(self):
        """Manage conversation history length to prevent context overflow"""
        if len(self.session_history) > self.max_history_length:
            # Keep the most recent messages, but preserve conversation flow
            # Remove pairs of messages (user + assistant) to maintain context
            messages_to_remove = len(self.session_history) - self.max_history_length

            # Ensure we remove an even number to maintain user/assistant pairs
            if messages_to_remove % 2 == 1:
                messages_to_remove += 1

            if messages_to_remove > 0:
                removed_messages = self.session_history[:messages_to_remove]
                self.session_history = self.session_history[messages_to_remove:]

                logger.info(f"Trimmed {len(removed_messages)} old messages from conversation history")
                self.ui.display_info(f"📝 Trimmed {len(removed_messages)} old messages to manage context length")

    async def _handle_batch_mode(self):
        """Handle interactive batch processing mode"""
        self.ui.display_info("🔄 Entering batch processing mode")
        self.ui.display_info("Enter prompts one by one. Type '/done' when finished, '/cancel' to abort.")
        self.ui.display_separator()

        prompts = []
        prompt_count = 1

        while True:
            try:
                prompt = self.ui.get_batch_input(prompt_count)
                if not prompt:
                    continue

                if prompt.lower() == '/done':
                    if prompts:
                        break
                    else:
                        self.ui.display_info("No prompts entered. Add at least one prompt or type '/cancel' to abort.")
                        continue
                elif prompt.lower() == '/cancel':
                    self.ui.display_info("Batch processing cancelled.")
                    return
                elif prompt.lower() == '/clear':
                    prompts.clear()
                    prompt_count = 1
                    self.ui.display_info("Batch cleared. Start adding prompts again.")
                    continue
                elif prompt.lower() == '/list':
                    self._display_batch_prompts(prompts)
                    continue

                prompts.append(prompt)
                self.ui.display_info(f"✅ Added prompt {prompt_count}: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
                prompt_count += 1

            except KeyboardInterrupt:
                self.ui.display_info("\nBatch processing cancelled.")
                return

        if prompts:
            await self._process_batch(prompts)

    def _display_batch_prompts(self, prompts: list):
        """Display current batch prompts"""
        if not prompts:
            self.ui.display_info("No prompts in batch yet.")
            return

        self.ui.display_info(f"📋 Current batch ({len(prompts)} prompts):")
        for i, prompt in enumerate(prompts, 1):
            truncated = prompt[:80] + "..." if len(prompt) > 80 else prompt
            self.ui.display_info(f"  {i}. {truncated}")

    async def _process_batch(self, prompts: list):
        """Process a batch of prompts"""
        if not self.connection:
            self.ui.display_error("Not connected to server")
            return

        self.ui.display_info(f"🚀 Processing batch of {len(prompts)} prompts...")
        self.ui.display_separator()

        # Prepare generation parameters
        params = {
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }

        try:
            # Show progress indicator
            with self.ui.display_batch_progress() as progress:
                progress.update_status("Sending batch request...")

                # Send batch request
                response = await self.connection.batch_generate(prompts, **params)

                if not response:
                    self.ui.display_error("Batch processing failed - no response from server")
                    return

                responses = response.get("responses", [])
                if len(responses) != len(prompts):
                    self.ui.display_error(f"Response count mismatch: expected {len(prompts)}, got {len(responses)}")
                    return

                progress.update_status("Processing responses...")

                # Display results
                self.ui.display_info("📊 Batch Results:")
                self.ui.display_separator()

                for i, (prompt, response) in enumerate(zip(prompts, responses), 1):
                    progress.update_status(f"Displaying result {i}/{len(prompts)}")
                    self.ui.display_batch_result(i, prompt, response)

                progress.update_status("Batch processing complete!")

            # Display batch statistics
            self._display_batch_stats(prompts, responses)

        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            self.ui.display_error(f"Batch processing failed: {str(e)}")

    def _display_batch_stats(self, prompts: list, responses: list):
        """Display batch processing statistics"""
        total_prompt_chars = sum(len(p) for p in prompts)
        total_response_chars = sum(len(r) for r in responses)
        avg_prompt_length = total_prompt_chars // len(prompts)
        avg_response_length = total_response_chars // len(responses)

        self.ui.display_separator()
        self.ui.display_info("📈 Batch Statistics:")
        self.ui.display_info(f"  Total prompts: {len(prompts)}")
        self.ui.display_info(f"  Total responses: {len(responses)}")
        self.ui.display_info(f"  Average prompt length: {avg_prompt_length:,} characters")
        self.ui.display_info(f"  Average response length: {avg_response_length:,} characters")
        self.ui.display_info(f"  Total characters processed: {total_prompt_chars + total_response_chars:,}")

        if self.model_info:
            model_name = self.model_info.get('model_id', 'Unknown')
            self.ui.display_info(f"  Model used: {model_name}")
        

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
    
    # Start the chat interface with comprehensive error handling
    try:
        asyncio.run(interface.start_chat())
    except KeyboardInterrupt:
        click.echo("\n\n🛑 Interrupted by user")
        click.echo("👋 Goodbye!")
        sys.exit(0)
    except ConnectionError as e:
        click.echo(f"\n❌ Connection Error: {str(e)}")
        click.echo("💡 Make sure the LocalLab server is running and accessible.")
        sys.exit(1)
    except asyncio.TimeoutError:
        click.echo("\n❌ Timeout Error: Connection or operation timed out")
        click.echo("💡 Try increasing timeout or check your network connection.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error in chat command: {str(e)}")
        click.echo(f"\n❌ Unexpected Error: {str(e)}")
        click.echo("💡 Please check the logs for more details.")
        sys.exit(1)
