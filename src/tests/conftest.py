"""Shared test fixtures."""

from __future__ import annotations

import pytest

from src.api.rate_limit import reset_limiter


@pytest.fixture(autouse=True)
def _fresh_rate_limiter():
    """Start every test with empty rate-limit buckets [ADE-19].

    The limiter is a process-wide singleton keyed by client IP, and every TestClient is
    "testclient", so buckets drained by earlier tests would otherwise throttle later ones (429).
    The production default (limiting on) is untouched; test_rate_limiting.py still exercises it.
    """
    reset_limiter()
    yield
