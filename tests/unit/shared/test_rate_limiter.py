"""
Unit tests for shared/rate_limiter.py — uses fakeredis, no real Redis needed.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from shared.rate_limiter import RedisSlidingWindowLimiter, RateLimitResult


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis()


def make_limiter(redis_client, limit: int = 10, window_seconds: int = 60):
    return RedisSlidingWindowLimiter(
        redis_client=redis_client,
        key_prefix="test:rl",
        limit=limit,
        window_seconds=window_seconds,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_within_limit_allows(fake_redis):
    """5 calls under limit=10 → all allowed, remaining decreases monotonically."""
    limiter = make_limiter(fake_redis, limit=10)
    identifier = "192.0.2.1"

    results = []
    for _ in range(5):
        result = await limiter.check(identifier)
        results.append(result)

    assert all(r.allowed for r in results)
    # remaining should decrease: 9, 8, 7, 6, 5
    remainings = [r.remaining for r in results]
    assert remainings == sorted(remainings, reverse=True), "remaining should decrease"
    assert remainings[0] == 9
    assert remainings[-1] == 5


async def test_exceeds_limit_denies(fake_redis):
    """11 calls with limit=10 → 11th denied with retry_after > 0."""
    limiter = make_limiter(fake_redis, limit=10)
    identifier = "192.0.2.2"

    for i in range(10):
        result = await limiter.check(identifier)
        assert result.allowed, f"call {i+1} should be allowed"

    # 11th call must be denied
    result = await limiter.check(identifier)
    assert not result.allowed
    assert result.retry_after > 0


async def test_window_slides(fake_redis):
    """
    Send N=10 requests at t=0, advance time past the window, send 1 more → allowed.
    """
    limiter = make_limiter(fake_redis, limit=10, window_seconds=60)
    identifier = "192.0.2.3"

    # Fill the window at t=0
    for _ in range(10):
        await limiter.check(identifier)

    # Verify we are now at limit
    result = await limiter.check(identifier)
    assert not result.allowed

    # Advance time beyond the window (61 seconds ahead)
    future_time = time.time() + 61

    with patch("shared.rate_limiter.time") as mock_time:
        mock_time.time.return_value = future_time
        result = await limiter.check(identifier)

    assert result.allowed, "after window expires, request should be allowed"


async def test_redis_unavailable_fails_open(fake_redis):
    """On RedisError → allowed=True, fail_open=True (fail-open design)."""
    limiter = make_limiter(fake_redis, limit=10)

    # Replace the pipeline with one that raises RedisConnectionError
    async def broken_pipeline(*args, **kwargs):
        raise RedisConnectionError("Cannot connect to Redis")

    with patch.object(fake_redis, "pipeline") as mock_pipe_factory:
        mock_pipe = AsyncMock()
        mock_pipe.zremrangebyscore = AsyncMock()
        mock_pipe.zcard = AsyncMock()
        mock_pipe.zadd = AsyncMock()
        mock_pipe.expire = AsyncMock()
        mock_pipe.execute = AsyncMock(side_effect=RedisConnectionError("down"))
        mock_pipe_factory.return_value = mock_pipe

        result = await limiter.check("192.0.2.4")

    assert result.allowed is True
    assert result.fail_open is True


async def test_different_identifiers_independent(fake_redis):
    """IP A and IP B should have completely independent counters."""
    limiter = make_limiter(fake_redis, limit=3)
    ip_a = "10.0.0.1"
    ip_b = "10.0.0.2"

    # Exhaust limit for ip_a
    for _ in range(3):
        await limiter.check(ip_a)

    # ip_a is now over limit
    result_a = await limiter.check(ip_a)
    assert not result_a.allowed

    # ip_b should still be unaffected
    result_b = await limiter.check(ip_b)
    assert result_b.allowed
