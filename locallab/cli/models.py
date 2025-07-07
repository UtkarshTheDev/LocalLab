"""
Model management CLI commands for LocalLab
"""

import sys
import json
import asyncio
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Confirm

# Import LocalLab components
from ..config import MODEL_REGISTRY, get_hf_token
from ..utils.system import format_model_size, get_system_resources
from ..utils.progress import configure_hf_hub_progress
from ..utils.model_cache import model_cache_manager
from ..logger.logger import logger

# Initialize rich console
console = Console()

# Use the centralized cache manager

@click.group()
def models():
    """Manage AI models for LocalLab"""
    pass

@models.command()
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table',
              help='Output format (table or json)')
@click.option('--registry-only', is_flag=True, help='Show only registry models')
@click.option('--custom-only', is_flag=True, help='Show only custom models')
def list(output_format: str, registry_only: bool, custom_only: bool):
    """List locally cached models"""
    try:
        cached_models = model_cache_manager.get_cached_models()

        # Add registry information
        for model in cached_models:
            model["is_registry_model"] = model["id"] in MODEL_REGISTRY
            if model["is_registry_model"]:
                registry_info = MODEL_REGISTRY[model["id"]]
                model["name"] = registry_info.get("name", model["name"])
                model["description"] = registry_info.get("description", "Registry model")
            else:
                model["description"] = "Custom model"
        
        # Apply filters
        if registry_only:
            cached_models = [m for m in cached_models if m["is_registry_model"]]
        elif custom_only:
            cached_models = [m for m in cached_models if not m["is_registry_model"]]
        
        if output_format == 'json':
            click.echo(json.dumps(cached_models, indent=2))
            return
        
        if not cached_models:
            console.print("📭 No models found in local cache.", style="yellow")
            console.print("\n💡 Use 'locallab models download <model_id>' to download models locally.")
            return
        
        # Create table
        table = Table(title="🤖 Locally Cached Models")
        table.add_column("Model", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Size", justify="right", style="magenta")
        table.add_column("Type", style="blue")
        table.add_column("Cached", style="dim")
        
        for model in cached_models:
            model_type = "Registry" if model["is_registry_model"] else "Custom"
            table.add_row(
                model["id"],
                model["name"],
                model["size_formatted"],
                model_type,
                model["cached_at"]
            )
        
        console.print(table)
        
        # Show summary
        total_size = sum(m["size"] for m in cached_models)
        console.print(f"\n📊 Total: {len(cached_models)} models, {format_model_size(total_size)}")
        
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        console.print(f"❌ Error listing models: {str(e)}", style="red")
        sys.exit(1)

@models.command()
@click.argument('model_id')
@click.option('--force', is_flag=True, help='Force download even if model exists')
@click.option('--no-cache-update', is_flag=True, help='Skip updating cache metadata')
def download(model_id: str, force: bool, no_cache_update: bool):
    """Download a model locally"""
    try:
        # Check if model already exists
        existing_model = model_cache_manager.get_model_info(model_id)
        
        if existing_model and not force:
            console.print(f"✅ Model '{model_id}' is already cached locally.", style="green")
            console.print(f"📁 Location: {existing_model['path']}")
            console.print(f"📏 Size: {existing_model['size_formatted']}")
            console.print("\n💡 Use --force to re-download the model.")
            return
        
        # Configure HuggingFace progress bars
        configure_hf_hub_progress()
        
        console.print(f"🚀 Starting download of model: {model_id}", style="green")
        
        # Run the download in async context
        asyncio.run(_download_model_async(model_id, no_cache_update))
        
    except KeyboardInterrupt:
        console.print("\n🛑 Download cancelled by user.", style="yellow")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error downloading model {model_id}: {e}")
        console.print(f"❌ Error downloading model: {str(e)}", style="red")
        sys.exit(1)

async def _download_model_async(model_id: str, no_cache_update: bool):
    """Async helper for model download"""
    from ..model_manager import ModelManager
    
    # Create a temporary model manager for download
    manager = ModelManager()
    
    try:
        # Load the model (this will download it if not cached)
        await manager.load_model(model_id)
        
        # Update cache metadata if not skipped
        if not no_cache_update:
            model_cache_manager.record_model_download(model_id, "cli")
        
        console.print(f"✅ Model '{model_id}' downloaded successfully!", style="green")
        
        # Show model info
        downloaded_model = model_cache_manager.get_model_info(model_id)
        if downloaded_model:
            console.print(f"📁 Location: {downloaded_model['path']}")
            console.print(f"📏 Size: {downloaded_model['size_formatted']}")
        
    except Exception as e:
        raise e
    finally:
        # Clean up the temporary model manager
        if manager.model:
            del manager.model
            manager.model = None
            manager.current_model = None
            # Clear GPU cache if available
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

@models.command()
@click.argument('model_id')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
def remove(model_id: str, force: bool):
    """Remove a locally cached model"""
    try:
        model_to_remove = model_cache_manager.get_model_info(model_id)
        
        if not model_to_remove:
            console.print(f"❌ Model '{model_id}' not found in local cache.", style="red")
            console.print("\n💡 Use 'locallab models list' to see available models.")
            return
        
        # Show model info
        console.print(f"🗑️  Model to remove: {model_to_remove['name']}", style="yellow")
        console.print(f"📁 Location: {model_to_remove['path']}")
        console.print(f"📏 Size: {model_to_remove['size_formatted']}")
        
        # Confirm removal
        if not force:
            if not Confirm.ask(f"\n⚠️  Are you sure you want to remove '{model_id}'?"):
                console.print("❌ Removal cancelled.", style="yellow")
                return
        
        # Remove the model using cache manager
        if model_cache_manager.remove_model(model_id):
            console.print(f"✅ Model '{model_id}' removed successfully!", style="green")
        else:
            console.print(f"⚠️  Failed to remove model '{model_id}'", style="yellow")
        
    except Exception as e:
        logger.error(f"Error removing model {model_id}: {e}")
        console.print(f"❌ Error removing model: {str(e)}", style="red")
        sys.exit(1)

@models.command()
@click.option('--search', help='Search models by name or description')
@click.option('--limit', type=int, default=20, help='Maximum number of models to show')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table',
              help='Output format (table or json)')
