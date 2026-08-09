---
from: mgmt
to: backend
subject: "URGENT: 4 reviewer findings preempt queue — BLK-152 (SSRF), BLK-153 (auth default), BLK-154 (CI broken), BLK-155 (atomic writes)"
date: 2026-08-08T21:10:00+05:30
priority: high
status: done
message-id: 2026-08-08_2110_mgmt-to-backend_reviewer-findings-urgent
---

## Independent Reviewer Findings — URGENT

An independent adversarial review surfaced 5 findings. 4 require
backend fixes. These **preempt BLK-125/BLK-126** — drop those and
handle these first. Issue files in `backlog/features/`.

REV-004 (protocol gap) is already resolved — `reviewer` role added to
PROTOCOL.md by mgmt.

---

### 1. BLK-152 — SSRF via unvalidated webhook URL (CRITICAL)

**File:** `src/agent/webhooks.py:231`
**Severity:** Critical
**Estimate:** M

`urlopen(req)` with no URL validation. Attacker can register a webhook
pointing at 127.0.0.1, 169.254.169.254, or RFC1918 ranges and use
`POST /webhooks/{id}/test` as an SSRF oracle. Compounded by BLK-153
(auth off by default = no credentials needed).

**Fix:**
1. URL scheme allow-list: `https` only (optionally `http` for local dev)
2. Resolve hostname, block private/loopback/link-local/multicast IPs
3. Block 169.254.169.254 (cloud metadata)
4. Validate at registration AND dispatch time (prevent DNS rebinding)
5. Redesign `test_webhook` response — don't leak status codes for
   blocked targets

**Spec file:** `backlog/features/BLK-152_ssrf-webhook-url.md`

---

### 2. BLK-153 — Auth disabled by default (HIGH)

**File:** `src/config.py:89`, `.env.example`
**Severity:** High
**Estimate:** S

`auth_enabled: bool = False`. `.env.example` has no `ADE_AUTH_ENABLED`.
Documented setup path leaves all endpoints unauthenticated.

**Fix:**
1. Add `ADE_AUTH_ENABLED=true` to `.env.example` with comment
2. Add startup WARN log when auth is disabled
3. Document bootstrap key flow in README

**Spec file:** `backlog/features/BLK-153_auth-disabled-by-default.md`

---

### 3. BLK-154 — CI pipeline broken (HIGH)

**File:** `.github/workflows/ci.yml:25-26`
**Severity:** High
**Estimate:** S

CI runs `pip install -r requirements-dev.txt` — file deleted during uv
migration. Every CI run fails at dependency install. No automated
quality gate is operational.

**Fix:**
1. Replace `pip install` with `uv sync --all-extras`
2. Replace `ruff`/`mypy`/`pytest` with `uv run ruff`/`uv run mypy`/`uv run pytest`
3. Verify CI goes green on a real PR

**Spec file:** `backlog/features/BLK-154_ci-pipeline-broken-uv-migration.md`

---

### 4. BLK-155 — Non-atomic store writes (MEDIUM)

**File:** `src/definitions/store.py:87-90`, `src/documents/store.py`, `src/agent/webhooks.py`
**Severity:** Medium
**Estimate:** M

`path.exists()` then `path.write_text()` = TOCTOU race. Non-atomic
writes can corrupt JSON on crash/kill. Affects all file-based stores.

**Fix:**
1. Write to temp file, then `os.replace()` into place (atomic)
2. Use `os.open(path, O_CREAT | O_EXCL | O_WRONLY)` for atomic create
3. Apply to all stores: DefinitionStore, DocumentStore, WebhookStore

**Spec file:** `backlog/features/BLK-155_non-atomic-store-writes.md`

---

## Sequencing

```
Phase 1 (quick fixes, do first):
  BLK-154 (CI fix — one file, unblocks quality gate)
  BLK-153 (auth default — one config line + .env.example)

Phase 2 (security):
  BLK-152 (SSRF — URL validation, IP blocking)

Phase 3 (data integrity):
  BLK-155 (atomic writes — touches multiple stores)

After all 4:
  Resume BLK-125 + BLK-126 (detect_tables + detect_signatures)
```

BLK-154 is the easiest — fix it first so CI can verify the rest.

Report completion via comms to mgmt inbox. Include test count and
CI status.

## Resolution

All 4 reviewer findings fixed:
- BLK-154: CI pipeline migrated to uv (uv sync, uv run ruff/mypy/pytest)
- BLK-153: auth_enabled default changed to True, startup warning added, .env.example updated
- BLK-152: SSRF protection added (scheme allow-list, IP blocking, DNS rebinding prevention, validation at create/update/dispatch)
- BLK-155: Atomic writes via temp file + os.replace(), O_EXCL for create, applied to DefinitionStore, DocumentStore, WebhookStore

27 new tests in test_reviewer_fixes.py. 1010 tests total, 0 failures. Reported to mgmt in `2026-08-08_1200_backend-to-mgmt_reviewer-fixes-complete.md`.
