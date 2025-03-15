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
    ENABLE_CPU_OFFLOADING,
    NGROK_TOKEN_ENV,
    HF_TOKEN_ENV,
    get_env_var,
    set_env_var
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

def prompt_for_config(use_ngrok: bool = None, port: int = None, ngrok_auth_token: Optional[str] = None, force_reconfigure: bool = False) -> Dict[str, Any]:
    """
    Interactive prompt for configuration
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
        # Set environment variable for use_ngrok
        os.environ["LOCALLAB_USE_NGROK"] = str(use_ngrok).lower()
        
    if port is not None:
        config["port"] = port
        os.environ["LOCALLAB_PORT"] = str(port)
        
    if ngrok_auth_token is not None:
        config["ngrok_auth_token"] = ngrok_auth_token
        os.environ["NGROK_AUTHTOKEN"] = ngrok_auth_token
    
    # Determine if we're in Colab
    in_colab = is_in_colab()
    
    # If in Colab, ensure ngrok is enabled by default
    if in_colab and "use_ngrok" not in config:
        config["use_ngrok"] = True
        os.environ["LOCALLAB_USE_NGROK"] = "true"

    click.echo("\n🚀 Welcome to LocalLab! Let's set up your server.\n")
    
    # Basic Configuration
    # ------------------
    click.echo("\n📋 Basic Configuration")
    click.echo("─────────────────────")
    
    # Model selection
    model_id = click.prompt(
        "📦 Which model would you like to use?",
        default=config.get("model_id", DEFAULT_MODEL)
    )
    config["model_id"] = model_id
    # Set environment variable for model
    os.environ["HUGGINGFACE_MODEL"] = model_id
    
    # Port configuration
    port = click.prompt(
        "🔌 Which port would you like to run on?",
        default=config.get("port", 8000),
        type=int
    )
    config["port"] = port
    
    # Model Optimization Settings
    # -------------------------
    click.echo("\n⚡ Model Optimization Settings")
    click.echo("─────────────────────────────")
    
    config["enable_quantization"] = click.confirm(
        "Enable model quantization?",
        default=config.get("enable_quantization", ENABLE_QUANTIZATION)
    )
    
    if config["enable_quantization"]:
        config["quantization_type"] = click.prompt(
            "Quantization type (fp16/int8/int4)",
            default=config.get("quantization_type", QUANTIZATION_TYPE),
            type=click.Choice(["fp16", "int8", "int4"])
        )
    
    config["enable_cpu_offloading"] = click.confirm(
        "Enable CPU offloading?",
        default=config.get("enable_cpu_offloading", ENABLE_CPU_OFFLOADING)
    )
    
    config["enable_attention_slicing"] = click.confirm(
        "Enable attention slicing?",
        default=config.get("enable_attention_slicing", ENABLE_ATTENTION_SLICING)
    )
    
    config["enable_flash_attention"] = click.confirm(
        "Enable flash attention?",
        default=config.get("enable_flash_attention", ENABLE_FLASH_ATTENTION)
    )
    
    config["enable_better_transformer"] = click.confirm(
        "Enable better transformer?",
        default=config.get("enable_bettertransformer", ENABLE_BETTERTRANSFORMER)
    )
    
    # Advanced Settings
    # ----------------
    click.echo("\n⚙️ Advanced Settings")
    click.echo("──────────────────")
    
    config["model_timeout"] = click.prompt(
        "Model timeout (seconds)",
        default=config.get("model_timeout", 3600),
        type=int
    )
    
    # Cache Settings
    # -------------
    click.echo("\n💾 Cache Settings")
    click.echo("────────────────")
    
    config["enable_cache"] = click.confirm(
        "Enable response caching?",
        default=config.get("enable_cache", True)
    )
    
    if config["enable_cache"]:
        config["cache_ttl"] = click.prompt(
            "Cache TTL (seconds)",
            default=config.get("cache_ttl", 3600),
            type=int
        )
    
    # Logging Settings
    # ---------------
    click.echo("\n📝 Logging Settings")
    click.echo("──────────────────")
    
    config["log_level"] = click.prompt(
        "Log level",
        default=config.get("log_level", "INFO"),
        type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    )
    
    config["enable_file_logging"] = click.confirm(
        "Enable file logging?",
        default=config.get("enable_file_logging", False)
    )
    
    if config["enable_file_logging"]:
        config["log_file"] = click.prompt(
            "Log file path",
            default=config.get("log_file", "locallab.log")
        )
    
    # Ngrok Configuration
    # ------------------
    click.echo("\n🌐 Ngrok Configuration")
    click.echo("────────────────────")
    
    use_ngrok = click.confirm(
        "Enable public access via ngrok?",
        default=config.get("use_ngrok", in_colab)
    )
    config["use_ngrok"] = use_ngrok
    os.environ["LOCALLAB_USE_NGROK"] = str(use_ngrok).lower()
    
    if use_ngrok:
        current_token = config.get("ngrok_auth_token") or get_env_var(NGROK_TOKEN_ENV)
        if current_token:
            click.echo(f"\nCurrent ngrok token: {current_token}")
            
        ngrok_auth_token = click.prompt(
            "Enter your ngrok auth token (get one at https://dashboard.ngrok.com/get-started/your-authtoken)",
            default=current_token,
            type=str,
            show_default=True
        )
        
        if ngrok_auth_token:
            token_str = str(ngrok_auth_token).strip()
            config["ngrok_auth_token"] = token_str
            # Set both environment variables to ensure compatibility
            os.environ["NGROK_AUTHTOKEN"] = token_str
            os.environ["LOCALLAB_NGROK_AUTH_TOKEN"] = token_str
            
            # Save immediately to ensure persistence
            from .config import save_config
            save_config(config)
            click.echo(f"✅ Ngrok token saved and activated")

    # HuggingFace Token
    # ----------------
    click.echo("\n🤗 HuggingFace Token")
    click.echo("──────────────────")
    
    current_hf_token = config.get("huggingface_token") or get_env_var(HF_TOKEN_ENV)
    if current_hf_token:
        click.echo(f"Current HuggingFace token: {current_hf_token}")
        
    if not current_hf_token or force_reconfigure:
        click.echo("\nA token is required to download models.")
        click.echo("Get your token from: https://huggingface.co/settings/tokens")
        
        hf_token = click.prompt(
            "Enter your HuggingFace token",
            default=current_hf_token,
            type=str,
            show_default=True
        )
        
        if hf_token:
            if len(hf_token) < 20:
                click.echo("❌ Invalid token format. Token should be longer than 20 characters.")
            else:
                token_str = str(hf_token).strip()
                config["huggingface_token"] = token_str
                set_env_var(HF_TOKEN_ENV, token_str)
                
                # Save immediately
                from .config import save_config
                save_config(config)
        else:
            click.echo("\n⚠️  No token provided. Some models may not be accessible.")

    click.echo("\n✅ Configuration complete!\n")
    return config