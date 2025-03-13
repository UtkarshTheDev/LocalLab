import os
import json
from typing import Dict, Any, Optional, List, Type
import torch
import psutil
from huggingface_hub import model_info, HfApi
import logging
from pathlib import Path
import click


def get_env_var(key: str, *, default: Any = None, var_type: Type = str) -> Any:
    """Get environment variable with type conversion and validation.

    Args:
        key: Environment variable key
        default: Default value if not found
        var_type: Type to convert to (str, int, float, bool)

    Returns:
        Converted and validated value
    """
    # First check environment variables
    value = os.environ.get(key)
    
    # If not found in environment, try the config file
    if value is None:
        try:
            # Import here to avoid circular imports
            from .cli.config import get_config_value
            # Convert key format: LOCALLAB_ENABLE_QUANTIZATION -> enable_quantization
            if key.startswith("LOCALLAB_"):
                config_key = key[9:].lower()
            else:
                config_key = key.lower()
            
            config_value = get_config_value(config_key)
            if config_value is not None:
                value = config_value
        except (ImportError, ModuleNotFoundError):
            # If the config module isn't available yet, just use the environment variable
            pass
    
    # If still not found, use default
    if value is None:
        return default

    try:
        if var_type == bool:
            return str(value).lower() in ('true', '1', 'yes', 'on')
        return var_type(value)
    except (ValueError, TypeError):
        logging.warning(f"Invalid value for {key}, using default: {default}")
        return default


# Server settings
SERVER_HOST = get_env_var("SERVER_HOST", default="0.0.0.0")
SERVER_PORT = get_env_var("SERVER_PORT", default="8000", var_type=int)

# CORS settings
ENABLE_CORS = get_env_var("ENABLE_CORS", default="true", var_type=bool)
CORS_ORIGINS = get_env_var("CORS_ORIGINS", default="*").split(",")

# Model settings
DEFAULT_MODEL = get_env_var("DEFAULT_MODEL", default="microsoft/phi-2")
DEFAULT_MAX_LENGTH = get_env_var(
    "DEFAULT_MAX_LENGTH", default=2048, var_type=int)
DEFAULT_TEMPERATURE = get_env_var(
    "DEFAULT_TEMPERATURE", default=0.7, var_type=float)
DEFAULT_TOP_P = get_env_var("DEFAULT_TOP_P", default=0.9, var_type=float)

# Optimization settings
ENABLE_QUANTIZATION = get_env_var(
    "ENABLE_QUANTIZATION", default="false", var_type=bool)
QUANTIZATION_TYPE = get_env_var("QUANTIZATION_TYPE", default="int8")
ENABLE_FLASH_ATTENTION = get_env_var(
    "ENABLE_FLASH_ATTENTION", default="false", var_type=bool)
ENABLE_ATTENTION_SLICING = get_env_var(
    "ENABLE_ATTENTION_SLICING", default="true", var_type=bool)
ENABLE_CPU_OFFLOADING = get_env_var(
    "ENABLE_CPU_OFFLOADING", default="false", var_type=bool)
ENABLE_BETTERTRANSFORMER = get_env_var(
    "ENABLE_BETTERTRANSFORMER", default="false", var_type=bool)

# Resource management
UNLOAD_UNUSED_MODELS = get_env_var(
    "UNLOAD_UNUSED_MODELS", default="true", var_type=bool)
MODEL_TIMEOUT = get_env_var("MODEL_TIMEOUT", default="3600", var_type=int)

# Ngrok settings
NGROK_AUTH_TOKEN = get_env_var("NGROK_AUTH_TOKEN", default="")

# Model registry
MODEL_REGISTRY = {
    "microsoft/phi-2": {
        "name": "Phi-2",
        "description": "Microsoft's 2.7B parameter model",
        "size": "2.7B",
        "requirements": {
            "min_ram": 6,  # Reduced from 8GB
            "min_vram": 4  # Reduced from 6GB
        },
        "fallback": "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    },
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0": {
        "name": "TinyLlama Chat",
        "description": "Lightweight 1.1B chat model",
        "size": "1.1B",
        "requirements": {
            "min_ram": 3,  # Reduced from 4GB
            "min_vram": 2  # Reduced from 3GB
        }
    }
}