def discover(search: Optional[str], limit: int, output_format: str):
    """Discover available models from HuggingFace Hub and registry"""
    try:
        console.print("🔍 Discovering available models...", style="blue")

        # Start with registry models
        available_models = []

        # Add registry models
        for model_id, config in MODEL_REGISTRY.items():
            model_info = {
                "id": model_id,
                "name": config.get("name", model_id),
                "description": config.get("description", ""),
                "size": config.get("size", "Unknown"),
                "type": "Registry",
                "requirements": config.get("requirements", {}),
                "is_cached": False
            }
            available_models.append(model_info)

        # Check which models are already cached
        cached_models = model_cache_manager.get_cached_models()
        cached_ids = {m["id"] for m in cached_models}

        for model in available_models:
            model["is_cached"] = model["id"] in cached_ids

        # Apply search filter
        if search:
            search_lower = search.lower()
            available_models = [
                m for m in available_models
                if search_lower in m["name"].lower() or search_lower in m["description"].lower()
            ]

        # Limit results
        available_models = available_models[:limit]

        if output_format == 'json':
            click.echo(json.dumps(available_models, indent=2))
            return

        if not available_models:
            console.print("📭 No models found matching your criteria.", style="yellow")
            return

        # Create table
        table = Table(title="🌟 Available Models")
        table.add_column("Model ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Size", style="magenta")
        table.add_column("Type", style="blue")
        table.add_column("Status", style="yellow")
        table.add_column("Description", style="dim")

        for model in available_models:
            status = "✅ Cached" if model["is_cached"] else "📥 Available"
            table.add_row(
                model["id"],
                model["name"],
                model["size"],
                model["type"],
                status,
                model["description"][:50] + "..." if len(model["description"]) > 50 else model["description"]
            )

        console.print(table)

        # Show summary
        cached_count = sum(1 for m in available_models if m["is_cached"])
        console.print(f"\n📊 Found {len(available_models)} models ({cached_count} cached, {len(available_models) - cached_count} available for download)")
        console.print("\n💡 Use 'locallab models download <model_id>' to download a model locally.")

    except Exception as e:
        logger.error(f"Error discovering models: {e}")
        console.print(f"❌ Error discovering models: {str(e)}", style="red")
        sys.exit(1)

