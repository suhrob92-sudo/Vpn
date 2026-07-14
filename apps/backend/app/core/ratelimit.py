"""Simple fixed-window rate limiting backed by Redis.

Fails open if Redis is unavailable — availability over strictness for MVP,
but the incident is logged for the admin alert task to pick up.
"""
import logging

from fastapi import HTTPException, Request, status

from app.core.redis import get_redis

logger = logging.getLogger(__name__)


def rate_limit(scope: str, limit: int, window_seconds: int = 60):
    """Dependency factory: at most `limit` requests per client IP per window."""

    async def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"rl:{scope}:{client_ip}"
        try:
            r = get_redis()
            current = await r.incr(key)
            if current == 1:
                await r.expire(key, window_seconds)
            if current > limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests",
                )
        except HTTPException:
            raise
        except Exception as exc:  # redis down
            logger.warning("rate limit check skipped (%s): %s", scope, exc)

    return dependency
