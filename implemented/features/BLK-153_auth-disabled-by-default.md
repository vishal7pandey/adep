# BLK-153: Auth disabled by default, missing from .env.example

**ID:** BLK-153
**Source:** REV-002 (independent reviewer)
**Severity:** High
**Category:** Security
**Status:** Done
**Assigned to:** Backend
**Estimate:** S

## Problem

API key authentication (BLK-122) is fully implemented but ships disabled
by default (`auth_enabled: bool = False` in `src/config.py:89`). The
environment variable `ADE_AUTH_ENABLED` is absent from `.env.example` —
the file the README Quick Start and docker-compose path tell operators
to copy.

A deployment following the documented setup path ends up with every
endpoint (runs, definitions, skills, templates, documents, admin,
budget, webhooks) open to any caller with network access.

## Evidence

- `src/config.py:89` — `auth_enabled: bool = False`
- `src/api/auth.py` — middleware returns early when
  `not settings.auth_enabled`, bypassing all scope checks.
- `.env.example` — no `ADE_AUTH_ENABLED` entry.
- `docker-compose.yml` — exposes port 8000 with no auth env override.

## Resolution

1. Add `ADE_AUTH_ENABLED=true` to `.env.example` with a comment
   recommending it be enabled for any non-loopback deployment.
2. Add a startup log warning (WARN level) when the app boots with auth
   disabled: "AUTH DISABLED — all API endpoints are unauthenticated."
3. Document the bootstrap key flow in README (how to create the first
   admin key when auth is enabled).

## Tests

- Start with fresh `.env` from `.env.example` → unauthenticated request
  to `SCOPE_ADMIN` route returns 401/403.
- Start with `ADE_AUTH_ENABLED=false` → startup log contains warning.
