import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { createParser } from 'eventsource-parser';
import WebSocket from 'ws';
import { 
  LocalLabConfig,
  GenerateOptions,
  GenerateResponse,
  ChatMessage,
  ChatResponse,
  ModelInfo,
  SystemInfo,
  BatchRequest,
  BatchResponse
} from './types';

export class LocalLabClient {
  private client: AxiosInstance;
  private baseUrl: string;
  private ws: WebSocket | null = null;

  constructor(config: LocalLabConfig) {
    this.baseUrl = config.baseUrl;
    this.client = axios.create({
      baseURL: config.baseUrl,
      timeout: config.timeout || 30000,
      headers: {
        ...config.headers,
        'Authorization': config.apiKey ? `Bearer ${config.apiKey}` : undefined,
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Generate text from a prompt
   */
  async generate(prompt: string, options: GenerateOptions = {}): Promise<GenerateResponse> {
    const response = await this.client.post<GenerateResponse>('/generate', {
      prompt,
      ...options,
    });
    return response.data;
  }

  /**
   * Stream generate text from a prompt
   */
  async *streamGenerate(prompt: string, options: GenerateOptions = {}): AsyncGenerator<string> {
    const response = await this.client.post('/generate/stream', {
      prompt,
      ...options,
      stream: true,
    }, {
      responseType: 'stream',
    });

    const parser = createParser((event) => {
      if (event.type === 'event' && event.data) {
        try {
          const data = JSON.parse(event.data);
          return data.response;
        } catch (e) {
          return event.data;
        }
      }
    });

    for await (const chunk of response.data) {
      const text = chunk.toString();
      parser.feed(text);
      if (text.trim()) {
        yield text;
      }
    }
  }

  /**
   * Chat completion with messages
   */
  async chat(messages: ChatMessage[], options: GenerateOptions = {}): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>('/chat', {
      messages,
      ...options,
    });
    return response.data;
  }

  /**
   * Stream chat completion
   */
  async *streamChat(messages: ChatMessage[], options: GenerateOptions = {}): AsyncGenerator<ChatMessage> {
    const response = await this.client.post('/chat/stream', {
      messages,
      ...options,
      stream: true,
    }, {
      responseType: 'stream',
    });

    const parser = createParser((event) => {
      if (event.type === 'event' && event.data) {
        try {
          return JSON.parse(event.data);
        } catch (e) {
          return null;
        }
      }
    });

    for await (const chunk of response.data) {
      const text = chunk.toString();
      const message = parser.feed(text);
      if (message) {
        yield message;
      }
    }
  }

  /**
   * Batch generate text from multiple prompts
   */
  async batchGenerate(prompts: string[], options: GenerateOptions = {}): Promise<BatchResponse> {
    const response = await this.client.post<BatchResponse>('/generate/batch', {
      prompts,
      ...options,
    });
    return response.data;
  }

  /**
   * Load a specific model
   */
  async loadModel(modelId: string, options: Record<string, any> = {}): Promise<boolean> {
    const response = await this.client.post('/models/load', {
      model_id: modelId,
      ...options,
    });
    return response.status === 200;
  }

  /**
   * Get information about the current model
   */
  async getCurrentModel(): Promise<ModelInfo> {
    const response = await this.client.get<ModelInfo>('/models/current');
    return response.data;
  }

  /**
   * List all available models
   */
  async listModels(): Promise<Record<string, ModelInfo>> {
    const response = await this.client.get<Record<string, ModelInfo>>('/models');
    return response.data;
  }

  /**
   * Get system information
   */
  async getSystemInfo(): Promise<SystemInfo> {
    const response = await this.client.get<SystemInfo>('/system/info');
    return response.data;
  }

  /**
   * Check system health
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.client.get('/health');
      return response.status === 200;
    } catch (error) {
      return false;
    }
  }

  /**
   * Connect to WebSocket for real-time updates
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(`ws://${this.baseUrl.replace(/^https?:\/\//, '')}/ws`);
      
      this.ws.on('open', () => {
        resolve();
      });

      this.ws.on('error', (error) => {
        reject(error);
      });
    });
  }

  /**
   * Disconnect WebSocket
   */
  async disconnect(): Promise<void> {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Subscribe to WebSocket events
   */
  onMessage(callback: (data: any) => void): void {
    if (this.ws) {
      this.ws.on('message', (data) => {
        try {
          const parsed = JSON.parse(data.toString());
          callback(parsed);
        } catch (error) {
          callback(data);
        }
      });
    }
  }

  /**
   * Close the client and clean up resources
   */
  async close(): Promise<void> {
    await this.disconnect();
  }
}

// Export types
export * from './types'; 