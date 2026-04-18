import redis as redis_lib
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import get_settings

settings = get_settings()

RATE_LIMITS = {
    "free":       (10, 60),
    "pro":        (100, 60),
    "enterprise": (1000, 60),
}

# Sync redis client for middleware (Starlette middleware is sync-friendly)
_redis = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/v1/tools"):
            return await call_next(request)

        tier = getattr(request.state, "user_tier", "free")
        limit, window = RATE_LIMITS.get(tier, RATE_LIMITS["free"])

        ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
        key = f"rl:{tier}:{ip}"

        try:
            count = _redis.incr(key)
            if count == 1:
                _redis.expire(key, window)
        except Exception:
            # Redis down → fail open, log in production
            return await call_next(request)

        if count > limit:
            return Response(
                content='{"detail":"Rate limit exceeded. Upgrade your plan for more requests."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(window), "X-RateLimit-Limit": str(limit)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        return response
