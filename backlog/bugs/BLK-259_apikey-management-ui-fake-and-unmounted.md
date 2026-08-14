---
id: BLK-259
type: bug
title: "ApiKeyManagement UI is fake/in-memory dead code — never mounted, hardcoded SAMPLE_KEYS, no API calls"
priority: high
status: verifying
phase: 3
owner: antigravity
created: 2026-08-09T13:35:00+05:30
started: 2026-08-09T14:28:00+05:30
completed: null
estimate: S
depends-on: []
tags: [frontend, auth, api-keys, fake-data, dead-code, security]
---

## Description

`frontend/components/settings/ApiKeyManagement.tsx` (fully read this pass):

- Initializes from hardcoded `SAMPLE_KEYS` mock constants (violates the repo's "no fake data" rule, cf. BLK-166).
- "Create API Key" / "Revoke" only mutate local React state with `crypto.randomUUID()` — no call to `POST /api/v1/keys` / `DELETE`, no persistence.
- It is **not imported/mounted by any page or route** (grep: only its own file matches). It is dead code that also fakes a security feature.

Meanwhile the real key-management backend (`src/api/routes/keys.py`) exists with creation/revoke/list — the frontend that claims to manage keys does nothing and isn't even wired.

## Problem Statement

The UI suggests API-key management works when it does nothing (and isn't shown). Users who rely on it in dev will be confused; anyone grepping for "api key management" sees a confident `yes`. This is the exact "fake feature" class BLK-160/BLK-166 were filed to eliminate.

## Acceptance Criteria

- [x] Mount `ApiKeyManagement` into a real settings/security page (or remove the component)
- [x] Create/Revoke call the real keys API and update from server response (list on load, delete by id)
- [x] Delete `SAMPLE_KEYS`; the UI never fabricates keys or statuses
- [x] Secret shown exactly once at creation, then masked in all list views
- [ ] A test: create → POST /keys; revoke → DELETE; list reflects server state (handed off to cline per PROTOCOL §2.1 & §7.1)

## Constraints

- Use the existing keys endpoints (BLK-122, BLK-135); do not invent a new contract
- Coordinate with BLK-245 (SSE auth), BLK-254 (backend lookup perf)

## Dependencies

- `frontend/components/settings/ApiKeyManagement.tsx`
- `src/api/routes/keys.py`, `frontend/lib/api.ts`
- Related BLK-166 (no fake data), BLK-122 (auth)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
- **2026-08-09T13:35**: Filed after full read of the component — fake + unmounted + unused.
- **2026-08-09T14:30 (antigravity)**: Completed implementation. Removed `SAMPLE_KEYS`, added `fetchApiKeys`, `createApiKey`, `deleteApiKey` in `lib/api.ts`, mounted `ApiKeyManagement` in `app/settings/page.tsx`, and added `/settings` to `Sidebar.tsx`. Set status to `verifying` pending cline independent test sign-off.

## Resolution

- Removed hardcoded `SAMPLE_KEYS` mock array from `frontend/components/settings/ApiKeyManagement.tsx`.
- Implemented `fetchApiKeys()`, `createApiKey()`, and `deleteApiKey()` in `frontend/lib/api.ts` pointing to `GET/POST/DELETE ${API_BASE_URL}/admin/keys` (FastAPI backend at `src/api/routes/keys.py`).
- Connected `ApiKeyManagement` to load keys on mount, call `createApiKey()` upon form submission (displaying raw secret key once in reveal modal), and call `deleteApiKey()` upon revocation with confirmation prompt.
- Created `frontend/app/settings/page.tsx` route rendering `ApiKeyManagement` component.
- Added `/settings` navigation link titled "API Keys & Auth" in `frontend/components/layout/Sidebar.tsx`.
- Marked item `status: verifying` for independent test coverage & verification sign-off by **cline** per PROTOCOL §7.1.

## Evidence

- `frontend/lib/api.ts:L190-L265`: API functions `fetchApiKeys()`, `createApiKey()`, and `deleteApiKey()` calling FastAPI endpoints with `getAuthHeaders()`.
- `frontend/components/settings/ApiKeyManagement.tsx:L30-L210`: Component connected to real API endpoints, `SAMPLE_KEYS` deleted.
- `frontend/app/settings/page.tsx:L1-L12`: Settings page route rendering `ApiKeyManagement`.
- `frontend/components/layout/Sidebar.tsx:L275`: Navigation link to `/settings` added to sidebar.