"""Regression for ADE-19: the rate limiter singleton must not leak state between tests.

The process-wide limiter (src/api/rate_limit.py) keeps per-IP token buckets. Without the autouse
reset in conftest.py, buckets drained by early tests throttle later ones (HTTP 429) and the
suite fails depending on how fast it runs. The two tests below run in definition order: the first
drains a bucket, the second asserts the next test starts clean.
"""

from __future__ import annotations

from src.api.rate_limit import TokenBucket, get_limiter


class TestLimiterIsolation:
    def test_a_drain_a_bucket(self):
        limiter = get_limiter()
        limiter._buckets["ip:testclient:mutating"] = TokenBucket(capacity=60, tokens=0.0)
        assert limiter.get_stats()["buckets"] == 1

    def test_b_next_test_starts_clean(self):
        assert get_limiter().get_stats()["buckets"] == 0
