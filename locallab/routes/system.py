"""
API routes for system information and server health
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, List, Any, Optional, Tuple
import time
import psutil
import torch

from ..logger import get_logger
from ..core.app import model_manager, request_count, start_time
from ..ui.banners import print_system_resources
from ..config import system_instructions

# Get logger
logger = get_logger("locallab.routes.system")

# Create router
router = APIRouter(tags=["System"])


class SystemInfoResponse(BaseModel):
    """Response model for system information"""
    cpu_usage: float
    memory_usage: float
    gpu_info: Optional[Dict[str, Any]] = None
    active_model: Optional[str] = None
    uptime: float
    request_count: int


class SystemInstructionsRequest(BaseModel):
    """Request model for updating system instructions"""
    instructions: str
    model_id: Optional[str] = None


def get_gpu_memory() -> Optional[Tuple[int, int]]:
    """Get GPU memory info in MB"""
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return (info.total // 1024 // 1024, info.free // 1024 // 1024)
    except Exception as e:
        logger.debug(f"Failed to get GPU memory: {str(e)}")
        return None


@router.post("/system/instructions")
async def update_system_instructions(request: SystemInstructionsRequest) -> Dict[str, str]:
    """Update system instructions"""
    try:
        if request.model_id:
            system_instructions.set_model_instructions(request.model_id, request.instructions)
            return {"message": f"Updated system instructions for model {request.model_id}"}
        else:
            system_instructions.set_global_instructions(request.instructions)
            return {"message": "Updated global system instructions"}
    except Exception as e:
        logger.error(f"Failed to update system instructions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/instructions")
async def get_system_instructions(model_id: Optional[str] = None) -> Dict[str, Any]:
    """Get current system instructions"""
    return {
        "instructions": system_instructions.get_instructions(model_id),
        "model_id": model_id if model_id else "global"
    }


@router.post("/system/instructions/reset")
async def reset_system_instructions(model_id: Optional[str] = None) -> Dict[str, str]:
    """Reset system instructions to default"""
    system_instructions.reset_instructions(model_id)
    return {
        "message": f"Reset system instructions for {'model ' + model_id if model_id else 'all models'}"
    }


@router.get("/system/info", response_model=SystemInfoResponse)
async def system_info() -> SystemInfoResponse:
    """Get detailed system information"""
    try:
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        gpu_info = None
        
        if torch.cuda.is_available():
            gpu_mem = get_gpu_memory()
            if gpu_mem:
                total_gpu, free_gpu = gpu_mem
                gpu_info = {
                    "total_memory": total_gpu,
                    "free_memory": free_gpu,
                    "used_memory": total_gpu - free_gpu,
                    "device": torch.cuda.get_device_name(0)
                }
        
        return SystemInfoResponse(
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            gpu_info=gpu_info,
            active_model=model_manager.current_model,
            uptime=time.time() - start_time,
            request_count=request_count
        )
    except Exception as e:
        logger.error(f"Failed to get system info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy"}


@router.get("/startup-status")
async def startup_status() -> Dict[str, Any]:
    """Get detailed startup status including model loading progress"""
    return {
        "server_ready": True,
        "model_loading": model_manager.is_loading() if hasattr(model_manager, "is_loading") else False,
        "current_model": model_manager.current_model,
        "uptime": time.time() - start_time
    }


@router.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with basic server information"""
    from .. import __version__
    
    # Get system resources
    resources = get_system_resources()
    
    # Print system resources to console
    print_system_resources(resources)
    
    # Return server info
    return {
        "name": "LocalLab",
        "version": __version__,
        "status": "running",
        "model": model_manager.current_model,
        "uptime": time.time() - start_time,
        "resources": resources
    }


def get_system_resources() -> Dict[str, Any]:
    """Get system resource information"""
    resources = {
        "ram_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
        "cpu_count": psutil.cpu_count(),
        "gpu_available": torch.cuda.is_available(),
        "gpu_info": []
    }
    
    if resources['gpu_available']:
        gpu_count = torch.cuda.device_count()
        for i in range(gpu_count):
            gpu_mem = get_gpu_memory()
            if gpu_mem:
                total_mem, _ = gpu_mem
                resources['gpu_info'].append({
                    'name': torch.cuda.get_device_name(i),
                    'total_memory': total_mem
                })
    
    return resources 