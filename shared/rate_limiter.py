"""
Redis sliding-window rate limiter.

Key format: {key_prefix}:{identifier}
Algorithm: sorted set (ZSET) with score = epoch ms timestamp.
Pipeline: ZREMRANGEBYSCORE + ZCARD + ZADD + EXPIRE for near-atomic execution.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass

import redis.asyncio as aioredis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int = 0
    retry_after: int = 0
    fail_open: bool = False


class RedisSlidingWindowLimiter:
    """
    Sliding window rate limiter backed by Redis ZSET.

    Multi-instance safe — all state lives in Redis.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        key_prefix: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        self._redis = redis_client
        self._key_prefix = key_prefix
        self._limit = limit
        self._window_seconds = window_seconds

    async def check(self, identifier: str) -> RateLimitResult:
        """
        Check rate limit for the given identifier using a Redis sliding window.

        Steps (inside a pipeline for near-atomicity):
          1. Remove entries older than (now - window_seconds).
          2. Count remaining entries (= requests in current window, before this one).
          3. Add the current request with score = now_ms.
          4. Set TTL so idle keys expire automatically.

        We read `count` BEFORE adding the current request.  That means:
          - count == 0  → this is the 1st request → allowed
          - count == limit-1 → this is the Nth request → allowed (remaining = 0)
          - count >= limit   → over limit → denied

        Returns RateLimitResult(allowed=True, remaining=-1, fail_open=True) on
        Redis errors — see DESIGN NOTE below.
        """
        key = f"{self._key_prefix}:{identifier}"
        now_ms = int(time.time() * 1000)
        window_start_ms = now_ms - self._window_seconds * 1000

        try:
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start_ms)
            pipe.zcard(key)
            pipe.zadd(key, {f"{now_ms}-{uuid.uuid4()}": now_ms})
            pipe.expire(key, self._window_seconds + 5)
            results = await pipe.execute()

            count_before = int(results[1])

            if count_before >= self._limit:
                # Already at or over limit — compute retry_after from oldest entry.
                oldest = await self._redis.zrange(key, 0, 0, withscores=True)
                retry_after = self._window_seconds
                if oldest:
                    oldest_score_ms = float(oldest[0][1])
                    retry_after = max(
                        1,
                        int((oldest_score_ms + self._window_seconds * 1000 - now_ms) / 1000),
                    )
                return RateLimitResult(allowed=False, retry_after=retry_after)

            remaining = self._limit - count_before - 1
            return RateLimitResult(allowed=True, remaining=remaining)

        except RedisError:
            # DESIGN: fail-open on Redis unavailable.  MVP trade-off — public
            # endpoint stays available during Redis outages; downside is no
            # rate-limit protection during outage.  Promotion to fail-closed
            # deferred until traffic warrants it.
            logger.warning(
                "rate_limiter_fail_open",
                extra={"redis_unavailable": True, "identifier": identifier},
            )
            return RateLimitResult(allowed=True, remaining=-1, fail_open=True)
