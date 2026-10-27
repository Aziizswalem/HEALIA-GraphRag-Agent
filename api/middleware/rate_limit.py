"""In-memory token bucket rate limit (per-process)."""

from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from config.settings import get_settings

_EXEMPT_PATHS = ("/health", "/ready", "/metrics", "/docs", "/redoc", "/openapi.json")
_memory_buckets: dict[str, tuple[float, float]] = {}


@dataclass
class RateLimitDecision:
    allowed: bool
    remaining_tokens: int
    retry_after_seconds: float
    limit: int


def _bucket_key(identifier: str) -> str:
    s = get_settings()
    return f"{s.RATE_LIMIT_PREFIX}:{identifier}"


def _refill(tokens: float, updated_at: float, now: float, capacity: int, refill_rate: float) -> float:
    elapsed = max(0.0, now - updated_at)
    return min(float(capacity), tokens + elapsed * refill_rate)


def _compute_decision(tokens: float, capacity: int, refill_rate: float) -> RateLimitDecision:
    if tokens >= 1.0:
        remaining = max(0, int(tokens - 1.0))
        return RateLimitDecision(
            allowed=True,
            remaining_tokens=remaining,
            retry_after_seconds=0.0,
            limit=capacity,
        )
    retry_after = (1.0 - tokens) / refill_rate if refill_rate > 0 else 1.0
    return RateLimitDecision(
        allowed=False,
        remaining_tokens=0,
        retry_after_seconds=max(0.0, retry_after),
        limit=capacity,
    )


def check_rate_limit(
    user_id: str,
    *,
    now: float | None = None,
    capacity: int | None = None,
    refill_rate: float | None = None,
) -> RateLimitDecision:
    s = get_settings()
    current_time = time.time() if now is None else now
    limit = int(capacity if capacity is not None else s.RATE_LIMIT_CAPACITY)
    refill = float(
        refill_rate
        if refill_rate is not None
        else s.RATE_LIMIT_REFILL_TOKENS_PER_SECOND
    )
    if limit <= 0 or refill <= 0:
        return RateLimitDecision(True, 10**9, 0.0, max(limit, 0))

    key = _bucket_key(user_id)

    tokens, updated_at = _memory_buckets.get(key, (float(limit), current_time))
    tokens = _refill(tokens, updated_at, current_time, limit, refill)
    decision = _compute_decision(tokens, limit, refill)
    stored_tokens = tokens - 1.0 if decision.allowed else tokens
    _memory_buckets[key] = (stored_tokens, current_time)
    return decision


def _request_identifier(request: Request) -> str:
    auth_context = getattr(request.state, "auth_context", None) or {}
    user_id = auth_context.get("user_id")
    if isinstance(user_id, str) and user_id.strip():
        return user_id.strip()
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        s = get_settings()
        if not s.RATE_LIMIT_ENABLED or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        identifier = _request_identifier(request)
        decision = check_rate_limit(identifier)
        request.state.rate_limit = decision

        if not decision.allowed:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )
            response.headers["Retry-After"] = f"{max(1, int(decision.retry_after_seconds + 0.999))}"
            response.headers["X-RateLimit-Limit"] = str(decision.limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(decision.limit)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining_tokens)
        return response
