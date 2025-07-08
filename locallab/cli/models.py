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
from ..utils.huggingface_search import hf_searcher
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
@click.option('--search', help='Search models by keywords, tags, or description')
@click.option('--limit', type=int, default=20, help='Maximum number of models to show (default: 20)')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table',
              help='Output format (table or json)')
@click.option('--registry-only', is_flag=True, help='Show only LocalLab registry models')
@click.option('--hub-only', is_flag=True, help='Show only HuggingFace Hub models')
@click.option('--sort', type=click.Choice(['downloads', 'likes', 'recent']), default='downloads',
              help='Sort HuggingFace models by downloads, likes, or recent updates')
@click.option('--tags', help='Filter by tags (comma-separated, e.g., "conversational,chat")')
def discover(search: Optional[str], limit: int, output_format: str, registry_only: bool,
             hub_only: bool, sort: str, tags: Optional[str]):
    """Discover available models from HuggingFace Hub and LocalLab registry"""
    try:
        console.print("🔍 Discovering available models...", style="blue")

        all_models = []

        # Get registry models (unless hub-only is specified)
        if not hub_only:
            registry_models = _get_registry_models()
            all_models.extend(registry_models)
            console.print(f"📚 Found {len(registry_models)} LocalLab registry models", style="dim")

        # Get HuggingFace Hub models (unless registry-only is specified)
        if not registry_only:
            hf_models, hf_success = _get_huggingface_models(search, limit, sort, tags)
            if hf_success:
                all_models.extend(hf_models)
                console.print(f"🤗 Found {len(hf_models)} HuggingFace Hub models", style="dim")
            else:
                console.print("⚠️  Could not search HuggingFace Hub (network issue or missing dependencies)", style="yellow")
                if search or tags:
                    console.print("💡 Try using --registry-only to search LocalLab registry models only.", style="dim")

        # Apply search filter to registry models if search is specified
        if search and not hub_only:
            search_lower = search.lower()
            registry_filtered = [
                m for m in all_models
                if m.get("type") == "Registry" and (
                    search_lower in m["name"].lower() or
                    search_lower in m["description"].lower()
                )
            ]
            # Keep HF models and filtered registry models
            hf_models_in_list = [m for m in all_models if m.get("type") == "HuggingFace"]
            all_models = registry_filtered + hf_models_in_list

        # Check which models are already cached
        cached_models = model_cache_manager.get_cached_models()
        cached_ids = {m["id"] for m in cached_models}

        for model in all_models:
            model["is_cached"] = model["id"] in cached_ids

        # Sort models: Registry first, then by specified sort order
        all_models.sort(key=lambda x: (
            0 if x.get("type") == "Registry" else 1,  # Registry models first
            -x.get("downloads", 0) if sort == "downloads" else 0,
            -x.get("likes", 0) if sort == "likes" else 0,
            x.get("updated_at", "") if sort == "recent" else ""
        ))

        # Apply final limit
        all_models = all_models[:limit]

        if output_format == 'json':
            click.echo(json.dumps(all_models, indent=2))
            return

        if not all_models:
            console.print("📭 No models found matching your criteria.", style="yellow")
            if not registry_only:
                console.print("💡 Try adjusting your search terms or check your internet connection.", style="dim")
            return

        # Create table
        table = Table(title="🌟 Available Models")
        table.add_column("Model ID", style="cyan", no_wrap=True, max_width=30)
        table.add_column("Name", style="green", max_width=20)
        table.add_column("Size", style="magenta", justify="right")
        table.add_column("Type", style="blue")
        table.add_column("Downloads", style="yellow", justify="right")
        table.add_column("Status", style="bright_green")
        table.add_column("Description", style="dim", max_width=40)

        for model in all_models:
            status = "✅ Cached" if model["is_cached"] else "📥 Available"
            downloads_str = ""
            if model.get("downloads", 0) > 0:
                downloads = model["downloads"]
                if downloads >= 1000000:
                    downloads_str = f"{downloads/1000000:.1f}M"
                elif downloads >= 1000:
                    downloads_str = f"{downloads/1000:.1f}K"
                else:
                    downloads_str = str(downloads)

            table.add_row(
                model["id"],
                model["name"],
                model.get("size", "Unknown"),
                model.get("type", "Unknown"),
                downloads_str,
                status,
                model["description"][:50] + "..." if len(model["description"]) > 50 else model["description"]
            )

        console.print(table)

        # Show summary
        cached_count = sum(1 for m in all_models if m["is_cached"])
        registry_count = sum(1 for m in all_models if m.get("type") == "Registry")
        hf_count = len(all_models) - registry_count

        console.print(f"\n📊 Found {len(all_models)} models:")
        console.print(f"   • {registry_count} LocalLab registry models")
        console.print(f"   • {hf_count} HuggingFace Hub models")
        console.print(f"   • {cached_count} already cached locally")
        console.print("\n💡 Use 'locallab models download <model_id>' to download a model locally.")

        if not registry_only and hf_count > 0:
            console.print("🔍 Use --search to find specific models or --tags to filter by categories.")

    except Exception as e:
        logger.error(f"Error discovering models: {e}")
        console.print(f"❌ Error discovering models: {str(e)}", style="red")
        sys.exit(1)

def _get_registry_models():
    """Get models from LocalLab registry"""
    registry_models = []

    for model_id, config in MODEL_REGISTRY.items():
        model_info = {
            "id": model_id,
            "name": config.get("name", model_id),
            "description": config.get("description", "LocalLab registry model"),
            "size": config.get("size", "Unknown"),
            "type": "Registry",
            "downloads": 0,  # Registry models don't have download counts
            "likes": 0,
            "requirements": config.get("requirements", {}),
            "is_cached": False,
            "tags": [],
            "author": "LocalLab",
            "updated_at": ""
        }
        registry_models.append(model_info)

    return registry_models

def _get_huggingface_models(search: Optional[str], limit: int, sort: str, tags: Optional[str]):
    """Get models from HuggingFace Hub"""
    try:
        # Parse tags if provided
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]

        # Convert sort parameter
        hf_sort = "downloads"
        if sort == "likes":
            hf_sort = "likes"
        elif sort == "recent":
            hf_sort = "lastModified"

        # Search HuggingFace Hub
        if search:
            hf_models, success = hf_searcher.search_models(
                search_query=search, limit=limit, sort=hf_sort
            )
        elif tag_list:
            hf_models, success = hf_searcher.search_models(
                search_query=None, limit=limit, sort=hf_sort, filter_tags=tag_list
            )
        else:
            hf_models, success = hf_searcher.search_models(
                search_query=None, limit=limit, sort=hf_sort
            )

        if not success:
            return [], False

        # Convert to our format
        converted_models = []
        for hf_model in hf_models:
            model_info = {
                "id": hf_model.id,
                "name": hf_model.name,
                "description": hf_model.description,
                "size": hf_model.size_formatted,
                "type": "HuggingFace",
                "downloads": hf_model.downloads,
                "likes": hf_model.likes,
                "is_cached": False,
                "tags": hf_model.tags,
                "author": hf_model.author,
                "updated_at": hf_model.updated_at or "",
                "pipeline_tag": hf_model.pipeline_tag,
                "library_name": hf_model.library_name
            }
            converted_models.append(model_info)

        return converted_models, True

    except Exception as e:
        logger.debug(f"Error getting HuggingFace models: {e}")
        return [], False

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
