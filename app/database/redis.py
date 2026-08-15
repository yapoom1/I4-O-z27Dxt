import redis.asyncio as aioredis
from app.config import settings

class RedisClient:
    """Asynchronous Redis client wrapper."""
    def __init__(self):
        self.client: aioredis.Redis | None = None

    def connect(self) -> aioredis.Redis:
        """Establish Redis connection pool."""
        self.client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20
        )
        return self.client

    async def close(self) -> None:
        """Disconnect Redis client."""
        if self.client:
            await self.client.aclose()

    async def get(self, key: str) -> str | None:
        if not self.client:
            raise RuntimeError("Redis client not initialized")
        return await self.client.get(key)

    async def set(self, key: str, value: str, expire_seconds: int | None = None) -> None:
        if not self.client:
            raise RuntimeError("Redis client not initialized")
        await self.client.set(key, value, ex=expire_seconds)

    async def delete(self, key: str) -> int:
        if not self.client:
            raise RuntimeError("Redis client not initialized")
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        if not self.client:
            raise RuntimeError("Redis client not initialized")
        return await self.client.exists(key)

redis_client = RedisClient()
