#!/usr/bin/env python3
"""
Lightweight memory manager for AI agents
Zero RAM overhead - file-based storage with smart caching
"""

import json
import os
import time
import fcntl
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import sqlite3


class MemoryManager:
    """Lightweight file-based memory manager with optional SQLite indexing"""
    
    def __init__(self, base_path: str = "./ai-agents-shared-memory"):
        self.base_path = Path(base_path)
        self.config_path = self.base_path / ".memory-config.json"
        self.config = self._load_config()
        self.storage_path = self.base_path / self.config["storage"]["base_path"]
        self.locks_path = self.base_path / "locks"
        
        # Create directories
        for category in self.config["categories"].keys():
            (self.storage_path / category).mkdir(parents=True, exist_ok=True)
        self.locks_path.mkdir(parents=True, exist_ok=True)
        
        # Optional SQLite index for fast queries
        self.db_path = self.base_path / "index.db"
        if self.config["indexing"]["enabled"]:
            self._init_index()
    
    def _load_config(self) -> Dict:
        """Load configuration (lightweight operation)"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _init_index(self):
        """Initialize SQLite index (minimal overhead ~100KB)"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS memory_index (
                id TEXT PRIMARY KEY,
                category TEXT,
                agent TEXT,
                timestamp TEXT,
                tags TEXT,
                file_path TEXT,
                checksum TEXT
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_category ON memory_index(category)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_agent ON memory_index(agent)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON memory_index(timestamp)')
        conn.commit()
        conn.close()
    
    def _acquire_lock(self, lock_name: str, timeout: int = 5) -> Optional[Any]:
        """File-based locking for concurrent access"""
        lock_file = self.locks_path / f"{lock_name}.lock"
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                lock_fd = open(lock_file, 'w')
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return lock_fd
            except IOError:
                time.sleep(0.1)
        
        return None
    
    def _release_lock(self, lock_fd):
        """Release file lock"""
        if lock_fd:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()
    
    def write(self, category: str, key: str, data: Dict, agent: str = "unknown", tags: List[str] = None) -> bool:
        """
        Write data to shared memory (file-based, no RAM overhead)
        
        Args:
            category: context, knowledge, tasks, or history
            key: Unique identifier for this memory
            data: Data to store
            agent: Name of the agent writing (kilocode, roocode, cline)
            tags: Optional tags for searching
        """
        if category not in self.config["categories"]:
            raise ValueError(f"Invalid category: {category}")
        
        # Create memory entry
        entry = {
            "id": hashlib.md5(f"{category}:{key}".encode()).hexdigest(),
            "category": category,
            "key": key,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
            "tags": tags or [],
            "data": data
        }
        
        # Write to file with locking
        file_path = self.storage_path / category / f"{key}.json"
        lock_fd = self._acquire_lock(f"{category}_{key}")
        
        try:
            with open(file_path, 'w') as f:
                json.dump(entry, f, indent=2)
            
            # Update index
            if self.config["indexing"]["enabled"]:
                checksum = hashlib.md5(json.dumps(data).encode()).hexdigest()
                conn = sqlite3.connect(self.db_path)
                conn.execute('''
                    INSERT OR REPLACE INTO memory_index 
                    (id, category, agent, timestamp, tags, file_path, checksum)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (entry["id"], category, agent, entry["timestamp"], 
                      json.dumps(tags), str(file_path), checksum))
                conn.commit()
                conn.close()
            
            return True
        finally:
            self._release_lock(lock_fd)
    
    def read(self, category: str, key: str) -> Optional[Dict]:
        """
        Read data from shared memory (on-demand, no RAM caching)
        
        Args:
            category: context, knowledge, tasks, or history
            key: Unique identifier for this memory
        """
        file_path = self.storage_path / category / f"{key}.json"
        
        if not file_path.exists():
            return None
        
        lock_fd = self._acquire_lock(f"{category}_{key}")
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        finally:
            self._release_lock(lock_fd)
    
    def query(self, category: Optional[str] = None, agent: Optional[str] = None, 
              tags: Optional[List[str]] = None, limit: int = 100) -> List[Dict]:
        """
        Query memories with filters (uses index for speed)
        
        Args:
            category: Filter by category
            agent: Filter by agent
            tags: Filter by tags (any match)
            limit: Maximum results
        """
        if not self.config["indexing"]["enabled"]:
            # Fallback to file scanning
            return self._query_files(category, agent, tags, limit)
        
        # Use SQLite index
        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM memory_index WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        if agent:
            query += " AND agent = ?"
            params.append(agent)
        if tags:
            # Simple tag matching (can be optimized with FTS)
            for tag in tags:
                query += " AND tags LIKE ?"
                params.append(f'%"{tag}"%')
        
        query += f" ORDER BY timestamp DESC LIMIT {limit}"
        
        cursor = conn.execute(query, params)
        results = []
        
        for row in cursor.fetchall():
            file_path = Path(row[5])
            if file_path.exists():
                with open(file_path, 'r') as f:
                    results.append(json.load(f))
        
        conn.close()
        return results
    
    def _query_files(self, category: Optional[str], agent: Optional[str], 
                     tags: Optional[List[str]], limit: int) -> List[Dict]:
        """Fallback query by scanning files"""
        results = []
        categories = [category] if category else self.config["categories"].keys()
        
        for cat in categories:
            cat_path = self.storage_path / cat
            if not cat_path.exists():
                continue
            
            for file_path in cat_path.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        entry = json.load(f)
                    
                    # Apply filters
                    if agent and entry.get("agent") != agent:
                        continue
                    if tags and not any(t in entry.get("tags", []) for t in tags):
                        continue
                    
                    results.append(entry)
                    
                    if len(results) >= limit:
                        break
                except Exception:
                    continue
            
            if len(results) >= limit:
                break
        
        # Sort by timestamp
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results[:limit]
    
    def cleanup(self):
        """Remove expired entries based on TTL"""
        for category, settings in self.config["categories"].items():
            ttl_hours = settings.get("ttl_hours")
            if ttl_hours is None:
                continue
            
            expiry_time = datetime.utcnow() - timedelta(hours=ttl_hours)
            cat_path = self.storage_path / category
            
            if not cat_path.exists():
                continue
            
            for file_path in cat_path.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        entry = json.load(f)
                    
                    timestamp = datetime.fromisoformat(entry["timestamp"])
                    if timestamp < expiry_time:
                        file_path.unlink()
                        
                        # Remove from index
                        if self.config["indexing"]["enabled"]:
                            conn = sqlite3.connect(self.db_path)
                            conn.execute("DELETE FROM memory_index WHERE id = ?", (entry["id"],))
                            conn.commit()
                            conn.close()
                except Exception:
                    continue
    
    def get_stats(self) -> Dict:
        """Get memory usage statistics"""
        stats = {
            "total_entries": 0,
            "categories": {},
            "disk_usage_mb": 0
        }
        
        for category in self.config["categories"].keys():
            cat_path = self.storage_path / category
            if not cat_path.exists():
                continue
            
            files = list(cat_path.glob("*.json"))
            stats["categories"][category] = len(files)
            stats["total_entries"] += len(files)
            
            for file_path in files:
                stats["disk_usage_mb"] += file_path.stat().st_size / (1024 * 1024)
        
        return stats


if __name__ == "__main__":
    # Example usage
    manager = MemoryManager()
    
    # Write context
    manager.write(
        category="context",
        key="current_task",
        data={
            "task": "implementing authentication",
            "status": "in_progress",
            "files": ["auth.py", "middleware.py"]
        },
        agent="kilocode",
        tags=["authentication", "in_progress"]
    )
    
    # Read context
    context = manager.read("context", "current_task")
    print("Current context:", context)
    
    # Query knowledge
    knowledge = manager.query(category="knowledge", tags=["bug_fix"])
    print(f"Found {len(knowledge)} knowledge entries")
    
    # Get stats
    stats = manager.get_stats()
    print("Memory stats:", stats)
