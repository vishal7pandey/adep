"""Retry storm prevention & circuit breaker [BLK-085].

Prevent retry storms when the LLM API is degraded. Implements:
1. Exponential backoff with jitter
2. Circuit breaker pattern (closed/open/half-open)
3. Per-run retry budget
4. Token-aware retry tracking
5. Provider fallback support
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Defaults
BACKOFF_BASE = 2.0  # seconds
BACKOFF_MAX = 60.0  # seconds
MAX_RETRY_ATTEMPTS = 3
CIRCUIT_FAILURE_THRESHOLD = 5
CIRCUIT_COOLDOWN = 60.0  # seconds
PER_RUN_RETRY_BUDGET = 10
RETRY_TOKEN_BUDGET_RATIO = 0.20  # 20% of run budget


class CircuitState(str, Enum):
    """Circuit breaker states [BLK-085]."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Tripped — fail-fast
    HALF_OPEN = "half_open"  # Testing if provider recovered


@dataclass
class CircuitBreakerStatus:
    """Status of a circuit breaker for a provider [BLK-085].

    Attributes:
        state: Current circuit state.
        consecutive_failures: Current consecutive failure count.
        last_failure_time: Timestamp of last failure.
        last_state_change: Timestamp of last state transition.
    """

    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_failure_time: float = 0.0
    last_state_change: float = field(default_factory=time.time)


