"""
Pie Extractor - Enhanced document text extraction using AI vision models.
"""

__version__ = "3.0.0"

# Core components (your existing)
from .main import PieExtractor, create_extractor, quick_extract
from .config import load_configuration, PieExtractorConfig
from .auth import AuthManager
from .api_client import OpenRouterClient
from .exceptions import PieExtractorError

# Enhanced components (new)
from .enhanced_extractor import DocumentExtractor, DocumentExtractionConfig
from .rate_manager import APIKeyManager, RateLimitConfig
from .model_manager import ModelManager, ModelRegistry, ModelCategory
from .hybrid_search import HybridSemanticSearch, SearchConfig

# Convenience imports
__all__ = [
    # Original components
    "PieExtractor",
    "create_extractor", 
    "quick_extract",
    "load_configuration",
    "PieExtractorConfig",
    "AuthManager",
    "OpenRouterClient",
    "PieExtractorError",
    
    # Enhanced components
    "DocumentExtractor",
    "DocumentExtractionConfig",
    "APIKeyManager",
    "RateLimitConfig",
    "ModelManager",
    "ModelRegistry",
    "ModelCategory",
    "HybridSemanticSearch",
    "SearchConfig"
]