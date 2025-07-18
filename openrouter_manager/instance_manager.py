"""Instance management for OpenRouter API.

This module provides functionality to manage API key instances
and handle instance-to-key mapping with TTL support.
"""
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Union
import logging

# Import shared types
from openrouter_manager.types import APIKey

# Import key_manager with a lazy import to avoid circular imports
APIKeyManager = None
def get_key_manager():
    global APIKeyManager
    if APIKeyManager is None:
        from openrouter_manager.key_manager import KeyManager as KM
        APIKeyManager = KM
    return APIKeyManager

class InstanceManager:
    """Manages API key instances and their usage tracking.
    
    This class handles tracking of API key usage by different instances,
    with support for TTL (time-to-live) for instance entries.
    """
    
    def __init__(self, key_manager=None, db_path: str = "instances.db"):
        if key_manager is None:
            key_manager = get_key_manager()()  # Instantiate the KeyManager
        """Initialize the InstanceManager.
        
        Args:
            key_manager: An instance of APIKeyManager
            db_path: Path to the SQLite database file
        """
        self.key_manager = key_manager
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create instances table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS instances (
                    instance_id TEXT PRIMARY KEY,
                    key_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (key_id) REFERENCES api_keys(key_id)
                )
            """)
            
            # Create instance_usage table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS instance_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    endpoint TEXT NOT NULL,
                    response_status INTEGER NOT NULL,
                    tokens_used INTEGER DEFAULT 0,
                    FOREIGN KEY (instance_id) REFERENCES instances(instance_id)
                )
            """)
            
            conn.commit()
    
    def assign_key_to_instance(self, instance_id: str, key_id: Optional[str] = None) -> str:
        """Assign an API key to an instance.
        
        Args:
            instance_id: Unique identifier for the instance
            key_id: Optional specific key ID to assign. If None, selects the best available key.
            
        Returns:
            The assigned API key
            
        Raises:
            ValueError: If no API keys are available
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if instance already has a key assigned
            cursor.execute(
                "SELECT key_id FROM instances WHERE instance_id = ?", 
                (instance_id,)
            )
            result = cursor.fetchone()
            
            if result:
                key_id = result[0]
            else:
                # Get the best available key if not specified
                if key_id is None:
                    key_id = self.key_manager.get_best_available_key()
                
                # Assign the key to the instance
                cursor.execute("""
                    INSERT INTO instances (instance_id, key_id, created_at, last_active)
                    VALUES (?, ?, datetime('now'), datetime('now'))
                    ON CONFLICT(instance_id) DO UPDATE SET 
                        key_id = excluded.key_id,
                        last_active = datetime('now')
                """, (instance_id, key_id))
                conn.commit()
            
            # Get the actual API key
            api_key = self.key_manager.get_key(key_id)
            if not api_key:
                raise ValueError(f"No API key found for key_id: {key_id}")
                
            return api_key
    
    def record_usage(
        self, 
        instance_id: str, 
        endpoint: str, 
        response_status: int,
        tokens_used: int = 0
    ) -> None:
        """Record API usage for an instance.
        
        Args:
            instance_id: The instance ID
            endpoint: The API endpoint that was called
            response_status: HTTP status code of the response
            tokens_used: Number of tokens used in the request
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Update last active time
            cursor.execute(
                "UPDATE instances SET last_active = datetime('now') WHERE instance_id = ?",
                (instance_id,)
            )
            
            # Record usage
            cursor.execute("""
                INSERT INTO instance_usage 
                (instance_id, timestamp, endpoint, response_status, tokens_used)
                VALUES (?, datetime('now'), ?, ?, ?)
            """, (instance_id, endpoint, response_status, tokens_used))
            
            conn.commit()
    
    def cleanup_old_instances(self, max_age_days: int = 30) -> int:
        """Remove old instance entries that haven't been active.
        
        Args:
            max_age_days: Maximum age in days before an inactive instance is removed
            
        Returns:
            Number of instances removed
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete old instances
            cursor.execute("""
                DELETE FROM instances 
                WHERE last_active < datetime('now', ? || ' days')
            """, (f"-{max_age_days}",))
            
            count = cursor.rowcount
            conn.commit()
            
            # Vacuum to reclaim space
            if count > 0:
                cursor.execute("VACUUM")
                
            return count
    
    def get_instance_stats(self, instance_id: str) -> Dict[str, Union[int, str, None]]:
        """Get usage statistics for an instance.
        
        Args:
            instance_id: The instance ID to get stats for
            
        Returns:
            Dictionary containing usage statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get instance info
            cursor.execute(
                "SELECT * FROM instances WHERE instance_id = ?", 
                (instance_id,)
            )
            instance = cursor.fetchone()
            
            if not instance:
                return {
                    "instance_id": instance_id,
                    "status": "not_found",
                    "created_at": None,
                    "last_active": None,
                    "total_requests": 0,
                    "successful_requests": 0,
                    "total_tokens": 0
                }
            
            # Get usage stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN response_status < 400 THEN 1 ELSE 0 END) as successful_requests,
                    COALESCE(SUM(tokens_used), 0) as total_tokens
                FROM instance_usage
                WHERE instance_id = ?
            """, (instance_id,))
            
            stats = cursor.fetchone()
            
            return {
                "instance_id": instance_id,
                "key_id": instance["key_id"],
                "status": "active",
                "created_at": instance["created_at"],
                "last_active": instance["last_active"],
                "total_requests": stats["total_requests"] or 0,
                "successful_requests": stats["successful_requests"] or 0,
                "total_tokens": stats["total_tokens"] or 0
            }
