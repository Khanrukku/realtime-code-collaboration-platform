import json
import redis.asyncio as redis

from app.core.config import settings

class RedisBus:
    """Optional cross-instance Pub/Sub adapter for future horizontal scaling."""

    def __init__(self):
        self.client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )

    async def publish(self, room_id: str, payload: dict):
        await self.client.publish(
            f"room:{room_id}",
            json.dumps(payload),
        )

    async def close(self):
        await self.client.aclose()
