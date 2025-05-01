# LocalLab API Documentation

## Base URL

When making API requests, use one of the following base URLs:

- **Local development**: `http://localhost:8000`
- **Remote access**: Use your ngrok URL (e.g., `https://abcd1234.ngrok.io`)

For all examples below, replace `{BASE_URL}` with your actual base URL.

```bash
# For local development
export BASE_URL=http://localhost:8000

# For remote access via ngrok
export BASE_URL=https://your-ngrok-url.ngrok.io
```

## REST API Endpoints

### Text Generation

#### POST `/generate`

Generate text using the loaded model.

**Request Body:**

```json
{
  "prompt": "string",
  "model_id": "string | null",
  "stream": "boolean",
  "max_length": "integer | null",
  "temperature": "float",
  "top_p": "float",
  "top_k": "integer",
  "repetition_penalty": "float"
}
```

**Response Quality Parameters:**

| Parameter            | Default | Description                                                          |
| -------------------- | ------- | -------------------------------------------------------------------- |
| `max_length`         | 8192    | Maximum number of tokens in the generated response                   |
| `temperature`        | 0.7     | Controls randomness (higher = more creative, lower = more focused)   |
| `top_p`              | 0.9     | Nucleus sampling parameter (higher = more diverse responses)         |
| `top_k`              | 80      | Limits vocabulary to top K tokens (higher = more diverse vocabulary) |
| `repetition_penalty` | 1.15    | Penalizes repetition (higher = less repetition)                      |

> **Note**: All parameters are optional. If not provided, the server will use the default values shown above.

**Response:**

```json
{
  "response": "string",
  "usage": {
    "prompt_tokens": "integer",
    "completion_tokens": "integer",
    "total_tokens": "integer"
  }
}
```

**Example (curl):**

```bash
# Basic generation with minimal parameters
curl -X POST "${BASE_URL}/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing in simple terms"
  }'

# Generation with all parameters
curl -X POST "${BASE_URL}/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing in simple terms",
    "model_id": null,
    "stream": false,
    "max_length": 8192,
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 80,
    "repetition_penalty": 1.15
  }'

# Streaming generation
curl -X POST "${BASE_URL}/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing in simple terms",
    "stream": true
  }'
```

**Error Responses:**

- `400 Bad Request`: Invalid parameters
- `413 Payload Too Large`: Input too long
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Model error

### Chat Completion

#### POST `/chat`

Chat completion endpoint similar to OpenAI's API.

**Request Body:**

```json
{
  "messages": [
    {
      "role": "string",
      "content": "string"
    }
  ],
  "model_id": "string | null",
  "stream": "boolean",
  "max_length": "integer | null",
  "temperature": "float",
  "top_p": "float",
  "top_k": "integer",
  "repetition_penalty": "float"
}
```

> **Note**: The same response quality parameters from the `/generate` endpoint apply here. All parameters are optional and use the same defaults.

**Response:**

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "string"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": "integer",
    "completion_tokens": "integer",
    "total_tokens": "integer"
  }
}
```

**Example (curl):**

```bash
# Basic chat with minimal parameters
curl -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'

# Chat with all parameters
curl -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "model_id": null,
    "stream": false,
    "max_length": 8192,
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 80,
    "repetition_penalty": 1.15
  }'

# Streaming chat
curl -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "stream": true
  }'
```

### Batch Generation

#### POST `/generate/batch`

Generate text for multiple prompts in parallel.

**Request Body:**

```json
{
  "prompts": ["string", "string", ...],
  "model_id": "string | null",
  "max_length": "integer | null",
  "temperature": "float",
  "top_p": "float",
  "top_k": "integer",
  "repetition_penalty": "float"
}
```

> **Note**: The same response quality parameters from the `/generate` endpoint apply here. All parameters are optional and use the same defaults.

**Response:**

```json
{
  "responses": ["string", "string", ...],
  "usage": {
    "prompt_tokens": "integer",
    "completion_tokens": "integer",
    "total_tokens": "integer"
  }
}
```

**Example (curl):**

```bash
# Basic batch generation with minimal parameters
curl -X POST "${BASE_URL}/generate/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "prompts": [
      "Write a haiku about nature",
      "Tell a short joke",
      "Give a fun fact about space"
    ]
  }'

# Batch generation with all parameters
curl -X POST "${BASE_URL}/generate/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "prompts": [
      "Write a haiku about nature",
      "Tell a short joke",
      "Give a fun fact about space"
    ],
    "model_id": null,
    "max_length": 8192,
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 80,
    "repetition_penalty": 1.15
  }'
```

### Model Management

#### POST `/models/load`

Load a specific model.

**Request Body:**

```json
{
  "model_id": "string"
}
```

**Example (curl):**

```bash
# Load a specific model
curl -X POST "${BASE_URL}/models/load" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "microsoft/phi-2"
  }'
```

#### GET `/models/current`

Get information about the currently loaded model.

**Example (curl):**

```bash
# Get current model information
curl -X GET "${BASE_URL}/models/current"
```

#### GET `/models/available`

List all available models in the registry.

**Example (curl):**

```bash
# List all available models
curl -X GET "${BASE_URL}/models/available"
```

#### POST `/models/unload`

Unload the current model to free up resources.

**Example (curl):**

```bash
# Unload the current model
curl -X POST "${BASE_URL}/models/unload"
```

### System Information

#### GET `/system/info`

Get detailed system information.

**Example (curl):**

```bash
# Get system information
curl -X GET "${BASE_URL}/system/info"
```

#### GET `/health`

Check the health status of the server.

**Example (curl):**

```bash
# Check server health
curl -X GET "${BASE_URL}/health"
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200`: Success
- `400`: Bad Request
- `404`: Not Found
- `500`: Internal Server Error

Error responses include a detail message:

```json
{
  "detail": "Error message describing what went wrong"
}
```

## Rate Limiting

- 60 requests per minute
- Burst size of 10 requests

## Tips for Using the API

### Default Parameters

All generation endpoints have sensible defaults for the response quality parameters:

- `max_length`: 8192 tokens
- `temperature`: 0.7
- `top_p`: 0.9
- `top_k`: 80
- `repetition_penalty`: 1.15

You can omit any or all of these parameters in your requests, and the server will use these defaults.

### Testing with Different Parameters

When experimenting with different parameter values, here's what to try:

- For more creative responses: Increase `temperature` (0.8-1.0) and `top_p` (0.95-1.0)
- For more focused responses: Decrease `temperature` (0.3-0.5) and `top_p` (0.5-0.7)
- For less repetition: Increase `repetition_penalty` (1.2-1.5)
- For longer responses: Increase `max_length` (up to 16384)

### Handling Streaming Responses

When using streaming endpoints (`stream: true`), the response will be sent as a series of Server-Sent Events (SSE). Each event starts with `data: ` followed by the token or chunk. The end of the stream is marked with `data: [DONE]`.

```bash
# Example of processing streaming responses with bash
curl -X POST "${BASE_URL}/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "stream": true}' | while read -r line; do
    if [[ $line == data:* ]]; then
      content=${line#data: }
      if [[ $content != "[DONE]" ]]; then
        echo -n "$content"
      fi
    fi
  done
```

## Related Documentation

- [Getting Started](./getting-started.md)
- [Features Guide](./features/README.md)
- [Local Deployment](./local_deployment.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)

---

Made with ❤️ by Utkarsh Tiwari
GitHub: [UtkarshTheDev](https://github.com/UtkarshTheDev) | Twitter: [@UtkarshTheDev](https://twitter.com/UtkarshTheDev) | LinkedIn: [utkarshthedev](https://linkedin.com/in/utkarshthedev)
