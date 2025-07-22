"""
CLI chat interface for LocalLab
"""

import click
import asyncio
import sys
from typing import Optional, Dict, Any
from enum import Enum
from rich.text import Text

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
                detected_url = await detect_local_server()
                if detected_url:
                    self.url = detected_url
                else:
                    click.echo("❌ No local server detected. Please specify a URL with --url")
                    return False

            # Test connection silently
            success, info = await test_connection(self.url)

            if not success:
                click.echo(f"❌ Failed to connect to {self.url}")
                click.echo("   Make sure the LocalLab server is running and accessible.")
                return False

            # Store connection info
            self.server_info = info.get("server_info")
            self.model_info = info.get("model_info")

            # Store connection info (debug logging removed for cleaner interface)

            # Create persistent connection
            self.connection = ServerConnection(self.url)
            self.connection.silent_mode = True  # Enable silent mode
            await self.connection.connect()
            self.connected = True

            # Get fresh model info from the persistent connection
            fresh_model_info = await self.connection.get_model_info()
            if fresh_model_info:
                self.model_info = fresh_model_info

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
            logger.debug("Successfully disconnected from server")
        except Exception as e:
            logger.error(f"Error during disconnection: {str(e)}")
            # Force cleanup even if disconnect fails
            self.connection = None
            self.connected = False

    async def _check_connection(self) -> bool:
        """Check if connection is still alive using enhanced monitoring"""
        if not self.connection or not self.connected:
            return False

        try:
            # Use connection quality monitoring instead of simple health check
            status = self.connection.get_connection_status()

            # Connection is considered good if:
            # 1. Client exists and is connected
            # 2. Connection quality is above threshold (30%)
            # 3. Not currently reconnecting
            if (status['connected'] and
                status['quality'] > 30 and
                not status['reconnecting']):
                return True

            # If connection quality is degraded but still connected,
            # let the background monitor handle reconnection
            if status['connected'] and status['quality'] <= 30:
                logger.debug(f"Connection quality degraded: {status['quality']}% - background monitor will handle")
                return True  # Don't trigger manual reconnection

            # Connection is truly lost
            logger.debug("Connection check failed - connection lost")
            self.connected = False
            return False

        except Exception as e:
            logger.debug(f"Connection check failed: {str(e)}")
            self.connected = False
            return False

    async def _attempt_reconnection(self) -> bool:
        """Attempt to reconnect to the server with enhanced silent recovery"""
        if not self.auto_reconnect or self.graceful_shutdown:
            return False

        # Check if connection has its own silent reconnection in progress
        if self.connection and hasattr(self.connection, '_reconnecting') and self.connection._reconnecting:
            logger.debug("Silent reconnection already in progress, waiting...")
            # Wait for silent reconnection to complete
            for _ in range(10):  # Wait up to 10 seconds
                await asyncio.sleep(1)
                if not self.connection._reconnecting:
                    status = self.connection.get_connection_status()
                    if status['connected'] and status['quality'] > 50:
                        self.connected = True
                        logger.debug("Silent reconnection completed successfully")
                        return True

        # If silent reconnection failed or not available, try manual reconnection
        # But make it less verbose - only show message for first attempt
        logger.debug("Attempting manual reconnection...")
        user_notified = False

        for attempt in range(1, min(self.max_retries, 3) + 1):  # Limit to 3 attempts
            try:
                # Only show user message on first attempt
                if not user_notified:
                    self.ui.display_info("🔄 Reconnecting...")
                    user_notified = True

                logger.debug(f"Reconnection attempt {attempt}/3...")

                # Clean up old connection
                if self.connection:
                    try:
                        await self.connection.disconnect()
                    except:
                        pass
                    self.connection = None

                # Create new connection with silent mode enabled
                self.connection = ServerConnection(self.url, timeout=self.connection_timeout)
                self.connection.silent_mode = True  # Enable silent mode
                success = await self.connection.connect()

                if success:
                    self.connected = True
                    logger.debug("Manual reconnection successful")
                    return True
                else:
                    logger.debug(f"Reconnection attempt {attempt} failed")

            except Exception as e:
                logger.debug(f"Reconnection attempt {attempt} failed: {str(e)}")

            # Wait before next attempt with shorter delays for faster recovery
            if attempt < 3:
                wait_time = min(2 ** attempt, 4)  # Cap at 4 seconds
                await asyncio.sleep(wait_time)

        # Only show error if all attempts failed
        logger.debug("Failed to reconnect after multiple attempts")
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

            # Modern minimal interface - no verbose help

            # Start the chat loop
            await self._chat_loop()

        except KeyboardInterrupt:
            self.graceful_shutdown = True
            # Minimal shutdown message
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
                # Enhanced connection checking with background monitoring
                if not await self._check_connection():
                    # Connection lost - try silent recovery first
                    if not await self._silent_recovery():
                        # If silent recovery fails, try one more manual attempt
                        if not await self._attempt_reconnection():
                            # Only exit if all recovery attempts fail
                            logger.debug("All connection recovery attempts failed")
                            self.ui.display_connection_error("Connection lost. Please check your network and try again.", silent=False)
                            break

                # Set connection to idle state before waiting for user input
                if self.connection:
                    self.connection.set_streaming_state(False)

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

                # Process the message (user message will be displayed by the prompt)
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

        # Minimal shutdown - goodbye handled elsewhere

    async def _handle_command(self, command: str) -> bool:
        """Handle chat commands. Returns True if should exit."""
        command = command.lower().strip()

        if command in ['/exit', '/quit', '/bye', '/goodbye']:
            self.graceful_shutdown = True
            # Minimal shutdown - no verbose messages
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

                # Mode override handled silently for cleaner interface

                # Enhanced chat-style loading indicator with horizontal padding
                loading_text = Text()
                loading_text.append("    Thinking", style="dim bright_white")  # Added horizontal padding
                loading_text.append("...", style="dim bright_cyan")
                self.ui.console.print(loading_text)

                # Choose generation method based on active mode
                if active_mode == GenerationMode.STREAM:
                    # Stream mode with enhanced reliability
                    try:
                        await self._generate_stream_with_recovery(cleaned_message)
                    except Exception as e:
                        logger.error(f"Stream mode failed with exception: {str(e)}")
                        self.ui.display_error(f"Stream generation failed: {str(e)}")
                elif active_mode == GenerationMode.CHAT:
                    # Chat mode with enhanced reliability
                    try:
                        response = await self._chat_completion_with_recovery(cleaned_message)
                        if response:
                            logger.debug("Chat mode: received response from server")
                            response_text = self._extract_response_text(response)
                            if response_text:
                                model_name = self.model_info.get('model_id', 'AI') if self.model_info else 'AI'
                                logger.debug(f"Chat mode: extracted {len(response_text)} characters")
                                self.ui.display_ai_response(response_text, model_name)
                            else:
                                logger.error("Chat mode: failed to extract text from response")
                                logger.debug(f"Response structure: {response}")
                                self.ui.display_error("Received empty response from server")
                        else:
                            logger.error("Chat mode: no response received from server")
                            self.ui.display_error("Failed to get response from server")
                    except Exception as e:
                        logger.error(f"Chat mode failed with exception: {str(e)}")
                        self.ui.display_error(f"Chat generation failed: {str(e)}")
                elif active_mode == GenerationMode.BATCH:
                    # Batch mode with enhanced reliability
                    try:
                        # For batch mode, treat single messages as single-item batches
                        await self._process_batch_with_recovery([cleaned_message])
                    except Exception as e:
                        logger.error(f"Batch mode failed with exception: {str(e)}")
                        self.ui.display_error(f"Batch generation failed: {str(e)}")
                else:
                    # Simple generation mode with enhanced reliability
                    try:
                        response = await self._generate_text_with_recovery(cleaned_message)
                        if response:
                            logger.debug("Simple generation: received response from server")
                            response_text = self._extract_response_text(response)
                            if response_text:
                                model_name = self.model_info.get('model_id', 'AI') if self.model_info else 'AI'
                                logger.debug(f"Simple generation: extracted {len(response_text)} characters")
                                self.ui.display_ai_response(response_text, model_name)
                            else:
                                logger.error("Simple generation: failed to extract text from response")
                                logger.debug(f"Response structure: {response}")
                                self.ui.display_error("Received empty response from server")
                        else:
                            logger.error("Simple generation: no response received from server")
                            self.ui.display_error("Failed to get response from server")
                    except Exception as e:
                        logger.error(f"Simple generation failed with exception: {str(e)}")
                        self.ui.display_error(f"Generation failed: {str(e)}")

                # If we reach here, processing was successful
                return

            except ConnectionError as e:
                logger.debug(f"Connection error on attempt {attempt + 1}: {str(e)}")
                if attempt == 0:
                    # Try to reconnect on first failure
                    if await self._attempt_reconnection():
                        continue
                self.ui.display_connection_error(f"Connection error: {str(e)}", silent=True)
                return

            except Exception as e:
                logger.error(f"Error processing message on attempt {attempt + 1}: {str(e)}")
                if attempt == max_attempts - 1:  # Last attempt
                    self.ui.display_error(f"❌ Error processing message: {str(e)}")
                    return

    async def _generate_stream_with_recovery(self, prompt: str):
        """Generate streaming text with enhanced connection recovery and reliability"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.debug(f"Stream generation attempt {attempt + 1}/{max_retries}")
                await self._generate_stream(prompt)
                logger.debug(f"Stream generation successful on attempt {attempt + 1}")
                return

            except Exception as e:
                logger.error(f"Stream generation attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    if self._is_connection_error(e):
                        # Try to reconnect before next attempt
                        try:
                            await self.connect()
                        except Exception:
                            pass
                    await asyncio.sleep(2)
                    continue
                else:
                    # Final attempt failed
                    if self._is_connection_error(e):
                        self.ui.display_connection_error("Connection issue - please try again", silent=True)
                        return
                    logger.error(f"Stream generation failed after {max_retries} attempts: {str(e)}")
                    self.ui.display_error(f"Stream generation failed: {str(e)}")
                    return

    async def _chat_completion_with_recovery(self, message: str):
        """Chat completion with enhanced connection recovery and reliability"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.debug(f"Chat completion attempt {attempt + 1}/{max_retries}")
                result = await self._chat_completion(message)

                if result is not None:
                    logger.debug(f"Chat completion successful on attempt {attempt + 1}")
                    return result
                else:
                    logger.warning(f"Chat completion returned None on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)
                        continue

            except Exception as e:
                logger.error(f"Chat completion attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    if self._is_connection_error(e):
                        # Try to reconnect before next attempt
                        try:
                            await self.connect()
                        except Exception:
                            pass
                    await asyncio.sleep(2)
                    continue
                else:
                    # Final attempt failed
                    if self._is_connection_error(e):
                        self.ui.display_connection_error("Connection issue - please try again", silent=True)
                        return None
                    raise

        return None

    def _is_connection_error(self, error: Exception) -> bool:
        """Check if an error is connection-related"""
        error_str = str(error).lower()
        connection_indicators = [
            "connection", "timeout", "network", "unreachable",
            "refused", "reset", "broken pipe", "socket"
        ]
        return any(indicator in error_str for indicator in connection_indicators)

    async def _silent_recovery(self) -> bool:
        """Attempt silent connection recovery"""
        if not self.connection or not self.auto_reconnect:
            return False

        try:
            # Check if connection has its own silent reconnection capability
            if hasattr(self.connection, '_silent_reconnect'):
                logger.debug("Attempting silent connection recovery...")
                success = await self.connection._silent_reconnect()
                if success:
                    self.connected = True
                    logger.debug("Silent recovery successful")
                    return True

            # Fallback to manual reconnection (but silent)
            logger.debug("Attempting manual silent recovery...")
            old_silent_mode = getattr(self.connection, 'silent_mode', False)
            if self.connection:
                self.connection.silent_mode = True

            success = await self._attempt_reconnection()

            # Restore original silent mode
            if self.connection:
                self.connection.silent_mode = old_silent_mode

            return success

        except Exception as e:
            logger.debug(f"Silent recovery failed: {e}")
            return False

    async def _generate_text_with_recovery(self, prompt: str):
        """Generate text with enhanced connection recovery and reliability"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.debug(f"Text generation attempt {attempt + 1}/{max_retries}")
                result = await self._generate_text(prompt)

                if result is not None:
                    logger.debug(f"Text generation successful on attempt {attempt + 1}")
                    return result
                else:
                    logger.warning(f"Text generation returned None on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)  # Brief delay before retry
                        continue

            except Exception as e:
                logger.error(f"Text generation attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    if "connection" in str(e).lower() or "timeout" in str(e).lower():
                        # Try to reconnect before next attempt
                        try:
                            await self.connect()
                        except Exception:
                            pass
                    await asyncio.sleep(2)  # Longer delay for error recovery
                    continue
                else:
                    # Final attempt failed
                    if "connection" in str(e).lower() or "timeout" in str(e).lower():
                        raise ConnectionError(f"Text generation connection failed after {max_retries} attempts: {str(e)}")
                    raise

        return None

    async def _process_batch_with_recovery(self, prompts: list):
        """Process batch with enhanced connection recovery and reliability"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.debug(f"Batch processing attempt {attempt + 1}/{max_retries}")
                await self._process_batch(prompts)
                logger.debug(f"Batch processing successful on attempt {attempt + 1}")
                return

            except Exception as e:
                logger.error(f"Batch processing attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    if "connection" in str(e).lower() or "timeout" in str(e).lower():
                        # Try to reconnect before next attempt
                        try:
                            await self.connect()
                        except Exception:
                            pass
                    await asyncio.sleep(2)
                    continue
                else:
                    # Final attempt failed
                    if "connection" in str(e).lower() or "timeout" in str(e).lower():
                        raise ConnectionError(f"Batch processing connection failed after {max_retries} attempts: {str(e)}")
                    raise

    async def _graceful_shutdown(self):
        """Perform graceful shutdown operations"""
        try:
            # Minimal graceful shutdown - no verbose messages

            # Save conversation if it exists and user wants to
            if self.session_history:
                try:
                    save_choice = self.ui.get_yes_no_input("Save conversation?")
                    if save_choice:
                        await self._save_conversation()
                except Exception as e:
                    logger.warning(f"Failed to save conversation during shutdown: {str(e)}")

            # Disconnect from server
            await self.disconnect()

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

            logger.debug("Cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
        finally:
            # Single minimal goodbye message
            self.ui.display_goodbye()

    async def _generate_text(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Generate text using the /generate endpoint with enhanced reliability"""
        try:
            if not self.connection:
                logger.error("No connection available for text generation")
                return None

            # Prepare generation parameters
            params = {
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
            }

            logger.debug(f"Sending text generation request with params: {params}")
            result = await self.connection.generate_text(prompt, **params)

            if result is None:
                logger.error("Connection returned None for text generation")
                return None

            logger.debug(f"Received response from server: {type(result)}")

            # Validate response structure
            if not isinstance(result, dict):
                logger.error(f"Invalid response type: {type(result)}, expected dict")
                return None

            return result

        except Exception as e:
            logger.error(f"Text generation failed with exception: {str(e)}")
            logger.debug(f"Exception details: {type(e).__name__}: {str(e)}")
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

            # Get model name from various possible fields
            model_name = 'AI'
            if self.model_info:
                model_name = (self.model_info.get('model_id') or
                             self.model_info.get('id') or
                             self.model_info.get('name') or 'AI')

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
                else:
                    logger.warning("No response content received from stream")

        except Exception as e:
            logger.error(f"Streaming generation failed: {str(e)}")
            import traceback
            logger.error(f"Streaming error traceback: {traceback.format_exc()}")
            self.ui.display_error(f"Streaming failed: {str(e)}")

    def _parse_stream_chunk(self, chunk: str) -> Optional[str]:
        """Parse a streaming chunk and extract text content"""
        try:
            if not chunk or chunk.strip() == "":
                return None

            # Try to parse as JSON first
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
                # If not JSON, treat as plain text token
                # This is likely the case for LocalLab's streaming format
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
        """Extract response text from API response with enhanced reliability"""
        try:
            if not response:
                logger.error("Response is None or empty")
                return None

            if not isinstance(response, dict):
                logger.error(f"Response is not a dict: {type(response)}")
                return None

            logger.debug(f"Extracting text from response keys: {list(response.keys())}")

            # Handle different response formats with comprehensive checking
            extracted_text = None

            # Check OpenAI-style format
            if "choices" in response and response["choices"]:
                choice = response["choices"][0]
                if "message" in choice and isinstance(choice["message"], dict):
                    extracted_text = choice["message"].get("content", "")
                elif "text" in choice:
                    extracted_text = choice["text"]

            # Check direct response formats
            elif "response" in response:
                extracted_text = response["response"]
            elif "text" in response:
                extracted_text = response["text"]
            elif "content" in response:
                extracted_text = response["content"]
            elif "generated_text" in response:
                extracted_text = response["generated_text"]
            elif "output" in response:
                extracted_text = response["output"]

            # Handle nested response structures
            elif "data" in response and isinstance(response["data"], dict):
                data = response["data"]
                if "text" in data:
                    extracted_text = data["text"]
                elif "content" in data:
                    extracted_text = data["content"]

            if extracted_text is None:
                logger.error(f"Could not extract text from response structure: {response}")
                return None

            # Clean and validate the extracted text
            if not isinstance(extracted_text, str):
                logger.warning(f"Extracted text is not a string: {type(extracted_text)}")
                extracted_text = str(extracted_text)

            # Clean up common artifacts and special tokens
            cleaned_text = self._clean_response_text(extracted_text)

            if not cleaned_text.strip():
                logger.warning("Extracted text is empty after cleaning")
                return None

            logger.debug(f"Successfully extracted {len(cleaned_text)} characters")
            return cleaned_text

        except Exception as e:
            logger.error(f"Failed to extract response text: {str(e)}")
            logger.debug(f"Response that caused error: {response}")
            return None

    def _clean_response_text(self, text: str) -> str:
        """Clean response text from common artifacts and special tokens"""
        try:
            if not text:
                return ""

            # Remove common conversation end markers
            end_markers = [
                "</|assistant|>",
                "<|endoftext|>",
                "</s>",
                "<|end|>",
                "</|im_end|>",
                "<|eot_id|>"
            ]

            cleaned = text
            for marker in end_markers:
                if marker in cleaned:
                    cleaned = cleaned.split(marker)[0]
                    logger.debug(f"Removed end marker: {marker}")

            # Remove excessive whitespace but preserve formatting
            lines = cleaned.split('\n')
            cleaned_lines = []
            for line in lines:
                cleaned_line = line.rstrip()  # Remove trailing whitespace
                cleaned_lines.append(cleaned_line)

            # Remove excessive empty lines at the end
            while cleaned_lines and not cleaned_lines[-1].strip():
                cleaned_lines.pop()

            cleaned = '\n'.join(cleaned_lines)

            return cleaned.strip()

        except Exception as e:
            logger.error(f"Error cleaning response text: {str(e)}")
            return text  # Return original text if cleaning fails

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
    
    # Modern minimal startup - no verbose information
    
    # Start the chat interface with comprehensive error handling
    try:
        asyncio.run(interface.start_chat())
    except KeyboardInterrupt:
        # Minimal shutdown - goodbye handled by cleanup
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
