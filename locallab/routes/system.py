"""
API routes for system information and server health
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, List, Any, Optional, Tuple
import time
import psutil
import torch
import platform
from datetime import datetime

from ..logger import get_logger
from ..logger.logger import get_request_count, get_uptime_seconds
from ..core.app import model_manager, start_time
from ..ui.banners import print_system_resources
from ..config import system_instructions
from ..utils.system import get_gpu_info as utils_get_gpu_info
from ..utils.networking import get_public_ip, get_network_interfaces

# Get logger
logger = get_logger("locallab.routes.system")

# Create router
router = APIRouter(tags=["System"])


class SystemInfoResponse(BaseModel):
    """Response model for system information"""
    cpu_usage: float
    memory_usage: float
    gpu_info: Optional[List[Dict[str, Any]]] = None
    active_model: Optional[str] = None
    uptime: float
    request_count: int


class SystemInstructionsRequest(BaseModel):
    """Request model for updating system instructions"""
    instructions: str
    model_id: Optional[str] = None


class SystemResourcesResponse(BaseModel):
    """Response model for system resources"""
    cpu: Dict[str, Any]
    memory: Dict[str, Any]
    gpu: Optional[List[Dict[str, Any]]] = None
    disk: Dict[str, Any]
    platform: str
    server_uptime: float
    api_requests: int


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
async def get_system_info():
    """Get system information including CPU, memory, GPU usage, and server stats"""
    try:
        # Get CPU and memory usage
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Get GPU info if available
        gpu_info = utils_get_gpu_info() if torch.cuda.is_available() else None
        
        # Get server stats
        uptime = time.time() - start_time
        
        # Return combined info
        return SystemInfoResponse(
            cpu_usage=cpu_percent,
            memory_usage=memory_percent,
            gpu_info=gpu_info,
            active_model=model_manager.current_model,
            uptime=uptime,
            request_count=get_request_count()  # Use the function from logger.logger instead
        )
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting system info: {str(e)}")


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


@router.get("/resources", response_model=SystemResourcesResponse)
async def get_system_resources() -> SystemResourcesResponse:
    """Get system resource information"""
    disk = psutil.disk_usage('/')
    uptime = time.time() - start_time
    
    # Get detailed GPU information
    gpu_info = utils_get_gpu_info()
    
    return SystemResourcesResponse(
        cpu={
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
            "usage": psutil.cpu_percent(interval=0.1),
            "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else None
        },
        memory={
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "used": psutil.virtual_memory().used,
            "percent": psutil.virtual_memory().percent
        },
        gpu=gpu_info,
        disk={
            "total": disk.total,
            "free": disk.free,
            "used": disk.used,
            "percent": disk.percent
        },
        platform=platform.platform(),
        server_uptime=uptime,
        api_requests=get_request_count()
    )


@router.get("/network", response_model=Dict[str, Any])
async def get_network_info() -> Dict[str, Any]:
    """Get network information"""
    try:
        public_ip = await get_public_ip()
    except:
        public_ip = "Unknown"
        
    return {
        "public_ip": public_ip,
        "hostname": platform.node(),
        "interfaces": get_network_interfaces()
    }


def get_system_resources() -> Dict[str, Any]:
    """Get system resource information"""
    try:
        import torch
        torch_available = True
    except ImportError:
        torch_available = False
    
    # Get memory information
    virtual_memory = psutil.virtual_memory()
    ram_gb = virtual_memory.total / 1024 / 1024 / 1024
    ram_available_gb = virtual_memory.available / 1024 / 1024 / 1024
    
    resources = {
        "ram_gb": ram_gb,
        "ram_available_gb": ram_available_gb, 
        "ram_used_percent": virtual_memory.percent,
        "cpu_count": psutil.cpu_count(),
        "cpu_usage": psutil.cpu_percent(interval=0.1),
        "gpu_available": torch_available and torch.cuda.is_available() if torch_available else False,
        "gpu_info": []
    }
    
    # Use the new gpu_info function from utils.system for more detailed GPU info
    if resources['gpu_available']:
        resources['gpu_info'] = utils_get_gpu_info()
    
    return resources