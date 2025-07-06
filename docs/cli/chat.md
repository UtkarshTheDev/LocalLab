# LocalLab Chat Interface - Your Personal ChatGPT

The LocalLab Chat Interface is a powerful terminal-based tool that gives you a **ChatGPT-like experience** right in your command line. It's the easiest and most intuitive way to interact with your AI models.

## 🎯 Why Use the Chat Interface?

- **🚀 Instant Access** - No coding required, just type and chat
- **💬 Natural Conversations** - ChatGPT-like experience in your terminal
- **🎨 Rich Formatting** - Markdown rendering with syntax highlighting
- **⚡ Real-time Responses** - See AI responses as they're generated
- **🔄 Smart Features** - History, saving, batch processing, and more
- **🌐 Works Everywhere** - Local, remote, or Google Colab

## 🚀 Quick Start

```bash
# 1. Start your server (if not already running)
locallab start

# 2. Open chat interface
locallab chat

# 3. Start chatting!
You: Hello! Can you help me with Python?
AI: Hello! I'd be happy to help you with Python programming...
```

### Advanced Usage

```bash
# Connect to remote server
locallab chat --url https://your-ngrok-url.app

# Use specific generation mode
locallab chat --generate chat

# Customize generation parameters
locallab chat --max-tokens 200 --temperature 0.8 --top-p 0.9
```

## ✨ Key Features

### 🎯 Generation Modes
| Mode | Description | Best For | Usage |
|------|-------------|----------|-------|
| **Stream** | Real-time response streaming | Interactive conversations | `--generate stream` |
| **Chat** | Conversational with context | Multi-turn discussions | `--generate chat` |
| **Simple** | Single-shot generation | Quick queries | `--generate simple` |
| **Batch** | Multiple prompt processing | Bulk operations | `--generate batch` |

### 🔄 Dynamic Mode Switching (New!)
Override the default mode for any message:
```bash
You: Write a story --stream          # Use streaming mode
You: Remember my name is Alice --chat # Use chat mode with context
You: What's 2+2? --simple           # Use simple mode
You: Process these --batch          # Use batch mode
```

### 💬 User Interface Features
- **🎨 Rich Markdown Rendering** - Full markdown support with syntax highlighting
- **💻 Code Highlighting** - 40+ programming languages supported
- **📊 Progress Indicators** - Visual progress bars for batch operations
- **🎮 Interactive Commands** - Built-in commands for session management
- **📱 Responsive Design** - Adapts to terminal size and capabilities

### 🛠️ Reliability Features
- **🔄 Auto-reconnection** - Automatic server reconnection with retries
- **💾 Graceful Shutdown** - Clean exit with conversation save prompts
- **📡 Connection Monitoring** - Real-time health checks and status monitoring
- **⚡ Resource Management** - Efficient memory and connection management

## Command Line Options

### Basic Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--url` | `-u` | LocalLab server URL | `http://localhost:8000` |
| `--generate` | `-g` | Generation mode | `stream` |
| `--verbose` | `-v` | Enable verbose output | `False` |

