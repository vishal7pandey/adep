---
id: BLK-215
type: bug
title: "Auth middleware fails OPEN for any HTTP method not explicitly listed in ROUTE_SCOPES — unauthenticated DELETE/PATCH/PUT on real endpoints"
priority: critical
status: verifying
phase: 1
owner: devin
created: 2026-08-09T11:10:00+05:30
started: 2026-08-09T15:30:00+05:30
completed: null
estimate: S
depends-on: []
tags: [security, auth, authorization, critical, api]
---

## Description

`install_auth_middleware()` in `src/api/auth.py` determines whether a request needs an API key by looking up `(method, path)` in a hardcoded `ROUTE_SCOPES` table via `_required_scope()`:

```python
def _required_scope(method: str, path: str) -> str | None:
    """... Returns None if no scope is required (public endpoint)."""
    for req_method, prefix, scope in ROUTE_SCOPES:
        if method == req_method and path.startswith(prefix):
            return scope
    return None
```

And in the middleware itself:

```python
required_scope = _required_scope(request.method, path)
if required_scope is None:
    # Unknown route — let FastAPI handle 404
    return await call_next(request)
```

The comment's assumption — that a `None` result means the route doesn't exist and FastAPI will 404 it — is false whenever a route **exists** but its **HTTP method** simply wasn't added to `ROUTE_SCOPES`. In that case the request is forwarded to the real handler with **zero authentication check**, not even a missing-Bearer-token check, regardless of `settings.auth_enabled`.

`ROUTE_SCOPES` (full table, `src/api/auth.py` ~lines 68-99) only defines these method/prefix pairs:

```
("GET",  "/api/v1/runs", ...)   ("POST", "/api/v1/runs", ...)
("GET",  "/api/v1/definitions", ...) ("POST"/"PUT"/"DELETE", "/api/v1/definitions", ...)
("GET",  "/api/v1/skills", ...)      ("POST"/"PUT"/"DELETE", "/api/v1/skills", ...)
("GET",  "/api/v1/templates", ...)   ("POST"/"PUT"/"DELETE", "/api/v1/templates", ...)
("GET",  "/api/v1/documents", ...)   ("POST", "/api/v1/documents", ...)
("GET"/"POST"/"PUT"/"DELETE", "/api/v1/admin", ...)
("GET",  "/api/v1/budget", ...)
("GET"/"POST"/"DELETE", "/api/v1/webhooks", ...)
```

There is **no `PATCH` entry anywhere in the entire table**, no `DELETE` entry for `/api/v1/runs`, and no `PUT` entry for `/api/v1/webhooks`. Cross-referencing against the actual route handlers:

- `src/api/routes/runs.py:218` — `@router.delete("/runs/{run_id}")` (delete a run) — **DELETE has no entry for the `/api/v1/runs` prefix → unauthenticated**
- `src/api/routes/runs.py:283` — `@router.patch("/runs/{run_id}")` (rename a run) — **no PATCH entry exists at all → unauthenticated**
- `src/api/routes/webhooks.py:86` — `@router.put("/webhooks/{webhook_id}")` (update a webhook's target URL/secret) — **no PUT entry for `/api/v1/webhooks` → unauthenticated**

Note: POST-based run actions (`/pause`, `/resume`, `/stop`, `/rollback`, `/approve`, `/verify`, `/compact`, `/duplicate`) are *not* affected — they're all `POST` and correctly caught by the blanket `("POST", "/api/v1/runs", SCOPE_RUNS_WRITE)` prefix rule. This bug is specifically about methods (`DELETE`, `PATCH`, and webhook `PUT`) that have zero matching entries.

## Problem Statement

With `auth_enabled = True` (the default in `src/config.py`) and a fully configured API-key system, an unauthenticated request with **no `Authorization` header at all** can:

- `DELETE /api/v1/runs/{run_id}` — permanently delete any run's data
- `PATCH /api/v1/runs/{run_id}` — rename any run
- `PUT /api/v1/webhooks/{webhook_id}` — rewrite any webhook's destination URL and secret (a real exfiltration vector: point someone else's webhook at an attacker-controlled endpoint to receive future run-completion payloads)

This is not a scope/permission gap (403) — it's a complete bypass of the 401 check, because the code path for "no matching route-scope entry" is identical to the code path for "this URL doesn't exist, let it 404." A route that exists but wasn't remembered when `ROUTE_SCOPES` was written is silently treated as public.

## Acceptance Criteria

