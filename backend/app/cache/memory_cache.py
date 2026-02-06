"""
In-Memory Cache Service.
"""

from cachetools import TTLCache
import asyncio
from typing import Any, Optional, Callable
from ..config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

class MemoryCache:
    _instance = None
    _cache: TTLCache

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MemoryCache, cls).__new__(cls)
            settings = get_settings()
            logger.info(f"Initializing MemoryCache with TTL={settings.cache_ttl_hours}h")
            cls._instance._cache = TTLCache(
                maxsize=1000,
                ttl=settings.cache_ttl_seconds
            )
        return cls._instance

    def get(self, key: str) -> Optional[Any]:
        """Retrieve item from cache."""
        val = self._cache.get(key)
        if val:
            logger.debug(f"Cache HIT for key: {key}")
        else:
            logger.debug(f"Cache MISS for key: {key}")
        return val

    def set(self, key: str, value: Any):
        """Set item in cache."""
        self._cache[key] = value

    def clear(self):
        """Clear all cache items."""
        self._cache.clear()
        logger.info("Cache cleared")

    async def get_or_set(self, key: str, factory_func: Callable, force_refresh: bool = False) -> Any:
        """
        Get from cache, or execute factory_func to set it.
        Handles async factory functions.
        """
        if not force_refresh:
            cached = self.get(key)
            if cached is not None:
                return cached
        
        # Execute factory
        logger.info(f"Fetching fresh data for key: {key}")
        result = await factory_func()
        
        self.set(key, result)
        return result

memory_cache = MemoryCache()