def can_run_model(model_id: str) -> bool:
    """Check if system meets model requirements"""
    if model_id not in MODEL_REGISTRY:
        return False

    import psutil
    import torch

    model = MODEL_REGISTRY[model_id]
    requirements = model["requirements"]

    # Get available memory with a buffer
    available_ram = (psutil.virtual_memory().available / (1024 ** 3)) * 0.8  # 80% of available RAM in GB
    
    # Adjust requirements based on optimizations
    if get_env_var("LOCALLAB_ENABLE_QUANTIZATION", default=False, var_type=bool):
        # Quantization reduces memory usage
        requirements["min_ram"] *= 0.5
        if "min_vram" in requirements:
            requirements["min_vram"] *= 0.5
    
    if get_env_var("LOCALLAB_ENABLE_CPU_OFFLOADING", default=False, var_type=bool):
        # CPU offloading allows running with less RAM
        requirements["min_ram"] *= 0.7
    
    # Check RAM
    if available_ram < requirements["min_ram"]:
        logger.warning(f"Insufficient RAM. Available: {available_ram:.1f}GB, Required: {requirements['min_ram']}GB")
        logger.info("Consider enabling quantization or CPU offloading to reduce memory usage")
        return False

    # Check VRAM if GPU available
    if torch.cuda.is_available() and "min_vram" in requirements:
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            available_vram = (info.free / (1024 ** 3)) * 0.8  # 80% of available VRAM in GB
            if available_vram < requirements["min_vram"]:
                logger.warning(f"Insufficient VRAM. Available: {available_vram:.1f}GB, Required: {requirements['min_vram']}GB")
                logger.info("Consider enabling quantization or using CPU offloading")
                return False
        except:
            pass

    return True


def estimate_model_requirements(model_id: str) -> Dict[str, float]:
    """Estimate resource requirements for a model"""
    if model_id not in MODEL_REGISTRY:
        return {}

    model = MODEL_REGISTRY[model_id]
    requirements = model["requirements"]

    # Add some buffer to minimum requirements
    return {
        "ram_gb": requirements["min_ram"] * 1.2,  # 20% buffer
        "vram_gb": requirements["min_vram"] * 1.2 if "min_vram" in requirements else 0
    }


# Model Configuration
CUSTOM_MODEL = get_env_var("LOCALLAB_CUSTOM_MODEL", default="")
WORKERS = get_env_var("LOCALLAB_WORKERS", default=1, var_type=int)
REQUEST_TIMEOUT = get_env_var(
    "LOCALLAB_REQUEST_TIMEOUT", default=30, var_type=int)
ENABLE_DYNAMIC_BATCHING = get_env_var(
    "LOCALLAB_ENABLE_DYNAMIC_BATCHING", default=True, var_type=bool)
BATCH_TIMEOUT = get_env_var(
    "LOCALLAB_BATCH_TIMEOUT", default=100, var_type=int)
MAX_CONCURRENT_REQUESTS = get_env_var(
    "LOCALLAB_MAX_CONCURRENT_REQUESTS", default=10, var_type=int)

# Performance Optimization
ENABLE_CUDA_GRAPHS = get_env_var(
    "LOCALLAB_ENABLE_CUDA_GRAPHS", default=True, var_type=bool)
ENABLE_TORCH_COMPILE = get_env_var(
    "LOCALLAB_ENABLE_TORCH_COMPILE", default=False, var_type=bool)

# Cache Settings
ENABLE_CACHE = get_env_var("LOCALLAB_ENABLE_CACHE",
                           default=True, var_type=bool)
CACHE_TTL = get_env_var("LOCALLAB_CACHE_TTL", default=3600, var_type=int)
CACHE_STRATEGY = get_env_var("LOCALLAB_CACHE_STRATEGY", default="lru")
CACHE_MAX_ITEMS = get_env_var(
    "LOCALLAB_CACHE_MAX_ITEMS", default=1000, var_type=int)

