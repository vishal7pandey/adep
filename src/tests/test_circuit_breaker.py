"""Tests for the CircuitBreaker [§2.7, TS, NFT]."""

from __future__ import annotations

from src.agent.graph import CircuitBreaker


class TestCircuitBreaker:
    """Verify circuit breaker trip behavior."""

    def test_does_not_trip_below_threshold(self):
        breaker = CircuitBreaker(threshold=3)
        breaker.record_failure("vlm")
        breaker.record_failure("vlm")
        assert not breaker.is_tripped("vlm")

    def test_trips_at_threshold(self):
        breaker = CircuitBreaker(threshold=3)
        breaker.record_failure("vlm")
        breaker.record_failure("vlm")
        breaker.record_failure("vlm")
        assert breaker.is_tripped("vlm")

    def test_independent_per_provider(self):
        breaker = CircuitBreaker(threshold=2)
        breaker.record_failure("ocr")
        breaker.record_failure("ocr")
        assert breaker.is_tripped("ocr")
        assert not breaker.is_tripped("vlm")

    def test_unseen_provider_not_tripped(self):
        breaker = CircuitBreaker(threshold=3)
        assert not breaker.is_tripped("unknown")
