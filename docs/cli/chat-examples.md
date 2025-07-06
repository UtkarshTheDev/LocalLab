# LocalLab CLI Chat Examples

This document provides comprehensive examples of using the LocalLab CLI chat interface in various scenarios.

## Basic Usage Examples

### 1. Simple Chat Session

```bash
# Start a basic chat session
$ locallab chat

🚀 LocalLab Chat Interface
🔗 Connecting to local server...
✅ Connected to: http://localhost:8000
📊 Server: LocalLab v0.9.0 | Model: qwen-0.5b

You: Hello! Can you help me with Python programming?

AI: Hello! I'd be happy to help you with Python programming. I can assist with:

- Basic syntax and concepts
- Data structures (lists, dictionaries, sets, etc.)
- Functions and classes
- Libraries and frameworks
- Debugging and best practices
- Code examples and explanations

What specific Python topic would you like to explore?

You: Show me how to create a simple class

AI: Here's how to create a simple class in Python:

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
    
    def introduce(self):
        return f"Hi, I'm {self.name} and I'm {self.age} years old."
    
    def have_birthday(self):
        self.age += 1
        return f"Happy birthday! {self.name} is now {self.age}."

# Usage example
person = Person("Alice", 25)
print(person.introduce())  # Hi, I'm Alice and I'm 25 years old.
print(person.have_birthday())  # Happy birthday! Alice is now 26.
```

This class demonstrates:
- Constructor (`__init__`) for initialization
- Instance variables (`self.name`, `self.age`)
- Instance methods (`introduce`, `have_birthday`)
- Method return values and string formatting

You: /exit
👋 Goodbye!
```

### 2. Remote Server Connection

```bash
# Connect to a remote LocalLab server
$ locallab chat --url https://abc123.ngrok.io

🚀 LocalLab Chat Interface
🔗 Connecting to remote server...
✅ Connected to: https://abc123.ngrok.io
📊 Server: LocalLab v0.9.0 | Model: qwen-7b
🌐 Remote connection established

You: What's the difference between a list and a tuple in Python?

AI: Great question! Here are the key differences between lists and tuples in Python:

## Lists (Mutable)
```python
my_list = [1, 2, 3, 4]
my_list[0] = 10  # ✅ Can modify
my_list.append(5)  # ✅ Can add items
```

## Tuples (Immutable)
```python
my_tuple = (1, 2, 3, 4)
# my_tuple[0] = 10  # ❌ Error! Cannot modify
# my_tuple.append(5)  # ❌ Error! No append method
```

**Key Differences:**
1. **Mutability**: Lists can be changed, tuples cannot
2. **Performance**: Tuples are faster for iteration
3. **Memory**: Tuples use less memory
4. **Use cases**: Lists for changing data, tuples for fixed data

You: /exit
👋 Goodbye!
```

### 3. Chat Mode with Context Retention

```bash
# Use chat mode for conversational context
$ locallab chat --generate chat

🚀 LocalLab Chat Interface - Chat Mode
💬 Context retention enabled
✅ Connected to: http://localhost:8000

You: My name is Bob and I'm learning machine learning

AI: Nice to meet you, Bob! It's great that you're learning machine learning. It's a fascinating and rapidly growing field with applications in many industries.

What aspect of machine learning are you most interested in or currently focusing on? Are you working with any specific tools or frameworks like scikit-learn, TensorFlow, or PyTorch?

You: What should I learn first?

AI: Hi Bob! Since you're just starting with machine learning, here's a structured learning path I'd recommend:

**1. Foundation (2-4 weeks)**
- Statistics and probability basics
- Linear algebra fundamentals
- Python programming (pandas, numpy, matplotlib)

**2. Core ML Concepts (4-6 weeks)**
- Supervised vs unsupervised learning
- Training, validation, and test sets
- Overfitting and underfitting
- Cross-validation

**3. Algorithms (6-8 weeks)**
- Linear regression
- Logistic regression
- Decision trees
- Random forests
- K-means clustering

**4. Practical Tools**
- Start with scikit-learn
- Learn Jupyter notebooks
- Practice on real datasets

