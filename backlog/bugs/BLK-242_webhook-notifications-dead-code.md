---
id: BLK-242
type: bug
title: "emit_webhook_event is never called — webhook notifications are dead code, and dispatch blocks the event loop"
priority: high
status: backlog
phase: 1
owner: devin
created: 2026-08-09T12:10:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [backend, webhooks, notifications, dead-code, async-blocking, reliability]
---

## Description

`src/agent/webhooks.py` implements the full webhook feature (`dispatch_webhook` with HMAC-SHA256 signing, retry-with-backoff, SSRF validation). However, the entry point that would trigger a webhook after a real run completes, `emit_webhook_event` (webhooks.py:388), is imported **only by tests** (`src/tests/test_wave7.py`, `src/tests/test_reviewer_fixes.py`). Grep across all production modules (`src/api/*`, `src/agent/graph.py`, `src/api/run_engine.py`, `run_executor.py`) shows zero production call sites.

Separately, `dispatch_webhook` uses synchronous `urllib.request.urlopen` with `time.sleep` backoff (up to ~3 × 10s + jitter). Where it *is* reachable — the `test_webhook` endpoint (`src/api/routes/webhooks.py:137`) — it runs inline in an async FastAPI handler, blocking the event loop while retrying.

## Problem Statement

- A user can create a webhook in the UI/API, but **no run completion ever triggers it**. The BLK-064 feature is effectively a lie the UI exposes (settings + a working "test webhook" button, but zero production delivery).
- When it *is* invoked (via the test endpoint or any future wiring), the sync HTTP + sleep retries block the entire API loop, replicating the BLK-224 event-loop problem at a smaller scale (up to ~36s).

## Acceptance Criteria

- [ ] `emit_webhook_event` is called from the run lifecycle on genuine terminal states (completed/failed/cancelled) in `run_engine.py`/`run_executor.py` with the serialized run payload
- [ ] Webhook dispatch is asynchronous (e.g. `httpx.AsyncClient`), never blocking the event loop; retries use `asyncio.sleep`
- [ ] A run-completion integration test asserts at least one webhook was delivered to a local test server
- [ ] The `test_webhook` endpoint remains but also uses the async dispatch path
- [ ] Document delivery guarantees honestly (at-most-once vs at-least-once) so users know the contract

## Constraints

- Keep the HMAC signature algorithm (BLK-064) unchanged for compatibility
- Keep SSRF validation (BLK-152) at dispatch time; do not weaken the DNS-rebinding protections to make the call async
- Non-blocking behavior is required; do not call sync `urlopen` from the async loop

## Dependencies

- `src/agent/webhooks.py` (`dispatch_webhook`, `emit_webhook_event`)
- `src/api/routes/webhooks.py`
- `src/api/run_engine.py` / `run_executor.py` (wiring point)
- `src/tests/test_wave7.py`, `src/tests/test_reviewer_fixes.py`

## Notes

- Found in full-repo cross-reference: only tests reference the emission function.
- This is a "feature exists, wiring missing" bug most like BLK-149-era issues; must be wired before users can rely on hook-driven automation.

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T12:10 (mgmt)**: Filed — `emit_webhook_event` dead in production; sync dispatch can freeze the loop.
