import os
import psutil
import torch
from typing import Optional, Tuple
from .logger import logger
from .config import MIN_FREE_MEMORY

def get_system_memory() -> Tuple[int, int]:
    """Get system memory information in MB"""
    vm = psutil.virtual_memory()
    total_memory = vm.total // (1024 * 1024)  # Convert to MB
    free_memory = vm.available // (1024 * 1024)  # Convert to MB
    return total_memory, free_memory

def get_gpu_memory() -> Optional[Tuple[int, int]]:
    """Get GPU memory information in MB if available"""
    if not torch.cuda.is_available():
        return None
    
    try:
        import nvidia_smi
        nvidia_smi.nvmlInit()
        handle = nvidia_smi.nvmlDeviceGetHandleByIndex(0)
        info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
        
        total_memory = info.total // (1024 * 1024)  # Convert to MB
        free_memory = info.free // (1024 * 1024)  # Convert to MB
        
        nvidia_smi.nvmlShutdown()
        return total_memory, free_memory
    except Exception as e:
        logger.warning(f"Failed to get GPU memory info: {str(e)}")
        return None

def check_resource_availability(required_memory: int) -> bool:
    """Check if system has enough resources for the requested operation"""
    _, free_memory = get_system_memory()
    
    # Check system memory
    if free_memory < MIN_FREE_MEMORY:
        logger.warning(f"Low system memory: {free_memory}MB available")
        return False
    
    # If GPU is available, check GPU memory
    if torch.cuda.is_available():
        gpu_memory = get_gpu_memory()
        if gpu_memory:
            total_gpu, free_gpu = gpu_memory
            if free_gpu < required_memory:
                logger.warning(f"Insufficient GPU memory: {free_gpu}MB available, {required_memory}MB required")
                return False
    
    return True

def get_device() -> torch.device:
    """Get the best available device for computation"""
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")

def format_model_size(size_in_bytes: int) -> str:
    """Format model size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} TB"