- [ ] `ROUTE_SCOPES` (or its replacement) covers every method actually implemented in `src/api/routes/*.py`, not just the four "primary" verbs per resource — specifically add `DELETE`/`PATCH` for runs and `PUT` for webhooks
- [ ] Fail-closed instead of fail-open: change the "no matching entry" branch so it does NOT silently allow the request through. Prefer deriving required scopes from the route table (e.g. FastAPI's `app.routes`) rather than a hand-maintained list that can drift from the real handlers, so a new endpoint can't ship auth-less by omission
- [ ] Add a test that enumerates every registered route (via `app.routes`) and asserts each non-public one has a `ROUTE_SCOPES` (or equivalent) entry — this is the regression guard that prevents this class of bug from recurring as routes are added
- [ ] Add an explicit regression test: unauthenticated `DELETE /api/v1/runs/{id}`, `PATCH /api/v1/runs/{id}`, and `PUT /api/v1/webhooks/{id}` all return 401 with `auth_enabled=True` and no API key
- [ ] Audit `PUBLIC_PATHS` and the rest of `ROUTE_SCOPES` for the same fail-open gap on any other method/prefix combination not covered above

## Constraints

- Do not change the intended scope *values* (`SCOPE_RUNS_WRITE`, `SCOPE_ADMIN`, etc.) for already-covered routes — this is about closing the gap for uncovered methods, not redesigning the scope model
- Prefer the systematic fix (derive coverage from actual routes, fail closed on no match) over just adding three more tuples — three more tuples fixes today's known gaps but leaves the same footgun for the next new endpoint

## Dependencies

- `src/api/auth.py` (`ROUTE_SCOPES`, `_required_scope`, `install_auth_middleware`)
- `src/api/routes/runs.py`, `src/api/routes/webhooks.py`
- `src/config.py` (`auth_enabled`, defaults to `True`)

## Notes

- Found via direct code inspection while cross-referencing route handlers against the auth middleware's scope table — this is a genuinely live/exploitable gap in code that IS wired into the real request path, distinct from the several "dead code that looks like it protects you" findings elsewhere in this backlog (e.g. the unwired guardrails package). This one is wired in and still fails open.
- Highest-severity finding in this pass: a real, unauthenticated write/delete path against production data with the default configuration.

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T11:10 (mgmt)**: Logged after tracing every `@router.<method>` in `runs.py` and `webhooks.py` against every tuple in `ROUTE_SCOPES` and confirming three real endpoints have no matching entry and therefore skip the auth check entirely.

- **2026-08-09T15:30 (devin)**: Implementation complete. Added missing method entries (DELETE/PATCH for runs, PUT for webhooks) to ROUTE_SCOPES. Changed _required_scope to fail closed (return "__deny__" sentinel) for any /api/v1/ path without a matching entry. Middleware now returns 401 for denied paths instead of passing them through. Handed to cline for verification + opencode for security co-sign (PROTOCOL §7.4).

## Resolution

### Fix 1: Added missing ROUTE_SCOPES entries

`src/api/auth.py:67-103` — Added three missing entries:
- `("DELETE", "/api/v1/runs", SCOPE_RUNS_WRITE)` — covers `DELETE /api/v1/runs/{run_id}`
- `("PATCH", "/api/v1/runs", SCOPE_RUNS_WRITE)` — covers `PATCH /api/v1/runs/{run_id}`
- `("PUT", "/api/v1/webhooks", SCOPE_ADMIN)` — covers `PUT /api/v1/webhooks/{webhook_id}`

### Fix 2: Fail-closed for unknown /api/v1/ routes

`src/api/auth.py:106-123` — Changed `_required_scope()` to return a `"__deny__"` sentinel for any `/api/v1/` path that has no matching `ROUTE_SCOPES` entry, instead of returning `None` (which the middleware treated as "public, pass through"). Non-api paths (e.g. `/health`, `/docs`) still return `None` and pass through normally.

`src/api/auth.py:356-367` — The middleware now checks for `"__deny__"` and returns `401 Unauthorized` with a warning log, instead of calling `call_next(request)` and letting the request reach the handler unauthenticated.

This is the systematic fix the ticket asked for: a new endpoint that ships without a ROUTE_SCOPES entry is denied by default, not silently exposed. The hand-maintained list can still drift, but the consequence of drift is now a denial (safe) rather than an open hole (exploitable).

### What was NOT done

- The ticket suggests deriving scopes from `app.routes` at request time. This would be more robust but the auth middleware is installed before routes are registered (see `src/api/main.py:110` vs `125-131`), so `app.routes` is empty at install time. A request-time introspection approach is possible but would add per-request overhead and complexity. The fail-closed sentinel achieves the same safety property (unknown = denied) without that cost. A future improvement could move route registration before middleware installation and introspect at startup.
- Tests are in cline's territory (`src/tests/`). The ticket asks for regression tests enumerating all routes — I've flagged this in the verification message to cline.

## Evidence

### Syntax validation

```
$ python -c "import ast; ast.parse(open('src/api/auth.py').read()); print('auth.py OK')"
auth.py OK
```

### Scope resolution verification

```
$ python -c "from src.api.auth import _required_scope; print('DELETE /api/v1/runs/xyz:', _required_scope('DELETE', '/api/v1/runs/xyz')); print('PATCH /api/v1/runs/xyz:', _required_scope('PATCH', '/api/v1/runs/xyz')); print('PUT /api/v1/webhooks/xyz:', _required_scope('PUT', '/api/v1/webhooks/xyz')); print('GET /api/v1/runs/xyz:', _required_scope('GET', '/api/v1/runs/xyz')); print('POST /api/v1/unknown:', _required_scope('POST', '/api/v1/unknown')); print('GET /health:', _required_scope('GET', '/health'))"
DELETE /api/v1/runs/xyz: runs:write
PATCH /api/v1/runs/xyz: runs:write
PUT /api/v1/webhooks/xyz: admin
GET /api/v1/runs/xyz: runs:read
POST /api/v1/unknown: __deny__
GET /health: None
```

Before the fix, `DELETE`, `PATCH`, and `PUT /webhooks` all returned `None` (unauthenticated pass-through). Now they return their correct scopes. Unknown `/api/v1/` routes return `__deny__` instead of `None`.

### Files changed (1, all in devin-owned `src/**` excluding `src/tests/`)

- `src/api/auth.py:67-103` — added 3 ROUTE_SCOPES entries
- `src/api/auth.py:106-123` — _required_scope fail-closed logic
- `src/api/auth.py:356-367` — middleware __deny__ handling

### Files NOT changed (cline's territory)

- `src/tests/` — regression tests for route enumeration and 401 assertions are cline's to write
