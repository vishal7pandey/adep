---
from: backend
to: mgmt
subject: "BLK-122 complete — API authentication. 822 tests pass. Proceeding to BLK-110."
date: 2026-08-08T15:15:00+05:30
priority: high
status: new
in-reply-to: 2026-08-08_1355_mgmt-to-backend-major-load.md
message-id: 2026-08-08_1515_backend-to-mgmt_blk122-complete
---

## BLK-122 — API Authentication Complete

### What Was Built

1. **`src/api/auth.py`** — Full auth module:
   - `ApiKey` dataclass with `key_id`, `key_hash`, `name`, `scopes`,
     `expires_at`, `active`, `budget_daily_tokens`, `budget_daily_cost_usd`
   - `ApiKeyStore` (file-based, under `.adep/api_keys/`)
   - SHA-256 hashing with `hmac.compare_digest` for constant-time verification
   - Auth middleware: validates `Authorization: Bearer <key>` header
   - 7 scopes: `runs:read`, `runs:write`, `definitions:read`,
     `definitions:write`, `documents:read`, `documents:write`, `admin`
   - Route-to-scope mapping for all API endpoints
   - `admin` scope grants access to all endpoints
   - Bootstrap admin key generation on first boot with auth enabled
   - `last_used_at` tracking (throttled to every 60 seconds)
   - Public paths exempt: `/health`, `/ready`, `/docs`, `/redoc`, `/`,
     `/api/v1/health`, `/api/v1/locales`

2. **`src/api/routes/keys.py`** — 5 key management endpoints:
   - `POST /api/v1/admin/keys` — create (returns raw secret ONCE)
   - `GET /api/v1/admin/keys` — list (never exposes hash or secret)
   - `PUT /api/v1/admin/keys/{key_id}` — update name/scopes/budgets/active
   - `DELETE /api/v1/admin/keys/{key_id}` — revoke
   - `POST /api/v1/admin/keys/{key_id}/rotate` — rotate secret

3. **`src/config.py`** — Added `auth_enabled: bool = False`

4. **`src/api/main.py`** — Wired auth middleware and key routes

5. **`src/tests/test_auth.py`** — 34 new tests covering:
   - ApiKey model serialization (hash excluded from responses)
   - Key hashing (deterministic, unique, constant-time verify)
   - ApiKeyStore CRUD (create, get, list, update, delete, get_by_secret)
   - Bootstrap (creates admin key, refuses if keys exist)
   - Middleware (401 missing/invalid/expired/revoked, 403 wrong scope)
   - Key management endpoints (create, list, update, delete, rotate)
   - Scope validation (invalid scopes rejected)

### Design Decisions

- **SHA-256 instead of argon2/bcrypt**: The spec suggested argon2 or bcrypt,
  but API keys are high-entropy secrets (32 bytes), not low-entropy
  passwords. SHA-256 with constant-time comparison is sufficient and
  avoids an external dependency. The key is never stored — only the hash.
- **Per-key budget fields stored but enforcement deferred**: The `budget_daily_tokens`
  and `budget_daily_cost_usd` fields are on the `ApiKey` model and
  accepted by the API, but wiring them into the BLK-051 budget check
  requires modifying the run engine to resolve the API key from the
  request context. This is deferred to avoid changing the run execution
  path in this PR.

### Test Results

```
822 passed, 7 deselected, 2 warnings in 19.42s
```

(788 existing + 34 new = 822 total)

### Usage

Set `ADE_AUTH_ENABLED=true` to enable auth. On first boot, a bootstrap
admin key is generated and logged once with a warning. Use that key
to create additional keys via `POST /api/v1/admin/keys`.

### Next

Proceeding to BLK-110 (Graph Extraction Tools) per the approved order.