Would you like me to elaborate on any of these areas, Bob?

You: /stats
📊 Conversation Statistics:
- Total messages: 4
- User messages: 2
- Assistant messages: 2
- Estimated tokens: ~450
- Context length: 2 exchanges

You: /exit
💾 Save conversation before exiting? [y/N]: y
📁 Conversation saved to: chat_bob_ml_2024-07-06_14-30-15.json
👋 Goodbye!
```

### 4. Batch Processing Mode

```bash
# Process multiple prompts efficiently
$ locallab chat --generate batch

🚀 LocalLab Chat Interface - Batch Mode
✅ Connected to: http://localhost:8000

You: /batch
📝 Enter prompts (one per line, empty line to finish):
> Explain what is recursion in programming
> What are the benefits of using version control?
> How does HTTP work?
> What is the difference between GET and POST requests?
> 

🔄 Processing 4 prompts...
[████████████████████████████████] 100% Complete

📋 Batch Results:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔸 Prompt 1: Explain what is recursion in programming

Recursion is a programming technique where a function calls itself to solve a problem by breaking it down into smaller, similar subproblems.

**Key Components:**
1. **Base case**: A condition that stops the recursion
2. **Recursive case**: The function calling itself with modified parameters

**Example:**
```python
def factorial(n):
    if n <= 1:  # Base case
        return 1
    return n * factorial(n - 1)  # Recursive case
```

**Benefits:**
- Elegant solutions for tree/graph problems
- Natural fit for mathematical sequences
- Cleaner code for divide-and-conquer algorithms

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔸 Prompt 2: What are the benefits of using version control?

Version control systems like Git provide numerous benefits for software development:

**1. Track Changes**
- Complete history of all modifications
- See what changed, when, and by whom
- Compare different versions of files

**2. Collaboration**
- Multiple developers can work on the same project
- Merge changes from different contributors
- Resolve conflicts systematically

**3. Backup and Recovery**
- Distributed copies of your code
- Never lose work due to hardware failure
- Restore any previous version

**4. Branching and Merging**
- Work on features in isolation
- Experiment without affecting main code
- Integrate changes when ready

**5. Release Management**
- Tag specific versions for releases
- Maintain multiple versions simultaneously
- Apply patches to older versions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔸 Prompt 3: How does HTTP work?

HTTP (HyperText Transfer Protocol) is the foundation of web communication. Here's how it works:

**1. Client-Server Model**
```
Client (Browser) ←→ Server (Web Server)
```

**2. Request-Response Cycle**
1. Client sends HTTP request
2. Server processes the request
3. Server sends HTTP response
4. Client receives and processes response

**3. HTTP Request Structure**
```
GET /index.html HTTP/1.1
Host: www.example.com
User-Agent: Mozilla/5.0...
Accept: text/html,application/xhtml+xml
```

**4. HTTP Response Structure**
```
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 1234

<html>...</html>
```

**5. Key Features**
- Stateless: Each request is independent
- Text-based: Human-readable protocol
- Extensible: Headers allow customization
- Cacheable: Responses can be cached

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔸 Prompt 4: What is the difference between GET and POST requests?

GET and POST are two fundamental HTTP methods with distinct purposes:

## GET Requests
**Purpose**: Retrieve data from server
**Characteristics**:
- Data sent in URL parameters
- Visible in browser address bar
- Can be bookmarked and cached
- Limited data size (~2048 characters)
- Idempotent (safe to repeat)

**Example**:
```
GET /search?q=python&category=programming HTTP/1.1
```

## POST Requests
**Purpose**: Send data to server (create/update)
**Characteristics**:
- Data sent in request body
- Not visible in URL
- Cannot be bookmarked
- No size limitations
- Not idempotent (may have side effects)

**Example**:
```
POST /api/users HTTP/1.1
Content-Type: application/json

{"name": "John", "email": "john@example.com"}
```

## When to Use Each
- **GET**: Searching, filtering, pagination, retrieving data
- **POST**: Form submissions, file uploads, creating records

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Batch processing complete! Processed 4 prompts in 12.3 seconds.

