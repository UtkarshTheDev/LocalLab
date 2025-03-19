#!/usr/bin/env zsh

# Test script for LocalLab server endpoints (ZSH version)
# Usage: ./test_endpoints.zsh <server_url>
# Example: ./test_endpoints.zsh "https://your-ngrok-url.ngrok-free.app"

# Colors
autoload -U colors && colors
GREEN=$fg[green]
RED=$fg[red]
BLUE=$fg[blue]
RESET=$reset_color

SERVER_URL=$1

if [[ -z "$SERVER_URL" ]]; then
    print "${RED}Please provide the server URL as an argument${RESET}"
    print "Usage: ./test_endpoints.zsh <server_url>"
    exit 1
fi

print "${BLUE}Testing LocalLab server at: $SERVER_URL${RESET}"
print "----------------------------------------"

function test_endpoint() {
    local endpoint=$1
    local method=${2:-GET}
    local data=$3
    
    print "\n${GREEN}Testing $endpoint endpoint...${RESET}"
    if [[ -n "$data" ]]; then
        curl -s -X $method "$SERVER_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X $method "$SERVER_URL$endpoint"
    fi
}

# Health Check
test_endpoint "/health"

# System Info
test_endpoint "/system/info"

# Get Current Model
test_endpoint "/models/current"

# List Available Models
test_endpoint "/models/available"

# Test Text Generation
test_endpoint "/generate" "POST" '{
    "prompt": "Hello! Tell me about React Native.",
    "stream": false
}'

# Test Streaming Generation
test_endpoint "/generate" "POST" '{
    "prompt": "Create a professional X post for any topics which you want.",
    "stream": true
}'

# Test Chat Completion
test_endpoint "/chat" "POST" '{
    "messages": [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hi, how are you?, Create a perfect X post for the Topic about Expo and React Native and tell difference btw them."}
    ],
    "stream": false
}'

# Test Batch Generation
test_endpoint "/generate/batch" "POST" '{
    "prompts": [
        "What is 2+2?",
        "Who is Linus Torwalds?"
    ]
}'

# Test Loading Model
test_endpoint "/models/load" "POST" '{
    "model_id": "microsoft/phi-2"
}'

# Test System Instructions
test_endpoint "/system/instructions" "POST" '{
    "instructions": "You are a helpful AI assistant"
}'

# Test Unloading Model
test_endpoint "/models/unload" "POST"

print "\n${GREEN}All tests completed!${RESET}"
