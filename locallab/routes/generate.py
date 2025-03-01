"""
API routes for text generation
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Generator, Tuple

from ..logger import get_logger
from ..core.app import model_manager, request_count
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
    system_prompt: Optional[str] = Field(default=DEFAULT_SYSTEM_INSTRUCTIONS)
    stream: bool = Field(default=False)


class BatchGenerationRequest(BaseModel):
    """Request model for batch text generation"""
    prompts: List[str]
    max_tokens: int = Field(default=DEFAULT_MAX_LENGTH, ge=1, le=32000)
    temperature: float = Field(default=DEFAULT_TEMPERATURE, ge=0.0, le=2.0)
    top_p: float = Field(default=DEFAULT_TOP_P, ge=0.0, le=1.0)
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


@router.post("/generate", response_model=GenerationResponse)
async def generate_text(request: GenerationRequest) -> GenerationResponse:
    """
    Generate text based on a prompt
    """
    if not model_manager.current_model:
        raise HTTPException(status_code=400, detail="No model is currently loaded")
    
    if request.stream:
        # Return a streaming response
        return StreamingResponse(
            generate_stream(request.prompt, request.max_tokens, request.temperature, 
                           request.top_p, request.system_prompt),
            media_type="text/event-stream"
        )
    
    try:
        # Get model-specific generation parameters
        model_params = get_model_generation_params(model_manager.current_model)
        
        # Update with request parameters
        generation_params = {
            "max_new_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        
        # Merge model-specific params with request params
        generation_params.update(model_params)
        
        # Generate text
        generated_text = model_manager.generate_text(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            **generation_params
        )
        
        return GenerationResponse(
            text=generated_text,
            model=model_manager.current_model
        )
    except Exception as e:
        logger.error(f"Generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat_completion(request: ChatRequest) -> ChatResponse:
    """Chat completion endpoint similar to OpenAI's API"""
    if not model_manager.current_model:
        raise HTTPException(status_code=400, detail="No model is currently loaded")
    
    try:
        # Format messages into a prompt
        formatted_prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages])
        
        if request.stream:
            # Return a streaming response
            return StreamingResponse(
                stream_chat(formatted_prompt, request.max_tokens, request.temperature, request.top_p),
                media_type="text/event-stream"
            )
        
        # Get model-specific generation parameters
        model_params = get_model_generation_params(model_manager.current_model)
        
        # Update with request parameters
        generation_params = {
            "max_new_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        
        # Merge model-specific params with request params
        generation_params.update(model_params)
        
        # Generate text
        response = model_manager.generate_text(
            prompt=formatted_prompt,
            **generation_params
        )
        
        return ChatResponse(
            choices=[{
                "message": {
                    "role": "assistant",
                    "content": response
                }
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
    system_prompt: Optional[str]
) -> Generator[str, None, None]:
    """Generate text in a streaming fashion"""
    try:
        # Get model-specific generation parameters
        model_params = get_model_generation_params(model_manager.current_model)
        
        # Update with request parameters
        generation_params = {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True
        }
        
        # Merge model-specific params with request params
        generation_params.update(model_params)
        
        for token in model_manager.generate_stream(
            prompt=prompt,
            system_prompt=system_prompt,
            **generation_params
        ):
            # Format as a server-sent event
            yield f"data: {token}\n\n"
        
        # End of stream marker
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Streaming generation failed: {str(e)}")
        yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
        yield "data: [DONE]\n\n"


async def stream_chat(
    formatted_prompt: str,
    max_tokens: int,
    temperature: float,
    top_p: float
) -> Generator[str, None, None]:
    """Stream chat completion tokens"""
    try:
        # Get model-specific generation parameters
        model_params = get_model_generation_params(model_manager.current_model)
        
        # Update with request parameters
        generation_params = {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True
        }
        
        # Merge model-specific params with request params
        generation_params.update(model_params)
        
        for token in model_manager.generate_stream(
            prompt=formatted_prompt,
            **generation_params
        ):
            # Format as a server-sent event with proper JSON structure
            yield f'data: {{"choices": [{{"delta": {{"content": "{token}"}}}}]}}\n\n'
        
        # End of stream marker
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Chat streaming failed: {str(e)}")
        yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
        yield "data: [DONE]\n\n"


@router.post("/generate/batch", response_model=BatchGenerationResponse)
async def batch_generate(request: BatchGenerationRequest) -> BatchGenerationResponse:
    """
    Generate text for multiple prompts in a single request
    """
    if not model_manager.current_model:
        raise HTTPException(status_code=400, detail="No model is currently loaded")
    
    try:
        # Get model-specific generation parameters
        model_params = get_model_generation_params(model_manager.current_model)
        
        # Update with request parameters
        generation_params = {
            "max_new_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        
        # Merge model-specific params with request params
        generation_params.update(model_params)
        
        responses = []
        for prompt in request.prompts:
            generated_text = model_manager.generate_text(
                prompt=prompt,
                system_prompt=request.system_prompt,
                **generation_params
            )
            responses.append(generated_text)
        
        return BatchGenerationResponse(responses=responses)
    except Exception as e:
        logger.error(f"Batch generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 