---
id: BLK-135
type: feature
title: "API key management UI + auth-aware client"
priority: medium
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T13:50:00+05:30
estimate: M
depends-on: [BLK-122]
tags: [frontend, security, auth, api-keys, settings]
---

## Problem

Once backend lands BLK-122 (API authentication), the frontend must
send credentials and let admins manage keys. Currently `lib/api.ts`
sends no auth header at all.

## Requirements

### 1. Auth-Aware API Client

- Attach `Authorization: Bearer <key>` to every request
- Read the key from a single source (see storage note below)
- On `401`, clear the stored key and route to the auth prompt
- On `403`, show a clear "insufficient permissions" message naming the
  required scope rather than a generic error

### 2. Key Storage

Store the key in `sessionStorage`, not `localStorage`.

Rationale: `localStorage` persists indefinitely and is readable by any
XSS payload. `sessionStorage` at least dies with the tab. Note plainly
in the code comment that neither is truly secure against XSS, and that
a proper solution is an httpOnly cookie issued by a session endpoint —
which requires a backend session layer that does not exist yet.

**Do not** put the key in a URL, a query parameter, or any logged
object.

### 3. Auth Prompt

When auth is enabled and no valid key is present:

```
  Connect to ADEP

  API key:  [____________________]
            Paste your key. It's stored for this
            browser session only.

  [ Connect ]
```

- Validate by calling a lightweight authenticated endpoint
- Show a specific error for invalid vs expired vs revoked
- Never echo the key back into the DOM after submission

### 4. Key Management (admin scope)

A Settings → API Keys page:

- List keys: name, key id prefix, scopes, created, last used, status
- **Never display full secrets** — they are unrecoverable by design
- Create: name + scope checkboxes + optional expiry + optional budget
  overrides
- On creation, show the raw key **once** in a modal with an explicit
  "copy now, you won't see this again" warning and a copy button
- Rotate: confirm dialog, then show the new key once
- Revoke: confirm dialog naming the key, warn that in-flight
  integrations will break

### 5. Graceful Degradation

Auth is disabled by default in local dev (`ADE_AUTH_ENABLED=false`).
The UI must work with no key present in that case — detect via a
capability probe rather than hardcoding an assumption, and hide the
auth prompt and key management entirely when auth is off.

## Acceptance Criteria

- [ ] `Authorization: Bearer` header on all requests
- [ ] Key read from sessionStorage; comment documents the XSS caveat
- [ ] Key never placed in a URL, query param, or logged object
- [ ] 401 clears the key and routes to the auth prompt
- [ ] 403 names the required scope
- [ ] Auth prompt validates against a real endpoint
- [ ] Distinct errors for invalid / expired / revoked
- [ ] Settings → API Keys list view (no secrets shown)
- [ ] Create flow with scope selection and one-time key reveal
- [ ] One-time reveal modal has an explicit non-recoverable warning
- [ ] Rotate and revoke with confirmation dialogs
- [ ] UI fully functional when auth is disabled
- [ ] Auth UI hidden entirely when auth is disabled
- [ ] Tests: header attachment, 401 handling, 403 handling,
      auth-disabled path

## Constraints

- Blocked on backend BLK-122. Build against a mocked auth layer first.
- Do not implement a bespoke crypto or token scheme in the frontend.
- Treat the key as a secret in every code path, including error
  reporting and analytics.
