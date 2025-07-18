"""Model management for OpenRouter API.

This module provides functionality to discover, select, and manage AI models
with automatic fallback to alternative models when needed.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, TypedDict

import requests

# Configure logging
logger = logging.getLogger(__name__)


class ModelInfo(TypedDict):
    """Type definition for model information dictionary."""
    id: str
    name: str
    description: str
    pricing: Dict[str, float]
    context_length: int
    architecture: Dict[str, str]
    top_provider: Dict[str, str]
    per_request_limits: Optional[Dict[str, int]]


@dataclass
class ModelManager:
    """Manages model discovery and selection with fallback support.
    
    This class handles:
    - Fetching available models from OpenRouter API
    - Caching model information
    - Selecting appropriate models based on category
    - Falling back to alternative models when needed
    """
    
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    _models_cache: Dict[str, ModelInfo] = field(default_factory=dict)
    _last_fetch_time: float = 0.0
    CACHE_TTL: float = 3600.0  # 1 hour in seconds
    
    # Preferred models by category (using free models where possible)
    PREFERRED_MODELS = {
        "vision": [
            "meta-llama/llama-3.2-11b-vision-instruct:free",  # Primary vision model
            "nousresearch/nous-hermes-2-vision-01:free",      # Fallback vision model
            "google/gemini-pro-vision:free"                   # Additional fallback
        ],
        "reasoning": [
            "deepseek/deepseek-r1-0528:free",                 # Primary reasoning model
            "mistralai/mistral-7b-instruct:free",             # Fallback reasoning model
            "google/gemini-pro:free"                          # Additional fallback
        ]
    }
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def fetch_models(self, force_refresh: bool = False) -> Dict[str, ModelInfo]:
        """Fetch available models from OpenRouter API.
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            Dictionary mapping model IDs to model information
        """
        import time
        
        current_time = time.time()
        
        # Return cached data if it's still fresh
        if not force_refresh and self._models_cache and \
           (current_time - self._last_fetch_time) < self.CACHE_TTL:
            return self._models_cache
            
        try:
            logger.info("Fetching available models from OpenRouter")
            response = requests.get(
                f"{self.base_url}/models",
                headers=self.get_headers(),
                timeout=10
            )
            response.raise_for_status()
            
            # Process and cache the response
            self._models_cache = {
                model["id"]: model 
                for model in response.json().get("data", [])
            }
            self._last_fetch_time = current_time
            logger.info("Fetched %d models from OpenRouter", len(self._models_cache))
            
        except Exception as e:
            logger.error("Failed to fetch models: %s", str(e))
            if not self._models_cache:
                raise RuntimeError("No cached models available and failed to fetch new ones") from e
                
        return self._models_cache
    
    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model."""
        if model_id in self._models_cache:
            return self._models_cache[model_id]
        
        # Try to fetch fresh data if model not in cache
        try:
            self.fetch_models(force_refresh=True)
            return self._models_cache.get(model_id)
        except Exception:
            return None
    
    def is_model_available(self, model_id: str) -> bool:
        """Check if a model is available."""
        return model_id in self._models_cache
    
    def get_free_models(self) -> List[ModelInfo]:
        """Get all free models."""
        return [
            model for model in self._models_cache.values()
            if model.get("pricing", {}).get("prompt") == 0
        ]
    
    def get_models_by_category(self, category: str) -> List[ModelInfo]:
        """Get models that match the specified category.
        
        Args:
            category: The category of models to retrieve ('vision' or 'reasoning')
            
        Returns:
            List of ModelInfo objects matching the category
        """
        category = category.lower()
        results = []
        
        # Define keywords that indicate a model belongs to a category
        category_keywords = {
            'vision': ['vision', 'llava', 'clip', 'multimodal', 'image'],
            'reasoning': ['chat', 'instruct', 'text', 'reasoning', 'llm']
        }
        
        # Get keywords for this category, or empty list if unknown category
        keywords = category_keywords.get(category, [category])
        
        for model_id, model_info in self._models_cache.items():
            # Handle pricing - ensure we're comparing numbers, not strings
            pricing = model_info.get("pricing", {})
            prompt_price = pricing.get("prompt")
            
            # Skip non-free models (handle both string and numeric pricing)
            if prompt_price is not None:
                try:
                    # Convert to float to handle both string and numeric values
                    price = float(prompt_price)
                    if price > 0:
                        continue
                except (TypeError, ValueError):
                    # If conversion fails, assume it's a free model
                    pass
                
            # Check model name and description for category keywords
            model_text = (model_info.get("name", "") + " " + 
                         model_info.get("description", "")).lower()
            
            if any(keyword in model_text for keyword in keywords):
                results.append(model_info)
        
        # Sort by context length (longer is generally better)
        results.sort(key=lambda x: x.get("context_length", 0), reverse=True)
        return results
    
    def get_fallback_models(self, preferred_models: List[str]) -> List[str]:
        """Get fallback models for a list of preferred models.
        
        Args:
            preferred_models: List of model IDs in order of preference
            
        Returns:
            List of model IDs with fallbacks included
        """
        if not preferred_models:
            return []
            
        # Start with preferred models
        result = preferred_models.copy()
        
        # Get all free models that aren't already in the preferred list
        free_models = [
            model["id"] for model in self.get_free_models()
            if model["id"] not in preferred_models
        ]
        
        # Add free models to the result
        result.extend(free_models)
        
        return result
    
    def get_best_model(self, category: str) -> Optional[str]:
        """Get the best available model for a category with fallback support.
        
        This method tries to find the best available model in this order:
        1. Any of the preferred models for the category (in order of preference)
        2. Any model that matches the category keywords (sorted by context length)
        3. Any free model (as a last resort)
        
        Args:
            category: Model category (e.g., 'vision', 'reasoning')
            
        Returns:
            Model ID of the best available model, or None if none found
        """
        logger.info(f"Finding best model for category: {category}")
        
        # Refresh model list if needed
        self.fetch_models()
        
        # Get preferred models for this category
        preferred_models = self.PREFERRED_MODELS.get(category.lower(), [])
        logger.debug(f"Preferred models for {category}: {preferred_models}")
        
        # Try each preferred model in order
        for model_id in preferred_models:
            if self.is_model_available(model_id):
                logger.info(f"Using preferred model: {model_id}")
                return model_id
            logger.debug(f"Preferred model not available: {model_id}")
        
        # If no preferred models are available, try to find any free model in the category
        logger.debug("No preferred models available, searching for category matches")
        category_models = self.get_models_by_category(category)
        
        if category_models:
            logger.info(f"Found {len(category_models)} models in category '{category}'. "
                       f"Selecting: {category_models[0]['id']}")
            return category_models[0]["id"]
        
        # Last resort: try any free model
        logger.debug("No category matches found, trying any free model")
        all_free = self.get_free_models()
        if all_free:
            logger.info(f"Using fallback free model: {all_free[0]['id']}")
            return all_free[0]["id"]
        
        logger.warning(f"No available models found for category: {category}")
        return None
    
    def get_model_fallback_chain(self, category: str) -> List[str]:
        """Get a list of models to try in order for a given category.
        
        Args:
            category: Model category (e.g., 'vision', 'reasoning')
            
        Returns:
            List of model IDs to try in order
        """
        # Refresh model list if needed
        self.fetch_models()
        
        # Get preferred models for this category
        preferred_models = self.PREFERRED_MODELS.get(category.lower(), [])
        
        # Filter to only available models
        available_preferred = [m for m in preferred_models if self.is_model_available(m)]
        
        # Get all free models in this category that aren't preferred
        category_models = [
            m["id"] for m in self.get_models_by_category(category)
            if m["id"] not in preferred_models and m.get("pricing", {}).get("prompt") == 0
        ]
        
        # Combine preferred and fallback models
        return available_preferred + category_models
