---
id: BLK-085
type: feature
title: "Retry storm prevention & circuit breaker"
priority: high
status: backlog
phase: 4
owner: backend
created: 2026-08-08T01:45:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-050, BLK-051]
tags: [backend, security, guardrails, retry, circuit-breaker, rate-limiting, resilience]
---

## Description

Prevent retry storms when the LLM API is degraded. Implement exponential
backoff, circuit breaker pattern, and per-run retry budgets.

## Motivation

When the LLM API returns errors (429, 500, timeout), naive retry logic
can amplify load — 10 concurrent runs each retrying 3x creates 30
requests against an already-struggling API. This makes things worse and
burns budget on failed calls.

## Guardrails

1. **Exponential backoff:** Retries use exponential backoff with jitter:
   `wait = min(base * 2^attempt + random_jitter, max_wait)`
   - base: 2 seconds
   - max_wait: 60 seconds
   - max_attempts: 3

2. **Circuit breaker:** Track LLM API health across all runs:
   - **Closed** (normal): requests pass through
   - **Open** (tripped): after 5 consecutive failures, all new LLM calls
     fail-fast for 60 seconds. No retries during open state.
   - **Half-open**: after cooldown, allow 1 test request. If it succeeds,
     close the circuit. If it fails, re-open.

3. **Per-run retry budget:** Each run has a max retry count (default 10
   across all cycles). When exhausted, the run terminates with
   `status: 'api_exhausted'`.

4. **Token-aware retry:** Retries consume tokens. Track retry token
   cost separately from extraction token cost. If retries consume > 20%
   of the run budget, stop retrying.

5. **Provider fallback:** If the primary LLM provider circuit is open,
   automatically fall back to a secondary provider (if configured).

6. **Retry event logging:** Every retry is logged with: attempt number,
   error type, wait time, whether circuit is open/closed.

## Acceptance Criteria

- [ ] Exponential backoff with jitter on LLM API errors
- [ ] Circuit breaker opens after 5 consecutive failures
- [ ] Circuit breaker auto-recovers via half-open test
- [ ] Per-run retry budget enforced
- [ ] Retry token cost tracked separately
- [ ] Provider fallback on circuit open
- [ ] All retries logged
- [ ] Unit tests: retry storm, circuit open/close, budget exhaustion

## Dependencies

- BLK-050 (token tracking)
- BLK-051 (budget enforcement)
