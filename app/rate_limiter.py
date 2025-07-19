import time
from collections import defaultdict
from typing import Dict, List
from fastapi import HTTPException, Request
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self):
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.max_requests = settings.RATE_LIMIT_REQUESTS
        self.window_size = settings.RATE_LIMIT_WINDOW

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Try to get real IP from headers (if behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct client host
        return request.client.host or "unknown"

    def _clean_old_requests(self, client_id: str):
        """Remove requests older than the window"""
        current_time = time.time()
        cutoff_time = current_time - self.window_size

        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id] if req_time > cutoff_time
        ]

    async def check_rate_limit(self, request: Request):
        """Check if request should be rate limited"""
        client_id = self._get_client_id(request)
        current_time = time.time()

        # Clean old requests
        self._clean_old_requests(client_id)

        # Check if over limit
        if len(self.requests[client_id]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window_size} seconds.",
                headers={"Retry-After": str(self.window_size)},
            )

        # Add current request
        self.requests[client_id].append(current_time)

        logger.debug(
            f"Rate limit check passed for {client_id}: {len(self.requests[client_id])}/{self.max_requests}"
        )


# Global rate limiter instance
rate_limiter = RateLimiter()
