# LocalLab Node.js Client

The official Node.js client for LocalLab, providing a simple and powerful interface to interact with your LocalLab server.

## 📦 Installation

```bash
npm install locallab-client
# or
yarn add locallab-client
```

## 🚀 Quick Start

```javascript
const LocalLabClient = require("locallab-client");

// Initialize client
const client = new LocalLabClient("http://localhost:8000");

// Basic text generation
async function generateText() {
  try {
    const response = await client.generate("Write a story about a robot");
    console.log(response);
  } catch (error) {
    console.error("Generation failed:", error);
  }
}

generateText();
```

## 📚 API Reference

### Client Initialization

```javascript
const client = new LocalLabClient(baseUrl, options);
```

Options:

```javascript
{
    timeout: 30000,           // Request timeout in ms
    retries: 3,              // Number of retry attempts
    headers: {},             // Custom headers
    validateStatus: true     // Enable response validation
}
```

### Text Generation

#### Basic Generation

```javascript
const response = await client.generate(prompt, {
  modelId: "qwen-0.5b",
  temperature: 0.7,
  maxLength: 100,
  topP: 0.9,
});
```

#### Streaming Generation

```javascript
for await (const token of client.streamGenerate(prompt, {
  modelId: "qwen-0.5b",
  temperature: 0.7,
})) {
  process.stdout.write(token);
}
```

### Chat Completion

```javascript
const response = await client.chat(
  [
    { role: "system", content: "You are a helpful assistant." },
    { role: "user", content: "Hello!" },
  ],
  {
    modelId: "qwen-0.5b",
    temperature: 0.7,
  }
);
```

### Batch Generation

```javascript
const responses = await client.batchGenerate(
  ["Write a haiku", "Tell a joke", "Give a fun fact"],
  {
    modelId: "qwen-0.5b",
    temperature: 0.7,
  }
);
```

### Model Management

```javascript
// List available models
const models = await client.listModels();

// Load specific model
await client.loadModel("qwen-0.5b");

// Get current model info
const modelInfo = await client.getCurrentModel();

// Unload model
await client.unloadModel();
```

### System Information

```javascript
const info = await client.getSystemInfo();
console.log(`CPU Usage: ${info.cpuUsage}%`);
console.log(`Memory Usage: ${info.memoryUsage}%`);
if (info.gpuInfo) {
  console.log(`GPU Memory: ${info.gpuInfo.usedMemory} MB`);
}
```

## 🌟 Features

### 1. Automatic Retries

```javascript
const client = new LocalLabClient("http://localhost:8000", {
  retries: 3,
  retryDelay: 1000,
});
```

### 2. Event Handling

```javascript
client.on("error", (error) => {
  console.error("Client error:", error);
});

client.on("modelLoaded", (modelId) => {
  console.log(`Model ${modelId} loaded`);
});
```

### 3. Request Cancellation

```javascript
const controller = new AbortController();
const response = await client.generate("Long prompt", {
  signal: controller.signal,
});

// Cancel request
controller.abort();
```

### 4. Batch Processing with Progress

```javascript
const responses = await client.batchGenerate(prompts, {
  onProgress: (completed, total) => {
    console.log(`Progress: ${completed}/${total}`);
  },
});
```

## 🛠️ Troubleshooting

Common issues and solutions:

1. **Connection Errors**

   ```javascript
   client.on("error", (error) => {
     if (error.code === "ECONNREFUSED") {
       console.error("Server not running");
     }
   });
   ```

2. **Timeout Handling**

   ```javascript
   const client = new LocalLabClient("http://localhost:8000", {
     timeout: 60000,
     retries: 3,
     onTimeout: () => console.log("Request timed out"),
   });
   ```

3. **Memory Management**
   ```javascript
   client.on("memoryWarning", async (usage) => {
     console.log(`High memory usage: ${usage}%`);
     await client.unloadModel();
   });
   ```

## 📚 Additional Resources

- [Error Codes](./errors.md)
- [Best Practices](./best-practices.md)
- [Migration Guide](./migration.md)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Run tests: `npm test`
4. Submit a pull request

## 📝 License

MIT License - see [LICENSE](../../LICENSE) for details.