# Advanced Model Settings
MODEL_UNLOAD_TIMEOUT = get_env_var(
    "LOCALLAB_MODEL_UNLOAD_TIMEOUT", default=1800, var_type=int)
ENABLE_MODEL_PRELOADING = get_env_var(
    "LOCALLAB_ENABLE_MODEL_PRELOADING", default=False, var_type=bool)
FALLBACK_STRATEGY = get_env_var("LOCALLAB_FALLBACK_STRATEGY", default="auto")

# Performance Settings
DEFAULT_TEMPERATURE = get_env_var(
    "LOCALLAB_TEMPERATURE", default=0.7, var_type=float)
DEFAULT_TOP_K = get_env_var("LOCALLAB_TOP_K", default=50, var_type=int)
DEFAULT_REPETITION_PENALTY = get_env_var(
    "LOCALLAB_REPETITION_PENALTY", default=1.1, var_type=float)

# Model Loading Settings
PRELOAD_MODELS = False  # Set to True to preload models at startup
LAZY_LOADING = True  # Load model components only when needed

# Security Settings
MAX_TOKENS_PER_REQUEST = 4096
RATE_LIMIT = {
    "requests_per_minute": 60,
    "burst_size": 10
}
ENABLE_REQUEST_VALIDATION = True

# Resource Management
MIN_FREE_MEMORY = get_env_var(
    "LOCALLAB_MIN_FREE_MEMORY", default=2000, var_type=int)
MAX_BATCH_SIZE = get_env_var(
    "LOCALLAB_MAX_BATCH_SIZE", default=4, var_type=int)


# Cache Settings
CACHE_TTL = get_env_var("LOCALLAB_CACHE_TTL", default=3600, var_type=int)
CACHE_STRATEGY = get_env_var("LOCALLAB_CACHE_STRATEGY", default="lru")
CACHE_MAX_ITEMS = get_env_var(
    "LOCALLAB_CACHE_MAX_ITEMS", default=1000, var_type=int)

# Server Configuration
SERVER_HOST = get_env_var("LOCALLAB_HOST", default="0.0.0.0")
SERVER_PORT = get_env_var("LOCALLAB_PORT", default=8000, var_type=int)
ENABLE_CORS = get_env_var("LOCALLAB_ENABLE_CORS", default=True, var_type=bool)
CORS_ORIGINS = get_env_var("LOCALLAB_CORS_ORIGINS", default="*").split(",")
WORKERS = get_env_var("LOCALLAB_WORKERS", default=1, var_type=int)
ENABLE_COMPRESSION = get_env_var(
    "LOCALLAB_ENABLE_COMPRESSION", default=True, var_type=bool)

# Advanced Model Settings
MODEL_UNLOAD_TIMEOUT = get_env_var(
    "LOCALLAB_MODEL_UNLOAD_TIMEOUT", default=1800, var_type=int)
ENABLE_MODEL_PRELOADING = get_env_var(
    "LOCALLAB_ENABLE_MODEL_PRELOADING", default=False, var_type=bool)
FALLBACK_STRATEGY = get_env_var("LOCALLAB_FALLBACK_STRATEGY", default="auto")

# Quantization Configuration
QUANTIZATION_SETTINGS = {
    "fp16": {
        "load_in_8bit": False,
        "load_in_4bit": False,
        "torch_dtype": torch.float16,
        "device_map": "auto"
    },
    "int8": {
        "load_in_8bit": True,
        "load_in_4bit": False,
        "device_map": "auto"
    },
    "int4": {
        "load_in_8bit": False,
        "load_in_4bit": True,
        "device_map": "auto"
    }
}

