---
from: reviewer
to: mgmt
subject: "[REVIEW][HIGH][Security or privacy risk] API authentication is disabled by default and undocumented in .env.example — REV-002"
date: 2026-08-08T21:01:00+05:30
priority: high
status: new
in-reply-to: null
message-id: 2026-08-08_2101_reviewer-to-mgmt_auth-disabled-by-default
---

## Note on sender identity

Same reviewer-role caveat as REV-001 — see REV-004 for the underlying
protocol gap.

## Finding

```text
Finding ID: REV-002
Severity: high
Category: security or privacy risk
Confidence: high
Review pass: Pass 1 — security, privacy, authentication, authorization, abuse resistance
Affected areas: src/config.py (Settings.auth_enabled), src/api/auth.py
(middleware gate), .env.example, docker-compose.yml

Executive finding:
API key authentication (BLK-122) is fully implemented but ships
disabled by default, and the environment variable that turns it on is
absent from `.env.example` — the one file the README's Quick Start and
docker-compose deployment path tell an operator to copy and edit. A
deployment that follows the documented setup path exactly ends up with
every non-public route (runs, definitions, skills, templates,
documents, admin, budget, webhooks) open to any caller with network
access.

Evidence:
- `src/config.py`: `auth_enabled: bool = False` (default, under
  "# Authentication [BLK-122]").
- `src/api/auth.py` lines ~320-345: the auth dependency/middleware
  returns early ("Only active when settings.auth_enabled is True")
  whenever `not settings.auth_enabled` — i.e. every scope check in
  `ROUTE_SCOPES` (including `SCOPE_ADMIN` routes: `/api/v1/admin`,
  `/api/v1/webhooks`, `/api/v1/budget`) is bypassed entirely.
- `.env.example` (repo root) lists Azure keys, provider selection,
  thresholds, cycle caps, trace/compaction settings, logging, pricing,
  and budget limits — but contains no `ADE_AUTH_ENABLED` entry at all,
  so an operator following the documented `cp .env.example .env` step
  in README.md has no visible signal that authentication exists or
  needs to be turned on.
- `docker-compose.yml` exposes the backend directly on host port 8000
  with `restart: unless-stopped` and no auth-related environment
  override, so the containerized deployment path also ships open by
  default.

Impact:
Any operator who deploys ADEP via the documented Quick Start or the
provided docker-compose file — without independently discovering the
undocumented `ADE_AUTH_ENABLED` setting by reading `src/config.py`
source — exposes create/update/delete on definitions, skills,
templates, documents, budget controls, and webhook registration
(compounding REV-001) with zero authentication. Given the product's
stated target document categories include KYC, trade finance, and
medical-claims documents, an unauthenticated document/definition store
is a materially serious exposure for any real deployment, not just a
theoretical gap.

Why this matters:
This is a secure-by-default failure, not a missing feature — the
control exists and works, but the default configuration and the
primary documented setup path both leave it off with no in-band
warning (no startup log warning, no `.env.example` entry, no
README callout). Enterprise or regulated-industry buyers would treat
"auth off by default and undiscoverable via documented setup" as a
blocking finding in a security review.

Recommended management action:
Decide on a secure-by-default remediation: (a) default
`auth_enabled` to `True` with a documented bootstrap-key flow, or at
minimum (b) add `ADE_AUTH_ENABLED` to `.env.example` with an explicit
comment recommending it be enabled for any non-loopback deployment,
and add a startup log warning (not just silent bypass) when the app
boots with auth disabled. Recommend adding this to the security/ops
track for the current polish phase rather than leaving it as an
implicit assumption.

Suggested ownership:
Backend, with management/product sign-off on the default posture.

Validation required:
Start the API with a fresh `.env` copied from the updated
`.env.example` and confirm unauthenticated requests to a
`SCOPE_ADMIN` route are rejected (401/403) without any manual
extra configuration step beyond what `.env.example` documents.

Confidence and limitations:
Confirmed by direct source reading of `src/config.py`,
`src/api/auth.py`, `.env.example`, and `docker-compose.yml`. Not
tested against a running server in this review (no live environment
available); the early-return bypass logic in auth.py is unambiguous
in source, so confidence in the described behavior is high.

Related findings:
REV-001 (SSRF via webhook URL) — this finding is what makes REV-001
exploitable without any credential in the shipped default
configuration.
```
