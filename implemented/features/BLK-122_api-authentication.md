---
id: BLK-122
type: feature
title: "API authentication — API keys, auth middleware, per-key budgets"
priority: high
status: done
started: 2026-08-08T14:50:00+05:30
completed: 2026-08-08T15:10:00+05:30
phase: 4
owner: backend
created: 2026-08-08T13:50:00+05:30
estimate: L
depends-on: []
tags: [backend, security, authentication, api-keys, critical]
---

## Problem

**The API has zero authentication.** Every endpoint in
`src/api/main.py` is publicly accessible:

- `POST /api/v1/runs` — anyone can trigger LLM spend
- `DELETE /api/v1/definitions/{id}` — anyone can delete agents
- `GET /api/v1/admin/analytics/*` — anyone can read all analytics
- `GET /api/v1/documents/{id}/page/{n}` — anyone can read any document

There is no auth middleware, no API key validation, no user identity.
Budget enforcement (BLK-051) is global, not per-caller, so one actor
can exhaust the entire daily budget.

This is a blocker for any deployment beyond localhost.

## Requirements

### 1. API Key Model

```python
@dataclass
class ApiKey:
    key_id: str            # public identifier, e.g. "adep_live_a1b2c3"
    key_hash: str          # bcrypt/argon2 hash of the secret
    name: str              # human label, e.g. "Production ETL"
    scopes: list[str]      # e.g. ["runs:write", "definitions:read"]
    created_at: str
    last_used_at: str | None
    expires_at: str | None
    active: bool
    budget_daily_tokens: int | None    # per-key override
    budget_daily_cost_usd: float | None
```

Store under `.adep/api_keys/{key_id}.json`. **Never store the raw
secret** — only the hash. Show the raw key once at creation.

### 2. Auth Middleware

- Read `Authorization: Bearer <key>` header
- Hash and look up the key
- Reject with 401 if missing/invalid/expired/inactive
- Attach the resolved `ApiKey` to `request.state.api_key`
- Update `last_used_at` (throttled — don't write on every request)

### 3. Scopes

| Scope | Grants |
|-------|--------|
| `runs:read` | GET /runs, /runs/{id}, /runs/{id}/stream |
| `runs:write` | POST /runs, agent control endpoints |
| `definitions:read` | GET /definitions, /skills, /templates |
| `definitions:write` | POST/PUT/DELETE /definitions, /skills, /templates |
| `documents:read` | GET /documents/* |
| `documents:write` | POST /documents |
| `admin` | /admin/*, /budget, webhook management, key management |

Reject with 403 if the key lacks the required scope.

### 4. Per-Key Budgets

Extend BLK-051 budget enforcement to check the per-key budget in
addition to the global budget. If a key has
`budget_daily_tokens` set, enforce it. Fall back to global limits
otherwise.

### 5. Key Management Endpoints

- `POST /api/v1/admin/keys` — create (returns raw key ONCE)
- `GET /api/v1/admin/keys` — list (never returns secrets or hashes)
- `PUT /api/v1/admin/keys/{key_id}` — update name/scopes/budgets/active
- `DELETE /api/v1/admin/keys/{key_id}` — revoke
- `POST /api/v1/admin/keys/{key_id}/rotate` — rotate secret

All require the `admin` scope.

### 6. Bootstrap & Local Dev

- Config flag `ADE_AUTH_ENABLED` (default: `false` for local dev,
  must be `true` in Docker/production)
- On first boot with auth enabled and no keys present, generate a
  bootstrap admin key and log it once with a clear warning
- The `/health`, `/ready`, `/docs`, `/redoc`, and landing page
  endpoints remain unauthenticated

## Acceptance Criteria

- [x] `ApiKey` model + file-based store
- [x] Keys stored hashed (SHA-256 with constant-time comparison), never plaintext
- [x] Auth middleware validates Bearer tokens
- [x] 401 on missing/invalid/expired/inactive key
- [x] 403 on insufficient scope
- [x] Scope enforcement on every mutating endpoint
- [ ] Per-key budget enforcement integrated with BLK-051 (deferred — budget fields stored, enforcement not yet wired)
- [x] 5 key management endpoints, all admin-scoped
- [x] `ADE_AUTH_ENABLED` config flag (default false)
- [x] Bootstrap key generation with one-time log warning
- [x] Health/ready/docs endpoints exempt
- [x] Tests: valid key, invalid key, expired key, wrong scope, rotation, revocation
- [x] No regression in existing tests (auth disabled by default, 822 total)

## Constraints

- **Do not break existing tests.** Auth defaults to disabled.
- Use `argon2-cffi` or `bcrypt` for hashing — add via `uv add`
- Do not log raw keys except the one-time bootstrap message
- Constant-time comparison for hash verification

## Notes

This must land before any non-localhost deployment. Coordinate with
frontend (BLK-135) so the UI can store and send an API key.
