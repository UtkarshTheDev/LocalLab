import { LocalLabClient } from '../src';

async function main() {
  // Initialize client
  const client = new LocalLabClient({
    baseUrl: 'http://localhost:8000',
    apiKey: process.env.LOCALLAB_API_KEY,
  });

  try {
    // Check health
    const isHealthy = await client.healthCheck();
    console.log('Server health:', isHealthy);

    // List available models
    const models = await client.listModels();
    console.log('Available models:', Object.keys(models));

    // Load a model
    await client.loadModel('mistral-7b');
    console.log('Loaded model: mistral-7b');

    // Basic generation
    const response = await client.generate('Hello, how are you?');
    console.log('Generated response:', response.response);

    // Chat completion
    const chatResponse = await client.chat([
      { role: 'user', content: 'What is the capital of France?' },
    ]);
    console.log('Chat response:', chatResponse.choices[0].message.content);

    // Streaming generation
    console.log('\nStreaming response:');
    for await (const token of client.streamGenerate('Tell me a story')) {
      process.stdout.write(token);
    }
    console.log('\n');

    // Batch processing
    const batchResponse = await client.batchGenerate([
      'What is 2+2?',
      'Who wrote Romeo and Juliet?',
      'What is the speed of light?',
    ]);
    console.log('Batch responses:', batchResponse.responses);

    // System information
    const systemInfo = await client.getSystemInfo();
    console.log('System info:', systemInfo);

  } catch (error) {
    console.error('Error:', error);
  } finally {
    // Clean up
    await client.close();
  }
}

// Run the example
main().catch(console.error); 