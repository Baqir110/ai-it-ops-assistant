"""Rate limiting middleware for OpsGuard API."""

import time
import logging
from collections import defaultdict
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter.

    Limits requests per client IP within a sliding window.
    Uses Redis if available, falls back to in-memory storage.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self._requests_per_minute = requests_per_minute
        self._window_seconds = 60
        self._clients: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED or not settings.RATE_LIMIT_REQUESTS_PER_MINUTE:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean old entries
        self._clients[client_ip] = [
            t for t in self._clients[client_ip]
            if now - t < self._window_seconds
        ]

        # Check limit
        if len(self._clients[client_ip]) >= self._requests_per_minute:
            logger.warning("Rate limit exceeded for %s", client_ip)
            return Response(
                content='{"detail": "Rate limit exceeded. Try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )

        # Record request
        self._clients[client_ip].append(now)

        response = await call_next(request)
        return response
