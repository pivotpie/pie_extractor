"""
OpenRouter API Key Management System

Handles API key rotation, usage tracking, and rate limiting for OpenRouter API.
"""
import sqlite3
import os
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import uuid
import logging
from typing import Dict, List, Optional, Tuple
import sqlite3
import os
from datetime import datetime, date
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import shared types
from openrouter_manager.types import APIKey

class KeyManager:
    def has_key(self, api_key: str) -> bool:
        """Check if the API key exists in the database."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT 1 FROM api_keys WHERE api_key = ? LIMIT 1", (api_key,))
            return cur.fetchone() is not None

    def add_key(self, api_key: str, key_id: str = None) -> None:
        """Add an API key to the database if it does not exist."""
        if not key_id:
            key_id = str(uuid.uuid4())
        with self._get_connection() as conn:
            try:
                conn.execute("INSERT OR IGNORE INTO api_keys (key_id, api_key) VALUES (?, ?)", (key_id, api_key))
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to add API key: {e}")

    def has_key(self, api_key: str) -> bool:
        """Check if the API key exists in the database."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT 1 FROM api_keys WHERE api_key = ? LIMIT 1", (api_key,))
            return cur.fetchone() is not None

    """Manages API keys and their usage for OpenRouter API."""
    
    def __init__(self, db_path: str = "api_keys.db"):
        """Initialize the KeyManager with a SQLite database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self) -> None:
        """Initialize the database tables if they don't exist."""
        with self._get_connection() as conn:
            # API keys table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    api_key TEXT NOT NULL UNIQUE,
                    daily_limit INTEGER DEFAULT 50,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Key usage tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS key_usage (
                    key_id TEXT,
                    usage_date TEXT,
                    request_count INTEGER DEFAULT 0,
                    last_used TIMESTAMP,
                    PRIMARY KEY (key_id, usage_date),
                    FOREIGN KEY (key_id) REFERENCES api_keys(key_id) ON DELETE CASCADE
                )
            """)
            
            # Instance tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS instances (
                    instance_id TEXT PRIMARY KEY,
                    key_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP,
                    FOREIGN KEY (key_id) REFERENCES api_keys(key_id)
                )
            """)
            
            conn.commit()
    
    def add_api_key(self, api_key: str, daily_limit: int = 50) -> str:
        """Add a new API key to the manager.
        
        Args:
            api_key: The OpenRouter API key
            daily_limit: Daily request limit for this key
            
        Returns:
            The internal key ID
        """
        key_id = str(uuid.uuid4())
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO api_keys (key_id, api_key, daily_limit)
                VALUES (?, ?, ?)
                """,
                (key_id, api_key, daily_limit)
            )
            conn.commit()
        logger.info(f"Added new API key with ID: {key_id}")
        return key_id
    
    def get_instance_key(self, instance_id: str, threshold: int = 40) -> Optional[str]:
        """Get or assign an API key for an instance.
        
        Args:
            instance_id: Unique identifier for the instance
            threshold: Usage threshold at which to consider rotating keys
            
        Returns:
            API key string or None if no valid key available
        """
        today = date.today().isoformat()
        
        with self._get_connection() as conn:
            # Check if instance already has a key
            cursor = conn.execute(
                "SELECT key_id FROM instances WHERE instance_id = ?",
                (instance_id,)
            )
            row = cursor.fetchone()
            
            if row:
                # Instance exists, get current key
                key_id = row['key_id']
                # Check if current key is still valid
                cursor = conn.execute("""
                    SELECT k.api_key, COALESCE(u.request_count, 0) as request_count, k.daily_limit
                    FROM api_keys k
                    LEFT JOIN key_usage u ON k.key_id = u.key_id AND u.usage_date = ?
                    WHERE k.key_id = ? AND k.is_active = 1
                """, (today, key_id))
                key_info = cursor.fetchone()
                
                if key_info and key_info['request_count'] < key_info['daily_limit'] - threshold:
                    # Current key is still good
                    conn.execute(
                        "UPDATE instances SET last_active = CURRENT_TIMESTAMP WHERE instance_id = ?",
                        (instance_id,)
                    )
                    conn.commit()
                    return key_info['api_key']
                # Current key is at or near limit, find a new one
            
            # First try to find a key that's already assigned to this instance
            cursor = conn.execute("""
                SELECT k.key_id, k.api_key, COALESCE(u.request_count, 0) as request_count, k.daily_limit
                FROM instances i
                JOIN api_keys k ON i.key_id = k.key_id
                LEFT JOIN key_usage u ON k.key_id = u.key_id AND u.usage_date = ?
                WHERE i.instance_id = ?
                AND k.is_active = 1
                AND (u.request_count IS NULL OR u.request_count < k.daily_limit - ?)
                LIMIT 1
            """, (today, instance_id, threshold))
            
            key_info = cursor.fetchone()
            
            # If no suitable key assigned to this instance, find any available key
            if not key_info:
                cursor = conn.execute("""
                    SELECT k.key_id, k.api_key, COALESCE(u.request_count, 0) as request_count, k.daily_limit
                    FROM api_keys k
                    LEFT JOIN key_usage u ON k.key_id = u.key_id AND u.usage_date = ?
                    WHERE k.is_active = 1
                    AND (u.request_count IS NULL OR u.request_count < k.daily_limit - ?)
                    ORDER BY COALESCE(u.request_count, 0) ASC, k.key_id
                    LIMIT 1
                """, (today, threshold))
                key_info = cursor.fetchone()
            
            if not key_info:
                logger.error("No active API keys available")
                return None
                
            # Update or create usage record
            conn.execute("""
                INSERT INTO key_usage (key_id, usage_date, request_count, last_used)
                VALUES (?, ?, COALESCE((SELECT request_count FROM key_usage 
                                      WHERE key_id = ? AND usage_date = ?), 0) + 1, CURRENT_TIMESTAMP)
                ON CONFLICT(key_id, usage_date) DO UPDATE SET 
                    request_count = request_count + 1,
                    last_used = CURRENT_TIMESTAMP
            """, (key_info['key_id'], today, key_info['key_id'], today))
            
            # Update instance mapping
            conn.execute("""
                INSERT INTO instances (instance_id, key_id, last_active)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(instance_id) DO UPDATE SET 
                    key_id = excluded.key_id,
                    last_active = CURRENT_TIMESTAMP
            """, (instance_id, key_info['key_id']))
            
            conn.commit()
            logger.info(f"Assigned API key {key_info['key_id']} to instance {instance_id}")
            return key_info['api_key']
    
    def record_request(self, api_key: str) -> bool:
        """Record an API request for the given key.
        
        Args:
            api_key: The API key that was used
            
        Returns:
            bool: True if the request was recorded, False if key not found
        """
        today = date.today().isoformat()
        
        with self._get_connection() as conn:
            # Get the key ID
            cursor = conn.execute(
                "SELECT key_id FROM api_keys WHERE api_key = ?",
                (api_key,)
            )
            row = cursor.fetchone()
            if not row:
                return False
                
            key_id = row['key_id']
            
            # Update usage
            conn.execute("""
                INSERT INTO key_usage (key_id, usage_date, request_count, last_used)
                VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(key_id, usage_date) DO UPDATE SET 
                    request_count = request_count + 1,
                    last_used = CURRENT_TIMESTAMP
            """, (key_id, today))
            
            conn.commit()
            return True
    
    def get_usage_stats(self, days: int = 7, current_date: str = None) -> List[Dict]:
        """Get usage statistics for the past N days.
        
        Args:
            days: Number of days of history to include
            current_date: For testing purposes, specify the current date (YYYY-MM-DD)
            
        Returns:
            List of usage records
        """
        with self._get_connection() as conn:
            # For testing, we need to use the provided date or current date
            if current_date:
                cursor = conn.execute("""
                    SELECT 
                        k.key_id,
                        k.api_key,
                        u.usage_date,
                        u.request_count,
                        u.last_used,
                        k.daily_limit
                    FROM api_keys k
                    JOIN key_usage u ON k.key_id = u.key_id
                    WHERE u.usage_date >= date(?, '-' || ? || ' days')
                    AND u.usage_date <= date(?)
                    ORDER BY u.usage_date DESC, k.key_id
                """, (current_date, days, current_date))
            else:
                cursor = conn.execute("""
                    SELECT 
                        k.key_id,
                        k.api_key,
                        u.usage_date,
                        u.request_count,
                        u.last_used,
                        k.daily_limit
                    FROM api_keys k
                    JOIN key_usage u ON k.key_id = u.key_id
                    WHERE u.usage_date >= date('now', '-' || ? || ' days')
                    AND u.usage_date <= date('now')
                    ORDER BY u.usage_date DESC, k.key_id
                """, (days,))
            
            return [dict(row) for row in cursor.fetchall()]

# Singleton instance
key_manager = KeyManager()

# Example usage
if __name__ == "__main__":
    # Initialize with test keys
    key_manager = KeyManager("test_keys.db")
    
    # Add some test keys
    test_keys = ["test_key_1", "test_key_2", "test_key_3"]
    for key in test_keys:
        key_manager.add_api_key(key)
    
    # Simulate instance getting a key
    instance_id = str(uuid.uuid4())
    api_key = key_manager.get_instance_key(instance_id)
    print(f"Instance {instance_id} got API key: {api_key}")
    
    # Record some usage
    if api_key:
        key_manager.record_request(api_key)
        print("Recorded request")
    
    # Show usage stats
    print("\nUsage stats:")
    for stat in key_manager.get_usage_stats():
        print(f"Key {stat['key_id']}: {stat['request_count']} requests on {stat['usage_date']}")
