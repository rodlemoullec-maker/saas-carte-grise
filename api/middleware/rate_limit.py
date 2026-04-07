"""
Middleware de rate limiting.

Deux backends :
- En mémoire (dev / si Redis indisponible) — sliding window par dict
- Redis (prod) — sliding window atomique

Limites :
- 60 req/min par IP (toutes routes)
- 10 req/min sur /auth/login (anti-brute-force)
- 20 req/min sur /documents/*/upload (coût OCR+Claude)
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ─── Config ─────────────────────────────────────────────────────────────────

RATE_LIMITS = {
    "default": (60, 60),        # 60 requêtes par 60 secondes
    "/auth/login": (10, 60),    # 10 tentatives par minute
    "/documents": (20, 60),     # 20 uploads par minute
}


# ─── Backend mémoire (dev / fallback) ───────────────────────────────────────

class InMemoryRateLimiter:
    """Sliding window en mémoire. Suffisant pour une seule instance."""

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds

        # Nettoyer les anciennes entrées
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

        if len(self._requests[key]) >= max_requests:
            return False

        self._requests[key].append(now)
        return True


# ─── Backend Redis (prod) ───────────────────────────────────────────────────

class RedisRateLimiter:
    """Sliding window via Redis ZSET. Fonctionne en multi-instance."""

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            import redis
            self._client = redis.from_url(self._redis_url)
        return self._client

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        try:
            r = self._get_client()
            now = time.time()
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, now - window_seconds)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window_seconds + 1)
            results = pipe.execute()
            count = results[2]
            return count <= max_requests
        except Exception as e:
            logger.warning(f"[RateLimit] Redis indisponible, fallback permissif: {e}")
            return True  # Fail open si Redis down


# ─── Factory ────────────────────────────────────────────────────────────────

_limiter = None


def get_limiter():
    global _limiter
    if _limiter is None:
        from config.settings import get_settings
        settings = get_settings()
        if settings.redis_url and settings.app_env.value != "development":
            try:
                _limiter = RedisRateLimiter(settings.redis_url)
                logger.info("[RateLimit] Backend Redis")
            except Exception:
                _limiter = InMemoryRateLimiter()
                logger.info("[RateLimit] Backend memoire (Redis indisponible)")
        else:
            _limiter = InMemoryRateLimiter()
            logger.info("[RateLimit] Backend memoire (dev)")
    return _limiter


# ─── Middleware FastAPI ─────────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next) -> Response:
        # Pas de rate limit sur /health et /docs
        path = request.url.path
        if path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        # Déterminer la limite applicable
        max_req, window = RATE_LIMITS["default"]
        for prefix, (m, w) in RATE_LIMITS.items():
            if prefix != "default" and path.startswith(prefix):
                max_req, window = m, w
                break

        # Clé = IP + path prefix
        client_ip = request.client.host if request.client else "unknown"
        key = f"rl:{client_ip}:{path.split('/')[1] if '/' in path[1:] else path}"

        limiter = get_limiter()
        if not limiter.is_allowed(key, max_req, window):
            logger.warning(f"[RateLimit] {client_ip} depasse {max_req}/{window}s sur {path}")
            return Response(
                content='{"detail":"Trop de requetes. Reessayez dans quelques instants."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(window)},
            )

        return await call_next(request)
