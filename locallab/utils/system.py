"""
System utilities for LocalLab
"""

import os
import psutil
import shutil
import socket
import platform
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
from typing import Optional, Tuple, Dict, Any, List

from ..logger import get_logger
from ..config import MIN_FREE_MEMORY

# Get logger
logger = get_logger("locallab.utils.system")


def get_system_memory() -> Tuple[int, int]:
    """Get system memory information in MB"""
    vm = psutil.virtual_memory()
    total_memory = vm.total // (1024 * 1024)  # Convert to MB
    free_memory = vm.available // (1024 * 1024)  # Convert to MB
    return total_memory, free_memory


def get_gpu_memory() -> Optional[Tuple[int, int]]:
    """Get GPU memory information in MB if available"""
    if not TORCH_AVAILABLE or not torch.cuda.is_available():
        return None
    
    # First try nvidia-ml-py3 (nvidia_smi)
    try:
        import nvidia_smi
        nvidia_smi.nvmlInit()
        handle = nvidia_smi.nvmlDeviceGetHandleByIndex(0)
        info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
        
        total_memory = info.total // (1024 * 1024)  # Convert to MB
        free_memory = info.free // (1024 * 1024)  # Convert to MB
        
        nvidia_smi.nvmlShutdown()
        return total_memory, free_memory
    except ImportError:
        # If nvidia_smi not available, log at debug level to avoid noise
        logger.debug("nvidia-ml-py3 not installed, falling back to torch for GPU info")
        # Fall back to torch for basic info
        try:
            # Get basic info from torch
            device = torch.cuda.current_device()
            total_memory = torch.cuda.get_device_properties(device).total_memory // (1024 * 1024)
            # Note: torch doesn't provide free memory info easily, so we estimate
            # by allocating a tensor and seeing what's available
            torch.cuda.empty_cache()
            free_memory = total_memory  # Optimistic starting point
            
            # Rough estimate - we can't get exact free memory from torch easily
            return total_memory, free_memory
        except Exception as torch_error:
            logger.debug(f"Torch GPU memory check also failed: {str(torch_error)}")
            return None
    except Exception as e:
        logger.debug(f"Failed to get detailed GPU memory info: {str(e)}")
        # Fall back to torch for basic info (same as ImportError case)
        try:
            device = torch.cuda.current_device()
            total_memory = torch.cuda.get_device_properties(device).total_memory // (1024 * 1024)
            torch.cuda.empty_cache()
            free_memory = total_memory  # Optimistic estimate
            return total_memory, free_memory
        except Exception:
            return None


def check_resource_availability(required_memory: int) -> bool:
    """Check if system has enough resources for the requested operation"""
    _, free_memory = get_system_memory()
    
    # Check system memory
    if free_memory < MIN_FREE_MEMORY:
        logger.warning(f"Low system memory: {free_memory}MB available")
        return False
    
    # If GPU is available, check GPU memory
    if TORCH_AVAILABLE and torch.cuda.is_available():
        gpu_memory = get_gpu_memory()
        if gpu_memory:
            total_gpu, free_gpu = gpu_memory
            if free_gpu < required_memory:
                logger.warning(f"Insufficient GPU memory: {free_gpu}MB available, {required_memory}MB required")
                return False
    
    return True


def get_device() -> str:
    """Get the device to use for computations."""
    if TORCH_AVAILABLE and torch.cuda.is_available():
        return "cuda"
    else:
        return "cpu"


def format_model_size(size_in_bytes: int) -> str:
    """Format model size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} TB"


def get_system_resources() -> Dict[str, Any]:
    """Get system resource information"""
    resources = {
        'cpu_count': psutil.cpu_count(),
        'cpu_usage': psutil.cpu_percent(),
        'ram_total': psutil.virtual_memory().total,  # in bytes
        'ram_available': psutil.virtual_memory().available,  # in bytes
        'ram_gb': psutil.virtual_memory().total / (1024 * 1024 * 1024),  # in GB
        'memory_usage': psutil.virtual_memory().percent,
        'gpu_available': False,
        'gpu_info': []
    }
    
    # Update GPU availability only if torch is available
    if TORCH_AVAILABLE:
        resources['gpu_available'] = torch.cuda.is_available()
        if resources['gpu_available']:
            gpu_count = torch.cuda.device_count()
            for i in range(gpu_count):
                gpu_mem = get_gpu_memory()
                if gpu_mem:
                    total_mem, free_mem = gpu_mem
                    resources['gpu_info'].append({
                        'name': torch.cuda.get_device_name(i),
                        'total_memory': total_mem,  # in MB
                        'free_memory': free_mem,  # in MB
                        'total_memory_gb': total_mem / 1024  # in GB
                    })
    
    return resources


def get_cpu_info() -> Dict[str, Any]:
    """Get information about the CPU."""
    return {
        "cores": psutil.cpu_count(logical=False),
        "threads": psutil.cpu_count(logical=True),
        "usage": psutil.cpu_percent(interval=0.1)
    }


def get_gpu_info() -> List[Dict[str, Any]]:
    """Get detailed information about all available GPUs.
    
    Returns:
        List of dictionaries with GPU information including name, memory, 
        utilization, and temperature if available
    """
    gpu_info = []
    
    if not TORCH_AVAILABLE or not torch.cuda.is_available():
        return gpu_info
    
    try:
        # Get basic CUDA information
        device_count = torch.cuda.device_count()
        
        for i in range(device_count):
            gpu_data = {
                "index": i,
                "name": torch.cuda.get_device_name(i),
                "total_memory_mb": round(torch.cuda.get_device_properties(i).total_memory / (1024 * 1024))
            }
            
            # Try to get more detailed info with pynvml
            try:
                import pynvml
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                # Memory info
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_data.update({
                    "memory_free_mb": round(mem_info.free / (1024 * 1024)),
                    "memory_used_mb": round(mem_info.used / (1024 * 1024)),
                    "memory_percent": round((mem_info.used / mem_info.total) * 100, 1)
                })
                
                # Utilization info
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_data.update({
                        "gpu_utilization": util.gpu,
                        "memory_utilization": util.memory
                    })
                except:
                    pass
                
                # Temperature
                try:
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    gpu_data["temperature"] = temp
                except:
                    pass
                    
                # Power usage
                try:
                    power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # convert from mW to W
                    gpu_data["power_usage_watts"] = round(power, 2)
                except:
                    pass
                    
            except (ImportError, Exception) as e:
                # If pynvml fails, we still have basic torch.cuda info
                gpu_data["available_memory_mb"] = round(torch.cuda.get_device_properties(i).total_memory / (1024 * 1024) - 
                                               torch.cuda.memory_allocated(i) / (1024 * 1024))
                gpu_data["used_memory_mb"] = round(torch.cuda.memory_allocated(i) / (1024 * 1024))
            
            gpu_info.append(gpu_data)
            
    except Exception as e:
        import logging
        logging.warning(f"Error getting GPU info: {str(e)}")
        
    return gpu_info


def get_memory_info() -> Dict[str, Any]:
    """Get information about the system memory."""
    mem = psutil.virtual_memory()
    return {
        "total": mem.total,
        "available": mem.available,
        "used": mem.used,
        "percent": mem.percent
    }


# Add this function for backward compatibility
def get_system_info() -> Dict[str, Any]:
    """Get system resource information (alias for get_system_resources)"""
    return get_system_resources() 