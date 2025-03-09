"""
Interactive CLI prompts for LocalLab
"""

import os
import sys
from typing import Dict, Any, Optional, List, Tuple
import click
from ..utils.system import get_gpu_memory, get_system_memory
from ..config import (
    DEFAULT_MODEL,
    ENABLE_QUANTIZATION,
    QUANTIZATION_TYPE,
    ENABLE_ATTENTION_SLICING,
    ENABLE_FLASH_ATTENTION,
    ENABLE_BETTERTRANSFORMER,
    ENABLE_CPU_OFFLOADING
)

def is_in_colab() -> bool:
    """Check if running in Google Colab"""
    try:
        import google.colab
        return True
    except ImportError:
        return False

def get_missing_required_env_vars() -> List[str]:
    """Get list of missing required environment variables"""
    missing = []
    
    # Check for model
    if not os.environ.get("HUGGINGFACE_MODEL") and not os.environ.get("DEFAULT_MODEL"):
        missing.append("HUGGINGFACE_MODEL")
    
    # Check for ngrok token if in Colab
    if is_in_colab() and not os.environ.get("NGROK_AUTH_TOKEN"):
        missing.append("NGROK_AUTH_TOKEN")
    
    return missing

def prompt_for_config(use_ngrok: bool = None, port: int = None, ngrok_auth_token: str = None) -> Dict[str, Any]:
    """
    Interactive prompt for configuration
    
    Args:
        use_ngrok: Whether to use ngrok
        port: Port to run the server on
        ngrok_auth_token: Ngrok authentication token
        
    Returns:
        Dict of configuration values
    """
    config = {}
    
    # Determine if we're in Colab
    in_colab = is_in_colab()
    
    # Check for GPU
    has_gpu = False
    gpu_memory = get_gpu_memory()
    if gpu_memory:
        has_gpu = True
        total_gpu_memory, free_gpu_memory = gpu_memory
        click.echo(f"🎮 GPU detected with {free_gpu_memory}MB free of {total_gpu_memory}MB total")
    else:
        click.echo("⚠️ No GPU detected. Running on CPU will be significantly slower.")
    
    # Get system memory
    total_memory, free_memory = get_system_memory()
    click.echo(f"💾 System memory: {free_memory}MB free of {total_memory}MB total")
    
    # Check for missing required environment variables
    missing_vars = get_missing_required_env_vars()
    
    # If no missing vars and all parameters provided, return early
    if not missing_vars and use_ngrok is not None and port is not None and (not in_colab or ngrok_auth_token is not None):
        config["use_ngrok"] = use_ngrok
        config["port"] = port
        config["ngrok_auth_token"] = ngrok_auth_token
        return config
    
    click.echo("\n🚀 Welcome to LocalLab! Let's set up your server.\n")
    
    # Ask for model if not provided
    if "HUGGINGFACE_MODEL" in missing_vars:
        model_id = click.prompt(
            "📦 Which model would you like to use?",
            default=DEFAULT_MODEL
        )
        os.environ["HUGGINGFACE_MODEL"] = model_id
        config["model_id"] = model_id
    
    # Ask for port if not provided
    if port is None:
        port = click.prompt(
            "🔌 Which port would you like to run on?",
            default=8000,
            type=int
        )
    config["port"] = port
    
    # Ask about ngrok if in Colab and not provided
    if in_colab:
        if use_ngrok is None:
            use_ngrok = click.confirm(
                "🌐 Do you want to enable public access via ngrok?",
                default=True
            )
        config["use_ngrok"] = use_ngrok
        
        if use_ngrok and (ngrok_auth_token is None or "NGROK_AUTH_TOKEN" in missing_vars):
            ngrok_auth_token = click.prompt(
                "🔑 Please enter your ngrok auth token (get one at https://dashboard.ngrok.com/get-started/your-authtoken)",
                hide_input=True
            )
            os.environ["NGROK_AUTH_TOKEN"] = ngrok_auth_token
            config["ngrok_auth_token"] = ngrok_auth_token
    else:
        # Not in Colab, ask about ngrok only if not provided
        if use_ngrok is None:
            use_ngrok = click.confirm(
                "🌐 Do you want to enable public access via ngrok?",
                default=False
            )
        config["use_ngrok"] = use_ngrok
        
        if use_ngrok and ngrok_auth_token is None:
            ngrok_auth_token = click.prompt(
                "🔑 Please enter your ngrok auth token (get one at https://dashboard.ngrok.com/get-started/your-authtoken)",
                hide_input=True
            )
            os.environ["NGROK_AUTH_TOKEN"] = ngrok_auth_token
            config["ngrok_auth_token"] = ngrok_auth_token
    
    # Ask about optimizations if GPU is available
    if has_gpu:
        setup_optimizations = click.confirm(
            "⚡ Would you like to configure optimizations for better performance?",
            default=True
        )
        
        if setup_optimizations:
            # Quantization
            enable_quantization = click.confirm(
                "📊 Enable quantization for reduced memory usage?",
                default=ENABLE_QUANTIZATION
            )
            os.environ["LOCALLAB_ENABLE_QUANTIZATION"] = str(enable_quantization).lower()
            config["enable_quantization"] = enable_quantization
            
            if enable_quantization:
                quant_type = click.prompt(
                    "📊 Quantization type",
                    type=click.Choice(["int8", "int4"]),
                    default=QUANTIZATION_TYPE or "int8"
                )
                os.environ["LOCALLAB_QUANTIZATION_TYPE"] = quant_type
                config["quantization_type"] = quant_type
            
            # Attention slicing
            enable_attn_slicing = click.confirm(
                "🔪 Enable attention slicing for reduced memory usage?",
                default=ENABLE_ATTENTION_SLICING
            )
            os.environ["LOCALLAB_ENABLE_ATTENTION_SLICING"] = str(enable_attn_slicing).lower()
            config["enable_attention_slicing"] = enable_attn_slicing
            
            # Flash attention
            enable_flash_attn = click.confirm(
                "⚡ Enable flash attention for faster inference?",
                default=ENABLE_FLASH_ATTENTION
            )
            os.environ["LOCALLAB_ENABLE_FLASH_ATTENTION"] = str(enable_flash_attn).lower()
            config["enable_flash_attention"] = enable_flash_attn
            
            # BetterTransformer
            enable_better_transformer = click.confirm(
                "🔄 Enable BetterTransformer for optimized inference?",
                default=ENABLE_BETTERTRANSFORMER
            )
            os.environ["LOCALLAB_ENABLE_BETTERTRANSFORMER"] = str(enable_better_transformer).lower()
            config["enable_better_transformer"] = enable_better_transformer
    
    # Ask about advanced options
    setup_advanced = click.confirm(
        "🔧 Would you like to configure advanced options?",
        default=False
    )
    
    if setup_advanced:
        # CPU offloading
        enable_cpu_offloading = click.confirm(
            "💻 Enable CPU offloading for large models?",
            default=ENABLE_CPU_OFFLOADING
        )
        os.environ["LOCALLAB_ENABLE_CPU_OFFLOADING"] = str(enable_cpu_offloading).lower()
        config["enable_cpu_offloading"] = enable_cpu_offloading
        
        # Model timeout
        model_timeout = click.prompt(
            "⏱️ Model unloading timeout in seconds (0 to disable)",
            default=3600,
            type=int
        )
        os.environ["LOCALLAB_MODEL_TIMEOUT"] = str(model_timeout)
        config["model_timeout"] = model_timeout
    
    click.echo("\n✅ Configuration complete! Starting server...\n")
    return config 