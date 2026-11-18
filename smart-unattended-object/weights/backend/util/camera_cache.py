import time

class HybridCache:
    def __init__(self, ttl: int = 120):
        self.ttl = ttl
        self.store = {}

    def get(self, key: str):
        """Get a cached value if still valid."""
        entry = self.store.get(key)
        if entry and (time.time() - entry["time"] < self.ttl):
            return entry["value"]
        return None

    def set(self, key: str, value):
        """Set a value in cache with timestamp."""
        self.store[key] = {"value": value, "time": time.time()}

    def invalidate(self, key: str):
        """Remove a cached entry."""
        self.store.pop(key, None)

    def get_all(self):
        """Return all valid entries (dict of key -> value)."""
        now = time.time()
        return {
            k: v["value"]
            for k, v in self.store.items()
            if now - v["time"] < self.ttl
        }

# Global cache instance (import this anywhere)
global_cache = HybridCache(ttl=120)
