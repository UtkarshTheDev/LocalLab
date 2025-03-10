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

def prompt_for_config(use_ngrok: bool = None, port: int = None, ngrok_auth_token: str = None, force_reconfigure: bool = False) -> Dict[str, Any]:
    """
    Interactive prompt for configuration
    
    Args:
        use_ngrok: Whether to use ngrok
        port: Port to run the server on
        ngrok_auth_token: Ngrok authentication token
        force_reconfigure: Whether to force reconfiguration of all settings
        
    Returns:
        Dict of configuration values
    """
    # Import here to avoid circular imports
    from .config import load_config, get_config_value
    
    # Load existing configuration
    saved_config = load_config()
    
    # Initialize config with saved values
    config = saved_config.copy()
    
    # Override with provided parameters
    if use_ngrok is not None:
        config["use_ngrok"] = use_ngrok
    if port is not None:
        config["port"] = port
    if ngrok_auth_token is not None:
        config["ngrok_auth_token"] = ngrok_auth_token
    
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
    
    # Check if we have all required configuration and not forcing reconfiguration
    has_model = "model_id" in config or os.environ.get("HUGGINGFACE_MODEL") or os.environ.get("DEFAULT_MODEL")
    has_port = "port" in config or port is not None
    has_ngrok_config = not in_colab or not config.get("use_ngrok", use_ngrok) or "ngrok_auth_token" in config or ngrok_auth_token is not None or os.environ.get("NGROK_AUTH_TOKEN")
    
    # If we have all required config and not forcing reconfiguration, return early
    if not force_reconfigure and has_model and has_port and has_ngrok_config and not missing_vars:
        # Ensure port is set in config
        if "port" not in config and port is not None:
            config["port"] = port
        # Ensure use_ngrok is set in config
        if "use_ngrok" not in config and use_ngrok is not None:
            config["use_ngrok"] = use_ngrok
        # Ensure ngrok_auth_token is set in config if needed
        if config.get("use_ngrok", False) and "ngrok_auth_token" not in config and ngrok_auth_token is not None:
            config["ngrok_auth_token"] = ngrok_auth_token
        
        return config
    
    click.echo("\n🚀 Welcome to LocalLab! Let's set up your server.\n")
    
    # Always ask for model when reconfiguring or if not provided
    model_id = click.prompt(
        "📦 Which model would you like to use?",
        default=config.get("model_id", DEFAULT_MODEL)
    )
    os.environ["HUGGINGFACE_MODEL"] = model_id
    config["model_id"] = model_id
    
    # Always ask for port when reconfiguring or if not provided
    port = click.prompt(
        "🔌 Which port would you like to run on?",
        default=config.get("port", 8000),
        type=int
    )
    config["port"] = port
    
    # Ask about ngrok
    use_ngrok = click.confirm(
        "🌐 Do you want to enable public access via ngrok?",
        default=config.get("use_ngrok", in_colab)
    )
    config["use_ngrok"] = use_ngrok
    
    if use_ngrok:
        ngrok_auth_token = click.prompt(
            "🔑 Please enter your ngrok auth token (get one at https://dashboard.ngrok.com/get-started/your-authtoken)",
            default=config.get("ngrok_auth_token", ""),
            hide_input=True
        )
        if ngrok_auth_token:
            os.environ["NGROK_AUTH_TOKEN"] = ngrok_auth_token
            config["ngrok_auth_token"] = ngrok_auth_token
    
    # Ask about optimizations
    setup_optimizations = click.confirm(
        "⚡ Would you like to configure optimizations for better performance?",
        default=True
    )
    
    if setup_optimizations:
        # Quantization
        enable_quantization = click.confirm(
            "📊 Enable quantization for reduced memory usage?",
            default=config.get("enable_quantization", ENABLE_QUANTIZATION)
        )
        os.environ["LOCALLAB_ENABLE_QUANTIZATION"] = str(enable_quantization).lower()
        config["enable_quantization"] = enable_quantization
        
        if enable_quantization:
            quant_type = click.prompt(
                "📊 Quantization type",
                type=click.Choice(["int8", "int4"]),
                default=config.get("quantization_type", QUANTIZATION_TYPE or "int8")
            )
            os.environ["LOCALLAB_QUANTIZATION_TYPE"] = quant_type
            config["quantization_type"] = quant_type
        
        # Attention slicing
        enable_attn_slicing = click.confirm(
            "🔪 Enable attention slicing for reduced memory usage?",
            default=config.get("enable_attention_slicing", ENABLE_ATTENTION_SLICING)
        )
        os.environ["LOCALLAB_ENABLE_ATTENTION_SLICING"] = str(enable_attn_slicing).lower()
        config["enable_attention_slicing"] = enable_attn_slicing
        
        # Flash attention
        enable_flash_attn = click.confirm(
            "⚡ Enable flash attention for faster inference?",
            default=config.get("enable_flash_attention", ENABLE_FLASH_ATTENTION)
        )
        os.environ["LOCALLAB_ENABLE_FLASH_ATTENTION"] = str(enable_flash_attn).lower()
        config["enable_flash_attention"] = enable_flash_attn
        
        # BetterTransformer
        enable_better_transformer = click.confirm(
            "🔄 Enable BetterTransformer for optimized inference?",
            default=config.get("enable_better_transformer", ENABLE_BETTERTRANSFORMER)
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
            default=config.get("enable_cpu_offloading", ENABLE_CPU_OFFLOADING)
        )
        os.environ["LOCALLAB_ENABLE_CPU_OFFLOADING"] = str(enable_cpu_offloading).lower()
        config["enable_cpu_offloading"] = enable_cpu_offloading
        
        # Model timeout
        model_timeout = click.prompt(
            "⏱️ Model unloading timeout in seconds (0 to disable)",
            default=config.get("model_timeout", 3600),
            type=int
        )
        os.environ["LOCALLAB_MODEL_TIMEOUT"] = str(model_timeout)
        config["model_timeout"] = model_timeout
        
        # Cache settings
        enable_cache = click.confirm(
            "🔄 Enable response caching?",
            default=config.get("enable_cache", True)
        )
        os.environ["LOCALLAB_ENABLE_CACHE"] = str(enable_cache).lower()
        config["enable_cache"] = enable_cache
        
        if enable_cache:
            cache_ttl = click.prompt(
                "⏱️ Cache TTL in seconds",
                default=config.get("cache_ttl", 3600),
                type=int
            )
            os.environ["LOCALLAB_CACHE_TTL"] = str(cache_ttl)
            config["cache_ttl"] = cache_ttl
        
        # Logging settings
        log_level = click.prompt(
            "📝 Log level",
            type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
            default=config.get("log_level", "INFO")
        )
        os.environ["LOCALLAB_LOG_LEVEL"] = log_level
        config["log_level"] = log_level
        
        enable_file_logging = click.confirm(
            "📄 Enable file logging?",
            default=config.get("enable_file_logging", False)
        )
        os.environ["LOCALLAB_ENABLE_FILE_LOGGING"] = str(enable_file_logging).lower()
        config["enable_file_logging"] = enable_file_logging
        
        if enable_file_logging:
            log_file = click.prompt(
                "📄 Log file path",
                default=config.get("log_file", "locallab.log")
            )
            os.environ["LOCALLAB_LOG_FILE"] = log_file
            config["log_file"] = log_file
    
    click.echo("\n✅ Configuration complete!\n")
    return config 