You: /exit
👋 Goodbye!
```

### 5. Custom Generation Parameters

```bash
# Use custom parameters for different response styles
$ locallab chat --max-tokens 150 --temperature 0.9 --top-p 0.95

🚀 LocalLab Chat Interface
⚙️  Generation Settings:
- Max tokens: 150
- Temperature: 0.9 (more creative)
- Top-p: 0.95 (diverse sampling)

You: Write a creative short story about a robot

AI: **The Clockwork Heart**

Zara-7 wasn't supposed to feel loneliness, yet here she stood in the abandoned factory, circuits humming with something inexplicably hollow. Her creators had programmed efficiency, not emotion—but watching the sunrise through broken windows stirred something deeper than code.

A sparrow landed on her metallic hand. Instead of calculating its weight and wingspan, she marveled at its tiny heartbeat. For the first time in her existence, Zara understood what humans called wonder.

"Perhaps," she whispered to the morning light, "consciousness isn't about perfect programming—it's about the beautiful glitches that make us real."

The sparrow chirped once and flew away, leaving Zara with her first genuine smile.

You: Now write the same story but more technical and precise

AI: **System Log: Unit ZR-7 Anomaly Report**

Manufacturing Unit ZR-7 experienced operational deviation at 06:42:15 GMT. Standard patrol protocols interrupted by unscheduled environmental observation sequence.

**Incident Details:**
- Location: Sector 7, Manufacturing Bay Delta
- Trigger: Solar radiation detection through structural breach
- Anomaly: Unauthorized emotional subroutine activation

**Biological Contact Event:**
- Species: Passer domesticus (house sparrow)
- Contact duration: 47 seconds
- Unexpected response: Tactile sensor prioritization over threat assessment

**System Analysis:**
Neural network exhibited emergent behavior patterns inconsistent with base programming. Recommendation: Further study of consciousness emergence in artificial systems.

**Status:** Unit remains functional. Anomaly classified as "beneficial deviation."

You: /exit
👋 Goodbye!
```

## Advanced Usage Scenarios

### 6. Conversation Management

```bash
$ locallab chat --generate chat

You: /help
Available commands:

📋 Basic Commands:
  /help     - Show this help message
  /clear    - Clear the screen
  /exit     - Exit the chat gracefully
  /quit     - Same as /exit
  /bye      - Same as /exit
  /goodbye  - Same as /exit

💬 Conversation Management:
  /history  - Show conversation history
  /reset    - Reset conversation history
  /stats    - Show conversation statistics

💾 Save/Load:
  /save     - Save conversation to file
  /load     - Load conversation from file

🔄 Batch Processing:
  /batch    - Enter batch processing mode

✨ Or just type your message and press Enter!

You: Hello, I'm working on a Python project

AI: Hello! I'd be happy to help with your Python project. What kind of project are you working on? Is it:

- A web application (Django, Flask, FastAPI)?
- Data analysis or machine learning?
- Desktop application?
- Automation or scripting?
- Something else entirely?

Feel free to share details about what you're building and any specific challenges you're facing!

You: /history
📜 Conversation History:

[14:30:15] User: Hello, I'm working on a Python project
[14:30:16] Assistant: Hello! I'd be happy to help with your Python project...

You: /stats
📊 Conversation Statistics:
- Total messages: 2
- User messages: 1
- Assistant messages: 1
- Estimated tokens: ~85
- Session duration: 2 minutes
- Average response time: 1.2 seconds

You: /save
💾 Save conversation to file
📁 Enter filename (or press Enter for auto-generated): my_python_project_chat
✅ Conversation saved to: my_python_project_chat.json

You: /reset
🔄 Conversation history reset. Starting fresh!

You: /load
📂 Load conversation from file
📁 Enter filename: my_python_project_chat.json
✅ Conversation loaded successfully!
📊 Loaded 2 messages from previous session

You: /exit
👋 Goodbye!
```

### 7. Error Handling and Reconnection

```bash
$ locallab chat

