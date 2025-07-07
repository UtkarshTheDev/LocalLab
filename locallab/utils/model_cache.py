"""
Model cache management utilities for LocalLab
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from ..logger.logger import logger
from .system import format_model_size

class ModelCacheManager:
    """Manages the local model cache for LocalLab"""
    
    def __init__(self):
        self.cache_dir = self._get_cache_dir()
        self.metadata_file = self._get_metadata_file()
        self._ensure_cache_structure()
    
    def _get_cache_dir(self) -> Path:
        """Get the model cache directory"""
        # Use HuggingFace Hub's default cache directory
        cache_dir = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
        return Path(cache_dir) / "hub"
    
    def _get_metadata_file(self) -> Path:
        """Get the model metadata cache file path"""
        config_dir = Path.home() / ".locallab"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "model_cache.json"
    
    def _ensure_cache_structure(self):
        """Ensure cache directory structure exists"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def load_metadata(self) -> Dict[str, Any]:
        """Load model cache metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load model cache metadata: {e}")
        return {}
    
    def save_metadata(self, metadata: Dict[str, Any]):
        """Save model cache metadata"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save model cache metadata: {e}")
    
    def get_cached_models(self) -> List[Dict[str, Any]]:
        """Get list of locally cached models with detailed information"""
        cached_models = []
        metadata = self.load_metadata()
        
        if not self.cache_dir.exists():
            return cached_models
        
        # Scan for model directories
        for model_dir in self.cache_dir.iterdir():
            if model_dir.is_dir() and model_dir.name.startswith("models--"):
                try:
                    model_info = self._analyze_model_directory(model_dir, metadata)
                    if model_info:
                        cached_models.append(model_info)
                except Exception as e:
                    logger.warning(f"Error analyzing model directory {model_dir}: {e}")
        
        return sorted(cached_models, key=lambda x: x["name"])
    
    def _analyze_model_directory(self, model_dir: Path, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze a model directory and extract information"""
        # Extract model name from directory name
        model_name = model_dir.name.replace("models--", "").replace("--", "/")
        
        # Calculate total size
        total_size = 0
        file_count = 0
        model_files = []
        
        for file_path in model_dir.rglob("*"):
            if file_path.is_file():
                file_size = file_path.stat().st_size
                total_size += file_size
                file_count += 1
                
                # Track model files specifically
                if file_path.suffix in ['.bin', '.safetensors', '.pt', '.pth', '.onnx']:
                    model_files.append({
                        "name": file_path.name,
                        "size": file_size,
                        "path": str(file_path.relative_to(model_dir))
                    })
        
        # Get cached metadata
        cached_metadata = metadata.get(model_name, {})
        
        # Get directory modification time as fallback for cache time
        cache_time = cached_metadata.get("cached_at")
        if not cache_time:
            try:
                cache_time = datetime.fromtimestamp(model_dir.stat().st_mtime).isoformat()
            except Exception:
                cache_time = "Unknown"
        
        return {
            "id": model_name,
            "name": model_name.split("/")[-1] if "/" in model_name else model_name,
            "full_name": model_name,
            "size": total_size,
            "size_formatted": format_model_size(total_size),
            "file_count": file_count,
            "model_files": model_files,
            "path": str(model_dir),
            "cached_at": cache_time,
            "download_method": cached_metadata.get("download_method", "unknown"),
            "last_accessed": cached_metadata.get("last_accessed"),
            "access_count": cached_metadata.get("access_count", 0)
        }
    
    def update_model_metadata(self, model_id: str, updates: Dict[str, Any]):
        """Update metadata for a specific model"""
        metadata = self.load_metadata()
        
        if model_id not in metadata:
            metadata[model_id] = {}
        
        metadata[model_id].update(updates)
        metadata[model_id]["last_updated"] = datetime.now().isoformat()
        
        self.save_metadata(metadata)
    
    def record_model_access(self, model_id: str):
        """Record that a model was accessed"""
        updates = {
            "last_accessed": datetime.now().isoformat(),
            "access_count": self.load_metadata().get(model_id, {}).get("access_count", 0) + 1
        }
        self.update_model_metadata(model_id, updates)
    
    def record_model_download(self, model_id: str, download_method: str = "cli"):
        """Record that a model was downloaded"""
        updates = {
            "cached_at": datetime.now().isoformat(),
            "download_method": download_method
        }
        self.update_model_metadata(model_id, updates)
    
    def remove_model(self, model_id: str) -> bool:
        """Remove a model from cache"""
        cached_models = self.get_cached_models()
        model_to_remove = next((m for m in cached_models if m["id"] == model_id), None)
        
        if not model_to_remove:
            return False
        
        try:
            # Remove the model directory
            model_path = Path(model_to_remove['path'])
            if model_path.exists():
                shutil.rmtree(model_path)
            
            # Remove from metadata
            metadata = self.load_metadata()
            if model_id in metadata:
                del metadata[model_id]
                self.save_metadata(metadata)
            
            return True
        except Exception as e:
            logger.error(f"Error removing model {model_id}: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cached_models = self.get_cached_models()
        
        total_size = sum(m["size"] for m in cached_models)
        total_files = sum(m["file_count"] for m in cached_models)
        
        # Group by download method
        download_methods = {}
        for model in cached_models:
            method = model["download_method"]
            if method not in download_methods:
                download_methods[method] = {"count": 0, "size": 0}
            download_methods[method]["count"] += 1
            download_methods[method]["size"] += model["size"]
        
        return {
            "total_models": len(cached_models),
            "total_size": total_size,
            "total_size_formatted": format_model_size(total_size),
            "total_files": total_files,
            "cache_directory": str(self.cache_dir),
            "download_methods": download_methods,
            "models": cached_models
        }
    
    def find_orphaned_files(self) -> List[Dict[str, Any]]:
        """Find orphaned cache files that can be cleaned up"""
        orphaned_items = []
        
        if not self.cache_dir.exists():
            return orphaned_items
        
        for item in self.cache_dir.iterdir():
            if item.is_dir():
                if item.name.startswith("models--"):
                    # Check if it has any actual model files
                    has_model_files = any(
                        f.suffix in ['.bin', '.safetensors', '.pt', '.pth', '.onnx']
                        for f in item.rglob("*") if f.is_file()
                    )
                    if not has_model_files:
                        size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                        orphaned_items.append({
                            "path": item,
                            "size": size,
                            "type": "empty_model_dir",
                            "description": f"Empty model directory: {item.name}"
                        })
                else:
                    # Unknown directory
                    size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                    orphaned_items.append({
                        "path": item,
                        "size": size,
                        "type": "unknown_dir",
                        "description": f"Unknown directory: {item.name}"
                    })
            elif item.is_file():
                # Check for temporary or lock files
                if item.suffix in ['.tmp', '.lock', '.partial']:
                    orphaned_items.append({
                        "path": item,
                        "size": item.stat().st_size,
                        "type": "temp_file",
                        "description": f"Temporary file: {item.name}"
                    })
        
        return orphaned_items
    
    def cleanup_orphaned_files(self) -> Tuple[int, int]:
        """Clean up orphaned files and return (count_removed, size_freed)"""
        orphaned_items = self.find_orphaned_files()
        
        removed_count = 0
        size_freed = 0
        
        for item in orphaned_items:
            try:
                if item["path"].is_dir():
                    shutil.rmtree(item["path"])
                else:
                    item["path"].unlink()
                removed_count += 1
                size_freed += item["size"]
            except Exception as e:
                logger.warning(f"Failed to remove {item['path']}: {e}")
        
        return removed_count, size_freed
    
    def is_model_cached(self, model_id: str) -> bool:
        """Check if a model is cached locally"""
        cached_models = self.get_cached_models()
        return any(m["id"] == model_id for m in cached_models)
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific cached model"""
        cached_models = self.get_cached_models()
        return next((m for m in cached_models if m["id"] == model_id), None)

# Global instance
model_cache_manager = ModelCacheManager()