### Generation Parameters

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--max-tokens` | `-m` | Maximum tokens to generate | `8192` |
| `--temperature` | `-t` | Temperature for generation | `0.7` |
| `--top-p` | `-p` | Top-p for nucleus sampling | `0.9` |

## Generation Modes

### Stream Mode (Default)
Real-time streaming responses with live text generation.

```bash
locallab chat --generate stream
```

**Features:**
- Live text streaming
- Real-time response display
- Immediate feedback
- Optimal for interactive conversations

### Simple Mode
Single-shot text generation without streaming.

```bash
locallab chat --generate simple
```

**Features:**
- Complete response at once
- Lower resource usage
- Suitable for quick queries
- Faster for short responses

### Chat Mode
Conversational mode with context retention and history.

```bash
locallab chat --generate chat
```

**Features:**
- Multi-turn conversations
- Context preservation
- Conversation history
- Memory of previous exchanges

### Batch Mode
Process multiple prompts efficiently in batches.

```bash
locallab chat --generate batch
```

**Features:**
- Multiple prompt processing
- Progress tracking
- Efficient resource usage
- Bulk text generation

## Interactive Commands

### Session Control
- `/exit`, `/quit`, `/bye`, `/goodbye` - Exit the chat gracefully
- `/clear` - Clear the terminal screen
- `/help` - Show available commands

### Conversation Management
- `/history` - Display conversation history
- `/reset` - Reset conversation history
- `/stats` - Show conversation statistics

### File Operations
- `/save` - Save conversation to file
- `/load` - Load conversation from file

### Batch Processing
- `/batch` - Enter interactive batch mode

## Inline Mode Switching

You can override the default generation mode for individual messages using inline mode switches. Simply append the desired mode to your message:

### Syntax
```
Your message --[mode]
```

### Available Modes
- `--stream` - Stream response in real-time
- `--chat` - Use conversational mode with context
- `--batch` - Process as single batch item
- `--simple` - Simple text generation

### Examples

```bash
# Override to stream mode for one message
You: Explain quantum physics --stream
🔄 Using stream mode for this message
AI: [Streaming response...]

# Override to chat mode
You: Remember my name is Alice --chat
🔄 Using chat mode for this message
AI: I'll remember that your name is Alice.

# Override to simple mode
You: What's 2+2? --simple
🔄 Using simple mode for this message
AI: 4

# Invalid mode shows error
You: Hello --invalid
❌ Invalid mode: --invalid. Valid modes: --stream, --chat, --batch, --simple
```

### Features
- **Per-message overrides**: Change mode for specific messages without affecting the default
- **Case insensitive**: `--STREAM`, `--Stream`, and `--stream` all work
- **Backward compatible**: Existing CLI options continue to work as default mode setters
- **Error handling**: Clear error messages for invalid mode specifications
- **Visual feedback**: Mode override notifications show which mode is being used

## Usage Examples

### Basic Chat Session

```bash
$ locallab chat
🚀 LocalLab Chat Interface
Connected to: http://localhost:8000
Server: LocalLab v0.9.0 | Model: qwen-0.5b

You: Hello! How are you today?
AI: Hello! I'm doing well, thank you for asking. I'm here and ready to help you with any questions or tasks you might have. How can I assist you today?

You: /exit
👋 Goodbye!
```

### Remote Server Connection

```bash
$ locallab chat --url https://abc123.ngrok.io
🚀 LocalLab Chat Interface
🔗 Connecting to remote server...
✅ Connected to: https://abc123.ngrok.io
Server: LocalLab v0.9.0 | Model: qwen-7b

You: What's the weather like?
AI: I don't have access to real-time weather data...
```

### Chat Mode with Context

```bash
$ locallab chat --generate chat
🚀 LocalLab Chat Interface - Chat Mode
💬 Context retention enabled

You: My name is Alice
AI: Nice to meet you, Alice! How can I help you today?

You: What's my name?
AI: Your name is Alice, as you just told me.

You: /stats
📊 Conversation Statistics:
- Total messages: 4
- User messages: 2
- Assistant messages: 2
- Estimated tokens: ~150
```

### Batch Processing

```bash
$ locallab chat --generate batch
🚀 LocalLab Chat Interface - Batch Mode

You: /batch
📝 Enter prompts (one per line, empty line to finish):
> Explain quantum computing
> What is machine learning?
> Define artificial intelligence
> 

🔄 Processing 3 prompts...
[████████████████████████████████] 100% Complete

Results:
1. Quantum computing is a revolutionary computing paradigm...
2. Machine learning is a subset of artificial intelligence...
3. Artificial intelligence (AI) refers to the simulation...
```

### Custom Parameters

```bash
$ locallab chat --max-tokens 200 --temperature 0.9 --top-p 0.95
🚀 LocalLab Chat Interface
⚙️  Generation Settings:
- Max tokens: 200
- Temperature: 0.9
- Top-p: 0.95

