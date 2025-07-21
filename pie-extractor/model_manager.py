"""
Model Management System for OpenRouter.
Handles model discovery, fallback strategies, and performance monitoring.
"""

import json
import time
import logging
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum
import threading
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class ModelCategory(Enum):
    """Model categories for classification."""
    VISION = "vision"
    REASONING = "reasoning"
    TEXT = "text"
    CHAT = "chat"
    CODE = "code"
    EMBEDDING = "embedding"
    OTHER = "other"


class ModelStatus(Enum):
    """Model status for circuit breaker pattern."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class ModelMetadata:
    """Metadata for a model."""
    model_id: str
    name: str
    category: ModelCategory
    provider: str
    context_length: int
    pricing: Dict[str, float]  # input_cost, output_cost per token
    capabilities: List[str]
    is_free: bool
    supports_vision: bool
    supports_function_calling: bool
    max_images: int = 0
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ModelPerformance:
    """Performance metrics for a model."""
    model_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    circuit_breaker_state: ModelStatus = ModelStatus.UNKNOWN
    failure_streak: int = 0
    last_reset: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FallbackConfig:
    """Configuration for fallback strategies."""
    strategy: str = "performance"  # performance, cost, reliability
    max_retries: int = 3
    circuit_breaker_threshold: int = 5  # failures before marking as failed
    circuit_breaker_timeout: int = 300  # seconds before retry
    prefer_free_models: bool = True
    exclude_models: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)


class ModelRegistry:
    """Registry for managing model metadata and discovery."""
    
    def __init__(self, db_path: str = "models.db", api_base_url: str = "https://openrouter.ai/api/v1"):
        self.db_path = Path(db_path)
        self.api_base_url = api_base_url
        self.models: Dict[str, ModelMetadata] = {}
        self.performance: Dict[str, ModelPerformance] = {}
        self.cache_ttl = 3600  # 1 hour cache
        self.last_discovery = 0
        self._lock = threading.Lock()
        
        # Predefined model categories and capabilities
        self.category_keywords = {
            ModelCategory.VISION: ["vision", "multimodal", "image", "visual"],
            ModelCategory.REASONING: ["reasoning", "r1", "think", "cot", "chain-of-thought"],
            ModelCategory.TEXT: ["text", "language", "llm"],
            ModelCategory.CHAT: ["chat", "instruct", "assistant"],
            ModelCategory.CODE: ["code", "coding", "programming", "developer"],
            ModelCategory.EMBEDDING: ["embedding", "embed", "vector"]
        }
        
        self._init_database()
        self._load_models_from_db()
    
    def _init_database(self):
        """Initialize SQLite database for model storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    model_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    provider TEXT,
                    context_length INTEGER,
                    pricing TEXT,
                    capabilities TEXT,
                    is_free BOOLEAN,
                    supports_vision BOOLEAN,
                    supports_function_calling BOOLEAN,
                    max_images INTEGER DEFAULT 0,
                    description TEXT,
                    created_at TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_performance (
                    model_id TEXT PRIMARY KEY,
                    total_requests INTEGER DEFAULT 0,
                    successful_requests INTEGER DEFAULT 0,
                    failed_requests INTEGER DEFAULT 0,
                    avg_response_time REAL DEFAULT 0.0,
                    last_success TEXT,
                    last_failure TEXT,
                    circuit_breaker_state TEXT DEFAULT 'unknown',
                    failure_streak INTEGER DEFAULT 0,
                    last_reset TEXT,
                    FOREIGN KEY (model_id) REFERENCES models (model_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discovery_cache (
                    id INTEGER PRIMARY KEY,
                    models_data TEXT NOT NULL,
                    discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    expires_at TEXT
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON models(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_is_free ON models(is_free)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_supports_vision ON models(supports_vision)")
            
            conn.commit()
    
    def _load_models_from_db(self):
        """Load models and performance data from database."""
        with sqlite3.connect(self.db_path) as conn:
            # Load models
            cursor = conn.execute("SELECT * FROM models")
            for row in cursor.fetchall():
                model = ModelMetadata(
                    model_id=row[0],
                    name=row[1],
                    category=ModelCategory(row[2]),
                    provider=row[3],
                    context_length=row[4],
                    pricing=json.loads(row[5]) if row[5] else {},
                    capabilities=json.loads(row[6]) if row[6] else [],
                    is_free=bool(row[7]),
                    supports_vision=bool(row[8]),
                    supports_function_calling=bool(row[9]),
                    max_images=row[10],
                    description=row[11] or "",
                    created_at=row[12]
                )
                self.models[model.model_id] = model
            
            # Load performance data
            cursor = conn.execute("SELECT * FROM model_performance")
            for row in cursor.fetchall():
                perf = ModelPerformance(
                    model_id=row[0],
                    total_requests=row[1],
                    successful_requests=row[2],
                    failed_requests=row[3],
                    avg_response_time=row[4],
                    last_success=row[5],
                    last_failure=row[6],
                    circuit_breaker_state=ModelStatus(row[7]),
                    failure_streak=row[8],
                    last_reset=row[9]
                )
                self.performance[perf.model_id] = perf
        
        logger.info(f"Loaded {len(self.models)} models from database")
    
    def discover_models(self, force_refresh: bool = False) -> bool:
        """Discover models from OpenRouter API."""
        current_time = time.time()
        
        # Check if cache is still valid
        if not force_refresh and (current_time - self.last_discovery) < self.cache_ttl:
            return False
        
        try:
            logger.info("Discovering models from OpenRouter API...")
            
            # Make API request
            response = requests.get(f"{self.api_base_url}/models", timeout=30)
            response.raise_for_status()
            
            models_data = response.json()
            
            if "data" not in models_data:
                logger.warning("Unexpected API response format")
                return False
            
            # Process discovered models
            new_models = 0
            updated_models = 0
            
            for model_data in models_data["data"]:
                model_id = model_data.get("id", "")
                if not model_id:
                    continue
                
                # Extract model information
                model_info = self._parse_model_data(model_data)
                
                if model_id not in self.models:
                    self.models[model_id] = model_info
                    new_models += 1
                else:
                    # Update existing model
                    self.models[model_id] = model_info
                    updated_models += 1
                
                # Initialize performance tracking if needed
                if model_id not in self.performance:
                    self.performance[model_id] = ModelPerformance(model_id=model_id)
            
            # Save to database
            self._save_models_to_db()
            
            self.last_discovery = current_time
            
            logger.info(f"Model discovery completed: {new_models} new, {updated_models} updated")
            return True
            
        except Exception as e:
            logger.error(f"Model discovery failed: {e}")
            return False
    
    def _parse_model_data(self, model_data: Dict[str, Any]) -> ModelMetadata:
        """Parse model data from API response."""
        model_id = model_data.get("id", "")
        name = model_data.get("name", model_id)
        
        # Determine category based on model name/description
        category = self._classify_model(name, model_data.get("description", ""))
        
        # Extract pricing information
        pricing = {}
        if "pricing" in model_data:
            pricing_data = model_data["pricing"]
            pricing = {
                "input_cost": float(pricing_data.get("prompt", 0)),
                "output_cost": float(pricing_data.get("completion", 0))
            }
        
        # Determine if model is free
        is_free = pricing.get("input_cost", 0) == 0 and pricing.get("output_cost", 0) == 0
        
        # Extract capabilities
        capabilities = []
        supports_vision = False
        supports_function_calling = False
        max_images = 0
        
        if "top_provider" in model_data:
            provider_data = model_data["top_provider"]
            if "modalities" in provider_data:
                modalities = provider_data["modalities"]
                if "image" in modalities:
                    supports_vision = True
                    capabilities.append("vision")
                    max_images = modalities.get("image", {}).get("max_images", 1)
                
                if "text" in modalities:
                    capabilities.append("text")
            
            if provider_data.get("supports_tools", False):
                supports_function_calling = True
                capabilities.append("function_calling")
        
        return ModelMetadata(
            model_id=model_id,
            name=name,
            category=category,
            provider=model_data.get("owned_by", "unknown"),
            context_length=model_data.get("context_length", 0),
            pricing=pricing,
            capabilities=capabilities,
            is_free=is_free,
            supports_vision=supports_vision,
            supports_function_calling=supports_function_calling,
            max_images=max_images,
            description=model_data.get("description", "")
        )
    
    def _classify_model(self, name: str, description: str) -> ModelCategory:
        """Classify model based on name and description."""
        text = f"{name} {description}".lower()
        
        # Check for specific keywords
        for category, keywords in self.category_keywords.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        # Default to text category
        return ModelCategory.TEXT
    
    def _save_models_to_db(self):
        """Save models and performance data to database."""
        with sqlite3.connect(self.db_path) as conn:
            # Save models
            for model in self.models.values():
                conn.execute("""
                    INSERT OR REPLACE INTO models 
                    (model_id, name, category, provider, context_length, pricing, 
                     capabilities, is_free, supports_vision, supports_function_calling, 
                     max_images, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    model.model_id, model.name, model.category.value, model.provider,
                    model.context_length, json.dumps(model.pricing),
                    json.dumps(model.capabilities), model.is_free,
                    model.supports_vision, model.supports_function_calling,
                    model.max_images, model.description, model.created_at
                ))
            
            # Save performance data
            for perf in self.performance.values():
                conn.execute("""
                    INSERT OR REPLACE INTO model_performance
                    (model_id, total_requests, successful_requests, failed_requests,
                     avg_response_time, last_success, last_failure, circuit_breaker_state,
                     failure_streak, last_reset)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    perf.model_id, perf.total_requests, perf.successful_requests,
                    perf.failed_requests, perf.avg_response_time, perf.last_success,
                    perf.last_failure, perf.circuit_breaker_state.value,
                    perf.failure_streak, perf.last_reset
                ))
            
            conn.commit()
    
    def get_models_by_category(self, category: ModelCategory, free_only: bool = False) -> List[ModelMetadata]:
        """Get models filtered by category."""
        models = [m for m in self.models.values() if m.category == category]
        
        if free_only:
            models = [m for m in models if m.is_free]
        
        return sorted(models, key=lambda x: x.name)
    
    def get_models_by_capability(self, capability: str, free_only: bool = False) -> List[ModelMetadata]:
        """Get models filtered by capability."""
        models = [m for m in self.models.values() if capability in m.capabilities]
        
        if free_only:
            models = [m for m in models if m.is_free]
        
        return sorted(models, key=lambda x: x.name)
    
    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Get a specific model by ID."""
        return self.models.get(model_id)
    
    def get_performance(self, model_id: str) -> Optional[ModelPerformance]:
        """Get performance data for a model."""
        return self.performance.get(model_id)


class CircuitBreaker:
    """Circuit breaker pattern for model failure handling."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = ModelStatus.HEALTHY
    
    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == ModelStatus.HEALTHY:
            return True
        
        if self.state == ModelStatus.FAILED:
            # Check if timeout has passed
            if time.time() - self.last_failure_time > self.timeout:
                self.state = ModelStatus.DEGRADED
                return True
            return False
        
        # DEGRADED state - allow limited attempts
        return True
    
    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = ModelStatus.HEALTHY
    
    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = ModelStatus.FAILED
        else:
            self.state = ModelStatus.DEGRADED


class ModelManager:
    """
    Main model management system with intelligent fallback and monitoring.
    
    Features:
    - Model discovery and caching
    - Performance monitoring
    - Circuit breaker pattern
    - Intelligent fallback strategies
    - Configuration-driven selection
    """
    
    def __init__(self, registry: ModelRegistry, fallback_config: FallbackConfig = None):
        self.registry = registry
        self.fallback_config = fallback_config or FallbackConfig()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.recent_response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
        self._lock = threading.Lock()
        
        logger.info("ModelManager initialized")
    
    def select_model(self, 
                     category: ModelCategory, 
                     requirements: Dict[str, Any] = None) -> Optional[str]:
        """
        Select the best model for given category and requirements.
        
        Args:
            category: Model category to select from
            requirements: Additional requirements (vision, function_calling, etc.)
            
        Returns:
            Model ID of selected model or None if no suitable model found
        """
        requirements = requirements or {}
        
        # Get candidate models
        candidates = self.registry.get_models_by_category(
            category, 
            free_only=self.fallback_config.prefer_free_models
        )
        
        # Filter by requirements
        candidates = self._filter_by_requirements(candidates, requirements)
        
        # Remove excluded models
        candidates = [m for m in candidates if m.model_id not in self.fallback_config.exclude_models]
        
        if not candidates:
            logger.warning(f"No suitable models found for category {category}")
            return None
        
        # Apply selection strategy
        selected = self._apply_selection_strategy(candidates)
        
        if selected:
            logger.info(f"Selected model: {selected.model_id} ({selected.name})")
            return selected.model_id
        
        return None
    
    def _filter_by_requirements(self, 
                                candidates: List[ModelMetadata], 
                                requirements: Dict[str, Any]) -> List[ModelMetadata]:
        """Filter models by requirements."""
        filtered = []
        
        for model in candidates:
            # Check vision requirement
            if requirements.get("vision", False) and not model.supports_vision:
                continue
            
            # Check function calling requirement
            if requirements.get("function_calling", False) and not model.supports_function_calling:
                continue
            
            # Check context length requirement
            min_context = requirements.get("min_context_length", 0)
            if model.context_length < min_context:
                continue
            
            # Check required capabilities
            required_caps = requirements.get("capabilities", [])
            if not all(cap in model.capabilities for cap in required_caps):
                continue
            
            # Check circuit breaker status
            if not self._is_model_available(model.model_id):
                continue
            
            filtered.append(model)
        
        return filtered
    
    def _apply_selection_strategy(self, candidates: List[ModelMetadata]) -> Optional[ModelMetadata]:
        """Apply selection strategy to choose best model."""
        if not candidates:
            return None
        
        strategy = self.fallback_config.strategy
        
        if strategy == "performance":
            return self._select_by_performance(candidates)
        elif strategy == "cost":
            return self._select_by_cost(candidates)
        elif strategy == "reliability":
            return self._select_by_reliability(candidates)
        else:
            # Default: return first available
            return candidates[0]
    
    def _select_by_performance(self, candidates: List[ModelMetadata]) -> Optional[ModelMetadata]:
        """Select model based on performance metrics."""
        best_model = None
        best_score = -1
        
        for model in candidates:
            perf = self.registry.get_performance(model.model_id)
            if not perf:
                continue
            
            # Calculate performance score
            success_rate = (perf.successful_requests / max(perf.total_requests, 1))
            response_time_score = max(0, 1 - (perf.avg_response_time / 60))  # Normalize to 60s
            
            score = (success_rate * 0.7) + (response_time_score * 0.3)
            
            if score > best_score:
                best_score = score
                best_model = model
        
        return best_model or candidates[0]
    
    def _select_by_cost(self, candidates: List[ModelMetadata]) -> Optional[ModelMetadata]:
        """Select model based on cost (prefer free/cheaper models)."""
        # Sort by cost (free first, then by total cost)
        def cost_key(model):
            if model.is_free:
                return (0, 0)
            total_cost = model.pricing.get("input_cost", 0) + model.pricing.get("output_cost", 0)
            return (1, total_cost)
        
        return sorted(candidates, key=cost_key)[0]
    
    def _select_by_reliability(self, candidates: List[ModelMetadata]) -> Optional[ModelMetadata]:
        """Select model based on reliability (success rate)."""
        best_model = None
        best_reliability = -1
        
        for model in candidates:
            perf = self.registry.get_performance(model.model_id)
            if not perf or perf.total_requests == 0:
                continue
            
            reliability = perf.successful_requests / perf.total_requests
            
            if reliability > best_reliability:
                best_reliability = reliability
                best_model = model
        
        # If no performance data, return first model
        return best_model or candidates[0]
    
    def _is_model_available(self, model_id: str) -> bool:
        """Check if model is available (not in failed circuit breaker state)."""
        breaker = self.circuit_breakers.get(model_id)
        if not breaker:
            return True
        
        return breaker.can_execute()
    
    def record_model_usage(self, 
                          model_id: str, 
                          success: bool, 
                          response_time: float = 0.0,
                          error: Optional[str] = None):
        """Record model usage for performance tracking."""
        with self._lock:
            # Update performance metrics
            perf = self.registry.performance.get(model_id)
            if not perf:
                perf = ModelPerformance(model_id=model_id)
                self.registry.performance[model_id] = perf
            
            perf.total_requests += 1
            
            if success:
                perf.successful_requests += 1
                perf.last_success = datetime.now().isoformat()
                perf.failure_streak = 0
                
                # Update circuit breaker
                breaker = self.circuit_breakers.get(model_id)
                if breaker:
                    breaker.record_success()
            else:
                perf.failed_requests += 1
                perf.last_failure = datetime.now().isoformat()
                perf.failure_streak += 1
                
                # Update circuit breaker
                if model_id not in self.circuit_breakers:
                    self.circuit_breakers[model_id] = CircuitBreaker(
                        self.fallback_config.circuit_breaker_threshold,
                        self.fallback_config.circuit_breaker_timeout
                    )
                
                self.circuit_breakers[model_id].record_failure()
                perf.circuit_breaker_state = self.circuit_breakers[model_id].state
            
            # Update response time
            if response_time > 0:
                recent_times = self.recent_response_times[model_id]
                recent_times.append(response_time)
                perf.avg_response_time = sum(recent_times) / len(recent_times)
        
        # Save to database periodically
        self.registry._save_models_to_db()
        
        logger.debug(f"Recorded usage for {model_id}: success={success}, time={response_time:.2f}s")
    
    def get_fallback_models(self, 
                           primary_model: str, 
                           category: ModelCategory, 
                           requirements: Dict[str, Any] = None) -> List[str]:
        """Get fallback models if primary model fails."""
        requirements = requirements or {}
        
        # Get all suitable models
        candidates = self.registry.get_models_by_category(category)
        candidates = self._filter_by_requirements(candidates, requirements)
        
        # Remove primary model and excluded models
        candidates = [m for m in candidates 
                     if m.model_id != primary_model 
                     and m.model_id not in self.fallback_config.exclude_models
                     and self._is_model_available(m.model_id)]
        
        # Sort by selection strategy
        sorted_candidates = []
        if self.fallback_config.strategy == "performance":
            sorted_candidates = sorted(candidates, 
                                     key=lambda m: self._get_performance_score(m), 
                                     reverse=True)
        elif self.fallback_config.strategy == "cost":
            sorted_candidates = sorted(candidates, 
                                     key=lambda m: (not m.is_free, m.pricing.get("input_cost", 0)))
        else:
            sorted_candidates = candidates
        
        return [m.model_id for m in sorted_candidates[:self.fallback_config.max_retries]]
    
    def _get_performance_score(self, model: ModelMetadata) -> float:
        """Get performance score for a model."""
        perf = self.registry.get_performance(model.model_id)
        if not perf or perf.total_requests == 0:
            return 0.5  # Neutral score for unknown models
        
        success_rate = perf.successful_requests / perf.total_requests
        return success_rate
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get comprehensive model statistics."""
        stats = {
            "total_models": len(self.registry.models),
            "models_by_category": {},
            "free_models": len([m for m in self.registry.models.values() if m.is_free]),
            "vision_models": len([m for m in self.registry.models.values() if m.supports_vision]),
            "failed_models": len([m for m in self.circuit_breakers.values() if m.state == ModelStatus.FAILED]),
            "last_discovery": self.registry.last_discovery
        }
        
        # Count by category
        for category in ModelCategory:
            count = len(self.registry.get_models_by_category(category))
            stats["models_by_category"][category.value] = count
        
        return stats


# Usage example and testing
if __name__ == "__main__":
    import sys
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        print("🤖 Model Management System Test")
        print("=" * 40)
        
        # Create model registry
        registry = ModelRegistry("test_models.db")
        
        # Create model manager
        fallback_config = FallbackConfig(
            strategy="performance",
            prefer_free_models=True,
            max_retries=3
        )
        manager = ModelManager(registry, fallback_config)
        
        # Try to discover models
        print("Discovering models from OpenRouter...")
        success = registry.discover_models()
        
        if success:
            print("✅ Model discovery successful")
        else:
            print("⚠️ Model discovery failed or cached")
        
        # Get model statistics
        stats = manager.get_model_stats()
        print(f"\n📊 Model Statistics:")
        print(f"Total models: {stats['total_models']}")
        print(f"Free models: {stats['free_models']}")
        print(f"Vision models: {stats['vision_models']}")
        
        print("\nModels by category:")
        for category, count in stats["models_by_category"].items():
            print(f"  {category}: {count}")
        
        # Test model selection
        print("\n🎯 Model Selection Tests:")
        
        # Select vision model
        vision_model = manager.select_model(
            ModelCategory.VISION,
            requirements={"vision": True}
        )
        if vision_model:
            print(f"Selected vision model: {vision_model}")
        else:
            print("No vision model available")
        
        # Select reasoning model
        reasoning_model = manager.select_model(
            ModelCategory.REASONING,
            requirements={}
        )
        if reasoning_model:
            print(f"Selected reasoning model: {reasoning_model}")
        else:
            print("No reasoning model available")
        
        # Test fallback models
        if vision_model:
            fallbacks = manager.get_fallback_models(
                vision_model, 
                ModelCategory.VISION,
                requirements={"vision": True}
            )
            print(f"Fallback models for {vision_model}: {fallbacks}")
        
        print("\n✅ Model management test completed successfully")
        
    except Exception as e:
        print(f"❌ Model management test failed: {e}")
        sys.exit(1)