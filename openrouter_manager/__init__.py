"""
OpenRouter Manager Package

This package provides modules for managing OpenRouter API interactions,
including client management, model selection, and API key management.
"""

__all__ = ['OpenRouterClient', 'APIKeyManager', 'ModelManager', 'InstanceManager']

# Lazy imports to prevent circular imports
_imports = {}

def __getattr__(name):
    if name in _imports:
        return _imports[name]
    
    if name == 'OpenRouterClient':
        from .client import OpenRouterClient
        _imports[name] = OpenRouterClient
        return OpenRouterClient
    elif name == 'APIKeyManager':
        from .key_manager import APIKeyManager
        _imports[name] = APIKeyManager
        return APIKeyManager
    elif name == 'ModelManager':
        from .model_manager import ModelManager
        _imports[name] = ModelManager
        return ModelManager
    elif name == 'InstanceManager':
        from .instance_manager import InstanceManager
        _imports[name] = InstanceManager
        return InstanceManager
    
    raise AttributeError(f"module 'openrouter_manager' has no attribute '{name}'")

def __dir__():
    return sorted(__all__)
