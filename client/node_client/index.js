const axios = require("axios");

class LocalLabClient {
  /**
   * Initialize the LocalLab client
   * @param {string} baseUrl - The base URL of the LocalLab server
   */
  constructor(baseUrl) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.axios = axios.create({
      baseURL: this.baseUrl,
      timeout: 30000,
    });
  }

  /**
   * Generate text using the model
   * @param {string} prompt - The input prompt
   * @param {Object} options - Generation options
   * @returns {Promise<string>} Generated text
   */
  async generate(prompt, options = {}) {
    try {
      const response = await this.axios.post("/generate", {
        prompt,
        model_id: options.modelId,
        stream: options.stream || false,
        max_length: options.maxLength,
        temperature: options.temperature || 0.7,
        top_p: options.topP || 0.9,
      });

      return response.data.response;
    } catch (error) {
      throw new Error(
        `Generation failed: ${error.response?.data?.detail || error.message}`
      );
    }
  }

  /**
   * Stream text generation
   * @param {string} prompt - The input prompt
   * @param {Object} options - Generation options
   * @returns {AsyncGenerator<string>} Generated text stream
   */
  async *streamGenerate(prompt, options = {}) {
    try {
      const response = await this.axios.post(
        "/generate",
        {
          prompt,
          model_id: options.modelId,
          stream: true,
          max_length: options.maxLength,
          temperature: options.temperature || 0.7,
          top_p: options.topP || 0.9,
        },
        {
          responseType: "stream",
        }
      );

      for await (const chunk of response.data) {
        yield chunk.toString();
      }
    } catch (error) {
      throw new Error(
        `Streaming failed: ${error.response?.data?.detail || error.message}`
      );
    }
  }

  /**
   * Load a specific model
   * @param {string} modelId - The ID of the model to load
   * @returns {Promise<boolean>} Success status
   */
  async loadModel(modelId) {
    try {
      const response = await this.axios.post("/models/load", {
        model_id: modelId,
      });
      return response.data.status === "success";
    } catch (error) {
      throw new Error(
        `Model loading failed: ${error.response?.data?.detail || error.message}`
      );
    }
  }

  /**
   * Get information about the currently loaded model
   * @returns {Promise<Object>} Model information
   */
  async getCurrentModel() {
    try {
      const response = await this.axios.get("/models/current");
      return response.data;
    } catch (error) {
      throw new Error(
        `Failed to get current model: ${
          error.response?.data?.detail || error.message
        }`
      );
    }
  }

  /**
   * List all available models
   * @returns {Promise<Object>} Available models
   */
  async listAvailableModels() {
    try {
      const response = await this.axios.get("/models/available");
      return response.data.models;
    } catch (error) {
      throw new Error(
        `Failed to list models: ${
          error.response?.data?.detail || error.message
        }`
      );
    }
  }

  /**
   * Check if the server is healthy
   * @returns {Promise<boolean>} Health status
   */
  async healthCheck() {
    try {
      const response = await this.axios.get("/health");
      return response.status === 200;
    } catch (error) {
      return false;
    }
  }
}

module.exports = LocalLabClient;

// Example usage:
/*
const client = new LocalLabClient('http://localhost:8000');

// Basic generation
client.generate('Tell me a story')
    .then(response => console.log(response))
    .catch(error => console.error(error));

// Streaming generation
(async () => {
    try {
        for await (const token of client.streamGenerate('Once upon a time')) {
            process.stdout.write(token);
        }
    } catch (error) {
        console.error(error);
    }
})();
*/
