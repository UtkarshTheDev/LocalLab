import { LocalLabClient } from '../index';
import axios from 'axios';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('LocalLabClient', () => {
  let client: LocalLabClient;

  beforeEach(() => {
    client = new LocalLabClient({
      baseUrl: 'http://localhost:8000',
      apiKey: 'test-key',
    });
    mockedAxios.create.mockReturnValue(mockedAxios);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('generate', () => {
    it('should generate text successfully', async () => {
      const mockResponse = {
        data: {
          response: 'Generated text',
          modelId: 'test-model',
          usage: {
            promptTokens: 10,
            completionTokens: 20,
            totalTokens: 30,
          },
        },
      };

      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      const result = await client.generate('Hello');

      expect(mockedAxios.post).toHaveBeenCalledWith('/generate', {
        prompt: 'Hello',
      });
      expect(result).toEqual(mockResponse.data);
    });

    it('should handle generation with options', async () => {
      const mockResponse = {
        data: {
          response: 'Generated text',
          modelId: 'test-model',
          usage: {
            promptTokens: 10,
            completionTokens: 20,
            totalTokens: 30,
          },
        },
      };

      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      const options = {
        temperature: 0.7,
        maxLength: 100,
      };

      const result = await client.generate('Hello', options);

      expect(mockedAxios.post).toHaveBeenCalledWith('/generate', {
        prompt: 'Hello',
        ...options,
      });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('chat', () => {
    it('should handle chat completion successfully', async () => {
      const mockResponse = {
        data: {
          choices: [
            {
              message: {
                role: 'assistant',
                content: 'Hello! How can I help you?',
              },
              finishReason: 'stop',
            },
          ],
          usage: {
            promptTokens: 10,
            completionTokens: 20,
            totalTokens: 30,
          },
        },
      };

      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      const messages = [
        { role: 'user' as const, content: 'Hello' },
      ];

      const result = await client.chat(messages);

      expect(mockedAxios.post).toHaveBeenCalledWith('/chat', {
        messages,
      });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('models', () => {
    it('should load model successfully', async () => {
      const mockResponse = { status: 200 };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      const result = await client.loadModel('test-model');

      expect(mockedAxios.post).toHaveBeenCalledWith('/models/load', {
        model_id: 'test-model',
      });
      expect(result).toBe(true);
    });

    it('should list models successfully', async () => {
      const mockResponse = {
        data: {
          'model-1': {
            name: 'Model 1',
            vram: 4000,
            ram: 8000,
            maxLength: 2048,
            fallback: null,
            description: 'Test model',
            quantization: 'fp16' as const,
            tags: ['test'],
          },
        },
      };

      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      const result = await client.listModels();

      expect(mockedAxios.get).toHaveBeenCalledWith('/models');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('system', () => {
    it('should get system info successfully', async () => {
      const mockResponse = {
        data: {
          cpuUsage: 50,
          memoryUsage: 60,
          gpuInfo: {
            device: 'nvidia',
            totalMemory: 8000,
            usedMemory: 4000,
            freeMemory: 4000,
            utilization: 50,
          },
          activeModel: 'test-model',
          uptime: 3600,
          requestCount: 100,
        },
      };

      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      const result = await client.getSystemInfo();

      expect(mockedAxios.get).toHaveBeenCalledWith('/system/info');
      expect(result).toEqual(mockResponse.data);
    });

    it('should check health successfully', async () => {
      const mockResponse = { status: 200 };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      const result = await client.healthCheck();

      expect(mockedAxios.get).toHaveBeenCalledWith('/health');
      expect(result).toBe(true);
    });
  });

  describe('error handling', () => {
    it('should handle API errors', async () => {
      const errorMessage = 'API Error';
      mockedAxios.post.mockRejectedValueOnce(new Error(errorMessage));

      await expect(client.generate('Hello')).rejects.toThrow(errorMessage);
    });

    it('should handle health check failures', async () => {
      mockedAxios.get.mockRejectedValueOnce(new Error('Health check failed'));

      const result = await client.healthCheck();
      expect(result).toBe(false);
    });
  });
}); 