"""
Resilient Redis Cache Client for NEXUS AI:
Provides distributed caching with automatic, graceful fallback to InMemoryCacheStore
when Redis is unavailable, unreachable, or encounters connection drops.
"""

import time
import logging
from typing import Optional, Dict, Any, Tuple
from app.core.config import settings

logger = logging.getLogger("nexus.redis")

class InMemoryCacheStore:
    """In-memory key-value cache with TTL expiration support."""

    def __init__(self):
        # key -> (value, expire_timestamp_or_none)
        self._store: Dict[str, Tuple[str, Optional[float]]] = {}

    def get(self, key: str) -> Optional[str]:
        if key not in self._store:
            return None
        val, exp = self._store[key]
        if exp is not None and time.time() > exp:
            del self._store[key]
            return None
        return val

    def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        exp_time = (time.time() + expire) if expire else None
        self._store[key] = (str(value), exp_time)
        return True

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self):
        self._store.clear()

class RedisClient:
    """
    Asynchronous Redis client wrapper with resilient fallback.
    If Redis fails, operations seamlessly continue using in-memory cache.
    """

    def __init__(self):
        self.memory_store = InMemoryCacheStore()
        self.is_connected = False
        self._client = None
        self._initialized = False

    async def connect(self):
        """Attempt connection to Redis; fall back to in-memory store if offline."""
        if self._initialized:
            return

        try:
            import redis.asyncio as aioredis
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0
            )
            # Ping test
            await self._client.ping()
            self.is_connected = True
            logger.info("Connected to Redis cache successfully.")
        except Exception as e:
            self.is_connected = False
            self._client = None
            logger.info(f"Redis offline or unreachable ({e}). Using in-memory cache fallback.")

        self._initialized = True

    async def get(self, key: str) -> Optional[str]:
        """Get cached value. Falls back to in-memory store if Redis drops."""
        if self.is_connected and self._client:
            try:
                return await self._client.get(key)
            except Exception as e:
                logger.warning(f"Redis get failed ({e}), falling back to in-memory store.")
                self.is_connected = False
        return self.memory_store.get(key)

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set cached value with optional TTL expiration."""
        # Always update in-memory store as backup
        self.memory_store.set(key, value, expire)

        if self.is_connected and self._client:
            try:
                if expire:
                    await self._client.setex(key, expire, str(value))
                else:
                    await self._client.set(key, str(value))
                return True
            except Exception as e:
                logger.warning(f"Redis set failed ({e}), saved in in-memory fallback.")
                self.is_connected = False
        return True

    async def delete(self, key: str) -> bool:
        """Delete cached key."""
        mem_deleted = self.memory_store.delete(key)
        if self.is_connected and self._client:
            try:
                await self._client.delete(key)
                return True
            except Exception as e:
                logger.warning(f"Redis delete failed ({e}).")
                self.is_connected = False
        return mem_deleted

    async def close(self):
        """Close Redis connection."""
        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None
            self.is_connected = False

redis_client = RedisClient()
