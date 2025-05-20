"""
API routes for text generation
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Generator, Tuple, AsyncGenerator
import json
import re

from ..logger import get_logger
from ..logger.logger import get_request_count
from ..core.app import model_manager
from ..config import (
    DEFAULT_SYSTEM_INSTRUCTIONS,
    DEFAULT_MAX_LENGTH,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    get_model_generation_params
)

# Get logger
logger = get_logger("locallab.routes.generate")

# Create router
router = APIRouter(tags=["Generation"])


class GenerationRequest(BaseModel):
    """Request model for text generation"""
    prompt: str
    max_tokens: int = Field(default=DEFAULT_MAX_LENGTH, ge=1, le=32000)
    temperature: float = Field(default=DEFAULT_TEMPERATURE, ge=0.0, le=2.0)
    top_p: float = Field(default=DEFAULT_TOP_P, ge=0.0, le=1.0)
    top_k: int = Field(default=80, ge=1, le=1000)  # Added top_k parameter
    repetition_penalty: float = Field(default=1.15, ge=1.0, le=2.0)  # Added repetition_penalty parameter
    max_time: Optional[float] = Field(default=None, ge=0.0, description="Maximum time in seconds for generation")
    system_prompt: Optional[str] = Field(default=DEFAULT_SYSTEM_INSTRUCTIONS)
    stream: bool = Field(default=False)


class BatchGenerationRequest(BaseModel):
    """Request model for batch text generation"""
    prompts: List[str]
    max_tokens: int = Field(default=DEFAULT_MAX_LENGTH, ge=1, le=32000)
    temperature: float = Field(default=DEFAULT_TEMPERATURE, ge=0.0, le=2.0)
    top_p: float = Field(default=DEFAULT_TOP_P, ge=0.0, le=1.0)
    top_k: int = Field(default=80, ge=1, le=1000)  # Added top_k parameter
    repetition_penalty: float = Field(default=1.15, ge=1.0, le=2.0)  # Added repetition_penalty parameter
    max_time: Optional[float] = Field(default=None, ge=0.0, description="Maximum time in seconds for generation")
    system_prompt: Optional[str] = Field(default=DEFAULT_SYSTEM_INSTRUCTIONS)


class ChatMessage(BaseModel):
    """Message model for chat requests"""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Request model for chat completion"""
    messages: List[ChatMessage]
    max_tokens: int = Field(default=DEFAULT_MAX_LENGTH, ge=1, le=32000)
    temperature: float = Field(default=DEFAULT_TEMPERATURE, ge=0.0, le=2.0)
    top_p: float = Field(default=DEFAULT_TOP_P, ge=0.0, le=1.0)
    top_k: int = Field(default=80, ge=1, le=1000)  # Added top_k parameter
    repetition_penalty: float = Field(default=1.15, ge=1.0, le=2.0)  # Added repetition_penalty parameter
    max_time: Optional[float] = Field(default=None, ge=0.0, description="Maximum time in seconds for generation")
    stream: bool = Field(default=False)


class GenerationResponse(BaseModel):
    """Response model for text generation"""
    text: str
    model: str


class ChatResponse(BaseModel):
    """Response model for chat completion"""
    choices: List[Dict[str, Any]]


class BatchGenerationResponse(BaseModel):
    """Response model for batch text generation"""
    responses: List[str]


def format_chat_messages(messages: List[ChatMessage]) -> str:
    """
    Format a list of chat messages into a prompt string that the model can understand

    Args:
        messages: List of ChatMessage objects with role and content

    Returns:
        Formatted prompt string
    """
    formatted_messages = []

    for msg in messages:
        role = msg.role.strip().lower()

        if role == "system":
            # System messages get special formatting
            formatted_messages.append(f"# System Instruction\n{msg.content}\n")
        elif role == "user":
            formatted_messages.append(f"User: {msg.content}")
        elif role == "assistant":
            formatted_messages.append(f"Assistant: {msg.content}")
        else:
            # Default formatting for other roles
            formatted_messages.append(f"{role.capitalize()}: {msg.content}")

    # Join all messages with newlines
    return "\n\n".join(formatted_messages)


