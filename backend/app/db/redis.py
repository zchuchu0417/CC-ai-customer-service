"""Redis 客户端"""
import redis
from app.config import settings

redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    decode_responses=True,
)


def check_redis() -> str:
    try:
        redis_client.ping()
        return "connected"
    except Exception as e:
        return f"error: {str(e)[:60]}"