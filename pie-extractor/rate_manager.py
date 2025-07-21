"""
Rate Limit and API Key Management System for OpenRouter Free Tier.
Handles automatic key rotation and usage tracking with SQLite.
"""

import sqlite3
import time
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import os
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class APIKeyInfo:
    """API key information and usage tracking."""
    key_id: str
    api_key: str
    daily_requests: int = 0
    last_request_time: float = 0
    is_active: bool = True
    balance_threshold_met: bool = False
    created_at: str = ""
    last_reset: str = ""


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int = 20
    requests_per_day_free: int = 50
    requests_per_day_paid: int = 1000
    key_switch_threshold: int = 40  # Switch when >= 40 requests used
    min_request_interval: float = 3.0  # 3 seconds between requests (20/min = 1 every 3s)
    balance_threshold: float = 10.0  # $10 for increased limits


class RateLimitError(Exception):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class APIKeyManager:
    """
    Manages multiple OpenRouter API keys with automatic rotation and usage tracking.
    
    Features:
    - SQLite-based usage tracking
    - Automatic key rotation based on usage
    - Rate limiting compliance
    - Instance-to-key mapping
    - Daily usage reset
    """
    
    def __init__(self, db_path: str = "api_keys.db", config: Optional[RateLimitConfig] = None):
        self.db_path = Path(db_path)
        self.config = config or RateLimitConfig()
        self.current_key: Optional[APIKeyInfo] = None
        self.instance_id = self._generate_instance_id()
        self._lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        # Load or assign key for this instance
        self._assign_instance_key()
        
        logger.info(f"APIKeyManager initialized for instance {self.instance_id}")
    
    def _generate_instance_id(self) -> str:
        """Generate unique instance ID."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _init_database(self):
        """Initialize SQLite database for key tracking."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    api_key TEXT UNIQUE NOT NULL,
                    daily_requests INTEGER DEFAULT 0,
                    last_request_time REAL DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    balance_threshold_met BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_reset TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS instance_mappings (
                    instance_id TEXT PRIMARY KEY,
                    key_id TEXT,
                    assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (key_id) REFERENCES api_keys (key_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_id TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    operation TEXT,
                    success BOOLEAN,
                    response_time REAL,
                    FOREIGN KEY (key_id) REFERENCES api_keys (key_id)
                )
            """)
            
            conn.commit()
    
    def add_api_key(self, api_key: str, balance_threshold_met: bool = False) -> str:
        """Add a new API key to the pool."""
        key_id = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO api_keys 
                    (key_id, api_key, balance_threshold_met, created_at, last_reset)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    key_id, api_key, balance_threshold_met,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                conn.commit()
                
                logger.info(f"Added API key {key_id} (balance_threshold_met: {balance_threshold_met})")
                return key_id
                
            except sqlite3.IntegrityError:
                logger.warning(f"API key {key_id} already exists")
                return key_id
    
    def _assign_instance_key(self):
        """Assign API key to this instance or load existing assignment."""
        with sqlite3.connect(self.db_path) as conn:
            # Check if instance already has a key assigned
            cursor = conn.execute("""
                SELECT key_id FROM instance_mappings WHERE instance_id = ?
            """, (self.instance_id,))
            
            result = cursor.fetchone()
            if result:
                # Load existing assignment
                key_id = result[0]
                self.current_key = self._load_key_info(key_id)
                logger.info(f"Loaded existing key assignment: {key_id}")
                return
            
            # Assign new key based on usage
            self.current_key = self._select_best_available_key()
            
            if self.current_key:
                # Record assignment
                conn.execute("""
                    INSERT OR REPLACE INTO instance_mappings (instance_id, key_id)
                    VALUES (?, ?)
                """, (self.instance_id, self.current_key.key_id))
                conn.commit()
                
                logger.info(f"Assigned new key {self.current_key.key_id} to instance {self.instance_id}")
            else:
                raise RateLimitError("No API keys available")
    
    def _load_key_info(self, key_id: str) -> Optional[APIKeyInfo]:
        """Load API key information from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM api_keys WHERE key_id = ? AND is_active = 1
            """, (key_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return APIKeyInfo(
                key_id=row[0],
                api_key=row[1],
                daily_requests=row[2],
                last_request_time=row[3],
                is_active=bool(row[4]),
                balance_threshold_met=bool(row[5]),
                created_at=row[6],
                last_reset=row[7]
            )
    
    def _select_best_available_key(self) -> Optional[APIKeyInfo]:
        """Select the best available API key based on usage."""
        with sqlite3.connect(self.db_path) as conn:
            # First, try to find keys under threshold
            cursor = conn.execute("""
                SELECT * FROM api_keys 
                WHERE is_active = 1 AND daily_requests < ?
                ORDER BY daily_requests ASC, last_request_time ASC
                LIMIT 1
            """, (self.config.key_switch_threshold,))
            
            row = cursor.fetchone()
            if row:
                return APIKeyInfo(
                    key_id=row[0],
                    api_key=row[1],
                    daily_requests=row[2],
                    last_request_time=row[3],
                    is_active=bool(row[4]),
                    balance_threshold_met=bool(row[5]),
                    created_at=row[6],
                    last_reset=row[7]
                )
            
            # If no keys under threshold, find the least used one
            cursor = conn.execute("""
                SELECT * FROM api_keys 
                WHERE is_active = 1
                ORDER BY daily_requests ASC, last_request_time ASC
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if row:
                return APIKeyInfo(
                    key_id=row[0],
                    api_key=row[1],
                    daily_requests=row[2],
                    last_request_time=row[3],
                    is_active=bool(row[4]),
                    balance_threshold_met=bool(row[5]),
                    created_at=row[6],
                    last_reset=row[7]
                )
            
            return None
    
    def get_current_api_key(self) -> str:
        """Get the current API key for this instance."""
        if not self.current_key:
            raise RateLimitError("No API key assigned to this instance")
        
        return self.current_key.api_key
    
    def can_make_request(self) -> Tuple[bool, Optional[str]]:
        """
        Check if a request can be made without violating rate limits.
        
        Returns:
            (can_make_request, reason_if_not)
        """
        if not self.current_key:
            return False, "No API key assigned"
        
        # Check daily limit
        daily_limit = (self.config.requests_per_day_paid 
                      if self.current_key.balance_threshold_met 
                      else self.config.requests_per_day_free)
        
        if self.current_key.daily_requests >= daily_limit:
            return False, f"Daily limit reached ({self.current_key.daily_requests}/{daily_limit})"
        
        # Check minute-based rate limiting
        current_time = time.time()
        time_since_last = current_time - self.current_key.last_request_time
        
        if time_since_last < self.config.min_request_interval:
            wait_time = self.config.min_request_interval - time_since_last
            return False, f"Rate limit: wait {wait_time:.1f} seconds"
        
        return True, None
    
    def record_request(self, operation: str, success: bool, response_time: float = 0.0):
        """Record a request and update usage statistics."""
        if not self.current_key:
            return
        
        with self._lock:
            current_time = time.time()
            
            # Update in-memory state
            self.current_key.daily_requests += 1
            self.current_key.last_request_time = current_time
            
            # Update database
            with sqlite3.connect(self.db_path) as conn:
                # Update key usage
                conn.execute("""
                    UPDATE api_keys 
                    SET daily_requests = ?, last_request_time = ?
                    WHERE key_id = ?
                """, (
                    self.current_key.daily_requests,
                    current_time,
                    self.current_key.key_id
                ))
                
                # Log usage
                conn.execute("""
                    INSERT INTO usage_log (key_id, operation, success, response_time)
                    VALUES (?, ?, ?, ?)
                """, (self.current_key.key_id, operation, success, response_time))
                
                conn.commit()
            
            logger.info(f"Recorded request: {operation} (success: {success}, "
                       f"usage: {self.current_key.daily_requests})")
    
    def wait_for_rate_limit(self):
        """Wait if necessary to comply with rate limits."""
        can_make, reason = self.can_make_request()
        
        if not can_make and "wait" in reason.lower():
            # Extract wait time from reason
            import re
            match = re.search(r'wait ([\d.]+) seconds', reason)
            if match:
                wait_time = float(match.group(1))
                logger.info(f"Rate limiting: waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
        elif not can_make:
            raise RateLimitError(reason)
    
    def reset_daily_usage(self):
        """Reset daily usage counters (typically called at midnight)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE api_keys 
                SET daily_requests = 0, last_reset = ?
                WHERE DATE(last_reset) < DATE('now')
            """, (datetime.now().isoformat(),))
            
            conn.commit()
            
            # Reload current key info
            if self.current_key:
                self.current_key = self._load_key_info(self.current_key.key_id)
        
        logger.info("Daily usage counters reset")
    
    def get_usage_stats(self) -> Dict:
        """Get usage statistics for all keys."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    key_id,
                    daily_requests,
                    balance_threshold_met,
                    is_active,
                    last_request_time
                FROM api_keys
                ORDER BY daily_requests DESC
            """)
            
            keys = []
            for row in cursor.fetchall():
                keys.append({
                    "key_id": row[0],
                    "daily_requests": row[1],
                    "balance_threshold_met": bool(row[2]),
                    "is_active": bool(row[3]),
                    "last_request_time": row[4],
                    "daily_limit": (self.config.requests_per_day_paid 
                                   if row[2] else self.config.requests_per_day_free)
                })
            
            # Get total usage
            cursor = conn.execute("""
                SELECT COUNT(*) FROM usage_log 
                WHERE DATE(timestamp) = DATE('now')
            """)
            total_today = cursor.fetchone()[0]
            
            return {
                "keys": keys,
                "total_requests_today": total_today,
                "current_instance": self.instance_id,
                "current_key": self.current_key.key_id if self.current_key else None
            }
    
    def should_switch_key(self) -> bool:
        """Check if the current key should be switched based on usage."""
        if not self.current_key:
            return True
        
        # Switch if over threshold
        if self.current_key.daily_requests >= self.config.key_switch_threshold:
            return True
        
        # Check if better key available
        better_key = self._select_best_available_key()
        if better_key and better_key.key_id != self.current_key.key_id:
            if better_key.daily_requests < self.current_key.daily_requests - 10:
                return True
        
        return False
    
    def switch_key(self) -> bool:
        """Switch to a different API key if beneficial."""
        if not self.should_switch_key():
            return False
        
        new_key = self._select_best_available_key()
        if not new_key or (self.current_key and new_key.key_id == self.current_key.key_id):
            return False
        
        old_key_id = self.current_key.key_id if self.current_key else "none"
        self.current_key = new_key
        
        # Update instance mapping
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE instance_mappings 
                SET key_id = ?, assigned_at = ?
                WHERE instance_id = ?
            """, (new_key.key_id, datetime.now().isoformat(), self.instance_id))
            conn.commit()
        
        logger.info(f"Switched from key {old_key_id} to {new_key.key_id}")
        return True


def setup_api_keys_from_env(manager: APIKeyManager):
    """Setup API keys from environment variables."""
    # Primary key
    primary_key = os.getenv('OPENROUTER_API_KEY')
    if primary_key:
        manager.add_api_key(primary_key, balance_threshold_met=False)
    
    # Additional keys (if you have multiple)
    for i in range(1, 6):  # Support up to 5 additional keys
        key = os.getenv(f'OPENROUTER_API_KEY_{i}')
        if key:
            # Check if this key has balance (you can set this manually)
            has_balance = os.getenv(f'OPENROUTER_API_KEY_{i}_BALANCE_MET', 'false').lower() == 'true'
            manager.add_api_key(key, balance_threshold_met=has_balance)


# Usage example and testing
if __name__ == "__main__":
    import sys
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Create rate manager
        config = RateLimitConfig(
            requests_per_minute=20,
            requests_per_day_free=50,
            key_switch_threshold=40
        )
        
        manager = APIKeyManager("test_api_keys.db", config)
        
        # Setup keys from environment
        setup_api_keys_from_env(manager)
        
        # Test usage
        print("Rate Limit Manager Test")
        print("=" * 30)
        
        # Check if we can make a request
        can_make, reason = manager.can_make_request()
        print(f"Can make request: {can_make}")
        if not can_make:
            print(f"Reason: {reason}")
        
        # Get current key
        try:
            current_key = manager.get_current_api_key()
            print(f"Current API key: {current_key[:20]}...")
        except RateLimitError as e:
            print(f"No API key available: {e}")
        
        # Get usage stats
        stats = manager.get_usage_stats()
        print(f"\nUsage Statistics:")
        print(f"Total requests today: {stats['total_requests_today']}")
        print(f"Current instance: {stats['current_instance']}")
        print(f"Current key: {stats['current_key']}")
        
        for key_info in stats['keys']:
            print(f"Key {key_info['key_id']}: {key_info['daily_requests']}/{key_info['daily_limit']} requests")
        
        print("\n✅ Rate manager test completed successfully")
        
    except Exception as e:
        print(f"❌ Rate manager test failed: {e}")
        sys.exit(1)