You: Write a creative story
AI: [More creative and varied response due to higher temperature]
```

## Error Handling

### Connection Issues

The chat interface automatically handles various connection scenarios:

```bash
❌ Connection failed: Server not responding
🔄 Attempting to reconnect... (1/3)
✅ Reconnected successfully!
```

### Server Disconnection

```bash
⚠️  Connection lost - attempting reconnection...
🔄 Reconnecting... (2/3)
✅ Connection restored!
```

### Graceful Shutdown

```bash
You: /exit
🛑 Initiating graceful shutdown...
💾 Save conversation before exiting? [y/N]: y
📁 Conversation saved to: chat_2024-07-06_14-30-15.json
👋 Goodbye!
```

## Configuration

### Environment Variables

```bash
# Default server URL
export LOCALLAB_URL="http://localhost:8000"

# Default generation parameters
export LOCALLAB_MAX_TOKENS=4096
export LOCALLAB_TEMPERATURE=0.7
export LOCALLAB_TOP_P=0.9
```

### Connection Settings

```bash
# Connection timeout (seconds)
export LOCALLAB_TIMEOUT=30

# Reconnection attempts
export LOCALLAB_MAX_RETRIES=3

# Retry delay (seconds)
export LOCALLAB_RETRY_DELAY=2
```

## Troubleshooting

### Common Issues

**Server Not Found**
```bash
❌ Error: Could not connect to LocalLab server
💡 Make sure the LocalLab server is running and accessible.
```

**Solution:** Start the LocalLab server first:
```bash
locallab start
```

**Connection Timeout**
```bash
❌ Timeout Error: Connection or operation timed out
💡 Try increasing timeout or check your network connection.
```

**Solution:** Use longer timeout:
```bash
locallab chat --timeout 60
```

**Model Not Loaded**
```bash
⚠️  Warning: No model currently loaded
💡 Load a model first using the LocalLab interface
```

**Solution:** Load a model through the web interface or API.

### Debug Mode

Enable verbose output for debugging:

```bash
locallab chat --verbose
```

This provides detailed logging of:
- Connection attempts
- API requests/responses
- Error details
- Performance metrics

## Advanced Usage

### Scripting and Automation

The chat interface can be used in scripts with input redirection:

```bash
# Process prompts from file
echo "Hello world" | locallab chat --generate simple

# Batch process from file
locallab chat --generate batch < prompts.txt
```

### Integration with Other Tools

```bash
# Pipe output to other commands
echo "Summarize this text" | locallab chat --generate simple | tee summary.txt

# Use with curl for remote processing
curl -s https://api.example.com/data | locallab chat --generate simple
```

## API Compatibility

The chat interface is compatible with LocalLab server endpoints:

- `/generate` - Text generation
- `/chat` - Chat completions
- `/generate/batch` - Batch processing
- `/health` - Health checks
- `/system/info` - Server information
- `/models/current` - Model information

## Performance Tips

1. **Use appropriate generation modes**:
   - Stream for interactive chat
   - Simple for quick queries
   - Batch for multiple prompts

2. **Optimize parameters**:
   - Lower max_tokens for faster responses
   - Adjust temperature based on use case
   - Use appropriate top_p values

3. **Connection management**:
   - Keep connections alive for multiple requests
   - Use local servers when possible
   - Monitor connection health

## Security Considerations

- Always use HTTPS for remote connections
- Validate server certificates
- Avoid sending sensitive data over unencrypted connections
- Use authentication when available
- Monitor for unusual connection patterns

## See Also

- [LocalLab Server Documentation](../server/README.md)
- [API Reference](../api/README.md)
- [Python Client](../clients/python/README.md)
- [Troubleshooting Guide](../guides/troubleshooting.md)
