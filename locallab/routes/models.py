"""
API routes for model management
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import time
import asyncio

from ..logger import get_logger
from ..core.app import model_manager
from ..config import MODEL_REGISTRY

# Get logger
logger = get_logger("locallab.routes.models")

# Create router
router = APIRouter(tags=["Models"], prefix="/models")


class ModelResponse(BaseModel):
    """Response model for the current model info"""
    id: str
    name: str
    is_loaded: bool
    loading_progress: Optional[float] = None


class ModelsListResponse(BaseModel):
    """Response model for the list of available models"""
    models: List[Dict[str, Any]]
    current_model: Optional[str] = None


@router.get("", response_model=ModelsListResponse)
async def list_models() -> ModelsListResponse:
    """List all available models"""
    models_list = []
    for model_id, model_info in MODEL_REGISTRY.items():
        models_list.append({
            "id": model_id,
            "name": model_info.get("name", model_id),
            "can_load": model_info.get("can_load", True),
            "description": model_info.get("description", ""),
            "is_loaded": model_manager.is_model_loaded(model_id)
        })
    
    return ModelsListResponse(
        models=models_list,
        current_model=model_manager.current_model
    )


@router.get("/available", response_model=ModelsListResponse)
async def available_models() -> ModelsListResponse:
    """List all available models (alternative endpoint)"""
    # This endpoint exists to provide compatibility with different API patterns
    return await list_models()


@router.get("/current", response_model=ModelResponse)
async def get_current_model() -> ModelResponse:
    """Get information about the currently loaded model"""
    if not model_manager.current_model:
        raise HTTPException(status_code=404, detail="No model currently loaded")
    
    model_id = model_manager.current_model
    model_info = MODEL_REGISTRY.get(model_id, {})
    
    return ModelResponse(
        id=model_id,
        name=model_info.get("name", model_id),
        is_loaded=True,
        loading_progress=1.0
    )


@router.post("/load/{model_id}", response_model=Dict[str, str])
async def load_model(model_id: str, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Load a specific model"""
    if model_id not in MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    # Check if the model is already loaded
    if model_manager.current_model == model_id and model_manager.is_model_loaded(model_id):
        return {"status": "success", "message": f"Model {model_id} is already loaded"}
    
    try:
        # Load model in background
        background_tasks.add_task(model_manager.load_model, model_id)
        return {"status": "loading", "message": f"Model {model_id} loading started in background"}
    except Exception as e:
        logger.error(f"Failed to load model {model_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class LoadModelRequest(BaseModel):
    """Request model for loading a model with JSON body"""
    model_id: str


@router.post("/load", response_model=Dict[str, str])
async def load_model_from_body(request: LoadModelRequest, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Load a specific model using model_id from request body"""
    model_id = request.model_id
    if model_id not in MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    # Check if the model is already loaded
    if model_manager.current_model == model_id and model_manager.is_model_loaded(model_id):
        return {"status": "success", "message": f"Model {model_id} is already loaded"}
    
    try:
        # Load model in background
        background_tasks.add_task(model_manager.load_model, model_id)
        return {"status": "loading", "message": f"Model {model_id} loading started in background"}
    except Exception as e:
        logger.error(f"Failed to load model {model_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unload", response_model=Dict[str, str])
async def unload_model() -> Dict[str, str]:
    """Unload the current model to free up resources"""
    if not model_manager.current_model:
        return {"status": "success", "message": "No model is currently loaded"}
    
    try:
        model_id = model_manager.current_model
        model_manager.unload_model()
        return {"status": "success", "message": f"Model {model_id} unloaded successfully"}
    except Exception as e:
        logger.error(f"Failed to unload model: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{model_id}", response_model=ModelResponse)
async def get_model_status(model_id: str) -> ModelResponse:
    """Get the loading status of a specific model"""
    if model_id not in MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    model_info = MODEL_REGISTRY.get(model_id, {})
    is_loaded = model_manager.is_model_loaded(model_id)
    
    # If this is the current model and it's loaded or loading
    if model_manager.current_model == model_id:
        return ModelResponse(
            id=model_id,
            name=model_info.get("name", model_id),
            is_loaded=is_loaded,
            loading_progress=1.0 if is_loaded else 0.5  # Approximation if loading
        )
    else:
        return ModelResponse(
            id=model_id,
            name=model_info.get("name", model_id),
            is_loaded=False,
            loading_progress=0.0
        ) 