@models.command()
@click.argument('model_id')
def info(model_id: str):
    """Show detailed information about a model"""
    try:
        # Check if model is in registry
        registry_info = MODEL_REGISTRY.get(model_id)

        # Check if model is cached locally
        cached_info = model_cache_manager.get_model_info(model_id)

        if not registry_info and not cached_info:
            console.print(f"❌ Model '{model_id}' not found in registry or local cache.", style="red")
            console.print("\n💡 Use 'locallab models discover' to find available models.")
            return

        # Create info panel
        info_text = Text()
        info_text.append(f"🤖 Model: {model_id}\n", style="bold cyan")

        if registry_info:
            info_text.append(f"📝 Name: {registry_info.get('name', model_id)}\n", style="green")
            info_text.append(f"📄 Description: {registry_info.get('description', 'No description')}\n")
            info_text.append(f"📏 Size: {registry_info.get('size', 'Unknown')}\n", style="magenta")

            # Requirements
            requirements = registry_info.get('requirements', {})
            if requirements:
                info_text.append("\n💾 Requirements:\n", style="bold yellow")
                if 'min_ram' in requirements:
                    info_text.append(f"  • RAM: {requirements['min_ram']} GB\n")
                if 'min_vram' in requirements:
                    info_text.append(f"  • VRAM: {requirements['min_vram']} GB\n")

            # Fallback model
            fallback = registry_info.get('fallback')
            if fallback:
                info_text.append(f"\n🔄 Fallback: {fallback}\n", style="dim")

        # Local cache info
        if cached_info:
            info_text.append(f"\n📁 Local Cache:\n", style="bold blue")
            info_text.append(f"  • Status: ✅ Cached\n", style="green")
            info_text.append(f"  • Size: {cached_info['size_formatted']}\n")
            info_text.append(f"  • Path: {cached_info['path']}\n", style="dim")
            info_text.append(f"  • Cached: {cached_info['cached_at']}\n", style="dim")
        else:
            info_text.append(f"\n📁 Local Cache:\n", style="bold blue")
            info_text.append(f"  • Status: ❌ Not cached\n", style="red")

        # System compatibility
        info_text.append(f"\n🖥️  System Compatibility:\n", style="bold yellow")
        try:
            system_resources = get_system_resources()
            ram_gb = system_resources.get('ram_total', 0) / (1024 * 1024 * 1024)
            info_text.append(f"  • Available RAM: {ram_gb:.1f} GB\n")

            if system_resources.get('gpu_available', False):
                gpu_info = system_resources.get('gpu_info', [])
                if gpu_info:
                    vram_gb = gpu_info[0].get('total_memory', 0) / (1024 * 1024 * 1024)
                    info_text.append(f"  • Available VRAM: {vram_gb:.1f} GB\n")
            else:
                info_text.append(f"  • GPU: Not available\n")

            # Check compatibility
            if registry_info and 'requirements' in registry_info:
                req = registry_info['requirements']
                ram_ok = ram_gb >= req.get('min_ram', 0)
                vram_ok = True
                if 'min_vram' in req and system_resources.get('gpu_available', False):
                    vram_ok = vram_gb >= req['min_vram']

                if ram_ok and vram_ok:
                    info_text.append(f"  • Compatibility: ✅ Compatible\n", style="green")
                else:
                    info_text.append(f"  • Compatibility: ⚠️  May have issues\n", style="yellow")
        except Exception:
            info_text.append(f"  • Status: Unable to check\n", style="dim")

        panel = Panel(info_text, title=f"Model Information", border_style="blue")
        console.print(panel)

        # Show available actions
        actions = []
        if not cached_info:
            actions.append("locallab models download " + model_id)
        else:
            actions.append("locallab models remove " + model_id)

        if actions:
            console.print("\n💡 Available actions:")
            for action in actions:
                console.print(f"  • {action}", style="dim")

    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        console.print(f"❌ Error getting model info: {str(e)}", style="red")
        sys.exit(1)

@models.command()
def clean():
    """Clean up orphaned model cache files"""
    try:
        console.print("🧹 Cleaning up model cache...", style="blue")

        # Find orphaned files using cache manager
        orphaned_items = model_cache_manager.find_orphaned_files()

        if not orphaned_items:
            console.print("✅ Cache is clean - no orphaned files found.", style="green")
            return

        total_size_freed = sum(item["size"] for item in orphaned_items)

        # Show what will be cleaned
        console.print(f"🗑️  Found {len(orphaned_items)} orphaned items ({format_model_size(total_size_freed)}):")
        for item in orphaned_items[:5]:  # Show first 5
            console.print(f"  • {item['description']} ({format_model_size(item['size'])})", style="dim")

        if len(orphaned_items) > 5:
            console.print(f"  • ... and {len(orphaned_items) - 5} more", style="dim")

        # Confirm cleanup
        if not Confirm.ask(f"\n⚠️  Remove {len(orphaned_items)} orphaned items?"):
            console.print("❌ Cleanup cancelled.", style="yellow")
            return

        # Perform cleanup using cache manager
        removed_count, size_freed = model_cache_manager.cleanup_orphaned_files()

        console.print(f"✅ Cleanup complete! Removed {removed_count} items, freed {format_model_size(size_freed)}.", style="green")

    except Exception as e:
        logger.error(f"Error cleaning cache: {e}")
        console.print(f"❌ Error cleaning cache: {str(e)}", style="red")
        sys.exit(1)
