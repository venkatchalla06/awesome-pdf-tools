"""Redis client for the document comparison feature."""
import redis.asyncio as aioredis
from app.config import get_settings

_redis = None

async def get_redis():
    global _redis
    settings = get_settings()
    if _redis is None:
        _redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis

RESULT_TTL = 7 * 24 * 3600  # 7 days
UPLOAD_DIR = "/tmp/pdfkit/compare-uploads"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
