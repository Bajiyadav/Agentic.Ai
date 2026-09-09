import time
import json
import hashlib
from typing import Optional, Dict, Any

class SmartCache:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SmartCache, cls).__new__(cls)
            cls._instance._init_cache()
        return cls._instance

    def _init_cache(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._stats = {"hits": 0, "misses": 0}
        self.default_ttl = 7 * 24 * 3600  # 7 days

    def _generate_key(self, namespace: str, identifier: str) -> str:
        return f"{namespace}:{identifier.strip().lower()}"

    def get(self, namespace: str, identifier: str) -> Optional[Any]:
        key = self._generate_key(namespace, identifier)
        entry = self._store.get(key)
        if not entry:
            self._stats["misses"] += 1
            return None

        # Check TTL
        if time.time() > entry["expires_at"]:
            del self._store[key]
            self._stats["misses"] += 1
            return None

        self._stats["hits"] += 1
        return entry["value"]

    def set(self, namespace: str, identifier: str, value: Any, ttl: Optional[int] = None):
        key = self._generate_key(namespace, identifier)
        expiry = time.time() + (ttl if ttl is not None else self.default_ttl)
        self._store[key] = {
            "value": value,
            "expires_at": expiry,
            "saved_at": time.time()
        }

    def compute_file_hash(self, file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        total = self._stats["hits"] + self._stats["misses"]
        rate = round((self._stats["hits"] / total) * 100, 1) if total > 0 else 0.0
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "total_queries": total,
            "hit_rate_pct": rate,
            "cached_entries": len(self._store)
        }

# Global singleton
smart_cache = SmartCache()
