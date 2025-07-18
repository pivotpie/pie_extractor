"""
Shared types and classes for the OpenRouter Manager package.

This module contains shared types and classes to avoid circular imports.
"""
from dataclasses import dataclass

@dataclass
class APIKey:
    """Represents an API key and its usage information."""
    key_id: str
    api_key: str
    daily_limit: int = 50
    is_active: bool = True
