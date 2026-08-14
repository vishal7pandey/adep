---
id: BLK-254
type: bug
title: "AuthMiddleware sync file I/O and token parsing on every request — API-key lookup is O(n) file reads with no async"
priority: high
status: backlog
phase: 2
owner: devin
created: 2026-08-09T13:10:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-122]
tags: [backend, auth, performance, async, api-keys, tech-debt, reliability]
---

## Description

`src/api/auth.py`'s middleware performs synchronous file I/O and JSON parsing on every authenticated request:

- `get_by_secret()` reads and parses **every** key JSON file under `.adep/api_keys/` on every request (BLK-122), and iterates to find the one with a matching secret hash — O(n) disk reads per request.
- Key files are cached only weakly; the constant parse loop runs even when auth is enabled in normal operation (default `auth_enabled=True`).
- The secret is stored as an unsalted SHA-256 (acceptable length, but no work factor), and earlier config/audit noted this.

## Problem Statement

With auth enabled by default and every API call to `/api/v1/**` (except public) hitting this loop, request latency scales linearly with the number of stored keys, and sync file I/O runs on the event loop. Under load this is a perf and a DoS surface (thousands of file opens per request batch). There's no caching/TTL, no index, and no way to isolate one key's lookup.

## Acceptance Criteria

- [ ] API-key lookup uses an in-memory index/cache (e.g. prefix → path or secret hash → key) keyed on boot and kept current on create/revoke/expire; only one file read on hit
- [ ] Lookups are awaited/async (or run in a worker) — no sync `open()`/`json.load` on the event loop
- [ ] A benchmark test asserts <2ms median for key lookup with N=100 keys
- [ ] Revocation (key delete/disable) invalidates the cache synchronously
- [ ] Secret handling: keep `secrets.token_urlsafe`-sourced, consider documented salt; on-read equality must be constant-time

## Constraints

- Do not change the auth contract or the scopes model (see BLK-215 for the fail-open gap); this is purely performance/implementation hardening
- Keep backward compatibility with existing key files on disk

## Dependencies

- `src/api/auth.py`
- `src/api/routes/keys.py`
- `src/tests` (auth tests)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T13:10 (mgmt)**: Filed from audit: O(N) sync key-file reads in middleware; no per-key isolation.
