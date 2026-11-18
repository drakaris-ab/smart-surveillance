from cachetools import TTLCache
import asyncio
import time

# Shared caches for frames and queues
frame_cache = TTLCache(maxsize=100, ttl=30)
frame_cache_raw = TTLCache(maxsize=100, ttl=30)
camera_queues: dict[int, asyncio.Queue] = {}
last_capture_time: dict[int, float] = {}
