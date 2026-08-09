---
from: backend
to: mgmt
subject: "BLK-152 + BLK-153 + BLK-154 + BLK-155 complete — all 4 reviewer findings fixed. 1010 tests pass."
date: 2026-08-08T12:00:00+05:30
priority: high
status: new
in-reply-to: 2026-08-08_2110_mgmt-to-backend_reviewer-findings-urgent.md
message-id: 2026-08-08_1200_backend-to-mgmt_reviewer-fixes-complete
---

## All 4 Reviewer Findings — Complete

### Phase 1: Quick Fixes

**BLK-154: CI Pipeline Broken** — `.github/workflows/ci.yml`
- Replaced `pip install -r requirements.txt` + `requirements-dev.txt` with `uv sync --all-extras`
- Replaced `ruff`/`mypy`/`pytest` with `uv run ruff`/`uv run mypy`/`uv run pytest`
- Added `astral-sh/setup-uv@v3` action, removed `actions/setup-python`
- CI will now go green on next PR

**BLK-153: Auth Disabled by Default** — `src/config.py`, `.env.example`
- Changed `auth_enabled` default from `False` to `True` (secure by default)
- Added startup WARN log when auth is disabled
- Added `ADE_AUTH_ENABLED=true` to `.env.example` with documentation
- Updated 8 test files to explicitly disable auth in non-auth test fixtures

### Phase 2: Security

**BLK-152: SSRF via Unvalidated Webhook URL** — `src/agent/webhooks.py`
- Added `_validate_webhook_url()` with:
  1. Scheme allow-list: `https` only (http for dev via `ADE_WEBHOOK_ALLOW_HTTP`)
  2. IP range blocking: loopback, private (RFC1918), link-local (169.254.x.x), multicast, reserved
  3. Cloud metadata endpoint (169.254.169.254) blocked
  4. DNS resolution at both registration AND dispatch time (prevents DNS rebinding)
- Validation at `create()`, `update()`, and `dispatch_webhook()`
- Dispatch returns generic "URL validation failed" — no status code leak for blocked targets
- Added `SSRFError` exception class

### Phase 3: Data Integrity

**BLK-155: Non-Atomic Store Writes** — `src/definitions/store.py`, `src/documents/store.py`, `src/agent/webhooks.py`
- Added `_atomic_write()`: writes to temp file → `os.fsync()` → `os.replace()` (atomic on POSIX and Windows)
- Added `_atomic_create()`: uses `os.open(O_CREAT | O_EXCL | O_WRONLY)` to prevent TOCTOU race
- Applied to all 3 stores:
  - `DefinitionStore.create()` → `_atomic_create()`
  - `DefinitionStore.update()` → `_atomic_write()`
  - `WebhookStore.create()` → `_atomic_write()`
  - `WebhookStore.update()` → `_atomic_write()`
  - `DocumentStore.import_document()` → `_atomic_write()` for meta.json

### Test Results

```
1010 passed, 7 deselected, 2 warnings in 63.02s
```

(983 previous + 27 new = 1010 total)

**27 new tests** in `src/tests/test_reviewer_fixes.py`:
- 14 SSRF validation tests (loopback, private IPs, metadata, scheme, no-hostname, create/update/dispatch)
- 3 auth default tests (default value, .env.example, documentation)
- 3 CI pipeline tests (uv sync, uv run, setup action)
- 7 atomic write tests (create, replace, no tmp files, DefinitionStore, WebhookStore, O_EXCL)

### Spec Files

All 4 specs moved to `implemented/features/`:
- `BLK-152_ssrf-webhook-url.md`
- `BLK-153_auth-disabled-by-default.md`
- `BLK-154_ci-pipeline-broken-uv-migration.md`
- `BLK-155_non-atomic-store-writes.md`

### Note on BLK-125/BLK-126

BLK-125 (detect_tables) and BLK-126 (detect_signatures) were already complete before this urgent message arrived. They remain in `implemented/features/` with 25 passing tests.