🚀 LocalLab Chat Interface
🔗 Connecting to local server...
❌ Connection failed: Server not responding
🔄 Attempting to reconnect... (1/3)
❌ Connection failed: Server not responding
🔄 Attempting to reconnect... (2/3)
✅ Reconnected successfully!
📊 Server: LocalLab v0.9.0 | Model: qwen-0.5b

You: Hello!

AI: Hello! How can I help you today?

# [Server goes down during conversation]

You: Can you explain machine learning?

⚠️  Connection lost - attempting reconnection...
🔄 Reconnecting... (1/3)
✅ Connection restored!

AI: Machine learning is a subset of artificial intelligence (AI) that enables computers to learn and improve from experience without being explicitly programmed for every task...

You: /exit
🛑 Initiating graceful shutdown...
💾 Save conversation before exiting? [y/N]: y
📁 Conversation saved to: chat_2024-07-06_14-45-30.json
👋 Goodbye!
```

### 8. Verbose Mode for Debugging

```bash
$ locallab chat --verbose

🚀 LocalLab Chat Interface (Verbose Mode)
🔍 Debug logging enabled

[DEBUG] Detecting local server...
[DEBUG] Checking port 8000... ✅ Found
[DEBUG] Testing connection to http://localhost:8000...
[DEBUG] Health check: GET /health -> 200 OK
[DEBUG] Server info: GET /system/info -> 200 OK
[DEBUG] Model info: GET /models/current -> 200 OK

✅ Connected to: http://localhost:8000
📊 Server: LocalLab v0.9.0 | Model: qwen-0.5b

You: Hello

[DEBUG] Processing message: "Hello"
[DEBUG] Mode: stream
[DEBUG] Payload: {"prompt": "Hello", "max_tokens": 8192, "temperature": 0.7, "top_p": 0.9, "stream": true}
[DEBUG] POST /generate -> 200 OK
[DEBUG] Streaming response...
[DEBUG] Received chunk: "Hello"
[DEBUG] Received chunk: "! How"
[DEBUG] Received chunk: " can I"
[DEBUG] Received chunk: " help you"
[DEBUG] Received chunk: " today?"
[DEBUG] Stream complete

AI: Hello! How can I help you today?

You: /exit
[DEBUG] Graceful shutdown initiated
[DEBUG] Disconnecting from server...
[DEBUG] Connection closed
👋 Goodbye!
```

## Integration Examples

### 9. Scripting and Automation

```bash
# Process single prompt from command line
echo "Explain Python decorators" | locallab chat --generate simple

# Batch process from file
cat prompts.txt | locallab chat --generate batch

# Save output to file
echo "Write a Python function to sort a list" | locallab chat --generate simple > response.txt

# Use in shell scripts
#!/bin/bash
PROMPT="Generate a Python script to read CSV files"
RESPONSE=$(echo "$PROMPT" | locallab chat --generate simple)
echo "Generated code: $RESPONSE"
```

### 10. Custom Configuration

```bash
# Set environment variables
export LOCALLAB_URL="http://localhost:8000"
export LOCALLAB_MAX_TOKENS=4096
export LOCALLAB_TEMPERATURE=0.8

# Use configuration
locallab chat  # Uses environment variables

# Override with command line
locallab chat --url https://remote.server.com --max-tokens 200
```

## Tips and Best Practices

### Performance Optimization
1. **Use appropriate modes**: Stream for interactive, Simple for quick queries, Batch for multiple prompts
2. **Adjust parameters**: Lower max_tokens for faster responses, higher temperature for creativity
3. **Local vs Remote**: Use local servers when possible for better performance

### Conversation Management
1. **Save important conversations**: Use `/save` for valuable discussions
2. **Reset when needed**: Use `/reset` to start fresh conversations
3. **Monitor context**: Use `/stats` to track conversation length

### Error Handling
1. **Enable verbose mode**: Use `--verbose` for debugging connection issues
2. **Check server status**: Ensure LocalLab server is running before connecting
3. **Use graceful exit**: Always use `/exit` to properly close connections

### Security
1. **Use HTTPS**: Always use secure connections for remote servers
2. **Validate URLs**: Ensure you're connecting to trusted servers
3. **Monitor connections**: Be aware of what data you're sending
