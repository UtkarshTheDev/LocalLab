# LocalLab Node.js Client

Official Node.js client for LocalLab - A local LLM server.

## Features

- 🚀 Full TypeScript support
- 🔄 Async/await API
- 📊 Batch processing
- 🌊 Streaming support
- 💬 Chat completion
- 🔍 Model management
- 📈 System monitoring
- 🔒 Type-safe API

## Installation

```bash
npm install locallab-client
# or
yarn add locallab-client
```

## Quick Start

```typescript
import { LocalLabClient } from 'locallab-client';

// Initialize client
const client = new LocalLabClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-api-key', // Optional
});

// Basic generation
const response = await client.generate('Hello, how are you?');
console.log(response.response);

// Clean up
await client.close();
```

## Usage Examples

### Text Generation

```typescript
// Basic generation
const response = await client.generate('Hello, how are you?');
console.log(response.response);

// Generation with options
const response = await client.generate('Hello', {
  temperature: 0.7,
  maxLength: 100,
});

// Streaming generation
for await (const token of client.streamGenerate('Tell me a story')) {
  process.stdout.write(token);
}
```

### Chat Completion

```typescript
const messages = [
  { role: 'system', content: 'You are a helpful assistant.' },
  { role: 'user', content: 'What is the capital of France?' },
];

const response = await client.chat(messages);
console.log(response.choices[0].message.content);
```

### Batch Processing

```typescript
const prompts = [
  'What is 2+2?',
  'Who wrote Romeo and Juliet?',
  'What is the speed of light?',
];

const response = await client.batchGenerate(prompts);
console.log(response.responses);
```

### Model Management

```typescript
// List available models
const models = await client.listModels();
console.log(models);

// Load a specific model
await client.loadModel('mistral-7b');

// Get current model info
const currentModel = await client.getCurrentModel();
console.log(currentModel);
```

### System Monitoring

```typescript
// Get system information
const systemInfo = await client.getSystemInfo();
console.log(systemInfo);

// Check system health
const isHealthy = await client.healthCheck();
console.log(isHealthy);
```

### WebSocket Connection

```typescript
// Connect to WebSocket for real-time updates
await client.connect();

// Subscribe to messages
client.onMessage((data) => {
  console.log('Received:', data);
});

// Disconnect when done
await client.disconnect();
```

## API Reference

### Client Configuration

```typescript
interface LocalLabConfig {
  baseUrl: string;
  apiKey?: string;
  timeout?: number;
  retries?: number;
  headers?: Record<string, string>;
}
```

### Generation Options

```typescript
interface GenerateOptions {
  modelId?: string;
  maxLength?: number;
  temperature?: number;
  topP?: number;
  stream?: boolean;
}
```

### Response Types

```typescript
interface GenerateResponse {
  response: string;
  modelId: string;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

interface ChatResponse {
  choices: Array<{
    message: ChatMessage;
    finishReason: string;
  }>;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}
```

## Error Handling

The client throws typed errors that you can catch and handle:

```typescript
try {
  await client.generate('Hello');
} catch (error) {
  if (error instanceof ValidationError) {
    console.error('Validation error:', error.fieldErrors);
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limit exceeded. Retry after ${error.retryAfter}s`);
  } else {
    console.error('Unknown error:', error);
  }
}
```

## Development

### Building

```bash
npm run build
```

### Testing

```bash
npm test
```

### Linting

```bash
npm run lint
```

### Formatting

```bash
npm run format
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Additional Resources

- [TypeScript Guide](docs/typescript.md)
- [Error Handling Guide](docs/errors.md)
- [Best Practices](docs/best-practices.md)
- [Migration Guide](docs/migration.md) 