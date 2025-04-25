# LocalLab API Documentation

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
  "top_p": "float"
}
```

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
  "top_p": "float"
}
```

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

### Model Management

#### POST `/models/load`

Load a specific model.

**Request Body:**

```json
{
  "model_id": "string"
}
```

#### GET `/models/current`

Get information about the currently loaded model.

#### GET `/models/available`

List all available models in the registry.

### System Information

#### GET `/system/info`

Get detailed system information.

#### GET `/health`

Check the health status of the server.

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

## Related Documentation

- [Getting Started](./getting-started.md)
- [Features Guide](./features/README.md)
- [Local Deployment](./local_deployment.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)

---

Made with ❤️ by Utkarsh Tiwari  
GitHub: [UtkarshTheDev](https://github.com/UtkarshTheDev) | Twitter: [@UtkarshTheDev](https://twitter.com/UtkarshTheDev) | LinkedIn: [utkarshthedev](https://linkedin.com/in/utkarshthedev)