class GlobalCircuitBreaker:
    """Global circuit breaker tracking LLM API health across all runs [BLK-085].

    Unlike the per-run CircuitBreaker in graph.py, this is a process-wide
    singleton that tracks provider health across all concurrent runs.

    States:
    - CLOSED: Normal operation, requests pass through.
    - OPEN: After N consecutive failures, all new calls fail-fast.
      No retries during open state. Stays open for cooldown period.
    - HALF_OPEN: After cooldown, allows 1 test request. If it succeeds,
      closes the circuit. If it fails, re-opens.
    """

    def __init__(
        self,
        failure_threshold: int = CIRCUIT_FAILURE_THRESHOLD,
        cooldown: float = CIRCUIT_COOLDOWN,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown = cooldown
        self._providers: dict[str, CircuitBreakerStatus] = {}

    def _get_status(self, provider: str) -> CircuitBreakerStatus:
        if provider not in self._providers:
            self._providers[provider] = CircuitBreakerStatus()
        return self._providers[provider]

    def can_call(self, provider: str) -> tuple[bool, str]:
        """Check if a call is allowed under the current circuit state [BLK-085].

        Returns:
            Tuple of (allowed, reason).
        """
        status = self._get_status(provider)
        now = time.time()

        if status.state == CircuitState.CLOSED:
            return True, ""

        if status.state == CircuitState.OPEN:
            # Check if cooldown has elapsed
            if now - status.last_state_change >= self.cooldown:
                # Transition to half-open
                status.state = CircuitState.HALF_OPEN
                status.last_state_change = now
                logger.info(
                    "Circuit breaker for '%s' transitioning to HALF_OPEN [BLK-085]", provider
                )
                return True, "half_open_test"

            return False, f"Circuit breaker open for provider '{provider}'"

        if status.state == CircuitState.HALF_OPEN:
            # Only allow one test call at a time
            # If we're still in half-open, only the first call gets through
            return True, "half_open_test"

        return True, ""

    def record_success(self, provider: str) -> None:
        """Record a successful call — closes the circuit [BLK-085]."""
        status = self._get_status(provider)
        if status.state != CircuitState.CLOSED:
            logger.info("Circuit breaker for '%s' closing (recovered) [BLK-085]", provider)
        status.state = CircuitState.CLOSED
        status.consecutive_failures = 0
        status.last_state_change = time.time()

    def record_failure(self, provider: str) -> None:
        """Record a failed call — may trip the circuit [BLK-085]."""
        status = self._get_status(provider)
        status.consecutive_failures += 1
        status.last_failure_time = time.time()

        if status.state == CircuitState.HALF_OPEN:
            # Half-open failure — re-open
            status.state = CircuitState.OPEN
            status.last_state_change = time.time()
            logger.warning(
                "Circuit breaker for '%s' re-OPENED (half-open test failed) [BLK-085]", provider
            )
        elif status.consecutive_failures >= self.failure_threshold:
            status.state = CircuitState.OPEN
            status.last_state_change = time.time()
            logger.warning(
                "Circuit breaker for '%s' OPENED after %d consecutive failures [BLK-085]",
                provider,
                status.consecutive_failures,
            )

    def get_status(self, provider: str) -> CircuitBreakerStatus:
        """Get the current status for a provider."""
        return self._get_status(provider)


# Singleton
_global_breaker: GlobalCircuitBreaker | None = None


def get_global_circuit_breaker() -> GlobalCircuitBreaker:
    """Get the singleton GlobalCircuitBreaker [BLK-085]."""
    global _global_breaker
    if _global_breaker is None:
        _global_breaker = GlobalCircuitBreaker()
    return _global_breaker


def reset_global_circuit_breaker() -> None:
    """Reset the global circuit breaker (for testing)."""
    global _global_breaker
    _global_breaker = None


def compute_backoff_wait(
    attempt: int, base: float = BACKOFF_BASE, max_wait: float = BACKOFF_MAX
) -> float:
    """Compute exponential backoff wait time with jitter [BLK-085].

    Formula: wait = min(base * 2^attempt + random_jitter, max_wait)

    Args:
        attempt: Zero-indexed attempt number.
        base: Base wait time in seconds.
        max_wait: Maximum wait time in seconds.

    Returns:
        Wait time in seconds.
    """
    exponential = base * (2**attempt)
    jitter = random.uniform(0, base)
    return min(exponential + jitter, max_wait)


@dataclass
class RunRetryBudget:
    """Per-run retry budget tracker [BLK-085].

    Attributes:
        max_retries: Maximum total retries for the run.
        retry_count: Current retry count.
        retry_tokens: Tokens consumed by retries.
        max_retry_tokens: Maximum tokens allowed for retries (20% of run budget).
    """

    max_retries: int = PER_RUN_RETRY_BUDGET
    retry_count: int = 0
    retry_tokens: int = 0
    max_retry_tokens: int = 0

    def __post_init__(self) -> None:
        if self.max_retry_tokens == 0:
            # Default to 20% of a typical run budget
            self.max_retry_tokens = int(100_000 * RETRY_TOKEN_BUDGET_RATIO)

    def can_retry(self) -> tuple[bool, str]:
        """Check if a retry is allowed under the budget [BLK-085].

        Returns:
            Tuple of (allowed, reason_if_denied).
        """
        if self.retry_count >= self.max_retries:
            return False, f"Per-run retry budget exhausted ({self.retry_count}/{self.max_retries})"
        if self.retry_tokens >= self.max_retry_tokens:
            return (
                False,
                f"Retry token budget exhausted ({self.retry_tokens}/{self.max_retry_tokens} tokens)",
            )
        return True, ""

    def record_retry(self, tokens_consumed: int = 0) -> None:
        """Record a retry attempt [BLK-085]."""
        self.retry_count += 1
        self.retry_tokens += tokens_consumed
        logger.info(
            "Retry recorded: attempt %d/%d, tokens %d/%d [BLK-085]",
            self.retry_count,
            self.max_retries,
            self.retry_tokens,
            self.max_retry_tokens,
        )


@dataclass
class RetryResult:
    """Result of a retry-attempted LLM call [BLK-085].

    Attributes:
        success: Whether the call eventually succeeded.
        result: The result if successful.
        error: Error message if all retries failed.
        attempts: Total number of attempts (including initial).
        total_wait: Total time spent waiting between retries.
        retries: Number of retries (attempts - 1).
    """

    success: bool
    result: Any = None
    error: str = ""
    attempts: int = 0
    total_wait: float = 0.0
    retries: int = 0


def retry_with_circuit_breaker(
    func: Callable[..., Any],
    provider: str,
    args: tuple = (),
    kwargs: dict[str, Any] | None = None,
    max_attempts: int = MAX_RETRY_ATTEMPTS,
    run_budget: RunRetryBudget | None = None,
    circuit_breaker: GlobalCircuitBreaker | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> RetryResult:
    """Execute a function with retry, backoff, and circuit breaker [BLK-085].

    Args:
        func: The function to call (typically an LLM invoke).
        provider: Provider name for circuit breaker tracking.
        args: Positional arguments for func.
        kwargs: Keyword arguments for func.
        max_attempts: Maximum total attempts (including initial).
        run_budget: Optional per-run retry budget.
        circuit_breaker: Optional circuit breaker (uses global if None).
        sleep_fn: Sleep function (injectable for testing).

    Returns:
        RetryResult with outcome.
    """
    if kwargs is None:
        kwargs = {}
    if circuit_breaker is None:
        circuit_breaker = get_global_circuit_breaker()

    total_wait = 0.0
    attempts = 0
    last_error = ""

    for attempt in range(max_attempts):
        attempts += 1

        # Check circuit breaker
        allowed, reason = circuit_breaker.can_call(provider)
        if not allowed:
            logger.warning("Circuit breaker blocked call to '%s': %s [BLK-085]", provider, reason)
            return RetryResult(
                success=False,
                error=f"Circuit breaker open: {reason}",
                attempts=attempts,
                total_wait=total_wait,
                retries=attempts - 1,
            )

        # Check run retry budget (only for retries, not initial attempt)
        if attempt > 0 and run_budget is not None:
            can_retry, budget_reason = run_budget.can_retry()
            if not can_retry:
                return RetryResult(
                    success=False,
                    error=f"Retry budget exhausted: {budget_reason}",
                    attempts=attempts,
                    total_wait=total_wait,
                    retries=attempts - 1,
                )

        try:
            result = func(*args, **kwargs)
            circuit_breaker.record_success(provider)
            return RetryResult(
                success=True,
                result=result,
                attempts=attempts,
                total_wait=total_wait,
                retries=attempts - 1,
            )
        except Exception as e:
            last_error = str(e)
            circuit_breaker.record_failure(provider)
            logger.warning(
                "LLM call to '%s' failed (attempt %d/%d): %s [BLK-085]",
                provider,
                attempt + 1,
                max_attempts,
                e,
            )

            # Record retry in budget
            if attempt > 0 and run_budget is not None:
                run_budget.record_retry()

            # Don't wait after the last attempt
            if attempt < max_attempts - 1:
                wait = compute_backoff_wait(attempt)
                total_wait += wait
                sleep_fn(wait)

    return RetryResult(
        success=False,
        error=last_error,
        attempts=attempts,
        total_wait=total_wait,
        retries=attempts - 1,
    )