# Logging Configuration
LOG_LEVEL = get_env_var("LOCALLAB_LOG_LEVEL", default="INFO")
LOG_FORMAT = get_env_var(
    "LOCALLAB_LOG_FORMAT",
    default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOG_FILE = get_env_var("LOCALLAB_LOG_FILE", default="")
ENABLE_CONSOLE_LOGGING = get_env_var(
    "LOCALLAB_ENABLE_CONSOLE_LOGGING", default=True, var_type=bool)
ENABLE_FILE_LOGGING = get_env_var(
    "LOCALLAB_ENABLE_FILE_LOGGING", default=False, var_type=bool)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler() if ENABLE_CONSOLE_LOGGING else logging.NullHandler(),
        logging.FileHandler(
            LOG_FILE) if ENABLE_FILE_LOGGING and LOG_FILE else logging.NullHandler()
    ]
)

logger = logging.getLogger("locallab")


def get_system_resources() -> Dict[str, Any]:
    """Get current system resources"""
    resources = {
        "cpu_count": psutil.cpu_count(),
        "ram_total": psutil.virtual_memory().total / (1024 * 1024),  # MB
        "ram_available": psutil.virtual_memory().available / (1024 * 1024),  # MB
        "gpu_available": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "gpu_info": []
    }

    if resources["gpu_available"]:
        for i in range(resources["gpu_count"]):
            gpu = torch.cuda.get_device_properties(i)
            resources["gpu_info"].append({
                "name": gpu.name,
                "total_memory": gpu.total_memory / (1024 * 1024),  # MB
                "major": gpu.major,
                "minor": gpu.minor
            })

    return resources


def estimate_model_requirements(model_id: str) -> Optional[Dict[str, Any]]:
    """Estimate model resource requirements more accurately"""
    try:
        info = model_info(model_id)

        # Get model config if available
        config = {}
        try:
            api = HfApi()
            files = api.list_repo_files(model_id)
            if "config.json" in files:
                config = json.loads(
                    api.hf_hub_download(model_id, "config.json"))
        except:
            pass

        # Get model size and parameters
        model_size_bytes = info.size or info.safetensors_size or 0
        # Rough estimate if not in config
        num_parameters = config.get("num_parameters", model_size_bytes / 4)

        # Calculate requirements
        base_vram = 2000  # Base VRAM requirement in MB
        param_size_factor = 4 if QUANTIZATION_TYPE == "fp16" else (
            2 if QUANTIZATION_TYPE == "int8" else 1)
        vram_per_param = (num_parameters * param_size_factor) / \
            (1024 * 1024)  # MB

        requirements = {
            "name": model_id,
            "vram": int(base_vram + vram_per_param),
            # RAM needs more headroom
            "ram": int((base_vram + vram_per_param) * 1.5),
            "max_length": config.get("max_position_embeddings", 2048),
            "architecture": config.get("architectures", ["Unknown"])[0],
            "quantization": QUANTIZATION_TYPE,
            "description": info.description or f"Custom model: {model_id}",
            "tags": info.tags or ["custom"],
            "fallback": "phi-2" if model_id != "microsoft/phi-2" else None
        }

        return requirements
    except Exception as e:

        logging.error(
            f"Error estimating requirements for {model_id}: {str(e)}"
        )

    return None


# Add custom model if specified
if CUSTOM_MODEL:
    requirements = estimate_model_requirements(CUSTOM_MODEL)
    if requirements:
        MODEL_REGISTRY[CUSTOM_MODEL.split("/")[-1]] = requirements


# Model Loading Settings
PRELOAD_MODELS = False  # Set to True to preload models at startup
LAZY_LOADING = True  # Load model components only when needed
UNLOAD_UNUSED_MODELS = True  # Automatically unload unused models
MODEL_TIMEOUT = 1800  # Unload model after 30 minutes of inactivity

# Server Configuration
SERVER_HOST = get_env_var("LOCALLAB_HOST", default="0.0.0.0")
SERVER_PORT = int(get_env_var("LOCALLAB_PORT", default="8000"))
ENABLE_CORS = get_env_var("LOCALLAB_ENABLE_CORS",
                          default="true", var_type=bool)