@router.post("/generate", response_model=GenerationResponse)
async def generate_text(request: GenerationRequest) -> GenerationResponse:
    """
    Generate text based on a prompt
    """
    # Check if model is loaded
    if not model_manager.current_model or not model_manager.model:
        raise HTTPException(
            status_code=400,
            detail="No model is currently loaded. Please load a model first using POST /models/load."
        )

    if request.stream:
        # Return a streaming response
        return StreamingResponse(
            generate_stream(request.prompt, request.max_tokens, request.temperature,
                           request.top_p, request.system_prompt, request.max_time),
            media_type="text/event-stream"
        )

    try:
        # Get model-specific generation parameters
        model_params = get_model_generation_params(model_manager.current_model)

        # Update with request parameters and optimized defaults for high-quality responses
        generation_params = {
            "max_new_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p if request.top_p is not None else 0.92,  # Optimized default
            "top_k": request.top_k if request.top_k is not None else 80,  # Optimized default
            "repetition_penalty": request.repetition_penalty if request.repetition_penalty is not None else 1.15,  # Optimized default
            "do_sample": model_params.get("do_sample", True),  # Pass do_sample from model params
            "max_time": request.max_time  # Pass max_time parameter
        }

        # Merge model-specific params with request params
        # This ensures we get the best of both worlds - model-specific optimizations
        # and our high-quality parameters
        generation_params.update(model_params)

        # Generate text with optimized parameters - properly await the async call
        generated_text = await model_manager.generate_text(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            **generation_params
        )

        # Additional cleanup for any special tokens that might have slipped through
        special_token_pattern = r'<\|[a-zA-Z0-9_]+\|>'
        cleaned_text = re.sub(special_token_pattern, '', generated_text)

        # Check for conversation markers and truncate if found
        conversation_end_markers = ["</|assistant|>", "<|user|>", "<|human|>", "<|reserved_special_token"]
        for end_marker in conversation_end_markers:
            if end_marker in cleaned_text:
                # Remove the end marker and everything after it
                marker_pos = cleaned_text.find(end_marker)
                if marker_pos > 0:
                    cleaned_text = cleaned_text[:marker_pos]
                break

        # Check for repetition patterns that indicate the model is stuck
        if len(cleaned_text) > 200:
            # Look for repeating patterns of 20+ characters that repeat 3+ times
            for pattern_len in range(20, 40):
                if pattern_len < len(cleaned_text) // 3:
                    for i in range(len(cleaned_text) - pattern_len * 3):
                        pattern = cleaned_text[i:i+pattern_len]
                        if pattern and not pattern.isspace():
                            if cleaned_text[i:].count(pattern) >= 3:
                                # Found a repeating pattern, truncate at the second occurrence
                                second_pos = cleaned_text.find(pattern, i + pattern_len)
                                if second_pos > 0:
                                    logger.info(f"Detected repetition pattern in text generation, truncating response")
                                    cleaned_text = cleaned_text[:second_pos + pattern_len]
                                    break

        return GenerationResponse(
            text=cleaned_text,
            model=model_manager.current_model
        )
    except Exception as e:
        logger.error(f"Generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat_completion(request: ChatRequest) -> ChatResponse:
    """
    Chat completion API that formats messages into a prompt and returns the response
    """
    if not model_manager.current_model:
        raise HTTPException(status_code=400, detail="No model is currently loaded")

    # Format messages into a prompt
    formatted_prompt = format_chat_messages(request.messages)

    # If streaming is requested, return a streaming response
    if request.stream:
        return StreamingResponse(
            stream_chat(formatted_prompt, request.max_tokens, request.temperature, request.top_p, request.max_time),
            media_type="text/event-stream"
        )

    try:
        # Get model-specific generation parameters
        model_params = get_model_generation_params(model_manager.current_model)

        # Prepare generation parameters with optimized defaults for high-quality responses
        generation_params = {
            "max_new_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p if request.top_p is not None else 0.92,  # Optimized default
            "top_k": request.top_k if request.top_k is not None else 80,  # Optimized default
            "repetition_penalty": request.repetition_penalty if request.repetition_penalty is not None else 1.15,  # Optimized default
            "do_sample": model_params.get("do_sample", True),  # Pass do_sample from model params
            "max_time": request.max_time  # Pass max_time parameter
        }

        # Merge model-specific params with request params
        # This ensures we get the best of both worlds - model-specific optimizations
        # and our high-quality parameters
        generation_params.update(model_params)

        # Generate completion with optimized parameters
        generated_text = await model_manager.generate_text(
            prompt=formatted_prompt,
            **generation_params
        )

        # Additional cleanup for any special tokens that might have slipped through
        special_token_pattern = r'<\|[a-zA-Z0-9_]+\|>'
        cleaned_text = re.sub(special_token_pattern, '', generated_text)

        # Check for conversation markers and truncate if found
        conversation_end_markers = ["</|assistant|>", "<|user|>", "<|human|>", "<|reserved_special_token"]
        for end_marker in conversation_end_markers:
            if end_marker in cleaned_text:
                # Remove the end marker and everything after it
                marker_pos = cleaned_text.find(end_marker)
                if marker_pos > 0:
                    cleaned_text = cleaned_text[:marker_pos]
                break

        # Check for repetition patterns that indicate the model is stuck
        if len(cleaned_text) > 200:
            # Look for repeating patterns of 20+ characters that repeat 3+ times
            for pattern_len in range(20, 40):
                if pattern_len < len(cleaned_text) // 3:
                    for i in range(len(cleaned_text) - pattern_len * 3):
                        pattern = cleaned_text[i:i+pattern_len]
                        if pattern and not pattern.isspace():
                            if cleaned_text[i:].count(pattern) >= 3:
                                # Found a repeating pattern, truncate at the second occurrence
                                second_pos = cleaned_text.find(pattern, i + pattern_len)
                                if second_pos > 0:
                                    logger.info(f"Detected repetition pattern in chat completion, truncating response")
                                    cleaned_text = cleaned_text[:second_pos + pattern_len]
                                    break

        # Format response with cleaned text
        return ChatResponse(
            choices=[{
                "message": {
                    "role": "assistant",
                    "content": cleaned_text
                },
                "index": 0,
                "finish_reason": "stop"
            }]
        )
    except Exception as e:
        logger.error(f"Chat completion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def generate_stream(
    prompt: str,
    max_tokens: int,
    temperature: float,
    top_p: float,
    system_prompt: Optional[str],
    max_time: Optional[float] = None
) -> AsyncGenerator[str, None]:
    """
    Generate text in a streaming fashion and return as server-sent events
    with optimized parameters for high-quality responses
    """
    try:
        # Get model-specific generation parameters
        model_params = get_model_generation_params(model_manager.current_model)

        # Update with request parameters and optimized defaults for high-quality streaming
        generation_params = {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": 80,  # Optimized top_k for high-quality streaming
            "repetition_penalty": 1.15,  # Optimized repetition_penalty for high-quality streaming
            "do_sample": model_params.get("do_sample", True),  # Pass do_sample from model params
            "max_time": max_time  # Pass max_time parameter
        }

        # Merge model-specific params with request params
        # This ensures we get the best of both worlds - model-specific optimizations
        # and our high-quality streaming parameters
        generation_params.update(model_params)

        # Get the stream generator with optimized parameters
        stream_generator = model_manager.generate_stream(
            prompt=prompt,
            system_prompt=system_prompt,
            **generation_params
        )

        # Stream tokens with proper SSE formatting and special token handling
        async for token in stream_generator:
            # Check for error messages
            if token.startswith("\nError:"):
                # Format error as SSE event
                error_msg = token.replace("\n", "\\n")
                yield f"data: [ERROR] {error_msg}\n\n"
                break

            # Clean any special tokens that might have slipped through
            cleaned_token = token

            # Remove any special tokens using regex pattern
            special_token_pattern = r'<\|[a-zA-Z0-9_]+\|>'
            import re
            cleaned_token = re.sub(special_token_pattern, '', cleaned_token)

            # Skip if token is empty after cleaning
            if not cleaned_token or cleaned_token.isspace():
                continue

            # Format as server-sent event
            # Replace newlines with escaped newlines for proper SSE format
            data = cleaned_token.replace("\n", "\\n")
            yield f"data: {data}\n\n"

        # End of stream
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Streaming generation failed: {str(e)}")
        yield f"data: [ERROR] {str(e)}\n\n"


async def stream_chat(
    formatted_prompt: str,
    max_tokens: int,
    temperature: float,
    top_p: float,
    max_time: Optional[float] = None
) -> AsyncGenerator[str, None]:
    """
    Stream chat completion responses as server-sent events
    with optimized parameters for high-quality responses
    """
    try:
        # Get model-specific generation parameters
        model_params = get_model_generation_params(model_manager.current_model)

        # Update with request parameters and optimized defaults for high-quality streaming
        generation_params = {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": 80,  # Optimized top_k for high-quality streaming
            "repetition_penalty": 1.15,  # Optimized repetition_penalty for high-quality streaming
            "do_sample": model_params.get("do_sample", True),  # Pass do_sample from model params
            "max_time": max_time  # Pass max_time parameter
        }

        # Merge model-specific params with request params
        # This ensures we get the best of both worlds - model-specific optimizations
        # and our high-quality streaming parameters
        generation_params.update(model_params)

        # Generate streaming tokens with optimized parameters
        stream_generator = model_manager.generate_stream(
            prompt=formatted_prompt,
            **generation_params
        )

        # Stream tokens with special token handling
        async for token in stream_generator:
            # Check for error messages and pass them through
            if token.startswith("\nError:"):
                yield token
                break

            # Clean any special tokens that might have slipped through
            cleaned_token = token

            # Remove any special tokens using regex pattern
            special_token_pattern = r'<\|[a-zA-Z0-9_]+\|>'
            import re
            cleaned_token = re.sub(special_token_pattern, '', cleaned_token)

            # Skip if token is empty after cleaning
            if not cleaned_token or cleaned_token.isspace():
                continue

            # Stream cleaned tokens
            yield cleaned_token
    except Exception as e:
        logger.error(f"Streaming generation failed: {str(e)}")
        # Return error as plain text
        yield f"\nError: {str(e)}"


@router.post("/generate/batch", response_model=BatchGenerationResponse)
async def batch_generate(request: BatchGenerationRequest) -> BatchGenerationResponse:
    """
    Generate high-quality text for multiple prompts in a single request
    """
    if not model_manager.current_model:
        raise HTTPException(status_code=400, detail="No model is currently loaded")

    try:
        # Get model-specific generation parameters
        model_params = get_model_generation_params(model_manager.current_model)

        # Update with request parameters and optimized defaults for high-quality responses
        generation_params = {
            "max_new_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p if request.top_p is not None else 0.92,  # Optimized default
            "top_k": request.top_k if request.top_k is not None else 80,  # Optimized default
            "repetition_penalty": request.repetition_penalty if request.repetition_penalty is not None else 1.15,  # Optimized default
            "do_sample": model_params.get("do_sample", True),  # Pass do_sample from model params
            "max_time": request.max_time  # Pass max_time parameter
        }

        # Merge model-specific params with request params
        # This ensures we get the best of both worlds - model-specific optimizations
        # and our high-quality parameters
        generation_params.update(model_params)

        responses = []
        for prompt in request.prompts:
            # Generate text with optimized parameters
            generated_text = await model_manager.generate_text(
                prompt=prompt,
                system_prompt=request.system_prompt,
                **generation_params
            )

            # Additional cleanup for any special tokens that might have slipped through
            special_token_pattern = r'<\|[a-zA-Z0-9_]+\|>'
            cleaned_text = re.sub(special_token_pattern, '', generated_text)

            # Check for conversation markers and truncate if found
            conversation_end_markers = ["</|assistant|>", "<|user|>", "<|human|>", "<|reserved_special_token"]
            for end_marker in conversation_end_markers:
                if end_marker in cleaned_text:
                    # Remove the end marker and everything after it
                    marker_pos = cleaned_text.find(end_marker)
                    if marker_pos > 0:
                        cleaned_text = cleaned_text[:marker_pos]
                    break

            # Check for repetition patterns that indicate the model is stuck
            if len(cleaned_text) > 200:
                # Look for repeating patterns of 20+ characters that repeat 3+ times
                for pattern_len in range(20, 40):
                    if pattern_len < len(cleaned_text) // 3:
                        for i in range(len(cleaned_text) - pattern_len * 3):
                            pattern = cleaned_text[i:i+pattern_len]
                            if pattern and not pattern.isspace():
                                if cleaned_text[i:].count(pattern) >= 3:
                                    # Found a repeating pattern, truncate at the second occurrence
                                    second_pos = cleaned_text.find(pattern, i + pattern_len)
                                    if second_pos > 0:
                                        logger.info(f"Detected repetition pattern in batch generation, truncating response")
                                        cleaned_text = cleaned_text[:second_pos + pattern_len]
                                        break

            responses.append(cleaned_text)

        return BatchGenerationResponse(responses=responses)
    except Exception as e:
        logger.error(f"Batch generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
