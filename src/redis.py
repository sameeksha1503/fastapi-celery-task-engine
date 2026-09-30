import redis.asyncio as redis

REDIS_URL="redis://127.0.0.1:6379/0"

redis_client = redis.from_url(
    REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    # protocol=2
)