CORS_ORIGINS = get_env_var("LOCALLAB_CORS_ORIGINS", default="*").split(",")
WORKERS = 1  # Number of worker processes

# Security Settings
MAX_TOKENS_PER_REQUEST = 4096
RATE_LIMIT = {
    "requests_per_minute": 60,
    "burst_size": 10
}
ENABLE_REQUEST_VALIDATION = True

# System instructions configuration
DEFAULT_SYSTEM_INSTRUCTIONS = """"You are a helpful virtual assistant. Your responses should:
- Be concise: Provide brief and direct answers, expanding only when the user requests more detail.

- Be helpful: Address the user's question with relevant and actionable information.

- Be polite: Use a professional and friendly tone, and respond to greetings with simple, friendly replies.
"""


def get_model_generation_params(model_id: Optional[str] = None) -> dict:
    """Get model generation parameters, optionally specific to a model.

    Args:
        model_id: Optional model ID to get specific parameters for

    Returns:
        Dictionary of generation parameters
    """
    # Base parameters (defaults)
    params = {
        "max_length": get_env_var("LOCALLAB_MODEL_MAX_LENGTH", default=DEFAULT_MAX_LENGTH, var_type=int),
        "temperature": get_env_var("LOCALLAB_MODEL_TEMPERATURE", default=DEFAULT_TEMPERATURE, var_type=float),
        "top_p": get_env_var("LOCALLAB_MODEL_TOP_P", default=DEFAULT_TOP_P, var_type=float),
        "top_k": get_env_var("LOCALLAB_TOP_K", default=DEFAULT_TOP_K, var_type=int),
        "repetition_penalty": get_env_var("LOCALLAB_REPETITION_PENALTY", default=DEFAULT_REPETITION_PENALTY, var_type=float),
    }

    # If model_id is provided and exists in MODEL_REGISTRY, use model-specific parameters
    if model_id and model_id in MODEL_REGISTRY:
        model_config = MODEL_REGISTRY[model_id]
        # Override with model-specific parameters if available
        if "max_length" in model_config:
            params["max_length"] = model_config["max_length"]

        # Add any other model-specific parameters from the registry
        for param in ["temperature", "top_p", "top_k", "repetition_penalty"]:
            if param in model_config:
                params[param] = model_config[param]

    return params


class SystemInstructions:
    def __init__(self):
        self.config_dir = Path.home() / ".locallab"
        self.config_file = self.config_dir / "system_instructions.json"
        self.global_instructions = DEFAULT_SYSTEM_INSTRUCTIONS
        self.model_instructions: Dict[str, str] = {}
        self.load_config()

    def load_config(self):
        """Load system instructions from config file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.global_instructions = config.get(
                        'global', DEFAULT_SYSTEM_INSTRUCTIONS)
                    self.model_instructions = config.get('models', {})
        except Exception as e:
            logger.warning(f"Failed to load system instructions: {e}")

    def save_config(self):
        """Save system instructions to config file"""
        try:
            self.config_dir.mkdir(exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump({
                    'global': self.global_instructions,
                    'models': self.model_instructions
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save system instructions: {e}")

    def get_instructions(self, model_id: Optional[str] = None) -> str:
        """Get system instructions for a model"""
        if model_id and model_id in self.model_instructions:
            return self.model_instructions[model_id]
        return self.global_instructions

    def set_global_instructions(self, instructions: str):
        """Set global system instructions"""
        self.global_instructions = instructions
        self.save_config()

    def set_model_instructions(self, model_id: str, instructions: str):
        """Set model-specific system instructions"""
        self.model_instructions[model_id] = instructions
        self.save_config()

    def reset_instructions(self, model_id: Optional[str] = None):
        """Reset instructions to default"""
        if model_id:
            self.model_instructions.pop(model_id, None)
        else:
            self.global_instructions = DEFAULT_SYSTEM_INSTRUCTIONS
            self.model_instructions.clear()
        self.save_config()


# Initialize system instructions
system_instructions = SystemInstructions()





