"""OpenRouter client integration for FastAPI application.

This module provides a singleton instance of the OpenRouter client
that can be used throughout the application.
"""
import os
from typing import Optional

# Add the project root to the Python path if not already added
import sys
from pathlib import Path

# Get the project root (two levels up from this file)
project_root = Path(__file__).parent.parent.parent.parent  # Go up to the project root
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now import from the root openrouter_manager
try:
    from openrouter_manager.client import OpenRouterClient
    from openrouter_manager.key_manager import KeyManager
    from openrouter_manager.instance_manager import InstanceManager
except ImportError as e:
    import logging
    logging.error(f"Failed to import openrouter_manager: {e}")
    logging.error(f"Current sys.path: {sys.path}")
    raise
from .config import settings

# Initialize the API key manager
key_manager = KeyManager("api_keys.db")

# Initialize the instance manager
instance_manager = InstanceManager(key_manager)

# Initialize the OpenRouter client
openrouter_client: Optional[OpenRouterClient] = None

def get_openrouter_client() -> OpenRouterClient:
    """Get or create the OpenRouter client instance with API key from settings.
    
    Returns:
        OpenRouterClient: Initialized OpenRouter client
        
    Raises:
        ValueError: If OPENROUTER_API_KEY is not configured
    """
    global openrouter_client
    
    if openrouter_client is None:
        api_key = settings.OPENROUTER_API_KEY
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured in settings")
            
        # Add the API key to the manager if it's not already there
        if not key_manager.has_key(api_key):
            key_manager.add_key(api_key, "default")
            
        openrouter_client = OpenRouterClient(
            api_key=api_key,
            base_url=settings.OPENROUTER_BASE_URL
        )
        
    return openrouter_client

async def get_async_openrouter_client() -> OpenRouterClient:
    """Async wrapper for getting the OpenRouter client.
    
    This allows the client to be used in FastAPI dependency injection.
    """
    return get_openrouter_client()
