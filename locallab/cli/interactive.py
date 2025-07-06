"""
Interactive CLI prompts for LocalLab
"""

import os
from typing import Dict, Any, Optional, List
import click
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
    Interactive prompt for configuration with improved user experience
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

    # Check if this is a fresh installation for better welcome message
    is_fresh_install = not any(key in saved_config for key in [
        'enable_quantization', 'enable_cpu_offloading', 'enable_attention_slicing',
        'enable_flash_attention', 'enable_bettertransformer'
    ])

    # Welcome message with visual appeal
    if is_fresh_install:
        click.echo("\n" + "🌟" * 30)
        click.echo("🎉 Welcome to LocalLab Setup!")
        click.echo("🌟" * 30)
        click.echo("\n🚀 Let's configure your personal AI server!")
        click.echo("   We'll walk through each step together.")
        click.echo("\n💡 What we'll set up:")
        click.echo("   📦 Choose your AI model")
        click.echo("   ⚡ Optimize for your hardware")
        click.echo("   🔐 Set up authentication")
        click.echo("   🌐 Configure access options")
        click.echo("\n✨ This should take just a few minutes!")
    else:
        click.echo("\n" + "⚙️" * 30)
        click.echo("🔧 LocalLab Configuration Update")
        click.echo("⚙️" * 30)
        click.echo("\n🔄 Let's update your AI server settings!")
        click.echo("   You can modify any of your current configuration.")

    click.echo("\n" + "─" * 60)

    # Step 1: Model Selection (Required)
    # ----------------------------------
    click.echo("\n📦 Step 1: Model Selection")
    click.echo("─" * 30)
    click.echo("Choose the AI model you want to use. This is required.")

    click.echo("\n💡 How to find models:")
    click.echo("   • Visit https://huggingface.co/models")
    click.echo("   • Filter by 'Text Generation' task")
    click.echo("   • Look for models with good ratings and recent updates")
    click.echo("   • Copy the model ID (e.g., 'microsoft/phi-2')")

    click.echo("\n🔥 Popular choices:")
    click.echo("   • microsoft/phi-2 (2.7B params, good for most tasks)")
    click.echo("   • TinyLlama/TinyLlama-1.1B-Chat-v1.0 (1.1B params, lightweight)")
    click.echo("   • microsoft/DialoGPT-medium (117M params, very fast)")
    click.echo("   • Or any other HuggingFace text generation model")

    model_id = click.prompt(
        "\n🤖 Enter the HuggingFace model ID you want to use",
        default=config.get("model_id", DEFAULT_MODEL),
        show_default=True
    )
    config["model_id"] = model_id
    # Set environment variable for model
    os.environ["HUGGINGFACE_MODEL"] = model_id

    # Step 2: Model Optimization Settings (Recommended for low-spec systems)
    # -----------------------------------------------------------------------
    click.echo("\n⚡ Step 2: Model Optimization Settings")
    click.echo("─" * 40)
    if is_fresh_install:
        click.echo("These settings help optimize performance for your hardware.")
        click.echo("💡 Recommended for most users, especially those with limited GPU memory.")
        click.echo("\n🎯 Default optimization settings (recommended):")
        click.echo(f"   • Quantization: {'✅ Enabled' if ENABLE_QUANTIZATION else '❌ Disabled'}")
        if ENABLE_QUANTIZATION:
            click.echo(f"     Type: {QUANTIZATION_TYPE} (good balance of speed and memory)")
        click.echo(f"   • CPU Offloading: {'✅ Enabled' if ENABLE_CPU_OFFLOADING else '❌ Disabled'}")
        click.echo(f"   • Attention Slicing: {'✅ Enabled' if ENABLE_ATTENTION_SLICING else '❌ Disabled'}")
        click.echo(f"   • Flash Attention: {'✅ Enabled' if ENABLE_FLASH_ATTENTION else '❌ Disabled'}")
        click.echo(f"   • Better Transformer: {'✅ Enabled' if ENABLE_BETTERTRANSFORMER else '❌ Disabled'}")
        click.echo("\n💡 These defaults work well for most hardware configurations.")
    else:
        click.echo("Review and update your optimization settings.")
        click.echo("💡 These settings help optimize performance for your hardware.")

        # For existing installations, show current settings
        current_quantization = config.get('enable_quantization', ENABLE_QUANTIZATION)
        current_cpu_offload = config.get('enable_cpu_offloading', ENABLE_CPU_OFFLOADING)
        current_attention = config.get('enable_attention_slicing', ENABLE_ATTENTION_SLICING)
        current_flash = config.get('enable_flash_attention', ENABLE_FLASH_ATTENTION)
        current_transformer = config.get('enable_bettertransformer', ENABLE_BETTERTRANSFORMER)

        click.echo(f"\n🔍 Current settings:")
        click.echo(f"   • Quantization: {'✅ Enabled' if current_quantization else '❌ Disabled'}")
        if current_quantization:
            click.echo(f"     Type: {config.get('quantization_type', QUANTIZATION_TYPE)}")
        click.echo(f"   • CPU Offloading: {'✅ Enabled' if current_cpu_offload else '❌ Disabled'}")
        click.echo(f"   • Attention Slicing: {'✅ Enabled' if current_attention else '❌ Disabled'}")
        click.echo(f"   • Flash Attention: {'✅ Enabled' if current_flash else '❌ Disabled'}")
        click.echo(f"   • Better Transformer: {'✅ Enabled' if current_transformer else '❌ Disabled'}")
        if current_quantization:
            click.echo(f"    Type: {config.get('quantization_type', QUANTIZATION_TYPE)}")
        click.echo(f"  • CPU Offloading: {'✅ Enabled' if current_cpu_offload else '❌ Disabled'}")
        click.echo(f"  • Attention Slicing: {'✅ Enabled' if current_attention else '❌ Disabled'}")
        click.echo(f"  • Flash Attention: {'✅ Enabled' if current_flash else '❌ Disabled'}")
        click.echo(f"  • Better Transformer: {'✅ Enabled' if current_transformer else '❌ Disabled'}")

    # Ask if user wants to configure optimization settings
    configure_optimization = click.confirm(
        "\n🔧 Do you want to configure model optimization settings?",
        default=True
    )

    if configure_optimization:
        click.echo("\n🔧 Configuring optimization settings...")

        # Quantization settings
        config["enable_quantization"] = click.confirm(
            "📦 Enable model quantization? (Reduces memory usage)",
            default=config.get("enable_quantization", ENABLE_QUANTIZATION)
        )

        # Always set quantization_type to fix the bug
        if config["enable_quantization"]:
            # Show quantization type descriptions BEFORE prompting for selection
            click.echo("\n   📋 Available quantization types:")
            click.echo("   • fp16: Fastest, moderate memory savings")
            click.echo("   • int8: Balanced speed and memory savings")
            click.echo("   • int4: Slowest, maximum memory savings")

            config["quantization_type"] = click.prompt(
                "\n   Select quantization type",
                default=config.get("quantization_type", QUANTIZATION_TYPE),
                type=click.Choice(["fp16", "int8", "int4"]),
                show_choices=True
            )
        else:
            config["quantization_type"] = "fp16"  # Set default to prevent KeyError

        # Other optimization settings with helpful descriptions
        config["enable_cpu_offloading"] = click.confirm(
            "🖥️  Enable CPU offloading? (Moves some computation to CPU to save GPU memory)",
            default=config.get("enable_cpu_offloading", ENABLE_CPU_OFFLOADING)
        )

        config["enable_attention_slicing"] = click.confirm(
            "🔪 Enable attention slicing? (Reduces memory usage during attention computation)",
            default=config.get("enable_attention_slicing", ENABLE_ATTENTION_SLICING)
        )

        config["enable_flash_attention"] = click.confirm(
            "⚡ Enable flash attention? (Faster attention computation if supported)",
            default=config.get("enable_flash_attention", ENABLE_FLASH_ATTENTION)
        )

        config["enable_bettertransformer"] = click.confirm(
            "🚀 Enable better transformer? (Optimized transformer implementation)",
            default=config.get("enable_bettertransformer", ENABLE_BETTERTRANSFORMER)
        )

        # Set environment variables for optimization settings (with bug fix)
        os.environ["LOCALLAB_ENABLE_QUANTIZATION"] = str(config["enable_quantization"]).lower()
        os.environ["LOCALLAB_QUANTIZATION_TYPE"] = str(config.get("quantization_type", "fp16"))  # Fixed: use .get() with default
        os.environ["LOCALLAB_ENABLE_CPU_OFFLOADING"] = str(config["enable_cpu_offloading"]).lower()
        os.environ["LOCALLAB_ENABLE_ATTENTION_SLICING"] = str(config["enable_attention_slicing"]).lower()
        os.environ["LOCALLAB_ENABLE_FLASH_ATTENTION"] = str(config["enable_flash_attention"]).lower()
        os.environ["LOCALLAB_ENABLE_BETTERTRANSFORMER"] = str(config["enable_bettertransformer"]).lower()

        # Save the optimization settings to config file
        from .config import save_config
        save_config(config)

        click.echo("\n✅ Optimization settings configured successfully!")
    else:
        # If user doesn't want to configure, use the current values or defaults
        if 'enable_quantization' not in config:
            config["enable_quantization"] = ENABLE_QUANTIZATION
        # Always ensure quantization_type is set to fix the bug
        if 'quantization_type' not in config:
            config["quantization_type"] = QUANTIZATION_TYPE if config.get("enable_quantization", ENABLE_QUANTIZATION) else "fp16"
        if 'enable_cpu_offloading' not in config:
            config["enable_cpu_offloading"] = ENABLE_CPU_OFFLOADING
        if 'enable_attention_slicing' not in config:
            config["enable_attention_slicing"] = ENABLE_ATTENTION_SLICING
        if 'enable_flash_attention' not in config:
            config["enable_flash_attention"] = ENABLE_FLASH_ATTENTION
        if 'enable_bettertransformer' not in config:
            config["enable_bettertransformer"] = ENABLE_BETTERTRANSFORMER

        # Set environment variables for optimization settings (with bug fix)
        os.environ["LOCALLAB_ENABLE_QUANTIZATION"] = str(config["enable_quantization"]).lower()
        os.environ["LOCALLAB_QUANTIZATION_TYPE"] = str(config.get("quantization_type", "fp16"))  # Fixed: use .get() with default
        os.environ["LOCALLAB_ENABLE_CPU_OFFLOADING"] = str(config["enable_cpu_offloading"]).lower()
        os.environ["LOCALLAB_ENABLE_ATTENTION_SLICING"] = str(config["enable_attention_slicing"]).lower()
        os.environ["LOCALLAB_ENABLE_FLASH_ATTENTION"] = str(config["enable_flash_attention"]).lower()
        os.environ["LOCALLAB_ENABLE_BETTERTRANSFORMER"] = str(config["enable_bettertransformer"]).lower()

        # Save the optimization settings to config file
        from .config import save_config
        save_config(config)

        click.echo("\n✅ Using current optimization settings.")

    # Step 3: Advanced Settings (Optional)
    # ------------------------------------
    click.echo("\n⚙️ Step 3: Advanced Settings")
    click.echo("─" * 30)
    click.echo("These are optional settings for fine-tuning performance and behavior.")
    click.echo("Most users can skip this and use the defaults.")

    # Ask if user wants to configure advanced settings
    configure_advanced = click.confirm(
        "\n🔧 Do you want to configure advanced settings?",
        default=False
    )

    if configure_advanced:
        click.echo("\n📊 Configuring advanced settings...")

        # Port configuration (moved here as it's more advanced)
        config["port"] = click.prompt(
            "🔌 Server port",
            default=config.get("port", 8000),
            type=int
        )

        # Model timeout
        config["model_timeout"] = click.prompt(
            "⏱️  Model timeout (seconds)",
            default=config.get("model_timeout", 3600),
            type=int
        )

        # Response Quality Settings
        click.echo("\n🎯 Response Quality Settings:")

        config["max_length"] = click.prompt(
            "   📏 Maximum response length (tokens)",
            default=config.get("max_length", 8192),
            type=int
        )

        config["temperature"] = click.prompt(
            "   🌡️  Temperature (0.1-1.0, higher = more creative)",
            default=config.get("temperature", 0.7),
            type=float
        )

        config["top_p"] = click.prompt(
            "   🎯 Top-p (0.1-1.0, higher = more diverse)",
            default=config.get("top_p", 0.9),
            type=float
        )

        config["top_k"] = click.prompt(
            "   🔢 Top-k (1-100, higher = more diverse vocabulary)",
            default=config.get("top_k", 80),
            type=int
        )

        config["repetition_penalty"] = click.prompt(
            "   🔄 Repetition penalty (1.0-2.0, higher = less repetition)",
            default=config.get("repetition_penalty", 1.15),
            type=float
        )

        config["max_time"] = click.prompt(
            "   ⏰ Maximum generation time (seconds)",
            default=config.get("max_time", 120.0),
            type=float
        )

        click.echo("\n✅ Advanced settings configured!")
    else:
        # Use defaults for advanced settings
        if 'port' not in config:
            config["port"] = 8000
        if 'model_timeout' not in config:
            config["model_timeout"] = 3600
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

        click.echo("\n✅ Using default advanced settings.")

    # Set environment variables for these settings
    os.environ["DEFAULT_MAX_LENGTH"] = str(config["max_length"])
    os.environ["DEFAULT_TEMPERATURE"] = str(config["temperature"])
    os.environ["DEFAULT_TOP_P"] = str(config["top_p"])
    os.environ["DEFAULT_TOP_K"] = str(config["top_k"])
    os.environ["DEFAULT_REPETITION_PENALTY"] = str(config["repetition_penalty"])
    os.environ["DEFAULT_MAX_TIME"] = str(config["max_time"])

    # Step 4: Authentication & Access
    # --------------------------------
    click.echo("\n🔐 Step 4: Authentication & Access")
    click.echo("─" * 35)

    # HuggingFace Token
    click.echo("\n🤗 HuggingFace Token Setup")
    click.echo("   ─────────────────────────")

    current_hf_token = config.get("huggingface_token") or get_env_var(HF_TOKEN_ENV)

    if current_hf_token:
        click.echo(f"\n   📋 Current token: {current_hf_token[:10]}...{current_hf_token[-4:] if len(current_hf_token) > 14 else ''}")
    else:
        click.echo("\n   📋 No HuggingFace token found.")

    click.echo("\n   💡 Why do you need this?")
    click.echo("      A token is required to download models from HuggingFace.")
    click.echo("      This allows you to access both public and private models.")

    click.echo("\n   🔗 How to get your token:")
    click.echo("      1. Visit: https://huggingface.co/settings/tokens")
    click.echo("      2. Click 'New token' and create a 'Read' token")
    click.echo("      3. Copy the token and paste it below")

    hf_token = click.prompt(
        "\n   🔑 Enter your HuggingFace token",
        default=current_hf_token or "",
        type=str,
        show_default=False
    )

    if hf_token and hf_token.strip():
        if len(hf_token.strip()) < 20:
            click.echo("\n   ⚠️  Warning: Token seems too short. Please verify it's correct.")

        token_str = str(hf_token).strip()
        config["huggingface_token"] = token_str
        set_env_var(HF_TOKEN_ENV, token_str)
        click.echo("\n   ✅ HuggingFace token saved successfully!")
    else:
        click.echo("\n   ⚠️  No token provided. Some models may not be accessible.")

    # Ngrok Configuration
    click.echo("\n\n🌐 Ngrok Setup (Public Access)")
    click.echo("   ──────────────────────────────")

    if in_colab:
        click.echo("\n   💡 Why use Ngrok?")
        click.echo("      Ngrok is recommended for Google Colab to access your server publicly.")
        click.echo("      It creates a secure tunnel to your local server.")
    else:
        click.echo("\n   💡 Why use Ngrok?")
        click.echo("      Ngrok allows you to access your server from anywhere on the internet.")
        click.echo("      Perfect for sharing your AI server with others or accessing remotely.")

    use_ngrok = click.confirm(
        "\n   🌍 Enable public access via ngrok?",
        default=config.get("use_ngrok", in_colab)
    )
    config["use_ngrok"] = use_ngrok
    os.environ["LOCALLAB_USE_NGROK"] = str(use_ngrok).lower()

    if use_ngrok:
        current_token = config.get("ngrok_auth_token") or get_env_var(NGROK_TOKEN_ENV)

        if current_token:
            click.echo(f"\n   📋 Current ngrok token: {current_token[:8]}...{current_token[-4:] if len(current_token) > 12 else ''}")
        else:
            click.echo("\n   📋 No ngrok token found.")

        click.echo("\n   🔗 How to get your free ngrok token:")
        click.echo("      1. Visit: https://dashboard.ngrok.com/get-started/your-authtoken")
        click.echo("      2. Sign up for a free account if you don't have one")
        click.echo("      3. Copy your authtoken and paste it below")

        ngrok_auth_token = click.prompt(
            "\n   🔑 Enter your ngrok auth token",
            default=current_token or "",
            type=str,
            show_default=False
        )

        if ngrok_auth_token and ngrok_auth_token.strip():
            token_str = str(ngrok_auth_token).strip()
            config["ngrok_auth_token"] = token_str
            # Set both environment variables to ensure compatibility
            os.environ["NGROK_AUTHTOKEN"] = token_str
            os.environ["LOCALLAB_NGROK_AUTH_TOKEN"] = token_str
            click.echo("\n   ✅ Ngrok token saved successfully!")
        else:
            click.echo("\n   ⚠️  No ngrok token provided. Public access will not be available.")
            config["use_ngrok"] = False
            os.environ["LOCALLAB_USE_NGROK"] = "false"
    else:
        click.echo("\n   ℹ️  Ngrok disabled. Server will only be accessible locally.")

    # Save all configuration
    from .config import save_config
    save_config(config)

    # Step 5: Configuration Summary & Completion
    # ------------------------------------------
    if is_fresh_install:
        click.echo("\n" + "🎉" * 30)
        click.echo("✨ Setup Complete! Welcome to LocalLab! ✨")
        click.echo("🎉" * 30)
        click.echo("\n🎊 Congratulations! Your AI server is ready to go!")
    else:
        click.echo("\n" + "✅" * 30)
        click.echo("🔧 Configuration Updated Successfully!")
        click.echo("✅" * 30)
        click.echo("\n🔄 Your settings have been updated!")

    click.echo("\n📋 Configuration Summary:")
    click.echo("   ─────────────────────")
    click.echo(f"   🤖 Model: {config.get('model_id', 'Not set')}")
    click.echo(f"   🌐 Port: {config.get('port', 8000)}")

    # Optimization summary
    click.echo(f"\n   ⚡ Optimization:")
    quantization = config.get('enable_quantization', False)
    click.echo(f"      • Quantization: {'✅ Enabled' if quantization else '❌ Disabled'}")
    if quantization:
        click.echo(f"        Type: {config.get('quantization_type', 'fp16')}")
    click.echo(f"      • CPU Offloading: {'✅ Enabled' if config.get('enable_cpu_offloading', False) else '❌ Disabled'}")
    click.echo(f"      • Attention Slicing: {'✅ Enabled' if config.get('enable_attention_slicing', False) else '❌ Disabled'}")
    click.echo(f"      • Flash Attention: {'✅ Enabled' if config.get('enable_flash_attention', False) else '❌ Disabled'}")

    # Access summary
    click.echo(f"\n   🔐 Access:")
    click.echo(f"      • HuggingFace Token: {'✅ Set' if config.get('huggingface_token') else '❌ Not set'}")
    click.echo(f"      • Public Access (Ngrok): {'✅ Enabled' if config.get('use_ngrok', False) else '❌ Disabled'}")

    click.echo("\n" + "─" * 60)
    click.echo("🚀 Your LocalLab server is now configured!")
    click.echo("💡 Next step: Run 'locallab start' to launch your AI server.")

    if config.get('use_ngrok', False):
        click.echo("🌐 With ngrok enabled, your server will be accessible from anywhere!")
    else:
        port = config.get('port', 8000)
        click.echo(f"🏠 Your server will be accessible locally at http://localhost:{port}")

    if is_fresh_install:
        click.echo("\n🎓 Pro tip: You can run 'locallab config' anytime to change these settings!")

    return config