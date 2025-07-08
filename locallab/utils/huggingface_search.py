"""
HuggingFace Hub search and discovery utilities for LocalLab
"""

import time
import requests
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ..config import get_hf_token
from ..logger.logger import logger
from ..utils.system import format_model_size

@dataclass
class HuggingFaceModel:
    """Represents a model from HuggingFace Hub"""
    id: str
    name: str
    description: str
    downloads: int
    likes: int
    tags: List[str]
    size_bytes: Optional[int] = None
    size_formatted: str = "Unknown"
    author: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    pipeline_tag: Optional[str] = None
    library_name: Optional[str] = None
    is_private: bool = False

class HuggingFaceSearcher:
    """Search and discover models from HuggingFace Hub"""
    
    def __init__(self):
        self.last_request_time = 0
        self.min_request_interval = 0.1  # Rate limiting: 10 requests per second max
        
    def _rate_limit(self):
        """Simple rate limiting to avoid hitting API limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def search_models(
        self, 
        search_query: Optional[str] = None,
        limit: int = 20,
        sort: str = "downloads",
        filter_tags: Optional[List[str]] = None,
        pipeline_tag: Optional[str] = None
    ) -> Tuple[List[HuggingFaceModel], bool]:
        """
        Search for models on HuggingFace Hub
        
        Returns:
            Tuple of (models_list, success_flag)
        """
        try:
            from huggingface_hub import HfApi
            logger.debug("Successfully imported huggingface_hub")

            # Rate limiting
            self._rate_limit()

            # Get HF token for authentication
            hf_token = get_hf_token(interactive=False)

            # Initialize HF API
            api = HfApi(token=hf_token if hf_token else None)

            # Prepare search parameters
            search_params = {
                "search": search_query,
                "sort": sort,
                "direction": -1,  # Descending order
                "limit": limit * 2,  # Get more to filter out incompatible ones
                "cardData": True,  # Get model card data for descriptions
                "fetch_config": False  # Don't fetch full config to save time
            }

            # Set pipeline tag filter (focus on text generation models)
            if pipeline_tag:
                search_params["pipeline_tag"] = pipeline_tag
            else:
                # Default to text generation models for LocalLab
                search_params["pipeline_tag"] = "text-generation"

            # Add tag filters if specified
            if filter_tags:
                search_params["tags"] = filter_tags

            # Search models with timeout handling
            logger.debug(f"Searching HuggingFace Hub with query: {search_query}, limit: {limit}")

            try:
                models_iterator = api.list_models(**search_params)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"Network timeout or connection error: {e}")
                return [], False
            except Exception as e:
                logger.warning(f"HuggingFace API error: {e}")
                return [], False
            
            # Convert to our model format
            hf_models = []
            processed_count = 0
            
            for model_info in models_iterator:
                if processed_count >= limit:
                    break
                    
                try:
                    # Skip models that are clearly not suitable for LocalLab
                    if self._should_skip_model(model_info):
                        continue
                    
                    hf_model = self._convert_model_info(model_info)
                    if hf_model:
                        hf_models.append(hf_model)
                        processed_count += 1
                        
                except Exception as e:
                    logger.debug(f"Error processing model {getattr(model_info, 'id', 'unknown')}: {e}")
                    continue
            
            logger.debug(f"Successfully retrieved {len(hf_models)} models from HuggingFace Hub")
            return hf_models, True
            
        except ImportError as e:
            logger.warning(f"huggingface_hub package not available for model search: {e}")
            return [], False
        except Exception as e:
            logger.warning(f"Error searching HuggingFace Hub: {str(e)}")
            logger.debug(f"Full error details: {e}", exc_info=True)
            return [], False
    
    def _should_skip_model(self, model_info) -> bool:
        """Check if a model should be skipped based on various criteria"""
        try:
            # Skip if no model ID
            if not hasattr(model_info, 'id') or not model_info.id:
                return True
            
            # Skip models that are too large (>50GB) - likely not suitable for local use
            if hasattr(model_info, 'safetensors') and model_info.safetensors:
                total_size = model_info.safetensors.get('total', 0)
                if total_size > 50 * 1024 * 1024 * 1024:  # 50GB
                    return True
            
            # Skip models with problematic tags
            if hasattr(model_info, 'tags') and model_info.tags:
                skip_tags = {'dataset', 'space', 'not-for-all-audiences'}
                if any(tag in skip_tags for tag in model_info.tags):
                    return True
            
            # Skip private models if no token
            if hasattr(model_info, 'private') and model_info.private:
                hf_token = get_hf_token(interactive=False)
                if not hf_token:
                    return True
            
            return False
            
        except Exception:
            return True  # Skip on any error
    
    def _convert_model_info(self, model_info) -> Optional[HuggingFaceModel]:
        """Convert HuggingFace model info to our format"""
        try:
            # Extract basic info
            model_id = getattr(model_info, 'id', '')
            if not model_id:
                return None
            
            # Extract name (use last part of ID if no display name)
            name = model_id.split('/')[-1] if '/' in model_id else model_id
            
            # Extract description
            description = ""
            if hasattr(model_info, 'card_data') and model_info.card_data:
                description = model_info.card_data.get('description', '')
            if not description and hasattr(model_info, 'description'):
                description = getattr(model_info, 'description', '')
            if not description:
                description = f"HuggingFace model: {name}"
            
            # Extract metrics
            downloads = getattr(model_info, 'downloads', 0) or 0
            likes = getattr(model_info, 'likes', 0) or 0
            
            # Extract tags
            tags = getattr(model_info, 'tags', []) or []
            
            # Extract size information
            size_bytes = None
            size_formatted = "Unknown"
            
            if hasattr(model_info, 'safetensors') and model_info.safetensors:
                size_bytes = model_info.safetensors.get('total', 0)
                if size_bytes:
                    size_formatted = format_model_size(size_bytes)
            
            # Extract additional metadata
            author = model_id.split('/')[0] if '/' in model_id else "Unknown"
            pipeline_tag = getattr(model_info, 'pipeline_tag', None)
            library_name = getattr(model_info, 'library_name', None)
            is_private = getattr(model_info, 'private', False)
            
            # Extract dates
            created_at = None
            updated_at = None
            if hasattr(model_info, 'created_at'):
                created_at = str(model_info.created_at) if model_info.created_at else None
            if hasattr(model_info, 'last_modified'):
                updated_at = str(model_info.last_modified) if model_info.last_modified else None
            
            return HuggingFaceModel(
                id=model_id,
                name=name,
                description=description[:200] + "..." if len(description) > 200 else description,
                downloads=downloads,
                likes=likes,
                tags=tags,
                size_bytes=size_bytes,
                size_formatted=size_formatted,
                author=author,
                created_at=created_at,
                updated_at=updated_at,
                pipeline_tag=pipeline_tag,
                library_name=library_name,
                is_private=is_private
            )
            
        except Exception as e:
            logger.debug(f"Error converting model info: {e}")
            return None
    
    def get_popular_models(self, limit: int = 10) -> Tuple[List[HuggingFaceModel], bool]:
        """Get popular text generation models"""
        return self.search_models(
            search_query=None,
            limit=limit,
            sort="downloads",
            pipeline_tag="text-generation"
        )
    
    def search_by_keyword(self, keyword: str, limit: int = 20) -> Tuple[List[HuggingFaceModel], bool]:
        """Search models by keyword"""
        return self.search_models(
            search_query=keyword,
            limit=limit,
            sort="downloads",
            pipeline_tag="text-generation"
        )
    
    def search_by_tags(self, tags: List[str], limit: int = 20) -> Tuple[List[HuggingFaceModel], bool]:
        """Search models by tags"""
        return self.search_models(
            search_query=None,
            limit=limit,
            sort="downloads",
            filter_tags=tags,
            pipeline_tag="text-generation"
        )

# Global instance
hf_searcher = HuggingFaceSearcher()
