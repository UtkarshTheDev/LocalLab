export interface LocalLabConfig {
  baseUrl: string;
  apiKey?: string;
  timeout?: number;
  retries?: number;
  headers?: Record<string, string>;
}

export interface GenerateOptions {
  modelId?: string;
  maxLength?: number;
  temperature?: number;
  topP?: number;
  stream?: boolean;
}

export interface GenerateResponse {
  response: string;
  modelId: string;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ChatResponse {
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

export interface BatchRequest {
  prompts: string[];
  modelId?: string;
  maxLength?: number;
  temperature?: number;
  topP?: number;
}

export interface BatchResponse {
  responses: string[];
  modelId: string;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

export interface ModelInfo {
  name: string;
  vram: number;
  ram: number;
  maxLength: number;
  fallback: string | null;
  description: string;
  quantization: "fp16" | "int8" | "int4" | null;
  tags: string[];
}

export interface SystemInfo {
  cpuUsage: number;
  memoryUsage: number;
  gpuInfo?: {
    device: string;
    totalMemory: number;
    usedMemory: number;
    freeMemory: number;
    utilization: number;
  };
  activeModel?: string;
  uptime: number;
  requestCount: number;
} 