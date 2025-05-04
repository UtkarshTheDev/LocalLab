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

    # Show current values for reference
    click.echo("\nCurrent optimization settings:")
    click.echo(f"  Quantization: {'Enabled' if config.get('enable_quantization', ENABLE_QUANTIZATION) else 'Disabled'}")
    if config.get('enable_quantization', ENABLE_QUANTIZATION):
        click.echo(f"  Quantization Type: {config.get('quantization_type', QUANTIZATION_TYPE)}")
    click.echo(f"  CPU Offloading: {'Enabled' if config.get('enable_cpu_offloading', ENABLE_CPU_OFFLOADING) else 'Disabled'}")
    click.echo(f"  Attention Slicing: {'Enabled' if config.get('enable_attention_slicing', ENABLE_ATTENTION_SLICING) else 'Disabled'}")
    click.echo(f"  Flash Attention: {'Enabled' if config.get('enable_flash_attention', ENABLE_FLASH_ATTENTION) else 'Disabled'}")
    click.echo(f"  Better Transformer: {'Enabled' if config.get('enable_bettertransformer', ENABLE_BETTERTRANSFORMER) else 'Disabled'}")

    # Ask if user wants to configure optimization settings
    configure_optimization = click.confirm(
        "\nWould you like to configure model optimization settings?",
        default=True  # Default to Yes for optimization settings
    )

    if configure_optimization:
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

        config["enable_bettertransformer"] = click.confirm(
            "Enable better transformer?",
            default=config.get("enable_bettertransformer", ENABLE_BETTERTRANSFORMER)
        )

        # Set environment variables for optimization settings
        os.environ["LOCALLAB_ENABLE_QUANTIZATION"] = str(config["enable_quantization"]).lower()
        os.environ["LOCALLAB_QUANTIZATION_TYPE"] = str(config["quantization_type"]) if config["enable_quantization"] else ""
        os.environ["LOCALLAB_ENABLE_CPU_OFFLOADING"] = str(config["enable_cpu_offloading"]).lower()
        os.environ["LOCALLAB_ENABLE_ATTENTION_SLICING"] = str(config["enable_attention_slicing"]).lower()
        os.environ["LOCALLAB_ENABLE_FLASH_ATTENTION"] = str(config["enable_flash_attention"]).lower()
        os.environ["LOCALLAB_ENABLE_BETTERTRANSFORMER"] = str(config["enable_bettertransformer"]).lower()

        # Save the optimization settings to config file
        from .config import save_config
        save_config(config)

        click.echo("\n✅ Optimization settings updated!")
    else:
        # If user doesn't want to configure, use the current values or defaults
        if 'enable_quantization' not in config:
            config["enable_quantization"] = ENABLE_QUANTIZATION
        if config["enable_quantization"] and 'quantization_type' not in config:
            config["quantization_type"] = QUANTIZATION_TYPE
        if 'enable_cpu_offloading' not in config:
            config["enable_cpu_offloading"] = ENABLE_CPU_OFFLOADING
        if 'enable_attention_slicing' not in config:
            config["enable_attention_slicing"] = ENABLE_ATTENTION_SLICING
        if 'enable_flash_attention' not in config:
            config["enable_flash_attention"] = ENABLE_FLASH_ATTENTION
        if 'enable_bettertransformer' not in config:
            config["enable_bettertransformer"] = ENABLE_BETTERTRANSFORMER

        # Set environment variables for optimization settings
        os.environ["LOCALLAB_ENABLE_QUANTIZATION"] = str(config["enable_quantization"]).lower()
        os.environ["LOCALLAB_QUANTIZATION_TYPE"] = str(config["quantization_type"]) if config["enable_quantization"] else ""
        os.environ["LOCALLAB_ENABLE_CPU_OFFLOADING"] = str(config["enable_cpu_offloading"]).lower()
        os.environ["LOCALLAB_ENABLE_ATTENTION_SLICING"] = str(config["enable_attention_slicing"]).lower()
        os.environ["LOCALLAB_ENABLE_FLASH_ATTENTION"] = str(config["enable_flash_attention"]).lower()
        os.environ["LOCALLAB_ENABLE_BETTERTRANSFORMER"] = str(config["enable_bettertransformer"]).lower()

        # Save the optimization settings to config file
        from .config import save_config
        save_config(config)

        click.echo("\nUsing current optimization settings.")

    # Advanced Settings
    # ----------------
    click.echo("\n⚙️ Advanced Settings")
    click.echo("──────────────────")

    config["model_timeout"] = click.prompt(
        "Model timeout (seconds)",
        default=config.get("model_timeout", 3600),
        type=int
    )

    # Response Quality Settings
    # -----------------------
    click.echo("\n🎯 Response Quality Settings")
    click.echo("───────────────────────────")

    # Show current values for reference with descriptions
    click.echo("\nCurrent response quality settings:")
    click.echo(f"  Max Length: {config.get('max_length', 8192)} tokens - Maximum number of tokens in the generated response")
    click.echo(f"  Temperature: {config.get('temperature', 0.7)} - Controls randomness (higher = more creative, lower = more focused)")
    click.echo(f"  Top-p: {config.get('top_p', 0.9)} - Nucleus sampling parameter (higher = more diverse responses)")
    click.echo(f"  Top-k: {config.get('top_k', 80)} - Limits vocabulary to top K tokens (higher = more diverse vocabulary)")
    click.echo(f"  Repetition Penalty: {config.get('repetition_penalty', 1.15)} - Penalizes repetition (higher = less repetition)")
    click.echo(f"  Max Time: {config.get('max_time', 120.0)} seconds - Maximum time allowed for generation")

    # Ask if user wants to configure response quality settings
    configure_response_quality = click.confirm(
        "\nWould you like to configure response quality settings?",
        default=False  # Default to No
    )

    if configure_response_quality:
        # If user wants to configure, show the prompts with descriptions
        config["max_length"] = click.prompt(
            "Maximum generation length in tokens (higher = longer responses, but slower)",
            default=config.get("max_length", 8192),
            type=int
        )

        config["temperature"] = click.prompt(
            "Temperature (0.1-1.0, higher = more creative, lower = more focused)",
            default=config.get("temperature", 0.7),
            type=float
        )

        config["top_p"] = click.prompt(
            "Top-p (0.1-1.0, higher = more diverse responses)",
            default=config.get("top_p", 0.9),
            type=float
        )

        config["top_k"] = click.prompt(
            "Top-k (1-100, higher = more diverse vocabulary)",
            default=config.get("top_k", 80),
            type=int
        )

        config["repetition_penalty"] = click.prompt(
            "Repetition penalty (1.0-2.0, higher = less repetition)",
            default=config.get("repetition_penalty", 1.15),
            type=float
        )

        config["max_time"] = click.prompt(
            "Maximum generation time in seconds (higher = more complete responses, but slower)",
            default=config.get("max_time", 120.0),
            type=float
        )

        click.echo("\n✅ Response quality settings updated!")
    else:
        # If user doesn't want to configure, use the current values or defaults
        if 'max_length' not in config:
            config["max_length"] = 8192
        if 'temperature' not in config:
            config["temperature"] = 0.7
        if 'top_p' not in config:
            config["top_p"] = 0.9
        if 'top_k' not in config:
            config["top_k"] = 80
        if 'repetition_penalty' not in config:
            config["repetition_penalty"] = 1.15
        if 'max_time' not in config:
            config["max_time"] = 120.0

        click.echo("\nUsing default response quality settings.")

    # Set environment variables for these settings
    os.environ["DEFAULT_MAX_LENGTH"] = str(config["max_length"])
    os.environ["DEFAULT_TEMPERATURE"] = str(config["temperature"])
    os.environ["DEFAULT_TOP_P"] = str(config["top_p"])
    os.environ["DEFAULT_TOP_K"] = str(config["top_k"])
    os.environ["DEFAULT_REPETITION_PENALTY"] = str(config["repetition_penalty"])
    os.environ["DEFAULT_MAX_TIME"] = str(config["max_time"])

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