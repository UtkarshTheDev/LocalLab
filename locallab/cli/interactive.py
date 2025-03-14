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

def prompt_for_config(use_ngrok: bool = None, port: int = None, ngrok_auth_token: str = None, force_reconfigure: bool = False) -> Dict[str, Any]:
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
    if port is not None:
        config["port"] = port
    if ngrok_auth_token is not None:
        config["ngrok_auth_token"] = ngrok_auth_token
    
    # Determine if we're in Colab
    in_colab = is_in_colab()
    
    # If in Colab, use simplified configuration
    if in_colab:
        # Set default values for Colab environment
        config.setdefault("port", 8000)
        config.setdefault("use_ngrok", True)
        config.setdefault("model_id", os.environ.get("HUGGINGFACE_MODEL", DEFAULT_MODEL))
        
        # Use ngrok token from environment if available
        if os.environ.get("NGROK_AUTH_TOKEN"):
            config["ngrok_auth_token"] = os.environ.get("NGROK_AUTH_TOKEN")
        elif ngrok_auth_token:
            config["ngrok_auth_token"] = ngrok_auth_token
            
        # Set some reasonable defaults for Colab
        config.setdefault("enable_quantization", True)
        config.setdefault("quantization_type", "int8")
        config.setdefault("enable_attention_slicing", True)
        config.setdefault("enable_flash_attention", True)
        config.setdefault("enable_better_transformer", True)
        
        return config
    
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
        # Show current token if exists
        current_token = config.get("ngrok_auth_token") or get_env_var(NGROK_TOKEN_ENV)
        if current_token:
            click.echo(f"\nCurrent ngrok token: {current_token}")
            
        ngrok_auth_token = click.prompt(
            "🔑 Enter your ngrok auth token (get one at https://dashboard.ngrok.com/get-started/your-authtoken)",
            default=current_token,
            type=str,
            show_default=True
        )
        
        if ngrok_auth_token:
            token_str = str(ngrok_auth_token).strip()
            config["ngrok_auth_token"] = token_str
            set_env_var(NGROK_TOKEN_ENV, token_str)
            click.echo(f"✅ Ngrok token saved: {token_str}")
    
    # Ask about HuggingFace token
    current_hf_token = config.get("huggingface_token") or get_env_var(HF_TOKEN_ENV)
    if current_hf_token:
        click.echo(f"\nCurrent HuggingFace token: {current_hf_token}")
        
    if not current_hf_token or force_reconfigure:
        click.echo("\n🔑 HuggingFace Token Configuration")
        click.echo("───────────────────────────────")
        click.echo("A token is required to download models like microsoft/phi-2")
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
                return config
            
            token_str = str(hf_token).strip()
            config["huggingface_token"] = token_str
            set_env_var(HF_TOKEN_ENV, token_str)
            click.echo(f"✅ HuggingFace token saved: {token_str}")
            
            # Save immediately
            from .config import save_config
            save_config(config)
        else:
            click.echo("\n⚠️  No token provided. Some models may not be accessible.")

    click.echo("\n✅ Configuration complete!\n")
    return config