"""
Rate-limit middleware for Zanovix CRM.

Redis key format: rate_limit:leads:post:{ip}
Limit:           20 requests / 60 seconds / IP address (sliding window).

Fail-open: if Redis is unavailable, the request is allowed through and a
WARNING is logged.  See shared/rate_limiter.py for the design rationale.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from shared.rate_limiter import RedisSlidingWindowLimiter

# ── Constants ────────────────────────────────────────────────────────────────

WINDOW_SECONDS = 60
MAX_REQUESTS = 20
KEY_PREFIX = "rate_limit:leads:post"  # spec §6 key format


# ── Factory ───────────────────────────────────────────────────────────────────

def get_lead_post_limiter(request: Request) -> RedisSlidingWindowLimiter:
    """
    Return a RedisSlidingWindowLimiter wired to the app's Redis client.

    Usage as a FastAPI dependency (used by Phase 5 POST /api/leads):
        dependencies=[Depends(enforce_lead_post_rate_limit)]
    """
    redis_client = request.app.state.redis
    return RedisSlidingWindowLimiter(
        redis_client=redis_client,
        key_prefix=KEY_PREFIX,
        limit=MAX_REQUESTS,
        window_seconds=WINDOW_SECONDS,
    )


# ── Dependency ────────────────────────────────────────────────────────────────

async def enforce_lead_post_rate_limit(
    request: Request,
    limiter: RedisSlidingWindowLimiter = Depends(get_lead_post_limiter),
) -> None:
    """
    FastAPI dependency that enforces the lead-post rate limit.

    Extracts the client IP (preferring the first value of X-Forwarded-For over
    the raw connection address), checks the sliding window, and raises HTTP 429
    if the limit is exceeded.
    """
    ip = _client_ip(request)
    result = await limiter.check(ip)

    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "retry_after_seconds": result.retry_after,
            },
            headers={"Retry-After": str(result.retry_after)},
        )


def _client_ip(request: Request) -> str:
    """
    Extract the real client IP.

    Prefers the first IP in X-Forwarded-For (set by proxies / load balancers),
    falls back to the direct TCP connection address.
    """
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
