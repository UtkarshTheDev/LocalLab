#!/bin/bash

# Test script for LocalLab server endpoints
# Usage: ./test_endpoints.sh <server_url>
# Example: ./test_endpoints.sh "https://your-ngrok-url.ngrok-free.app"

SERVER_URL=$1

if [ -z "$SERVER_URL" ]; then
    echo "Please provide the server URL as an argument"
    echo "Usage: ./test_endpoints.sh <server_url>"
    exit 1
fi

echo "Testing LocalLab server at: $SERVER_URL"
echo "----------------------------------------"

# Health Check
echo "\nTesting /health endpoint..."
curl -s "$SERVER_URL/health"

# System Info
echo "\nTesting /system/info endpoint..."
curl -s "$SERVER_URL/system/info"

# Get Current Model
echo "\nTesting /models/current endpoint..."
curl -s "$SERVER_URL/models/current"

# List Available Models
echo "\nTesting /models/available endpoint..."
curl -s "$SERVER_URL/models/available"

# Test Text Generation
echo "\nTesting /generate endpoint..."
curl -X POST "$SERVER_URL/generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Hello!", "stream": false}'

# Test Streaming Generation
echo "\nTesting /generate streaming..."
curl -X POST "$SERVER_URL/generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Tell me a story", "stream": true}'

# Test Chat Completion
echo "\nTesting /chat endpoint..."
curl -X POST "$SERVER_URL/chat" \
    -H "Content-Type: application/json" \
    -d '{
        "messages": [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hi, how are you?"}
        ],
        "stream": false
    }'

# Test Batch Generation
echo "\nTesting /generate/batch endpoint..."
curl -X POST "$SERVER_URL/generate/batch" \
    -H "Content-Type: application/json" \
    -d '{
        "prompts": [
            "What is 2+2?",
            "Who is Shakespeare?"
        ]
    }'

# Test Loading Model
echo "\nTesting /models/load endpoint..."
curl -X POST "$SERVER_URL/models/load" \
    -H "Content-Type: application/json" \
    -d '{"model_id": "microsoft/phi-2"}'

# Test System Instructions
echo "\nTesting /system/instructions endpoint..."
curl -X POST "$SERVER_URL/system/instructions" \
    -H "Content-Type: application/json" \
    -d '{"instructions": "You are a helpful AI assistant"}'

# Test Unloading Model
echo "\nTesting /models/unload endpoint..."
curl -X POST "$SERVER_URL/models/unload"

echo "\nAll tests completed!"
